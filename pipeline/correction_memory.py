"""
Correction memory: a transparent, file-backed feedback log.

This is explicitly NOT a trained ML model. It's a lookup table: when a
human reviewer corrects a predicted field value for a given
(manufacturer_input, mpn) pair, that correction is stored. If a future
product shares the same (manufacturer_input, mpn) signature, the stored
correction is surfaced as an additional Evidence signal -- visibly
labeled as coming from correction memory, not from the base pipeline.
"""

from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "correction_memory.csv"
)

FIELDNAMES = [
    "timestamp", "product_id", "field", "mpn_signature", "manufacturer_input_signature",
    "predicted_value", "corrected_value", "reason",
]


@dataclass
class Correction:
    timestamp: str
    product_id: str
    field: str
    mpn_signature: str
    manufacturer_input_signature: str
    predicted_value: str
    corrected_value: str
    reason: str = ""


def _signature(value: str | None) -> str:
    return (value or "").strip().lower()


def record_correction(
    product_id: str,
    field: str,
    mpn: str | None,
    manufacturer_input: str | None,
    predicted_value: str | None,
    corrected_value: str,
    reason: str = "",
    path: str = MEMORY_PATH,
) -> Correction:
    correction = Correction(
        timestamp=datetime.now(timezone.utc).isoformat(),
        product_id=product_id,
        field=field,
        mpn_signature=_signature(mpn),
        manufacturer_input_signature=_signature(manufacturer_input),
        predicted_value=predicted_value or "",
        corrected_value=corrected_value,
        reason=reason,
    )
    file_exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(correction))
    return correction


def load_corrections(path: str = MEMORY_PATH) -> list[Correction]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [Correction(**row) for row in csv.DictReader(f)]


def lookup_correction(
    field: str,
    mpn: str | None,
    manufacturer_input: str | None,
    corrections: list[Correction] | None = None,
) -> Correction | None:
    """Find the most recent correction matching this field + MPN + input
    manufacturer signature. Returns None if no prior correction exists."""
    if corrections is None:
        corrections = load_corrections()
    mpn_sig = _signature(mpn)
    mfg_sig = _signature(manufacturer_input)
    matches = [
        c for c in corrections
        if c.field == field and c.mpn_signature == mpn_sig and c.manufacturer_input_signature == mfg_sig
        and mpn_sig  # require a non-empty MPN signature to avoid over-matching on blank/blank
    ]
    if not matches:
        return None
    return matches[-1]  # most recent
