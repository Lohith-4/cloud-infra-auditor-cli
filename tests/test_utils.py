"""
Tests for region utilities and rate-limit retry logic.
"""

import boto3
from moto import mock_aws
from botocore.exceptions import ClientError

from auditor.utils.regions import list_available_regions, validate_region, FALLBACK_REGIONS
from auditor.utils.rate_limiter import with_retry


@mock_aws
def test_list_available_regions_returns_region_list(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")

    session = boto3.Session(region_name="us-east-1")
    regions = list_available_regions(session)

    assert isinstance(regions, list)
    assert len(regions) > 0
    assert "us-east-1" in regions


def test_validate_region_true_for_known_region():
    assert validate_region("us-east-1", FALLBACK_REGIONS) is True


def test_validate_region_false_for_unknown_region():
    assert validate_region("not-a-real-region-99", FALLBACK_REGIONS) is False


def test_with_retry_succeeds_after_transient_throttle():
    call_count = {"n": 0}

    @with_retry(max_attempts=5, base_delay=0.01, max_delay=0.05)
    def flaky_call():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
                "DescribeInstances",
            )
        return "success"

    result = flaky_call()
    assert result == "success"
    assert call_count["n"] == 3


def test_with_retry_reraises_non_throttle_errors_immediately():
    call_count = {"n": 0}

    @with_retry(max_attempts=5, base_delay=0.01)
    def denied_call():
        call_count["n"] += 1
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "DescribeInstances",
        )

    try:
        denied_call()
        assert False, "Expected ClientError to be raised"
    except ClientError as e:
        assert e.response["Error"]["Code"] == "AccessDenied"

    assert call_count["n"] == 1