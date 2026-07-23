"""
Scanner: unassociated Elastic IPs.

AWS charges for an Elastic IP that is allocated but NOT attached to
a running instance/ENI. These are easy to forget after decommissioning
an instance, and quietly accumulate cost over time.
"""

from __future__ import annotations

import boto3

from auditor.utils.rate_limiter import with_retry

# AWS charges roughly $0.005/hour for an unattached EIP (varies by region).
# ~730 hours/month is the standard AWS billing approximation for a month.
EIP_HOURLY_COST_USD = 0.005
HOURS_PER_MONTH = 730


@with_retry()
def _describe_all_addresses(ec2_client) -> list[dict]:
    """Fetch all Elastic IP addresses in the region."""
    response = ec2_client.describe_addresses()
    return response["Addresses"]


def scan_unassociated_eips(session: boto3.Session, region: str) -> list[dict]:
    """
    Return a list of Elastic IPs that are allocated but not associated
    with any running instance or network interface.
    """
    ec2 = session.client("ec2", region_name=region)
    all_addresses = _describe_all_addresses(ec2)

    findings = []
    for addr in all_addresses:
        # An EIP is "in use" if it has an AssociationId (attached to
        # an instance or ENI). No AssociationId = wasted allocation.
        if "AssociationId" in addr:
            continue

        name_tag = next(
            (t["Value"] for t in addr.get("Tags", []) if t["Key"] == "Name"),
            "(no name tag)",
        )

        findings.append({
            "resource_type": "Elastic IP",
            "resource_id": addr.get("AllocationId", addr.get("PublicIp")),
            "name": name_tag,
            "region": region,
            "public_ip": addr.get("PublicIp", "unknown"),
            "domain": addr.get("Domain", "unknown"),
            "estimated_monthly_cost_usd": round(EIP_HOURLY_COST_USD * HOURS_PER_MONTH, 2),
            "reason": "Elastic IP is allocated but not associated with any resource",
        })

    return findings