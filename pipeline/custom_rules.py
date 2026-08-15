"""
Pluggable custom validation rules.

Allows users to provide a YAML or JSON configuration file containing
custom validation rules that are merged with the built-in reference data
at runtime. This lets operators add LOV lists, UOM entries, and
category-specific anomaly rules without modifying Python source code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class AnomalyRule:
    category: str
    attribute: str
    unit: str
    max_value: float
    message: str


@dataclass
class CustomRules:
    """User-provided rules merged on top of built-in reference data."""

    lov: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    uom: dict[str, tuple[str, str]] = field(default_factory=dict)
    anomaly_rules: list[AnomalyRule] = field(default_factory=list)


def load_rules_file(path: str) -> CustomRules:
    """Load a YAML or JSON rules configuration file.

    The file format is:

    ```yaml
    lov:
      "Faucets":
        Finish: ["Chrome", "Brushed Nickel", "Oil Rubbed Bronze"]

    uom:
      m:
        normalized: "m"
        template: "{value} m"

    anomaly_rules:
      - category: "Faucets"
        attribute: "weight"
        unit: "kg"
        max_value: 50
        message: "Faucet weight over {max_value} kg is unusual"
    ```

    Returns a ``CustomRules`` instance.  Raises ``ValueError`` if the file
    cannot be parsed or contains invalid structure.
    """
    if not os.path.exists(path):
        raise ValueError(f"Rules file not found: {path}")

    raw = _read_file(path)

    rules = CustomRules()

    # --- LOV ---
    for category, attrs in (raw.get("lov") or {}).items():
        if not isinstance(attrs, dict):
            continue
        for attribute, values in attrs.items():
            if not isinstance(values, list):
                continue
            key = (str(category), str(attribute))
            rules.lov.setdefault(key, set()).update(str(v) for v in values)

    # --- UOM ---
    for raw_form, entry in (raw.get("uom") or {}).items():
        if not isinstance(entry, dict):
            continue
        normalized = str(entry.get("normalized", "")).strip()
        template = str(entry.get("template", "")).strip()
        if normalized and template:
            rules.uom[str(raw_form).strip().lower()] = (normalized, template)

    # --- Anomaly rules ---
    for ar in (raw.get("anomaly_rules") or []):
        if not isinstance(ar, dict):
            continue
        try:
            rules.anomaly_rules.append(
                AnomalyRule(
                    category=str(ar["category"]),
                    attribute=str(ar["attribute"]),
                    unit=str(ar["unit"]),
                    max_value=float(ar["max_value"]),
                    message=str(ar.get("message", "Anomaly detected: value exceeds {max_value} {unit}")),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    return rules


def merge_custom_rules_into_ref(ref, custom: CustomRules) -> None:
    """Merge custom rules into an existing ``ReferenceData`` instance.

    Mutates ``ref`` in-place:
    - LOV entries are added (or extended) on top of existing ones.
    - UOM entries are added (or extended) on top of existing ones.
    - Anomaly rules are stored in ``ref._custom_anomaly_rules`` for the
      validation module to pick up.
    """
    for key, values in custom.lov.items():
        ref.lov.setdefault(key, set()).update(values)

    for raw_form, entry in custom.uom.items():
        ref.uom_map[raw_form] = entry

    # Store anomaly rules on the ref for check_contextual_anomaly to use.
    if not hasattr(ref, "_custom_anomaly_rules"):
        ref._custom_anomaly_rules = []
    ref._custom_anomaly_rules.extend(custom.anomaly_rules)


def _read_file(path: str) -> dict[str, Any]:
    """Read a YAML or JSON file and return its contents as a dict."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        data = yaml.safe_load(content)
    elif ext == ".json":
        data = json.loads(content)
    else:
        # Try YAML first, fall back to JSON
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = json.loads(content)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Rules file must contain a mapping at the top level, got {type(data).__name__}")
    return data
