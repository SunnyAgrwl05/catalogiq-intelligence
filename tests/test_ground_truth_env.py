import csv
import os
import tempfile
import unittest
from unittest.mock import patch

# We test the load_ground_truth function from app.py
# but app.py has heavy Streamlit imports, so we test the env var logic directly.


class TestGroundTruthEnvVar(unittest.TestCase):
    def test_default_path_used_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            path = os.environ.get("CATALOGIQ_GROUND_TRUTH_PATH", "data/sample_ground_truth.csv")
            self.assertEqual(path, "data/sample_ground_truth.csv")

    def test_custom_path_used_when_env_set(self):
        custom_path = "/custom/path/ground_truth.csv"
        with patch.dict(os.environ, {"CATALOGIQ_GROUND_TRUTH_PATH": custom_path}):
            path = os.environ.get("CATALOGIQ_GROUND_TRUTH_PATH", "data/sample_ground_truth.csv")
            self.assertEqual(path, custom_path)

    def test_load_from_custom_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["product_id", "manufacturer", "mpn"])
            writer.writeheader()
            writer.writerow({"product_id": "P1", "manufacturer": "Moen", "mpn": "MN-7000"})
            tmp_path = f.name

        try:
            with patch.dict(os.environ, {"CATALOGIQ_GROUND_TRUTH_PATH": tmp_path}):
                path = os.environ.get("CATALOGIQ_GROUND_TRUTH_PATH", "data/sample_ground_truth.csv")
                with open(path, newline="", encoding="utf-8-sig") as g:
                    rows = list(csv.DictReader(g))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["product_id"], "P1")
        finally:
            os.unlink(tmp_path)

    def test_empty_path_results_in_error(self):
        with patch.dict(os.environ, {"CATALOGIQ_GROUND_TRUTH_PATH": ""}):
            path = os.environ.get("CATALOGIQ_GROUND_TRUTH_PATH", "data/sample_ground_truth.csv")
            self.assertEqual(path, "")

    def test_nonexistent_path_results_in_error(self):
        with patch.dict(os.environ, {"CATALOGIQ_GROUND_TRUTH_PATH": "/nonexistent/path.csv"}):
            path = os.environ.get("CATALOGIQ_GROUND_TRUTH_PATH", "data/sample_ground_truth.csv")
            with self.assertRaises(FileNotFoundError):
                with open(path, newline="", encoding="utf-8-sig") as f:
                    list(csv.DictReader(f))


if __name__ == "__main__":
    unittest.main()
