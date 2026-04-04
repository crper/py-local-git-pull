"""Persist and load run records."""

import json
from dataclasses import asdict
from pathlib import Path

from py_local_git_pull.core.models import (
    BranchOutcome,
    BranchStatus,
    FailureKind,
    FailureRecord,
    PolicyMode,
    RepoOutcome,
    RepoStatus,
    RunEvent,
    RunEventType,
    RunRecord,
    RunSummary,
    SuggestedAction,
)


def _record_path(runs_dir: Path, run_id: str) -> Path:
    return runs_dir / f"{run_id}.json"


def write_run_record(runs_dir: Path, run: RunRecord) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = _record_path(runs_dir, run.run_id)
    path.write_text(json.dumps(asdict(run), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_run(runs_dir: Path, run_id: str) -> RunRecord | None:
    path = _record_path(runs_dir, run_id)
    if not path.exists():
        return None
    return _load_run_file(path)


def load_last_run(runs_dir: Path) -> RunRecord | None:
    files = sorted(runs_dir.glob("*.json"))
    if not files:
        return None
    return _load_run_file(files[-1])


def list_runs(runs_dir: Path) -> tuple[RunRecord, ...]:
    files = sorted(runs_dir.glob("*.json"), reverse=True)
    return tuple(_load_run_file(path) for path in files)


def _load_run_file(path: Path) -> RunRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _deserialize_run_record(payload)


def _deserialize_run_record(payload: dict) -> RunRecord:
    events = tuple(
        RunEvent(
            run_id=item["run_id"],
            event_type=RunEventType(item["event_type"]),
            ts=item["ts"],
            repo_name=item.get("repo_name"),
            repo_path=item.get("repo_path"),
            message=item.get("message"),
            status=item.get("status"),
            failure_kind=item.get("failure_kind"),
        )
        for item in payload.get("events", [])
    )
    outcomes = tuple(
        RepoOutcome(
            repo_name=item["repo_name"],
            path=item["path"],
            status=RepoStatus(item["status"]),
            current_branch=item.get("current_branch"),
            target_branches=tuple(item.get("target_branches", [])),
            synced_branches=tuple(item.get("synced_branches", [])),
            skipped_branches=tuple(item.get("skipped_branches", [])),
            stashed=item["stashed"],
            branch_outcomes=tuple(
                BranchOutcome(
                    name=branch["name"],
                    status=BranchStatus(branch["status"]),
                    is_current=branch["is_current"],
                    has_upstream=branch["has_upstream"],
                    upstream_name=branch.get("upstream_name"),
                    ahead=branch.get("ahead"),
                    behind=branch.get("behind"),
                    failure=None,
                )
                for branch in item.get("branch_outcomes", [])
            ),
            failure=_deserialize_failure(item.get("failure")),
            notes=tuple(item.get("notes", [])),
        )
        for item in payload.get("outcomes", [])
    )
    summary = RunSummary(**payload["summary"])
    return RunRecord(
        run_id=payload["run_id"],
        command=payload["command"],
        path=payload["path"],
        policy=PolicyMode(payload["policy"]),
        started_at=payload["started_at"],
        finished_at=payload.get("finished_at"),
        events=events,
        outcomes=outcomes,
        summary=summary,
    )


def _deserialize_failure(payload: dict | None) -> FailureRecord | None:
    if payload is None:
        return None
    return FailureRecord(
        kind=FailureKind(payload["kind"]),
        summary=payload["summary"],
        detail=payload.get("detail"),
        raw_error=payload.get("raw_error"),
        can_auto_fix=payload["can_auto_fix"],
        suggested_actions=tuple(
            SuggestedAction(
                label=action["label"],
                command=action.get("command"),
                description=action["description"],
                auto_fixable=action.get("auto_fixable", False),
            )
            for action in payload.get("suggested_actions", [])
        ),
    )
