"""Context assembly from search results for LLM generation."""

from __future__ import annotations

from backend.app.retrieval.search import SearchResult


def assemble_context(
    results: list[SearchResult],
    max_chunks: int = 3,
    trim_after_rank: int = 3,
    trim_char_limit: int = 800,
) -> str:
    """Assemble search results into a context string for the LLM.

    Ranks 1 through trim_after_rank get full text.
    Later ranks get header + first trim_char_limit chars + truncation marker.
    """
    context_parts = []

    for i, result in enumerate(results[:max_chunks]):
        header = (
            f"--- Source {i + 1}: {result.file_path} "
            f"(lines {result.start_line}-{result.end_line}) "
            f"[{result.routine_type}: {result.routine_name}] "
            f"(relevance: {result.score:.3f}) ---"
        )
        if i < trim_after_rank:
            context_parts.append(f"{header}\n{result.text}")
        else:
            trimmed = result.text[:trim_char_limit]
            if len(result.text) > trim_char_limit:
                trimmed += "\n... [truncated]"
            context_parts.append(f"{header}\n{trimmed}")

    return "\n\n".join(context_parts)


def format_sources(results: list[SearchResult], max_sources: int = 5) -> list[dict]:
    """Format source references for the API response."""
    sources = []
    seen = set()

    for result in results[:max_sources]:
        key = f"{result.file_path}:{result.routine_name}"
        if key in seen:
            continue
        seen.add(key)

        sources.append({
            "file_path": result.file_path,
            "routine_name": result.routine_name,
            "routine_type": result.routine_type,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "score": round(result.score, 4),
            "snippet": result.text[:500] + ("..." if len(result.text) > 500 else ""),
        })

    return sources
