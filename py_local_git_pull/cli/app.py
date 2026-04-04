"""Typer application entrypoint with global options."""

import logging
from typing import Annotated

import structlog
import typer

from .doctor import doctor_command
from .runs import app as runs_app
from .scan import scan_command
from .sync import sync_command


def _configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


_configure_structlog()

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Git task console for scanning, syncing, and diagnosing local repositories.",
)


@app.callback()
def main(
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="Increase output verbosity (can repeat)"),
    ] = 0,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress non-essential output")
    ] = False,
) -> None:
    """Global options for py-local-git-pull."""
    if verbose and quiet:
        raise typer.Exit(code=2)


app.command("scan")(scan_command)
app.command("sync")(sync_command)
app.command("doctor")(doctor_command)
app.add_typer(runs_app, name="runs")
