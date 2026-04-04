from py_local_git_pull.core.models import RepoOutcome, RepoStatus
from py_local_git_pull.runtime.executor import summarize_outcomes


def test_summarize_outcomes_counts_repo_statuses() -> None:
    outcomes = (
        RepoOutcome("a", "/tmp/a", RepoStatus.SYNCED, "main", ("main",), ("main",), (), False),
        RepoOutcome("b", "/tmp/b", RepoStatus.FAILED, "main", ("main",), (), (), False),
    )

    summary = summarize_outcomes(outcomes)
    assert summary.synced == 1
    assert summary.failed == 1
