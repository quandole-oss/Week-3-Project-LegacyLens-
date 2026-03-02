# LegacyLens Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [0.3.1] - 2026-03-02

Comprehensive test coverage sprint — nearly doubled total test count.

### Tests Added

- **test_scanner.py** (NEW, 12 tests): `detect_language` for all extensions, `count_lines` edge cases (empty, nonexistent), `scan_directory` with temp dirs (Fortran discovery, non-Fortran exclusion, TESTING dir filtering, BLAS/SRC scanning, sorted output, SourceFile field validation)
- **test_embedder.py** (NEW, 8 tests): `get_embeddings_model` config wiring, `embed_chunks` single/multi-batch, retry on failure, max_retries exhaustion, empty chunks, exponential backoff timing verification
- **test_pipeline.py** (NEW, 10 tests): `read_file_content` UTF-8 and latin-1 fallback, `chunk_all_files` routine + summary chunks, `upsert_to_pinecone` metadata truncation (40K text, 1K fields), batch sizing (250→3 calls), `create_pinecone_index` create/skip logic, `run_ingestion` full orchestration
- **test_dependencies.py** (NEW, 10 tests): `CALL_PATTERN` and `EXTERNAL_PATTERN` regex matching, `extract_dependencies` from DGESV sample (sorted, uppercased), empty code, case insensitivity, `map_dependencies` SSE event sequence, error on no results, graph key validation
- **test_features.py** (NEW, 12 tests): `stream_explanation` sources/tokens/done sequence, source count limit (≤5), required fields validation; `stream_documentation` and `stream_business_logic` SSE events; `find_similar_patterns` grouping by routine_type, results/done events, totals, empty results
- **test_llm.py** (NEW, 8 tests): `get_llm` ChatAnthropic config, `get_query_chain` returns runnable, `stream_query_response` with/without prefetched results, `generate_answer` dict structure, `explain_code` and `generate_docs` token streaming
- **test_search_result.py** (NEW, 6 tests): `SearchResult.to_dict` all fields + score rounding, `CodeSearcher.__init__` wiring, `_embed_query` cache miss/hit behavior, `search` Pinecone response parsing
- **test_api.py** (EXPANDED, +15 tests): `/api/stats` mocked Pinecone stats, `/api/file-context` valid/404/traversal-blocked, `/api/smart-query` explain→SSE and search→JSON routing, `/api/explain`, `/api/docgen`, `/api/patterns`, `/api/dependencies`, `/api/business-logic` SSE responses, `/api/query` with reranker and query expansion
- **QueryInput.test.tsx** (NEW, 9 tests): render, disabled states, form submission with trimming, example buttons, loading state, custom placeholder
- **SourceCard.test.tsx** (NEW, 10 tests): score badge colors (green/yellow/gray), expand/collapse toggle, syntax highlighting, context loading, error display, snippet toggle
- **Header.test.tsx** (NEW, 5 tests): title/badge render, stats fetch on mount, formatted vector count, rejection handling
- **api.test.ts** (EXPANDED, +6 tests): `searchCode` POST/error, `getStats` GET/error, `getFileContext` params/defaults

**Total test count**: 171 backend + 53 frontend = **224 tests** (up from 113)

---

## [0.3.0] - 2026-03-02

Phase 2 completion and Phase 3 performance/observability features.

### Added

