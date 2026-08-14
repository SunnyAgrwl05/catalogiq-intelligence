import unittest

from pipeline.entity_resolution import resolve_from_description, resolve_manufacturer, resolve_mpn
from pipeline.reference_data import load_reference_data


class TestEntityResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_exact_manufacturer_match(self):
        result = resolve_manufacturer("Moen", self.ref)
        self.assertEqual(result.match_type, "exact")
        self.assertEqual(result.record.manufacturer, "Moen Incorporated")

    def test_case_insensitive_match(self):
        result = resolve_manufacturer("DELTA", self.ref)
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.brand, "Delta")

    def test_corporate_suffix_stripped(self):
        result = resolve_manufacturer("Kohler Company", self.ref)
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.brand, "Kohler")

    def test_unknown_manufacturer_no_match(self):
        result = resolve_manufacturer("Totally Fictional Brand Co", self.ref)
        self.assertIsNone(result.record)
        self.assertEqual(result.match_type, "none")

    def test_none_input(self):
        result = resolve_manufacturer(None, self.ref)
        self.assertEqual(result.match_type, "none")
        self.assertEqual(result.score, 0.0)

    def test_mpn_prefix_match(self):
        result = resolve_mpn("7000", self.ref)
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.brand, "Moen")

    def test_mpn_no_match(self):
        result = resolve_mpn("XYZZY-000", self.ref)
        self.assertIsNone(result.record)

    def test_mpn_none_input(self):
        result = resolve_mpn(None, self.ref)
        self.assertEqual(result.match_type, "none")

    def test_description_mention_word_boundary(self):
        # "GE" should match as a whole word...
        result = resolve_from_description("GE top load washer", self.ref)
        self.assertIsNotNone(result.record)
        self.assertEqual(result.record.brand, "GE")

    def test_description_no_false_positive_substring(self):
        # ...but must NOT match "ge" inside "large"
        result = resolve_from_description("large capacity generic item", self.ref)
        self.assertIsNone(result.record)


if __name__ == "__main__":
    unittest.main()
