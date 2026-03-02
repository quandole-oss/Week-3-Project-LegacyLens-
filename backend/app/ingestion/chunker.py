"""Fortran-aware code chunking for LAPACK source files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CodeChunk:
    text: str
    file_path: str
    start_line: int
    end_line: int
    routine_name: str
    routine_type: str  # "subroutine", "function", "program", "block_data", "module"
    language: str  # "f77" or "f90"
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        safe_path = self.file_path.replace("/", "_").replace(".", "_")
        return f"{safe_path}_{self.routine_name}_{self.start_line}"

    def embedding_text(self) -> str:
        """Text sent to the embedding model, with metadata header."""
        header = (
            f"File: {self.file_path} | "
            f"Routine: {self.routine_name} | "
            f"Type: {self.routine_type} | "
            f"Language: {self.language}"
        )
        return f"{header}\n{self.text}"


# Pattern to match Fortran routine boundaries
ROUTINE_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:(?:RECURSIVE|PURE|ELEMENTAL|INTEGER|REAL|DOUBLE\s+PRECISION|COMPLEX|CHARACTER|LOGICAL)\s+)*'
    r'(SUBROUTINE|FUNCTION|PROGRAM|BLOCK\s+DATA)\s+(\w+)',
    re.IGNORECASE | re.MULTILINE,
)

# Pattern to match LAPACK structured header sections (both * and ** prefix styles)
HEADER_SECTION_PATTERN = re.compile(
    r'^\*{1,2}\s+(Purpose|Arguments|Further Details|Description)',
    re.IGNORECASE | re.MULTILINE,
)

# Patterns for COMMON blocks and INCLUDE statements
COMMON_PATTERN = re.compile(
    r'^[ \t]*COMMON\s*/\s*(\w+)\s*/',
    re.IGNORECASE | re.MULTILINE,
)

INCLUDE_PATTERN = re.compile(
    r'^[ \t]*INCLUDE\s+[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE | re.MULTILINE,
)

# Pattern to match END of routines
END_PATTERN = re.compile(
    r'^[ \t]*END\s*(?:SUBROUTINE|FUNCTION|PROGRAM|BLOCK\s+DATA)?\s*(\w*)',
    re.IGNORECASE | re.MULTILINE,
)


def _extract_preceding_comments(lines: list[str], routine_start: int) -> int:
    """Walk backwards from routine_start to find the beginning of the comment block."""
    idx = routine_start - 1
    while idx >= 0:
        line = lines[idx].strip()
        # LAPACK comment lines start with '*' or 'C' or '!' in column 1
        if line and (line[0] in ('*', 'C', 'c', '!')):
            idx -= 1
        elif line == '':
            idx -= 1
        else:
            break
    return idx + 1


def _parse_header_sections(lines: list[str], start: int, end: int) -> dict[str, str]:
    """Parse structured LAPACK header sections from comment block.

    Looks for sections like:
        *  Purpose
        *  =======
        *  DGESV computes the solution to ...
    or:
        **  Purpose
        **  =======

    Returns dict with keys like 'purpose', 'arguments', 'further_details'.
    """
    sections: dict[str, str] = {}
    current_section = None
    current_lines: list[str] = []

    for i in range(start, min(end + 1, len(lines))):
        line = lines[i]
        match = HEADER_SECTION_PATTERN.match(line)
        if match:
            # Save previous section
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines).strip()
            current_section = match.group(1).lower().replace(' ', '_')
            current_lines = []
        elif current_section:
            # Strip comment prefix (* or ** or !) and collect text
            stripped = line.lstrip()
            if stripped and stripped[0] in ('*', '!'):
                # Remove leading asterisk(s) and space
                text = stripped.lstrip('*').lstrip('!').lstrip()
                # Skip separator lines (=== or ---)
                if text and not all(c in '=-' for c in text):
                    current_lines.append(text)
            elif not stripped:
                current_lines.append('')

    # Save last section
    if current_section and current_lines:
        sections[current_section] = '\n'.join(current_lines).strip()

    return sections


def _extract_common_and_includes(text: str) -> dict:
    """Extract COMMON block names and INCLUDE file references from code."""
    common_blocks = sorted(set(m.group(1).upper() for m in COMMON_PATTERN.finditer(text)))
    includes = sorted(set(m.group(1) for m in INCLUDE_PATTERN.finditer(text)))
    result = {}
    if common_blocks:
        result['common_blocks'] = ', '.join(common_blocks)
    if includes:
        result['includes'] = ', '.join(includes)
    return result


def create_file_summary_chunk(
    file_content: str,
    file_path: str,
    language: str,
    routine_chunks: list[CodeChunk],
) -> CodeChunk | None:
    """Create a file-level summary chunk that aggregates routine info.

    This enables broader file-level queries like "what routines are in dgesv.f?"
    """
    if not routine_chunks:
        return None

    routine_summaries = []
    for chunk in routine_chunks:
        summary = f"- {chunk.routine_type} {chunk.routine_name}"
        purpose = chunk.metadata.get('purpose', '')
        if purpose:
            # Take first sentence of purpose
            first_sentence = purpose.split('.')[0].strip()
            if first_sentence:
                summary += f": {first_sentence}"
        routine_summaries.append(summary)

    total_lines = file_content.count('\n') + 1
    summary_text = (
        f"File: {file_path} ({language}, {total_lines} lines)\n"
        f"Contains {len(routine_chunks)} routine(s):\n"
        + '\n'.join(routine_summaries)
    )

    # Collect file-level COMMON/INCLUDE references
    file_meta = _extract_common_and_includes(file_content)
    file_meta['is_file_summary'] = 'true'

    return CodeChunk(
        text=summary_text,
        file_path=file_path,
        start_line=1,
        end_line=total_lines,
        routine_name=f"_file_summary_{file_path.split('/')[-1].replace('.', '_')}",
        routine_type="file_summary",
        language=language,
        metadata=file_meta,
    )


def chunk_fortran_file(
    file_content: str,
    file_path: str,
    language: str,
    max_chunk_tokens: int = 800,
    overlap_tokens: int = 200,
) -> list[CodeChunk]:
    """Split a Fortran file into chunks based on routine boundaries."""
    lines = file_content.split('\n')
    chunks = []

    # Find all routine boundaries
    routines = []
    for match in ROUTINE_PATTERN.finditer(file_content):
        routine_type = match.group(1).strip().lower().replace(' ', '_')
        routine_name = match.group(2).strip()
        # Find line number of match
        line_num = file_content[:match.start()].count('\n')
        routines.append((line_num, routine_name, routine_type))

    if not routines:
        # No routines found -- fall back to fixed-size chunking
        return _fixed_size_chunks(file_content, file_path, language,
                                  max_chunk_tokens, overlap_tokens)

    for i, (line_num, name, rtype) in enumerate(routines):
        # Include preceding comment block
        comment_start = _extract_preceding_comments(lines, line_num)

        # Find end of routine
        end_line = _find_routine_end(lines, line_num, name)

        # Extract chunk text
        chunk_lines = lines[comment_start:end_line + 1]
        chunk_text = '\n'.join(chunk_lines)

        # Parse structured LAPACK header sections from the comment block
        header_metadata = _parse_header_sections(lines, comment_start, line_num)

        # Extract COMMON blocks and INCLUDE references from the routine body
        common_include = _extract_common_and_includes(chunk_text)
        header_metadata.update(common_include)

        chunks.append(CodeChunk(
            text=chunk_text,
            file_path=file_path,
            start_line=comment_start + 1,  # 1-indexed
            end_line=end_line + 1,
            routine_name=name,
            routine_type=rtype,
            language=language,
            metadata=header_metadata,
        ))

    return chunks


def _find_routine_end(lines: list[str], start_line: int, routine_name: str) -> int:
    """Find the END statement for a routine."""
    for i in range(start_line + 1, len(lines)):
        match = END_PATTERN.match(lines[i])
        if match:
            end_name = match.group(1).strip().lower()
            # Match if END has no name or matches our routine
            if not end_name or end_name == routine_name.lower():
                return i
    # If no END found, return last line
    return len(lines) - 1


def _fixed_size_chunks(
    content: str,
    file_path: str,
    language: str,
    max_tokens: int = 800,
    overlap_tokens: int = 200,
) -> list[CodeChunk]:
    """Fallback: split into fixed-size chunks with overlap."""
    lines = content.split('\n')
    chunks = []

    # Approximate: 1 token ~= 4 chars for code
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap_tokens * chars_per_token

    text = content
    start_char = 0
    chunk_idx = 0

    while start_char < len(text):
        end_char = min(start_char + max_chars, len(text))
        chunk_text = text[start_char:end_char]

        # Find line numbers
        start_line = text[:start_char].count('\n') + 1
        end_line = text[:end_char].count('\n') + 1

        file_stem = file_path.split('/')[-1].replace('.', '_')
        chunks.append(CodeChunk(
            text=chunk_text,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            routine_name=f"{file_stem}_chunk_{chunk_idx}",
            routine_type="fragment",
            language=language,
        ))

        if end_char >= len(text):
            break

        start_char = end_char - overlap_chars
        chunk_idx += 1

    return chunks
