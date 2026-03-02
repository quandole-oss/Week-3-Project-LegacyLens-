"""Ingestion pipeline: scan -> chunk -> embed -> store in Pinecone."""

from pinecone import Pinecone, ServerlessSpec
from backend.app.config import get_settings
from backend.app.ingestion.scanner import scan_directory, SourceFile
from backend.app.ingestion.chunker import chunk_fortran_file, create_file_summary_chunk, CodeChunk
from backend.app.ingestion.embedder import embed_chunks


def create_pinecone_index(settings=None):
    """Create Pinecone index if it doesn't exist."""
    settings = settings or get_settings()
    pc = Pinecone(api_key=settings.pinecone_api_key)

    existing = [idx.name for idx in pc.list_indexes()]
    if settings.pinecone_index not in existing:
        print(f"Creating Pinecone index '{settings.pinecone_index}'...")
        pc.create_index(
            name=settings.pinecone_index,
            dimension=settings.embedding_dimensions,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )
        print("Index created.")
    else:
        print(f"Index '{settings.pinecone_index}' already exists.")

    return pc.Index(settings.pinecone_index)


def read_file_content(filepath: str) -> str:
    """Read file content with encoding fallback."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as f:
            return f.read()


def chunk_all_files(files: list[SourceFile]) -> list[CodeChunk]:
    """Chunk all source files with routine-level and file-level summary chunks."""
    all_chunks = []
    summary_count = 0

    for source_file in files:
        content = read_file_content(source_file.path)
        routine_chunks = chunk_fortran_file(
            file_content=content,
            file_path=source_file.relative_path,
            language=source_file.language,
        )
        all_chunks.extend(routine_chunks)

        # Create a file-level summary chunk for hierarchical retrieval
        summary = create_file_summary_chunk(
            content, source_file.relative_path,
            source_file.language, routine_chunks,
        )
        if summary:
            all_chunks.append(summary)
            summary_count += 1

    print(f"Generated {len(all_chunks)} chunks ({summary_count} file summaries) from {len(files)} files")
    return all_chunks


def upsert_to_pinecone(
    index,
    embedded_chunks: list[tuple[CodeChunk, list[float]]],
    batch_size: int = 100,
):
    """Upsert embedded chunks to Pinecone."""
    vectors = []
    for chunk, embedding in embedded_chunks:
        meta = {
            "text": chunk.text[:40000],  # Pinecone metadata limit
            "file_path": chunk.file_path,
            "routine_name": chunk.routine_name,
            "routine_type": chunk.routine_type,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "language": chunk.language,
        }
        # Include parsed metadata (purpose, arguments, common_blocks, etc.)
        for key, value in chunk.metadata.items():
            if isinstance(value, str) and value:
                meta[key] = value[:1000]  # Cap metadata field size
        vectors.append({
            "id": chunk.chunk_id,
            "values": embedding,
            "metadata": meta,
        })

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        if (i + batch_size) % 500 == 0 or i + batch_size >= len(vectors):
            print(f"Upserted {min(i + batch_size, len(vectors))}/{len(vectors)} vectors")

    print(f"Upsert complete. Total vectors: {len(vectors)}")


def run_ingestion(data_dir: str = None):
    """Run the full ingestion pipeline."""
    settings = get_settings()
    data_dir = data_dir or settings.lapack_data_dir

    print("=" * 60)
    print("LegacyLens Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Scan
    print("\n[1/4] Scanning for Fortran source files...")
    files = scan_directory(data_dir)

    # Step 2: Chunk
    print("\n[2/4] Chunking source files...")
    chunks = chunk_all_files(files)

    # Step 3: Embed
    print("\n[3/4] Generating embeddings...")
    embedded_chunks = embed_chunks(chunks, batch_size=settings.chunk_batch_size)

    # Step 4: Store
    print("\n[4/4] Storing in Pinecone...")
    index = create_pinecone_index(settings)
    upsert_to_pinecone(index, embedded_chunks)

    print("\n" + "=" * 60)
    print(f"Ingestion complete!")
    print(f"  Files processed: {len(files)}")
    print(f"  Chunks created:  {len(chunks)}")
    print(f"  Vectors stored:  {len(embedded_chunks)}")
    print("=" * 60)

    return {
        "files": len(files),
        "chunks": len(chunks),
        "vectors": len(embedded_chunks),
    }
