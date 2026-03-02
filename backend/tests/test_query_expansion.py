"""Tests for query expansion via LLM."""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.retrieval.query_expansion import expand_query


class TestExpandQuery:

    def test_returns_expanded_text(self):
        with patch("backend.app.retrieval.query_expansion.get_settings") as mock_settings, \
             patch("backend.app.retrieval.query_expansion.Anthropic") as mock_anthropic_cls:
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text="solve linear system DGESV LU factorization pivot")]
            mock_client.messages.create.return_value = mock_resp

            result = expand_query("solve linear system")
            assert "DGESV" in result
            assert "LU" in result

    def test_falls_back_on_error(self):
        with patch("backend.app.retrieval.query_expansion.get_settings") as mock_settings, \
             patch("backend.app.retrieval.query_expansion.Anthropic") as mock_anthropic_cls:
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_anthropic_cls.return_value.messages.create.side_effect = Exception("API down")

            result = expand_query("test query")
            assert result == "test query"

    def test_falls_back_when_no_api_key(self):
        with patch("backend.app.retrieval.query_expansion.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key="")

            result = expand_query("test query")
            assert result == "test query"
