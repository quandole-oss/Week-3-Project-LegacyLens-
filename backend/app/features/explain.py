"""Feature 1: Code Explanation - Plain English explanation of Fortran routines."""

import json
from collections.abc import AsyncIterator
from backend.app.retrieval.search import CodeSearcher
from backend.app.retrieval.context import assemble_context
from backend.app.generation.llm import get_explain_chain


async def stream_explanation(
    query: str,
    searcher: CodeSearcher,
    top_k: int = 5,
) -> AsyncIterator[str]:
    """Search for relevant code and stream an explanation."""
    results = searcher.search(query, top_k=top_k)
    context = assemble_context(results, max_chunks=5)

    sources = [
        {
            "file_path": r.file_path,
            "routine_name": r.routine_name,
            "start_line": r.start_line,
            "end_line": r.end_line,
            "score": round(r.score, 4),
        }
        for r in results[:5]
    ]

    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

    chain = get_explain_chain()
    async for chunk in chain.astream({"context": context}):
        yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
