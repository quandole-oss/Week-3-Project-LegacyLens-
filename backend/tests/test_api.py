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
        mock_settings.use_query_expansion = False
        mock_settings.use_intent_detection = False
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.reranker_initial_top_k = 20
        mock_settings.reranker_final_top_k = 5
        mock_settings.pinecone_api_key = "test"
        mock_settings.pinecone_index = "test"
        mock_settings.lapack_data_dir = "/tmp/test-data"
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

    async def test_query_with_reranker(self, patched_app, mock_searcher):
        async def fake_stream(question, searcher, top_k, prefetched_results=None):
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        with patch("backend.app.main.stream_query_response", side_effect=fake_stream), \
             patch("backend.app.main.rerank_results", new_callable=AsyncMock) as mock_rerank, \
             patch("backend.app.main.settings") as ms:
            ms.use_reranker = True
            ms.use_query_expansion = False
            ms.reranker_initial_top_k = 20
            ms.reranker_final_top_k = 5
            ms.cors_origins = ["http://localhost:5173"]
            mock_rerank.return_value = [_make_result()]

            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/query",
                    json={"question": "test", "stream": True},
                )
            assert resp.status_code == 200
            mock_rerank.assert_called_once()

    async def test_query_with_expansion(self, patched_app, mock_searcher):
        async def fake_stream(question, searcher, top_k, prefetched_results=None):
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        with patch("backend.app.main.stream_query_response", side_effect=fake_stream), \
             patch("backend.app.main.expand_query", return_value="expanded query") as mock_expand, \
             patch("backend.app.main.settings") as ms:
            ms.use_reranker = False
            ms.use_query_expansion = True
            ms.cors_origins = ["http://localhost:5173"]

            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/query",
                    json={"question": "LU decomposition", "stream": True},
                )
            assert resp.status_code == 200
            mock_expand.assert_called_once()


@pytest.mark.asyncio
class TestStatsEndpoint:

    async def test_stats_returns_index_info(self, patched_app):
        mock_stats = MagicMock()
        mock_stats.total_vector_count = 5000
        mock_stats.dimension = 1536
        mock_stats.namespaces = {}

        with patch("backend.app.main.Pinecone") as MockPC:
            mock_index = MagicMock()
            mock_index.describe_index_stats.return_value = mock_stats
            MockPC.return_value.Index.return_value = mock_index

            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vectors"] == 5000
        assert data["dimensions"] == 1536


@pytest.mark.asyncio
class TestFileContextEndpoint:

    async def test_valid_request(self, patched_app):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = os.path.join(tmpdir, "SRC", "dgesv.f")
            os.makedirs(os.path.dirname(test_file))
            with open(test_file, "w") as f:
                for i in range(100):
                    f.write(f"      LINE {i+1}\n")

            with patch("backend.app.main.settings") as ms:
                ms.lapack_data_dir = tmpdir
                ms.use_reranker = False
                ms.cors_origins = ["http://localhost:5173"]

                transport = ASGITransport(app=patched_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/file-context",
                        json={"file_path": "SRC/dgesv.f", "start_line": 10, "end_line": 20, "context_lines": 5},
                    )

            assert resp.status_code == 200
            data = resp.json()
            assert data["file_path"] == "SRC/dgesv.f"
            assert "content" in data

    async def test_file_not_found(self, patched_app):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("backend.app.main.settings") as ms:
                ms.lapack_data_dir = tmpdir
                ms.cors_origins = ["http://localhost:5173"]

                transport = ASGITransport(app=patched_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/file-context",
                        json={"file_path": "SRC/nonexistent.f", "start_line": 1},
                    )
            assert resp.status_code == 404

    async def test_path_traversal_blocked(self, patched_app):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("backend.app.main.settings") as ms:
                ms.lapack_data_dir = tmpdir
                ms.cors_origins = ["http://localhost:5173"]

                transport = ASGITransport(app=patched_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/file-context",
                        json={"file_path": "../../etc/passwd", "start_line": 1},
                    )
            assert resp.status_code == 400


@pytest.mark.asyncio
class TestSmartQueryEndpoint:

    async def test_explain_intent_returns_sse(self, patched_app, mock_searcher):
        async def fake_explain(query, searcher, top_k):
            yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        with patch("backend.app.main.stream_explanation", side_effect=fake_explain), \
             patch("backend.app.main.settings") as ms:
            ms.use_intent_detection = True
            ms.use_query_expansion = False
            ms.use_reranker = False
            ms.cors_origins = ["http://localhost:5173"]
            with patch("backend.app.main.detect_intent", return_value="explain"):
                transport = ASGITransport(app=patched_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/smart-query",
                        json={"question": "explain DGESV"},
                    )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

    async def test_search_intent_returns_json(self, patched_app, mock_searcher):
        with patch("backend.app.main.settings") as ms:
            ms.use_intent_detection = True
            ms.use_query_expansion = False
            ms.use_reranker = False
            ms.cors_origins = ["http://localhost:5173"]
            with patch("backend.app.main.detect_intent", return_value="search"):
                transport = ASGITransport(app=patched_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/smart-query",
                        json={"question": "find DGESV"},
                    )
            assert resp.status_code == 200
            data = resp.json()
            assert data["intent"] == "search"
            assert "results" in data


@pytest.mark.asyncio
class TestFeatureEndpoints:

    async def _test_feature_endpoint(self, patched_app, endpoint, mock_fn_path, mock_searcher):
        async def fake_feature(query, searcher, top_k):
            yield f"data: {json.dumps({'type': 'sources', 'data': []})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        with patch(mock_fn_path, side_effect=fake_feature):
            transport = ASGITransport(app=patched_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(endpoint, json={"query": "DGESV"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_explain_endpoint(self, patched_app, mock_searcher):
        await self._test_feature_endpoint(
            patched_app, "/api/explain",
            "backend.app.main.stream_explanation", mock_searcher,
        )

    async def test_docgen_endpoint(self, patched_app, mock_searcher):
        await self._test_feature_endpoint(
            patched_app, "/api/docgen",
            "backend.app.main.stream_documentation", mock_searcher,
        )

    async def test_patterns_endpoint(self, patched_app, mock_searcher):
        await self._test_feature_endpoint(
            patched_app, "/api/patterns",
            "backend.app.main.find_similar_patterns", mock_searcher,
        )

    async def test_dependencies_endpoint(self, patched_app, mock_searcher):
        await self._test_feature_endpoint(
            patched_app, "/api/dependencies",
            "backend.app.main.map_dependencies", mock_searcher,
        )

    async def test_business_logic_endpoint(self, patched_app, mock_searcher):
        await self._test_feature_endpoint(
            patched_app, "/api/business-logic",
            "backend.app.main.stream_business_logic", mock_searcher,
        )
