"""
Tests for the EC2 underutilization scanner.

moto doesn't auto-generate CloudWatch metrics for running instances,
so we manually put fake CPUUtilization datapoints to simulate both
an idle instance and a busy one.
"""

from datetime import datetime, timedelta, timezone

import boto3
from moto import mock_aws

from auditor.providers.aws.scanners.ec2 import scan_underutilized_instances


@mock_aws
def test_scan_flags_instance_with_low_cpu(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")
    cloudwatch = session.client("cloudwatch", region_name="us-east-1")

    reservation = ec2.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": "idle-test-instance"}],
        }],
    )
    instance_id = reservation["Instances"][0]["InstanceId"]

    # Simulate 14 days of low CPU (2% average)
    now = datetime.now(timezone.utc)
    for i in range(14):
        cloudwatch.put_metric_data(
            Namespace="AWS/EC2",
            MetricData=[{
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - timedelta(days=i),
                "Value": 2.0,
                "Unit": "Percent",
            }],
        )

    findings = scan_underutilized_instances(session, "us-east-1", days=14, cpu_threshold=5.0)

    assert len(findings) == 1
    assert findings[0]["resource_id"] == instance_id
    assert findings[0]["avg_cpu_percent"] == 2.0
    assert findings[0]["name"] == "idle-test-instance"


@mock_aws
def test_scan_ignores_instance_with_high_cpu(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")
    cloudwatch = session.client("cloudwatch", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    instance_id = reservation["Instances"][0]["InstanceId"]

    now = datetime.now(timezone.utc)
    for i in range(14):
        cloudwatch.put_metric_data(
            Namespace="AWS/EC2",
            MetricData=[{
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - timedelta(days=i),
                "Value": 65.0,  # clearly active
                "Unit": "Percent",
            }],
        )

    findings = scan_underutilized_instances(session, "us-east-1", days=14, cpu_threshold=5.0)

    assert len(findings) == 0


@mock_aws
def test_scan_skips_instance_with_no_metric_data(monkeypatch):
    """An instance with zero CloudWatch datapoints should be skipped,
    not flagged as a false-positive."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")
    ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    # No put_metric_data call — no CloudWatch history exists

    findings = scan_underutilized_instances(session, "us-east-1", days=14, cpu_threshold=5.0)

    assert len(findings) == 0