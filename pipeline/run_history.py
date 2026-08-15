"""
Persistent run-history tracking for catalog quality trend analysis.

After each pipeline run, a summary row is appended to a local CSV file
recording key quality metrics. This enables a lightweight Catalog Health
trend view without requiring a database.
"""

from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "run_history.csv"
)

FIELDNAMES = [
    "timestamp",
    "n_records",
    "overall_field_accuracy",
    "auto_approved_pct",
    "conflict_count",
]


@dataclass
class RunRecord:
    timestamp: str
    n_records: int
    overall_field_accuracy: float
    auto_approved_pct: float
    conflict_count: int


def record_run(
    n_records: int,
    overall_field_accuracy: float,
    auto_approved_pct: float,
    conflict_count: int,
    path: str = HISTORY_PATH,
) -> RunRecord:
    """Append a single run summary row to the history file."""
    record = RunRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        n_records=n_records,
        overall_field_accuracy=round(overall_field_accuracy, 4),
        auto_approved_pct=round(auto_approved_pct, 4),
        conflict_count=conflict_count,
    )
    file_exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(record))
    return record


def load_history(path: str = HISTORY_PATH) -> list[RunRecord]:
    """Load all run records from the history file."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    records = []
    for row in rows:
        try:
            records.append(RunRecord(
                timestamp=row["timestamp"],
                n_records=int(row["n_records"]),
                overall_field_accuracy=float(row["overall_field_accuracy"]),
                auto_approved_pct=float(row["auto_approved_pct"]),
                conflict_count=int(row["conflict_count"]),
            ))
        except (ValueError, KeyError):
            continue
    return records


def recent_history(n: int = 10, path: str = HISTORY_PATH) -> list[RunRecord]:
    """Return the most recent N run records (newest last)."""
    return load_history(path)[-n:]
