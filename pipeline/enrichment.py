"""
Orchestrates the full per-product pipeline:

RAW -> normalize -> gather evidence (+ correction memory) -> fuse/detect
contradiction -> validate -> compute confidence -> decide -> ProductResult

This is the module the Streamlit app calls. Every step is a plain function
from another pipeline module -- this file just wires them together and
builds the explainable ProductResult.
"""

from __future__ import annotations

from pipeline import confidence as confidence_mod
from pipeline import validation as validation_mod
from pipeline.contradiction import fuse_evidence
from pipeline.correction_memory import Correction, lookup_correction
from pipeline.evidence import gather_manufacturer_evidence
from pipeline.preprocessing import normalize_product_row
from pipeline.reference_data import ReferenceData
from pipeline.schemas import Evidence, EvidenceType, FieldResult, ProductResult, ValidationState
from pipeline.web_evidence import WebEvidenceProvider


def enrich_manufacturer_field(
    row: dict,
    ref: ReferenceData,
    corrections: list[Correction] | None = None,
    web_provider: WebEvidenceProvider | None = None,
) -> FieldResult:
    evidence = gather_manufacturer_evidence(row, ref)

    correction_applied = False
    correction = lookup_correction("manufacturer", row.get("mpn"), row.get("manufacturer"), corrections)
    if correction:
        evidence.append(Evidence(
            type=EvidenceType.CORRECTION_MEMORY,
            signal=f"A prior human correction for this MPN/manufacturer signature "
                   f"set manufacturer = '{correction.corrected_value}'",
            value=correction.corrected_value,
            strength=0.9,
        ))
        correction_applied = True

    # Optional live web evidence sourcing
    if web_provider and web_provider.enabled:
        try:
            web_results = web_provider.gather(
                row.get("manufacturer"), row.get("mpn"), row.get("description"),
            )
            web_evidence = web_provider.to_evidence(web_results)
            evidence.extend(web_evidence)
        except Exception:
            pass  # web evidence failures never break the pipeline

    fusion = fuse_evidence(evidence)

    validation = validation_mod.ValidationResult()
    if fusion.winning_value:
        has_web = any(e.type == EvidenceType.WEB_SOURCED for e in evidence)
        validation.source = ValidationState.PASSED if has_web else ValidationState.NOT_APPLICABLE

    conf = confidence_mod.compute_field_confidence(fusion, validation)
    decision = confidence_mod.decide(conf, fusion.is_conflict)
    reason = confidence_mod.reason_for(conf, decision, fusion, validation)

    return FieldResult(
        field="manufacturer",
        value=fusion.winning_value,
        confidence=conf,
        evidence=evidence,
        validation=validation,
        decision=decision,
        reason=reason,
        is_conflict=fusion.is_conflict,
        conflict_severity=fusion.conflict_severity,
        correction_applied=correction_applied,
    )


def enrich_brand_field(manufacturer_field: FieldResult, ref: ReferenceData) -> FieldResult:
    """Brand is derived from the resolved manufacturer record (they share
    the same master row), inheriting its confidence/evidence chain."""
    if not manufacturer_field.value:
        return FieldResult(
            field="brand", value=None, confidence=0.0,
            decision=manufacturer_field.decision, reason="No manufacturer resolved; brand cannot be derived.",
        )
    record = ref.manufacturer_index.get(manufacturer_field.value.strip().lower())
    brand_value = record.brand if record else None
    return FieldResult(
        field="brand",
        value=brand_value,
        confidence=manufacturer_field.confidence,
        evidence=manufacturer_field.evidence,
        validation=manufacturer_field.validation,
        decision=manufacturer_field.decision,
        reason="Derived from resolved manufacturer record." if brand_value else "Manufacturer resolved but brand unknown.",
        is_conflict=manufacturer_field.is_conflict,
        conflict_severity=manufacturer_field.conflict_severity,
        correction_applied=manufacturer_field.correction_applied,
    )


