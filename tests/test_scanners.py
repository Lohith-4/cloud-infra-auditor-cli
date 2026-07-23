"""
Tests for EBS and Elastic IP scanners.
Uses moto to simulate real AWS resources — no real account needed.
"""

import boto3
from moto import mock_aws

from auditor.providers.aws.scanners.ebs import scan_unattached_volumes
from auditor.providers.aws.scanners.eip import scan_unassociated_eips


@mock_aws
def test_scan_unattached_volumes_finds_orphaned_volume(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")

    # Create an unattached volume (never attached to any instance)
    ec2.create_volume(
        AvailabilityZone="us-east-1a",
        Size=100,
        VolumeType="gp3",
        TagSpecifications=[{
            "ResourceType": "volume",
            "Tags": [{"Key": "Name", "Value": "orphaned-test-volume"}],
        }],
    )

    findings = scan_unattached_volumes(session, "us-east-1")

    assert len(findings) == 1
    assert findings[0]["size_gb"] == 100
    assert findings[0]["volume_type"] == "gp3"
    assert findings[0]["name"] == "orphaned-test-volume"
    assert findings[0]["estimated_monthly_cost_usd"] == 8.0  # 100GB * $0.08


@mock_aws
def test_scan_unattached_volumes_ignores_attached_volume(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")

    # Create an instance, then attach a volume to it
    reservation = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    instance_id = reservation["Instances"][0]["InstanceId"]

    volume = ec2.create_volume(AvailabilityZone="us-east-1a", Size=50, VolumeType="gp2")
    ec2.attach_volume(
        VolumeId=volume["VolumeId"],
        InstanceId=instance_id,
        Device="/dev/sdf",
    )

    findings = scan_unattached_volumes(session, "us-east-1")

    assert len(findings) == 0  # attached volume should NOT be flagged


@mock_aws
def test_scan_unassociated_eips_finds_orphaned_eip(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")

    # Allocate an EIP but never associate it with anything
    ec2.allocate_address(Domain="vpc")

    findings = scan_unassociated_eips(session, "us-east-1")

    assert len(findings) == 1
    assert findings[0]["resource_type"] == "Elastic IP"
    assert findings[0]["estimated_monthly_cost_usd"] == 3.65  # 0.005 * 730


@mock_aws
def test_scan_unassociated_eips_ignores_associated_eip(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2", region_name="us-east-1")

    reservation = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)
    instance_id = reservation["Instances"][0]["InstanceId"]

    address = ec2.allocate_address(Domain="vpc")
    ec2.associate_address(InstanceId=instance_id, AllocationId=address["AllocationId"])

    findings = scan_unassociated_eips(session, "us-east-1")

    assert len(findings) == 0  # associated EIP should NOT be flagged