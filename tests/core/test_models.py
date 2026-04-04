from dataclasses import asdict

from py_local_git_pull.core.models import (
    FailureKind,
    PolicyMode,
    RepoStatus,
    RiskFlag,
    RunEvent,
    RunEventType,
)


def test_repo_status_values_are_stable() -> None:
    assert RepoStatus.SYNCED.value == "synced"
    assert RepoStatus.PARTIAL.value == "partial"
    assert RepoStatus.SKIPPED.value == "skipped"
    assert RepoStatus.FAILED.value == "failed"


def test_failure_kind_contains_upstream_and_ff_conflict() -> None:
    assert FailureKind.UPSTREAM_MISSING.value == "upstream_missing"
    assert FailureKind.PULL_FF_CONFLICT.value == "pull_ff_conflict"


def test_risk_flag_contains_local_changes() -> None:
    assert RiskFlag.HAS_LOCAL_CHANGES.value == "has_local_changes"


def test_policy_mode_values_are_stable() -> None:
    assert PolicyMode.SAFE.value == "safe"
    assert PolicyMode.CAREFUL.value == "careful"
    assert PolicyMode.FORCE.value == "force"


def test_run_event_serializes_with_schema_stable_fields() -> None:
    event = RunEvent(
        run_id="run-123",
        event_type=RunEventType.REPO_COMPLETED,
        repo_name="demo-api",
        message="repo finished",
        ts="2026-04-01T10:00:00Z",
    )

    payload = asdict(event)
    assert payload["run_id"] == "run-123"
    assert payload["repo_name"] == "demo-api"
    assert payload["message"] == "repo finished"