def enrich_category_field(row: dict) -> FieldResult:
    """Category currently passes through from input (no independent
    classifier is implemented) -- confidence reflects that it is an
    unvalidated input echo, not an inferred value."""
    value = row.get("category")
    if value:
        ev = [Evidence(EvidenceType.INPUT_FIELD, "Category taken directly from input field", value, 0.7)]
        conf = 0.7
        decision = confidence_mod.decide(conf, is_conflict=False)
        reason = "Category is passed through from the input catalog (no independent category classifier is implemented in this build)."
    else:
        ev = []
        conf = 0.0
        decision = confidence_mod.decide(conf, is_conflict=False)
        reason = "No category provided in input."
    return FieldResult(field="category", value=value, confidence=conf, evidence=ev, decision=decision, reason=reason)


def enrich_measurement_fields(row: dict, category: str | None, ref: ReferenceData) -> list[FieldResult]:
    """Turn extracted (raw_value, raw_unit) pairs into validated,
    normalized-format FieldResults, including the contextual anomaly guard."""
    results = []
    for i, m in enumerate(row.get("_measurements", [])):
        raw_value, raw_unit = m["raw_value"], m["raw_unit"]
        display, uom_note = validation_mod.normalize_uom(raw_value, raw_unit, ref)
        field_name = f"measurement_{i+1}"

        vr = validation_mod.ValidationResult()
        evidence = [Evidence(EvidenceType.INPUT_FIELD, f"Extracted from raw_specs: '{raw_value} {raw_unit}'", display or f"{raw_value} {raw_unit}", 0.85)]

        if uom_note:
            vr.uom = ValidationState.FAILED
            vr.notes.append(uom_note)
            conf = 0.3
        else:
            fmt_state, fmt_note = validation_mod.validate_uom_formatting(display)
            vr.uom = fmt_state
            if fmt_note:
                vr.notes.append(fmt_note)
            conf = 0.9 if fmt_state == ValidationState.PASSED else 0.5

        anomaly = validation_mod.check_contextual_anomaly(category, "weight", raw_value, raw_unit, ref=ref) if "lb" in raw_unit.lower() or "kg" in raw_unit.lower() else None
        if anomaly:
            vr.rules = ValidationState.FAILED
            vr.notes.append(anomaly)
            conf = min(conf, 0.2)

        decision = confidence_mod.decide(conf, is_conflict=False)
        reason = "; ".join(vr.notes) if vr.notes else "Extracted and normalized from input specs."

        results.append(FieldResult(
            field=field_name, value=display or f"{raw_value}{raw_unit}", confidence=conf,
            evidence=evidence, validation=vr, decision=decision, reason=reason,
        ))
    return results


def enrich_product(raw_row: dict, ref: ReferenceData, corrections: list[Correction] | None = None, web_provider: WebEvidenceProvider | None = None) -> ProductResult:
    normalized = normalize_product_row(raw_row)
    product_id = normalized.get("product_id") or "UNKNOWN_ID"

    manufacturer_field = enrich_manufacturer_field(normalized, ref, corrections, web_provider=web_provider)
    brand_field = enrich_brand_field(manufacturer_field, ref)
    category_field = enrich_category_field(normalized)
    measurement_fields = enrich_measurement_fields(normalized, category_field.value, ref)

    result = ProductResult(product_id=product_id, raw_input=raw_row)
    result.fields["manufacturer"] = manufacturer_field
    result.fields["brand"] = brand_field
    result.fields["category"] = category_field
    for mf in measurement_fields:
        result.fields[mf.field] = mf

    return result


def enrich_catalog(rows: list[dict], ref: ReferenceData, corrections: list[Correction] | None = None, web_provider: WebEvidenceProvider | None = None) -> list[ProductResult]:
    return [enrich_product(row, ref, corrections, web_provider=web_provider) for row in rows]
