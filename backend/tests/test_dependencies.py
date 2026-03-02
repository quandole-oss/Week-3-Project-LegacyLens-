"""Tests for backend/app/features/dependencies.py — dependency mapping."""

import json
import pytest
from unittest.mock import MagicMock

from backend.app.features.dependencies import (
    CALL_PATTERN,
    EXTERNAL_PATTERN,
    extract_dependencies,
    map_dependencies,
)
from backend.app.retrieval.search import SearchResult


def _make_result(name: str = "DGESV", score: float = 0.9, text: str = None) -> SearchResult:
    default_text = (
        "      SUBROUTINE DGESV(N)\n"
        "      EXTERNAL DGETRF, DGETRS, XERBLA\n"
        "      CALL DGETRF(N, N, A, LDA, IPIV, INFO)\n"
        "      CALL DGETRS('N', N, 1, A, LDA, IPIV, B, LDB, INFO)\n"
        "      END\n"
    )
    return SearchResult(
        text=text or default_text,
        file_path=f"SRC/{name.lower()}.f",
        routine_name=name,
        routine_type="subroutine",
        start_line=1,
        end_line=5,
        language="f77",
        score=score,
    )


class TestCallPattern:

    def test_matches_call_uppercase(self):
        match = CALL_PATTERN.search("      CALL DGETRF(N)")
        assert match is not None
        assert match.group(1) == "DGETRF"

    def test_matches_call_lowercase(self):
        match = CALL_PATTERN.search("      call dgetrs(n)")
        assert match is not None
        assert match.group(1) == "dgetrs"

    def test_matches_call_xerbla(self):
        match = CALL_PATTERN.search("      CALL XERBLA('DGESV', INFO)")
        assert match is not None
        assert match.group(1) == "XERBLA"

    def test_no_match_comment_line(self):
        # CALL inside a comment — the pattern still matches because it
        # doesn't filter comments, but extract_dependencies shows real behavior
        code = "C     This calls DGETRF"
        matches = list(CALL_PATTERN.finditer(code))
        # Pattern doesn't look for CALL keyword here — no "CALL" word
        assert len(matches) == 0


class TestExternalPattern:

    def test_matches_single_name(self):
        match = EXTERNAL_PATTERN.search("      EXTERNAL DGETRF")
        assert match is not None
        assert "DGETRF" in match.group(1)

    def test_matches_comma_separated(self):
        match = EXTERNAL_PATTERN.search("      EXTERNAL DGETRF, DGETRS, XERBLA")
        assert match is not None
        names = match.group(1)
        assert "DGETRF" in names
        assert "DGETRS" in names
        assert "XERBLA" in names


class TestExtractDependencies:

    def test_dgesv_sample(self):
        code = (
            "      SUBROUTINE DGESV(N)\n"
            "      EXTERNAL DGETRF, DGETRS, XERBLA\n"
            "      CALL DGETRF(N, N, A, LDA, IPIV, INFO)\n"
            "      CALL DGETRS('N', N, 1, A, LDA, IPIV, B, LDB, INFO)\n"
            "      END\n"
        )
        deps = extract_dependencies(code)
        assert "DGETRF" in deps["calls"]
        assert "DGETRS" in deps["calls"]
        assert deps["calls"] == sorted(deps["calls"])
        assert "DGETRF" in deps["externals"]
        assert "XERBLA" in deps["externals"]
        assert deps["externals"] == sorted(deps["externals"])

    def test_empty_code(self):
        deps = extract_dependencies("")
        assert deps["calls"] == []
        assert deps["externals"] == []

    def test_case_insensitive_uppercased_result(self):
        code = "      call dgetrf(n)\n      external dgetrs\n"
        deps = extract_dependencies(code)
        assert "DGETRF" in deps["calls"]
        assert "DGETRS" in deps["externals"]


@pytest.mark.asyncio
class TestMapDependencies:

    async def test_yields_dependencies_graph_done(self):
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [_make_result("DGESV")]

        events = []
        async for event in map_dependencies("DGESV", mock_searcher):
            events.append(event)

        assert len(events) == 3
        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events]
        assert parsed[0]["type"] == "dependencies"
        assert parsed[1]["type"] == "graph"
        assert parsed[2]["type"] == "done"

    async def test_no_results_yields_error(self):
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        events = []
        async for event in map_dependencies("NONEXISTENT", mock_searcher):
            events.append(event)

        assert len(events) == 1
        parsed = json.loads(events[0].replace("data: ", "").strip())
        assert parsed["type"] == "error"

    async def test_graph_keys_match_routine_names(self):
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [
            _make_result("DGESV"),
            _make_result("DGETRF", text="      SUBROUTINE DGETRF(N)\n      CALL XERBLA('DGETRF')\n      END\n"),
        ]

        events = []
        async for event in map_dependencies("DGESV", mock_searcher):
            events.append(event)

        graph_event = json.loads(events[1].replace("data: ", "").strip())
        graph = graph_event["data"]
        assert "DGESV" in graph
        assert "DGETRF" in graph
        assert "DGETRF" in graph["DGESV"]
        assert "XERBLA" in graph["DGETRF"]
