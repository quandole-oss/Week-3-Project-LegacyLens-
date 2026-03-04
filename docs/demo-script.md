# LegacyLens Demo Script (3-5 minutes)

## Setup
- Open https://legacylens-murex.vercel.app/ in browser
- Have this script visible on a second monitor or printed
- Start screen recording with audio (QuickTime/OBS/Loom)

---

## [0:00 - 0:15] Introduction
**Say:** "This is LegacyLens, a RAG-powered code understanding tool for legacy Fortran codebases. It's built to help developers understand LAPACK — over 200,000 lines of numerical linear algebra code written in Fortran."

**Show:** The landing page with all 7 tabs visible.

---

## [0:15 - 0:45] Ask Tab
**Say:** "The Ask tab lets you ask natural language questions about the codebase. Let me ask: 'What does DGESV do?'"

**Do:** Type "What does DGESV do?" and submit.

**Show:** Streaming tokens appearing in real-time, then the source cards at the bottom with file paths and relevance scores.

**Say:** "You can see the answer streams in real-time from Claude, with citations to the actual Fortran source files."

---

## [0:45 - 1:15] Search Tab
**Say:** "The Search tab does semantic search across all 2,306 LAPACK source files."

**Do:** Click Search tab, type "eigenvalue decomposition", submit.

**Show:** Ranked results with routine names, file paths, relevance scores.

**Say:** "Each result shows the routine name, a code snippet, and a relevance score from our vector search over 4,620 embeddings."

---

## [1:15 - 1:45] Explain Tab
**Say:** "Explain gives you a detailed walkthrough of any routine."

**Do:** Click Explain tab, type "DGEMM", submit.

**Show:** The streaming explanation with algorithm steps.

**Say:** "DGEMM is the core matrix multiplication routine — the AI explains its purpose, parameters, and algorithm step by step."

---

## [1:45 - 2:15] Docs Tab
**Say:** "The Docs tab generates modern documentation from legacy code."

**Do:** Click Docs tab, type "DGESV", submit.

**Show:** Generated documentation with parameter table.

**Say:** "It extracts all parameters with their types, intent, and descriptions — turning decades-old Fortran headers into readable docs."

---

## [2:15 - 2:45] Deps Tab
**Say:** "Dependencies maps the call chain of any routine."

**Do:** Click Deps tab, type "DGESV subroutine", submit.

**Show:** The dependency analysis results.

**Say:** "You can see DGESV calls DGETRF for LU factorization, DGETRS for the solve step, and XERBLA for error handling."

---

## [2:45 - 3:15] Patterns Tab
**Say:** "Patterns detects common coding patterns across the codebase."

**Do:** Click Patterns tab, type "matrix factorization routines", submit.

**Show:** Grouped pattern results.

**Say:** "It identifies shared patterns — like how all factorization routines follow the same error-checking, workspace-query, and compute structure."

---

## [3:15 - 3:45] Logic Tab
**Say:** "Finally, the Logic tab extracts the core algorithm from any routine."

**Do:** Click Logic tab, type "DPOTRF Cholesky factorization", submit.

**Show:** Business logic extraction results.

**Say:** "It pulls out the mathematical algorithm — here showing Cholesky decomposition's blocked approach with DTRSM and DSYRK calls."

---

## [3:45 - 4:15] Architecture Summary
**Say:** "Under the hood, LegacyLens processes 2,306 Fortran source files into 4,620 vector embeddings stored in Pinecone. The backend is FastAPI with LangChain, the frontend is React with TypeScript, and generation uses Claude. It's deployed on Railway and Vercel."

**Show:** (Optional) Briefly show the GitHub repo or architecture diagram.

---

## RAG Pipeline Deep Dive

### Ingestion Pipeline

The ingestion pipeline transforms raw Fortran source files into searchable vector embeddings. Each stage handles a specific concern:

| Component | What It Does | LegacyLens Implementation |
|---|---|---|
| **File Discovery** | Recursively scan codebase, filter by file extension | Walks the LAPACK source tree, selects `.f`, `.f90` files (2,306 files total) |
| **Preprocessing** | Handle encoding issues, normalize whitespace, extract comments | Strips Fortran fixed-format column artifacts, normalizes line continuations, preserves comment blocks as documentation |
| **Chunking** | Syntax-aware splitting into meaningful units | Function-level chunking using `SUBROUTINE`/`FUNCTION`/`END` boundaries, producing 4,620 chunks from 2,306 files |
| **Metadata Extraction** | Capture file path, line numbers, function names, dependencies | Extracts routine name, file path, parameter lists, and `CALL` dependencies for each chunk |
| **Embedding Generation** | Generate vectors for each chunk | OpenAI `text-embedding-ada-002` encodes each chunk into a 1536-dimensional vector |
| **Storage** | Insert into vector database with metadata | Upserts vectors + metadata into a Pinecone index with cosine similarity |

### Retrieval Pipeline

When a user asks a question, the retrieval pipeline finds relevant code and generates an answer:

| Component | What It Does | LegacyLens Implementation |
|---|---|---|
| **Query Processing** | Parse natural language, extract intent and entities | LangChain parses the user query; tab selection (Ask, Explain, Docs, etc.) determines the prompt template and retrieval strategy |
| **Embedding** | Convert query to vector using same model as ingestion | Same `text-embedding-ada-002` model encodes the query into a 1536-d vector |
| **Similarity Search** | Find top-k most similar chunks | Pinecone returns top-k nearest neighbors (k varies by tab: 5 for Ask, 3 for Explain, 8 for Patterns) |
| **Re-ranking** | Reorder results by relevance score | Pinecone cosine similarity scores are used directly; results below a threshold are filtered out |
| **Context Assembly** | Combine retrieved chunks with surrounding context | Retrieved Fortran source chunks are assembled into a structured context block with file paths and line references |
| **Answer Generation** | LLM generates response using retrieved context | Claude receives the assembled context + a tab-specific system prompt and streams the response back |

### Chunking Strategy

Legacy Fortran code requires specialized chunking. LegacyLens uses a **function-level** strategy as its primary approach:

| Strategy | Use Case | How LegacyLens Uses It |
|---|---|---|
| **Function-level** | Each `SUBROUTINE`/`FUNCTION` as a chunk | **Primary strategy** — Fortran routines are self-contained units with clear `SUBROUTINE name ... END` boundaries |
| **Paragraph-level** | COBOL `PARAGRAPH` as natural boundary | Not applicable (Fortran codebase), but the architecture supports pluggable chunkers for other languages |
| **Fixed-size + overlap** | Fallback for unstructured sections | Used for very large routines (>500 lines) that exceed embedding token limits — splits with 50-line overlap to preserve context |
| **Semantic splitting** | Use LLM to identify logical boundaries | Not used at ingestion time (too expensive at scale), but the Explain/Logic tabs effectively do this at query time |
| **Hierarchical** | Multiple granularities (file → section → function) | File-level metadata is preserved so retrieval can pull in sibling routines from the same file when needed |

Function-level chunking works well for LAPACK because each routine is a well-defined unit (typically 50-300 lines) with a clear name, parameter list, and purpose comment block — making each chunk both semantically coherent and small enough for accurate embedding.

---

## [4:15 - 4:30] Closing
**Say:** "The project has 235 automated tests across backend and frontend, with CI/CD via GitHub Actions. You can try it yourself at legacylens-murex.vercel.app. Built during Gauntlet AI Week 3. Thanks for watching!"

**Show:** The app URL one more time.
