from pathlib import Path

from typer.testing import CliRunner

from py_local_git_pull.cli.app import app
from py_local_git_pull.state.paths import StatePaths


runner = CliRunner()


def _mock_state_paths() -> StatePaths:
    return StatePaths(
        state_dir=Path("/tmp"),
        runs_dir=Path("/tmp"),
        logs_dir=Path("/tmp"),
        config_file=Path("/tmp/config.toml"),
    )


def test_doctor_command_renders_problem_and_actions(monkeypatch) -> None:
    from py_local_git_pull.core.models import FailureKind, FailureRecord, SuggestedAction

    monkeypatch.setattr(
        "py_local_git_pull.cli.doctor.get_state_paths",
        _mock_state_paths,
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.doctor.load_diagnosis",
        lambda **_: [
            (
                "demo",
                FailureRecord(
                    kind=FailureKind.UPSTREAM_MISSING,
                    summary="current branch has no upstream",
                    detail="main is not tracking origin/main",
                    raw_error=None,
                    can_auto_fix=True,
                    suggested_actions=(
                        SuggestedAction(
                            label="set_upstream",
                            command="git branch --set-upstream-to=origin/main main",
                            description="set upstream for main",
                            auto_fixable=True,
                        ),
                    ),
                ),
                "branch=main, failure=upstream_missing",
            ),
        ],
    )

    result = runner.invoke(app, ["doctor", "/tmp/demo"])
    assert result.exit_code == 0
    assert "PROBLEM" in result.stdout
    assert "DO NOW" in result.stdout
    assert "EVIDENCE" in result.stdout


def test_doctor_help_mentions_last_and_run() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "--last" in result.stdout
    assert "--run" in result.stdout


def test_doctor_command_reports_when_no_issues_found(monkeypatch) -> None:
    monkeypatch.setattr(
        "py_local_git_pull.cli.doctor.get_state_paths",
        _mock_state_paths,
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.doctor.load_diagnosis",
        lambda **_: (),
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.doctor.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (),
    )

    result = runner.invoke(app, ["doctor", "/tmp/demo"])
    assert result.exit_code == 0
    assert "no issues found" in result.stdout.lower()
