"""
Builds the evidence list for the manufacturer/brand field by running every
available resolver (input field, MPN prefix, description mention) and
converting each into an Evidence object. This module does NOT decide the
final value -- that fusion + conflict logic lives in contradiction.py and
confidence.py. This module only *collects* signals.
"""

from __future__ import annotations

from pipeline.entity_resolution import resolve_from_description, resolve_manufacturer, resolve_mpn
from pipeline.reference_data import ReferenceData
from pipeline.schemas import Evidence, EvidenceType


def gather_manufacturer_evidence(row: dict, ref: ReferenceData) -> list[Evidence]:
    """Collect one Evidence item per resolver that found something.

    row is expected to already be normalized (preprocessing.normalize_product_row).
    """
    evidence: list[Evidence] = []

    # Signal 1: the input's own manufacturer field, resolved against the master
    mfg_match = resolve_manufacturer(row.get("manufacturer"), ref)
    if mfg_match.record:
        evidence.append(Evidence(
            type=EvidenceType.INPUT_FIELD,
            signal=f"Input manufacturer field '{row.get('manufacturer')}' "
                   f"matched via {mfg_match.match_type} match",
            value=mfg_match.record.manufacturer,
            strength=mfg_match.score,
        ))

    # Signal 2: MPN prefix lookup
    mpn_match = resolve_mpn(row.get("mpn"), ref)
    if mpn_match.record:
        evidence.append(Evidence(
            type=EvidenceType.MPN_PATTERN,
            signal=f"MPN '{row.get('mpn')}' matches known prefix pattern for "
                   f"{mpn_match.record.manufacturer}",
            value=mpn_match.record.manufacturer,
            strength=mpn_match.score,
        ))

    # Signal 3: description mention
    desc_match = resolve_from_description(row.get("description"), ref)
    if desc_match.record:
        evidence.append(Evidence(
            type=EvidenceType.DESCRIPTION,
            signal=f"Description text mentions '{desc_match.record.brand}'",
            value=desc_match.record.manufacturer,
            strength=desc_match.score,
        ))

    return evidence
