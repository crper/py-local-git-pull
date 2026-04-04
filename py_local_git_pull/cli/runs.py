"""Historical run inspection commands."""

import typer

from py_local_git_pull.runtime.journal import list_runs, load_run
from py_local_git_pull.state.paths import get_state_paths
from py_local_git_pull.ui.console import make_console
from py_local_git_pull.ui.runs_view import render_run_detail, render_runs_list

app = typer.Typer(help="Inspect persisted sync runs.")


@app.command("list")
def list_runs_command() -> None:
    paths = get_state_paths()
    console = make_console()
    render_runs_list(console, list_runs(paths.runs_dir))


@app.command("show")
def show_run_command(run_id: str) -> None:
    paths = get_state_paths()
    console = make_console()
    run = load_run(paths.runs_dir, run_id)
    if run is None:
        console.print(f"[yellow]Run not found: {run_id}[/]")
        raise typer.Exit(code=1)
    render_run_detail(console, run)
