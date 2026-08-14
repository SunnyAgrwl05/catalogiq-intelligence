import unittest

from pipeline.reference_data import load_reference_data
from pipeline.schemas import ValidationState
from pipeline.validation import (
    check_contextual_anomaly,
    normalize_uom,
    validate_description_quality,
    validate_lov,
    validate_uom_formatting,
)


class TestValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_lov_passes_for_allowed_value(self):
        state, note = validate_lov("Faucets", "Finish", "Chrome", self.ref)
        self.assertEqual(state, ValidationState.PASSED)
        self.assertIsNone(note)

    def test_lov_fails_for_disallowed_value(self):
        state, note = validate_lov("Faucets", "Finish", "Purple", self.ref)
        self.assertEqual(state, ValidationState.FAILED)
        self.assertIsNotNone(note)

    def test_lov_not_applicable_for_unknown_attribute(self):
        state, _ = validate_lov("Faucets", "Nonexistent Attribute", "X", self.ref)
        self.assertEqual(state, ValidationState.NOT_APPLICABLE)

    def test_uom_normalization_known_unit(self):
        display, note = normalize_uom("24", "in", self.ref)
        self.assertEqual(display, "24 in")
        self.assertIsNone(note)

    def test_uom_normalization_unknown_unit(self):
        display, note = normalize_uom("24", "furlongs", self.ref)
        self.assertIsNone(display)
        self.assertIsNotNone(note)

    def test_uom_format_requires_space(self):
        state, note = validate_uom_formatting("24in")
        self.assertEqual(state, ValidationState.FAILED)
        state2, note2 = validate_uom_formatting("24 in")
        self.assertEqual(state2, ValidationState.PASSED)

    def test_contextual_anomaly_flags_impossible_faucet_weight(self):
        note = check_contextual_anomaly("Faucets", "weight", "1000", "kg")
        self.assertIsNotNone(note)
        self.assertIn("CONTEXTUAL ANOMALY", note)

    def test_contextual_anomaly_does_not_flag_normal_weight(self):
        note = check_contextual_anomaly("Faucets", "weight", "3", "lb")
        self.assertIsNone(note)

    def test_contextual_anomaly_requires_all_inputs(self):
        self.assertIsNone(check_contextual_anomaly(None, "weight", "1000", "kg"))
        self.assertIsNone(check_contextual_anomaly("Faucets", "weight", None, "kg"))

    def test_description_quality_flags_missing(self):
        state, notes = validate_description_quality(None)
        self.assertEqual(state, ValidationState.FAILED)

    def test_description_quality_flags_placeholder(self):
        state, notes = validate_description_quality("N/A")
        self.assertEqual(state, ValidationState.FAILED)

    def test_description_quality_passes_reasonable_text(self):
        state, notes = validate_description_quality("Moen 7000 single handle kitchen faucet, chrome finish")
        self.assertEqual(state, ValidationState.PASSED)


if __name__ == "__main__":
    unittest.main()
