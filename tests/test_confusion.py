import unittest

from evaluation.scorer import ErrorCase, EvaluationReport, manufacturer_confusion_pairs


def _make_report(error_cases: list[ErrorCase]) -> EvaluationReport:
    return EvaluationReport(n_records=0, error_cases=error_cases)


class TestManufacturerConfusionPairs(unittest.TestCase):
    def test_empty_report(self):
        report = _make_report([])
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(result, [])

    def test_single_manufacturer_error(self):
        errors = [ErrorCase(
            product_id="P1", field="manufacturer",
            predicted="Delta", expected="Moen",
            confidence=0.8, was_conflict=False, reason="",
        )]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ("moen", "delta", 1))

    def test_repeated_confusion_pairs(self):
        errors = [
            ErrorCase(product_id="P1", field="manufacturer", predicted="Delta", expected="Moen", confidence=0.8, was_conflict=False, reason=""),
            ErrorCase(product_id="P2", field="manufacturer", predicted="Delta", expected="Moen", confidence=0.7, was_conflict=False, reason=""),
            ErrorCase(product_id="P3", field="manufacturer", predicted="Delta", expected="Moen", confidence=0.9, was_conflict=False, reason=""),
            ErrorCase(product_id="P4", field="manufacturer", predicted="Kohler", expected="Moen", confidence=0.6, was_conflict=False, reason=""),
        ]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("moen", "delta", 3))
        self.assertEqual(result[1], ("moen", "kohler", 1))

    def test_ignores_non_manufacturer_errors(self):
        errors = [
            ErrorCase(product_id="P1", field="brand", predicted="Delta", expected="Moen", confidence=0.8, was_conflict=False, reason=""),
            ErrorCase(product_id="P2", field="category", predicted="Sinks", expected="Faucets", confidence=0.7, was_conflict=False, reason=""),
        ]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(result, [])

    def test_top_n_limits_results(self):
        errors = [
            ErrorCase(product_id=f"P{i}", field="manufacturer", predicted=f"B{i}", expected="Moen", confidence=0.8, was_conflict=False, reason="")
            for i in range(20)
        ]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report, top_n=5)
        self.assertEqual(len(result), 5)

    def test_sorted_by_count_descending(self):
        errors = [
            ErrorCase(product_id="P1", field="manufacturer", predicted="Kohler", expected="Moen", confidence=0.8, was_conflict=False, reason=""),
            ErrorCase(product_id="P2", field="manufacturer", predicted="Delta", expected="Moen", confidence=0.7, was_conflict=False, reason=""),
            ErrorCase(product_id="P3", field="manufacturer", predicted="Delta", expected="Moen", confidence=0.9, was_conflict=False, reason=""),
        ]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(result[0][2], 2)  # Delta -> Moen has count 2
        self.assertEqual(result[1][2], 1)  # Kohler -> Moen has count 1

    def test_normalizes_values(self):
        errors = [ErrorCase(
            product_id="P1", field="manufacturer",
            predicted="  Delta  ", expected="  Moen  ",
            confidence=0.8, was_conflict=False, reason="",
        )]
        report = _make_report(errors)
        result = manufacturer_confusion_pairs(report)
        self.assertEqual(result[0], ("moen", "delta", 1))


if __name__ == "__main__":
    unittest.main()
