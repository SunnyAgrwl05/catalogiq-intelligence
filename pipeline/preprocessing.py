"""
Input normalization: whitespace cleanup, placeholder detection,
and turning free-text "raw_specs" into structured (value, unit) pairs.
"""

from __future__ import annotations

import re
from typing import Any

PLACEHOLDER_PATTERNS = [
    r"^--\s*unbranded\s*--$",
    r"^n/?a$",
    r"^unknown$",
    r"^none$",
    r"^tbd$",
    r"^\s*$",
    r"^null$",
    r"^-+$",
]
_PLACEHOLDER_RE = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    v = re.sub(r"\s+", " ", v)
    return v


def is_placeholder(value: str | None) -> bool:
    """Treat known placeholder strings ('-- Unbranded --', 'N/A', ...) as null."""
    if value is None:
        return True
    v = clean_text(value)
    if v is None:
        return True
    return bool(_PLACEHOLDER_RE.match(v))


def normalize_field(value: str | None) -> str | None:
    """Clean a text field and collapse placeholders to None (missing)."""
    v = clean_text(value)
    if is_placeholder(v):
        return None
    return v


# Matches things like "24in", "24 in", "3lb", "3 lb", "120v", "500w", "0.5 in"
_MEASURE_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>in\.?|inch(?:es)?|\"|lb\.?s?|pounds?|kg|gpm|gal/min|v(?:olts?)?|w(?:atts?)?)",
    re.IGNORECASE,
)


def extract_measurements(text: str | None) -> list[dict[str, str]]:
    """Pull (raw_value, raw_unit) pairs out of free-text spec strings.

    Returns a list of dicts: {"raw_value": "24", "raw_unit": "in"}.
    This does NOT normalize the unit -- that's validation.uom's job. This
    stage only extracts what's literally present in the text.
    """
    if not text:
        return []
    results: list[dict[str, str]] = []
    for m in _MEASURE_RE.finditer(text):
        results.append({"raw_value": m.group("value"), "raw_unit": m.group("unit")})
    return results


def normalize_product_row(row: dict[str, Any]) -> dict[str, Any]:
    """Apply text normalization + placeholder collapsing to a raw input row.

    Returns a new dict with the same keys, normalized. Fields that were
    placeholders become None. Nothing is invented here -- missing stays
    missing, per the content-quality rule.
    """
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if key in ("product_id",):
            normalized[key] = clean_text(value)
            continue
        normalized[key] = normalize_field(value)
    normalized["_measurements"] = extract_measurements(row.get("raw_specs"))
    return normalized
