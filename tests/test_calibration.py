import unittest

from evaluation.scorer import (
    CalibrationReport,
    ConfidenceBucket,
    calibration_report,
    evaluate,
)
from pipeline.schemas import (
    Decision,
    Evidence,
    EvidenceType,
    FieldResult,
    ProductResult,
    ValidationResult,
)


def _make_product(product_id: str, field: str, value: str, confidence: float) -> ProductResult:
    """Helper to build a ProductResult with a single field."""
    fr = FieldResult(
        field=field, value=value, confidence=confidence,
        evidence=[], validation=ValidationResult(),
        decision=Decision.AUTO_APPROVED, reason="",
    )
    return ProductResult(
        product_id=product_id,
        raw_input={"product_id": product_id},
        fields={field: fr},
    )


class TestCalibrationBuckets(unittest.TestCase):
    def test_bucket_mid(self):
        b = ConfidenceBucket(lower=0.5, upper=0.6, count=10, correct=8)
        self.assertAlmostEqual(b.mid, 0.55)

    def test_bucket_observed_accuracy(self):
        b = ConfidenceBucket(lower=0.0, upper=0.1, count=10, correct=7)
        self.assertAlmostEqual(b.observed_accuracy, 0.7)

    def test_bucket_zero_count(self):
        b = ConfidenceBucket(lower=0.0, upper=0.1)
        self.assertAlmostEqual(b.observed_accuracy, 0.0)


class TestCalibrationReport(unittest.TestCase):
    def test_calibration_with_known_data(self):
        ground_truth = [
            {"product_id": "P1", "manufacturer_expected": "Moen", "brand_expected": "Moen", "category_expected": "Faucets"},
            {"product_id": "P2", "manufacturer_expected": "Delta", "brand_expected": "Delta", "category_expected": "Faucets"},
            {"product_id": "P3", "manufacturer_expected": "Kohler", "brand_expected": "Kohler", "category_expected": "Sinks"},
            {"product_id": "P4", "manufacturer_expected": "Moen", "brand_expected": "Moen", "category_expected": "Faucets"},
        ]
        results = [
            _make_product("P1", "manufacturer", "Moen", 0.95),
            _make_product("P2", "manufacturer", "Delta", 0.90),
            _make_product("P3", "manufacturer", "Kohler", 0.92),
            _make_product("P4", "manufacturer", "Moen", 0.88),
        ]
        cal = calibration_report(results, ground_truth)
        self.assertIsInstance(cal, CalibrationReport)
        self.assertEqual(cal.total_predictions, 4)
        self.assertEqual(len(cal.buckets), 10)

    def test_calibration_empty_when_no_ground_truth(self):
        results = [_make_product("P1", "manufacturer", "Moen", 0.95)]
        cal = calibration_report(results, [])
        self.assertEqual(cal.total_predictions, 0)
        self.assertEqual(len(cal.buckets), 10)

    def test_calibration_empty_when_no_results(self):
        ground_truth = [{"product_id": "P1", "manufacturer_expected": "Moen"}]
        cal = calibration_report([], ground_truth)
        self.assertEqual(cal.total_predictions, 0)

    def test_calibration_distributes_into_buckets(self):
        ground_truth = [
            {"product_id": f"P{i}", "manufacturer_expected": "X", "brand_expected": "X", "category_expected": "X"}
            for i in range(20)
        ]
        results = [
            _make_product(f"P{i}", "manufacturer", "X", i / 20.0)
            for i in range(20)
        ]
        cal = calibration_report(results, ground_truth)
        non_empty = [b for b in cal.buckets if b.count > 0]
        self.assertTrue(len(non_empty) >= 1)

    def test_calibration_mae_is_bounded(self):
        ground_truth = [{"product_id": "P1", "manufacturer_expected": "Moen"}]
        results = [_make_product("P1", "manufacturer", "Moen", 0.55)]
        cal = calibration_report(results, ground_truth)
        self.assertGreaterEqual(cal.mean_absolute_error, 0.0)
        self.assertLessEqual(cal.mean_absolute_error, 1.0)

    def test_calibration_mae_positive_when_miscalibrated(self):
        ground_truth = [{"product_id": "P1", "manufacturer_expected": "Moen"}]
        results = [_make_product("P1", "manufacturer", "Moen", 0.9)]
        cal = calibration_report(results, ground_truth)
        self.assertGreater(cal.mean_absolute_error, 0.0)

    def test_calibration_includes_brand_and_category(self):
        ground_truth = [{"product_id": "P1", "manufacturer_expected": "Moen", "brand_expected": "Moen", "category_expected": "Faucets"}]
        fr_mfg = FieldResult(field="manufacturer", value="Moen", confidence=0.9, evidence=[], validation=ValidationResult(), decision=Decision.AUTO_APPROVED, reason="")
        fr_brand = FieldResult(field="brand", value="Moen", confidence=0.9, evidence=[], validation=ValidationResult(), decision=Decision.AUTO_APPROVED, reason="")
        fr_cat = FieldResult(field="category", value="Faucets", confidence=0.9, evidence=[], validation=ValidationResult(), decision=Decision.AUTO_APPROVED, reason="")
        product = ProductResult(product_id="P1", raw_input={}, fields={"manufacturer": fr_mfg, "brand": fr_brand, "category": fr_cat})
        cal = calibration_report([product], ground_truth)
        self.assertEqual(cal.total_predictions, 3)


class TestEvaluateIncludesCalibration(unittest.TestCase):
    def test_evaluate_populates_calibration(self):
        ground_truth = [{"product_id": "P1", "manufacturer_expected": "Moen"}]
        results = [_make_product("P1", "manufacturer", "Moen", 0.95)]
        report = evaluate(results, ground_truth)
        self.assertIsNotNone(report.calibration)
        self.assertEqual(report.calibration.total_predictions, 1)


if __name__ == "__main__":
    unittest.main()
