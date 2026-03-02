# LegacyLens TODO

## Completed

- [x] Project scaffolding (git init, directory structure, .gitignore, .env.example)
- [x] Backend config with pydantic-settings (`backend/app/config.py`)
- [x] File scanner for LAPACK SRC/ and BLAS/SRC/ (`backend/app/ingestion/scanner.py`)
- [x] Fortran-aware chunker with routine boundary splitting (`backend/app/ingestion/chunker.py`)
- [x] Batch embedding generation with retry (`backend/app/ingestion/embedder.py`)
- [x] Ingestion pipeline orchestrator + Pinecone index creation (`backend/app/ingestion/pipeline.py`)
- [x] CLI ingestion script (`scripts/ingest.py`)
- [x] Pinecone similarity search (`backend/app/retrieval/search.py`)
- [x] Context assembly with metadata headers (`backend/app/retrieval/context.py`)
- [x] LCEL chains with streaming for answer generation (`backend/app/generation/llm.py`)
- [x] Prompt templates: query, explain, docgen, business logic (`backend/app/generation/prompts.py`)
- [x] Feature: Code Explanation (`backend/app/features/explain.py`)
- [x] Feature: Documentation Generation (`backend/app/features/docgen.py`)
- [x] Feature: Pattern Detection (`backend/app/features/patterns.py`)
- [x] Feature: Dependency Mapping (`backend/app/features/dependencies.py`)
- [x] Feature: Business Logic Extraction (`backend/app/features/business.py`)
- [x] FastAPI app with 8 endpoints, CORS, SSE streaming (`backend/app/main.py`)
- [x] Dockerfile for Railway deployment (`backend/Dockerfile`)
- [x] React frontend with Vite + TypeScript + Tailwind (`frontend/`)
- [x] 7-tab UI: Ask, Search, Explain, Docs, Deps, Patterns, Logic
- [x] Streaming response display with live token rendering
- [x] Fortran syntax highlighting via react-syntax-highlighter
- [x] Source cards with file paths, line numbers, relevance scores
- [x] Example query buttons for quick exploration
- [x] Pre-search methodology document (`docs/pre-search.md`)
- [x] Architecture document (`docs/architecture.md`)
- [x] Cost analysis document (`docs/cost-analysis.md`)
- [x] README with setup guide and API reference

## Bug Fixes (v0.2.0)

- [x] Register Fortran language in AnswerPanel for markdown code blocks
- [x] Handle remaining SSE buffer after stream ends in `api.ts`
- [x] Fix Dockerfile for root-context builds (monorepo-compatible)
- [x] Add `.dockerignore` to exclude frontend, data, .git, .env

## Phase 2: Refinement (v0.2.0)

- [x] Claude Haiku re-ranking (`backend/app/retrieval/reranker.py`)
- [x] Parse LAPACK structured headers (PURPOSE, ARGUMENTS, FURTHER DETAILS sections)
- [x] Frontend: loading skeleton states
- [x] Frontend: responsive design polish (flex-wrap tabs, mobile padding)
- [x] Add `use_reranker` toggle in config

## Testing (v0.2.0)

- [x] Backend: pytest + pytest-asyncio + httpx setup (`backend/requirements.txt`, `backend/pytest.ini`)
- [x] Backend: test_chunker.py — 18 tests (routine detection, header parsing, comment extraction)
- [x] Backend: test_config.py — 5 tests (defaults, env overrides, reranker toggle)
- [x] Backend: test_context.py — 9 tests (assembly, formatting, dedup, truncation)
- [x] Backend: test_reranker.py — 9 tests (scoring, clamping, normalization, failure handling)
- [x] Backend: test_api.py — 6 tests (health, search, query streaming + non-streaming)
- [x] Frontend: vitest + @testing-library/react + jsdom setup (`vitest.config.ts`)
- [x] Frontend: api.test.ts — 6 tests (SSE stream, chunked reads, buffer flush, error cases)
- [x] Frontend: AnswerPanel.test.tsx — 6 tests (empty state, markdown, streaming indicator)
- [x] Frontend: Skeleton.test.tsx — 6 tests (card count, animation classes)
- [x] Frontend: TabBar.test.tsx — 5 tests (tabs, active state, click, responsive)
- [x] Add `from __future__ import annotations` for Python 3.9 compatibility
- [x] Fix anthropic version conflict (>=0.41.0 for langchain-anthropic 0.3.1 compat)

