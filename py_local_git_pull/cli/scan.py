"""Scan command for repository inspection."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from py_local_git_pull.core.models import RiskLevel
from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.ui.scan_view import render_scan_summary


def scan_command(
    path: Path,
    recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
    max_depth: Annotated[int, typer.Option("--max-depth")] = 3,
    output: Annotated[str, typer.Option("--output")] = "table",
) -> None:
    """Scan a path for git repositories and show their status."""
    inspections = RepoInspector().inspect_path(
        str(path),
        recursive=recursive,
        max_depth=max_depth,
    )

    if output == "json":
        counts = {
            "low": sum(1 for item in inspections if item.risk_level is RiskLevel.LOW),
            "medium": sum(1 for item in inspections if item.risk_level is RiskLevel.MEDIUM),
            "high": sum(1 for item in inspections if item.risk_level is RiskLevel.HIGH),
        }
        payload = {
            "schema_version": 3,
            "command": "scan",
            "path": str(path),
            "summary": {
                "total": len(inspections),
                "clean": counts["low"],
                "attention": counts["medium"],
                "blocked": counts["high"],
                "risk_counts": counts,
            },
            "repos": [asdict(inspection) for inspection in inspections],
        }
        print(json.dumps(payload, ensure_ascii=False, default=list))
        raise typer.Exit(code=0)

    if output == "jsonl":
        counts = {
            "low": sum(1 for item in inspections if item.risk_level is RiskLevel.LOW),
            "medium": sum(1 for item in inspections if item.risk_level is RiskLevel.MEDIUM),
            "high": sum(1 for item in inspections if item.risk_level is RiskLevel.HIGH),
        }
        for inspection in inspections:
            print(
                json.dumps(
                    {
                        "schema_version": 3,
                        "command": "scan",
                        "event": "repo_scanned",
                        "path": str(path),
                        "repo": asdict(inspection),
                    },
                    ensure_ascii=False,
                    default=list,
                )
            )
        print(
            json.dumps(
                {
                    "schema_version": 3,
                    "command": "scan",
                    "event": "scan_summary",
                    "path": str(path),
                    "summary": {
                        "total": len(inspections),
                        "clean": counts["low"],
                        "attention": counts["medium"],
                        "blocked": counts["high"],
                        "risk_counts": counts,
                    },
                },
                ensure_ascii=False,
                default=list,
            )
        )
        raise typer.Exit(code=0)

    from py_local_git_pull.ui.console import make_console

    console = make_console()
    render_scan_summary(
        console,
        inspections,
        path=str(path),
        recursive=recursive,
        max_depth=max_depth,
    )
    raise typer.Exit(code=0)
