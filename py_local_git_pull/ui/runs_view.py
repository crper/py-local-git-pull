"""Render persisted run history."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def render_runs_list(console: Console, runs) -> None:
    table = Table(title="RUNS")
    table.add_column("Run ID", width=26)
    table.add_column("Policy", width=10)
    table.add_column("Synced", width=8)
    table.add_column("Failed", width=8)

    for run in runs:
        table.add_row(
            run.run_id,
            run.policy.value,
            str(run.summary.synced),
            str(run.summary.failed),
        )

    if not runs:
        console.print("[yellow]No recorded runs found.[/]")
        return

    console.print(table)


def render_run_detail(console: Console, run) -> None:
    summary = "\n".join(
        [
            f"run_id: {run.run_id}",
            f"path: {run.path}",
            f"policy: {run.policy.value}",
            f"started_at: {run.started_at}",
            f"finished_at: {run.finished_at or '-'}",
            f"synced: {run.summary.synced}",
            f"partial: {run.summary.partial}",
            f"skipped: {run.summary.skipped}",
            f"failed: {run.summary.failed}",
        ]
    )
    console.print(Panel(summary, title="RUN DETAIL", border_style="cyan"))

    outcomes = Table(title="REPO OUTCOMES")
    outcomes.add_column("Repo", width=20)
    outcomes.add_column("Status", width=12)
    outcomes.add_column("Branch", width=16)
    outcomes.add_column("Failure")

    for outcome in run.outcomes:
        outcomes.add_row(
            outcome.repo_name,
            outcome.status.value,
            outcome.current_branch or "-",
            outcome.failure.kind.value if outcome.failure else "-",
        )

    if run.outcomes:
        console.print(outcomes)
