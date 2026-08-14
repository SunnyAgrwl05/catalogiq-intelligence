import unittest

from pipeline.preprocessing import extract_measurements, is_placeholder, normalize_field, normalize_product_row


class TestPlaceholderDetection(unittest.TestCase):
    def test_known_placeholders(self):
        for val in ["-- Unbranded --", "N/A", "n/a", "Unknown", "None", "TBD", "", "   ", "null", "---"]:
            self.assertTrue(is_placeholder(val), f"expected placeholder: {val!r}")

    def test_real_values_not_placeholder(self):
        for val in ["Moen", "Delta Faucet Company", "24 in", "GE"]:
            self.assertFalse(is_placeholder(val), f"expected NOT placeholder: {val!r}")

    def test_none_is_placeholder(self):
        self.assertTrue(is_placeholder(None))


class TestNormalizeField(unittest.TestCase):
    def test_placeholder_becomes_none(self):
        self.assertIsNone(normalize_field("-- Unbranded --"))

    def test_whitespace_collapsed(self):
        self.assertEqual(normalize_field("Moen   Incorporated"), "Moen Incorporated")

    def test_real_value_preserved(self):
        self.assertEqual(normalize_field("Delta"), "Delta")


class TestExtractMeasurements(unittest.TestCase):
    def test_extracts_value_and_unit(self):
        result = extract_measurements("Height: 15.25 in Weight: 3lb")
        self.assertEqual(result, [
            {"raw_value": "15.25", "raw_unit": "in"},
            {"raw_value": "3", "raw_unit": "lb"},
        ])

    def test_empty_text(self):
        self.assertEqual(extract_measurements(""), [])
        self.assertEqual(extract_measurements(None), [])

    def test_inch_mark(self):
        result = extract_measurements('24" reach')
        self.assertEqual(result[0]["raw_value"], "24")


class TestNormalizeProductRow(unittest.TestCase):
    def test_placeholder_manufacturer_becomes_none(self):
        row = {"product_id": "P002", "manufacturer": "-- Unbranded --", "mpn": "CA87-BN",
               "description": "Moen Align faucet", "category": "Faucets", "raw_specs": "Height: 15.25 in"}
        normalized = normalize_product_row(row)
        self.assertIsNone(normalized["manufacturer"])
        self.assertEqual(normalized["mpn"], "CA87-BN")
        self.assertEqual(len(normalized["_measurements"]), 1)


if __name__ == "__main__":
    unittest.main()
