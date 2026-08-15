"""
LOV, UOM, and content-quality validation. This module never invents a
value -- it only checks a candidate value against reference rules and
returns pass/fail + human-readable notes.
"""

from __future__ import annotations

import re

from pipeline.preprocessing import is_placeholder
from pipeline.reference_data import ReferenceData
from pipeline.schemas import ValidationResult, ValidationState

MAX_DESCRIPTION_LENGTH = 500
MIN_DESCRIPTION_LENGTH = 10


def validate_lov(category: str, attribute: str, value: str | None, ref: ReferenceData) -> tuple[ValidationState, str | None]:
    key = (category, attribute)
    allowed = ref.lov.get(key)
    if allowed is None:
        return ValidationState.NOT_APPLICABLE, None
    if value is None:
        return ValidationState.NOT_APPLICABLE, None
    if value in allowed:
        return ValidationState.PASSED, None
    return ValidationState.FAILED, f"'{value}' is not an approved value for {category}/{attribute}"


def normalize_uom(raw_value: str, raw_unit: str, ref: ReferenceData) -> tuple[str | None, str | None]:
    """Return (normalized_display_string, note). E.g. ('24 in', None) or
    (None, 'unrecognized unit ...') if the unit isn't in the standards table."""
    entry = ref.uom_map.get(raw_unit.strip().lower())
    if entry is None:
        return None, f"Unrecognized unit '{raw_unit}' -- not in UOM standards table"
    normalized_unit, template = entry
    display = template.format(value=raw_value)
    return display, None


def validate_uom_formatting(display_value: str | None) -> tuple[ValidationState, str | None]:
    """Check the official formatting rule: '24 in' not '24in' (space
    required between number and unit)."""
    if re.match(r"^\d+(\.\d+)?[a-zA-Z%]", display_value or ""):
        return ValidationState.FAILED, f"'{display_value}' is missing required space between value and unit"
    return ValidationState.PASSED, None


def validate_description_quality(description: str | None) -> tuple[ValidationState, list[str]]:
    notes = []
    if description is None:
        return ValidationState.FAILED, ["Description is missing"]
    if is_placeholder(description):
        return ValidationState.FAILED, ["Description is a placeholder value"]
    if len(description) < MIN_DESCRIPTION_LENGTH:
        notes.append(f"Description shorter than {MIN_DESCRIPTION_LENGTH} chars")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        notes.append(f"Description exceeds {MAX_DESCRIPTION_LENGTH} char limit")
    return (ValidationState.FAILED if notes else ValidationState.PASSED), notes


def check_contextual_anomaly(category: str | None, attribute: str | None, raw_value: str | None, raw_unit: str | None, ref: ReferenceData | None = None) -> str | None:
    """Lightweight, rule-based anomaly guard. Only flags things a
    configured rule actually covers -- never claims physical impossibility
    beyond what's configured here."""
    if not (category and attribute and raw_value and raw_unit):
        return None
    try:
        val = float(raw_value)
    except ValueError:
        return None

    unit = raw_unit.strip().lower()
    attr = attribute.lower()

    # Built-in rule: faucet weight threshold
    if "faucet" in category.lower() and attr == "weight":
        if unit in ("kg",) and val >= 50:
            return f"CONTEXTUAL ANOMALY: {val} kg is an implausible weight for category '{category}' (rule: faucet weight < 50 kg)"
        if unit in ("lb", "lbs", "pound", "pounds") and val >= 110:
            return f"CONTEXTUAL ANOMALY: {val} lb is an implausible weight for category '{category}' (rule: faucet weight < 110 lb)"

    # Custom anomaly rules from user-provided rules file
    for ar in getattr(ref, "_custom_anomaly_rules", []) if ref is not None else []:
        if (
            ar.category.lower() in category.lower()
            and ar.attribute.lower() == attr
            and ar.unit.lower() == unit
            and val >= ar.max_value
        ):
            msg = ar.message.format(max_value=ar.max_value, unit=ar.unit)
            return f"CONTEXTUAL ANOMALY: {val} {ar.unit} -- {msg}"

    return None


def build_field_validation(
    category: str | None,
    attribute: str,
    value: str | None,
    ref: ReferenceData,
) -> ValidationResult:
    vr = ValidationResult()
    if category and value is not None:
        lov_state, lov_note = validate_lov(category, attribute, value, ref)
        vr.lov = lov_state
        if lov_note:
            vr.notes.append(lov_note)
    return vr