- **Hierarchical Chunking** (`backend/app/ingestion/chunker.py`): `create_file_summary_chunk()` generates file-level summary chunks aggregating routine names, types, and purposes for broader retrieval context
- **COMMON/INCLUDE Parsing** (`backend/app/ingestion/chunker.py`): Detects `COMMON /name/` blocks and `INCLUDE 'file'` statements via regex, stores as chunk metadata for dependency-aware retrieval
- **Query Expansion** (`backend/app/retrieval/query_expansion.py`): LLM-powered query augmentation that adds Fortran/LAPACK-specific terms (routine names, mathematical concepts) to improve vector search recall. Falls back gracefully on error or missing API key
- **Intent Detection** (`backend/app/retrieval/intent.py`): Keyword heuristic rules for 6 intent categories (explain, dependencies, docgen, search, patterns, business) with LLM fallback for ambiguous queries. Returns `query` as safe default
- **Smart Query Routing** (`/api/smart-query`): Auto-routes queries to the appropriate feature endpoint based on detected intent
- **File Context Expansion** (`/api/file-context`): Returns surrounding lines for a given file/line range with configurable context window. Includes path traversal security validation
- **Click-to-Expand** (`frontend/src/components/SourceCard.tsx`): "View full context" / "Show snippet" toggle button that fetches and displays surrounding code lines via `/api/file-context`
- **Embedding Cache** (`backend/app/retrieval/search.py`): LRU cache (OrderedDict-based, max 256 entries) for query embeddings. Tracks hit/miss counts. Avoids redundant OpenAI embedding API calls for repeated queries
- **Latency Logging** (`backend/app/main.py`): Request timing middleware adds `X-Response-Time-Ms` header and logs elapsed time per request
- **Token Logging** (`backend/app/generation/llm.py`): Logs token count and generation time per streamed response
- **Pipeline Metadata** (`backend/app/ingestion/pipeline.py`): Upserts parsed metadata fields (purpose, arguments, further_details, common_blocks, includes) to Pinecone vectors for metadata-filtered retrieval
- `use_query_expansion`, `use_intent_detection` settings in `backend/app/config.py`

### Tests Added

- `test_query_expansion.py` — 3 tests (expansion output, error fallback, no-key fallback)
- `test_intent.py` — 10 tests (6 keyword intents, LLM fallback, unknown response, API error, no key)
- `test_embedding_cache.py` — 7 tests (miss, hit, eviction, LRU refresh, stats, duplicate put, default size)
- `test_chunker.py` additions — 10 tests (COMMON/INCLUDE pattern matching, extract function, file summary creation)
- **Total test count**: 90 backend + 23 frontend = 113 tests

---

## [0.2.0] - 2026-03-02

Bug fixes from code review and Phase 2 refinement features.

### Fixed

