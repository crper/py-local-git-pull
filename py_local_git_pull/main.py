"""CLI entrypoint."""

from .cli.app import app


def main() -> None:
    app(prog_name="py-local-git-pull")
