import json

from typer.testing import CliRunner

from py_local_git_pull.cli.app import app


runner = CliRunner()


def test_scan_help_lists_recursive_options() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.stdout
    assert "--max-depth" in result.stdout


def test_scan_command_renders_inventory_risks_and_next(monkeypatch) -> None:
    from py_local_git_pull.core.models import RepoInspection, RiskFlag, RiskLevel

    monkeypatch.setattr(
        "py_local_git_pull.cli.scan.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (
            RepoInspection(
                repo_name="demo",
                path="/tmp/demo",
                current_branch="main",
                is_git_repo=True,
                is_bare=False,
                has_changes=True,
                has_untracked_changes=False,
                detached_head=False,
                branches=(),
                risk_level=RiskLevel.MEDIUM,
                risk_flags=(RiskFlag.HAS_LOCAL_CHANGES,),
            ),
        ),
    )

    result = runner.invoke(app, ["scan", "/tmp/demo"])
    assert result.exit_code == 0
    assert "INVENTORY" in result.stdout
    assert "RISKS" in result.stdout
    assert "NEXT" in result.stdout
    assert "REPOS" in result.stdout


def test_scan_json_uses_schema_v3(monkeypatch) -> None:
    from py_local_git_pull.core.models import RepoInspection, RiskLevel

    monkeypatch.setattr(
        "py_local_git_pull.cli.scan.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (
            RepoInspection(
                repo_name="demo",
                path="/tmp/demo",
                current_branch="main",
                is_git_repo=True,
                is_bare=False,
                has_changes=False,
                has_untracked_changes=False,
                detached_head=False,
                branches=(),
                risk_level=RiskLevel.LOW,
                risk_flags=(),
            ),
        ),
    )

    result = runner.invoke(app, ["scan", "/tmp/demo", "--output", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 3
    assert payload["summary"]["total"] == 1


def test_scan_jsonl_streams_repo_rows_and_summary(monkeypatch) -> None:
    from py_local_git_pull.core.models import RepoInspection, RiskFlag, RiskLevel

    monkeypatch.setattr(
        "py_local_git_pull.cli.scan.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (
            RepoInspection(
                repo_name="demo",
                path="/tmp/demo",
                current_branch="main",
                is_git_repo=True,
                is_bare=False,
                has_changes=True,
                has_untracked_changes=False,
                detached_head=False,
                branches=(),
                risk_level=RiskLevel.MEDIUM,
                risk_flags=(RiskFlag.HAS_LOCAL_CHANGES,),
            ),
        ),
    )

    result = runner.invoke(app, ["scan", "/tmp/demo", "--output", "jsonl"])
    assert result.exit_code == 0
    lines = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert lines[0]["event"] == "repo_scanned"
    assert lines[0]["repo"]["repo_name"] == "demo"
    assert lines[-1]["event"] == "scan_summary"
    assert lines[-1]["summary"]["total"] == 1
