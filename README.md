# LegacyLens

RAG-powered legacy code understanding for LAPACK (Linear Algebra PACKage).

LegacyLens uses Retrieval-Augmented Generation to help developers understand, search, and document legacy Fortran codebases. It combines vector similarity search with LLM-powered explanation to make 200K+ lines of Fortran code accessible through natural language.

## Features

1. **Code Search** -- Natural language search across LAPACK routines
2. **Code Explanation** -- Plain English explanations of Fortran routines
3. **Documentation Generation** -- Auto-generate parameter docs and usage examples
4. **Dependency Mapping** -- Visualize CALL/EXTERNAL dependency graphs
5. **Pattern Detection** -- Find similar code patterns via embedding similarity
6. **Business Logic Extraction** -- Extract mathematical algorithms from routines

## Tech Stack

- **Backend**: Python, FastAPI, LangChain (LCEL), Pinecone, OpenAI Embeddings
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **LLM**: Claude Sonnet (Anthropic) for generation
- **Deployment**: Railway (backend) + Vercel (frontend)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- API keys: OpenAI, Anthropic, Pinecone

### Setup

```bash
# Clone and enter project
git clone <repo-url>
cd LegacyLens

# Create .env from example
cp .env.example .env
# Edit .env with your API keys

# Clone LAPACK source data
git clone https://github.com/Reference-LAPACK/lapack.git data/lapack

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run ingestion (one-time, populates Pinecone)
cd ..
python -m scripts.ingest

# Start backend
uvicorn backend.app.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX` | Pinecone index name (default: `legacylens`) |
| `VITE_API_URL` | Backend URL for frontend (default: `http://localhost:8000`) |

## Testing

### Backend (pytest)

```bash
# From project root with venv activated:
PYTHONPATH=. python -m pytest backend/tests/ -v
```

**Test suites** (60 tests):
- `test_chunker.py` -- Fortran chunking, routine detection, header parsing, comment extraction
- `test_config.py` -- Settings defaults, env overrides, reranker toggle
- `test_context.py` -- Context assembly, source formatting, deduplication, truncation
- `test_reranker.py` -- Haiku scoring, score clamping, normalization, failure handling
- `test_api.py` -- Health, search, query (streaming + non-streaming) endpoints

### Frontend (vitest)

```bash
cd frontend
npm test          # single run
npm run test:watch  # watch mode
```

**Test suites** (23 tests):
- `api.test.ts` -- SSE streaming, chunked reads, buffer flush, error handling
- `AnswerPanel.test.tsx` -- Rendering, markdown, streaming indicator
- `Skeleton.test.tsx` -- Loading skeleton cards, animation classes
- `TabBar.test.tsx` -- Tab rendering, active state, click handling, responsive layout

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

```
User → React UI → FastAPI → Pinecone (search) → Claude (generate) → Streamed Response
```

## Documentation

- [Architecture](docs/architecture.md) -- RAG pipeline design and decisions
- [Pre-Search](docs/pre-search.md) -- Pre-search methodology checklist
- [Cost Analysis](docs/cost-analysis.md) -- Development and scaling cost projections

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query` | Ask a question (streaming) |
| POST | `/api/search` | Search code chunks |
| GET | `/api/stats` | Index statistics |
| POST | `/api/explain` | Explain a routine |
| POST | `/api/docgen` | Generate documentation |
| POST | `/api/dependencies` | Map dependencies |
| POST | `/api/patterns` | Find similar patterns |
| POST | `/api/business-logic` | Extract business logic |
