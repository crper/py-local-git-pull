from typer.testing import CliRunner

from py_local_git_pull.cli.app import app


runner = CliRunner()


def test_root_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout
    assert "sync" in result.stdout
    assert "doctor" in result.stdout
    assert "runs" in result.stdout


def test_sync_help_mentions_branch_option() -> None:
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--branch" in result.stdout
    assert "--interactive" in result.stdout
    assert "--policy" in result.stdout
