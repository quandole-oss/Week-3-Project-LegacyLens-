# LegacyLens Pre-Search Methodology

Completed before writing any code, as required by the project specification.

## 1. Problem Definition
**What problem does LegacyLens solve?**
Understanding legacy Fortran codebases (specifically LAPACK) is extremely difficult for modern developers. The code uses outdated conventions (fixed-form Fortran 77, implicit typing, cryptic 6-character naming) and lacks modern documentation tooling. LegacyLens uses RAG to make this code searchable and explainable in natural language.

## 2. Target Codebase Selection
**Why LAPACK?**
- 200K+ lines of Fortran code (substantial but bounded)
- Well-structured with consistent conventions (routine-level comments, standardized headers)
- Actively used in production (NumPy, MATLAB, R all depend on it)
- Clear subroutine boundaries make chunking straightforward
- Rich mathematical context for business logic extraction

## 3. Vector Database Selection
**Choice: Pinecone (Serverless)**
- **Pros**: Fully managed, free tier (sufficient for ~2K vectors), zero operational overhead, serverless scales automatically, simple API
- **Alternatives considered**:
  - ChromaDB: Good for local dev but requires hosting for deployment
  - Weaviate: More features than needed, heavier operational burden
  - pgvector: Requires Postgres hosting, more setup
- **Decision rationale**: Fastest path to deployed MVP with zero infrastructure management

## 4. Embedding Model Selection
**Choice: OpenAI text-embedding-3-small (1536 dimensions)**
- **Pros**: Best cost/quality ratio for code, 1536 dims balances expressiveness vs storage, battle-tested on code corpora
- **Alternatives considered**:
  - text-embedding-3-large: Higher quality but 3072 dims = 2x storage cost, marginal improvement
  - Cohere embed-v3: Competitive but adds another API dependency
  - Local models (e5-large): Requires GPU hosting, adds latency
- **Decision rationale**: OpenAI embeddings are the industry standard, well-integrated with LangChain, and cost-effective at ~$0.02/1M tokens

## 5. Chunking Strategy
**Choice: Fortran routine-boundary splitting**
- Each SUBROUTINE/FUNCTION becomes one chunk, including its preceding comment block
- LAPACK header comments contain PURPOSE, ARGUMENTS, FURTHER DETAILS -- critical for semantic search
- Fallback: 800-token fixed chunks with 200-token overlap for non-routine code
- Metadata per chunk: file_path, routine_name, routine_type, start_line, end_line, language

**Why not token-based chunking?**
- Splitting mid-routine loses context about what the code does
- LAPACK routines are typically 50-300 lines, fitting well in a single chunk
- Header comments are essential context that must stay with the code

## 6. Retrieval Strategy
- Embed user query with same model (text-embedding-3-small)
- Cosine similarity search in Pinecone, top-k=10
- Context assembly: concatenate top-k chunks with metadata separators
- Future: Claude Haiku re-ranking for improved precision

## 7. Generation Model
**Choice: Claude Sonnet for generation, Claude Haiku for lightweight tasks**
- Claude excels at code explanation and has strong Fortran knowledge
- Streaming responses for sub-3s perceived latency
- LCEL chains (not deprecated RetrievalQA)

## 8. Scope Boundaries
**Included**: `SRC/` (core LAPACK), `BLAS/SRC/` (BLAS routines)
**Excluded**: `TESTING/` (test code), `INSTALL/` (build scripts), `CMAKE/` (build system), `LAPACKE/` (C interface), `CBLAS/` (C BLAS interface)
**Rationale**: Focus on the core mathematical library, not build/test infrastructure

## 9. Feature Prioritization
| Priority | Feature | Rationale |
|----------|---------|-----------|
| P0 | Code Explanation | Core value proposition |
| P0 | Documentation Gen | Most immediate developer need |
| P1 | Dependency Mapping | Enables understanding of call chains |
| P1 | Pattern Detection | Helps find similar routines |
| P2 | Business Logic Extraction | Advanced feature for deep understanding |

## 10. Performance Targets
- End-to-end query latency: <3s (with streaming)
- Precision@5: >70% relevant results in top 5
- Embedding ingestion: <10 minutes for full LAPACK

## 11. Cost Projections (Development)
- Embedding generation: ~$0.10 (LAPACK ~500K tokens)
- LLM queries during development: ~$5-10
- Pinecone: Free tier
- Total estimated dev cost: <$15

## 12. Deployment Strategy
- Backend: Railway (Dockerfile, env vars via dashboard)
- Frontend: Vercel (automatic from git push)
- Ingestion: Run locally before deploy, Pinecone persists in cloud
- No server-side data storage needed (stateless backend)

## 13. Risk Assessment
| Risk | Mitigation |
|------|------------|
| Pinecone free tier limits | ~2K vectors is sufficient for LAPACK SRC + BLAS/SRC |
| LLM hallucinations | Strict prompt: "only use provided context" |
| Fortran parsing edge cases | Fallback to fixed-size chunks |
| Slow response times | Streaming responses, embedding cache |

## 14. Testing Strategy
- 6 test queries from PDF specification
- Manual precision@5 evaluation
- Latency logging per query

## 15. Documentation Plan
- Architecture doc (architecture.md)
- Cost analysis (cost-analysis.md)
- This pre-search document
- README with setup and deployment guide

## 16. Success Criteria
- [ ] All 6 test queries return relevant, cited answers
- [ ] 4+ code understanding features working
- [ ] Deployed and accessible via public URL
- [ ] <3s perceived latency with streaming
- [ ] Architecture doc explains RAG pipeline decisions
