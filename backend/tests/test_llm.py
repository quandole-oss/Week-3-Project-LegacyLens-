"""Tests for backend/app/generation/llm.py — LLM chains and streaming."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.app.retrieval.search import SearchResult


def _make_result(name: str = "DGESV", score: float = 0.9) -> SearchResult:
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


@patch("backend.app.generation.llm.get_settings")
@patch("backend.app.generation.llm.ChatAnthropic")
class TestGetLlm:

    def test_returns_chat_anthropic(self, MockChat, mock_settings):
        mock_settings.return_value.generation_model = "claude-sonnet-4-6"
        mock_settings.return_value.anthropic_api_key = "test-key"

        from backend.app.generation.llm import get_llm
        get_llm()

        MockChat.assert_called_once_with(
            model="claude-sonnet-4-6",
            anthropic_api_key="test-key",
            temperature=0,
            streaming=True,
            max_tokens=4096,
        )


class TestGetQueryChain:

    @patch("backend.app.generation.llm.get_llm")
    def test_returns_runnable(self, mock_llm):
        mock_llm.return_value = MagicMock()
        from backend.app.generation.llm import get_query_chain
        chain = get_query_chain()
        # LCEL chains have invoke/ainvoke methods
        assert chain is not None


@pytest.mark.asyncio
class TestStreamQueryResponse:

    @patch("backend.app.generation.llm.get_query_chain")
    @patch("backend.app.generation.llm.assemble_context", return_value="context text")
    @patch("backend.app.generation.llm.format_sources", return_value=[{"file_path": "test.f"}])
    async def test_yields_sources_tokens_done(self, mock_fmt, mock_ctx, mock_chain_fn):
        from backend.app.generation.llm import stream_query_response

        mock_chain = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield "Hello"
            yield " world"

        mock_chain.astream = fake_astream
        mock_chain_fn.return_value = mock_chain

        searcher = MagicMock()
        searcher.search.return_value = [_make_result()]

        events = []
        async for event in stream_query_response("What is DGESV?", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "done"

    @patch("backend.app.generation.llm.get_query_chain")
    @patch("backend.app.generation.llm.assemble_context", return_value="context")
    @patch("backend.app.generation.llm.format_sources", return_value=[])
    async def test_uses_prefetched_results(self, mock_fmt, mock_ctx, mock_chain_fn):
        from backend.app.generation.llm import stream_query_response

        mock_chain = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield "ok"

        mock_chain.astream = fake_astream
        mock_chain_fn.return_value = mock_chain

        searcher = MagicMock()
        prefetched = [_make_result()]

        events = []
        async for event in stream_query_response("test", searcher, prefetched_results=prefetched):
            events.append(event)

        # Should NOT call searcher.search when prefetched_results provided
        searcher.search.assert_not_called()

    @patch("backend.app.generation.llm.get_query_chain")
    @patch("backend.app.generation.llm.assemble_context", return_value="context")
    @patch("backend.app.generation.llm.format_sources", return_value=[])
    async def test_calls_searcher_when_no_prefetched(self, mock_fmt, mock_ctx, mock_chain_fn):
        from backend.app.generation.llm import stream_query_response

        mock_chain = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield "ok"

        mock_chain.astream = fake_astream
        mock_chain_fn.return_value = mock_chain

        searcher = MagicMock()
        searcher.search.return_value = [_make_result()]

        events = []
        async for event in stream_query_response("test", searcher):
            events.append(event)

        searcher.search.assert_called_once()


@pytest.mark.asyncio
class TestGenerateAnswer:

    @patch("backend.app.generation.llm.get_query_chain")
    @patch("backend.app.generation.llm.assemble_context", return_value="context")
    @patch("backend.app.generation.llm.format_sources", return_value=[{"file_path": "test.f"}])
    async def test_returns_dict(self, mock_fmt, mock_ctx, mock_chain_fn):
        from backend.app.generation.llm import generate_answer

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value="DGESV solves linear systems.")
        mock_chain_fn.return_value = mock_chain

        searcher = MagicMock()
        searcher.search.return_value = [_make_result()]

        result = await generate_answer("What is DGESV?", searcher)
        assert "answer" in result
        assert "sources" in result
        assert "query" in result
        assert result["query"] == "What is DGESV?"


@pytest.mark.asyncio
class TestExplainCode:

    @patch("backend.app.generation.llm.get_explain_chain")
    async def test_yields_tokens_done(self, mock_chain_fn):
        from backend.app.generation.llm import explain_code

        mock_chain = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield "explanation"

        mock_chain.astream = fake_astream
        mock_chain_fn.return_value = mock_chain

        events = []
        async for event in explain_code("some context"):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert "token" in types
        assert types[-1] == "done"


@pytest.mark.asyncio
class TestGenerateDocs:

    @patch("backend.app.generation.llm.get_docgen_chain")
    async def test_yields_tokens_done(self, mock_chain_fn):
        from backend.app.generation.llm import generate_docs

        mock_chain = MagicMock()

        async def fake_astream(*args, **kwargs):
            yield "docs"

        mock_chain.astream = fake_astream
        mock_chain_fn.return_value = mock_chain

        events = []
        async for event in generate_docs("some context"):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert "token" in types
        assert types[-1] == "done"
