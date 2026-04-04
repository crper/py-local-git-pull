"""Scan output with summary-first task-console sections."""

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from py_local_git_pull.core.models import RepoInspection, RiskLevel

_RISK_STYLE: dict[RiskLevel, str] = {
    RiskLevel.LOW: "green",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.HIGH: "red",
}


def render_scan_summary(
    console: Console,
    inspections: tuple[RepoInspection, ...],
    *,
    path: str | None = None,
    recursive: bool = False,
    max_depth: int = 3,
) -> None:
    """Render scan results with summary panels followed by repo detail."""
    if not inspections:
        console.print("[yellow]No repositories found.[/]")
        return

    counts = Counter(insp.risk_level for insp in inspections)
    total = len(inspections)
    clean = counts.get(RiskLevel.LOW, 0)
    attention = counts.get(RiskLevel.MEDIUM, 0)
    blocked = counts.get(RiskLevel.HIGH, 0)

    if path:
        mode = "recursive" if recursive else "single"
        header_body = f"path: {path}\nrepos_found: {total}\nmode: {mode}(max_depth={max_depth})"
        console.print(Panel(header_body, title="py-local-git-pull scan", border_style="cyan"))

    inventory_body = "\n".join(
        [
            f"total: {total}",
            f"clean: {clean}",
            f"attention: {attention}",
            f"blocked: {blocked}",
        ]
    )
    console.print(Panel(inventory_body, title="INVENTORY", border_style="blue"))

    risk_body = "\n".join(
        [
            f"high: {blocked}",
            f"medium: {attention}",
            f"low: {clean}",
        ]
    )
    console.print(Panel(risk_body, title="RISKS", border_style="yellow"))

    next_lines = _build_next_actions(path, recursive, blocked, attention)
    console.print(Panel("\n".join(next_lines), title="NEXT", border_style="green"))

    table = Table(title="REPOS")
    table.add_column("Repo", width=20)
    table.add_column("Branch", width=15)
    table.add_column("Risk", width=8)
    table.add_column("Flags")

    for insp in inspections:
        risk_style = _RISK_STYLE.get(insp.risk_level, "white")
        flags = ", ".join(f.value for f in insp.risk_flags) or "none"
        table.add_row(
            insp.repo_name,
            insp.current_branch or "(detached)",
            f"[{risk_style}]{insp.risk_level.value}[/]",
            flags,
        )

    console.print(table)


def _build_next_actions(
    path: str | None, recursive: bool, blocked: int, attention: int
) -> list[str]:
    if path is None:
        return ["review repo risks before running sync"]

    recursive_flag = " -r" if recursive else ""
    lines = [f"run: py-local-git-pull sync {path}{recursive_flag} --policy safe"]
    if attention or blocked:
        lines.append(
            f"run: py-local-git-pull sync {path}{recursive_flag} --policy careful --interactive"
        )
    return lines
