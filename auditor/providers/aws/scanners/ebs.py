"""
Scanner: unattached (orphaned) EBS volumes.

An EBS volume in the 'available' state is not attached to any EC2
instance, meaning it's provisioned storage that AWS is billing for
but nothing is using. These are one of the most common sources of
silent cloud waste.
"""

from __future__ import annotations

import boto3

from auditor.utils.rate_limiter import with_retry

# Rough on-demand EBS pricing, USD per GB-month, us-east-1 pricing tier.
# Real pricing varies by region/volume type; this is a reasonable estimate
# for surfacing relative cost impact, not an exact billing figure.
EBS_PRICE_PER_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

DEFAULT_PRICE_PER_GB_MONTH = 0.10  # fallback if volume type is unrecognized


@with_retry()
def _describe_all_volumes(ec2_client) -> list[dict]:
    """Fetch all EBS volumes in the region, handling pagination."""
    volumes = []
    paginator = ec2_client.get_paginator("describe_volumes")
    for page in paginator.paginate():
        volumes.extend(page["Volumes"])
    return volumes


def _estimate_monthly_cost(size_gb: int, volume_type: str) -> float:
    price_per_gb = EBS_PRICE_PER_GB_MONTH.get(volume_type, DEFAULT_PRICE_PER_GB_MONTH)
    return round(size_gb * price_per_gb, 2)


def scan_unattached_volumes(session: boto3.Session, region: str) -> list[dict]:
    """
    Return a list of unattached (orphaned) EBS volumes in the given region.

    Each entry contains enough detail for both human-readable reporting
    and safe cleanup targeting (volume_id is the key identifier needed
    to delete a volume later).
    """
    ec2 = session.client("ec2", region_name=region)
    all_volumes = _describe_all_volumes(ec2)

    findings = []
    for vol in all_volumes:
        if vol["State"] != "available":
            continue  # attached or in-use volumes are not waste

        size_gb = vol["Size"]
        volume_type = vol.get("VolumeType", "gp2")

        # Pull the Name tag if present, for human-readable reports
        name_tag = next(
            (t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"),
            "(no name tag)",
        )

        findings.append({
            "resource_type": "EBS Volume",
            "resource_id": vol["VolumeId"],
            "name": name_tag,
            "region": region,
            "size_gb": size_gb,
            "volume_type": volume_type,
            "availability_zone": vol.get("AvailabilityZone", "unknown"),
            "created_at": str(vol.get("CreateTime", "unknown")),
            "estimated_monthly_cost_usd": _estimate_monthly_cost(size_gb, volume_type),
            "reason": "Volume is unattached (state: available)",
        })

    return findings