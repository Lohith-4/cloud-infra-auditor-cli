"""
Aggregates findings from all scanners into a single unified structure.

This is the data contract the rest of the application builds on:
Week 3's Rich tables, CSV export, and JSON export all consume the
dictionary shape produced here, rather than talking to each scanner
individually.
"""

from __future__ import annotations

from datetime import datetime, timezone

import boto3

from auditor.providers.aws.scanners.ebs import scan_unattached_volumes
from auditor.providers.aws.scanners.eip import scan_unassociated_eips
from auditor.providers.aws.scanners.ec2 import scan_underutilized_instances


def run_full_audit(
    session: boto3.Session,
    region: str,
    ec2_days: int = 14,
    ec2_cpu_threshold: float = 5.0,
) -> dict:
    """
    Run every scanner against the given region and return a single
    aggregated audit result.

    Structure:
    {
        "region": str,
        "scanned_at": ISO timestamp,
        "findings": [ ...all findings from every scanner, tagged... ],
        "summary": {
            "total_findings": int,
            "total_estimated_monthly_cost_usd": float,
            "by_resource_type": {
                "EBS Volume": {"count": int, "cost": float},
                "Elastic IP": {"count": int, "cost": float},
                "EC2 Instance": {"count": int, "cost": float},
            }
        }
    }
    """
    all_findings = []

    all_findings.extend(scan_unattached_volumes(session, region))
    all_findings.extend(scan_unassociated_eips(session, region))
    all_findings.extend(
        scan_underutilized_instances(
            session, region, days=ec2_days, cpu_threshold=ec2_cpu_threshold
        )
    )

    summary = _build_summary(all_findings)

    return {
        "region": region,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "findings": all_findings,
        "summary": summary,
    }


def _build_summary(findings: list[dict]) -> dict:
    """Compute aggregate statistics from a flat list of findings."""
    by_resource_type: dict[str, dict] = {}

    for f in findings:
        resource_type = f["resource_type"]
        cost = f["estimated_monthly_cost_usd"]

        if resource_type not in by_resource_type:
            by_resource_type[resource_type] = {"count": 0, "cost": 0.0}

        by_resource_type[resource_type]["count"] += 1
        by_resource_type[resource_type]["cost"] = round(
            by_resource_type[resource_type]["cost"] + cost, 2
        )

    total_cost = round(sum(f["estimated_monthly_cost_usd"] for f in findings), 2)

    return {
        "total_findings": len(findings),
        "total_estimated_monthly_cost_usd": total_cost,
        "by_resource_type": by_resource_type,
    }