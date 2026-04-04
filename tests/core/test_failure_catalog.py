from py_local_git_pull.core.failure.catalog import classify_git_failure
from py_local_git_pull.core.models import FailureKind


def test_classify_upstream_missing_error() -> None:
    failure = classify_git_failure("fatal: no upstream configured")
    assert failure.kind is FailureKind.UPSTREAM_MISSING
    assert failure.can_auto_fix is True


def test_classify_ff_only_failure() -> None:
    failure = classify_git_failure("fatal: Not possible to fast-forward, aborting.")
    assert failure.kind is FailureKind.PULL_FF_CONFLICT
    assert failure.can_auto_fix is False
