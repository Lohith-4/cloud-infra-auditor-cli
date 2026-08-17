"""
Tests for CSV and JSON export of scan findings.
"""

import csv
import json
from pathlib import Path

from auditor.reports.exporter import export_to_csv, export_to_json


def _sample_findings():
    return [
        {
            "resource_type": "EBS Volume",
            "resource_id": "vol-123",
            "name": "test-vol",
            "region": "us-east-1",
            "size_gb": 100,
            "volume_type": "gp3",
            "estimated_monthly_cost_usd": 8.0,
            "reason": "Volume is unattached",
        },
        {
            "resource_type": "Elastic IP",
            "resource_id": "eip-456",
            "name": "(no name tag)",
            "region": "us-east-1",
            "public_ip": "3.3.3.3",
            "estimated_monthly_cost_usd": 3.65,
            "reason": "Elastic IP is unassociated",
        },
    ]


def test_export_to_csv_creates_file_with_correct_rows(tmp_path):
    output_dir = tmp_path / "reports_test"
    filepath = export_to_csv(_sample_findings(), output_dir=output_dir)

    assert filepath.exists()
    assert filepath.suffix == ".csv"

    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["resource_id"] == "vol-123"
    assert rows[0]["estimated_monthly_cost_usd"] == "8.0"
    assert rows[1]["resource_id"] == "eip-456"


def test_export_to_json_creates_file_with_full_audit_structure(tmp_path):
    output_dir = tmp_path / "reports_test"
    audit = {
        "region": "us-east-1",
        "scanned_at": "2026-01-01T00:00:00+00:00",
        "findings": _sample_findings(),
        "summary": {
            "total_findings": 2,
            "total_estimated_monthly_cost_usd": 11.65,
            "by_resource_type": {
                "EBS Volume": {"count": 1, "cost": 8.0},
                "Elastic IP": {"count": 1, "cost": 3.65},
            },
        },
    }

    filepath = export_to_json(audit, output_dir=output_dir)

    assert filepath.exists()
    assert filepath.suffix == ".json"

    with open(filepath, encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["region"] == "us-east-1"
    assert loaded["summary"]["total_findings"] == 2
    assert len(loaded["findings"]) == 2


def test_export_to_csv_creates_output_directory_if_missing(tmp_path):
    output_dir = tmp_path / "does_not_exist_yet"
    assert not output_dir.exists()

    export_to_csv(_sample_findings(), output_dir=output_dir)

    assert output_dir.exists()