"""
Benchmark: difflib vs rapidfuzz for manufacturer entity resolution.

Compares throughput and matching accuracy on the bundled synthetic
datasets.  Run with::

    python -m benchmarks.fuzzy_matcher_benchmark
"""

from __future__ import annotations

import csv
import os
import time
from difflib import SequenceMatcher
from typing import Optional

from pipeline.reference_data import load_reference_data

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_products(filename: str) -> list[dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return list(csv.DictReader(f))


def _similarity_difflib(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _resolve_difflib(
    queries: list[str],
    candidates: dict,
    threshold: float = 0.82,
) -> list[tuple[Optional[object], float]]:
    results = []
    for query in queries:
        best_record = None
        best_score = 0.0
        for name, record in candidates.items():
            score = _similarity_difflib(query, name)
            if score > best_score:
                best_score = score
                best_record = record
        if best_record and best_score >= threshold:
            results.append((best_record, best_score))
        else:
            results.append((None, best_score))
    return results


def _resolve_rapidfuzz(
    queries: list[str],
    candidates: dict,
    threshold: float = 0.82,
) -> list[tuple[Optional[object], float]]:
    from rapidfuzz import fuzz

    candidate_names = list(candidates.keys())
    candidate_records = list(candidates.values())

    results = []
    for query in queries:
        best_record = None
        best_score = 0.0
        for i, name in enumerate(candidate_names):
            score = fuzz.token_set_ratio(query.lower(), name.lower()) / 100.0
            if score > best_score:
                best_score = score
                best_record = candidate_records[i]
        if best_record and best_score >= threshold:
            results.append((best_record, best_score))
        else:
            results.append((None, best_score))
    return results


def run_benchmark(filename: str) -> dict:
    ref = load_reference_data()
    products = _load_products(filename)

    queries = [
        (p.get("manufacturer") or "").strip().lower()
        for p in products
        if p.get("manufacturer")
    ]
    candidates = ref.manufacturer_index

    # --- difflib ---
    t0 = time.perf_counter()
    difflib_results = _resolve_difflib(queries, candidates)
    difflib_time = time.perf_counter() - t0

    # --- rapidfuzz ---
    t0 = time.perf_counter()
    rf_results = _resolve_rapidfuzz(queries, candidates)
    rf_time = time.perf_counter() - t0

    # Accuracy: count agreements
    agreements = sum(
        1 for d, r in zip(difflib_results, rf_results)
        if (d[0] is None) == (r[0] is None) and
           (d[0] is None or d[0].manufacturer == r[0].manufacturer)
    )

    return {
        "file": filename,
        "n_queries": len(queries),
        "difflib_seconds": round(difflib_time, 4),
        "rapidfuzz_seconds": round(rf_time, 4),
        "speedup": round(difflib_time / rf_time, 2) if rf_time > 0 else 0,
        "agreement_pct": round(100 * agreements / len(queries), 1) if queries else 0,
    }


def main() -> None:
    files = ["sample_input.csv", "synthetic_scale_1000.csv"]
    print(f"{'File':<30} {'Rows':>6} {'difflib':>10} {'rapidfuzz':>10} {'Speedup':>8} {'Agree%':>7}")
    print("-" * 75)
    for f in files:
        if not os.path.exists(os.path.join(DATA_DIR, f)):
            print(f"  {f} not found, skipping")
            continue
        result = run_benchmark(f)
        print(
            f"{result['file']:<30} {result['n_queries']:>6} "
            f"{result['difflib_seconds']:>9.4f}s {result['rapidfuzz_seconds']:>9.4f}s "
            f"{result['speedup']:>7.1f}x {result['agreement_pct']:>6.1f}%"
        )


if __name__ == "__main__":
    main()
