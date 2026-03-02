"""Query expansion using Claude Haiku to add Fortran-specific terms."""

from __future__ import annotations

import logging
from anthropic import Anthropic
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

EXPANSION_PROMPT = """You are a query expansion system for searching LAPACK (Linear Algebra PACKage) Fortran code.

Given a user query, generate an expanded version that includes:
1. The original query terms
2. Relevant LAPACK routine names (e.g., DGESV, DGETRF, SGEMM)
3. Fortran-specific terminology (e.g., SUBROUTINE, DOUBLE PRECISION)
4. Mathematical terms related to the query

IMPORTANT: Return ONLY the expanded query text, nothing else. Keep it under 100 words.

User query: {query}"""


def expand_query(query: str) -> str:
    """Expand a user query with Fortran/LAPACK-specific terms.

    Uses Claude Haiku for fast, cheap expansion. Falls back to
    the original query on any failure.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        return query

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.rerank_model,  # Haiku — fast and cheap
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": EXPANSION_PROMPT.format(query=query),
            }],
        )
        expanded = response.content[0].text.strip()
        logger.info(f"Query expanded: '{query}' -> '{expanded[:80]}...'")
        return expanded
    except Exception as e:
        logger.warning(f"Query expansion failed, using original: {e}")
        return query
