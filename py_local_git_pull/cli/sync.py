"""Sync command with event-driven execution and journal persistence."""

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Annotated

import anyio
import typer

from py_local_git_pull.config.defaults import DEFAULT_MAX_DEPTH, DEFAULT_WORKERS
from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations
from py_local_git_pull.core.models import PolicyMode, RepoOutcome, RepoStatus, RunRecord
from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.core.services.sync_service import SyncService, build_sync_plan
from py_local_git_pull.runtime.executor import execute_sync_run, summarize_outcomes
from py_local_git_pull.runtime.journal import write_run_record
from py_local_git_pull.state.paths import get_state_paths
from py_local_git_pull.ui.console import make_console
from py_local_git_pull.ui.interactive import choose_repo_paths
from py_local_git_pull.ui.live import LiveSyncRenderer
from py_local_git_pull.ui.sync_view import (
    render_next_actions,
    render_plan_panel,
    render_profile_panel,
    render_summary_panel,
    render_sync_header,
)


def build_sync_service(repo_path: str) -> SyncService:
    runner = GitRunner(repo_path)
    return SyncService(
        runner=runner,
        branch_ops=BranchOperations(runner),
        stash_ops=StashOperations(runner),
        remote_ops=RemoteOperations(runner),
        info_ops=InfoOperations(runner),
    )


def run_sync_flow(
    *,
    path: str,
    inspections: tuple,
    branches: tuple[str, ...],
    policy: PolicyMode,
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
    dry_run: bool,
    workers: int,
    emit,
):
    """Execute the sync flow, returning outcomes."""
    plans = tuple(
        build_sync_plan(insp, branches=branches, no_stash=no_stash) for insp in inspections
    )

    if dry_run:
        outcomes = tuple(
            RepoOutcome(
                repo_name=insp.repo_name,
                path=insp.path,
                status=RepoStatus.SKIPPED if plan.will_skip else RepoStatus.SYNCED,
                current_branch=insp.current_branch,
                target_branches=plan.target_branches,
                synced_branches=(),
                skipped_branches=plan.target_branches if plan.will_skip else (),
                stashed=False,
                notes=((plan.skip_reason,) if plan.skip_reason else ()),
            )
            for insp, plan in zip(inspections, plans, strict=False)
        )
        now = datetime.now(UTC)
        return RunRecord(
            run_id=f"{now.strftime('%Y%m%dT%H%M%SZ')}-dry-run",
            command="sync",
            path=path,
            policy=policy,
            started_at=now.isoformat(),
            finished_at=now.isoformat(),
            events=(),
            outcomes=outcomes,
            summary=summarize_outcomes(outcomes),
        )

    execute = partial(
        execute_sync_run,
        path=path,
        inspections=inspections,
        branches=branches,
        policy=policy,
        service_factory=build_sync_service,
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
        no_stash=no_stash,
        depth=depth,
        workers=workers,
        emit=emit,
    )
    return anyio.run(execute)


def sync_command(
    path: Path,
    branch: Annotated[
        list[str] | None, typer.Option("--branch", "-b", help="Branch to sync (repeatable)")
    ] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
    max_depth: Annotated[int, typer.Option("--max-depth")] = DEFAULT_MAX_DEPTH,
    auto_upstream: Annotated[bool, typer.Option("--auto-upstream")] = False,
    skip_non_exist: Annotated[bool, typer.Option("--skip-non-exist/--no-skip-non-exist")] = True,
    no_stash: Annotated[bool, typer.Option("--no-stash")] = False,
    depth: Annotated[int, typer.Option("--depth")] = 1,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Interactive repo selection")
    ] = False,
    policy: Annotated[
        PolicyMode,
        typer.Option("--policy", case_sensitive=False, help="Execution policy: safe/careful/force"),
    ] = PolicyMode.SAFE,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show plan without executing")
    ] = False,
    workers: Annotated[
        int, typer.Option("--workers", "-w", help="Parallel sync workers")
    ] = DEFAULT_WORKERS,
    output: Annotated[
        str,
        typer.Option("--output", help="Output format: table, json, or jsonl"),
    ] = "table",
    profile_inspect: Annotated[
        bool,
        typer.Option("--profile-inspect", help="Show lightweight stage timings"),
    ] = False,
) -> None:
    """Sync local git repositories."""
    console = make_console()
    branches = tuple(branch or ())
    paths = get_state_paths()
    timings: dict[str, float] = {}

    inspector = RepoInspector()
    inspect_started = perf_counter()
    inspections = inspector.inspect_path(
        str(path),
        recursive=recursive,
        max_depth=max_depth,
        include_branch_deltas=not interactive,
    )
    timings["lightweight_inspect" if interactive else "inspect"] = (
        perf_counter() - inspect_started
    )

    if interactive:
        picker_started = perf_counter()
        selected_paths = choose_repo_paths(inspections)
        timings["picker"] = perf_counter() - picker_started
        if not selected_paths:
            console.print("[yellow]No repos selected, exiting.[/]")
            raise typer.Exit(code=0)
        full_inspect_started = perf_counter()
        inspections = tuple(
            inspector.inspect_repo(
                selected_path,
                include_branch_deltas=True,
            )
            for selected_path in selected_paths
        )
        timings["full_inspect"] = perf_counter() - full_inspect_started

    try:
        event_log = []
        renderer: LiveSyncRenderer | None = None

        async def emit(event):
            event_log.append(event)
            if output == "jsonl":
                print(json.dumps(asdict(event), ensure_ascii=False))
            elif renderer is not None:
                renderer.push(event)

        def execute() -> RunRecord:
            return run_sync_flow(
                path=str(path),
                inspections=inspections,
                branches=branches,
                policy=policy,
                auto_upstream=auto_upstream,
                skip_non_exist=skip_non_exist,
                no_stash=no_stash,
                depth=depth,
                dry_run=dry_run,
                workers=workers,
                emit=emit,
            )

        if output == "table":
            with LiveSyncRenderer(console) as live_renderer:
                renderer = live_renderer
                execution_started = perf_counter()
                run_record = execute()
                timings["execution"] = perf_counter() - execution_started
        else:
            execution_started = perf_counter()
            run_record = execute()
            timings["execution"] = perf_counter() - execution_started

        run_record = replace(run_record, events=tuple(event_log))
        write_run_record(paths.runs_dir, run_record)

        if output == "json":
            payload = {
                "schema_version": 3,
                "command": "sync",
                "run": asdict(run_record),
                "repos": [asdict(o) for o in run_record.outcomes],
            }
            if profile_inspect:
                payload["timings"] = timings
            print(json.dumps(payload, ensure_ascii=False, default=list))
            raise typer.Exit(code=0)

        if output == "table":
            render_sync_header(console, str(path), inspections, branches, dry_run)
            if profile_inspect:
                render_profile_panel(console, timings)
            render_plan_panel(console, inspections)
            render_summary_panel(console, run_record.outcomes)
            render_next_actions(console, run_record.outcomes)
        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]sync failed: {exc}")
        raise typer.Exit(code=1) from exc
