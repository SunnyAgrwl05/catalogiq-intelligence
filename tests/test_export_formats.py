import unittest

from pipeline.export_formats import (
    EXPORT_FORMATS,
    export_rows,
    get_format,
    list_formats,
)
from pipeline.schemas import (
    Decision,
    Evidence,
    EvidenceType,
    FieldResult,
    ProductResult,
    ValidationResult,
    ValidationState,
)


def _make_product_result() -> ProductResult:
    """Build a minimal ProductResult for testing export mappings."""
    mfg_evidence = Evidence(
        type=EvidenceType.REFERENCE_DATA,
        signal="Manufacturer matched from reference data",
        value="Moen",
        strength=0.95,
    )
    mfg_vr = ValidationResult(lov=ValidationState.PASSED)
    mfg_field = FieldResult(
        field="manufacturer", value="Moen", confidence=0.95,
        evidence=[mfg_evidence], validation=mfg_vr,
        decision=Decision.AUTO_APPROVED, reason="Strong evidence match",
    )

    brand_field = FieldResult(
        field="brand", value="Moen", confidence=0.90,
        evidence=[], validation=ValidationResult(),
        decision=Decision.AUTO_APPROVED, reason="",
    )

    cat_field = FieldResult(
        field="category", value="Faucets", confidence=0.85,
        evidence=[], validation=ValidationResult(),
        decision=Decision.AUTO_APPROVED, reason="",
    )

    mpn_field = FieldResult(
        field="mpn", value="MN-7000", confidence=0.88,
        evidence=[], validation=ValidationResult(),
        decision=Decision.AUTO_APPROVED, reason="",
    )

    desc_field = FieldResult(
        field="description", value="Single handle kitchen faucet, chrome finish",
        confidence=0.80, evidence=[], validation=ValidationResult(),
        decision=Decision.AUTO_APPROVED, reason="",
    )

    return ProductResult(
        product_id="PROD-001",
        raw_input={"product_id": "PROD-001", "manufacturer": "Moen"},
        fields={
            "manufacturer": mfg_field,
            "brand": brand_field,
            "category": cat_field,
            "mpn": mpn_field,
            "description": desc_field,
        },
    )


class TestExportFormats(unittest.TestCase):
    def test_list_formats_returns_all(self):
        formats = list_formats()
        self.assertIn("generic", formats)
        self.assertIn("shopify", formats)

    def test_get_format_generic(self):
        fmt = get_format("generic")
        self.assertEqual(fmt.name, "Generic")

    def test_get_format_shopify(self):
        fmt = get_format("shopify")
        self.assertEqual(fmt.name, "Shopify")

    def test_get_format_unknown_raises(self):
        with self.assertRaises(KeyError):
            get_format("nonexistent")


class TestGenericExport(unittest.TestCase):
    def test_generic_row_has_expected_columns(self):
        r = _make_product_result()
        rows = export_rows([r], "generic")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["product_id"], "PROD-001")
        self.assertIn("manufacturer_value", row)
        self.assertIn("manufacturer_confidence", row)
        self.assertIn("manufacturer_decision", row)
        self.assertIn("manufacturer_evidence_summary", row)
        self.assertIn("manufacturer_validation", row)

    def test_generic_row_field_values(self):
        r = _make_product_result()
        rows = export_rows([r], "generic")
        row = rows[0]
        self.assertEqual(row["manufacturer_value"], "Moen")
        self.assertEqual(row["manufacturer_decision"], "AUTO_APPROVED")
        self.assertIn("Manufacturer matched", row["manufacturer_evidence_summary"])

    def test_generic_multiple_products(self):
        r1 = _make_product_result()
        r2 = ProductResult(
            product_id="PROD-002",
            raw_input={},
            fields={"manufacturer": FieldResult(
                field="manufacturer", value="Delta", confidence=0.7,
                evidence=[], validation=ValidationResult(),
                decision=Decision.REVIEW_REQUIRED, reason="",
            )},
        )
        rows = export_rows([r1, r2], "generic")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["product_id"], "PROD-001")
        self.assertEqual(rows[1]["product_id"], "PROD-002")


class TestShopifyExport(unittest.TestCase):
    def test_shopify_row_has_expected_columns(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        expected_cols = [
            "Handle", "Title", "Body (HTML)", "Vendor", "Product Category",
            "Type", "Tags", "Published", "Option1 Name", "Option1 Value",
            "Variant SKU", "Variant Grams", "Variant Inventory Qty",
            "Variant Price", "Variant Compare At Price", "Status",
        ]
        for col in expected_cols:
            self.assertIn(col, row)

    def test_shopify_maps_vendor_from_manufacturer(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        row = rows[0]
        self.assertEqual(row["Vendor"], "Moen")

    def test_shopify_maps_title_from_brand(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Title"], "Moen")

    def test_shopify_maps_type_from_category(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Type"], "Faucets")
        self.assertEqual(rows[0]["Product Category"], "Faucets")

    def test_shopify_maps_sku_from_mpn(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Variant SKU"], "MN-7000")

    def test_shopify_maps_body_from_description(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Body (HTML)"], "Single handle kitchen faucet, chrome finish")

    def test_shopify_handle_from_product_id(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Handle"], "prod-001")

    def test_shopify_published_and_status(self):
        r = _make_product_result()
        rows = export_rows([r], "shopify")
        self.assertEqual(rows[0]["Published"], "TRUE")
        self.assertEqual(rows[0]["Status"], "active")

    def test_shopify_empty_fields_handled(self):
        r = ProductResult(
            product_id="EMPTY-001",
            raw_input={},
            fields={},
        )
        rows = export_rows([r], "shopify")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Vendor"], "")
        self.assertEqual(rows[0]["Title"], "")
        self.assertEqual(rows[0]["Variant SKU"], "")


if __name__ == "__main__":
    unittest.main()
