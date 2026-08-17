"""
Cleanup logic for flagged AWS resources.

Supports dry-run (default, always safe) and execute (destructive,
requires explicit confirmation) modes. Only EBS volumes and Elastic
IPs are eligible for automated cleanup — EC2 instance termination is
intentionally excluded, since "underutilized" is a judgment call that
deserves human review, unlike an orphaned volume or unassociated IP.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import boto3

from auditor.utils.rate_limiter import with_retry

CLEANUP_ELIGIBLE_TYPES = {"EBS Volume", "Elastic IP"}

DEFAULT_LOG_PATH = Path("reports_output") / "cleanup_log.jsonl"


class CleanupError(Exception):
    """Raised when a cleanup action fails for a specific resource."""


@with_retry()
def _delete_ebs_volume(ec2_client, volume_id: str) -> None:
    ec2_client.delete_volume(VolumeId=volume_id)


@with_retry()
def _release_eip(ec2_client, allocation_id: str) -> None:
    ec2_client.release_address(AllocationId=allocation_id)


def filter_cleanup_eligible(findings: list[dict]) -> list[dict]:
    """Return only findings that are safe/supported for automated cleanup."""
    return [f for f in findings if f["resource_type"] in CLEANUP_ELIGIBLE_TYPES]


def _log_cleanup_action(log_path: Path, entry: dict) -> None:
    """Append a single cleanup action to a JSONL audit log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def execute_cleanup(
    session: boto3.Session,
    region: str,
    findings: list[dict],
    log_path: Path = DEFAULT_LOG_PATH,
) -> dict:
    """
    Actually delete the given findings' resources. This is DESTRUCTIVE
    and irreversible — callers (the CLI layer) are responsible for
    obtaining explicit user confirmation before calling this function.

    Returns a summary dict of what succeeded and what failed.
    """
    ec2 = session.client("ec2", region_name=region)

    succeeded = []
    failed = []

    for finding in findings:
        resource_type = finding["resource_type"]
        resource_id = finding["resource_id"]

        try:
            if resource_type == "EBS Volume":
                _delete_ebs_volume(ec2, resource_id)
            elif resource_type == "Elastic IP":
                _release_eip(ec2, resource_id)
            else:
                raise CleanupError(f"Unsupported resource type for cleanup: {resource_type}")

            succeeded.append(finding)
            _log_cleanup_action(log_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "deleted",
                "resource_type": resource_type,
                "resource_id": resource_id,
                "region": region,
                "estimated_monthly_savings_usd": finding["estimated_monthly_cost_usd"],
            })

        except Exception as e:
            failed.append({"finding": finding, "error": str(e)})
            _log_cleanup_action(log_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "failed",
                "resource_type": resource_type,
                "resource_id": resource_id,
                "region": region,
                "error": str(e),
            })

    total_savings = round(sum(f["estimated_monthly_cost_usd"] for f in succeeded), 2)

    return {
        "succeeded": succeeded,
        "failed": failed,
        "total_deleted": len(succeeded),
        "total_failed": len(failed),
        "total_monthly_savings_usd": total_savings,
    }