"""File discovery for LAPACK source files."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceFile:
    path: str
    relative_path: str
    line_count: int
    language: str  # "f77" or "f90"
    size_bytes: int


INCLUDE_DIRS = ["SRC", "BLAS/SRC"]
EXCLUDE_DIRS = {"TESTING", "INSTALL", "CMAKE", "LAPACKE", "CBLAS"}
FORTRAN_EXTENSIONS = {".f", ".f90", ".F", ".F90"}


def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    return "f90" if ext in (".f90", ".F90") else "f77"


def count_lines(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def scan_directory(base_dir: str) -> list[SourceFile]:
    """Scan LAPACK directory for Fortran source files."""
    base_path = Path(base_dir)
    files = []

    for include_dir in INCLUDE_DIRS:
        scan_path = base_path / include_dir
        if not scan_path.exists():
            print(f"Warning: {scan_path} does not exist, skipping")
            continue

        for root, dirs, filenames in os.walk(scan_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for filename in filenames:
                filepath = os.path.join(root, filename)
                ext = Path(filename).suffix

                if ext not in FORTRAN_EXTENSIONS:
                    continue

                relative = os.path.relpath(filepath, base_dir)
                files.append(SourceFile(
                    path=filepath,
                    relative_path=relative,
                    line_count=count_lines(filepath),
                    language=detect_language(filepath),
                    size_bytes=os.path.getsize(filepath),
                ))

    files.sort(key=lambda f: f.relative_path)
    print(f"Discovered {len(files)} Fortran source files")
    return files
