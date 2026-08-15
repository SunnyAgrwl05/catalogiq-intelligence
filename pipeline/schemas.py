"""
Core data model for CatalogIQ's Evidence Graph.

Every enriched field on every product is represented as a FieldResult:
a value, a confidence score, and the list of Evidence items that were
fused (or that conflicted) to produce it. Nothing in this module invents
data — it is pure structure. The pipeline modules populate it.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INVESTIGATE = "INVESTIGATE"


class ValidationState(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "n/a"


class EvidenceType(str, Enum):
    MPN_PATTERN = "mpn_pattern"
    DESCRIPTION = "description"
    REFERENCE_DATA = "reference_data"
    INPUT_FIELD = "input_field"
    CORRECTION_MEMORY = "correction_memory"
    CATEGORY_RULE = "category_rule"
    WEB_SOURCED = "web_sourced"


@dataclass
class Evidence:
    """A single signal that supports (or contradicts) a candidate value."""
    type: EvidenceType
    signal: str          # human-readable description of what was matched
    value: str            # the value this evidence points to
    strength: float        # 0..1, how strong/reliable this signal is

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "signal": self.signal,
            "value": self.value,
            "strength": round(self.strength, 3),
        }


@dataclass
class ValidationResult:
    lov: ValidationState = ValidationState.NOT_APPLICABLE
    uom: ValidationState = ValidationState.NOT_APPLICABLE
    rules: ValidationState = ValidationState.NOT_APPLICABLE
    source: ValidationState = ValidationState.NOT_APPLICABLE
    notes: list[str] = dataclass_field(default_factory=list)

    def all_passed(self) -> bool:
        states = [self.lov, self.uom, self.rules, self.source]
        return all(s != ValidationState.FAILED for s in states)

    def to_dict(self) -> dict:
        return {
            "lov": self.lov.value,
            "uom": self.uom.value,
            "rules": self.rules.value,
            "source": self.source.value,
            "notes": self.notes,
        }


@dataclass
class FieldResult:
    """The full, explainable result for a single field on a single product."""
    field: str
    value: Optional[str]
    confidence: float                      # 0..1
    evidence: list[Evidence] = dataclass_field(default_factory=list)
    validation: ValidationResult = dataclass_field(default_factory=ValidationResult)
    decision: Decision = Decision.INVESTIGATE
    reason: str = ""
    is_conflict: bool = False
    conflict_severity: float = 0.0          # 0..1, 0 = consensus
    correction_applied: bool = False

    def confidence_pct(self) -> str:
        return f"{self.confidence * 100:.1f}%"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "confidence_display": self.confidence_pct(),
            "evidence": [e.to_dict() for e in self.evidence],
            "validation": self.validation.to_dict(),
            "decision": self.decision.value,
            "reason": self.reason,
            "is_conflict": self.is_conflict,
            "conflict_severity": round(self.conflict_severity, 3),
            "correction_applied": self.correction_applied,
        }


@dataclass
class ProductResult:
    """All field results for one product, plus derived product-level trust."""
    product_id: str
    raw_input: dict
    fields: dict[str, FieldResult] = dataclass_field(default_factory=dict)

    def overall_trust(self) -> float:
        if not self.fields:
            return 0.0
        return sum(f.confidence for f in self.fields.values()) / len(self.fields)

    def overall_decision(self) -> Decision:
        """Product-level decision is the worst of its field-level decisions."""
        decisions = [f.decision for f in self.fields.values()]
        if any(d == Decision.INVESTIGATE for d in decisions):
            return Decision.INVESTIGATE
        if any(d == Decision.REVIEW_REQUIRED for d in decisions):
            return Decision.REVIEW_REQUIRED
        return Decision.AUTO_APPROVED

    def conflict_count(self) -> int:
        return sum(1 for f in self.fields.values() if f.is_conflict)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "raw_input": self.raw_input,
            "overall_trust": round(self.overall_trust(), 4),
            "overall_decision": self.overall_decision().value,
            "conflict_count": self.conflict_count(),
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
        }
