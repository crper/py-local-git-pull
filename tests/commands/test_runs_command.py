from pathlib import Path

from typer.testing import CliRunner

from py_local_git_pull.cli.app import app
from py_local_git_pull.core.models import PolicyMode, RunRecord, RunSummary
from py_local_git_pull.state.paths import StatePaths


runner = CliRunner()


def _mock_state_paths() -> StatePaths:
    return StatePaths(
        state_dir=Path("/tmp"),
        runs_dir=Path("/tmp"),
        logs_dir=Path("/tmp"),
        config_file=Path("/tmp/config.toml"),
    )


def test_runs_help_is_available() -> None:
    result = runner.invoke(app, ["runs", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout
    assert "show" in result.stdout


def test_runs_list_renders_table(monkeypatch) -> None:
    monkeypatch.setattr("py_local_git_pull.cli.runs.get_state_paths", _mock_state_paths)
    monkeypatch.setattr(
        "py_local_git_pull.cli.runs.list_runs",
        lambda _: (
            RunRecord(
                run_id="run-1",
                command="sync",
                path="/tmp/demo",
                policy=PolicyMode.SAFE,
                started_at="2026-04-01T10:00:00Z",
                finished_at="2026-04-01T10:00:01Z",
                events=(),
                outcomes=(),
                summary=RunSummary(synced=1, partial=0, skipped=0, failed=0),
            ),
        ),
    )

    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0
    assert "RUNS" in result.stdout


def test_runs_show_renders_detailed_run_view(monkeypatch) -> None:
    monkeypatch.setattr("py_local_git_pull.cli.runs.get_state_paths", _mock_state_paths)
    monkeypatch.setattr(
        "py_local_git_pull.cli.runs.load_run",
        lambda _, __: RunRecord(
            run_id="run-1",
            command="sync",
            path="/tmp/demo",
            policy=PolicyMode.SAFE,
            started_at="2026-04-01T10:00:00Z",
            finished_at="2026-04-01T10:00:01Z",
            events=(),
            outcomes=(),
            summary=RunSummary(synced=1, partial=0, skipped=0, failed=0),
        ),
    )

    result = runner.invoke(app, ["runs", "show", "run-1"])
    assert result.exit_code == 0
    assert "RUN DETAIL" in result.stdout
    assert "run-1" in result.stdout
    assert "/tmp/demo" in result.stdout
