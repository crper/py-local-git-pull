"""Render diagnosis results for the doctor command."""

from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import FailureRecord


def render_doctor_result(
    console: Console, repo_name: str, failure: FailureRecord, evidence: str | None = None
) -> None:
    lines = [
        f"PROBLEM: {failure.kind.value}",
        f"WHY: {failure.detail or failure.summary}",
    ]
    if evidence:
        lines.append(f"EVIDENCE: {evidence}")
    lines.append("DO NOW:")
    lines.extend(
        f"  {idx}. {action.description}{f' → {action.command}' if action.command else ''}"
        for idx, action in enumerate(failure.suggested_actions, start=1)
    )
    console.print(Panel("\n".join(lines), title=f"REPO: {repo_name}", border_style="magenta"))
