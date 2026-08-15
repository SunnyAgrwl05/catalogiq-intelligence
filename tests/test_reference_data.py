import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.reference_data import load_reference_data


class TestReferenceData(unittest.TestCase):
    def _write_csv(self, root: Path, name: str, fieldnames, rows):
        with (root / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_bundled_reference_data_has_expected_structures(self):
        from pipeline.reference_data import DATA_DIR

        ref = load_reference_data(DATA_DIR)

        self.assertGreater(len(ref.manufacturers), 0)
        self.assertIn("moen", ref.manufacturer_index)
        self.assertIn(("Faucets", "Mount Type"), ref.lov)
        self.assertIn("in", ref.uom_map)
        self.assertEqual(ref.decimal_fraction[0.125], "1/8")

    def test_malformed_rows_are_skipped_without_losing_valid_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_csv(
                root,
                "manufacturer_brand_master.csv",
                ["manufacturer", "brand", "aliases", "mpn_prefixes", "category_focus"],
                [
                    {"manufacturer": "Valid Co", "brand": "Valid", "aliases": "V", "mpn_prefixes": "VC", "category_focus": "Tools"},
                    {"manufacturer": "", "brand": "Broken", "aliases": "", "mpn_prefixes": "", "category_focus": "Tools"},
                ],
            )
            self._write_csv(
                root,
                "lov_master.csv",
                ["category", "attribute", "allowed_value"],
                [
                    {"category": "Tools", "attribute": "Kind", "allowed_value": "Hammer"},
                    {"category": "", "attribute": "Kind", "allowed_value": "Broken"},
                ],
            )
            self._write_csv(
                root,
                "uom_standards.csv",
                ["raw_form", "normalized_uom", "format_template"],
                [
                    {"raw_form": "kg", "normalized_uom": "kg", "format_template": "{value} kg"},
                    {"raw_form": "", "normalized_uom": "kg", "format_template": "{value} kg"},
                ],
            )
            self._write_csv(
                root,
                "decimal_fraction.csv",
                ["decimal", "fraction"],
                [
                    {"decimal": "0.5", "fraction": "1/2"},
                    {"decimal": "not-a-number", "fraction": "broken"},
                ],
            )

            ref = load_reference_data(str(root))

            self.assertEqual([record.brand for record in ref.manufacturers], ["Valid"])
            self.assertEqual(ref.lov[("Tools", "Kind")], {"Hammer"})
            self.assertEqual(ref.uom_map["kg"], ("kg", "{value} kg"))
            self.assertEqual(ref.decimal_fraction[0.5], "1/2")


if __name__ == "__main__":
    unittest.main()
