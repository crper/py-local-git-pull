"""Event stream renderers for sync flows."""

from rich.console import Console

from py_local_git_pull.core.models import RepoOutcome


def render_repo_events(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    console.print("EXECUTION")
    for index, outcome in enumerate(outcomes, start=1):
        branch = outcome.current_branch or "-"
        note = outcome.failure.kind.value if outcome.failure else branch
        console.print(
            f"[{index:02d}/{len(outcomes):02d}] "
            f"{outcome.repo_name:<16} {outcome.status.value:<10} {note}"
        )
