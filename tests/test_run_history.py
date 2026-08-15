import os
import tempfile
import unittest

from pipeline.run_history import (
    RunRecord,
    load_history,
    recent_history,
    record_run,
)


class TestRunHistoryRecording(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.tmp_dir, "run_history.csv")

    def tearDown(self):
        if os.path.exists(self.history_path):
            os.unlink(self.history_path)
        os.rmdir(self.tmp_dir)

    def test_record_creates_file(self):
        record_run(
            n_records=20, overall_field_accuracy=0.95,
            auto_approved_pct=0.6, conflict_count=2,
            path=self.history_path,
        )
        self.assertTrue(os.path.exists(self.history_path))

    def test_record_writes_header(self):
        record_run(
            n_records=20, overall_field_accuracy=0.95,
            auto_approved_pct=0.6, conflict_count=2,
            path=self.history_path,
        )
        import csv
        with open(self.history_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, [
                "timestamp", "n_records", "overall_field_accuracy",
                "auto_approved_pct", "conflict_count",
            ])

    def test_record_has_timestamp(self):
        record_run(
            n_records=10, overall_field_accuracy=0.8,
            auto_approved_pct=0.5, conflict_count=1,
            path=self.history_path,
        )
        records = load_history(self.history_path)
        self.assertEqual(len(records), 1)
        self.assertTrue(len(records[0].timestamp) > 0)

    def test_record_stores_values(self):
        record_run(
            n_records=50, overall_field_accuracy=0.92,
            auto_approved_pct=0.7, conflict_count=3,
            path=self.history_path,
        )
        records = load_history(self.history_path)
        r = records[0]
        self.assertEqual(r.n_records, 50)
        self.assertAlmostEqual(r.overall_field_accuracy, 0.92, places=3)
        self.assertAlmostEqual(r.auto_approved_pct, 0.7, places=3)
        self.assertEqual(r.conflict_count, 3)

    def test_multiple_records_append(self):
        record_run(
            n_records=10, overall_field_accuracy=0.8,
            auto_approved_pct=0.5, conflict_count=1,
            path=self.history_path,
        )
        record_run(
            n_records=20, overall_field_accuracy=0.9,
            auto_approved_pct=0.6, conflict_count=0,
            path=self.history_path,
        )
        records = load_history(self.history_path)
        self.assertEqual(len(records), 2)

    def test_load_empty_when_no_file(self):
        records = load_history("/nonexistent/path.csv")
        self.assertEqual(records, [])


class TestRunHistoryLoading(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.tmp_dir, "run_history.csv")

    def tearDown(self):
        if os.path.exists(self.history_path):
            os.unlink(self.history_path)
        os.rmdir(self.tmp_dir)

    def test_load_returns_run_records(self):
        record_run(
            n_records=10, overall_field_accuracy=0.8,
            auto_approved_pct=0.5, conflict_count=1,
            path=self.history_path,
        )
        records = load_history(self.history_path)
        self.assertIsInstance(records[0], RunRecord)

    def test_malformed_rows_are_skipped(self):
        with open(self.history_path, "w", newline="", encoding="utf-8") as f:
            f.write("timestamp,n_records,overall_field_accuracy,auto_approved_pct,conflict_count\n")
            f.write("2026-01-01T00:00:00,10,0.8,0.5,1\n")
            f.write("bad_row,data,here\n")
            f.write("2026-01-02T00:00:00,20,0.9,0.6,0\n")
        records = load_history(self.history_path)
        self.assertEqual(len(records), 2)

    def test_empty_csv_returns_empty(self):
        with open(self.history_path, "w", newline="", encoding="utf-8") as f:
            f.write("timestamp,n_records,overall_field_accuracy,auto_approved_pct,conflict_count\n")
        records = load_history(self.history_path)
        self.assertEqual(len(records), 0)


class TestRecentHistory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.tmp_dir, "run_history.csv")

    def tearDown(self):
        if os.path.exists(self.history_path):
            os.unlink(self.history_path)
        os.rmdir(self.tmp_dir)

    def test_returns_most_recent_n(self):
        for i in range(5):
            record_run(
                n_records=10 + i, overall_field_accuracy=0.8 + i * 0.02,
                auto_approved_pct=0.5, conflict_count=i,
                path=self.history_path,
            )
        recent = recent_history(n=3, path=self.history_path)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].n_records, 12)
        self.assertEqual(recent[-1].n_records, 14)

    def test_returns_all_when_fewer_than_n(self):
        for i in range(2):
            record_run(
                n_records=10, overall_field_accuracy=0.8,
                auto_approved_pct=0.5, conflict_count=0,
                path=self.history_path,
            )
        recent = recent_history(n=5, path=self.history_path)
        self.assertEqual(len(recent), 2)

    def test_empty_when_no_history(self):
        recent = recent_history(n=5, path=self.history_path)
        self.assertEqual(len(recent), 0)


if __name__ == "__main__":
    unittest.main()
