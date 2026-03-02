"""Tests for backend/app/ingestion/pipeline.py — ingestion pipeline orchestrator."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, call

from backend.app.ingestion.pipeline import (
    read_file_content,
    chunk_all_files,
    upsert_to_pinecone,
    create_pinecone_index,
    run_ingestion,
)
from backend.app.ingestion.scanner import SourceFile
from backend.app.ingestion.chunker import CodeChunk


class TestReadFileContent:

    def test_reads_utf8(self, tmp_path):
        f = tmp_path / "test.f"
        f.write_text("      SUBROUTINE DGESV(N)\n      END\n", encoding="utf-8")
        content = read_file_content(str(f))
        assert "SUBROUTINE DGESV" in content

    def test_falls_back_to_latin1(self, tmp_path):
        f = tmp_path / "test.f"
        # Write bytes that are valid latin-1 but invalid utf-8
        f.write_bytes(b"      SUBROUTINE DGESV(N)\n      \xe9\n      END\n")
        content = read_file_content(str(f))
        assert "SUBROUTINE DGESV" in content


class TestChunkAllFiles:

    def test_produces_routine_and_summary_chunks(self, tmp_path):
        f = tmp_path / "dgesv.f"
        code = "      SUBROUTINE DGESV(N)\n      INTEGER N\n      END SUBROUTINE DGESV\n"
        f.write_text(code)
        source_file = SourceFile(
            path=str(f),
            relative_path="SRC/dgesv.f",
            line_count=3,
            language="f77",
            size_bytes=len(code),
        )
        chunks = chunk_all_files([source_file])
        # Should have routine chunk(s) + file summary chunk
        assert len(chunks) >= 2
        types = [c.routine_type for c in chunks]
        assert "subroutine" in types
        assert "file_summary" in types

    def test_empty_file_list(self):
        chunks = chunk_all_files([])
        assert chunks == []


class TestUpsertToPinecone:

    def test_metadata_text_truncated(self):
        mock_index = MagicMock()
        long_text = "x" * 50000
        chunk = CodeChunk(
            text=long_text,
            file_path="SRC/test.f",
            start_line=1,
            end_line=1,
            routine_name="TEST",
            routine_type="subroutine",
            language="f77",
        )
        embedded = [(chunk, [0.1, 0.2])]
        upsert_to_pinecone(mock_index, embedded)

        upserted = mock_index.upsert.call_args[1]["vectors"]
        assert len(upserted[0]["metadata"]["text"]) == 35000

    def test_metadata_fields_capped(self):
        mock_index = MagicMock()
        chunk = CodeChunk(
            text="test",
            file_path="SRC/test.f",
            start_line=1,
            end_line=1,
            routine_name="TEST",
            routine_type="subroutine",
            language="f77",
            metadata={"purpose": "y" * 2000},
        )
        embedded = [(chunk, [0.1, 0.2])]
        upsert_to_pinecone(mock_index, embedded)

        upserted = mock_index.upsert.call_args[1]["vectors"]
        assert len(upserted[0]["metadata"]["purpose"]) == 1000

    def test_batches_of_100(self):
        mock_index = MagicMock()
        chunks = []
        for i in range(250):
            chunk = CodeChunk(
                text=f"routine_{i}",
                file_path="SRC/test.f",
                start_line=1,
                end_line=1,
                routine_name=f"R{i}",
                routine_type="subroutine",
                language="f77",
            )
            chunks.append((chunk, [float(i)]))

        upsert_to_pinecone(mock_index, chunks, batch_size=100)
        assert mock_index.upsert.call_count == 3  # 100 + 100 + 50


class TestCreatePineconeIndex:

    @patch("backend.app.ingestion.pipeline.get_settings")
    @patch("backend.app.ingestion.pipeline.Pinecone")
    def test_creates_new_index(self, MockPC, mock_settings):
        mock_settings.return_value.pinecone_api_key = "key"
        mock_settings.return_value.pinecone_index = "legacylens"
        mock_settings.return_value.embedding_dimensions = 1536
        mock_settings.return_value.pinecone_cloud = "aws"
        mock_settings.return_value.pinecone_region = "us-east-1"

        mock_pc = MagicMock()
        MockPC.return_value = mock_pc
        # No existing indexes
        mock_pc.list_indexes.return_value = []

        create_pinecone_index(mock_settings.return_value)
        mock_pc.create_index.assert_called_once()

    @patch("backend.app.ingestion.pipeline.get_settings")
    @patch("backend.app.ingestion.pipeline.Pinecone")
    def test_skips_creation_when_exists(self, MockPC, mock_settings):
        mock_settings.return_value.pinecone_api_key = "key"
        mock_settings.return_value.pinecone_index = "legacylens"
        mock_settings.return_value.embedding_dimensions = 1536

        mock_pc = MagicMock()
        MockPC.return_value = mock_pc
        # Index already exists
        existing_idx = MagicMock()
        existing_idx.name = "legacylens"
        mock_pc.list_indexes.return_value = [existing_idx]

        create_pinecone_index(mock_settings.return_value)
        mock_pc.create_index.assert_not_called()


class TestRunIngestion:

    @patch("backend.app.ingestion.pipeline.get_settings")
    @patch("backend.app.ingestion.pipeline.scan_directory")
    @patch("backend.app.ingestion.pipeline.chunk_all_files")
    @patch("backend.app.ingestion.pipeline.embed_chunks")
    @patch("backend.app.ingestion.pipeline.create_pinecone_index")
    @patch("backend.app.ingestion.pipeline.upsert_to_pinecone")
    def test_orchestrates_all_steps(
        self, mock_upsert, mock_create_idx, mock_embed,
        mock_chunk, mock_scan, mock_settings
    ):
        mock_settings.return_value.lapack_data_dir = "/data"
        mock_settings.return_value.chunk_batch_size = 100

        # Set up mock pipeline
        mock_files = [MagicMock(), MagicMock()]
        mock_scan.return_value = mock_files
        mock_chunks = [MagicMock(), MagicMock(), MagicMock()]
        mock_chunk.return_value = mock_chunks
        mock_embedded = [(MagicMock(), [0.1])] * 3
        mock_embed.return_value = mock_embedded
        mock_index = MagicMock()
        mock_create_idx.return_value = mock_index

        result = run_ingestion("/data")

        mock_scan.assert_called_once_with("/data")
        mock_chunk.assert_called_once_with(mock_files)
        mock_embed.assert_called_once()
        mock_create_idx.assert_called_once()
        mock_upsert.assert_called_once_with(mock_index, mock_embedded)

        assert result == {
            "files": 2,
            "chunks": 3,
            "vectors": 3,
        }
