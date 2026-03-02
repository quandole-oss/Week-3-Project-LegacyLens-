"""Feature 3: Pattern Detection - Find similar code patterns via embedding similarity."""

import json
from collections.abc import AsyncIterator
from backend.app.retrieval.search import CodeSearcher


async def find_similar_patterns(
    query: str,
    searcher: CodeSearcher,
    top_k: int = 10,
) -> AsyncIterator[str]:
    """Find code patterns similar to the query and group by similarity."""
    results = searcher.search(query, top_k=top_k)

    # Group results by routine type
    groups: dict[str, list] = {}
    for r in results:
        key = r.routine_type
        if key not in groups:
            groups[key] = []
        groups[key].append(r.to_dict())

    # Send grouped patterns
    yield f"data: {json.dumps({'type': 'patterns', 'data': groups})}\n\n"

    # Send individual results with similarity scores
    for i, result in enumerate(results):
        yield f"data: {json.dumps({'type': 'result', 'data': {'index': i, **result.to_dict()}})}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'data': {'total': len(results), 'groups': len(groups)}})}\n\n"
