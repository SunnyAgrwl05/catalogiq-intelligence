"""
Contradiction / consensus detection.

This is deliberately NOT "average all the evidence strengths together."
It groups evidence by the *value* each signal points to, sums the
strength behind each candidate value, and compares the leader against
the runner-up. If they're close, that's a real disagreement between
signals (e.g. MPN says Moen, description says GE) and must be flagged
-- not silently blended into a mushy average.
"""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.schemas import Evidence

CONFLICT_MARGIN_THRESHOLD = 0.15  # if leader beats runner-up by less than this -> conflict


@dataclass
class FusionResult:
    winning_value: str | None
    winning_support: float          # summed strength behind the winner
    runner_up_value: str | None
    runner_up_support: float
    is_conflict: bool
    conflict_severity: float        # 0 (clear consensus) .. 1 (dead tie)
    grouped: dict[str, float]       # value -> summed strength, for the UI


def fuse_evidence(evidence: list[Evidence]) -> FusionResult:
    if not evidence:
        return FusionResult(None, 0.0, None, 0.0, is_conflict=False, conflict_severity=0.0, grouped={})

    grouped: dict[str, float] = {}
    for e in evidence:
        grouped[e.value] = grouped.get(e.value, 0.0) + e.strength

    ranked = sorted(grouped.items(), key=lambda kv: kv[1], reverse=True)
    winner_value, winner_support = ranked[0]

    if len(ranked) == 1:
        return FusionResult(
            winning_value=winner_value,
            winning_support=winner_support,
            runner_up_value=None,
            runner_up_support=0.0,
            is_conflict=False,
            conflict_severity=0.0,
            grouped=grouped,
        )

    runner_value, runner_support = ranked[1]
    margin = winner_support - runner_support
    # Normalize margin against total support so it's comparable across products.
    total_support = winner_support + runner_support
    normalized_margin = margin / total_support if total_support > 0 else 0.0

    is_conflict = normalized_margin < CONFLICT_MARGIN_THRESHOLD
    conflict_severity = max(0.0, 1.0 - normalized_margin) if is_conflict else 0.0

    return FusionResult(
        winning_value=winner_value,
        winning_support=winner_support,
        runner_up_value=runner_value,
        runner_up_support=runner_support,
        is_conflict=is_conflict,
        conflict_severity=round(conflict_severity, 3),
        grouped=grouped,
    )
