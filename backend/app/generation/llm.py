"""LLM answer generation using LCEL chains with streaming."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser

from backend.app.config import get_settings, VerbosityProfile
from backend.app.generation.prompts import (
    QUERY_TEMPLATE,
    EXPLAIN_TEMPLATE,
    DOCGEN_TEMPLATE,
    BUSINESS_LOGIC_TEMPLATE,
)
from backend.app.retrieval.search import CodeSearcher, SearchResult
from backend.app.retrieval.context import assemble_context, format_sources


def get_llm(
    streaming: bool = True,
    model_override: str | None = None,
    max_tokens_override: int | None = None,
):
    settings = get_settings()
    return ChatAnthropic(
        model=model_override or settings.generation_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0,
        streaming=streaming,
        max_tokens=max_tokens_override or 2048,
    )


def get_query_chain(
    model_override: str | None = None,
    max_tokens_override: int | None = None,
):
    return QUERY_TEMPLATE | get_llm(
        model_override=model_override,
        max_tokens_override=max_tokens_override,
    ) | StrOutputParser()


def get_explain_chain():
    return EXPLAIN_TEMPLATE | get_llm() | StrOutputParser()


def get_docgen_chain():
    return DOCGEN_TEMPLATE | get_llm() | StrOutputParser()


def get_business_logic_chain():
    return BUSINESS_LOGIC_TEMPLATE | get_llm() | StrOutputParser()


async def stream_query_response(
    question: str,
    searcher: CodeSearcher,
    top_k: int = 10,
    prefetched_results: list[SearchResult] | None = None,
    profile: VerbosityProfile | None = None,
) -> AsyncIterator[str]:
    """Stream an answer to a code question with source references."""
    # Use pre-fetched results (e.g. from reranker) or search directly
    results = prefetched_results if prefetched_results is not None else searcher.search(question, top_k=top_k)

    # Assemble context with profile-driven trimming
    if profile:
        context = assemble_context(
            results,
            max_chunks=profile.max_chunks,
            trim_after_rank=profile.trim_after_rank,
            trim_char_limit=profile.trim_char_limit,
        )
    else:
        context = assemble_context(results)

    sources = format_sources(results)

    # Send sources first as a JSON event
    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

    # Build the question with optional prompt suffix
    effective_question = question
    if profile and profile.prompt_suffix:
        effective_question = f"{question}\n\n{profile.prompt_suffix}"

    # Build chain with profile overrides
    if profile:
        chain = get_query_chain(
            model_override=profile.generation_model,
            max_tokens_override=profile.max_tokens,
        )
    else:
        chain = get_query_chain()

    # Stream the LLM response with timing
    token_count = 0
    t0 = time.perf_counter()
    async for chunk in chain.astream({"context": context, "question": effective_question}):
        token_count += 1
        yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"

    elapsed = time.perf_counter() - t0
    logger.info(
        f"stream_query_response: {token_count} chunks in {elapsed:.2f}s "
        f"({token_count / elapsed:.0f} chunks/s)" if elapsed > 0 else
        f"stream_query_response: {token_count} chunks"
    )
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def generate_answer(
    question: str,
    searcher: CodeSearcher,
    top_k: int = 10,
    prefetched_results: list[SearchResult] | None = None,
    profile: VerbosityProfile | None = None,
) -> dict:
    """Generate a non-streaming answer."""
    results = prefetched_results if prefetched_results is not None else searcher.search(question, top_k=top_k)

    if profile:
        context = assemble_context(
            results,
            max_chunks=profile.max_chunks,
            trim_after_rank=profile.trim_after_rank,
            trim_char_limit=profile.trim_char_limit,
        )
    else:
        context = assemble_context(results)

    sources = format_sources(results)

    effective_question = question
    if profile and profile.prompt_suffix:
        effective_question = f"{question}\n\n{profile.prompt_suffix}"

    if profile:
        chain = get_query_chain(
            model_override=profile.generation_model,
            max_tokens_override=profile.max_tokens,
        )
    else:
        chain = get_query_chain()

    answer = await chain.ainvoke({"context": context, "question": effective_question})

    return {
        "answer": answer,
        "sources": sources,
        "query": question,
    }


async def explain_code(context: str) -> AsyncIterator[str]:
    """Stream an explanation of code."""
    chain = get_explain_chain()
    async for chunk in chain.astream({"context": context}):
        yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def generate_docs(context: str) -> AsyncIterator[str]:
    """Stream generated documentation."""
    chain = get_docgen_chain()
    async for chunk in chain.astream({"context": context}):
        yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def extract_business_logic(context: str) -> AsyncIterator[str]:
    """Stream business logic extraction."""
    chain = get_business_logic_chain()
    async for chunk in chain.astream({"context": context}):
        yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
