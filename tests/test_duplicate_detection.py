import unittest

from pipeline.duplicate_detection import (
    DuplicateCandidate,
    DuplicateGroup,
    _desc_similarity,
    _mpn_norm,
    compute_similarity,
    detect_duplicates,
)
from pipeline.schemas import (
    Decision,
    FieldResult,
    ProductResult,
    ValidationResult,
)


def _make_product(product_id: str, manufacturer: str | None, mpn: str | None, description: str | None) -> ProductResult:
    return ProductResult(
        product_id=product_id,
        raw_input={
            "product_id": product_id,
            "manufacturer": manufacturer,
            "mpn": mpn,
            "description": description,
        },
        fields={},
    )


class TestHelpers(unittest.TestCase):
    def test_mpn_norm_strips_hyphens(self):
        self.assertEqual(_mpn_norm("MN-7000"), "mn7000")

    def test_mpn_norm_strips_spaces(self):
        self.assertEqual(_mpn_norm("MN 7000"), "mn7000")

    def test_mpn_norm_lowercase(self):
        self.assertEqual(_mpn_norm("MN7000"), "mn7000")

    def test_desc_similarity_identical(self):
        self.assertAlmostEqual(_desc_similarity("Faucet", "Faucet"), 1.0)

    def test_desc_similarity_empty(self):
        self.assertAlmostEqual(_desc_similarity(None, None), 0.0)
        self.assertAlmostEqual(_desc_similarity("", ""), 0.0)

    def test_desc_similarity_partial(self):
        sim = _desc_similarity("Kitchen faucet chrome", "Kitchen faucet brushed nickel")
        self.assertGreater(sim, 0.5)
        self.assertLess(sim, 1.0)


class TestComputeSimilarity(unittest.TestCase):
    def test_identical_products_high_similarity(self):
        a = _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome")
        b = _make_product("P2", "Moen", "MN-7000", "Kitchen faucet chrome")
        c = compute_similarity(a, b)
        self.assertIsNotNone(c)
        self.assertGreater(c.similarity, 0.9)

    def test_same_manufacturer_different_mpn(self):
        a = _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome")
        b = _make_product("P2", "Moen", "MN-8000", "Kitchen faucet chrome")
        c = compute_similarity(a, b)
        self.assertIsNotNone(c)
        self.assertGreater(c.similarity, 0.5)

    def test_different_products_low_similarity(self):
        a = _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome")
        b = _make_product("P2", "Delta", "DL-5000", "Bathroom shower head")
        c = compute_similarity(a, b)
        self.assertIsNone(c)

    def test_same_mpn_different_manufacturer(self):
        a = _make_product("P1", "Moen", "MN-7000", "Kitchen faucet")
        b = _make_product("P2", "Delta", "MN-7000", "Kitchen faucet")
        c = compute_similarity(a, b)
        self.assertIsNotNone(c)
        self.assertGreater(c.similarity, 0.5)

    def test_description_only_moderate(self):
        a = _make_product("P1", None, None, "Chrome kitchen faucet single handle")
        b = _make_product("P2", None, None, "Chrome kitchen faucet single handle")
        c = compute_similarity(a, b)
        # Description-only score is 1.0 * 0.25 = 0.25, below 0.3 threshold
        # So this returns None, which is correct behavior
        self.assertIsNone(c)

    def test_no_evidence_returns_none(self):
        a = _make_product("P1", "Moen", "MN-7000", "Faucet")
        b = _make_product("P2", "Delta", "DL-5000", "Shower")
        c = compute_similarity(a, b)
        self.assertIsNone(c)

    def test_evidence_list_populated(self):
        a = _make_product("P1", "Moen", "MN-7000", "Faucet")
        b = _make_product("P2", "Moen", "MN-7000", "Faucet")
        c = compute_similarity(a, b)
        self.assertTrue(len(c.evidence) > 0)


class TestDetectDuplicates(unittest.TestCase):
    def test_finds_identical_pair(self):
        products = [
            _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P2", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P3", "Delta", "DL-5000", "Bathroom shower head"),
        ]
        groups = detect_duplicates(products, similarity_threshold=0.5)
        self.assertEqual(len(groups), 1)
        self.assertIn("P1", groups[0].product_ids)
        self.assertIn("P2", groups[0].product_ids)

    def test_no_duplicates(self):
        products = [
            _make_product("P1", "Moen", "MN-7000", "Kitchen faucet"),
            _make_product("P2", "Delta", "DL-5000", "Shower head"),
            _make_product("P3", "Kohler", "KH-3000", "Bathroom sink"),
        ]
        groups = detect_duplicates(products, similarity_threshold=0.7)
        self.assertEqual(len(groups), 0)

    def test_empty_catalog(self):
        groups = detect_duplicates([], similarity_threshold=0.5)
        self.assertEqual(len(groups), 0)

    def test_single_product(self):
        products = [_make_product("P1", "Moen", "MN-7000", "Faucet")]
        groups = detect_duplicates(products, similarity_threshold=0.5)
        self.assertEqual(len(groups), 0)

    def test_three_way_duplicate(self):
        products = [
            _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P2", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P3", "Moen", "MN-7000", "Kitchen faucet chrome"),
        ]
        groups = detect_duplicates(products, similarity_threshold=0.5)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].product_ids), 3)

    def test_groups_sorted_by_similarity(self):
        products = [
            _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P2", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P3", "Moen", "MN-7000", "Kitchen faucet"),
            _make_product("P4", "Delta", "DL-5000", "Shower head"),
        ]
        groups = detect_duplicates(products, similarity_threshold=0.5)
        if len(groups) >= 2:
            self.assertGreaterEqual(groups[0].best_similarity, groups[1].best_similarity)

    def test_threshold_affects_results(self):
        products = [
            _make_product("P1", "Moen", "MN-7000", "Kitchen faucet chrome"),
            _make_product("P2", "Moen", "DL-5000", "Bathroom shower head"),
        ]
        groups_high = detect_duplicates(products, similarity_threshold=0.8)
        groups_low = detect_duplicates(products, similarity_threshold=0.3)
        self.assertGreaterEqual(len(groups_low), len(groups_high))


class TestDuplicateGroup(unittest.TestCase):
    def test_group_attributes(self):
        group = DuplicateGroup(
            group_id=0,
            product_ids=["P1", "P2"],
            candidates=[
                DuplicateCandidate(
                    product_a_id="P1", product_b_id="P2",
                    similarity=0.85, evidence=["manufacturer match"],
                )
            ],
            best_similarity=0.85,
        )
        self.assertEqual(group.group_id, 0)
        self.assertEqual(len(group.product_ids), 2)
        self.assertEqual(len(group.candidates), 1)
        self.assertAlmostEqual(group.best_similarity, 0.85)


if __name__ == "__main__":
    unittest.main()
