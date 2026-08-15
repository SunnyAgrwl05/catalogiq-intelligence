"""
Export format presets for CatalogIQ enriched catalogs.

Each preset maps CatalogIQ's enriched field results to a target
platform's expected schema. The layer is kept separate from the core
enrichment pipeline so additional platforms can be added later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.schemas import ProductResult


@dataclass
class ExportFormat:
    name: str
    description: str
    columns: list[str]
    mapper: callable


def _build_generic_row(r: ProductResult) -> dict:
    row = {
        "product_id": r.product_id,
        "overall_trust": round(r.overall_trust(), 4),
        "overall_decision": r.overall_decision().value,
    }
    for field_name, fr in r.fields.items():
        row[f"{field_name}_value"] = fr.value
        row[f"{field_name}_confidence"] = round(fr.confidence, 4)
        row[f"{field_name}_decision"] = fr.decision.value
        row[f"{field_name}_evidence_summary"] = "; ".join(e.signal for e in fr.evidence)
        row[f"{field_name}_validation"] = "; ".join(fr.validation.notes) if fr.validation.notes else "ok"
    return row


GENERIC_COLUMNS = [
    "product_id", "overall_trust", "overall_decision",
]

SHOPIFY_COLUMNS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Qty",
    "Variant Price",
    "Variant Compare At Price",
    "Status",
]


def _build_shopify_row(r: ProductResult) -> dict:
    """Map CatalogIQ enriched fields to Shopify product CSV columns.

    Shopify CSV reference:
    https://shopify.dev/docs/api/admin-rest/2023-10/resources/product#properties
    """
    mfg = r.fields.get("manufacturer")
    brand = r.fields.get("brand")
    cat = r.fields.get("category")
    mpn_field = r.fields.get("mpn")
    desc_field = r.fields.get("description")

    vendor = mfg.value if mfg and mfg.value else ""
    product_type = cat.value if cat and cat.value else ""
    title = brand.value if brand and brand.value else ""
    body_html = desc_field.value if desc_field and desc_field.value else ""
    sku = mpn_field.value if mpn_field and mpn_field.value else ""

    # Use brand as tags if available
    tags = brand.value if brand and brand.value else ""

    handle = r.product_id.lower().replace(" ", "-") if r.product_id else ""

    return {
        "Handle": handle,
        "Title": title,
        "Body (HTML)": body_html,
        "Vendor": vendor,
        "Product Category": product_type,
        "Type": product_type,
        "Tags": tags,
        "Published": "TRUE",
        "Option1 Name": "Title",
        "Option1 Value": "Default Title",
        "Variant SKU": sku,
        "Variant Grams": "",
        "Variant Inventory Qty": "",
        "Variant Price": "",
        "Variant Compare At Price": "",
        "Status": "active",
    }


EXPORT_FORMATS: dict[str, ExportFormat] = {
    "generic": ExportFormat(
        name="Generic",
        description="CatalogIQ enriched output with all field details",
        columns=GENERIC_COLUMNS,
        mapper=_build_generic_row,
    ),
    "shopify": ExportFormat(
        name="Shopify",
        description="Shopify-compatible product CSV",
        columns=SHOPIFY_COLUMNS,
        mapper=_build_shopify_row,
    ),
}


def list_formats() -> list[str]:
    """Return available format keys."""
    return list(EXPORT_FORMATS.keys())


def get_format(format_key: str) -> ExportFormat:
    """Return the ExportFormat for the given key. Raises KeyError if not found."""
    if format_key not in EXPORT_FORMATS:
        raise KeyError(f"Unknown export format: {format_key}. Available: {list_formats()}")
    return EXPORT_FORMATS[format_key]


def export_rows(results: list[ProductResult], format_key: str) -> list[dict]:
    """Convert enriched ProductResults into rows matching the target format."""
    fmt = get_format(format_key)
    return [fmt.mapper(r) for r in results]
