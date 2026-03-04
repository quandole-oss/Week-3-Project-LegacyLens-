"""FastAPI application for LegacyLens."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pinecone import Pinecone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

from backend.app.config import get_settings, Verbosity, VERBOSITY_PROFILES
from backend.app.retrieval.search import CodeSearcher
from backend.app.retrieval.reranker import rerank_results
from backend.app.retrieval.query_expansion import expand_query
from backend.app.retrieval.intent import detect_intent
from backend.app.generation.llm import stream_query_response, generate_answer
from backend.app.features.explain import stream_explanation
from backend.app.features.docgen import stream_documentation
from backend.app.features.patterns import find_similar_patterns
from backend.app.features.dependencies import map_dependencies
from backend.app.features.business import stream_business_logic

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the searcher on startup and optionally keep the container warm."""
    get_searcher()
    logger.info("Searcher pre-warmed")

    async def _keep_alive():
        while True:
            await asyncio.sleep(300)
            get_searcher()
            logger.info("Keep-alive: searcher warm")

    task = asyncio.create_task(_keep_alive())
    yield
    task.cancel()


app = FastAPI(
    title="LegacyLens",
    description="RAG-powered legacy code understanding for LAPACK",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log request path and total latency for /api/ endpoints."""
    if request.url.path.startswith("/api/"):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} completed in {elapsed_ms:.0f}ms")
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.0f}"
        return response
    return await call_next(request)


# Lazy-initialized searcher
_searcher: CodeSearcher | None = None


def get_searcher() -> CodeSearcher:
    global _searcher
    if _searcher is None:
        _searcher = CodeSearcher()
    return _searcher


# --- Request Models ---

class QueryRequest(BaseModel):
    question: str
    top_k: int = 10
    stream: bool = True
    verbosity: str = "regular"


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class FeatureRequest(BaseModel):
    query: str
    top_k: int = 5


def resolve_profile(verbosity_str: str):
    """Resolve a verbosity string to a VerbosityProfile."""
    try:
        level = Verbosity(verbosity_str.lower())
    except ValueError:
        level = Verbosity.REGULAR
    return VERBOSITY_PROFILES[level]


# --- Routes ---

@app.get("/")
async def root():
    return {"message": "LegacyLens API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/query")
async def query_code(request: QueryRequest):
    """Ask a question about the LAPACK codebase. Supports streaming."""
    searcher = get_searcher()
    profile = resolve_profile(request.verbosity)

    # Optionally expand the query with Fortran-specific terms
    search_query = request.question
    if profile.use_query_expansion:
        search_query = expand_query(request.question)

    # Optionally re-rank results with Claude Haiku for higher quality
    prefetched = None
    if profile.use_reranker:
        raw_results = searcher.search(
            search_query, top_k=profile.reranker_initial_top_k
        )
        prefetched = await rerank_results(
            request.question, raw_results, final_top_k=profile.reranker_final_top_k
        )

    if request.stream:
        return StreamingResponse(
            stream_query_response(
                request.question, searcher, request.top_k,
                prefetched_results=prefetched,
                profile=profile,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        result = await generate_answer(
            request.question, searcher, request.top_k,
            prefetched_results=prefetched,
            profile=profile,
        )
        return result


@app.post("/api/smart-query")
async def smart_query(request: QueryRequest):
    """Auto-detect intent and route to the best handler."""
    searcher = get_searcher()
    profile = resolve_profile(request.verbosity)

    detected_intent = "query"
    if settings.use_intent_detection:
        detected_intent = detect_intent(request.question)

    # Map intents to their streaming handlers
    intent_handlers = {
        "explain": lambda: stream_explanation(request.question, searcher, request.top_k),
        "docgen": lambda: stream_documentation(request.question, searcher, request.top_k),
        "dependencies": lambda: map_dependencies(request.question, searcher, request.top_k),
        "patterns": lambda: find_similar_patterns(request.question, searcher, request.top_k),
        "business": lambda: stream_business_logic(request.question, searcher, request.top_k),
    }

    if detected_intent == "search":
        search_query = request.question
        if profile.use_query_expansion:
            search_query = expand_query(request.question)
        results = searcher.search(search_query, top_k=request.top_k)
        return {
            "intent": detected_intent,
            "query": request.question,
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

    if detected_intent in intent_handlers:
        return StreamingResponse(
            intent_handlers[detected_intent](),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Default: use the standard query pipeline with profile-driven settings
    search_query = request.question
    if profile.use_query_expansion:
        search_query = expand_query(request.question)
    prefetched = None
    if profile.use_reranker:
        raw_results = searcher.search(search_query, top_k=profile.reranker_initial_top_k)
        prefetched = await rerank_results(
            request.question, raw_results, final_top_k=profile.reranker_final_top_k
        )
    return StreamingResponse(
        stream_query_response(
            request.question, searcher, request.top_k,
            prefetched_results=prefetched,
            profile=profile,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/search")
async def search_code(request: SearchRequest):
    """Search for relevant code chunks without LLM generation."""
    searcher = get_searcher()
    search_query = request.query
    if settings.use_query_expansion:
        search_query = expand_query(request.query)
    results = searcher.search(search_query, top_k=request.top_k)
    return {
        "query": request.query,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }


class FileContextRequest(BaseModel):
    file_path: str
    start_line: int = 1
    end_line: int = 0  # 0 = to end of file
    context_lines: int = 50  # Extra lines above/below


@app.post("/api/file-context")
async def file_context(request: FileContextRequest):
    """Get expanded file context around a code region."""
    import os
    data_dir = settings.lapack_data_dir
    full_path = os.path.join(data_dir, request.file_path)

    # Security: prevent path traversal
    resolved = os.path.realpath(full_path)
    base_resolved = os.path.realpath(data_dir)
    if not resolved.startswith(base_resolved):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))

    total_lines = len(lines)
    start = max(1, request.start_line - request.context_lines)
    end = request.end_line if request.end_line > 0 else request.start_line
    end = min(total_lines, end + request.context_lines)

    selected = lines[start - 1:end]
    return {
        "file_path": request.file_path,
        "start_line": start,
        "end_line": end,
        "total_lines": total_lines,
        "content": "".join(selected),
    }


@app.get("/api/stats")
async def get_stats():
    """Get index statistics."""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index)
        stats = index.describe_index_stats()
        return {
            "index_name": settings.pinecone_index,
            "total_vectors": stats.total_vector_count,
            "dimensions": stats.dimension,
            "namespaces": dict(stats.namespaces) if stats.namespaces else {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Feature Routes ---

@app.post("/api/explain")
async def explain(request: FeatureRequest):
    """Explain a Fortran routine in plain English."""
    searcher = get_searcher()
    return StreamingResponse(
        stream_explanation(request.query, searcher, request.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/docgen")
async def docgen(request: FeatureRequest):
    """Generate documentation for a Fortran routine."""
    searcher = get_searcher()
    return StreamingResponse(
        stream_documentation(request.query, searcher, request.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/patterns")
async def patterns(request: FeatureRequest):
    """Find similar code patterns."""
    searcher = get_searcher()
    return StreamingResponse(
        find_similar_patterns(request.query, searcher, request.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/dependencies")
async def dependencies(request: FeatureRequest):
    """Map dependencies for a routine."""
    searcher = get_searcher()
    return StreamingResponse(
        map_dependencies(request.query, searcher, request.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/business-logic")
async def business_logic(request: FeatureRequest):
    """Extract business logic / mathematical algorithm."""
    searcher = get_searcher()
    return StreamingResponse(
        stream_business_logic(request.query, searcher, request.top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
