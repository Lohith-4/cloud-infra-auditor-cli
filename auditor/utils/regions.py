"""
AWS region mapping and validation utilities.

Provides a way to list currently valid AWS regions and validate
user-supplied region strings before a scan begins, rather than letting
an invalid region fail deep inside a scan with a confusing error.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError


FALLBACK_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
]


def list_available_regions(session: boto3.Session) -> list[str]:
    """
    Return the list of AWS regions currently enabled for this account,
    using a live EC2 DescribeRegions call.

    Falls back to a static list if the API call fails for any reason,
    so region validation never blocks the CLI entirely.
    """
    try:
        ec2 = session.client("ec2", region_name="us-east-1")
        response = ec2.describe_regions(AllRegions=False)
        return sorted(r["RegionName"] for r in response["Regions"])
    except ClientError:
        return sorted(FALLBACK_REGIONS)


def validate_region(region: str, available_regions: list[str]) -> bool:
    """Return True if the given region string is a valid, available region."""
    return region in available_regions