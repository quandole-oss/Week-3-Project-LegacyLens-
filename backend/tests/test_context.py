"""Tests for context assembly from search results."""

import pytest
from backend.app.retrieval.context import assemble_context, format_sources
from backend.app.retrieval.search import SearchResult


def _make_result(name: str = "DGESV", score: float = 0.95) -> SearchResult:
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


class TestAssembleContext:
    """Test context string assembly for LLM input."""

    def test_includes_all_results(self):
        results = [_make_result("DGESV"), _make_result("DGETRF")]
        ctx = assemble_context(results)
        assert "DGESV" in ctx
        assert "DGETRF" in ctx

    def test_includes_metadata_header(self):
        results = [_make_result("DGESV", score=0.95)]
        ctx = assemble_context(results)
        assert "Source 1:" in ctx
        assert "SRC/dgesv.f" in ctx
        assert "subroutine: DGESV" in ctx
        assert "0.950" in ctx

    def test_respects_max_chunks(self):
        results = [_make_result(f"R{i}") for i in range(20)]
        ctx = assemble_context(results, max_chunks=3)
        assert "Source 1:" in ctx
        assert "Source 3:" in ctx
        assert "Source 4:" not in ctx

    def test_empty_results(self):
        ctx = assemble_context([])
        assert ctx == ""


class TestFormatSources:
    """Test source formatting for API responses."""

    def test_formats_source_fields(self):
        results = [_make_result("DGESV", score=0.9512)]
        sources = format_sources(results)
        assert len(sources) == 1
        s = sources[0]
        assert s["file_path"] == "SRC/dgesv.f"
        assert s["routine_name"] == "DGESV"
        assert s["routine_type"] == "subroutine"
        assert s["start_line"] == 1
        assert s["end_line"] == 3
        assert s["score"] == 0.9512

    def test_deduplicates_by_file_and_routine(self):
        results = [_make_result("DGESV"), _make_result("DGESV")]
        sources = format_sources(results)
        assert len(sources) == 1

    def test_respects_max_sources(self):
        results = [_make_result(f"R{i}") for i in range(10)]
        sources = format_sources(results, max_sources=3)
        assert len(sources) == 3

    def test_snippet_truncation(self):
        r = _make_result("DGESV")
        r.text = "X" * 600
        sources = format_sources([r])
        assert len(sources[0]["snippet"]) < 600
        assert sources[0]["snippet"].endswith("...")

    def test_empty_results(self):
        sources = format_sources([])
        assert sources == []
