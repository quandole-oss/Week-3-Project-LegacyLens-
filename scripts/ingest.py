#!/usr/bin/env python3
"""CLI script to run the LegacyLens ingestion pipeline.

Usage:
    python -m scripts.ingest [--data-dir DATA_DIR]
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.app.ingestion.pipeline import run_ingestion


def main():
    parser = argparse.ArgumentParser(description="Run LegacyLens ingestion pipeline")
    parser.add_argument(
        "--data-dir",
        default="data/lapack",
        help="Path to LAPACK source directory (default: data/lapack)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"Error: Data directory '{args.data_dir}' not found.")
        print("Please clone LAPACK first:")
        print("  git clone https://github.com/Reference-LAPACK/lapack.git data/lapack")
        sys.exit(1)

    result = run_ingestion(data_dir=args.data_dir)
    print(f"\nSummary: {result}")


if __name__ == "__main__":
    main()
