"""Feature 4: Dependency Mapping - Parse CALL/EXTERNAL to build call graph."""

import re
import json
from collections.abc import AsyncIterator
from backend.app.retrieval.search import CodeSearcher

# Pattern to match CALL statements
CALL_PATTERN = re.compile(r'\bCALL\s+(\w+)', re.IGNORECASE)

# Pattern to match EXTERNAL declarations
EXTERNAL_PATTERN = re.compile(r'\bEXTERNAL\s+(.+)', re.IGNORECASE)

# Common LAPACK/BLAS function prefixes that indicate function calls
LAPACK_PREFIXES = {'S', 'D', 'C', 'Z', 'DS', 'ZC'}


def extract_dependencies(code: str) -> dict:
    """Extract CALL targets and EXTERNAL declarations from Fortran code."""
    calls = set()
    externals = set()

    for match in CALL_PATTERN.finditer(code):
        calls.add(match.group(1).upper())

    for match in EXTERNAL_PATTERN.finditer(code):
        names = match.group(1).split(',')
        for name in names:
            clean = name.strip().upper()
            if clean:
                externals.add(clean)

    return {
        "calls": sorted(calls),
        "externals": sorted(externals),
    }


async def map_dependencies(
    query: str,
    searcher: CodeSearcher,
    top_k: int = 5,
) -> AsyncIterator[str]:
    """Search for a routine and map its dependencies."""
    results = searcher.search(query, top_k=top_k)

    if not results:
        yield f"data: {json.dumps({'type': 'error', 'data': 'No matching routines found'})}\n\n"
        return

    all_deps = []
    for result in results[:5]:
        deps = extract_dependencies(result.text)
        entry = {
            "routine_name": result.routine_name,
            "file_path": result.file_path,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "calls": deps["calls"],
            "externals": deps["externals"],
            "score": round(result.score, 4),
        }
        all_deps.append(entry)

    # Build a simplified call graph
    graph = {}
    for dep in all_deps:
        graph[dep["routine_name"]] = dep["calls"]

    yield f"data: {json.dumps({'type': 'dependencies', 'data': all_deps})}\n\n"
    yield f"data: {json.dumps({'type': 'graph', 'data': graph})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
