import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from py_local_git_pull.cli.app import app
from py_local_git_pull.cli.sync import run_sync_flow
from py_local_git_pull.core.models import (
    PolicyMode,
    RepoInspection,
    RepoOutcome,
    RepoStatus,
    RiskLevel,
    RunRecord,
    RunSummary,
)
from py_local_git_pull.state.paths import StatePaths


runner = CliRunner()
DEMO_PATH = "/tmp/demo"
RUN_ID = "run-1"
RUN_STARTED_AT = "2026-04-01T10:00:00Z"
RUN_FINISHED_AT = "2026-04-01T10:00:01Z"


def _mock_state_paths() -> StatePaths:
    return StatePaths(
        state_dir=Path("/tmp"),
        runs_dir=Path("/tmp"),
        logs_dir=Path("/tmp"),
        config_file=Path("/tmp/config.toml"),
    )


def _make_inspection(path: str = DEMO_PATH) -> RepoInspection:
    return RepoInspection(
        repo_name=Path(path).name,
        path=path,
        current_branch="main",
        is_git_repo=True,
        is_bare=False,
        has_changes=False,
        has_untracked_changes=False,
        detached_head=False,
        branches=(),
        risk_level=RiskLevel.LOW,
        risk_flags=(),
    )


def _make_outcome(
    path: str = DEMO_PATH,
    *,
    status: RepoStatus = RepoStatus.SYNCED,
) -> RepoOutcome:
    skipped_branches = ("main",) if status is RepoStatus.SKIPPED else ()
    synced_branches = ("main",) if status is RepoStatus.SYNCED else ()
    return RepoOutcome(
        repo_name=Path(path).name,
        path=path,
        status=status,
        current_branch="main",
        target_branches=("main",),
        synced_branches=synced_branches,
        skipped_branches=skipped_branches,
        stashed=False,
    )


def _make_summary(outcomes: tuple[RepoOutcome, ...]) -> RunSummary:
    return RunSummary(
        synced=sum(1 for item in outcomes if item.status is RepoStatus.SYNCED),
        partial=sum(1 for item in outcomes if item.status is RepoStatus.PARTIAL),
        skipped=sum(1 for item in outcomes if item.status is RepoStatus.SKIPPED),
        failed=sum(1 for item in outcomes if item.status is RepoStatus.FAILED),
    )


def _make_run_record(
    *,
    path: str = DEMO_PATH,
    outcomes: tuple[RepoOutcome, ...] | None = None,
) -> RunRecord:
    run_outcomes = (_make_outcome(path),) if outcomes is None else outcomes
    return RunRecord(
        run_id=RUN_ID,
        command="sync",
        path=path,
        policy=PolicyMode.SAFE,
        started_at=RUN_STARTED_AT,
        finished_at=RUN_FINISHED_AT,
        events=(),
        outcomes=run_outcomes,
        summary=_make_summary(run_outcomes),
    )


def test_make_run_record_preserves_empty_outcomes() -> None:
    run_record = _make_run_record(outcomes=())
    assert run_record.outcomes == ()
    assert run_record.summary == RunSummary(synced=0, partial=0, skipped=0, failed=0)


def _patch_sync_command(
    monkeypatch,
    *,
    inspections: tuple[RepoInspection, ...] | None = None,
    run_record: RunRecord | None = None,
) -> None:
    patched_inspections = inspections or (_make_inspection(),)
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth, include_branch_deltas=True: patched_inspections,
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.run_sync_flow",
        lambda **_: run_record or _make_run_record(),
    )
    monkeypatch.setattr("py_local_git_pull.cli.sync.get_state_paths", _mock_state_paths)
    monkeypatch.setattr("py_local_git_pull.cli.sync.write_run_record", lambda *args, **kwargs: None)


def test_sync_command_renders_plan_and_summary(monkeypatch) -> None:
    _patch_sync_command(monkeypatch)

    result = runner.invoke(app, ["sync", DEMO_PATH])
    assert result.exit_code == 0
    assert "SUMMARY" in result.stdout
    assert "NEXT ACTIONS" in result.stdout


