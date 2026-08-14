import os
import tempfile
import unittest

from pipeline.correction_memory import load_corrections, lookup_correction, record_correction


class TestCorrectionMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        self.tmp.close()
        self.path = self.tmp.name
        os.remove(self.path)  # let record_correction create it fresh

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_record_and_lookup_roundtrip(self):
        record_correction(
            product_id="P011", field="manufacturer", mpn="9192-XYZ",
            manufacturer_input="Unknown", predicted_value="Delta Faucet Company",
            corrected_value="General Electric (GE Appliances)", reason="badge confirmed",
            path=self.path,
        )
        corrections = load_corrections(self.path)
        match = lookup_correction("manufacturer", "9192-XYZ", "Unknown", corrections)
        self.assertIsNotNone(match)
        self.assertEqual(match.corrected_value, "General Electric (GE Appliances)")

    def test_no_match_for_different_signature(self):
        record_correction(
            product_id="P011", field="manufacturer", mpn="9192-XYZ",
            manufacturer_input="Unknown", predicted_value="Delta Faucet Company",
            corrected_value="GE", path=self.path,
        )
        corrections = load_corrections(self.path)
        match = lookup_correction("manufacturer", "DIFFERENT-MPN", "Unknown", corrections)
        self.assertIsNone(match)

    def test_empty_mpn_never_matches(self):
        # Guards against over-matching on blank/blank signatures.
        record_correction(
            product_id="P015", field="manufacturer", mpn="",
            manufacturer_input="", predicted_value=None,
            corrected_value="UNKNOWN", path=self.path,
        )
        corrections = load_corrections(self.path)
        match = lookup_correction("manufacturer", "", "", corrections)
        self.assertIsNone(match)

    def test_multiple_corrections_returns_most_recent(self):
        record_correction(
            product_id="P011", field="manufacturer", mpn="9192-XYZ",
            manufacturer_input="Unknown", predicted_value="Delta Faucet Company",
            corrected_value="First Correction", path=self.path,
        )
        record_correction(
            product_id="P011", field="manufacturer", mpn="9192-XYZ",
            manufacturer_input="Unknown", predicted_value="First Correction",
            corrected_value="Second Correction", path=self.path,
        )
        corrections = load_corrections(self.path)
        match = lookup_correction("manufacturer", "9192-XYZ", "Unknown", corrections)
        self.assertEqual(match.corrected_value, "Second Correction")


if __name__ == "__main__":
    unittest.main()
