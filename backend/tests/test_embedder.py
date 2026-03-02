"""Tests for backend/app/ingestion/embedder.py — embedding generation with batching."""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.ingestion.chunker import CodeChunk
from backend.app.ingestion.embedder import get_embeddings_model, embed_chunks


def _make_chunk(name: str = "DGESV") -> CodeChunk:
    return CodeChunk(
        text=f"      SUBROUTINE {name}(N)\n      END",
        file_path=f"SRC/{name.lower()}.f",
        start_line=1,
        end_line=2,
        routine_name=name,
        routine_type="subroutine",
        language="f77",
    )


@patch("backend.app.ingestion.embedder.get_settings")
@patch("backend.app.ingestion.embedder.OpenAIEmbeddings")
class TestGetEmbeddingsModel:

    def test_returns_model_with_correct_params(self, MockEmbed, mock_settings):
        mock_settings.return_value.embedding_model = "text-embedding-3-small"
        mock_settings.return_value.openai_api_key = "test-key"
        mock_settings.return_value.embedding_dimensions = 1536
        get_embeddings_model()
        MockEmbed.assert_called_once_with(
            model="text-embedding-3-small",
            openai_api_key="test-key",
            dimensions=1536,
        )


@patch("backend.app.ingestion.embedder.get_settings")
@patch("backend.app.ingestion.embedder.OpenAIEmbeddings")
class TestEmbedChunks:

    def _setup_mock(self, MockEmbed, mock_settings, dim=3):
        mock_settings.return_value.embedding_model = "test-model"
        mock_settings.return_value.openai_api_key = "key"
        mock_settings.return_value.embedding_dimensions = dim
        mock_model = MagicMock()
        MockEmbed.return_value = mock_model
        return mock_model

    def test_single_batch(self, MockEmbed, mock_settings):
        mock_model = self._setup_mock(MockEmbed, mock_settings)
        chunks = [_make_chunk("DGESV"), _make_chunk("DGETRF")]
        mock_model.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        results = embed_chunks(chunks, batch_size=100)
        assert len(results) == 2
        assert results[0][0].routine_name == "DGESV"
        assert results[0][1] == [0.1, 0.2, 0.3]
        assert results[1][0].routine_name == "DGETRF"
        mock_model.embed_documents.assert_called_once()

    def test_multiple_batches(self, MockEmbed, mock_settings):
        mock_model = self._setup_mock(MockEmbed, mock_settings)
        chunks = [_make_chunk(f"R{i}") for i in range(5)]
        mock_model.embed_documents.return_value = [[1.0]] * 2  # Will be called per batch

        # batch_size=2 means 3 batches: [2, 2, 1]
        # Set side_effect to return correct number of vectors per batch
        mock_model.embed_documents.side_effect = [
            [[1.0]] * 2,
            [[2.0]] * 2,
            [[3.0]] * 1,
        ]

        results = embed_chunks(chunks, batch_size=2)
        assert len(results) == 5
        assert mock_model.embed_documents.call_count == 3

    @patch("backend.app.ingestion.embedder.time.sleep")
    def test_retry_on_failure(self, mock_sleep, MockEmbed, mock_settings):
        mock_model = self._setup_mock(MockEmbed, mock_settings)
        chunks = [_make_chunk("DGESV")]
        # First call fails, second succeeds
        mock_model.embed_documents.side_effect = [
            Exception("API error"),
            [[0.1, 0.2, 0.3]],
        ]

        results = embed_chunks(chunks, batch_size=100, max_retries=3)
        assert len(results) == 1
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @patch("backend.app.ingestion.embedder.time.sleep")
    def test_exhausts_max_retries(self, mock_sleep, MockEmbed, mock_settings):
        mock_model = self._setup_mock(MockEmbed, mock_settings)
        chunks = [_make_chunk("DGESV")]
        mock_model.embed_documents.side_effect = Exception("Persistent error")

        with pytest.raises(Exception, match="Persistent error"):
            embed_chunks(chunks, batch_size=100, max_retries=3)

        assert mock_model.embed_documents.call_count == 3
        assert mock_sleep.call_count == 2  # retries: 0, 1 (not after last)

    def test_empty_chunks(self, MockEmbed, mock_settings):
        self._setup_mock(MockEmbed, mock_settings)
        results = embed_chunks([], batch_size=100)
        assert results == []

    @patch("backend.app.ingestion.embedder.time.sleep")
    def test_exponential_backoff(self, mock_sleep, MockEmbed, mock_settings):
        mock_model = self._setup_mock(MockEmbed, mock_settings)
        chunks = [_make_chunk("DGESV")]
        mock_model.embed_documents.side_effect = [
            Exception("error 1"),
            Exception("error 2"),
            Exception("error 3"),
            [[0.1, 0.2, 0.3]],
        ]

        results = embed_chunks(chunks, batch_size=100, max_retries=5)
        assert len(results) == 1
        # Verify exponential backoff: 2^0=1, 2^1=2, 2^2=4
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2, 4]
