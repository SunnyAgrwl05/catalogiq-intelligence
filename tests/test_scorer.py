import unittest

from evaluation.scorer import (
    ErrorCase,
    EvaluationReport,
    FieldAccuracy,
    error_category_summary,
    evaluate,
)
from pipeline.schemas import Decision, FieldResult, ProductResult


class TestScorer(unittest.TestCase):
    def test_evaluate_perfect_match(self):
        product = ProductResult(
            product_id="P100",
            raw_input={},
            fields={
                "manufacturer": FieldResult(
                    field="manufacturer",
                    value="Moen Incorporated",
                    confidence=0.95,
                    decision=Decision.AUTO_APPROVED,
                ),
                "brand": FieldResult(
                    field="brand",
                    value="Moen",
                    confidence=0.90,
                    decision=Decision.AUTO_APPROVED,
                ),
                "category": FieldResult(
                    field="category",
                    value="Faucets",
                    confidence=0.88,
                    decision=Decision.AUTO_APPROVED,
                ),
            },
        )
        ground_truth = [
            {
                "product_id": "P100",
                "manufacturer_expected": "moen incorporated",
                "brand_expected": "MOEN",
                "category_expected": "Faucets",
            }
        ]

        report = evaluate([product], ground_truth)

        self.assertEqual(report.n_records, 1)
        self.assertEqual(report.overall_field_accuracy, 1.0)
        self.assertEqual(len(report.error_cases), 0)
        self.assertEqual(report.auto_approved, 1)
        self.assertEqual(report.review_required, 0)
        self.assertEqual(report.investigate, 0)
        self.assertAlmostEqual(report.avg_confidence, (0.95 + 0.90 + 0.88) / 3)

    def test_evaluate_with_mismatch(self):
        product = ProductResult(
            product_id="P101",
            raw_input={},
            fields={
                "manufacturer": FieldResult(
                    field="manufacturer",
                    value="Kohler Co.",
                    confidence=0.70,
                    decision=Decision.REVIEW_REQUIRED,
                    reason="Disagreement",
                    is_conflict=True,
                ),
                "brand": FieldResult(
                    field="brand",
                    value="Kohler",
                    confidence=0.90,
                    decision=Decision.REVIEW_REQUIRED,
                ),
            },
        )
        ground_truth = [
            {
                "product_id": "P101",
                "manufacturer_expected": "Delta Faucet",
                "brand_expected": "Kohler",
            }
        ]

        report = evaluate([product], ground_truth)

        self.assertEqual(len(report.error_cases), 1)
        error = report.error_cases[0]
        self.assertEqual(error.product_id, "P101")
        self.assertEqual(error.field, "manufacturer")
        self.assertEqual(error.predicted, "Kohler Co.")
        self.assertEqual(error.expected, "Delta Faucet")
        self.assertEqual(error.confidence, 0.70)
        self.assertTrue(error.was_conflict)
        self.assertEqual(error.reason, "Disagreement")

        acc = report.field_accuracies["manufacturer"]
        self.assertEqual(acc.correct, 0)
        self.assertEqual(acc.incorrect, 1)
        self.assertEqual(acc.accuracy(), 0.0)

    def test_expected_is_unknown_and_predicted_is_unknown(self):
        product = ProductResult(
            product_id="P102",
            raw_input={},
            fields={
                "manufacturer": FieldResult(
                    field="manufacturer",
                    value=None,
                    confidence=0.0,
                    decision=Decision.INVESTIGATE,
                ),
            },
        )
        ground_truth = [
            {
                "product_id": "P102",
                "manufacturer_expected": "UNKNOWN",
            }
        ]

        report = evaluate([product], ground_truth)

        acc = report.field_accuracies["manufacturer"]
        self.assertEqual(acc.unknown_correctly_flagged, 1)
        self.assertEqual(acc.correct, 1)
        self.assertEqual(acc.incorrect, 0)
        self.assertEqual(len(report.error_cases), 0)

    def test_missing_product_id_in_ground_truth(self):
        product = ProductResult(
            product_id="P103",
            raw_input={},
            fields={
                "manufacturer": FieldResult(
                    field="manufacturer",
                    value="Delta",
                    confidence=0.85,
                    decision=Decision.AUTO_APPROVED,
                ),
            },
        )
        ground_truth = []

        report = evaluate([product], ground_truth)

        self.assertEqual(report.n_records, 1)
        self.assertEqual(report.overall_field_accuracy, 0.0)
        self.assertEqual(len(report.error_cases), 0)
        self.assertEqual(report.auto_approved, 1)

    def test_error_category_summary_sorting_and_top_n(self):
        report = EvaluationReport(n_records=5)
        report.error_cases = [
            ErrorCase("P1", "brand", "A", "B", 0.5, False, ""),
            ErrorCase("P2", "manufacturer", "C", "D", 0.4, False, ""),
            ErrorCase("P3", "manufacturer", "E", "F", 0.3, False, ""),
            ErrorCase("P4", "manufacturer", "G", "H", 0.2, False, ""),
            ErrorCase("P5", "category", "I", "J", 0.1, False, ""),
            ErrorCase("P6", "brand", "K", "L", 0.6, False, ""),
        ]

        summary = error_category_summary(report, top_n=2)

        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0], ("manufacturer", 3))
        self.assertEqual(summary[1], ("brand", 2))

    def test_field_accuracy_zero_total(self):
        fa = FieldAccuracy(field="category")
        self.assertEqual(fa.accuracy(), 0.0)


if __name__ == "__main__":
    unittest.main()
