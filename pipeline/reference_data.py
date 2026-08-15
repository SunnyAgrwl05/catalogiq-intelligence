"""
Loads and indexes the reference master data:
manufacturer/brand master, LOV master, UOM standards, decimal-fraction table.

NOTE ON DATA PROVENANCE:
The CSVs shipped in /data are a small SYNTHETIC reference set built to
demonstrate the pipeline end-to-end. They are NOT the official UniHack
reference files (Unicat LOV, UNILOG UOM standards, manufacturer/brand
master, etc). Drop the official files into /data with matching column
names (see README) and this loader will pick them up unchanged -- no
pipeline code needs to change.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@dataclass
class ManufacturerRecord:
    manufacturer: str
    brand: str
    aliases: list[str]
    mpn_prefixes: list[str]
    category_focus: str


@dataclass
class ReferenceData:
    manufacturers: list[ManufacturerRecord] = field(default_factory=list)
    # normalized alias/name -> ManufacturerRecord
    manufacturer_index: dict[str, ManufacturerRecord] = field(default_factory=dict)
    # mpn prefix -> ManufacturerRecord (longest-prefix match performed by caller)
    mpn_prefix_index: dict[str, ManufacturerRecord] = field(default_factory=dict)
    # (category, attribute) -> set of allowed values
    lov: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    # raw_form (lowercased) -> (normalized_uom, format_template)
    uom_map: dict[str, tuple[str, str]] = field(default_factory=dict)
    # decimal (float, rounded to 4dp) -> fraction string
    decimal_fraction: dict[float, str] = field(default_factory=dict)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_reference_data(data_dir: str = DATA_DIR) -> ReferenceData:
    ref = ReferenceData()

    # --- Manufacturer / brand master ---
    for row in _read_csv(os.path.join(data_dir, "manufacturer_brand_master.csv")):
        manufacturer = (row.get("manufacturer") or "").strip()
        brand = (row.get("brand") or "").strip()
        # A single malformed reference row should not discard the rest of the
        # master file or crash the application at startup.
        if not manufacturer or not brand:
            continue
        aliases = [a.strip() for a in (row.get("aliases") or "").split(";") if a.strip()]
        prefixes = [p.strip() for p in (row.get("mpn_prefixes") or "").split(";") if p.strip()]
        rec = ManufacturerRecord(
            manufacturer=manufacturer,
            brand=brand,
            aliases=aliases,
            mpn_prefixes=prefixes,
            category_focus=(row.get("category_focus") or "").strip(),
        )
        ref.manufacturers.append(rec)

        ref.manufacturer_index[_norm(rec.manufacturer)] = rec
        ref.manufacturer_index[_norm(rec.brand)] = rec
        for a in aliases:
            ref.manufacturer_index[_norm(a)] = rec
        for p in prefixes:
            ref.mpn_prefix_index[p.upper()] = rec

    # --- LOV master ---
    for row in _read_csv(os.path.join(data_dir, "lov_master.csv")):
        category = (row.get("category") or "").strip()
        attribute = (row.get("attribute") or "").strip()
        allowed_value = (row.get("allowed_value") or "").strip()
        if not category or not attribute or not allowed_value:
            continue
        key = (category, attribute)
        ref.lov.setdefault(key, set()).add(allowed_value)

    # --- UOM standards ---
    for row in _read_csv(os.path.join(data_dir, "uom_standards.csv")):
        raw_form = _norm(row.get("raw_form"))
        normalized_uom = (row.get("normalized_uom") or "").strip()
        format_template = (row.get("format_template") or "").strip()
        if not raw_form or not normalized_uom or not format_template:
            continue
        ref.uom_map[raw_form] = (normalized_uom, format_template)

    # --- Decimal -> fraction ---
    for row in _read_csv(os.path.join(data_dir, "decimal_fraction.csv")):
        try:
            ref.decimal_fraction[round(float(row["decimal"]), 4)] = row["fraction"].strip()
        except (ValueError, KeyError):
            continue

    return ref


def reference_data_status(data_dir: str = DATA_DIR) -> dict:
    """Reports whether official-looking files are present vs the bundled
    synthetic sample, so the UI can label results honestly."""
    files = {
        "manufacturer_brand_master.csv": "Manufacturer/Brand master",
        "lov_master.csv": "LOV master",
        "uom_standards.csv": "UOM standards",
        "decimal_fraction.csv": "Decimal-fraction table",
        "sample_input.csv": "Sample input catalog",
        "sample_ground_truth.csv": "Sample ground truth",
    }
    status = {}
    for fname, label in files.items():
        path = os.path.join(data_dir, fname)
        status[label] = os.path.exists(path)
    return status
