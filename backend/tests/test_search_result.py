"""Tests for SearchResult and CodeSearcher in backend/app/retrieval/search.py."""

import pytest
from unittest.mock import patch, MagicMock

from backend.app.retrieval.search import SearchResult, CodeSearcher, EmbeddingCache


class TestSearchResultToDict:

    def test_returns_all_fields(self):
        sr = SearchResult(
            text="SUBROUTINE DGESV(N)",
            file_path="SRC/dgesv.f",
            routine_name="DGESV",
            routine_type="subroutine",
            start_line=1,
            end_line=55,
            language="f77",
            score=0.912345,
        )
        d = sr.to_dict()
        assert d["text"] == "SUBROUTINE DGESV(N)"
        assert d["file_path"] == "SRC/dgesv.f"
        assert d["routine_name"] == "DGESV"
        assert d["routine_type"] == "subroutine"
        assert d["start_line"] == 1
        assert d["end_line"] == 55
        assert d["language"] == "f77"

    def test_score_rounded_to_4_places(self):
        sr = SearchResult(
            text="test", file_path="test.f", routine_name="T",
            routine_type="sub", start_line=1, end_line=1,
            language="f77", score=0.912345678,
        )
        d = sr.to_dict()
        assert d["score"] == 0.9123


class TestCodeSearcherInit:

    @patch("backend.app.retrieval.search.Pinecone")
    @patch("backend.app.retrieval.search.OpenAIEmbeddings")
    @patch("backend.app.retrieval.search.get_settings")
    def test_initializes_correctly(self, mock_settings, MockEmbed, MockPC):
        mock_settings.return_value.embedding_model = "text-embedding-3-small"
        mock_settings.return_value.openai_api_key = "key"
        mock_settings.return_value.embedding_dimensions = 1536
        mock_settings.return_value.pinecone_api_key = "pc-key"
        mock_settings.return_value.pinecone_index = "legacylens"

        searcher = CodeSearcher()
        MockEmbed.assert_called_once()
        MockPC.assert_called_once_with(api_key="pc-key")
        assert isinstance(searcher._embedding_cache, EmbeddingCache)


class TestCodeSearcherEmbedQuery:

    @patch("backend.app.retrieval.search.Pinecone")
    @patch("backend.app.retrieval.search.OpenAIEmbeddings")
    @patch("backend.app.retrieval.search.get_settings")
    def test_cache_miss_calls_embeddings(self, mock_settings, MockEmbed, MockPC):
        mock_settings.return_value.embedding_model = "m"
        mock_settings.return_value.openai_api_key = "k"
        mock_settings.return_value.embedding_dimensions = 3
        mock_settings.return_value.pinecone_api_key = "k"
        mock_settings.return_value.pinecone_index = "idx"

        mock_embed_instance = MagicMock()
        mock_embed_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        MockEmbed.return_value = mock_embed_instance

        searcher = CodeSearcher()
        vec = searcher._embed_query("test query")
        assert vec == [0.1, 0.2, 0.3]
        mock_embed_instance.embed_query.assert_called_once_with("test query")

    @patch("backend.app.retrieval.search.Pinecone")
    @patch("backend.app.retrieval.search.OpenAIEmbeddings")
    @patch("backend.app.retrieval.search.get_settings")
    def test_cache_hit_skips_embeddings(self, mock_settings, MockEmbed, MockPC):
        mock_settings.return_value.embedding_model = "m"
        mock_settings.return_value.openai_api_key = "k"
        mock_settings.return_value.embedding_dimensions = 3
        mock_settings.return_value.pinecone_api_key = "k"
        mock_settings.return_value.pinecone_index = "idx"

        mock_embed_instance = MagicMock()
        mock_embed_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        MockEmbed.return_value = mock_embed_instance

        searcher = CodeSearcher()
        # First call — cache miss
        searcher._embed_query("test query")
        # Second call — cache hit
        vec = searcher._embed_query("test query")

        assert vec == [0.1, 0.2, 0.3]
        assert mock_embed_instance.embed_query.call_count == 1


class TestCodeSearcherSearch:

    @patch("backend.app.retrieval.search.Pinecone")
    @patch("backend.app.retrieval.search.OpenAIEmbeddings")
    @patch("backend.app.retrieval.search.get_settings")
    def test_parses_pinecone_response(self, mock_settings, MockEmbed, MockPC):
        mock_settings.return_value.embedding_model = "m"
        mock_settings.return_value.openai_api_key = "k"
        mock_settings.return_value.embedding_dimensions = 3
        mock_settings.return_value.pinecone_api_key = "k"
        mock_settings.return_value.pinecone_index = "idx"
        mock_settings.return_value.retrieval_top_k = 5

        mock_embed_instance = MagicMock()
        mock_embed_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        MockEmbed.return_value = mock_embed_instance

        # Mock Pinecone query response
        mock_match = MagicMock()
        mock_match.metadata = {
            "text": "SUBROUTINE DGESV(N)",
            "file_path": "SRC/dgesv.f",
            "routine_name": "DGESV",
            "routine_type": "subroutine",
            "start_line": "1",
            "end_line": "55",
            "language": "f77",
        }
        mock_match.score = 0.95

        mock_index = MagicMock()
        mock_index.query.return_value = MagicMock(matches=[mock_match])
        MockPC.return_value.Index.return_value = mock_index

        searcher = CodeSearcher()
        results = searcher.search("DGESV")

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].routine_name == "DGESV"
        assert results[0].score == 0.95
        assert results[0].start_line == 1
