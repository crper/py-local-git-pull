"""Diagnosis from recorded run evidence."""

from py_local_git_pull.core.failure.catalog import diagnose_inspection
from py_local_git_pull.core.models import FailureRecord, RepoInspection
from py_local_git_pull.runtime.journal import load_last_run, load_run


def diagnose_run_failure(
    run_record, repo_name: str | None = None
) -> tuple[tuple[str, FailureRecord, str], ...]:
    results: list[tuple[str, FailureRecord, str]] = []
    for outcome in run_record.outcomes:
        if repo_name and outcome.repo_name != repo_name:
            continue
        if outcome.failure is not None:
            evidence = []
            if outcome.current_branch:
                evidence.append(f"branch={outcome.current_branch}")
            if outcome.failure.kind:
                evidence.append(f"failure={outcome.failure.kind.value}")
            results.append((outcome.repo_name, outcome.failure, ", ".join(evidence)))
    return tuple(results)


def load_diagnosis(*, runs_dir, run_id: str | None, repo_name: str | None):
    run = load_run(runs_dir, run_id) if run_id else load_last_run(runs_dir)
    if run is None:
        return None
    return diagnose_run_failure(run, repo_name=repo_name)


def diagnose_from_inspections(
    inspections: tuple[RepoInspection, ...], repo_name: str | None, kind: str | None
) -> tuple[tuple[str, FailureRecord, str | None], ...]:
    results: list[tuple[str, FailureRecord, str | None]] = []
    for inspection in inspections:
        if repo_name and inspection.repo_name != repo_name:
            continue
        failure = diagnose_inspection(inspection)
        if failure is None:
            continue
        if kind and failure.kind.value != kind:
            continue
        results.append((inspection.repo_name, failure, None))
    return tuple(results)
