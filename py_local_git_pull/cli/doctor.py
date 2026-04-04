"""Doctor command with json output."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.runtime.doctor import diagnose_from_inspections, load_diagnosis
from py_local_git_pull.state.paths import get_state_paths
from py_local_git_pull.ui.doctor_view import render_doctor_result


def doctor_command(
    path: Path,
    repo: Annotated[str | None, typer.Option("--repo")] = None,
    kind: Annotated[str | None, typer.Option("--kind")] = None,
    last: Annotated[bool, typer.Option("--last")] = False,
    run: Annotated[str | None, typer.Option("--run")] = None,
    output: Annotated[str, typer.Option("--output")] = "table",
) -> None:
    """Diagnose repository issues and suggest fixes."""
    paths = get_state_paths()
    results = load_diagnosis(
        runs_dir=paths.runs_dir,
        run_id=run,
        repo_name=repo,
    )

    if results is None or (not last and run is None and not results):
        inspections = RepoInspector().inspect_path(str(path), recursive=True, max_depth=3)
        results = diagnose_from_inspections(inspections, repo_name=repo, kind=kind)
    elif kind:
        results = tuple(item for item in results if item[1].kind.value == kind)

    if output == "json":
        payload = [
            {
                "repo_name": repo_name,
                "failure": asdict(failure),
                "evidence": evidence,
            }
            for repo_name, failure, evidence in results
        ]
        print(json.dumps({"command": "doctor", "path": str(path), "results": payload}))
        raise typer.Exit(code=0)

    from py_local_git_pull.ui.console import make_console

    console = make_console()
    if not results:
        console.print("[green]no issues found[/]")
        raise typer.Exit(code=0)

    for repo_name, failure, evidence in results:
        render_doctor_result(console, repo_name, failure, evidence=evidence)

    raise typer.Exit(code=0)
