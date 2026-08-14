import unittest

from pipeline.confidence import compute_field_confidence, decide
from pipeline.contradiction import fuse_evidence
from pipeline.schemas import Decision, Evidence, EvidenceType, ValidationResult, ValidationState


class TestContradictionEngine(unittest.TestCase):
    def test_consensus_not_flagged_as_conflict(self):
        evidence = [
            Evidence(EvidenceType.MPN_PATTERN, "s", "Speed Queen", 0.94),
            Evidence(EvidenceType.DESCRIPTION, "s", "Speed Queen", 0.75),
            Evidence(EvidenceType.REFERENCE_DATA, "s", "Speed Queen", 0.97),
        ]
        fusion = fuse_evidence(evidence)
        self.assertEqual(fusion.winning_value, "Speed Queen")
        self.assertFalse(fusion.is_conflict)
        self.assertEqual(fusion.conflict_severity, 0.0)

    def test_close_disagreement_flagged_as_conflict(self):
        evidence = [
            Evidence(EvidenceType.MPN_PATTERN, "s", "Delta Faucet Company", 0.8),
            Evidence(EvidenceType.DESCRIPTION, "s", "General Electric (GE Appliances)", 0.75),
        ]
        fusion = fuse_evidence(evidence)
        self.assertTrue(fusion.is_conflict)
        self.assertGreater(fusion.conflict_severity, 0.0)

    def test_lopsided_disagreement_not_conflict(self):
        # One strong signal vs one very weak signal for a different value
        # should NOT be flagged as a genuine conflict.
        evidence = [
            Evidence(EvidenceType.REFERENCE_DATA, "s", "Moen Incorporated", 0.98),
            Evidence(EvidenceType.DESCRIPTION, "s", "Kohler Co.", 0.1),
        ]
        fusion = fuse_evidence(evidence)
        self.assertEqual(fusion.winning_value, "Moen Incorporated")
        self.assertFalse(fusion.is_conflict)

    def test_no_evidence(self):
        fusion = fuse_evidence([])
        self.assertIsNone(fusion.winning_value)
        self.assertFalse(fusion.is_conflict)

    def test_single_evidence_item(self):
        fusion = fuse_evidence([Evidence(EvidenceType.INPUT_FIELD, "s", "Moen Incorporated", 1.0)])
        self.assertEqual(fusion.winning_value, "Moen Incorporated")
        self.assertFalse(fusion.is_conflict)


class TestConfidenceEngine(unittest.TestCase):
    def test_no_evidence_gives_zero_confidence(self):
        fusion = fuse_evidence([])
        conf = compute_field_confidence(fusion, ValidationResult())
        self.assertEqual(conf, 0.0)

    def test_conflict_routes_to_investigate(self):
        evidence = [
            Evidence(EvidenceType.MPN_PATTERN, "s", "A", 0.8),
            Evidence(EvidenceType.DESCRIPTION, "s", "B", 0.78),
        ]
        fusion = fuse_evidence(evidence)
        conf = compute_field_confidence(fusion, ValidationResult())
        decision = decide(conf, fusion.is_conflict)
        self.assertEqual(decision, Decision.INVESTIGATE)

    def test_strong_consensus_routes_to_auto_approved(self):
        evidence = [
            Evidence(EvidenceType.MPN_PATTERN, "s", "Moen Incorporated", 0.9),
            Evidence(EvidenceType.REFERENCE_DATA, "s", "Moen Incorporated", 0.95),
        ]
        fusion = fuse_evidence(evidence)
        vr = ValidationResult(lov=ValidationState.PASSED)
        conf = compute_field_confidence(fusion, vr)
        decision = decide(conf, fusion.is_conflict)
        self.assertEqual(decision, Decision.AUTO_APPROVED)

    def test_failed_validation_lowers_confidence(self):
        evidence = [Evidence(EvidenceType.INPUT_FIELD, "s", "Purple", 1.0)]
        fusion = fuse_evidence(evidence)
        vr_pass = ValidationResult()
        vr_fail = ValidationResult(lov=ValidationState.FAILED)
        conf_pass = compute_field_confidence(fusion, vr_pass)
        conf_fail = compute_field_confidence(fusion, vr_fail)
        self.assertLess(conf_fail, conf_pass)

    def test_confidence_bounded_0_to_1(self):
        evidence = [
            Evidence(EvidenceType.MPN_PATTERN, "s", "X", 1.0),
            Evidence(EvidenceType.DESCRIPTION, "s", "X", 1.0),
            Evidence(EvidenceType.REFERENCE_DATA, "s", "X", 1.0),
        ]
        fusion = fuse_evidence(evidence)
        conf = compute_field_confidence(fusion, ValidationResult())
        self.assertLessEqual(conf, 1.0)
        self.assertGreaterEqual(conf, 0.0)


if __name__ == "__main__":
    unittest.main()
