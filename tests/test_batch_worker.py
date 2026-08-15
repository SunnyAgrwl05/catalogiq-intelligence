import unittest

from pipeline.batch_worker import (
    _enrich_chunk,
    _dicts_to_results,
    benchmark_comparison,
    enrich_catalog_parallel,
)
from pipeline.reference_data import load_reference_data


class TestEnrichChunk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = "/tmp/catalogiq-intelligence/data"

    def test_enrich_chunk_returns_dicts(self):
        rows = [{"product_id": "P1", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"}]
        result = _enrich_chunk(rows, self.data_dir)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(result[0]["product_id"], "P1")

    def test_enrich_chunk_empty(self):
        result = _enrich_chunk([], self.data_dir)
        self.assertEqual(result, [])

    def test_enrich_chunk_multiple_rows(self):
        rows = [
            {"product_id": "P1", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"},
            {"product_id": "P2", "manufacturer": "Delta", "mpn": "DL-5000", "description": "Shower"},
        ]
        result = _enrich_chunk(rows, self.data_dir)
        self.assertEqual(len(result), 2)


class TestDictsToResults(unittest.TestCase):
    def test_reconstructs_product_results(self):
        serialized = [
            {"product_id": "P1", "raw_input": {"manufacturer": "Moen"}},
            {"product_id": "P2", "raw_input": {"manufacturer": "Delta"}},
        ]
        results = _dicts_to_results(serialized)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].product_id, "P1")
        self.assertEqual(results[1].product_id, "P2")

    def test_empty_list(self):
        results = _dicts_to_results([])
        self.assertEqual(results, [])


class TestEnrichCatalogParallel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_parallel_returns_results(self):
        rows = [
            {"product_id": "P1", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"},
            {"product_id": "P2", "manufacturer": "Delta", "mpn": "DL-5000", "description": "Shower"},
        ]
        results = enrich_catalog_parallel(rows, self.ref, max_workers=2)
        self.assertEqual(len(results), 2)

    def test_parallel_empty_rows(self):
        results = enrich_catalog_parallel([], self.ref)
        self.assertEqual(results, [])

    def test_parallel_preserves_order(self):
        rows = [{"product_id": f"P{i}", "manufacturer": "Moen", "mpn": f"MN-{i}", "description": "Faucet"} for i in range(10)]
        results = enrich_catalog_parallel(rows, self.ref, max_workers=2, chunk_size=3)
        self.assertEqual(len(results), 10)
        for i, r in enumerate(results):
            self.assertEqual(r.product_id, f"P{i}")

    def test_parallel_single_worker(self):
        rows = [{"product_id": "P1", "manufacturer": "Moen", "mpn": "MN-7000", "description": "Faucet"}]
        results = enrich_catalog_parallel(rows, self.ref, max_workers=1)
        self.assertEqual(len(results), 1)

    def test_parallel_small_chunk_size(self):
        rows = [{"product_id": f"P{i}", "manufacturer": "Moen", "mpn": f"MN-{i}", "description": "Faucet"} for i in range(5)]
        results = enrich_catalog_parallel(rows, self.ref, max_workers=2, chunk_size=2)
        self.assertEqual(len(results), 5)


class TestBenchmarkComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_benchmark_returns_metrics(self):
        rows = [{"product_id": f"P{i}", "manufacturer": "Moen", "mpn": f"MN-{i}", "description": "Faucet"} for i in range(5)]
        result = benchmark_comparison(rows, self.ref, max_workers=2)
        self.assertIn("n_rows", result)
        self.assertIn("single_process_seconds", result)
        self.assertIn("multiprocessing_seconds", result)
        self.assertIn("speedup", result)
        self.assertEqual(result["n_rows"], 5)
        self.assertGreater(result["single_process_seconds"], 0)

    def test_benchmark_empty_rows(self):
        result = benchmark_comparison([], self.ref)
        self.assertEqual(result["n_rows"], 0)


if __name__ == "__main__":
    unittest.main()
