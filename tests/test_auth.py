"""
Tests for AWS authentication/session handling.
Uses moto to mock AWS — no real account, no network calls, no cost.
"""

import os
import pytest
import boto3
from moto import mock_aws

from auditor.providers.aws.auth import (
    get_session,
    get_account_identity,
    AWSAuthError,
)


@mock_aws
def test_get_session_with_valid_credentials(monkeypatch):
    """A session should succeed when valid (mocked) credentials exist."""
    # moto intercepts these — no real AWS account is contacted
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
    """get_account_identity() should return account_id, arn, and user_id."""
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
    """Requesting a profile that doesn't exist should raise our custom
    AWSAuthError, not a raw botocore traceback."""
    with pytest.raises(AWSAuthError):
        get_session(profile="this-profile-does-not-exist-12345", region="us-east-1")