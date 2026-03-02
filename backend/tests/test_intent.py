"""Tests for intent detection."""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.retrieval.intent import detect_intent


class TestKeywordIntentDetection:
    """Test fast keyword-based intent detection."""

    def test_detects_explain_intent(self):
        assert detect_intent("explain what DGESV does") == "explain"
        assert detect_intent("What does DGETRF do?") == "explain"
        assert detect_intent("How does LU decomposition work?") == "explain"

    def test_detects_dependency_intent(self):
        assert detect_intent("what does DGESV depend on") == "dependencies"
        assert detect_intent("show me the call graph for DGETRF") == "dependencies"

    def test_detects_docgen_intent(self):
        assert detect_intent("generate documentation for DGESV") == "docgen"
        assert detect_intent("write a docstring for DGETRF") == "docgen"

    def test_detects_search_intent(self):
        assert detect_intent("find all routines for eigenvalues") == "search"
        assert detect_intent("search for LU decomposition") == "search"

    def test_detects_pattern_intent(self):
        assert detect_intent("find similar code to DGESV") == "patterns"
        assert detect_intent("what patterns are related to pivoting") == "patterns"

    def test_detects_business_intent(self):
        assert detect_intent("what algorithm does DGESV implement") == "business"
        assert detect_intent("the mathematical formula used in pivoting") == "business"


class TestLLMFallbackIntentDetection:
    """Test LLM-based intent detection for ambiguous queries."""

    def test_uses_llm_for_ambiguous_query(self):
        with patch("backend.app.retrieval.intent.get_settings") as mock_settings, \
             patch("backend.app.retrieval.intent.Anthropic") as mock_anthropic_cls:
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text="explain")]
            mock_client.messages.create.return_value = mock_resp

            # "DGESV" alone doesn't match any keyword rule
            result = detect_intent("DGESV")
            assert result == "explain"

    def test_defaults_to_query_on_unknown_llm_response(self):
        with patch("backend.app.retrieval.intent.get_settings") as mock_settings, \
             patch("backend.app.retrieval.intent.Anthropic") as mock_anthropic_cls:
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text="unknown_category")]
            mock_client.messages.create.return_value = mock_resp

            result = detect_intent("DGESV")
            assert result == "query"

    def test_defaults_to_query_on_llm_failure(self):
        with patch("backend.app.retrieval.intent.get_settings") as mock_settings, \
             patch("backend.app.retrieval.intent.Anthropic") as mock_anthropic_cls:
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_anthropic_cls.return_value.messages.create.side_effect = Exception("API error")

            result = detect_intent("DGESV")
            assert result == "query"

    def test_defaults_to_query_without_api_key(self):
        with patch("backend.app.retrieval.intent.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(anthropic_api_key="")
            result = detect_intent("DGESV")
            assert result == "query"
