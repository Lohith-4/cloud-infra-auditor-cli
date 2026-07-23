"""
Scanner: underutilized EC2 instances.

Identifies running EC2 instances whose average CPU utilization over a
configurable lookback window (default 14 days) falls below a threshold
(default 5%). These are strong candidates for downsizing or termination
since they're consuming compute budget while doing very little work.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import boto3

from auditor.utils.rate_limiter import with_retry

# Rough on-demand EC2 pricing, USD/hour, us-east-1 tier. Real pricing
# varies by region; this is for surfacing relative cost impact.
EC2_HOURLY_PRICE = {
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "t3.large": 0.0832,
    "m5.large": 0.096,
    "m5.xlarge": 0.192,
    "m5.2xlarge": 0.384,
    "c5.large": 0.085,
    "c5.xlarge": 0.17,
    "r5.large": 0.126,
}

DEFAULT_HOURLY_PRICE = 0.10  # fallback for unrecognized instance types
HOURS_PER_MONTH = 730


@with_retry()
def _describe_running_instances(ec2_client) -> list[dict]:
    """Fetch all running EC2 instances, handling pagination."""
    instances = []
    paginator = ec2_client.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page["Reservations"]:
            instances.extend(reservation["Instances"])
    return instances


@with_retry()
def _get_average_cpu_utilization(
    cloudwatch_client, instance_id: str, days: int
) -> float | None:
    """
    Query CloudWatch for average CPUUtilization over the given lookback
    window. Returns None if no data points exist (e.g. instance too new,
    or CloudWatch monitoring not enabled).
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,  # daily granularity
        Statistics=["Average"],
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None

    return sum(dp["Average"] for dp in datapoints) / len(datapoints)


def _estimate_monthly_cost(instance_type: str) -> float:
    hourly_price = EC2_HOURLY_PRICE.get(instance_type, DEFAULT_HOURLY_PRICE)
    return round(hourly_price * HOURS_PER_MONTH, 2)


def scan_underutilized_instances(
    session: boto3.Session,
    region: str,
    days: int = 14,
    cpu_threshold: float = 5.0,
) -> list[dict]:
    """
    Return a list of running EC2 instances whose average CPU utilization
    over the lookback window is below the given threshold.

    Instances with no CloudWatch data (too new, monitoring disabled) are
    skipped rather than flagged, since we can't make a confident judgment
    without data.
    """
    ec2 = session.client("ec2", region_name=region)
    cloudwatch = session.client("cloudwatch", region_name=region)

    instances = _describe_running_instances(ec2)

    findings = []
    for inst in instances:
        instance_id = inst["InstanceId"]
        instance_type = inst.get("InstanceType", "unknown")

        avg_cpu = _get_average_cpu_utilization(cloudwatch, instance_id, days)

        if avg_cpu is None:
            continue  # no data — can't judge, skip rather than guess

        if avg_cpu >= cpu_threshold:
            continue  # instance is actually being used

        name_tag = next(
            (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
            "(no name tag)",
        )

        findings.append({
            "resource_type": "EC2 Instance",
            "resource_id": instance_id,
            "name": name_tag,
            "region": region,
            "instance_type": instance_type,
            "avg_cpu_percent": round(avg_cpu, 2),
            "lookback_days": days,
            "estimated_monthly_cost_usd": _estimate_monthly_cost(instance_type),
            "reason": f"Average CPU utilization ({round(avg_cpu, 2)}%) is below "
                      f"{cpu_threshold}% threshold over {days} days",
        })

    return findings