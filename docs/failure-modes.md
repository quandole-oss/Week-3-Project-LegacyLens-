# LegacyLens Failure Modes

Documented edge cases tested against the live API at `https://week-3-project-legacylens-production.up.railway.app/`.

Last tested: 2026-03-02

---

## 1. Empty Query (POST /api/query)

**Input:** `{"question": "", "stream": false}`
**HTTP Status:** 500
**Observed Behavior:** Unhandled `Internal Server Error` — no structured error response.
**Severity:** HIGH
**Mitigation:** Add `min_length=1` validator on the `question` field in the Pydantic request model, or check for empty input before calling the embedding/LLM pipeline.

---

## 2. Very Long Query (POST /api/query)

**Input:** `{"question": "DGESV " repeated ~500 times (~2500 chars), "stream": false}`
**HTTP Status:** 200
**Observed Behavior:** Processed successfully and returned a valid answer about DGESV.
**Severity:** LOW
**Mitigation:** Add a max query length (e.g., 500 chars) to prevent token cost abuse. Not a crash, but an operational concern.

---

## 3. Missing Required Field (POST /api/query)

**Input:** `{"stream": false}` (missing `question` field)
**HTTP Status:** 422
**Observed Behavior:** Pydantic validation returned a structured error: `{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required"}]}`.
**Severity:** NONE — correct behavior.

---

## 4. Invalid JSON (POST /api/query)

**Input:** `this is not json`
**HTTP Status:** 422
**Observed Behavior:** FastAPI returned a structured error: `{"detail":[{"type":"json_invalid","loc":["body",0],"msg":"JSON decode error"}]}`.
**Severity:** NONE — correct behavior.

---

## 5. Off-Topic Query — Weather (POST /api/query)

**Input:** `{"question": "What is the weather today?", "stream": false}`
**HTTP Status:** 200
**Observed Behavior:** LLM politely declined: "I'm sorry, but I can't answer that question based on the provided source code context." Redirected user to LAPACK topics.
**Severity:** NONE — excellent guardrails.

---

## 6. Off-Topic Query — Chocolate Cake (POST /api/query)

**Input:** `{"question": "recipe for chocolate cake", "stream": false}`
**HTTP Status:** 200
**Observed Behavior:** LLM responded: "I'm sorry, but that question is completely outside my area of expertise. I'm LegacyLens, an assistant specialized in understanding legacy Fortran codebases."
**Severity:** NONE — excellent guardrails.

---

## 7. Typo in Routine Name (POST /api/explain)

**Input:** `{"query": "DGESVV"}` (extra V)
**HTTP Status:** 200
**Observed Behavior:** Vector search found closest matches (dgesvd.f at 0.51, dgesv.f at 0.51) and the LLM explained DGESVD. Did not inform user that "DGESVV" doesn't exist.
**Severity:** LOW
**Mitigation:** Add a fuzzy-match disclaimer: "DGESVV was not found. Showing results for the closest match: DGESVD."

---

## 8. Natural Language Misspellings (POST /api/query)

**Input:** `{"question": "How does linnear algebra work in LAPCK?", "stream": false}`
**HTTP Status:** 200
**Observed Behavior:** Both vector search and LLM understood the intent despite typos ("linnear" → "linear", "LAPCK" → "LAPACK"). Returned a comprehensive, accurate answer.
**Severity:** NONE — excellent resilience.

---

## 9. Stats Endpoint (GET /api/stats)

**Input:** None (GET request)
**HTTP Status:** 500
**Observed Behavior:** Unhandled `Internal Server Error` — no structured error response. Likely caused by attempting to read local filesystem stats or uninitialized counters in the Railway environment.
**Severity:** HIGH
**Mitigation:** Add try/except around stats collection. Return partial stats or a graceful 503 with a message when the underlying data source is unavailable.

---

## 10. File Context on Railway (POST /api/file-context)

**Input:** `{"file_path": "SRC/dgesv.f"}`
**HTTP Status:** 404
**Observed Behavior:** `{"detail":"File not found"}` — correct JSON error. The endpoint reads from the local filesystem, which doesn't have LAPACK source files on Railway.
**Severity:** LOW
**Mitigation:** Document that file-context requires local source files. Consider storing file contents in Pinecone metadata or an object store for production use.

---

## 11. Dependencies Endpoint — Empty Call Chains (POST /api/dependencies)

**Input:** `{"query": "DGESV subroutine call chain"}`
**HTTP Status:** 200
**Observed Behavior:** Returns relevant file-level matches (dgesv.f, dgesvd.f) but the `calls` and `externals` arrays are empty. The dependency graph data has empty adjacency lists. The LLM streams analysis based on retrieved source context, but the structured dependency data is not populated.
**Severity:** MEDIUM
**Mitigation:** The dependency extraction relies on pattern matching in the chunked text. File summary chunks may not contain CALL statements. Consider searching routine-level chunks specifically for dependency queries, or pre-compute a static call graph during ingestion.

---

## Summary

| # | Category | Input | HTTP | Severity | Graceful? |
|---|----------|-------|------|----------|-----------|
| 1 | Malformed | Empty query | 500 | HIGH | No |
| 2 | Malformed | Very long query | 200 | LOW | Yes |
| 3 | Malformed | Missing field | 422 | NONE | Yes |
| 4 | Malformed | Invalid JSON | 422 | NONE | Yes |
| 5 | Off-topic | Weather question | 200 | NONE | Yes |
| 6 | Off-topic | Chocolate cake | 200 | NONE | Yes |
| 7 | Misspelling | DGESVV (typo) | 200 | LOW | Yes |
| 8 | Misspelling | "linnear"/"LAPCK" | 200 | NONE | Yes |
| 9 | System | /api/stats | 500 | HIGH | No |
| 10 | System | File context (no local files) | 404 | LOW | Yes |
| 11 | System | Empty dependency chains | 200 | MEDIUM | Partial |

**Counts:** 2 HIGH, 1 MEDIUM, 3 LOW, 5 NONE (11 total edge cases)
