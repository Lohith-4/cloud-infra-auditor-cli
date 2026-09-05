"""
Tests for AWS authentication/session handling.
Uses moto to mock AWS - no real account, no network calls, no cost.
"""

import pytest
import boto3
from moto import mock_aws

from auditor.providers.aws.auth import (
    get_session,
    get_account_identity,
    assume_role,
    AWSAuthError,
)


@mock_aws
def test_get_session_with_valid_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    session = boto3.Session(region_name="us-east-1")
    sts = session.client("sts")
    identity = sts.get_caller_identity()

    assert "Account" in identity
    assert "Arn" in identity


@mock_aws
def test_get_account_identity_returns_expected_fields(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    session = boto3.Session(region_name="us-east-1")
    identity = get_account_identity(session)

    assert "account_id" in identity
    assert "arn" in identity
    assert "user_id" in identity


def test_get_session_raises_clean_error_for_missing_profile():
    with pytest.raises(AWSAuthError):
        get_session(profile="this-profile-does-not-exist-12345", region="us-east-1")


@mock_aws
def test_assume_role_returns_scoped_session(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    base_session = boto3.Session(region_name="us-east-1")

    scoped_session = assume_role(
        base_session,
        role_arn="arn:aws:iam::123456789012:role/test-role",
        session_name="test-session",
        region="us-east-1",
    )

    identity = scoped_session.client("sts").get_caller_identity()
    assert "Account" in identity
    assert "Arn" in identity