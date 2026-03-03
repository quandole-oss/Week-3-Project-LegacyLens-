#!/usr/bin/env python3
"""Precision@5 evaluation script for LegacyLens search endpoint.

Sends 10 test queries to /api/search (baseline) or /api/query (--reranked)
with top_k=5 and checks whether returned routine names fall within a
ground-truth set of relevant routines.
Computes per-query precision and average precision@5.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error

DEFAULT_API_BASE = "https://week-3-project-legacylens-production.up.railway.app"

# Each entry: (query, set of routine names considered relevant)
TEST_QUERIES: list[tuple[str, set[str]]] = [
    (
        "DGESV linear system solver",
        {
            "dgesv", "dgesvx", "dgesvxx", "dsgesv", "sgesv",
            "dgtsv", "dptsv", "dposv", "dsysv", "dgesc2", "dgetc2",
            "dgetrf", "dgetrs",
        },
    ),
    (
        "LU decomposition factorization",
        {
            "dgetrf", "dgetrf2", "dgetrs", "sgetrf", "zgetrf",
            "dgetf2", "dgetc2", "dgbtrf", "cgetrf",
        },
    ),
    (
        "eigenvalue solver symmetric",
        {
            "dsyev", "dsyevd", "dsyevr", "dsyevx", "ssyev",
            "dgeev", "dsyevd_2stage", "dsytrd_sb2st", "dsytrd",
            "dsteqr", "ssteqr", "dstebz",
        },
    ),
    (
        "QR factorization",
        {
            "dgeqrf", "dgeqr2", "dorgqr", "dormqr", "sgeqrf",
            "dgeqp3", "dgeqrt3", "dgeqrfp", "dggqrf", "dgeqrt",
        },
    ),
    (
        "singular value decomposition SVD",
        {
            "dgesvd", "dgesdd", "sgesvd", "dbdsqr", "dbdsdc",
            "dlasv2", "dlasdq", "slasdq", "slasv2", "dlas2",
            "dgesvdx", "dlasd0", "dlasd6",
        },
    ),
    (
        "DGEMM matrix multiply",
        {"dgemm", "sgemm", "zgemm", "cgemm", "dgemmtr", "dtrmm", "dsymm"},
    ),
    (
        "Cholesky factorization positive definite",
        {
            "dpotrf", "dpotrf2", "dpotrs", "spotrf", "dposv",
            "dpotf2", "dpbtrf", "dpptrf", "cpotrf",
        },
    ),
    (
        "DLANGE matrix norm",
        {
            "dlange", "slange", "zlange", "dlansy", "dlantr",
            "dlanhs", "dlansp", "dlanst", "dlansb", "clange",
            "dlassq", "dcombssq", "disnan",
        },
    ),
    (
        "XERBLA error handling",
        {"xerbla", "xerbla_array", "ilaenv", "ieeeck", "lsame"},
    ),
    (
        "tridiagonal system solver",
        {
            "dgtsv", "dgttrf", "dgttrs", "sgtsv", "dptsv",
            "dsteqr", "dgtts2", "cgtsv", "sgtts2", "dlagtf",
        },
    ),
]


def search_baseline(api_base: str, query: str, top_k: int = 5) -> list[dict]:
    """Send a search request to /api/search and return the results list."""
    url = f"{api_base}/api/search"
    payload = json.dumps({"query": query, "top_k": top_k}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"  ERROR: {exc}")
        return []


def search_reranked(api_base: str, query: str, top_k: int = 5) -> list[dict]:
    """Send a query request to /api/query (non-streaming) and return sources."""
    url = f"{api_base}/api/query"
    payload = json.dumps({
        "question": query,
        "top_k": top_k,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("sources", [])
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"  ERROR: {exc}")
        return []


def normalize(name: str) -> str:
    """Normalize a routine name for comparison."""
    return name.lower().strip().replace(".f", "").replace(".f90", "")


def run_eval(api_base: str, mode: str, search_fn) -> float:
    """Run all test queries and compute precision@5. Returns avg precision."""
    print("=" * 70)
    print(f"LegacyLens Precision@5 Evaluation  [{mode}]")
    print("=" * 70)
    print()

    total_precision = 0.0
    results_table: list[tuple[str, int, int, float]] = []

    for query, ground_truth in TEST_QUERIES:
        normalized_gt = {normalize(r) for r in ground_truth}
        results = search_fn(api_base, query, top_k=5)

        relevant = 0
        returned_names = []
        for r in results[:5]:
            name = r.get("routine_name", r.get("metadata", {}).get("routine_name", ""))
            returned_names.append(name)
            if normalize(name) in normalized_gt:
                relevant += 1

        precision = relevant / min(len(results), 5) if results else 0.0
        total_precision += precision
        results_table.append((query, relevant, min(len(results), 5), precision))

        print(f"Query: {query}")
        print(f"  Returned: {returned_names}")
        print(f"  Ground truth: {sorted(ground_truth)}")
        print(f"  Relevant: {relevant}/5  Precision: {precision:.0%}")
        print()

    avg_precision = total_precision / len(TEST_QUERIES) if TEST_QUERIES else 0.0

    print("=" * 70)
    print(f"SUMMARY  [{mode}]")
    print("=" * 70)
    print(f"{'Query':<45} {'Rel':>3} {'Ret':>3} {'P@5':>6}")
    print("-" * 60)
    for query, rel, ret, prec in results_table:
        print(f"{query[:44]:<45} {rel:>3} {ret:>3} {prec:>6.0%}")
    print("-" * 60)
    print(f"{'AVERAGE PRECISION@5':<45} {'':>3} {'':>3} {avg_precision:>6.0%}")
    print()

    return avg_precision


def evaluate() -> None:
    parser = argparse.ArgumentParser(description="LegacyLens Precision@5 Evaluation")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_BASE,
        help=f"Base URL of the API (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--reranked",
        action="store_true",
        help="Use /api/query (with re-ranking) instead of /api/search",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Run both baseline and reranked modes side-by-side",
    )
    args = parser.parse_args()

    if args.both:
        baseline_avg = run_eval(args.api_url, "baseline", search_baseline)
        print()
        reranked_avg = run_eval(args.api_url, "reranked", search_reranked)

        print("=" * 70)
        print("COMPARISON")
        print("=" * 70)
        print(f"  Baseline  precision@5: {baseline_avg:.0%}")
        print(f"  Reranked  precision@5: {reranked_avg:.0%}")
        delta = reranked_avg - baseline_avg
        print(f"  Delta:                 {delta:+.0%}")
        print()

        avg_precision = reranked_avg
    elif args.reranked:
        avg_precision = run_eval(args.api_url, "reranked", search_reranked)
    else:
        avg_precision = run_eval(args.api_url, "baseline", search_baseline)

    target = 0.70
    if avg_precision >= target:
        print(f"PASS: Average precision@5 = {avg_precision:.0%} (target >= {target:.0%})")
    else:
        print(f"FAIL: Average precision@5 = {avg_precision:.0%} (target >= {target:.0%})")
        sys.exit(1)


if __name__ == "__main__":
    evaluate()
