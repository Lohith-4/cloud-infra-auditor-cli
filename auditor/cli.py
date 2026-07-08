"""
Cloud Infrastructure Auditor & Cost Optimizer
Entry point for the CLI. Defines top-level command groups and routes
them to provider-specific logic.
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="cloud-auditor",
    help="Audit cloud infrastructure for cost-saving opportunities and safely clean up waste.",
    add_completion=True,
)

console = Console()

# Sub-command groups (we'll flesh these out over the coming days)
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


@scan_app.command("ebs")
def scan_ebs(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
):
    """Scan for unattached EBS volumes."""
    console.print(f"[yellow]Placeholder:[/yellow] would scan EBS in {region} using profile '{profile}'")


@scan_app.command("eip")
def scan_eip(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
):
    """Scan for unassociated Elastic IPs."""
    console.print(f"[yellow]Placeholder:[/yellow] would scan Elastic IPs in {region} using profile '{profile}'")


@scan_app.command("ec2")
def scan_ec2(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
    days: int = typer.Option(14, help="Lookback window (days) for CPU utilization."),
):
    """Scan for underutilized EC2 instances (low CPU over N days)."""
    console.print(f"[yellow]Placeholder:[/yellow] would scan EC2 in {region} over last {days} days")


if __name__ == "__main__":
    app()