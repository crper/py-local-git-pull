from pathlib import Path

from py_local_git_pull.core.models import (
    FailureKind,
    FailureRecord,
    PolicyMode,
    RepoOutcome,
    RepoStatus,
    RunRecord,
    RunSummary,
)
from py_local_git_pull.runtime.doctor import load_diagnosis
from py_local_git_pull.runtime.journal import write_run_record


def test_load_diagnosis_reads_failure_from_latest_run(tmp_path: Path) -> None:
    run = RunRecord(
        run_id="run-123",
        command="sync",
        path="/tmp/repos",
        policy=PolicyMode.SAFE,
        started_at="2026-04-01T10:00:00Z",
        finished_at="2026-04-01T10:01:00Z",
        events=(),
        outcomes=(
            RepoOutcome(
                repo_name="demo",
                path="/tmp/demo",
                status=RepoStatus.FAILED,
                current_branch="main",
                target_branches=("main",),
                synced_branches=(),
                skipped_branches=(),
                stashed=False,
                failure=FailureRecord(
                    kind=FailureKind.UPSTREAM_MISSING,
                    summary="current branch has no upstream",
                    detail="main is not tracking origin/main",
                    raw_error=None,
                    can_auto_fix=True,
                ),
            ),
        ),
        summary=RunSummary(synced=0, partial=0, skipped=0, failed=1),
    )

    write_run_record(tmp_path, run)
    loaded = load_diagnosis(runs_dir=tmp_path, run_id=None, repo_name="demo")

    assert loaded is not None
    assert loaded[0][0] == "demo"
    assert loaded[0][1].kind is FailureKind.UPSTREAM_MISSING