## Pipeline Metadata (v0.3.0)

- [x] Upsert parsed metadata (purpose, arguments, common_blocks, includes) to Pinecone vectors

## Phase 2: Remaining (v0.3.0) — Completed

- [x] Hierarchical chunking: file-level summary chunks + routine-level chunks (`create_file_summary_chunk`)
- [x] Handle COMMON blocks and INCLUDE references in chunker (`COMMON_PATTERN`, `INCLUDE_PATTERN`)
- [x] Query expansion via LLM (`backend/app/retrieval/query_expansion.py`)
- [x] Intent detection with keyword heuristics + LLM fallback (`backend/app/retrieval/intent.py`)
- [x] Frontend: click-to-expand full file context (`/api/file-context` + SourceCard toggle)

## Phase 3: Performance & Observability (v0.3.0) — Completed

- [x] Cache repeated query embeddings (`EmbeddingCache` LRU in `search.py`)
- [x] Log latency and token usage per query (middleware + `llm.py` timing)
- [x] Smart query routing via `/api/smart-query` endpoint

## Additional Tests (v0.3.0)

- [x] Backend: test_query_expansion.py — 3 tests (expansion, error fallback, no-key fallback)
- [x] Backend: test_intent.py — 10 tests (keyword detection for 6 intents, LLM fallback, error cases)
- [x] Backend: test_embedding_cache.py — 7 tests (miss, hit, eviction, LRU refresh, stats)
- [x] Backend: test_chunker.py additions — 10 tests (COMMON/INCLUDE patterns, file summary chunks)
- [x] Total: 90 backend tests, 23 frontend tests (113 total)

## Test Coverage Sprint (v0.3.1)

- [x] Backend: test_scanner.py — 12 tests (detect_language, count_lines, scan_directory, SourceFile fields)
- [x] Backend: test_embedder.py — 8 tests (get_embeddings_model, batch embedding, retry, backoff)
- [x] Backend: test_pipeline.py — 10 tests (read_file_content, chunk_all_files, upsert batching, create_pinecone_index, run_ingestion)
- [x] Backend: test_dependencies.py — 10 tests (CALL/EXTERNAL patterns, extract_dependencies, map_dependencies)
- [x] Backend: test_features.py — 12 tests (explain, docgen, patterns, business streaming)
- [x] Backend: test_llm.py — 8 tests (get_llm, chains, stream_query_response, generate_answer, explain_code, generate_docs)
- [x] Backend: test_search_result.py — 6 tests (SearchResult.to_dict, CodeSearcher init/embed/search)
- [x] Backend: test_api.py expanded — 15 new tests (stats, file-context, smart-query, feature endpoints, reranker, expansion)
- [x] Frontend: QueryInput.test.tsx — 9 tests (render, submit, examples, loading, placeholder)
- [x] Frontend: SourceCard.test.tsx — 10 tests (badges, expand/collapse, context loading, error handling)
- [x] Frontend: Header.test.tsx — 5 tests (title, stats fetch, error handling)
- [x] Frontend: api.test.ts expanded — 6 new tests (searchCode, getStats, getFileContext)
- [x] Total: 171 backend + 53 frontend = 224 tests (up from 113)

## CI & Deployment Prep (v0.3.2)

- [x] GitHub Actions CI workflow (`.github/workflows/ci.yml`) — backend pytest + frontend vitest + build on push/PR
- [x] Frontend: App.test.tsx — 11 tests (render, tab switching, streaming query, search, errors, state clearing)
- [x] Vercel deployment config (`frontend/vercel.json`) — SPA routing, Vite framework
- [x] Total: 171 backend + 64 frontend = 235 tests

## Remaining (Requires User Action)

- [ ] Clone LAPACK data and run ingestion pipeline
- [ ] Set up .env with real API keys and verify end-to-end locally
- [ ] Test all 6 query scenarios from the PDF specification
- [ ] Measure precision@5 (target >70%)
- [ ] Document failure modes with real examples
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel (set VITE_API_URL)
- [ ] Add CORS origin for Vercel domain in config
- [ ] Health check endpoint verification on deployed backend
- [ ] End-to-end test: deployed frontend -> Railway -> Pinecone -> streamed response
- [ ] Record demo video (3-5 min)
- [ ] Social post on X or LinkedIn tagging @GauntletAI
