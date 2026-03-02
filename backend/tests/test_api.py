"""Tests for FastAPI endpoints."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
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


@pytest.fixture
def mock_searcher():
    searcher = MagicMock()
    searcher.search.return_value = [_make_result("DGESV"), _make_result("DGETRF", 0.85)]
    return searcher


@pytest.fixture
def patched_app(mock_searcher):
    """Patch get_searcher and reranker to avoid real API calls."""
    with patch("backend.app.main.get_searcher", return_value=mock_searcher), \
         patch("backend.app.main.settings") as mock_settings:
        mock_settings.use_reranker = False
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.reranker_initial_top_k = 20
        mock_settings.reranker_final_top_k = 5
        mock_settings.pinecone_api_key = "test"
        mock_settings.pinecone_index = "test"
        yield app


@pytest.mark.asyncio
class TestHealthEndpoint:

    async def test_health_returns_200(self, patched_app):
        transport = ASGITransport(app=patched_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


@pytest.mark.asyncio
class TestRootEndpoint:

    async def test_root_returns_app_info(self, patched_app):
        transport = ASGITransport(app=patched_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "LegacyLens API"
        assert "version" in data


@pytest.mark.asyncio
class TestSearchEndpoint:

    async def test_search_returns_results(self, patched_app, mock_searcher):
        transport = ASGITransport(app=patched_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/search",
                json={"query": "LU decomposition", "top_k": 5},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] == 2
        assert data["query"] == "LU decomposition"

    async def test_search_calls_searcher(self, patched_app, mock_searcher):
        transport = ASGITransport(app=patched_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/search",
                json={"query": "DGESV", "top_k": 3},
            )
        mock_searcher.search.assert_called_once_with("DGESV", top_k=3)


@pytest.mark.asyncio
class TestQueryEndpoint:

    async def test_query_non_streaming(self, patched_app, mock_searcher):
        with patch("backend.app.main.generate_answer", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "answer": "DGESV solves a linear system.",
                "sources": [],
                "query": "What is DGESV?",
            }
            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/query",
                    json={"question": "What is DGESV?", "stream": False},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "answer" in data

    async def test_query_streaming_returns_sse(self, patched_app, mock_searcher):
        async def fake_stream(question, searcher, top_k, prefetched_results=None):
            yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'data': 'Hello'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        with patch("backend.app.main.stream_query_response", side_effect=fake_stream):
            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/query",
                    json={"question": "What is DGESV?", "stream": True},
                )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = resp.text
            assert "sources" in body
            assert "token" in body
            assert "done" in body
