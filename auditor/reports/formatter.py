"""
Rich-based terminal formatting for scan results.

Converts the standard findings/summary data structure (produced by
scanners and the aggregator) into polished terminal tables and panels.
Kept separate from cli.py so Day 4-5's CSV/JSON export can reuse the
same underlying data without duplicating formatting logic.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


def render_findings_table(console: Console, findings: list[dict], title: str) -> None:
    """
    Render a list of findings as a Rich table. Column set adapts based
    on the fields actually present across all findings, since EBS, EIP,
    and EC2 findings each carry slightly different detail fields.
    """
    if not findings:
        console.print(f"[green]No findings for: {title}[/green]")
        return

    table = Table(title=title, show_lines=False, header_style="bold cyan")

    table.add_column("Resource ID", style="white", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Name", style="white")
    table.add_column("Region", style="dim")
    table.add_column("Detail", style="white")
    table.add_column("Est. Monthly Cost", style="bold red", justify="right")
    table.add_column("Reason", style="yellow")

    for f in findings:
        detail = _extract_detail(f)
        table.add_row(
            f["resource_id"],
            f["resource_type"],
            f.get("name", "-"),
            f["region"],
            detail,
            f"${f['estimated_monthly_cost_usd']:.2f}",
            f["reason"],
        )

    console.print(table)


def _extract_detail(finding: dict) -> str:
    """Pull the most relevant type-specific field for the 'Detail' column."""
    if finding["resource_type"] == "EBS Volume":
        return f"{finding['size_gb']}GB {finding['volume_type']}"
    if finding["resource_type"] == "Elastic IP":
        return finding.get("public_ip", "-")
    if finding["resource_type"] == "EC2 Instance":
        return f"{finding['instance_type']} @ {finding['avg_cpu_percent']}% CPU"
    return "-"


def render_summary_panel(console: Console, audit: dict) -> None:
    """
    Render a high-level summary panel: total findings, total estimated
    monthly waste, and a per-resource-type cost breakdown.
    """
    summary = audit["summary"]

    if summary["total_findings"] == 0:
        console.print(Panel(
            "[bold green]No waste detected. Clean audit![/bold green]",
            title=f"Audit Summary — {audit['region']}",
            border_style="green",
        ))
        return

    body = Text()
    body.append(f"Total findings: ", style="white")
    body.append(f"{summary['total_findings']}\n", style="bold white")
    body.append(f"Estimated monthly waste: ", style="white")
    body.append(f"${summary['total_estimated_monthly_cost_usd']:.2f}\n\n", style="bold red")

    body.append("Breakdown by resource type:\n", style="bold white")
    for resource_type, stats in summary["by_resource_type"].items():
        body.append(f"  • {resource_type}: ", style="cyan")
        body.append(f"{stats['count']} finding(s) — ${stats['cost']:.2f}/mo\n", style="white")

    console.print(Panel(
        body,
        title=f"Audit Summary — {audit['region']}",
        border_style="red",
    ))