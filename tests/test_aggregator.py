"""
Tests for the scan aggregator, proving it correctly combines findings
from all three scanners into one unified structure with accurate summaries.
"""

from datetime import datetime, timedelta, timezone

import boto3
from moto import mock_aws

from auditor.reports.aggregator import run_full_audit


@mock_aws
def test_run_full_audit_combines_all_finding_types(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")
    cloudwatch = session.client("cloudwatch", region_name="us-east-1")

    # Orphaned EBS volume
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=50, VolumeType="gp3")

    # Unassociated EIP
    ec2.allocate_address(Domain="vpc")

    # Idle EC2 instance
    reservation = ec2.run_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t2.micro"
    )
    instance_id = reservation["Instances"][0]["InstanceId"]
    now = datetime.now(timezone.utc)
    for i in range(14):
        cloudwatch.put_metric_data(
            Namespace="AWS/EC2",
            MetricData=[{
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - timedelta(days=i),
                "Value": 1.5,
                "Unit": "Percent",
            }],
        )

    audit = run_full_audit(session, "us-east-1", ec2_days=14, ec2_cpu_threshold=5.0)

    assert audit["region"] == "us-east-1"
    assert "scanned_at" in audit
    assert audit["summary"]["total_findings"] == 3

    types_found = {f["resource_type"] for f in audit["findings"]}
    assert types_found == {"EBS Volume", "Elastic IP", "EC2 Instance"}

    by_type = audit["summary"]["by_resource_type"]
    assert by_type["EBS Volume"]["count"] == 1
    assert by_type["Elastic IP"]["count"] == 1
    assert by_type["EC2 Instance"]["count"] == 1

    expected_total = round(
        by_type["EBS Volume"]["cost"]
        + by_type["Elastic IP"]["cost"]
        + by_type["EC2 Instance"]["cost"],
        2,
    )
    assert audit["summary"]["total_estimated_monthly_cost_usd"] == expected_total


@mock_aws
def test_run_full_audit_returns_empty_summary_when_clean(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    # No resources created at all

    audit = run_full_audit(session, "us-east-1")

    assert audit["summary"]["total_findings"] == 0
    assert audit["summary"]["total_estimated_monthly_cost_usd"] == 0
    assert audit["findings"] == []