- **AnswerPanel**: Registered Fortran language with `react-syntax-highlighter` so ` ```fortran ` code blocks in LLM markdown responses render with proper syntax highlighting (previously rendered as plain text)
- **SSE streaming** (`api.ts`): Process remaining buffer content after stream ends — previously, if the final `data:` line arrived without a trailing newline, it was silently discarded
- **Dockerfile**: Changed to root-context build (`COPY backend/requirements.txt`, `COPY backend/`) for monorepo compatibility — previously only worked when build context was `backend/` itself
- Added `.dockerignore` to exclude `frontend/`, `data/`, `node_modules/`, `.git/`, `.env` from Docker build context

### Added

- **Claude Haiku Re-Ranker** (`backend/app/retrieval/reranker.py`): Retrieves top-20 from Pinecone, scores each chunk with `claude-haiku-4-5-20251001` for query relevance (0-10), returns top-5 re-ranked results. Controlled by `use_reranker` setting (default: true)
- **LAPACK Header Parsing** (`backend/app/ingestion/chunker.py`): Parses structured header sections (`Purpose`, `Arguments`, `Further Details`) from LAPACK comment blocks (both `*` and `**` prefix styles) into chunk metadata for richer retrieval
- **Loading Skeletons** (`frontend/src/components/Skeleton.tsx`): Pulsing skeleton cards shown while waiting for streamed response — answer skeleton and source card skeleton
- **Responsive Layout**: Tab bar wraps on small screens (`flex-wrap`), main content uses responsive padding (`px-4 sm:px-6 py-4 sm:py-8`)
- `use_reranker`, `reranker_initial_top_k`, `reranker_final_top_k` settings in `backend/app/config.py`
- **Backend test suite** (60 tests): pytest + pytest-asyncio + httpx — covers chunker, config, context assembly, re-ranker, and API endpoints. All external APIs mocked.
- **Frontend test suite** (23 tests): vitest + @testing-library/react + jsdom — covers SSE streaming logic, AnswerPanel, Skeleton, and TabBar components.
- `from __future__ import annotations` added to backend modules for Python 3.9 compatibility
- Fixed `anthropic` version constraint (`>=0.41.0`) for `langchain-anthropic` 0.3.1 compatibility

---

## [0.1.0] - 2026-03-02

Initial MVP implementation.

### Added

#### Backend
- **Config**: Pydantic-settings based configuration loading from `.env` (`backend/app/config.py`)
- **Scanner**: Recursive file discovery for `.f`/`.f90` in `SRC/` and `BLAS/SRC/`, excludes `TESTING/`, `INSTALL/`, `CMAKE/`, `LAPACKE/`, `CBLAS/` (`backend/app/ingestion/scanner.py`)
- **Chunker**: Fortran-aware splitting on SUBROUTINE/FUNCTION/PROGRAM boundaries with preceding comment block extraction; fallback to 800-token fixed chunks with 200-token overlap (`backend/app/ingestion/chunker.py`)
- **Embedder**: Batch embedding via OpenAI `text-embedding-3-small` (1536 dims) with exponential backoff retry (`backend/app/ingestion/embedder.py`)
- **Pipeline**: Full ingestion orchestrator — scan, chunk, embed, upsert to Pinecone serverless index (`backend/app/ingestion/pipeline.py`)
- **Search**: Embed user query + Pinecone cosine similarity search, top-k configurable (`backend/app/retrieval/search.py`)
- **Context assembly**: Concatenates top-k chunks with metadata separators for LLM input (`backend/app/retrieval/context.py`)
- **LLM generation**: LCEL chains (`prompt | llm | parser`) using Claude Sonnet with streaming via `ChatAnthropic` — replaces deprecated `RetrievalQA` pattern (`backend/app/generation/llm.py`)
- **Prompt templates**: System prompt + task-specific templates for query, explain, docgen, business logic (`backend/app/generation/prompts.py`)
- **Feature — Code Explanation**: Stream plain English explanations of Fortran routines (`backend/app/features/explain.py`)
- **Feature — Documentation Generation**: Stream generated parameter docs and usage examples (`backend/app/features/docgen.py`)
- **Feature — Pattern Detection**: Find similar code via embedding similarity, grouped by routine type (`backend/app/features/patterns.py`)
- **Feature — Dependency Mapping**: Parse CALL/EXTERNAL statements to build call graph (`backend/app/features/dependencies.py`)
- **Feature — Business Logic Extraction**: Stream mathematical algorithm explanations (`backend/app/features/business.py`)
- **FastAPI app**: 8 API endpoints with CORS middleware and SSE streaming (`backend/app/main.py`)
  - `POST /api/query` — streamed Q&A
  - `POST /api/search` — ranked code chunks (no LLM)
  - `GET /api/stats` — Pinecone index stats
  - `POST /api/explain`, `/api/docgen`, `/api/patterns`, `/api/dependencies`, `/api/business-logic`
- **Dockerfile** for Railway deployment (`backend/Dockerfile`)
- **CLI ingestion script** (`scripts/ingest.py`)

#### Frontend
- Vite + React + TypeScript project scaffolding
- Tailwind CSS (via `@tailwindcss/vite` plugin)
- **TabBar**: 7-tab interface — Ask, Search, Explain, Docs, Deps, Patterns, Logic
- **QueryInput**: Text input with submit button + 5 example query buttons
- **AnswerPanel**: Markdown rendering of streamed LLM responses with syntax highlighting
- **SourceCard**: Expandable cards showing file path, line numbers, routine name, relevance score badge, Fortran syntax-highlighted code snippets
- **Header**: App title + live vector count from `/api/stats`
- **Streaming**: SSE consumption with live token-by-token display
- **API client** (`src/api.ts`): Typed fetch + SSE streaming generator

#### Documentation
- `docs/pre-search.md` — 16-point pre-search methodology checklist
- `docs/architecture.md` — RAG pipeline design, component table, design decisions, failure modes, performance targets
- `docs/cost-analysis.md` — Dev cost breakdown + scaling projections for 100–100K users
- `README.md` — Setup guide, environment variables, API reference

### Technical Decisions
- **Pinecone serverless** over ChromaDB/Weaviate: zero ops, free tier sufficient for LAPACK
- **OpenAI text-embedding-3-small** over larger models: best cost/quality at 1536 dims
- **Routine-boundary chunking** over token-based: preserves semantic context of LAPACK header comments
- **LCEL chains** over deprecated `RetrievalQA.from_chain_type()`: follows current LangChain best practices
- **SSE streaming** for all LLM endpoints: sources sent first, then tokens streamed for sub-3s perceived latency
- **Claude Sonnet** for generation: superior Fortran code explanation quality
