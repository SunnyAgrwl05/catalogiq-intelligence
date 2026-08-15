import csv
import os
import tempfile
import unittest

from pipeline.audit_log import (
    AuditRecord,
    filter_audit_log,
    load_audit_log,
    record_audit,
)


class TestAuditLogRecording(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.audit_path = os.path.join(self.tmp_dir, "review_audit_log.csv")

    def tearDown(self):
        if os.path.exists(self.audit_path):
            os.unlink(self.audit_path)
        os.rmdir(self.tmp_dir)

    def test_record_creates_file(self):
        record_audit(
            product_id="P001", field="manufacturer",
            action="Accept", old_value="Moen", new_value="Moen",
            path=self.audit_path,
        )
        self.assertTrue(os.path.exists(self.audit_path))

    def test_record_writes_header(self):
        record_audit(
            product_id="P001", field="manufacturer",
            action="Accept", old_value="Moen", new_value="Moen",
            path=self.audit_path,
        )
        with open(self.audit_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, [
                "timestamp", "product_id", "field", "action", "old_value", "new_value",
            ])

    def test_record_correct_action(self):
        record_audit(
            product_id="P002", field="brand",
            action="Correct", old_value="Acme", new_value="Moen",
            path=self.audit_path,
        )
        records = load_audit_log(self.audit_path)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.product_id, "P002")
        self.assertEqual(r.field, "brand")
        self.assertEqual(r.action, "Correct")
        self.assertEqual(r.old_value, "Acme")
        self.assertEqual(r.new_value, "Moen")

    def test_record_mark_unknown_action(self):
        record_audit(
            product_id="P003", field="category",
            action="Mark Unknown", old_value="Faucets", new_value="UNKNOWN",
            path=self.audit_path,
        )
        records = load_audit_log(self.audit_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].action, "Mark Unknown")
        self.assertEqual(records[0].new_value, "UNKNOWN")

    def test_record_has_timestamp(self):
        record_audit(
            product_id="P001", field="manufacturer",
            action="Accept", old_value="Moen", new_value="Moen",
            path=self.audit_path,
        )
        records = load_audit_log(self.audit_path)
        self.assertTrue(len(records[0].timestamp) > 0)

    def test_multiple_records_append(self):
        record_audit(
            product_id="P001", field="manufacturer",
            action="Accept", old_value="Moen", new_value="Moen",
            path=self.audit_path,
        )
        record_audit(
            product_id="P001", field="brand",
            action="Correct", old_value="Acme", new_value="Moen",
            path=self.audit_path,
        )
        records = load_audit_log(self.audit_path)
        self.assertEqual(len(records), 2)

    def test_load_empty_when_no_file(self):
        records = load_audit_log("/nonexistent/path.csv")
        self.assertEqual(records, [])


class TestAuditLogFiltering(unittest.TestCase):
    def _make_records(self):
        return [
            AuditRecord(timestamp="2026-01-01T00:00:00", product_id="P001", field="manufacturer", action="Accept", old_value="Moen", new_value="Moen"),
            AuditRecord(timestamp="2026-01-01T00:01:00", product_id="P001", field="brand", action="Correct", old_value="Acme", new_value="Moen"),
            AuditRecord(timestamp="2026-01-01T00:02:00", product_id="P002", field="manufacturer", action="Mark Unknown", old_value="Delta", new_value="UNKNOWN"),
            AuditRecord(timestamp="2026-01-01T00:03:00", product_id="P002", field="category", action="Accept", old_value="Valves", new_value="Valves"),
        ]

    def test_filter_by_product_id(self):
        records = self._make_records()
        filtered = filter_audit_log(records, product_id="P001")
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(r.product_id == "P001" for r in filtered))

    def test_filter_by_field(self):
        records = self._make_records()
        filtered = filter_audit_log(records, field="manufacturer")
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(r.field == "manufacturer" for r in filtered))

    def test_filter_by_both(self):
        records = self._make_records()
        filtered = filter_audit_log(records, product_id="P002", field="category")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].product_id, "P002")
        self.assertEqual(filtered[0].field, "category")

    def test_filter_no_match(self):
        records = self._make_records()
        filtered = filter_audit_log(records, product_id="P999")
        self.assertEqual(len(filtered), 0)

    def test_filter_no_criteria_returns_all(self):
        records = self._make_records()
        filtered = filter_audit_log(records)
        self.assertEqual(len(filtered), 4)


class TestAuditLogRoundtrip(unittest.TestCase):
    def test_write_and_read_back(self):
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, "audit.csv")
        try:
            record_audit(
                product_id="P100", field="mpn",
                action="Correct", old_value="XYZ-123", new_value="ABC-456",
                path=path,
            )
            record_audit(
                product_id="P100", field="mpn",
                action="Accept", old_value="ABC-456", new_value="ABC-456",
                path=path,
            )
            records = load_audit_log(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].old_value, "XYZ-123")
            self.assertEqual(records[0].new_value, "ABC-456")
            self.assertEqual(records[1].action, "Accept")
        finally:
            if os.path.exists(path):
                os.unlink(path)
            os.rmdir(tmp_dir)


if __name__ == "__main__":
    unittest.main()
