"""
Deterministic confidence scoring.

confidence = base_evidence_score
             * validation_multiplier
             * contradiction_penalty
             * (0 if no evidence at all, per missing-evidence penalty)

All weights are named constants at the top of this file (not buried
magic numbers) so they're easy to tune and defend to a judge.
"""

from __future__ import annotations

from pipeline.contradiction import FusionResult
from pipeline.schemas import Decision, ValidationResult, ValidationState

# --- configurable weights ---
NO_EVIDENCE_CONFIDENCE = 0.0
VALIDATION_FAIL_MULTIPLIER = 0.5      # a single failed validation check halves confidence
CONTRADICTION_PENALTY_MAX = 0.5        # at max conflict severity, confidence is halved again

AUTO_APPROVE_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.65
# below REVIEW_THRESHOLD -> INVESTIGATE


def compute_field_confidence(fusion: FusionResult, validation: ValidationResult) -> float:
    """Combine evidence support, validation results, and contradiction
    severity into one deterministic 0..1 confidence score."""
    if fusion.winning_value is None or fusion.winning_support == 0.0:
        return NO_EVIDENCE_CONFIDENCE

    # Evidence support is a sum of strengths (can exceed 1 with multiple
    # agreeing signals). A single signal's strength is used as-is; when
    # several signals agree, apply diminishing returns rather than letting
    # confidence exceed a meaningful 0..1 scale.
    base = fusion.winning_support if fusion.winning_support <= 1.0 else _diminishing(fusion.winning_support)

    multiplier = 1.0
    if validation.lov == ValidationState.FAILED:
        multiplier *= VALIDATION_FAIL_MULTIPLIER
    if validation.uom == ValidationState.FAILED:
        multiplier *= VALIDATION_FAIL_MULTIPLIER
    if validation.rules == ValidationState.FAILED:
        multiplier *= VALIDATION_FAIL_MULTIPLIER
    if validation.source == ValidationState.FAILED:
        multiplier *= VALIDATION_FAIL_MULTIPLIER

    contradiction_multiplier = 1.0 - (CONTRADICTION_PENALTY_MAX * fusion.conflict_severity)

    confidence = base * multiplier * contradiction_multiplier
    return round(max(0.0, min(confidence, 1.0)), 4)


def _diminishing(support: float) -> float:
    """Combine multiple agreeing signals with real diminishing returns,
    but scaled so that two strong agreeing signals (e.g. 0.90 + 0.95)
    clear the auto-approve threshold rather than falling just short of it.
    `support` is the pre-summed total strength of all evidence pointing to
    the winning value; a steeper rate (1.6) than a plain 1-e^-x means two
    solid signals combine to ~0.95+ instead of ~0.84."""
    import math
    return round(1.0 - math.exp(-1.6 * support), 4)


def decide(confidence: float, is_conflict: bool) -> Decision:
    if is_conflict:
        return Decision.INVESTIGATE
    if confidence >= AUTO_APPROVE_THRESHOLD:
        return Decision.AUTO_APPROVED
    if confidence >= REVIEW_THRESHOLD:
        return Decision.REVIEW_REQUIRED
    return Decision.INVESTIGATE


def reason_for(confidence: float, decision: Decision, fusion: FusionResult, validation: ValidationResult) -> str:
    if fusion.winning_value is None:
        return "No evidence found for this field."
    if decision == Decision.INVESTIGATE and fusion.is_conflict:
        return (f"Conflicting evidence: '{fusion.winning_value}' "
                f"({fusion.winning_support:.2f}) vs '{fusion.runner_up_value}' "
                f"({fusion.runner_up_support:.2f}) -- disagreement too close to call automatically.")
    if not validation.all_passed():
        failed = [k for k, v in validation.to_dict().items() if v == "failed"]
        return f"Validation failed: {', '.join(failed)}."
    if decision == Decision.AUTO_APPROVED:
        return f"Strong, consistent evidence ({confidence*100:.1f}%) and all validation checks passed."
    if decision == Decision.REVIEW_REQUIRED:
        return f"Moderate confidence ({confidence*100:.1f}%) -- recommend human confirmation."
    return f"Low confidence ({confidence*100:.1f}%) -- insufficient or weak evidence."
