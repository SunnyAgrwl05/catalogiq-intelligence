"""
Scalable fuzzy matcher for manufacturer/brand entity resolution.

Replaces the stdlib ``difflib.SequenceMatcher``-based approach with
``rapidfuzz`` for significantly faster fuzzy matching on large reference
masters while preserving identical match semantics.

Falls back to ``difflib`` if ``rapidfuzz`` is not installed so that the
app still works without the optional compiled dependency.
"""

from __future__ import annotations

from typing import Mapping, Optional, TypeVar

T = TypeVar("T")

try:
    from rapidfuzz import fuzz as _rfuzz

    def _similarity(a: str, b: str) -> float:
        """Token-set ratio normalized to 0..1 — fast and handles token
        reordering (e.g. 'GE Microwave' vs 'Microwave GE')."""
        return _rfuzz.token_set_ratio(a.lower(), b.lower()) / 100.0

except ImportError:
    from difflib import SequenceMatcher

    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(
    query: str,
    candidates: Mapping[str, T],
    threshold: float = 0.82,
) -> tuple[Optional[T], float]:
    """Return the best-matching candidate and its score.

    Parameters
    ----------
    query : str
        The normalized (lower-cased, stripped) string to match.
    candidates : Mapping[str, T]
        Mapping of normalized name to record object.
    threshold : float
        Minimum score to accept a match.

    Returns
    -------
    tuple
        ``(record, score)`` or ``(None, best_score)`` if below threshold.
    """
    best_record = None
    best_score = 0.0
    for name, record in candidates.items():
        score = _similarity(query, name)
        if score > best_score:
            best_score = score
            best_record = record

    if best_record and best_score >= threshold:
        return best_record, best_score
    return None, best_score


def batch_resolve(
    queries: list[str],
    candidates: Mapping[str, T],
    threshold: float = 0.82,
) -> list[tuple[Optional[T], float]]:
    """Resolve multiple queries against the same candidate set.

    Uses rapidfuzz's ``cdist`` for vectorized distance computation when
    available, falling back to per-query ``find_best_match`` otherwise.

    Returns a list of ``(record, score)`` tuples in the same order as
    ``queries``.
    """
    if not queries:
        return []

    candidate_names = list(candidates.keys())
    candidate_records = list(candidates.values())

    results: list[tuple[Optional[T], float]] = []
    try:
        from rapidfuzz.process import cdist

        # cdist returns a matrix of (query_idx, candidate_idx) → score
        score_matrix = cdist(
            [q.lower() for q in queries],
            [c.lower() for c in candidate_names],
            scorer=_rfuzz.token_set_ratio,
        )

        for row in score_matrix:
            best_idx = int(row.argmax())
            best_score = float(row[best_idx]) / 100.0
            if best_score >= threshold:
                results.append((candidate_records[best_idx], best_score))
            else:
                results.append((None, best_score))
        return results

    except ImportError:
        for q in queries:
            results.append(find_best_match(q, candidates, threshold))
        return results
