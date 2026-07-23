"""
Cloud Infrastructure Auditor & Cost Optimizer
Entry point for the CLI. Defines top-level command groups and routes
them to provider-specific logic.
"""
from auditor.providers.aws.scanners.ec2 import scan_underutilized_instances
from auditor.providers.aws.scanners.ebs import scan_unattached_volumes
from auditor.providers.aws.scanners.eip import scan_unassociated_eips
import typer
from rich.console import Console

from auditor.providers.aws.auth import get_session, get_account_identity, AWSAuthError

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

    if not findings:
        console.print(f"[green]No unattached EBS volumes found in {region}.[/green]")
        return

    total_cost = sum(f["estimated_monthly_cost_usd"] for f in findings)
    console.print(f"[yellow]Found {len(findings)} unattached EBS volume(s)[/yellow] "
                  f"— estimated waste: [bold red]${total_cost:.2f}/month[/bold red]")
    for f in findings:
        console.print(f"  • {f['resource_id']} ({f['name']}) — {f['size_gb']}GB "
                       f"{f['volume_type']} — ${f['estimated_monthly_cost_usd']}/mo")


@scan_app.command("eip")
def scan_eip(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
):
    """Scan for unassociated Elastic IPs."""
    session = _connect(profile, region)
    findings = scan_unassociated_eips(session, region)

    if not findings:
        console.print(f"[green]No unassociated Elastic IPs found in {region}.[/green]")
        return

    total_cost = sum(f["estimated_monthly_cost_usd"] for f in findings)
    console.print(f"[yellow]Found {len(findings)} unassociated Elastic IP(s)[/yellow] "
                  f"— estimated waste: [bold red]${total_cost:.2f}/month[/bold red]")
    for f in findings:
        console.print(f"  • {f['resource_id']} ({f['public_ip']}) — "
                       f"${f['estimated_monthly_cost_usd']}/mo")

@scan_app.command("ec2")
def scan_ec2(
    profile: str = typer.Option("default", help="AWS profile name to use."),
    region: str = typer.Option("us-east-1", help="AWS region to scan."),
    days: int = typer.Option(14, help="Lookback window (days) for CPU utilization."),
):
    """Scan for underutilized EC2 instances (low CPU over N days)."""
    session = _connect(profile, region)
    findings = scan_underutilized_instances(session, region, days=days)

    if not findings:
        console.print(f"[green]No underutilized EC2 instances found in {region}.[/green]")
        return

    total_cost = sum(f["estimated_monthly_cost_usd"] for f in findings)
    console.print(f"[yellow]Found {len(findings)} underutilized EC2 instance(s)[/yellow] "
                  f"— estimated waste: [bold red]${total_cost:.2f}/month[/bold red]")
    for f in findings:
        console.print(f"  • {f['resource_id']} ({f['name']}) — {f['instance_type']} — "
                       f"avg CPU {f['avg_cpu_percent']}% — ${f['estimated_monthly_cost_usd']}/mo")


if __name__ == "__main__":
    app()