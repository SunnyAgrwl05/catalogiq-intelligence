import os
import tempfile
import unittest
from copy import deepcopy

from pipeline.custom_rules import (
    AnomalyRule,
    CustomRules,
    load_rules_file,
    merge_custom_rules_into_ref,
)
from pipeline.reference_data import load_reference_data
from pipeline.schemas import ValidationState
from pipeline.validation import check_contextual_anomaly, validate_lov


class TestCustomRulesLoading(unittest.TestCase):
    def test_load_yaml_rules_file(self):
        content = """
lov:
  TestCategory:
    TestAttr: ["Value1", "Value2"]
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            rules = load_rules_file(path)
            self.assertIn(("TestCategory", "TestAttr"), rules.lov)
            self.assertEqual(rules.lov[("TestCategory", "TestAttr")], {"Value1", "Value2"})
        finally:
            os.unlink(path)

    def test_load_json_rules_file(self):
        content = """
{
  "lov": {
    "TestCategory": {
      "TestAttr": ["ValueA"]
    }
  }
}
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            rules = load_rules_file(path)
            self.assertIn(("TestCategory", "TestAttr"), rules.lov)
            self.assertEqual(rules.lov[("TestCategory", "TestAttr")], {"ValueA"})
        finally:
            os.unlink(path)

    def test_load_uom_rules(self):
        content = """
uom:
  m:
    normalized: "m"
    template: "{value} m"
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            rules = load_rules_file(path)
            self.assertIn("m", rules.uom)
            self.assertEqual(rules.uom["m"], ("m", "{value} m"))
        finally:
            os.unlink(path)

    def test_load_anomaly_rules(self):
        content = """
anomaly_rules:
  - category: "Valves"
    attribute: "weight"
    unit: "kg"
    max_value: 200
    message: "Too heavy for a valve"
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            rules = load_rules_file(path)
            self.assertEqual(len(rules.anomaly_rules), 1)
            self.assertEqual(rules.anomaly_rules[0].category, "Valves")
            self.assertEqual(rules.anomaly_rules[0].max_value, 200)
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with self.assertRaises(ValueError):
            load_rules_file("/nonexistent/path.yaml")

    def test_non_mapping_top_level_raises(self):
        content = "- item1\n- item2\n"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_rules_file(path)
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_rules(self):
        content = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w", encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            rules = load_rules_file(path)
            self.assertIsInstance(rules, CustomRules)
            self.assertEqual(len(rules.lov), 0)
            self.assertEqual(len(rules.uom), 0)
            self.assertEqual(len(rules.anomaly_rules), 0)
        finally:
            os.unlink(path)


class TestMergeCustomRulesIntoRef(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_merge_lov_extends_existing(self):
        ref = deepcopy(self.ref)
        custom = CustomRules(
            lov={("Faucets", "Finish"): {"Rose Gold"}},
        )
        merge_custom_rules_into_ref(ref, custom)
        self.assertIn("Rose Gold", ref.lov[("Faucets", "Finish")])
        self.assertIn("Chrome", ref.lov[("Faucets", "Finish")])

    def test_merge_uom_adds_new_entries(self):
        ref = deepcopy(self.ref)
        custom = CustomRules(
            uom={"ft": ("ft", "{value} ft")},
        )
        merge_custom_rules_into_ref(ref, custom)
        self.assertEqual(ref.uom_map["ft"], ("ft", "{value} ft"))

    def test_merge_anomaly_rules_stored(self):
        ref = deepcopy(self.ref)
        rule = AnomalyRule(
            category="Pipes",
            attribute="length",
            unit="m",
            max_value=500,
            message="Pipe over 500 m is unusual",
        )
        custom = CustomRules(anomaly_rules=[rule])
        merge_custom_rules_into_ref(ref, custom)
        self.assertEqual(len(ref._custom_anomaly_rules), 1)
        self.assertEqual(ref._custom_anomaly_rules[0].category, "Pipes")


class TestCustomRulesAffectValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = load_reference_data()

    def test_custom_lov_value_passes(self):
        ref = deepcopy(self.ref)
        custom = CustomRules(
            lov={("Faucets", "Finish"): {"Rose Gold"}},
        )
        merge_custom_rules_into_ref(ref, custom)
        state, _ = validate_lov("Faucets", "Finish", "Rose Gold", ref)
        self.assertEqual(state, ValidationState.PASSED)

    def test_custom_lov_value_not_in_built_in_fails(self):
        state, _ = validate_lov("Faucets", "Finish", "Rose Gold", self.ref)
        self.assertEqual(state, ValidationState.FAILED)

    def test_custom_anomaly_rule_triggers(self):
        ref = deepcopy(self.ref)
        rule = AnomalyRule(
            category="Valves",
            attribute="weight",
            unit="kg",
            max_value=200,
            message="Valve weight over {max_value} kg is unusual",
        )
        custom = CustomRules(anomaly_rules=[rule])
        merge_custom_rules_into_ref(ref, custom)
        note = check_contextual_anomaly("Valves", "weight", "250", "kg", ref=ref)
        self.assertIsNotNone(note)
        self.assertIn("CONTEXTUAL ANOMALY", note)
        self.assertIn("250", note)

    def test_custom_anomaly_rule_below_threshold(self):
        ref = deepcopy(self.ref)
        rule = AnomalyRule(
            category="Valves",
            attribute="weight",
            unit="kg",
            max_value=200,
            message="Valve weight over {max_value} kg is unusual",
        )
        custom = CustomRules(anomaly_rules=[rule])
        merge_custom_rules_into_ref(ref, custom)
        note = check_contextual_anomaly("Valves", "weight", "100", "kg", ref=ref)
        self.assertIsNone(note)

    def test_builtin_anomaly_still_works(self):
        note = check_contextual_anomaly("Faucets", "weight", "100", "kg")
        self.assertIsNotNone(note)
        self.assertIn("CONTEXTUAL ANOMALY", note)

    def test_no_ref_still_works(self):
        note = check_contextual_anomaly("Faucets", "weight", "3", "lb")
        self.assertIsNone(note)


if __name__ == "__main__":
    unittest.main()
