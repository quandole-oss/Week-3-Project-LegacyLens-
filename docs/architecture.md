# LegacyLens Architecture

## Overview

LegacyLens is a RAG (Retrieval-Augmented Generation) system that helps developers understand the LAPACK legacy Fortran codebase. It combines vector similarity search with LLM-powered code explanation to make legacy code accessible.

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   React UI  │────▶│  FastAPI     │────▶│   Pinecone   │
│   (Vercel)  │◀────│  (Railway)   │◀────│  Vector DB   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Claude LLM  │
                    │  (Anthropic) │
                    └──────────────┘
```

### Data Flow

1. **Ingestion (offline, one-time)**:
   - Scanner discovers Fortran files in LAPACK `SRC/` and `BLAS/SRC/`
   - Chunker splits files at SUBROUTINE/FUNCTION boundaries
   - Embedder generates vectors via OpenAI text-embedding-3-small
   - Pipeline upserts vectors + metadata to Pinecone

2. **Query (real-time)**:
   - User submits natural language question
   - Query is embedded with same model
   - Pinecone returns top-k similar chunks
   - Context assembled with metadata headers
   - Claude generates streamed answer citing sources

## Component Details

### Ingestion Pipeline

| Component | File | Purpose |
|-----------|------|---------|
| Scanner | `backend/app/ingestion/scanner.py` | Discover `.f` and `.f90` files in LAPACK |
| Chunker | `backend/app/ingestion/chunker.py` | Split at routine boundaries with header comments |
| Embedder | `backend/app/ingestion/embedder.py` | Batch embed with exponential backoff |
| Pipeline | `backend/app/ingestion/pipeline.py` | Orchestrate scan → chunk → embed → store |

### Retrieval

| Component | File | Purpose |
|-----------|------|---------|
| Search | `backend/app/retrieval/search.py` | Embed query, search Pinecone, return ranked results |
| Re-Ranker | `backend/app/retrieval/reranker.py` | Score chunks with Claude Haiku for relevance, return top-k |
| Context | `backend/app/retrieval/context.py` | Assemble chunks into LLM context with citations |

### Generation

| Component | File | Purpose |
|-----------|------|---------|
| LLM | `backend/app/generation/llm.py` | LCEL chains with streaming for answer generation |
| Prompts | `backend/app/generation/prompts.py` | System and task-specific prompt templates |

### Code Understanding Features

| # | Feature | File | Description |
|---|---------|------|-------------|
| 1 | Code Explanation | `features/explain.py` | Plain English explanation of routines |
| 2 | Documentation Gen | `features/docgen.py` | Generate parameter docs and usage examples |
| 3 | Pattern Detection | `features/patterns.py` | Find similar code via embedding similarity |
| 4 | Dependency Mapping | `features/dependencies.py` | Parse CALL/EXTERNAL for call graphs |
| 5 | Business Logic | `features/business.py` | Extract mathematical algorithms |

## Key Design Decisions

### Vector Database: Pinecone Serverless
- **Why**: Zero operational overhead, free tier sufficient for LAPACK (~1500 routines), managed scaling
- **Trade-off**: Vendor lock-in, but migration to any vector DB is straightforward (just re-embed and re-upsert)

### Embedding: OpenAI text-embedding-3-small (1536 dims)
- **Why**: Best cost/quality ratio, native LangChain support, proven on code
- **Trade-off**: Requires API call per query (~50ms added latency)

### Chunking: Routine-Boundary Splitting
- **Why**: LAPACK has clean SUBROUTINE/FUNCTION boundaries; header comments contain critical context (PURPOSE, ARGUMENTS sections)
- **Trade-off**: Some routines are very long (500+ lines); addressed by ensuring embedding captures the header + key algorithm sections
- **Fallback**: 800-token fixed chunks with 200-token overlap for non-routine files

### Generation: Claude Sonnet via LCEL
- **Why**: Superior code explanation quality, strong Fortran knowledge, streaming support
- **Trade-off**: Higher cost than GPT-3.5, but quality justifies it for a code understanding tool
- **Chain**: Uses LangChain Expression Language (LCEL) -- `prompt | llm | parser` -- not deprecated `RetrievalQA`

### Streaming
- **Why**: Sub-3s perceived latency even for complex explanations. Sources are sent first, then tokens stream in.
- **Implementation**: Server-Sent Events (SSE) via FastAPI `StreamingResponse`

### Re-Ranking: Claude Haiku

- **Why**: Raw Pinecone cosine similarity misses semantic nuances (e.g., returns `DGETRS` when user asks about `DGESV`'s purpose). LLM-based re-ranking improves precision@5 by scoring each chunk for query relevance.
- **How**: Fetch top-20 from Pinecone, score each with Claude Haiku (0-10 relevance), return top-5.
- **Trade-off**: Adds ~1-2s latency and ~$0.001 per query. Controlled by `USE_RERANKER` env var (default: on).

## Testing

### Backend (pytest, 60 tests)

| Suite | Coverage |
|-------|----------|
| `test_chunker.py` | Routine detection regex, header parsing (single/double `*`), comment extraction, fixed-size fallback, chunk ID format |
| `test_config.py` | Default settings, env overrides, reranker toggle |
| `test_context.py` | Context assembly with metadata headers, source deduplication, snippet truncation |
| `test_reranker.py` | Haiku scoring (mocked), score clamping 0-10, normalization to 0-1, failure fallback to mid-range |
| `test_api.py` | Health endpoint, search endpoint, query (streaming SSE + non-streaming JSON) |

All external APIs (Pinecone, Anthropic, OpenAI) are mocked in tests — no API keys required to run the suite.

### Frontend (vitest, 23 tests)

| Suite | Coverage |
|-------|----------|
| `api.test.ts` | SSE stream parsing, chunked reads, remaining buffer flush, malformed event skip, error responses |
| `AnswerPanel.test.tsx` | Empty state, markdown rendering, streaming indicator toggle |
| `Skeleton.test.tsx` | Skeleton card count, animation classes |
| `TabBar.test.tsx` | 7-tab rendering, active highlight, click callbacks, `flex-wrap` responsive class |

## Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Pinecone unavailable | No search results | Return error, suggest retry |
| LLM timeout | No generated answer | Return raw search results as fallback |
| Irrelevant results | Bad answers | Prompt says "only use provided context", user sees relevance scores |
| Embedding API down | No query embedding | Exponential backoff, error message |
| Fortran parsing failure | Missing chunks | Fallback to fixed-size chunking |

## Performance

- **Target latency**: <3s end-to-end with streaming
  - Embedding: ~100ms
  - Pinecone search: ~100ms
  - First token from LLM: ~500ms
  - Full response stream: 2-5s
- **Precision@5**: Target >70% relevant results in top 5
