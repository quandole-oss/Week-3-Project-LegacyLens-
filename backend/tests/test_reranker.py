"""Tests for the Claude Haiku re-ranker."""

import json
import pytest
from unittest.mock import patch, MagicMock

from backend.app.retrieval.reranker import _score_single, rerank_results
from backend.app.retrieval.search import SearchResult


def _make_result(name: str = "DGESV", score: float = 0.8) -> SearchResult:
    return SearchResult(
        text=f"      SUBROUTINE {name}(N)\n      INTEGER N\n      END",
        file_path=f"SRC/{name.lower()}.f",
        routine_name=name,
        routine_type="subroutine",
        start_line=1,
        end_line=3,
        language="f77",
        score=score,
    )


class TestScoreSingle:
    """Test the single-result scoring function."""

    def test_returns_parsed_score(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 8}')]
        mock_client.messages.create.return_value = mock_response

        result = _make_result("DGESV")
        scored_result, score = _score_single(mock_client, "test-model", "What is DGESV?", result)
        assert score == 8
        assert scored_result.routine_name == "DGESV"

    def test_clamps_score_to_0_10(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 15}')]
        mock_client.messages.create.return_value = mock_response

        result = _make_result("DGESV")
        _, score = _score_single(mock_client, "model", "query", result)
        assert score == 10

    def test_clamps_negative_to_zero(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": -3}')]
        mock_client.messages.create.return_value = mock_response

        result = _make_result("DGESV")
        _, score = _score_single(mock_client, "model", "query", result)
        assert score == 0

    def test_defaults_to_5_on_failure(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")

        result = _make_result("DGESV")
        _, score = _score_single(mock_client, "model", "query", result)
        assert score == 5

    def test_defaults_to_5_on_malformed_json(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='not json')]
        mock_client.messages.create.return_value = mock_response

        result = _make_result("DGESV")
        _, score = _score_single(mock_client, "model", "query", result)
        assert score == 5

    def test_truncates_long_text(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 7}')]
        mock_client.messages.create.return_value = mock_response

        result = _make_result("DGESV")
        result.text = "X" * 5000  # Very long text
        _score_single(mock_client, "model", "query", result)

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        # The text in the prompt should be truncated to 2000 chars
        assert len(prompt) < 5000


@pytest.mark.asyncio
class TestRerankResults:
    """Test the full re-ranking pipeline."""

    async def test_returns_top_k_results(self):
        results = [_make_result(f"R{i}", score=0.5 + i * 0.01) for i in range(10)]

        with patch("backend.app.retrieval.reranker.get_settings") as mock_settings, \
             patch("backend.app.retrieval.reranker.Anthropic") as mock_anthropic_cls:

            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )

            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client

            # Each result gets a score based on its index (higher index = higher score)
            def create_response(**kwargs):
                prompt = kwargs["messages"][0]["content"]
                # Extract routine name to determine score
                for i in range(10):
                    if f"R{i}" in prompt:
                        mock_resp = MagicMock()
                        mock_resp.content = [MagicMock(text=json.dumps({"score": i}))]
                        return mock_resp
                mock_resp = MagicMock()
                mock_resp.content = [MagicMock(text='{"score": 5}')]
                return mock_resp

            mock_client.messages.create.side_effect = create_response

            reranked = await rerank_results("test query", results, final_top_k=3)

            assert len(reranked) == 3
            # Highest scored results should come first
            assert reranked[0].score >= reranked[1].score
            assert reranked[1].score >= reranked[2].score

    async def test_handles_empty_results(self):
        with patch("backend.app.retrieval.reranker.get_settings") as mock_settings, \
             patch("backend.app.retrieval.reranker.Anthropic"):
            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            reranked = await rerank_results("test", [], final_top_k=5)
            assert reranked == []

    async def test_scores_normalized_0_to_1(self):
        results = [_make_result("DGESV")]

        with patch("backend.app.retrieval.reranker.get_settings") as mock_settings, \
             patch("backend.app.retrieval.reranker.Anthropic") as mock_anthropic_cls:

            mock_settings.return_value = MagicMock(
                anthropic_api_key="test-key",
                rerank_model="test-model",
            )
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text='{"score": 8}')]
            mock_client.messages.create.return_value = mock_resp

            reranked = await rerank_results("test", results, final_top_k=5)

            assert len(reranked) == 1
            assert 0.0 <= reranked[0].score <= 1.0
            assert reranked[0].score == 0.8  # 8/10
