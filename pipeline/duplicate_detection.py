"""
Catalog-wide duplicate product detection.

Identifies likely duplicate products within a single uploaded catalog
using resolved manufacturer, normalized MPN, and description similarity.
Returns candidate groups for human review rather than automatically
merging records.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from pipeline.schemas import ProductResult


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _mpn_norm(s: str | None) -> str:
    """Normalize MPN by stripping hyphens, spaces, and lowercasing."""
    return (s or "").strip().lower().replace("-", "").replace(" ", "")


def _desc_similarity(a: str | None, b: str | None) -> float:
    """Compute similarity between two description strings."""
    a = _norm(a) or ""
    b = _norm(b) or ""
    if not a and not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


@dataclass
class DuplicateCandidate:
    """A pair of products that may be duplicates."""
    product_a_id: str
    product_b_id: str
    similarity: float
    evidence: list[str] = field(default_factory=list)
    match_type: str = "combined"


@dataclass
class DuplicateGroup:
    """A group of products that may be duplicates of each other."""
    group_id: int
    product_ids: list[str] = field(default_factory=list)
    candidates: list[DuplicateCandidate] = field(default_factory=list)
    best_similarity: float = 0.0


def _exact_match_score(a: str | None, b: str | None) -> tuple[float, str]:
    """Check for exact match on a field. Returns (score, reason)."""
    a_norm = _norm(a)
    b_norm = _norm(b)
    if a_norm and b_norm and a_norm == b_norm:
        return 1.0, f"exact match on '{a_norm}'"
    return 0.0, ""


def _mpn_match_score(a: str | None, b: str | None) -> tuple[float, str]:
    """Check for normalized MPN match. Returns (score, reason)."""
    a_n = _mpn_norm(a)
    b_n = _mpn_norm(b)
    if a_n and b_n and a_n == b_n:
        return 1.0, f"MPN match: '{a}' = '{b}'"
    return 0.0, ""


def _manufacturer_match_score(a: str | None, b: str | None) -> tuple[float, str]:
    """Check for manufacturer match. Returns (score, reason)."""
    a_n = _norm(a)
    b_n = _norm(b)
    if a_n and b_n and a_n == b_n:
        return 1.0, f"manufacturer match: '{a_n}'"
    return 0.0, ""


def _description_match_score(a: str | None, b: str | None, threshold: float = 0.7) -> tuple[float, str]:
    """Compute description similarity. Returns (score, reason)."""
    sim = _desc_similarity(a, b)
    if sim >= threshold:
        return sim, f"description similarity: {sim:.2f}"
    return 0.0, ""


def compute_similarity(
    product_a: ProductResult,
    product_b: ProductResult,
    mpn_threshold: float = 0.7,
    desc_threshold: float = 0.7,
) -> DuplicateCandidate | None:
    """Compute duplicate similarity between two products.

    Uses a weighted combination of:
    - Manufacturer match (weight: 0.4)
    - MPN match (weight: 0.35)
    - Description similarity (weight: 0.25)

    Returns a DuplicateCandidate if similarity exceeds the minimum threshold,
    otherwise None.
    """
    raw_a = product_a.raw_input
    raw_b = product_b.raw_input

    evidence = []
    total_score = 0.0

    # Manufacturer
    mfg_score, mfg_reason = _manufacturer_match_score(
        raw_a.get("manufacturer"), raw_b.get("manufacturer")
    )
    if mfg_reason:
        evidence.append(mfg_reason)
    total_score += mfg_score * 0.4

    # MPN
    mpn_score, mpn_reason = _mpn_match_score(
        raw_a.get("mpn"), raw_b.get("mpn")
    )
    if mpn_reason:
        evidence.append(mpn_reason)
    total_score += mpn_score * 0.35

    # Description
    desc_score, desc_reason = _description_match_score(
        raw_a.get("description"), raw_b.get("description"), desc_threshold
    )
    if desc_reason:
        evidence.append(desc_reason)
    total_score += desc_score * 0.25

    # If no evidence at all, not a candidate
    if not evidence:
        return None

    # Only return if there's meaningful signal
    if total_score < 0.3:
        return None

    return DuplicateCandidate(
        product_a_id=product_a.product_id,
        product_b_id=product_b.product_id,
        similarity=round(total_score, 4),
        evidence=evidence,
    )


def detect_duplicates(
    results: list[ProductResult],
    similarity_threshold: float = 0.5,
) -> list[DuplicateGroup]:
    """Scan a catalog for candidate duplicate products.

    Compares every pair of products and groups those with similarity
    above the threshold into DuplicateGroups.

    Returns a list of DuplicateGroup, sorted by best_similarity descending.
    """
    n = len(results)
    candidates: list[DuplicateCandidate] = []

    for i in range(n):
        for j in range(i + 1, n):
            candidate = compute_similarity(results[i], results[j])
            if candidate and candidate.similarity >= similarity_threshold:
                candidates.append(candidate)

    # Group candidates using simple union-find
    parent: dict[str, str] = {}
    for r in results:
        parent[r.product_id] = r.product_id

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for c in candidates:
        union(c.product_a_id, c.product_b_id)

    # Collect groups
    groups_map: dict[str, list[str]] = {}
    for r in results:
        root = find(r.product_id)
        groups_map.setdefault(root, []).append(r.product_id)

    # Build DuplicateGroups (only groups with 2+ members)
    groups = []
    group_id = 0
    for root, members in groups_map.items():
        if len(members) < 2:
            continue
        group_candidates = [
            c for c in candidates
            if c.product_a_id in members and c.product_b_id in members
        ]
        best_sim = max((c.similarity for c in group_candidates), default=0.0)
        groups.append(DuplicateGroup(
            group_id=group_id,
            product_ids=members,
            candidates=group_candidates,
            best_similarity=best_sim,
        ))
        group_id += 1

    groups.sort(key=lambda g: g.best_similarity, reverse=True)
    return groups
