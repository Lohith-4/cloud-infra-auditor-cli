"""
Export scan findings to CSV and JSON files for management review.

Both exporters consume the same findings/audit data structure the
formatter and aggregator already use, keeping one consistent data
contract across the whole application.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("reports_output")

# Superset of all possible finding fields across EBS, EIP, EC2 scanners.
# Using a fixed column order keeps CSV output consistent even when a
# given finding type doesn't populate every field.
CSV_COLUMNS = [
    "resource_type",
    "resource_id",
    "name",
    "region",
    "size_gb",
    "volume_type",
    "public_ip",
    "instance_type",
    "avg_cpu_percent",
    "estimated_monthly_cost_usd",
    "reason",
]


def _timestamped_filename(prefix: str, extension: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def export_to_csv(findings: list[dict], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """
    Write findings to a timestamped CSV file. Returns the path written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / _timestamped_filename("audit_report", "csv")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding)

    return filepath


def export_to_json(audit: dict, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """
    Write the full audit result (findings + summary + metadata) to a
    timestamped JSON file. Returns the path written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / _timestamped_filename("audit_report", "json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, default=str)

    return filepath