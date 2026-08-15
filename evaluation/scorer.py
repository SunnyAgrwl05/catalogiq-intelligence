"""
Compares pipeline output against a ground-truth CSV and computes accuracy
metrics live. Nothing here is a hardcoded number -- every metric is
computed from the actual ProductResult objects passed in.

Ground truth CSV columns expected: product_id, manufacturer_expected,
brand_expected, category_expected (case-insensitive comparison after
whitespace normalization).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.schemas import ProductResult


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


@dataclass
class FieldAccuracy:
    field: str
    correct: int = 0
    incorrect: int = 0
    unknown_correctly_flagged: int = 0     # ground truth is UNKNOWN and system also said unknown/review
    total: int = 0

    # confusion matrix counts for the "unknown" positive class
    tp: int = 0  # true positive:  ground truth UNKNOWN  → predicted UNKNOWN
    fp: int = 0  # false positive: ground truth KNOWN    → predicted UNKNOWN
    fn: int = 0  # false negative: ground truth UNKNOWN  → predicted KNOWN
    tn: int = 0  # true negative:  ground truth KNOWN    → predicted KNOWN

    def accuracy(self) -> float:
        return (self.correct / self.total) if self.total else 0.0

    def precision(self) -> float:
        denom = self.tp + self.fp
        return (self.tp / denom) if denom else 0.0

    def recall(self) -> float:
        denom = self.tp + self.fn
        return (self.tp / denom) if denom else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return (2 * p * r / (p + r)) if (p + r) else 0.0


@dataclass
class ErrorCase:
    product_id: str
    field: str
    predicted: str | None
    expected: str
    confidence: float
    was_conflict: bool
    reason: str


@dataclass
class EvaluationReport:
    n_records: int
    field_accuracies: dict[str, FieldAccuracy] = field(default_factory=dict)
    overall_field_accuracy: float = 0.0
    error_cases: list[ErrorCase] = field(default_factory=list)
    auto_approved: int = 0
    review_required: int = 0
    investigate: int = 0
    conflict_count: int = 0
    avg_confidence: float = 0.0


def evaluate(results: list[ProductResult], ground_truth: list[dict]) -> EvaluationReport:
    gt_by_id = {row["product_id"]: row for row in ground_truth}
    field_map = {
        "manufacturer": "manufacturer_expected",
        "brand": "brand_expected",
        "category": "category_expected",
    }

    report = EvaluationReport(n_records=len(results))
    for pipeline_field in field_map:
        report.field_accuracies[pipeline_field] = FieldAccuracy(field=pipeline_field)

    confidences = []
    for product in results:
        gt_row = gt_by_id.get(product.product_id)
        d = product.overall_decision().value
        if d == "AUTO_APPROVED":
            report.auto_approved += 1
        elif d == "REVIEW_REQUIRED":
            report.review_required += 1
        else:
            report.investigate += 1
        report.conflict_count += product.conflict_count()

        if gt_row is None:
            continue

        for pipeline_field, gt_col in field_map.items():
            fr = product.fields.get(pipeline_field)
            if fr is None:
                continue
            expected = gt_row.get(gt_col, "")
            predicted = fr.value
            confidences.append(fr.confidence)

            acc = report.field_accuracies[pipeline_field]
            acc.total += 1

            expected_is_unknown = _norm(expected) == "unknown"
            predicted_is_unknown = predicted is None

            if expected_is_unknown and predicted_is_unknown:
                acc.unknown_correctly_flagged += 1
                acc.correct += 1
                acc.tp += 1
                continue

            if expected_is_unknown and not predicted_is_unknown:
                # ground truth UNKNOWN but system predicted a value
                acc.fn += 1
                acc.incorrect += 1
                report.error_cases.append(ErrorCase(
                    product_id=product.product_id,
                    field=pipeline_field,
                    predicted=predicted,
                    expected=expected,
                    confidence=fr.confidence,
                    was_conflict=fr.is_conflict,
                    reason=fr.reason,
                ))
                continue

            if not expected_is_unknown and predicted_is_unknown:
                # ground truth KNOWN but system predicted unknown
                acc.fp += 1
                acc.incorrect += 1
                report.error_cases.append(ErrorCase(
                    product_id=product.product_id,
                    field=pipeline_field,
                    predicted=predicted,
                    expected=expected,
                    confidence=fr.confidence,
                    was_conflict=fr.is_conflict,
                    reason=fr.reason,
                ))
                continue

            # both are known values
            if _norm(predicted) == _norm(expected):
                acc.correct += 1
                acc.tn += 1
            else:
                acc.incorrect += 1
                acc.tn += 1
                report.error_cases.append(ErrorCase(
                    product_id=product.product_id,
                    field=pipeline_field,
                    predicted=predicted,
                    expected=expected,
                    confidence=fr.confidence,
                    was_conflict=fr.is_conflict,
                    reason=fr.reason,
                ))

    total_correct = sum(a.correct for a in report.field_accuracies.values())
    total_fields = sum(a.total for a in report.field_accuracies.values())
    report.overall_field_accuracy = (total_correct / total_fields) if total_fields else 0.0
    report.avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0

    return report


def error_category_summary(report: EvaluationReport, top_n: int = 5) -> list[tuple[str, int]]:
    """Group error cases by field to surface 'top error categories'."""
    counts: dict[str, int] = {}
    for e in report.error_cases:
        counts[e.field] = counts.get(e.field, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:top_n]


def manufacturer_confusion_pairs(report: EvaluationReport, top_n: int = 10) -> list[tuple[str, str, int]]:
    """Return the most frequent (expected, predicted) manufacturer pairs.

    Each entry is a tuple of (expected, predicted, count) sorted by
    count descending.  Only manufacturer-field errors are included.
    """
    pairs: dict[tuple[str, str], int] = {}
    for e in report.error_cases:
        if e.field != "manufacturer":
            continue
        key = (_norm(e.expected), _norm(e.predicted))
        pairs[key] = pairs.get(key, 0) + 1
    ranked = sorted(pairs.items(), key=lambda kv: kv[1], reverse=True)
    return [(exp, pred, count) for (exp, pred), count in ranked[:top_n]]
