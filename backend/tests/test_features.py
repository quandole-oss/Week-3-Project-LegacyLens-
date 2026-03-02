"""Tests for feature modules: explain, docgen, patterns, business."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

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


def _make_mock_searcher(results=None):
    searcher = MagicMock()
    searcher.search.return_value = results if results is not None else [_make_result("DGESV"), _make_result("DGETRF", 0.85)]
    return searcher


def _make_mock_chain():
    chain = MagicMock()

    async def fake_astream(*args, **kwargs):
        yield "token1"
        yield "token2"

    chain.astream = fake_astream
    return chain


@pytest.mark.asyncio
class TestStreamExplanation:

    @patch("backend.app.features.explain.get_explain_chain")
    @patch("backend.app.features.explain.assemble_context", return_value="context")
    async def test_yields_sources_tokens_done(self, mock_ctx, mock_chain_fn):
        from backend.app.features.explain import stream_explanation

        mock_chain_fn.return_value = _make_mock_chain()
        searcher = _make_mock_searcher()

        events = []
        async for event in stream_explanation("explain DGESV", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "done"

    @patch("backend.app.features.explain.get_explain_chain")
    @patch("backend.app.features.explain.assemble_context", return_value="context")
    async def test_sources_limited_to_5(self, mock_ctx, mock_chain_fn):
        from backend.app.features.explain import stream_explanation

        mock_chain_fn.return_value = _make_mock_chain()
        results = [_make_result(f"R{i}") for i in range(10)]
        searcher = _make_mock_searcher(results)

        events = []
        async for event in stream_explanation("test", searcher):
            events.append(event)

        sources_event = json.loads(events[0].replace("data: ", "").strip())
        assert len(sources_event["data"]) <= 5

    @patch("backend.app.features.explain.get_explain_chain")
    @patch("backend.app.features.explain.assemble_context", return_value="context")
    async def test_sources_have_required_fields(self, mock_ctx, mock_chain_fn):
        from backend.app.features.explain import stream_explanation

        mock_chain_fn.return_value = _make_mock_chain()
        searcher = _make_mock_searcher()

        events = []
        async for event in stream_explanation("test", searcher):
            events.append(event)

        sources_event = json.loads(events[0].replace("data: ", "").strip())
        for source in sources_event["data"]:
            assert "file_path" in source
            assert "routine_name" in source
            assert "start_line" in source
            assert "end_line" in source
            assert "score" in source


@pytest.mark.asyncio
class TestStreamDocumentation:

    @patch("backend.app.features.docgen.get_docgen_chain")
    @patch("backend.app.features.docgen.assemble_context", return_value="context")
    async def test_yields_sources_tokens_done(self, mock_ctx, mock_chain_fn):
        from backend.app.features.docgen import stream_documentation

        mock_chain_fn.return_value = _make_mock_chain()
        searcher = _make_mock_searcher()

        events = []
        async for event in stream_documentation("doc DGESV", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "done"


@pytest.mark.asyncio
class TestStreamBusinessLogic:

    @patch("backend.app.features.business.get_business_logic_chain")
    @patch("backend.app.features.business.assemble_context", return_value="context")
    async def test_yields_sources_tokens_done(self, mock_ctx, mock_chain_fn):
        from backend.app.features.business import stream_business_logic

        mock_chain_fn.return_value = _make_mock_chain()
        searcher = _make_mock_searcher()

        events = []
        async for event in stream_business_logic("business DGESV", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "done"


@pytest.mark.asyncio
class TestFindSimilarPatterns:

    async def test_groups_by_routine_type(self):
        from backend.app.features.patterns import find_similar_patterns

        results = [
            _make_result("DGESV"),
            _make_result("DGETRF"),
        ]
        # Both are "subroutine" type
        searcher = _make_mock_searcher(results)

        events = []
        async for event in find_similar_patterns("LU decomposition", searcher):
            events.append(event)

        patterns_event = json.loads(events[0].replace("data: ", "").strip())
        assert patterns_event["type"] == "patterns"
        assert "subroutine" in patterns_event["data"]
        assert len(patterns_event["data"]["subroutine"]) == 2

    async def test_yields_patterns_results_done(self):
        from backend.app.features.patterns import find_similar_patterns

        searcher = _make_mock_searcher()

        events = []
        async for event in find_similar_patterns("test", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        types = [p["type"] for p in parsed]
        assert types[0] == "patterns"
        assert "result" in types
        assert types[-1] == "done"

    async def test_done_event_has_totals(self):
        from backend.app.features.patterns import find_similar_patterns

        searcher = _make_mock_searcher()

        events = []
        async for event in find_similar_patterns("test", searcher):
            events.append(event)

        done_event = json.loads(events[-1].replace("data: ", "").strip())
        assert done_event["type"] == "done"
        assert "total" in done_event["data"]
        assert "groups" in done_event["data"]
        assert done_event["data"]["total"] == 2
        assert done_event["data"]["groups"] == 1  # both are subroutine type

    async def test_empty_results(self):
        from backend.app.features.patterns import find_similar_patterns

        searcher = _make_mock_searcher([])

        events = []
        async for event in find_similar_patterns("test", searcher):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        patterns_event = parsed[0]
        assert patterns_event["type"] == "patterns"
        assert patterns_event["data"] == {}
        done_event = parsed[-1]
        assert done_event["data"]["total"] == 0
