"""
Secure AWS credential handling and session management.

Supports:
- Local AWS named profiles (~/.aws/credentials, ~/.aws/config)
- Environment variable credentials (fallback, standard Boto3 behavior)
- Cross-account role assumption via STS (for auditing multiple AWS accounts)

This module intentionally never hardcodes or logs raw credentials.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
)


class AWSAuthError(Exception):
    """Raised when AWS authentication fails in a way the CLI should
    report cleanly to the user, instead of a raw traceback."""


def get_session(profile: str = "default", region: str = "us-east-1") -> boto3.Session:
    """
    Create a Boto3 session using a local named AWS profile.

    This mirrors how the AWS CLI itself resolves credentials: it checks
    ~/.aws/credentials and ~/.aws/config for the given profile name.

    Raises:
        AWSAuthError: if the profile doesn't exist or credentials are invalid.
    """
    try:
        session = boto3.Session(profile_name=profile, region_name=region)

        # Force a lightweight credential check now, rather than letting
        # the failure surface later mid-scan. This calls STS GetCallerIdentity,
        # which is a free, read-only, universally-permitted API call.
        sts = session.client("sts")
        sts.get_caller_identity()

        return session

    except ProfileNotFound as e:
        raise AWSAuthError(
            f"AWS profile '{profile}' was not found. "
            f"Run 'aws configure --profile {profile}' to set it up, "
            f"or check ~/.aws/credentials."
        ) from e

    except NoCredentialsError as e:
        raise AWSAuthError(
            "No AWS credentials could be located. "
            "Configure credentials with 'aws configure' or set "
            "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY environment variables."
        ) from e

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        raise AWSAuthError(
            f"AWS rejected the provided credentials (error: {error_code}). "
            f"Verify the access key/secret are correct and not expired."
        ) from e


def assume_role(
    session: boto3.Session,
    role_arn: str,
    session_name: str = "cloud-auditor-session",
    region: str = "us-east-1",
) -> boto3.Session:
    """
    Assume an IAM role in another AWS account and return a new session
    scoped to that role's temporary credentials.

    This is the standard pattern for FinOps/DevOps tools that need to
    audit multiple AWS accounts from a single set of base credentials
    (e.g. a central security/ops account with cross-account trust).

    Raises:
        AWSAuthError: if the role cannot be assumed (bad ARN, no trust
        relationship, insufficient permissions, etc.)
    """
    try:
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name,
        )

        creds = response["Credentials"]

        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        raise AWSAuthError(
            f"Failed to assume role '{role_arn}' (error: {error_code}). "
            f"Verify the role ARN is correct and that a trust relationship "
            f"allows this account to assume it."
        ) from e


def get_account_identity(session: boto3.Session) -> dict:
    """
    Return basic identity info (account ID, ARN, user ID) for the
    credentials backing this session. Useful for confirming which
    AWS account a scan is about to run against, before doing anything else.
    """
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    return {
        "account_id": identity["Account"],
        "arn": identity["Arn"],
        "user_id": identity["UserId"],
    }