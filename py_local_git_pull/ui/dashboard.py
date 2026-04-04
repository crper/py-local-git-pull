"""Dashboard panels for the sync task console."""

from collections import Counter

from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import RepoInspection, RepoOutcome, RepoStatus


def render_sync_header(
    console: Console,
    path: str,
    inspections: tuple[RepoInspection, ...],
    branches: tuple[str, ...],
) -> None:
    branch_text = ", ".join(branches) if branches else "current"
    body = f"path: {path}\nrepos: {len(inspections)}\nbranches: {branch_text}"
    console.print(Panel(body, title="py-local-git-pull sync", border_style="cyan"))


def render_plan_panel(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    safe = sum(1 for item in inspections if not item.risk_flags)
    attention = sum(1 for item in inspections if item.risk_flags)
    body = f"safe: {safe}\nattention: {attention}\nskipped: 0"
    console.print(Panel(body, title="PLAN", border_style="blue"))


def render_summary_panel(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    counts = Counter(outcome.status.value for outcome in outcomes)
    body = (
        f"success: {counts.get(RepoStatus.SYNCED.value, 0)}\n"
        f"partial: {counts.get(RepoStatus.PARTIAL.value, 0)}\n"
        f"skipped: {counts.get(RepoStatus.SKIPPED.value, 0)}\n"
        f"failed: {counts.get(RepoStatus.FAILED.value, 0)}"
    )
    console.print(Panel(body, title="SUMMARY", border_style="green"))


def render_next_actions(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    failed_count = sum(1 for outcome in outcomes if outcome.status is RepoStatus.FAILED)
    lines = (
        [f"{failed_count} failed repos -> run doctor"]
        if failed_count
        else ["all repos synced cleanly"]
    )
    console.print(Panel("\n".join(lines), title="NEXT ACTIONS", border_style="yellow"))
