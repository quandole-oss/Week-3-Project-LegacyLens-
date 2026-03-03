"""Ingestion pipeline: scan -> chunk -> embed -> store in Pinecone."""

import time

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
            "text": chunk.text[:35000],  # Pinecone 40KB metadata limit (leave room for other fields)
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

    t_start = time.perf_counter()

    # Step 1: Scan
    print("\n[1/4] Scanning for Fortran source files...")
    t0 = time.perf_counter()
    files = scan_directory(data_dir)
    t_scan = time.perf_counter() - t0

    # Step 2: Chunk
    print("\n[2/4] Chunking source files...")
    t0 = time.perf_counter()
    chunks = chunk_all_files(files)
    t_chunk = time.perf_counter() - t0

    # Step 3: Embed
    print("\n[3/4] Generating embeddings...")
    t0 = time.perf_counter()
    embedded_chunks = embed_chunks(chunks, batch_size=settings.chunk_batch_size)
    t_embed = time.perf_counter() - t0

    # Step 4: Store
    print("\n[4/4] Storing in Pinecone...")
    t0 = time.perf_counter()
    index = create_pinecone_index(settings)
    upsert_to_pinecone(index, embedded_chunks)
    t_upsert = time.perf_counter() - t0

    total_time = time.perf_counter() - t_start
    total_loc = sum(f.line_count for f in files)
    loc_per_min = total_loc / (total_time / 60) if total_time > 0 else 0

    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print(f"  Files processed: {len(files)}")
    print(f"  Chunks created:  {len(chunks)}")
    print(f"  Vectors stored:  {len(embedded_chunks)}")
    print(f"  Total LOC:       {total_loc:,}")
    print()
    print(f"  {'Stage':<12} {'Time (s)':>10}")
    print(f"  {'-'*12} {'-'*10}")
    print(f"  {'Scan':<12} {t_scan:>10.2f}")
    print(f"  {'Chunk':<12} {t_chunk:>10.2f}")
    print(f"  {'Embed':<12} {t_embed:>10.2f}")
    print(f"  {'Upsert':<12} {t_upsert:>10.2f}")
    print(f"  {'-'*12} {'-'*10}")
    print(f"  {'Total':<12} {total_time:>10.2f}")
    print()
    print(f"  Throughput: {loc_per_min:,.0f} LOC/min")
    print("=" * 60)

    return {
        "files": len(files),
        "chunks": len(chunks),
        "vectors": len(embedded_chunks),
        "total_loc": total_loc,
        "t_scan": round(t_scan, 2),
        "t_chunk": round(t_chunk, 2),
        "t_embed": round(t_embed, 2),
        "t_upsert": round(t_upsert, 2),
        "total_time": round(total_time, 2),
        "loc_per_min": round(loc_per_min, 0),
    }
