"""Event-driven sync executor."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from functools import partial
import uuid

import anyio

from py_local_git_pull.core.models import (
    PolicyMode,
    RepoInspection,
    RepoOutcome,
    RepoStatus,
    RunEvent,
    RunEventType,
    RunRecord,
    RunSummary,
    SyncOptions,
)
from py_local_git_pull.core.services.sync_service import build_sync_plan


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def build_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def summarize_outcomes(outcomes: tuple[RepoOutcome, ...]) -> RunSummary:
    counts = Counter(item.status for item in outcomes)
    return RunSummary(
        synced=counts.get(RepoStatus.SYNCED, 0),
        partial=counts.get(RepoStatus.PARTIAL, 0),
        skipped=counts.get(RepoStatus.SKIPPED, 0),
        failed=counts.get(RepoStatus.FAILED, 0),
    )


def _is_blocked_by_policy(plan, policy: PolicyMode) -> bool:
    """Check if repository should be blocked based on policy."""
    return policy is PolicyMode.SAFE and plan.will_skip


def _create_blocked_outcome(inspection: RepoInspection, plan) -> RepoOutcome:
    """Create outcome for a blocked repository."""
    return RepoOutcome(
        repo_name=inspection.repo_name,
        path=inspection.path,
        status=RepoStatus.SKIPPED,
        current_branch=inspection.current_branch,
        target_branches=plan.target_branches,
        synced_branches=(),
        skipped_branches=plan.target_branches,
        stashed=False,
        notes=((plan.skip_reason,) if plan.skip_reason else ()),
    )


def _determine_repo_event_type(status: RepoStatus) -> RunEventType:
    """Determine event type based on repository sync status."""
    if status is RepoStatus.FAILED:
        return RunEventType.REPO_FAILED
    return RunEventType.REPO_COMPLETED


async def _execute_repo_sync(
    inspection: RepoInspection,
    *,
    run_id: str,
    branches: tuple[str, ...],
    service_factory,
    options: SyncOptions,
    semaphore: anyio.Semaphore,
    lock: anyio.Lock,
    outcomes: list[RepoOutcome],
    emit,
) -> None:
    """Execute sync for a single repository."""
    plan = build_sync_plan(inspection, branches=branches, no_stash=False)

    await emit(
        RunEvent(
            run_id=run_id,
            event_type=RunEventType.REPO_QUEUED,
            ts=utc_now(),
            repo_name=inspection.repo_name,
            repo_path=inspection.path,
        )
    )

    async with semaphore:
        await emit(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.REPO_STARTED,
                ts=utc_now(),
                repo_name=inspection.repo_name,
                repo_path=inspection.path,
            )
        )

        service = service_factory(inspection.path)
        sync_call = partial(service.sync_repo, inspection, plan, options)
        outcome = await anyio.to_thread.run_sync(sync_call)

        async with lock:
            outcomes.append(outcome)

        await emit(
            RunEvent(
                run_id=run_id,
                event_type=_determine_repo_event_type(outcome.status),
                ts=utc_now(),
                repo_name=inspection.repo_name,
                repo_path=inspection.path,
                status=outcome.status.value,
                failure_kind=outcome.failure.kind.value if outcome.failure else None,
            )
        )


async def _handle_blocked_repo(
    inspection: RepoInspection,
    plan,
    *,
    run_id: str,
    lock: anyio.Lock,
    outcomes: list[RepoOutcome],
    emit,
) -> None:
    """Handle a repository blocked by policy."""
    blocked = _create_blocked_outcome(inspection, plan)
    async with lock:
        outcomes.append(blocked)
    await emit(
        RunEvent(
            run_id=run_id,
            event_type=RunEventType.REPO_BLOCKED,
            ts=utc_now(),
            repo_name=inspection.repo_name,
            repo_path=inspection.path,
            message=plan.skip_reason,
            status=blocked.status.value,
        )
    )


async def execute_sync_run(
    *,
    path: str,
    inspections: tuple[RepoInspection, ...],
    branches: tuple[str, ...],
    policy: PolicyMode,
    service_factory,
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
    workers: int,
    emit,
) -> RunRecord:
    run_id = build_run_id()
    started_at = utc_now()
    outcomes: list[RepoOutcome] = []
    lock = anyio.Lock()
    semaphore = anyio.Semaphore(max(1, workers))

    options = SyncOptions(
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
        depth=depth,
    )

    await emit(RunEvent(run_id=run_id, event_type=RunEventType.RUN_STARTED, ts=started_at))

    async def sync_one(inspection: RepoInspection) -> None:
        plan = build_sync_plan(inspection, branches=branches, no_stash=no_stash)

        if _is_blocked_by_policy(plan, policy):
            await _handle_blocked_repo(
                inspection, plan, run_id=run_id, lock=lock, outcomes=outcomes, emit=emit
            )
            return

        await _execute_repo_sync(
            inspection,
            run_id=run_id,
            branches=branches,
            service_factory=service_factory,
            options=options,
            semaphore=semaphore,
            lock=lock,
            outcomes=outcomes,
            emit=emit,
        )

    async with anyio.create_task_group() as tg:
        for inspection in inspections:
            tg.start_soon(sync_one, inspection)

    finished_at = utc_now()
    ordered_outcomes = tuple(sorted(outcomes, key=lambda item: item.repo_name))
    summary = summarize_outcomes(ordered_outcomes)

    await emit(
        RunEvent(
            run_id=run_id,
            event_type=RunEventType.RUN_COMPLETED,
            ts=finished_at,
            message="run completed",
        )
    )

    return RunRecord(
        run_id=run_id,
        command="sync",
        path=path,
        policy=policy,
        started_at=started_at,
        finished_at=finished_at,
        events=(),
        outcomes=ordered_outcomes,
        summary=summary,
    )
