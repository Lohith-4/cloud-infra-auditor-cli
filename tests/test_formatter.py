"""
Tests for Rich table/panel formatting. Since Rich output is visual,
we mainly verify these functions run without errors on realistic data
shapes, rather than asserting on exact rendered text.
"""

from rich.console import Console

from auditor.reports.formatter import render_findings_table, render_summary_panel


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
            "reason": "Volume is unattached (state: available)",
        },
        {
            "resource_type": "Elastic IP",
            "resource_id": "eip-456",
            "name": "(no name tag)",
            "region": "us-east-1",
            "public_ip": "3.3.3.3",
            "estimated_monthly_cost_usd": 3.65,
            "reason": "Elastic IP is allocated but not associated with any resource",
        },
    ]


def test_render_findings_table_runs_without_error():
    console = Console(record=True)
    render_findings_table(console, _sample_findings(), title="Test Findings")
    output = console.export_text()
    assert "Test Findings" in output
    assert "vol-123" in output


def test_render_findings_table_handles_empty_list():
    console = Console(record=True)
    render_findings_table(console, [], title="Empty Test")
    output = console.export_text()
    assert "No findings" in output


def test_render_summary_panel_with_findings():
    console = Console(record=True)
    audit = {
        "region": "us-east-1",
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
    render_summary_panel(console, audit)
    output = console.export_text()
    assert "11.65" in output
    assert "us-east-1" in output


def test_render_summary_panel_when_clean():
    console = Console(record=True)
    audit = {
        "region": "us-east-1",
        "findings": [],
        "summary": {
            "total_findings": 0,
            "total_estimated_monthly_cost_usd": 0,
            "by_resource_type": {},
        },
    }
    render_summary_panel(console, audit)
    output = console.export_text()
    assert "Clean audit" in output