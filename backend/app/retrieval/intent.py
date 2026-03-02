"""Intent detection for routing queries to the best handler."""

from __future__ import annotations

import logging
import re

from anthropic import Anthropic
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# Intent categories matching the API endpoints
INTENTS = {
    "query": "General question about LAPACK code",
    "search": "Looking for specific code or routines",
    "explain": "Wants explanation of what code does",
    "docgen": "Wants documentation generated",
    "dependencies": "Wants to know what a routine calls or depends on",
    "patterns": "Looking for similar code patterns",
    "business": "Wants mathematical/algorithmic logic extracted",
}

# Fast keyword-based heuristics to avoid LLM call for obvious cases
KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("dependencies", ["depend", "calls", "call graph", "call tree", "external", "imports"]),
    ("explain", ["explain", "what does", "how does", "what is", "describe", "tell me about"]),
    ("docgen", ["document", "docstring", "generate docs", "parameter docs", "usage example"]),
    ("patterns", ["similar", "pattern", "like this", "related routines", "find code"]),
    ("business", ["algorithm", "mathematical", "formula", "equation", "numerical method", "business logic"]),
    ("search", ["find", "search", "where is", "locate", "list", "show me"]),
]

INTENT_PROMPT = """Classify this LAPACK/Fortran query into exactly ONE category.

Categories:
- query: General question about code
- search: Looking for specific routines or code
- explain: Wants plain English explanation
- docgen: Wants documentation generated
- dependencies: Wants call graph or dependency info
- patterns: Looking for similar code patterns
- business: Wants mathematical algorithm explanation

Respond with ONLY the category name (one word).

Query: {query}"""


def detect_intent(query: str) -> str:
    """Detect the user's intent from their query.

    Uses keyword heuristics first, falls back to LLM for ambiguous queries.
    Returns one of: query, search, explain, docgen, dependencies, patterns, business.
    """
    query_lower = query.lower().strip()

    # Fast keyword-based detection
    for intent, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw in query_lower:
                logger.info(f"Intent detected via keyword '{kw}': {intent}")
                return intent

    # Fall back to LLM for ambiguous queries
    settings = get_settings()
    if not settings.anthropic_api_key:
        return "query"  # Default

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.rerank_model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": INTENT_PROMPT.format(query=query),
            }],
        )
        detected = response.content[0].text.strip().lower()
        # Validate it's a known intent
        if detected in INTENTS:
            logger.info(f"Intent detected via LLM: {detected}")
            return detected
        logger.warning(f"LLM returned unknown intent '{detected}', defaulting to 'query'")
        return "query"
    except Exception as e:
        logger.warning(f"Intent detection failed: {e}")
        return "query"
