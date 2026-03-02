"""Claude Haiku-based re-ranking for improved retrieval quality."""

from __future__ import annotations

import asyncio
import json
import logging

from anthropic import Anthropic

from backend.app.config import get_settings
from backend.app.retrieval.search import SearchResult

logger = logging.getLogger(__name__)

RERANK_PROMPT = """You are a relevance scoring system. Given a user query about LAPACK/Fortran code and a code chunk, rate the relevance of the chunk to the query on a scale of 0-10.

Scoring guidelines:
- 10: Directly answers the query or contains the exact routine/concept asked about
- 7-9: Highly relevant, contains closely related routines or concepts
- 4-6: Somewhat relevant, shares topic area but not directly answering
- 1-3: Tangentially related
- 0: Completely irrelevant

Respond with ONLY a JSON object: {{"score": <integer 0-10>}}

Query: {query}

Code chunk:
File: {file_path} | Routine: {routine_name} | Type: {routine_type}
{text}"""


def _score_single(client: Anthropic, model: str, query: str, result: SearchResult) -> tuple[SearchResult, int]:
    """Score a single search result using Claude Haiku."""
    prompt = RERANK_PROMPT.format(
        query=query,
        file_path=result.file_path,
        routine_name=result.routine_name,
        routine_type=result.routine_type,
        text=result.text[:2000],  # Limit text length to control costs
    )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=32,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()
        parsed = json.loads(content)
        score = int(parsed.get("score", 0))
        return result, max(0, min(10, score))
    except Exception as e:
        logger.warning(f"Rerank scoring failed for {result.routine_name}: {e}")
        return result, 5  # Default mid-range score on failure


async def rerank_results(
    query: str,
    results: list[SearchResult],
    final_top_k: int = 5,
) -> list[SearchResult]:
    """Re-rank search results using Claude Haiku for relevance scoring.

    Args:
        query: The user's original query.
        results: Initial search results from Pinecone.
        final_top_k: Number of results to return after re-ranking.

    Returns:
        Top-k results sorted by Haiku relevance score.
    """
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    model = settings.rerank_model

    loop = asyncio.get_event_loop()

    # Score all results concurrently using thread pool
    tasks = [
        loop.run_in_executor(None, _score_single, client, model, query, result)
        for result in results
    ]
    scored = await asyncio.gather(*tasks)

    # Sort by Haiku score (descending), break ties with original Pinecone score
    scored.sort(key=lambda pair: (pair[1], pair[0].score), reverse=True)

    # Return top-k with adjusted scores normalized to 0-1 range
    reranked = []
    for result, haiku_score in scored[:final_top_k]:
        result.score = round(haiku_score / 10.0, 4)
        reranked.append(result)

    return reranked
