"""
Tests for cleanup filtering and execution logic.
"""

from pathlib import Path

import boto3
from moto import mock_aws

from auditor.providers.aws.scanners.cleanup import (
    filter_cleanup_eligible,
    execute_cleanup,
)


def _sample_findings():
    return [
        {
            "resource_type": "EBS Volume",
            "resource_id": "vol-123",
            "name": "test-vol",
            "region": "us-east-1",
            "estimated_monthly_cost_usd": 8.0,
        },
        {
            "resource_type": "Elastic IP",
            "resource_id": "eip-456",
            "name": "(no name tag)",
            "region": "us-east-1",
            "estimated_monthly_cost_usd": 3.65,
        },
        {
            "resource_type": "EC2 Instance",
            "resource_id": "i-789",
            "name": "test-instance",
            "region": "us-east-1",
            "estimated_monthly_cost_usd": 15.0,
        },
    ]


def test_filter_cleanup_eligible_excludes_ec2():
    eligible = filter_cleanup_eligible(_sample_findings())

    types_found = {f["resource_type"] for f in eligible}
    assert types_found == {"EBS Volume", "Elastic IP"}
    assert len(eligible) == 2


@mock_aws
def test_execute_cleanup_deletes_ebs_volume_and_releases_eip(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")

    volume = ec2.create_volume(AvailabilityZone="us-east-1a", Size=50, VolumeType="gp3")
    volume_id = volume["VolumeId"]

    address = ec2.allocate_address(Domain="vpc")
    allocation_id = address["AllocationId"]

    findings = [
        {
            "resource_type": "EBS Volume",
            "resource_id": volume_id,
            "estimated_monthly_cost_usd": 4.0,
        },
        {
            "resource_type": "Elastic IP",
            "resource_id": allocation_id,
            "estimated_monthly_cost_usd": 3.65,
        },
    ]

    log_path = tmp_path / "cleanup_log.jsonl"
    result = execute_cleanup(session, "us-east-1", findings, log_path=log_path)

    assert result["total_deleted"] == 2
    assert result["total_failed"] == 0
    assert result["total_monthly_savings_usd"] == 7.65

    # Confirm volume was actually deleted
    volumes = ec2.describe_volumes()["Volumes"]
    volume_ids = [v["VolumeId"] for v in volumes]
    assert volume_id not in volume_ids

    # Confirm log file was written
    assert log_path.exists()
    log_contents = log_path.read_text()
    assert volume_id in log_contents
    assert allocation_id in log_contents


@mock_aws
def test_execute_cleanup_records_failure_for_invalid_resource(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")

    findings = [
        {
            "resource_type": "EBS Volume",
            "resource_id": "vol-doesnotexist",
            "estimated_monthly_cost_usd": 4.0,
        },
    ]

    log_path = tmp_path / "cleanup_log.jsonl"
    result = execute_cleanup(session, "us-east-1", findings, log_path=log_path)

    assert result["total_deleted"] == 0
    assert result["total_failed"] == 1
    assert result["total_monthly_savings_usd"] == 0