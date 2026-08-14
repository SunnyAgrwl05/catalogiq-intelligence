"""
Manufacturer / brand entity resolution and MPN-based candidate lookup.

Uses only the Python standard library (difflib) for fuzzy matching, so the
app has no hard dependency on a compiled fuzzy-matching library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from pipeline.reference_data import ManufacturerRecord, ReferenceData

FUZZY_MATCH_THRESHOLD = 0.82


@dataclass
class MatchResult:
    record: ManufacturerRecord | None
    match_type: str    # "exact" | "alias" | "fuzzy" | "none"
    score: float        # 0..1


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def resolve_manufacturer(name: str | None, ref: ReferenceData) -> MatchResult:
    """Resolve a free-text manufacturer/brand string against the master.

    Tries exact/alias index lookup first (fast, high precision), then
    falls back to fuzzy string matching against all known names.
    """
    if not name:
        return MatchResult(record=None, match_type="none", score=0.0)

    key = name.strip().lower()
    if key in ref.manufacturer_index:
        return MatchResult(record=ref.manufacturer_index[key], match_type="exact", score=1.0)

    # normalized match: strip common corporate suffixes
    stripped = key
    for suffix in [" inc.", " inc", " incorporated", " co.", " co", " company",
                    " llc", " corp.", " corp", " gmbh", " brands", " systems"]:
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)].strip()
    if stripped != key and stripped in ref.manufacturer_index:
        return MatchResult(record=ref.manufacturer_index[stripped], match_type="alias", score=0.97)

    # fuzzy match against all known names
    best_record = None
    best_score = 0.0
    for indexed_name, record in ref.manufacturer_index.items():
        score = _similarity(key, indexed_name)
        if score > best_score:
            best_score = score
            best_record = record

    if best_record and best_score >= FUZZY_MATCH_THRESHOLD:
        return MatchResult(record=best_record, match_type="fuzzy", score=best_score)

    return MatchResult(record=None, match_type="none", score=best_score)


def resolve_mpn(mpn: str | None, ref: ReferenceData) -> MatchResult:
    """Longest-prefix match of an MPN against the manufacturer master's
    known MPN prefixes. Deliberately conservative: an MPN prefix alone is
    treated as one signal, never as a standalone identification."""
    if not mpn:
        return MatchResult(record=None, match_type="none", score=0.0)

    mpn_clean = mpn.strip().upper()
    best_prefix = None
    for prefix, record in ref.mpn_prefix_index.items():
        if mpn_clean.startswith(prefix) and (best_prefix is None or len(prefix) > len(best_prefix)):
            best_prefix = prefix
            best_record = record

    if best_prefix:
        # Longer, more specific prefixes are more trustworthy signals.
        score = min(0.6 + 0.05 * len(best_prefix), 0.95)
        return MatchResult(record=best_record, match_type="mpn_prefix", score=score)

    return MatchResult(record=None, match_type="none", score=0.0)


def resolve_from_description(description: str | None, ref: ReferenceData) -> MatchResult:
    """Look for a known manufacturer/brand name mentioned inside free-text
    description. This is a weaker signal than a direct manufacturer field
    match because descriptions can reference a *compatible* brand rather
    than the actual manufacturer."""
    if not description:
        return MatchResult(record=None, match_type="none", score=0.0)

    desc_lower = description.lower()
    best_record = None
    best_len = 0
    for name, record in ref.manufacturer_index.items():
        if len(name) < 2:
            continue
        # Word-boundary match: avoids "ge" matching inside "large", while
        # still allowing short brand codes like "GE" to match as a whole word.
        pattern = r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])"
        if re.search(pattern, desc_lower) and len(name) > best_len:
            best_record = record
            best_len = len(name)

    if best_record:
        return MatchResult(record=best_record, match_type="description_mention", score=0.75)
    return MatchResult(record=None, match_type="none", score=0.0)
