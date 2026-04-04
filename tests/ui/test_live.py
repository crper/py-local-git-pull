from py_local_git_pull.core.models import RunEvent, RunEventType
from py_local_git_pull.ui.live import summarize_live_state


def _event(
    event_type: RunEventType,
    *,
    repo_name: str | None = None,
    status: str | None = None,
    failure_kind: str | None = None,
) -> RunEvent:
    return RunEvent(
        run_id="run-1",
        event_type=event_type,
        ts="2026-04-01T10:00:00Z",
        repo_name=repo_name,
        status=status,
        failure_kind=failure_kind,
    )


def test_summarize_live_state_counts_repo_progress() -> None:
    summary = summarize_live_state(
        (
            _event(RunEventType.RUN_STARTED),
            _event(RunEventType.REPO_QUEUED, repo_name="alpha"),
            _event(RunEventType.REPO_STARTED, repo_name="alpha"),
            _event(RunEventType.REPO_COMPLETED, repo_name="alpha", status="synced"),
            _event(RunEventType.REPO_BLOCKED, repo_name="beta", status="skipped"),
            _event(RunEventType.REPO_STARTED, repo_name="gamma"),
        )
    )

    assert summary["total"] == 3
    assert summary["queued"] == 0
    assert summary["running"] == 1
    assert summary["synced"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 0


def test_summarize_live_state_counts_failures() -> None:
    summary = summarize_live_state(
        (
            _event(RunEventType.REPO_STARTED, repo_name="delta"),
            _event(
                RunEventType.REPO_FAILED,
                repo_name="delta",
                status="failed",
                failure_kind="fetch_failed",
            ),
        )
    )

    assert summary["total"] == 1
    assert summary["running"] == 0
    assert summary["failed"] == 1