def test_sync_command_profiles_stage_timings(monkeypatch) -> None:
    _patch_sync_command(monkeypatch)
    perf_samples = iter([0.0, 0.2, 0.2, 0.7])
    monkeypatch.setattr("py_local_git_pull.cli.sync.perf_counter", lambda: next(perf_samples))

    result = runner.invoke(app, ["sync", DEMO_PATH, "--profile-inspect"])
    assert result.exit_code == 0
    assert "TIMINGS" in result.stdout
    assert "inspect" in result.stdout
    assert "execution" in result.stdout


def test_sync_json_output_includes_timings_when_profile_enabled(monkeypatch) -> None:
    _patch_sync_command(monkeypatch)
    perf_samples = iter([0.0, 0.2, 0.2, 0.7])
    monkeypatch.setattr("py_local_git_pull.cli.sync.perf_counter", lambda: next(perf_samples))

    result = runner.invoke(
        app,
        ["sync", DEMO_PATH, "--output", "json", "--profile-inspect"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["timings"]["inspect"] == 0.2
    assert payload["timings"]["execution"] == pytest.approx(0.5)


def test_sync_interactive_uses_prompt_selection(monkeypatch) -> None:
    inspect_path_calls: list[tuple[str, bool]] = []
    inspect_repo_calls: list[tuple[str, bool]] = []

    def fake_inspect_path(self, path, recursive, max_depth, include_branch_deltas=True):
        inspect_path_calls.append((path, include_branch_deltas))
        return (_make_inspection(path),)

    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.RepoInspector.inspect_path",
        fake_inspect_path,
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.RepoInspector.inspect_repo",
        lambda self, repo_path, include_branch_deltas=True: (
            inspect_repo_calls.append((repo_path, include_branch_deltas))
            or _make_inspection(repo_path)
        ),
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.choose_repo_paths",
        lambda inspections: [DEMO_PATH],
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.run_sync_flow",
        lambda **_: _make_run_record(outcomes=()),
    )
    monkeypatch.setattr("py_local_git_pull.cli.sync.get_state_paths", _mock_state_paths)
    monkeypatch.setattr("py_local_git_pull.cli.sync.write_run_record", lambda *args, **kwargs: None)

    result = runner.invoke(app, ["sync", DEMO_PATH, "--interactive"])
    assert result.exit_code == 0
    assert inspect_path_calls == [(DEMO_PATH, False)]
    assert inspect_repo_calls == [(DEMO_PATH, True)]


def test_sync_command_handles_unexpected_errors_without_traceback(monkeypatch) -> None:
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth, include_branch_deltas=True: (_make_inspection(),),
    )
    monkeypatch.setattr(
        "py_local_git_pull.cli.sync.run_sync_flow",
        lambda **_: (_ for _ in ()).throw(ValueError("boom")),
    )
    monkeypatch.setattr("py_local_git_pull.cli.sync.get_state_paths", _mock_state_paths)

    result = runner.invoke(app, ["sync", DEMO_PATH])
    assert result.exit_code == 1
    assert "sync failed: boom" in result.stdout
    assert "Traceback" not in result.stdout


def test_sync_help_mentions_policy_and_jsonl() -> None:
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--policy" in result.stdout
    assert "jsonl" in result.stdout


def test_run_sync_flow_calls_anyio_run_without_kwargs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_anyio_run(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr("py_local_git_pull.cli.sync.anyio.run", fake_anyio_run)

    result = run_sync_flow(
        path=DEMO_PATH,
        inspections=(),
        branches=(),
        policy=PolicyMode.SAFE,
        auto_upstream=False,
        skip_non_exist=True,
        no_stash=False,
        depth=1,
        dry_run=False,
        workers=1,
        emit=lambda event: None,
    )

    assert result == "ok"
    assert captured["kwargs"] == {}
