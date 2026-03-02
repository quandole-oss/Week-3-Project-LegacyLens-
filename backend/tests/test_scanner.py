"""Tests for backend/app/ingestion/scanner.py — file discovery for LAPACK sources."""

import os
import tempfile
import pytest

from backend.app.ingestion.scanner import (
    detect_language,
    count_lines,
    scan_directory,
    SourceFile,
    FORTRAN_EXTENSIONS,
    EXCLUDE_DIRS,
)


class TestDetectLanguage:

    def test_dot_f_returns_f77(self):
        assert detect_language("SRC/dgesv.f") == "f77"

    def test_dot_f90_returns_f90(self):
        assert detect_language("SRC/dgesv.f90") == "f90"

    def test_dot_F_uppercase_returns_f77(self):
        assert detect_language("SRC/dgesv.F") == "f77"

    def test_dot_F90_uppercase_returns_f90(self):
        assert detect_language("SRC/dgesv.F90") == "f90"

    def test_unknown_extension_returns_f77(self):
        # .f extension not in .f90/.F90, so defaults to f77
        assert detect_language("SRC/dgesv.for") == "f77"


class TestCountLines:

    def test_normal_file(self, tmp_path):
        f = tmp_path / "test.f"
        f.write_text("line1\nline2\nline3\n")
        assert count_lines(str(f)) == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.f"
        f.write_text("")
        assert count_lines(str(f)) == 0

    def test_nonexistent_file(self):
        assert count_lines("/nonexistent/path/to/file.f") == 0

    def test_single_line_no_newline(self, tmp_path):
        f = tmp_path / "single.f"
        f.write_text("single line")
        assert count_lines(str(f)) == 1


class TestScanDirectory:

    def _create_lapack_tree(self, base_dir):
        """Helper to create a mock LAPACK directory structure."""
        src = os.path.join(base_dir, "SRC")
        os.makedirs(src)
        # Create Fortran files
        for name in ["dgesv.f", "dgetrf.f", "dlange.f90"]:
            path = os.path.join(src, name)
            with open(path, "w") as f:
                f.write(f"      SUBROUTINE {name.split('.')[0].upper()}(N)\n      END\n")
        return src

    def test_discovers_fortran_files(self):
        with tempfile.TemporaryDirectory() as base_dir:
            self._create_lapack_tree(base_dir)
            results = scan_directory(base_dir)
            assert len(results) == 3
            assert all(isinstance(r, SourceFile) for r in results)

    def test_excludes_non_fortran_files(self):
        with tempfile.TemporaryDirectory() as base_dir:
            src = os.path.join(base_dir, "SRC")
            os.makedirs(src)
            # Fortran file
            with open(os.path.join(src, "dgesv.f"), "w") as f:
                f.write("      SUBROUTINE DGESV(N)\n      END\n")
            # Non-Fortran files
            with open(os.path.join(src, "util.c"), "w") as f:
                f.write("int main() {}")
            with open(os.path.join(src, "readme.txt"), "w") as f:
                f.write("readme")

            results = scan_directory(base_dir)
            assert len(results) == 1
            assert results[0].relative_path.endswith(".f")

    def test_excludes_testing_dirs(self):
        with tempfile.TemporaryDirectory() as base_dir:
            src = os.path.join(base_dir, "SRC")
            os.makedirs(src)
            testing_dir = os.path.join(src, "TESTING")
            os.makedirs(testing_dir)
            # Fortran file in SRC/
            with open(os.path.join(src, "dgesv.f"), "w") as f:
                f.write("      SUBROUTINE DGESV(N)\n      END\n")
            # Fortran file in SRC/TESTING/ — should be excluded
            with open(os.path.join(testing_dir, "test_dgesv.f"), "w") as f:
                f.write("      SUBROUTINE TEST_DGESV(N)\n      END\n")

            results = scan_directory(base_dir)
            assert len(results) == 1
            assert "TESTING" not in results[0].relative_path

    def test_missing_src_prints_warning_returns_empty(self, capsys):
        with tempfile.TemporaryDirectory() as base_dir:
            results = scan_directory(base_dir)
            assert len(results) == 0
            captured = capsys.readouterr()
            assert "Warning" in captured.out

    def test_results_sorted_by_relative_path(self):
        with tempfile.TemporaryDirectory() as base_dir:
            src = os.path.join(base_dir, "SRC")
            os.makedirs(src)
            for name in ["zgesv.f", "atest.f", "dgesv.f"]:
                with open(os.path.join(src, name), "w") as f:
                    f.write(f"      SUBROUTINE {name.split('.')[0].upper()}(N)\n      END\n")

            results = scan_directory(base_dir)
            paths = [r.relative_path for r in results]
            assert paths == sorted(paths)

    def test_source_file_fields_populated(self):
        with tempfile.TemporaryDirectory() as base_dir:
            src = os.path.join(base_dir, "SRC")
            os.makedirs(src)
            content = "      SUBROUTINE DGESV(N)\n      INTEGER N\n      END\n"
            with open(os.path.join(src, "dgesv.f"), "w") as f:
                f.write(content)

            results = scan_directory(base_dir)
            assert len(results) == 1
            sf = results[0]
            assert sf.relative_path == os.path.join("SRC", "dgesv.f")
            assert sf.line_count == 3
            assert sf.language == "f77"
            assert sf.size_bytes > 0
            assert os.path.isabs(sf.path)

    def test_scans_blas_src_dir(self):
        with tempfile.TemporaryDirectory() as base_dir:
            blas_src = os.path.join(base_dir, "BLAS", "SRC")
            os.makedirs(blas_src)
            with open(os.path.join(blas_src, "dgemm.f"), "w") as f:
                f.write("      SUBROUTINE DGEMM(N)\n      END\n")

            results = scan_directory(base_dir)
            assert len(results) == 1
            assert "BLAS" in results[0].relative_path
