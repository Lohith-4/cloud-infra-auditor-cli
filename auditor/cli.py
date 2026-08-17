"""
Cloud Infrastructure Auditor & Cost Optimizer
Entry point for the CLI. Defines top-level command groups and routes
them to provider-specific logic.
"""

import typer
from rich.console import Console

from auditor.providers.aws.auth import get_session, get_account_identity, AWSAuthError
from auditor.providers.aws.scanners.ebs import scan_unattached_volumes
from auditor.providers.aws.scanners.eip import scan_unassociated_eips
from auditor.providers.aws.scanners.ec2 import scan_underutilized_instances
from auditor.reports.aggregator import run_full_audit
from auditor.reports.formatter import render_findings_table, render_summary_panel
from pathlib import Path
from auditor.reports.exporter import export_to_csv, export_to_json

app = typer.Typer(
    name="cloud-auditor",
    help="Audit cloud infrastructure for cost-saving opportunities and safely clean up waste.",
    add_completion=True,
)

console = Console()

# Sub-command groups
scan_app = typer.Typer(help="Scan cloud resources for waste and misconfigurations.")
report_app = typer.Typer(help="Generate and export audit reports.")
cleanup_app = typer.Typer(help="Review and execute cleanup of flagged resources.")

app.add_typer(scan_app, name="scan")
app.add_typer(report_app, name="report")
app.add_typer(cleanup_app, name="cleanup")


@app.command()
def version():
    """Show the CLI version."""
    console.print("[bold cyan]Cloud Infrastructure Auditor[/bold cyan] v0.1.0")


def _connect(profile: str, region: str):
    """
    Shared helper: establish an AWS session and confirm identity before
    any scan proceeds. Prints a clean error and exits if auth fails,
    rather than crashing with a raw traceback.
    """
    try:
        session = get_session(profile=profile, region=region)
        identity = get_account_identity(session)
        console.print(
            f"[green]Connected[/green] to AWS account "
            f"[bold]{identity['account_id']}[/bold] as [bold]{identity['arn']}[/bold]"
        )
        return session
    except AWSAuthError as e:
        console.print(f"[bold red]Authentication failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@scan_app.command("ebs")
def scan_ebs(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
):
    """Scan for unattached EBS volumes."""
    session = _connect(profile, region)
    findings = scan_unattached_volumes(session, region)
    render_findings_table(console, findings, title=f"Unattached EBS Volumes — {region}")


@scan_app.command("eip")
def scan_eip(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
):
    """Scan for unassociated Elastic IPs."""
    session = _connect(profile, region)
    findings = scan_unassociated_eips(session, region)
    render_findings_table(console, findings, title=f"Unassociated Elastic IPs — {region}")


@scan_app.command("ec2")
def scan_ec2(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
    days: int = typer.Option(14, help="Lookback window (days) for CPU utilization."),
):
    """Scan for underutilized EC2 instances (low CPU over N days)."""
    session = _connect(profile, region)
    findings = scan_underutilized_instances(session, region, days=days)
    render_findings_table(console, findings, title=f"Underutilized EC2 Instances — {region}")


@scan_app.command("all")
def scan_all(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
    days: int = typer.Option(14, help="Lookback window (days) for EC2 CPU utilization."),
):
    """Run all scanners (EBS, EIP, EC2) and show a combined report."""
    session = _connect(profile, region)
    audit = run_full_audit(session, region, ec2_days=days)

    render_summary_panel(console, audit)
    if audit["findings"]:
        console.print()  # spacing
        render_findings_table(console, audit["findings"], title=f"All Findings — {region}")

@report_app.command("export")
def report_export(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
    days: int = typer.Option(14, help="Lookback window (days) for EC2 CPU utilization."),
    format: str = typer.Option("both", help="Export format: csv, json, or both."),
    output_dir: str = typer.Option("reports_output", help="Directory to save reports in."),
):
    """Run a full audit and export results to CSV and/or JSON."""
    session = _connect(profile, region)
    audit = run_full_audit(session, region, ec2_days=days)

    render_summary_panel(console, audit)

    out_dir = Path(output_dir)
    exported_files = []

    if format in ("csv", "both"):
        csv_path = export_to_csv(audit["findings"], output_dir=out_dir)
        exported_files.append(csv_path)

    if format in ("json", "both"):
        json_path = export_to_json(audit, output_dir=out_dir)
        exported_files.append(json_path)

    console.print("\n[bold green]Exported:[/bold green]")
    for path in exported_files:
        console.print(f"  • {path}")


if __name__ == "__main__":
    app()