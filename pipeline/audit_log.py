"""
Audit trail for human review decisions.

Every action taken in the Human Review workflow (Accept, Correct, Mark
Unknown) is recorded with a timestamp, product_id, field, action type,
old value, and new value. The log is append-only and stored as a CSV
for lightweight persistence.

The schema is designed so an actor/user field can be added later without
breaking existing records.
"""

from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

AUDIT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "review_audit_log.csv"
)

FIELDNAMES = [
    "timestamp",
    "product_id",
    "field",
    "action",
    "old_value",
    "new_value",
]


@dataclass
class AuditRecord:
    timestamp: str
    product_id: str
    field: str
    action: str
    old_value: str
    new_value: str


def record_audit(
    product_id: str,
    field: str,
    action: str,
    old_value: str | None,
    new_value: str | None,
    path: str = AUDIT_LOG_PATH,
) -> AuditRecord:
    """Append a single audit record to the log file.

    Parameters
    ----------
    product_id : str
        The product identifier.
    field : str
        The field that was reviewed (e.g. "manufacturer", "brand").
    action : str
        One of "Accept", "Correct", "Mark Unknown".
    old_value : str or None
        The value before the action was taken.
    new_value : str or None
        The value after the action was taken.
    path : str
        Override path for testing.
    """
    record = AuditRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        product_id=product_id,
        field=field,
        action=action,
        old_value=old_value or "",
        new_value=new_value or "",
    )
    file_exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(record))
    return record


def load_audit_log(path: str = AUDIT_LOG_PATH) -> list[AuditRecord]:
    """Load all audit records from the log file."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [AuditRecord(**row) for row in csv.DictReader(f)]


def filter_audit_log(
    records: list[AuditRecord],
    product_id: str | None = None,
    field: str | None = None,
) -> list[AuditRecord]:
    """Filter audit records by product_id and/or field."""
    result = records
    if product_id:
        result = [r for r in result if r.product_id == product_id]
    if field:
        result = [r for r in result if r.field == field]
    return result
