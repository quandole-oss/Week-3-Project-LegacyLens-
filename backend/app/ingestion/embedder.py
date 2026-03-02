"""Embedding generation using OpenAI text-embedding-3-small."""

import time
from langchain_openai import OpenAIEmbeddings
from backend.app.config import get_settings
from backend.app.ingestion.chunker import CodeChunk


def get_embeddings_model() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
        dimensions=settings.embedding_dimensions,
    )


def embed_chunks(
    chunks: list[CodeChunk],
    batch_size: int = 100,
    max_retries: int = 5,
) -> list[tuple[CodeChunk, list[float]]]:
    """Generate embeddings for code chunks with batching and retry."""
    embeddings_model = get_embeddings_model()
    results = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk.embedding_text() for chunk in batch]
        current_batch_size = len(batch)

        for attempt in range(max_retries):
            try:
                vectors = embeddings_model.embed_documents(texts)
                for chunk, vector in zip(batch, vectors):
                    results.append((chunk, vector))
                break
            except Exception as e:
                err_str = str(e)
                # Token limit exceeded — split batch in half and retry
                if "max_tokens_per_request" in err_str and current_batch_size > 1:
                    print(f"Batch too large ({current_batch_size} chunks). Splitting in half...")
                    mid = len(batch) // 2
                    first_half = embed_chunks(batch[:mid], batch_size=max(1, current_batch_size // 2), max_retries=max_retries)
                    second_half = embed_chunks(batch[mid:], batch_size=max(1, current_batch_size // 2), max_retries=max_retries)
                    results.extend(first_half)
                    results.extend(second_half)
                    break
                elif attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"Embedding error (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"Failed to embed batch after {max_retries} attempts: {e}")
                    raise

        if (i + batch_size) % 500 == 0 or i + batch_size >= len(chunks):
            print(f"Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")

    return results
