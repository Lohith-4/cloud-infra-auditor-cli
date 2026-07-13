"""
Tests for the CLI's handling of authentication failures.
"""

from typer.testing import CliRunner

from auditor.cli import app

runner = CliRunner()


def test_scan_ebs_fails_cleanly_without_credentials():
    """Running scan ebs with no valid AWS credentials should exit with
    code 1 and print a clean error — never a raw traceback."""
    result = runner.invoke(app, ["scan", "ebs", "--profile", "nonexistent-profile-xyz"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.stdout