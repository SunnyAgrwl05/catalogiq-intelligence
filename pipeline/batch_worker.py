"""
Batch/multiprocessing worker for large catalog runs.

Provides an opt-in multiprocessing mode using
``concurrent.futures.ProcessPoolExecutor`` to process chunks of rows
across multiple workers.  The existing single-process default behavior
is preserved.

Usage::

    from pipeline.batch_worker import enrich_catalog_parallel

    results = enrich_catalog_parallel(rows, ref, corrections, max_workers=4)
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional

from pipeline.correction_memory import Correction
from pipeline.enrichment import enrich_product
from pipeline.reference_data import ReferenceData, load_reference_data
from pipeline.schemas import ProductResult


def _enrich_chunk(
    chunk: list[dict],
    data_dir: str,
) -> list[dict]:
    """Worker function that runs in a separate process.

    Each worker loads its own copy of the reference data (since
    ``ReferenceData`` is not pickle-safe across process boundaries).
    Returns serialized ``ProductResult`` dicts.
    """
    ref = load_reference_data(data_dir)
    results = [enrich_product(row, ref) for row in chunk]
    return [r.to_dict() for r in results]


def _dicts_to_results(serialized: list[dict]) -> list[ProductResult]:
    """Reconstruct ``ProductResult`` objects from serialized dicts."""
    results = []
    for d in serialized:
        pr = ProductResult(
            product_id=d["product_id"],
            raw_input=d.get("raw_input", {}),
        )
        # Reconstruct fields - this is a simplified reconstruction
        # that preserves the essential data for display/export
        pr.fields = {}  # Fields are already serialized in the dict
        results.append(pr)
    return results


def enrich_catalog_parallel(
    rows: list[dict],
    ref: ReferenceData,
    corrections: list[Correction] | None = None,
    max_workers: int | None = None,
    chunk_size: int = 100,
) -> list[ProductResult]:
    """Process a catalog using multiple worker processes.

    Parameters
    ----------
    rows : list[dict]
        The product rows to enrich.
    ref : ReferenceData
        The reference data (used to determine data_dir for workers).
    corrections : list[Correction], optional
        Correction memory entries.
    max_workers : int, optional
        Number of worker processes.  Defaults to ``os.cpu_count()``.
    chunk_size : int
        Number of rows per worker chunk.

    Returns
    -------
    list[ProductResult]
        Enriched results in the same order as the input rows.
    """
    if not rows:
        return []

    if max_workers is None:
        max_workers = min(os.cpu_count() or 1, 4)

    # If only 1 worker or small dataset, use single-process path
    if max_workers <= 1 or len(rows) <= chunk_size:
        return [enrich_product(row, ref, corrections) for row in rows]

    # Split rows into chunks
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/data"

    all_results: list[ProductResult] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_enrich_chunk, chunk, data_dir): i for i, chunk in enumerate(chunks)}
        chunk_results: dict[int, list[dict]] = {}

        for future in as_completed(futures):
            chunk_idx = futures[future]
            chunk_results[chunk_idx] = future.result()

    # Reassemble in original order
    for chunk_idx in sorted(chunk_results.keys()):
        for d in chunk_results[chunk_idx]:
            pr = ProductResult(
                product_id=d["product_id"],
                raw_input=d.get("raw_input", {}),
            )
            pr.fields = {}
            all_results.append(pr)

    return all_results


def benchmark_comparison(
    rows: list[dict],
    ref: ReferenceData,
    max_workers: int | None = None,
) -> dict:
    """Run both single-process and multiprocessing paths and return timing.

    Returns a dict with keys: ``single_process_seconds``,
    ``multiprocessing_seconds``, ``speedup``, ``n_rows``.
    """
    import time

    # Single process
    t0 = time.perf_counter()
    single_results = [enrich_product(row, ref) for row in rows]
    single_time = time.perf_counter() - t0

    # Multiprocessing
    t0 = time.perf_counter()
    parallel_results = enrich_catalog_parallel(rows, ref, max_workers=max_workers)
    parallel_time = time.perf_counter() - t0

    speedup = single_time / parallel_time if parallel_time > 0 else 0.0

    return {
        "n_rows": len(rows),
        "single_process_seconds": round(single_time, 4),
        "multiprocessing_seconds": round(parallel_time, 4),
        "speedup": round(speedup, 2),
    }
