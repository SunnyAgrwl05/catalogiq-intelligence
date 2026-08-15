import unittest

from pipeline.scalable_matcher import _similarity, batch_resolve, find_best_match


class TestSimilarity(unittest.TestCase):
    def test_identical_strings(self):
        self.assertAlmostEqual(_similarity("moen", "moen"), 1.0)

    def test_case_insensitive(self):
        self.assertAlmostEqual(_similarity("MOEN", "moen"), 1.0)

    def test_similar_strings(self):
        score = _similarity("moen", "moen incorporated")
        self.assertGreater(score, 0.8)

    def test_different_strings(self):
        score = _similarity("moen", "delta")
        self.assertLess(score, 0.7)

    def test_empty_strings(self):
        score = _similarity("", "")
        self.assertGreaterEqual(score, 0.0)

    def test_one_empty(self):
        score = _similarity("moen", "")
        self.assertLess(score, 0.5)


class TestFindBestMatch(unittest.TestCase):
    def setUp(self):
        self.candidates = {
            "moen": "record_moen",
            "delta": "record_delta",
            "kohler": "record_kohler",
        }

    def test_exact_match(self):
        record, score = find_best_match("moen", self.candidates)
        self.assertEqual(record, "record_moen")
        self.assertAlmostEqual(score, 1.0)

    def test_close_match(self):
        record, score = find_best_match("moen inc", self.candidates)
        self.assertIsNotNone(record)
        self.assertGreater(score, 0.8)

    def test_no_match_below_threshold(self):
        record, score = find_best_match("xyzzy", self.candidates, threshold=0.82)
        self.assertIsNone(record)

    def test_empty_candidates(self):
        record, score = find_best_match("moen", {})
        self.assertIsNone(record)

    def test_custom_threshold(self):
        record, score = find_best_match("moen", self.candidates, threshold=0.5)
        self.assertIsNotNone(record)


class TestBatchResolve(unittest.TestCase):
    def setUp(self):
        self.candidates = {
            "moen": "record_moen",
            "delta": "record_delta",
            "kohler": "record_kohler",
        }

    def test_batch_resolve(self):
        queries = ["moen", "delta", "kohler"]
        results = batch_resolve(queries, self.candidates)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "record_moen")
        self.assertEqual(results[1][0], "record_delta")
        self.assertEqual(results[2][0], "record_kohler")

    def test_batch_resolve_empty(self):
        results = batch_resolve([], self.candidates)
        self.assertEqual(results, [])

    def test_batch_resolve_mixed(self):
        queries = ["moen", "xyzzy", "delta"]
        results = batch_resolve(queries, self.candidates)
        self.assertEqual(len(results), 3)
        self.assertIsNotNone(results[0][0])
        self.assertIsNone(results[1][0])
        self.assertIsNotNone(results[2][0])

    def test_batch_resolve_ordering(self):
        queries = ["kohler", "delta", "moen"]
        results = batch_resolve(queries, self.candidates)
        self.assertEqual(results[0][0], "record_kohler")
        self.assertEqual(results[1][0], "record_delta")
        self.assertEqual(results[2][0], "record_moen")


class TestEntityResolutionWithScalableMatcher(unittest.TestCase):
    def test_import_does_not_fail(self):
        from pipeline.entity_resolution import resolve_manufacturer
        self.assertTrue(callable(resolve_manufacturer))


if __name__ == "__main__":
    unittest.main()
