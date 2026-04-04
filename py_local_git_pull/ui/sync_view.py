"""Sync output: header, events, summary with progress and colors."""

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_local_git_pull.core.models import RepoInspection, RepoOutcome, RepoStatus

_STATUS_STYLE: dict[RepoStatus, str] = {
    RepoStatus.SYNCED: "[green]✓ synced",
    RepoStatus.FAILED: "[red]✗ failed",
    RepoStatus.SKIPPED: "[yellow]⊘ skipped",
    RepoStatus.PARTIAL: "[orange3]◐ partial",
}


def render_sync_header(
    console: Console,
    path: str,
    inspections: tuple[RepoInspection, ...],
    branches: tuple[str, ...],
    dry_run: bool = False,
) -> None:
    """Render sync header panel."""
    branch_text = ", ".join(branches) if branches else "current"
    mode = " [dry-run]" if dry_run else ""
    body = f"path: {path}\nrepos: {len(inspections)}\nbranches: {branch_text}{mode}"
    console.print(Panel(body, title="py-local-git-pull sync", border_style="cyan"))


def render_plan_panel(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    """Render plan panel."""
    safe = sum(1 for item in inspections if not item.risk_flags)
    attention = sum(1 for item in inspections if item.risk_flags)
    body = f"safe: {safe}\nattention: {attention}\nskipped: 0"
    console.print(Panel(body, title="PLAN", border_style="blue"))


def render_repo_events(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render repo events as a Rich Table."""
    if not outcomes:
        return

    table = Table(title="EXECUTION", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Repo", width=20)
    table.add_column("Status", width=12)
    table.add_column("Detail")

    for idx, outcome in enumerate(outcomes, start=1):
        status_style = _STATUS_STYLE.get(outcome.status, outcome.status.value)
        detail = outcome.failure.kind.value if outcome.failure else (outcome.current_branch or "-")
        table.add_row(str(idx), outcome.repo_name, status_style, detail)

    console.print(table)


def render_summary_panel(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render summary panel with color-coded counts."""
    counts = Counter(outcome.status for outcome in outcomes)
    body = (
        f"[green]synced: {counts.get(RepoStatus.SYNCED, 0)}[/]\n"
        f"[orange3]partial: {counts.get(RepoStatus.PARTIAL, 0)}[/]\n"
        f"[yellow]skipped: {counts.get(RepoStatus.SKIPPED, 0)}[/]\n"
        f"[red]failed: {counts.get(RepoStatus.FAILED, 0)}[/]"
    )
    console.print(Panel(body, title="SUMMARY", border_style="green"))


def render_next_actions(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render next actions panel."""
    failed_count = sum(1 for o in outcomes if o.status is RepoStatus.FAILED)
    lines = (
        [f"[red]{failed_count}[/] failed repos → run [bold]doctor[/] for diagnosis"]
        if failed_count
        else ["[green]all repos synced cleanly[/]"]
    )
    console.print(Panel("\n".join(lines), title="NEXT ACTIONS", border_style="yellow"))


def render_profile_panel(console: Console, timings: dict[str, float]) -> None:
    """Render lightweight stage timings for sync flows."""
    body = "\n".join(f"{name}: {duration:.3f}s" for name, duration in timings.items())
    console.print(Panel(body or "no timings captured", title="TIMINGS", border_style="magenta"))
