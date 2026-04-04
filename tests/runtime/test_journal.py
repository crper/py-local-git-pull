from pathlib import Path

from py_local_git_pull.core.models import PolicyMode, RunRecord, RunSummary
from py_local_git_pull.runtime.journal import load_last_run, write_run_record


def test_write_and_load_last_run(tmp_path: Path) -> None:
    run = RunRecord(
        run_id="run-123",
        command="sync",
        path="/tmp/repos",
        policy=PolicyMode.SAFE,
        started_at="2026-04-01T10:00:00Z",
        finished_at="2026-04-01T10:01:00Z",
        events=(),
        outcomes=(),
        summary=RunSummary(synced=1, partial=0, skipped=0, failed=0),
    )

    write_run_record(tmp_path, run)
    loaded = load_last_run(tmp_path)

    assert loaded is not None
    assert loaded.run_id == "run-123"
    assert loaded.summary.synced == 1
