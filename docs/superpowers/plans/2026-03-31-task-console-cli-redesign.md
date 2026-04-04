# Task Console CLI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `py-local-git-pull` 重构为纯 CLI 的 Git 任务控制台，落地 `scan / sync / doctor` 子命令、仓库级任务视图、失败分类与诊断建议。

**Architecture:** 使用 `Typer` 重建命令骨架，保留现有 `GitManager / BranchSyncer / RepoFinder` 的 Git 执行核心，在 `core/` 中新增 inspection、planning、failure taxonomy 与新结果模型，在 `ui/` 中新增 summary、dashboard、events、doctor 渲染器。`doctor` 采用实时诊断模式，基于当前仓库状态生成建议，不依赖额外状态存储。

**Tech Stack:** Python 3.13, Typer, Rich, Questionary, pytest, Ruff

---

## Scope Check

这份 spec 虽然覆盖了命令、模型、渲染和诊断，但它们都属于同一个可交付子系统：现代 CLI 重构。它不是多个互不相关的产品块，所以保持为一份实施计划是合理的。

## File Structure Lock-In

### Create

- `docs/superpowers/plans/2026-03-31-task-console-cli-redesign.md`
- `py_local_git_pull/commands/__init__.py`
- `py_local_git_pull/commands/app.py`
- `py_local_git_pull/commands/scan.py`
- `py_local_git_pull/commands/sync.py`
- `py_local_git_pull/commands/doctor.py`
- `py_local_git_pull/core/models.py`
- `py_local_git_pull/core/repo_inspector.py`
- `py_local_git_pull/core/sync_planner.py`
- `py_local_git_pull/core/failure_catalog.py`
- `py_local_git_pull/ui/dashboard.py`
- `py_local_git_pull/ui/events.py`
- `py_local_git_pull/ui/summary.py`
- `py_local_git_pull/ui/doctor_view.py`
- `py_local_git_pull/ui/prompts.py`
- `tests/commands/test_app.py`
- `tests/commands/test_scan_command.py`
- `tests/commands/test_sync_command.py`
- `tests/commands/test_doctor_command.py`
- `tests/commands/test_readme_contract.py`
- `tests/core/test_models.py`
- `tests/core/test_repo_inspector.py`
- `tests/core/test_sync_planner.py`
- `tests/core/test_failure_catalog.py`
- `tests/core/test_sync_execution.py`
- `tests/ui/test_summary_render.py`
- `tests/ui/test_doctor_view.py`

### Modify

- `pyproject.toml`
- `py_local_git_pull/main.py`
- `py_local_git_pull/__main__.py`
- `py_local_git_pull/core/__init__.py`
- `py_local_git_pull/core/git_manager.py`
- `py_local_git_pull/core/branch_syncer.py`
- `py_local_git_pull/core/sync_options.py`
- `py_local_git_pull/ui/__init__.py`
- `README.md`

### Delete

- `py_local_git_pull/config/cli_parser.py`
- `py_local_git_pull/core/result_model.py`
- `py_local_git_pull/ui/display.py`
- `py_local_git_pull/ui/progress.py`

### Responsibility map

```text
commands/app.py
  -> Typer app 入口与子命令注册

commands/scan.py
  -> 组装 inspection + scan 输出

commands/sync.py
  -> 组装 inspection + planning + execution + task console 输出

commands/doctor.py
  -> 组装实时诊断与建议输出

core/models.py
  -> 新的 Inspection / Plan / Outcome / Failure 数据模型

core/repo_inspector.py
  -> 将 GitManager 当前能力翻译成 RepoInspection

core/sync_planner.py
  -> 将 RepoInspection 翻译成 RepoSyncPlan

core/failure_catalog.py
  -> 将 Git 原始错误或 inspection 风险翻译成 FailureRecord

ui/dashboard.py
  -> sync Header / Plan / Summary / Next Actions

ui/events.py
  -> sync 仓库级事件流

ui/summary.py
  -> scan / json 前的简要汇总输出

ui/doctor_view.py
  -> doctor 的 problem / why / do-now 视图
```

## Task 1: Bootstrap the Typer Command App

**Files:**
- Create: `py_local_git_pull/commands/__init__.py`
- Create: `py_local_git_pull/commands/app.py`
- Create: `py_local_git_pull/commands/scan.py`
- Create: `py_local_git_pull/commands/sync.py`
- Create: `py_local_git_pull/commands/doctor.py`
- Modify: `pyproject.toml`
- Modify: `py_local_git_pull/main.py`
- Modify: `py_local_git_pull/__main__.py`
- Test: `tests/commands/test_app.py`

- [ ] **Step 1: Write the failing CLI bootstrap test**

```python
from typer.testing import CliRunner

from py_local_git_pull.commands.app import app


runner = CliRunner()


def test_root_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout
    assert "sync" in result.stdout
    assert "doctor" in result.stdout


def test_sync_help_mentions_branch_option() -> None:
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--branch" in result.stdout
    assert "--interactive" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --group dev pytest tests/commands/test_app.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'py_local_git_pull.commands'`

- [ ] **Step 3: Add Typer and Questionary dependencies**

Modify `pyproject.toml`:

```toml
[project]
dependencies = [
  "rich>=14.3.3",
  "typer>=0.16.0",
  "questionary>=2.1.0",
]
```

- [ ] **Step 4: Create the new command app skeleton**

Create `py_local_git_pull/commands/app.py`:

```python
import typer

from .doctor import doctor_command
from .scan import scan_command
from .sync import sync_command


app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Git task console for scanning, syncing, and diagnosing local repositories.",
)

app.command("scan")(scan_command)
app.command("sync")(sync_command)
app.command("doctor")(doctor_command)
```

Create `py_local_git_pull/commands/scan.py`:

```python
from pathlib import Path

import typer


def scan_command(path: Path) -> None:
    raise typer.Exit(code=0)
```

Create `py_local_git_pull/commands/sync.py`:

```python
from pathlib import Path
from typing import List, Optional

import typer


def sync_command(
    path: Path,
    branch: Optional[List[str]] = typer.Option(None, "--branch", "-b"),
    interactive: bool = typer.Option(False, "--interactive"),
) -> None:
    raise typer.Exit(code=0)
```

Create `py_local_git_pull/commands/doctor.py`:

```python
from pathlib import Path
from typing import Optional

import typer


def doctor_command(
    path: Path,
    repo: Optional[str] = typer.Option(None, "--repo"),
    kind: Optional[str] = typer.Option(None, "--kind"),
) -> None:
    raise typer.Exit(code=0)
```

- [ ] **Step 5: Point the package entrypoint at the Typer app**

Modify `py_local_git_pull/main.py`:

```python
from .commands.app import app


def main() -> None:
    app(prog_name="py-local-git-pull")
```

Modify `py_local_git_pull/__main__.py`:

```python
from .main import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run --group dev pytest tests/commands/test_app.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml py_local_git_pull/main.py py_local_git_pull/__main__.py py_local_git_pull/commands tests/commands/test_app.py
git commit -m "feat(cli): bootstrap typer command app"
```

## Task 2: Introduce Core Models and Failure Taxonomy

**Files:**
- Create: `py_local_git_pull/core/models.py`
- Create: `py_local_git_pull/core/failure_catalog.py`
- Modify: `py_local_git_pull/core/__init__.py`
- Test: `tests/core/test_models.py`
- Test: `tests/core/test_failure_catalog.py`

- [ ] **Step 1: Write the failing model tests**

```python
from py_local_git_pull.core.models import FailureKind, RepoStatus, RiskFlag


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
```

```python
from py_local_git_pull.core.failure_catalog import classify_git_failure
from py_local_git_pull.core.models import FailureKind


def test_classify_upstream_missing_error() -> None:
    failure = classify_git_failure("fatal: no upstream configured")
    assert failure.kind is FailureKind.UPSTREAM_MISSING
    assert failure.can_auto_fix is True


def test_classify_ff_only_failure() -> None:
    failure = classify_git_failure("fatal: Not possible to fast-forward, aborting.")
    assert failure.kind is FailureKind.PULL_FF_CONFLICT
    assert failure.can_auto_fix is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/core/test_models.py tests/core/test_failure_catalog.py -q`
Expected: FAIL with `ModuleNotFoundError` for `py_local_git_pull.core.models`

- [ ] **Step 3: Create the new shared models**

Create `py_local_git_pull/core/models.py`:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class RepoStatus(str, Enum):
    SYNCED = "synced"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    FAILED = "failed"


class BranchStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    SKIPPED = "skipped"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskFlag(str, Enum):
    HAS_LOCAL_CHANGES = "has_local_changes"
    DETACHED_HEAD = "detached_head"
    NO_UPSTREAM = "no_upstream"
    REMOTE_BRANCH_MISSING = "remote_branch_missing"
    BARE_REPOSITORY = "bare_repository"
    UNKNOWN_STATE = "unknown_state"


class FailureKind(str, Enum):
    DIRTY_WORKTREE = "dirty_worktree"
    STASH_FAILED = "stash_failed"
    FETCH_FAILED = "fetch_failed"
    CHECKOUT_FAILED = "checkout_failed"
    UPSTREAM_MISSING = "upstream_missing"
    REMOTE_BRANCH_MISSING = "remote_branch_missing"
    PULL_FF_CONFLICT = "pull_ff_conflict"
    PULL_REJECTED = "pull_rejected"
    BARE_REPOSITORY = "bare_repository"
    REPO_NOT_FOUND = "repo_not_found"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_GIT_ERROR = "unknown_git_error"


class PlanAction(str, Enum):
    SYNC_CURRENT = "sync_current"
    SYNC_BRANCHES = "sync_branches"
    SKIP = "skip"


class StashStrategy(str, Enum):
    NONE = "none"
    AUTO_STASH = "auto_stash"
    USER_DISABLED = "user_disabled"


@dataclass(frozen=True)
class SuggestedAction:
    label: str
    command: Optional[str]
    description: str
    auto_fixable: bool = False


@dataclass(frozen=True)
class FailureRecord:
    kind: FailureKind
    summary: str
    detail: Optional[str]
    raw_error: Optional[str]
    can_auto_fix: bool
    suggested_actions: Tuple[SuggestedAction, ...] = ()


@dataclass(frozen=True)
class BranchInspection:
    name: str
    is_current: bool
    exists_locally: bool
    exists_remotely: bool
    has_upstream: bool
    upstream_name: Optional[str]
    ahead: Optional[int]
    behind: Optional[int]


@dataclass(frozen=True)
class RepoInspection:
    repo_name: str
    path: str
    current_branch: Optional[str]
    is_git_repo: bool
    is_bare: bool
    has_changes: bool
    has_untracked_changes: bool
    detached_head: bool
    branches: Tuple[BranchInspection, ...]
    risk_level: RiskLevel
    risk_flags: Tuple[RiskFlag, ...]


@dataclass(frozen=True)
class RepoSyncPlan:
    repo_name: str
    path: str
    target_branches: Tuple[str, ...]
    action: PlanAction
    stash_strategy: StashStrategy
    will_skip: bool
    skip_reason: Optional[str]
    needs_attention: bool
    attention_reason: Optional[str]


@dataclass(frozen=True)
class BranchOutcome:
    name: str
    status: BranchStatus
    is_current: bool
    has_upstream: bool
    upstream_name: Optional[str]
    ahead: Optional[int]
    behind: Optional[int]
    failure: Optional[FailureRecord] = None


@dataclass(frozen=True)
class RepoOutcome:
    repo_name: str
    path: str
    status: RepoStatus
    current_branch: Optional[str]
    target_branches: Tuple[str, ...]
    synced_branches: Tuple[str, ...]
    skipped_branches: Tuple[str, ...]
    stashed: bool
    branch_outcomes: Tuple[BranchOutcome, ...] = ()
    failure: Optional[FailureRecord] = None
    notes: Tuple[str, ...] = ()
```

- [ ] **Step 4: Create the failure catalog**

Create `py_local_git_pull/core/failure_catalog.py`:

```python
from .models import FailureKind, FailureRecord, SuggestedAction


def classify_git_failure(raw_error: str | None) -> FailureRecord:
    text = (raw_error or "").lower()

    if "fetch failed" in text:
        return FailureRecord(
            kind=FailureKind.FETCH_FAILED,
            summary="fetch failed before sync could start",
            detail="The remote could not be fetched successfully.",
            raw_error=raw_error,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="retry_fetch",
                    command=None,
                    description="verify network, auth, and remote URL, then retry the sync",
                    auto_fixable=False,
                ),
            ),
        )

    if "no upstream" in text:
        return FailureRecord(
            kind=FailureKind.UPSTREAM_MISSING,
            summary="current branch has no upstream",
            detail="The branch is not tracking a remote branch.",
            raw_error=raw_error,
            can_auto_fix=True,
            suggested_actions=(
                SuggestedAction(
                    label="set_upstream",
                    command=None,
                    description="rerun with --auto-upstream or set upstream manually",
                    auto_fixable=True,
                ),
            ),
        )

    if "not possible to fast-forward" in text:
        return FailureRecord(
            kind=FailureKind.PULL_FF_CONFLICT,
            summary="fast-forward only pull cannot continue",
            detail="Local and remote history diverged.",
            raw_error=raw_error,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="inspect_divergence",
                    command=None,
                    description="inspect local history and choose rebase, merge, or reset",
                    auto_fixable=False,
                ),
            ),
        )

    return FailureRecord(
        kind=FailureKind.UNKNOWN_GIT_ERROR,
        summary="git command failed",
        detail="The error did not match a known failure pattern.",
        raw_error=raw_error,
        can_auto_fix=False,
        suggested_actions=(
            SuggestedAction(
                label="rerun_manually",
                command=None,
                description="rerun the relevant git command manually to inspect full stderr",
                auto_fixable=False,
            ),
        ),
    )
```

- [ ] **Step 5: Export the new models from the core package**

Modify `py_local_git_pull/core/__init__.py`:

```python
from .failure_catalog import classify_git_failure
from .git_manager import GitManager
from .models import (
    BranchInspection,
    BranchOutcome,
    BranchStatus,
    FailureKind,
    FailureRecord,
    PlanAction,
    RepoInspection,
    RepoOutcome,
    RepoStatus,
    RepoSyncPlan,
    RiskFlag,
    RiskLevel,
    StashStrategy,
    SuggestedAction,
)
from .repo_finder import find_git_repos, is_git_repo
from .sync_options import SyncOptions

__all__ = [
    "GitManager",
    "find_git_repos",
    "is_git_repo",
    "SyncOptions",
    "classify_git_failure",
    "BranchInspection",
    "BranchOutcome",
    "BranchStatus",
    "FailureKind",
    "FailureRecord",
    "PlanAction",
    "RepoInspection",
    "RepoOutcome",
    "RepoStatus",
    "RepoSyncPlan",
    "RiskFlag",
    "RiskLevel",
    "StashStrategy",
    "SuggestedAction",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/core/test_models.py tests/core/test_failure_catalog.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add py_local_git_pull/core py_local_git_pull/core/__init__.py tests/core/test_models.py tests/core/test_failure_catalog.py
git commit -m "feat(core): add task console models and failure taxonomy"
```

## Task 3: Build the Repo Inspector and the `scan` Command

**Files:**
- Create: `py_local_git_pull/core/repo_inspector.py`
- Create: `py_local_git_pull/ui/summary.py`
- Modify: `py_local_git_pull/commands/scan.py`
- Test: `tests/core/test_repo_inspector.py`
- Test: `tests/commands/test_scan_command.py`
- Test: `tests/ui/test_summary_render.py`

- [ ] **Step 1: Write the failing repo inspector tests**

```python
from py_local_git_pull.core.models import RiskFlag, RiskLevel
from py_local_git_pull.core.repo_inspector import derive_risk_state


def test_local_changes_raise_medium_risk() -> None:
    level, flags = derive_risk_state(
        has_changes=True,
        detached_head=False,
        is_bare=False,
        branches_have_missing_upstream=False,
        branches_have_missing_remote=False,
    )
    assert level is RiskLevel.MEDIUM
    assert RiskFlag.HAS_LOCAL_CHANGES in flags


def test_detached_head_raises_high_risk() -> None:
    level, flags = derive_risk_state(
        has_changes=False,
        detached_head=True,
        is_bare=False,
        branches_have_missing_upstream=False,
        branches_have_missing_remote=False,
    )
    assert level is RiskLevel.HIGH
    assert RiskFlag.DETACHED_HEAD in flags
```

```python
from typer.testing import CliRunner

from py_local_git_pull.commands.app import app


runner = CliRunner()


def test_scan_help_lists_recursive_options() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.stdout
    assert "--max-depth" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/core/test_repo_inspector.py tests/commands/test_scan_command.py -q`
Expected: FAIL with `ImportError` for `repo_inspector`

- [ ] **Step 3: Implement `RepoInspector` and risk derivation**

Create `py_local_git_pull/core/repo_inspector.py`:

```python
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Tuple

from .git_manager import GitManager
from .models import BranchInspection, RepoInspection, RiskFlag, RiskLevel
from .repo_finder import find_git_repos, is_git_repo


def derive_risk_state(
    *,
    has_changes: bool,
    detached_head: bool,
    is_bare: bool,
    branches_have_missing_upstream: bool,
    branches_have_missing_remote: bool,
) -> tuple[RiskLevel, tuple[RiskFlag, ...]]:
    flags: list[RiskFlag] = []

    if has_changes:
        flags.append(RiskFlag.HAS_LOCAL_CHANGES)
    if detached_head:
        flags.append(RiskFlag.DETACHED_HEAD)
    if is_bare:
        flags.append(RiskFlag.BARE_REPOSITORY)
    if branches_have_missing_upstream:
        flags.append(RiskFlag.NO_UPSTREAM)
    if branches_have_missing_remote:
        flags.append(RiskFlag.REMOTE_BRANCH_MISSING)

    if RiskFlag.DETACHED_HEAD in flags or RiskFlag.BARE_REPOSITORY in flags:
        level = RiskLevel.HIGH
    elif flags:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return level, tuple(flags)


class RepoInspector:
    def inspect_repo(self, repo_path: str) -> RepoInspection:
        manager = GitManager(repo_path)
        current_branch = manager.get_current_branch() or None

        returncode, bare_stdout, _ = manager.executor.run(
            ["rev-parse", "--is-bare-repository"],
            check=False,
        )
        is_bare = returncode == 0 and bare_stdout == "true"

        branch_details = manager.get_branch_details()
        branches = tuple(
            BranchInspection(
                name=detail.name,
                is_current=detail.is_current,
                exists_locally=detail.exists_locally,
                exists_remotely=detail.exists_remotely,
                has_upstream=detail.has_upstream,
                upstream_name=detail.upstream_name,
                ahead=detail.ahead_behind.ahead if detail.ahead_behind else None,
                behind=detail.ahead_behind.behind if detail.ahead_behind else None,
            )
            for detail in branch_details
        )

        level, flags = derive_risk_state(
            has_changes=manager.has_changes(),
            detached_head=current_branch is None,
            is_bare=is_bare,
            branches_have_missing_upstream=any(not branch.has_upstream for branch in branches),
            branches_have_missing_remote=any(not branch.exists_remotely for branch in branches),
        )

        return RepoInspection(
            repo_name=Path(repo_path).name,
            path=str(Path(repo_path).resolve()),
            current_branch=current_branch,
            is_git_repo=is_git_repo(repo_path),
            is_bare=is_bare,
            has_changes=manager.has_changes(),
            has_untracked_changes=manager.has_changes(),
            detached_head=current_branch is None,
            branches=branches,
            risk_level=level,
            risk_flags=flags,
        )

    def inspect_path(self, path: str, recursive: bool, max_depth: int) -> tuple[RepoInspection, ...]:
        if recursive:
            repo_paths = find_git_repos(path, max_depth)
        else:
            repo_paths = [path] if is_git_repo(path) else []
        return tuple(self.inspect_repo(repo_path) for repo_path in repo_paths)
```

- [ ] **Step 4: Add the scan summary renderer**

Create `py_local_git_pull/ui/summary.py`:

```python
from collections import Counter

from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import RepoInspection, RiskLevel


def render_scan_summary(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    risk_counter = Counter(inspection.risk_level.value for inspection in inspections)
    body = "\n".join(
        [
            f"total: {len(inspections)}",
            f"high: {risk_counter.get(RiskLevel.HIGH.value, 0)}",
            f"medium: {risk_counter.get(RiskLevel.MEDIUM.value, 0)}",
            f"low: {risk_counter.get(RiskLevel.LOW.value, 0)}",
        ]
    )
    console.print(Panel(body, title="SCAN SUMMARY", border_style="cyan"))
```

- [ ] **Step 5: Implement the `scan` command**

Modify `py_local_git_pull/commands/scan.py`:

```python
import json
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console

from py_local_git_pull.core.repo_inspector import RepoInspector
from py_local_git_pull.ui.summary import render_scan_summary


def scan_command(
    path: Path,
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    max_depth: int = typer.Option(3, "--max-depth"),
    output: str = typer.Option("table", "--output"),
) -> None:
    inspections = RepoInspector().inspect_path(str(path), recursive=recursive, max_depth=max_depth)

    if output == "json":
        payload = {
            "schema_version": 2,
            "command": "scan",
            "path": str(path),
            "repos": [asdict(inspection) for inspection in inspections],
        }
        print(json.dumps(payload, ensure_ascii=False, default=list))
        return

    console = Console()
    render_scan_summary(console, inspections)
```

- [ ] **Step 6: Add a renderer smoke test**

Create `tests/ui/test_summary_render.py`:

```python
from rich.console import Console

from py_local_git_pull.core.models import RepoInspection, RiskLevel
from py_local_git_pull.ui.summary import render_scan_summary


def test_render_scan_summary_contains_title() -> None:
    console = Console(record=True)
    inspection = RepoInspection(
        repo_name="demo",
        path="/tmp/demo",
        current_branch="main",
        is_git_repo=True,
        is_bare=False,
        has_changes=False,
        has_untracked_changes=False,
        detached_head=False,
        branches=(),
        risk_level=RiskLevel.LOW,
        risk_flags=(),
    )
    render_scan_summary(console, (inspection,))
    output = console.export_text()
    assert "SCAN SUMMARY" in output
    assert "total: 1" in output
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/core/test_repo_inspector.py tests/commands/test_scan_command.py tests/ui/test_summary_render.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add py_local_git_pull/core/repo_inspector.py py_local_git_pull/ui/summary.py py_local_git_pull/commands/scan.py tests/core/test_repo_inspector.py tests/commands/test_scan_command.py tests/ui/test_summary_render.py
git commit -m "feat(scan): add repo inspection and scan command"
```

## Task 4: Add Sync Planning

**Files:**
- Create: `py_local_git_pull/core/sync_planner.py`
- Test: `tests/core/test_sync_planner.py`

- [ ] **Step 1: Write the failing planner tests**

```python
from py_local_git_pull.core.models import (
    BranchInspection,
    PlanAction,
    RepoInspection,
    RiskFlag,
    RiskLevel,
    StashStrategy,
)
from py_local_git_pull.core.sync_planner import build_sync_plan


def _inspection(*, risk_flags=(), has_changes=False) -> RepoInspection:
    return RepoInspection(
        repo_name="demo",
        path="/tmp/demo",
        current_branch="main",
        is_git_repo=True,
        is_bare=False,
        has_changes=has_changes,
        has_untracked_changes=has_changes,
        detached_head=False,
        branches=(
            BranchInspection(
                name="main",
                is_current=True,
                exists_locally=True,
                exists_remotely=True,
                has_upstream=True,
                upstream_name="origin/main",
                ahead=0,
                behind=0,
            ),
        ),
        risk_level=RiskLevel.MEDIUM if risk_flags else RiskLevel.LOW,
        risk_flags=tuple(risk_flags),
    )


def test_build_sync_plan_for_current_branch() -> None:
    plan = build_sync_plan(_inspection(), branches=(), no_stash=False)
    assert plan.action is PlanAction.SYNC_CURRENT
    assert plan.stash_strategy is StashStrategy.NONE


def test_build_sync_plan_for_dirty_repo_uses_auto_stash() -> None:
    plan = build_sync_plan(_inspection(has_changes=True), branches=("main",), no_stash=False)
    assert plan.action is PlanAction.SYNC_BRANCHES
    assert plan.stash_strategy is StashStrategy.AUTO_STASH


def test_build_sync_plan_skips_bare_repo() -> None:
    plan = build_sync_plan(
        _inspection(risk_flags=(RiskFlag.BARE_REPOSITORY,)),
        branches=(),
        no_stash=False,
    )
    assert plan.will_skip is True
    assert plan.action is PlanAction.SKIP
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/core/test_sync_planner.py -q`
Expected: FAIL with `ImportError` for `sync_planner`

- [ ] **Step 3: Implement the planner**

Create `py_local_git_pull/core/sync_planner.py`:

```python
from .models import PlanAction, RepoInspection, RepoSyncPlan, RiskFlag, StashStrategy


def build_sync_plan(
    inspection: RepoInspection,
    *,
    branches: tuple[str, ...],
    no_stash: bool,
) -> RepoSyncPlan:
    if RiskFlag.BARE_REPOSITORY in inspection.risk_flags:
        return RepoSyncPlan(
            repo_name=inspection.repo_name,
            path=inspection.path,
            target_branches=(),
            action=PlanAction.SKIP,
            stash_strategy=StashStrategy.NONE,
            will_skip=True,
            skip_reason="bare repository",
            needs_attention=True,
            attention_reason="bare repository cannot follow the standard task flow",
        )

    target_branches = branches or ((inspection.current_branch,) if inspection.current_branch else ())
    action = PlanAction.SYNC_BRANCHES if branches else PlanAction.SYNC_CURRENT
    stash_strategy = (
        StashStrategy.USER_DISABLED
        if no_stash
        else StashStrategy.AUTO_STASH if inspection.has_changes else StashStrategy.NONE
    )

    return RepoSyncPlan(
        repo_name=inspection.repo_name,
        path=inspection.path,
        target_branches=tuple(branch for branch in target_branches if branch),
        action=action,
        stash_strategy=stash_strategy,
        will_skip=False,
        skip_reason=None,
        needs_attention=bool(inspection.risk_flags),
        attention_reason=", ".join(flag.value for flag in inspection.risk_flags) or None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/core/test_sync_planner.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add py_local_git_pull/core/sync_planner.py tests/core/test_sync_planner.py
git commit -m "feat(core): add sync planning layer"
```

## Task 5: Adapt Execution Core to Emit `RepoOutcome`

**Files:**
- Modify: `py_local_git_pull/core/git_manager.py`
- Modify: `py_local_git_pull/core/branch_syncer.py`
- Modify: `py_local_git_pull/core/sync_options.py`
- Test: `tests/core/test_sync_execution.py`

- [ ] **Step 1: Write the failing execution outcome test**

```python
from py_local_git_pull.core.models import FailureKind, RepoStatus
from py_local_git_pull.core.git_manager import GitManager


def test_sync_repo_returns_failed_outcome_when_fetch_fails(monkeypatch) -> None:
    manager = GitManager("/tmp/demo")

    monkeypatch.setattr(manager, "get_current_branch", lambda: "main")
    monkeypatch.setattr(manager, "fetch", lambda depth: False)

    outcome = manager.sync_repo_for_task_console(branches=(), auto_upstream=False, skip_non_exist=True, no_stash=False, depth=1)
    assert outcome.status is RepoStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.kind is FailureKind.FETCH_FAILED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/core/test_sync_execution.py -q`
Expected: FAIL with `AttributeError: 'GitManager' object has no attribute 'sync_repo_for_task_console'`

- [ ] **Step 3: Add a task-console sync entrypoint to `GitManager`**

Modify `py_local_git_pull/core/git_manager.py`:

```python
from .failure_catalog import classify_git_failure
from .models import RepoOutcome, RepoStatus


def sync_repo_for_task_console(
    self,
    *,
    branches: tuple[str, ...],
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
) -> RepoOutcome:
    current_branch = self.get_current_branch() or None

    if not self.fetch(depth):
        failure = classify_git_failure("fetch failed")
        return RepoOutcome(
            repo_name=self.repo_name,
            path=self.repo_path,
            status=RepoStatus.FAILED,
            current_branch=current_branch,
            target_branches=branches,
            synced_branches=(),
            skipped_branches=(),
            stashed=False,
            failure=failure,
        )

    # 后续步骤在下一步接 BranchSyncer 结果聚合
```

- [ ] **Step 4: Teach `BranchSyncer` to return `BranchOutcome`**

Modify `py_local_git_pull/core/branch_syncer.py`:

```python
from .failure_catalog import classify_git_failure
from .models import BranchOutcome, BranchStatus
from .result_model import SyncResult
from .sync_options import SyncOptions


def sync_branch_for_task_console(
    self,
    branch: str,
    *,
    auto_upstream: bool,
        skip_non_exist: bool,
        is_current: bool = False,
    ) -> BranchOutcome:
    legacy_result = SyncResult(
        repo_name=self.git_manager.repo_name,
        path=self.git_manager.repo_path,
        current_branch=self.git_manager.get_current_branch(),
    )
    legacy_options = SyncOptions(
        path=self.git_manager.repo_path,
        branch=branch if not is_current else None,
        branches=(),
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
    )
    branch_detail = self.sync_single_branch(
        branch,
        legacy_options,
        legacy_result,
        is_current=is_current,
    )
    failure = classify_git_failure(branch_detail.error) if branch_detail.error else None
    return BranchOutcome(
        name=branch_detail.name,
        status=BranchStatus(branch_detail.status.value),
        is_current=branch_detail.is_current,
        has_upstream=branch_detail.has_upstream,
        upstream_name=branch_detail.upstream_name,
        ahead=branch_detail.ahead_behind.ahead if branch_detail.ahead_behind else None,
        behind=branch_detail.ahead_behind.behind if branch_detail.ahead_behind else None,
        failure=failure,
    )
```

- [ ] **Step 5: Finish repo outcome aggregation**

Modify `py_local_git_pull/core/git_manager.py` again:

```python
branch_names = branches or ((current_branch,) if current_branch else ())
branch_outcomes = tuple(
    self.branch_syncer.sync_branch_for_task_console(
        branch_name,
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
        is_current=(branch_name == current_branch),
    )
    for branch_name in branch_names
)

failed = [outcome for outcome in branch_outcomes if outcome.status is BranchStatus.FAILED]
skipped = [outcome for outcome in branch_outcomes if outcome.status is BranchStatus.SKIPPED]
synced = [outcome for outcome in branch_outcomes if outcome.status is BranchStatus.SYNCED]

status = RepoStatus.SYNCED
if failed and synced:
    status = RepoStatus.PARTIAL
elif failed:
    status = RepoStatus.FAILED
elif skipped and not synced:
    status = RepoStatus.SKIPPED

return RepoOutcome(
    repo_name=self.repo_name,
    path=self.repo_path,
    status=status,
    current_branch=current_branch,
    target_branches=tuple(branch_names),
    synced_branches=tuple(outcome.name for outcome in synced),
    skipped_branches=tuple(outcome.name for outcome in skipped),
    stashed=False,
    branch_outcomes=branch_outcomes,
    failure=failed[0].failure if len(failed) == 1 and status is RepoStatus.FAILED else None,
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/core/test_sync_execution.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add py_local_git_pull/core/git_manager.py py_local_git_pull/core/branch_syncer.py py_local_git_pull/core/sync_options.py tests/core/test_sync_execution.py
git commit -m "feat(core): emit repo outcomes for task console sync"
```

## Task 6: Build the Sync Task Console UI

**Files:**
- Create: `py_local_git_pull/ui/dashboard.py`
- Create: `py_local_git_pull/ui/events.py`
- Modify: `py_local_git_pull/ui/__init__.py`
- Modify: `py_local_git_pull/commands/sync.py`
- Test: `tests/commands/test_sync_command.py`

- [ ] **Step 1: Write the failing sync command test**

```python
from typer.testing import CliRunner

from py_local_git_pull.commands.app import app


runner = CliRunner()


def test_sync_command_renders_plan_and_summary(monkeypatch) -> None:
    from py_local_git_pull.core.models import RepoInspection, RepoOutcome, RepoStatus, RiskLevel

    monkeypatch.setattr(
        "py_local_git_pull.commands.sync.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (
            RepoInspection(
                repo_name="demo",
                path="/tmp/demo",
                current_branch="main",
                is_git_repo=True,
                is_bare=False,
                has_changes=False,
                has_untracked_changes=False,
                detached_head=False,
                branches=(),
                risk_level=RiskLevel.LOW,
                risk_flags=(),
            ),
        ),
    )
    monkeypatch.setattr(
        "py_local_git_pull.commands.sync.run_sync_flow",
        lambda **_: (
            (
                RepoInspection(
                    repo_name="demo",
                    path="/tmp/demo",
                    current_branch="main",
                    is_git_repo=True,
                    is_bare=False,
                    has_changes=False,
                    has_untracked_changes=False,
                    detached_head=False,
                    branches=(),
                    risk_level=RiskLevel.LOW,
                    risk_flags=(),
                ),
            ),
            (
                RepoOutcome(
                    repo_name="demo",
                    path="/tmp/demo",
                    status=RepoStatus.SYNCED,
                    current_branch="main",
                    target_branches=("main",),
                    synced_branches=("main",),
                    skipped_branches=(),
                    stashed=False,
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["sync", "/tmp/demo"])
    assert result.exit_code == 0
    assert "PLAN" in result.stdout
    assert "SUMMARY" in result.stdout
    assert "NEXT ACTIONS" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/commands/test_sync_command.py -q`
Expected: FAIL with `ImportError` for `run_sync_flow` or dashboard modules

- [ ] **Step 3: Create the dashboard and event renderers**

Create `py_local_git_pull/ui/dashboard.py`:

```python
from collections import Counter

from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import RepoInspection, RepoOutcome, RepoStatus


def render_sync_header(console: Console, path: str, inspections: tuple[RepoInspection, ...], branches: tuple[str, ...]) -> None:
    body = f"path: {path}\nrepos: {len(inspections)}\nbranches: {', '.join(branches) if branches else 'current'}"
    console.print(Panel(body, title="py-local-git-pull sync", border_style="cyan"))


def render_plan_panel(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    safe = sum(1 for item in inspections if not item.risk_flags)
    attention = sum(1 for item in inspections if item.risk_flags)
    body = f"safe: {safe}\nattention: {attention}\nskipped: 0"
    console.print(Panel(body, title="PLAN", border_style="blue"))


def render_summary_panel(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    counts = Counter(outcome.status.value for outcome in outcomes)
    body = (
        f"success: {counts.get(RepoStatus.SYNCED.value, 0)}\n"
        f"partial: {counts.get(RepoStatus.PARTIAL.value, 0)}\n"
        f"skipped: {counts.get(RepoStatus.SKIPPED.value, 0)}\n"
        f"failed: {counts.get(RepoStatus.FAILED.value, 0)}"
    )
    console.print(Panel(body, title="SUMMARY", border_style="green"))


def render_next_actions(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    failed_count = sum(1 for outcome in outcomes if outcome.status is RepoStatus.FAILED)
    lines = [f"{failed_count} failed repos -> run doctor"] if failed_count else ["all repos synced cleanly"]
    console.print(Panel("\n".join(lines), title="NEXT ACTIONS", border_style="yellow"))
```

Create `py_local_git_pull/ui/events.py`:

```python
from rich.console import Console

from py_local_git_pull.core.models import RepoOutcome


def render_repo_events(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    console.print("EXECUTION")
    for index, outcome in enumerate(outcomes, start=1):
        branch = outcome.current_branch or "-"
        note = outcome.failure.kind.value if outcome.failure else branch
        console.print(f"[{index:02d}/{len(outcomes):02d}] {outcome.repo_name:<16} {outcome.status.value:<10} {note}")
```

- [ ] **Step 4: Wire the sync command to the new flow**

Modify `py_local_git_pull/commands/sync.py`:

```python
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

from py_local_git_pull.core.git_manager import GitManager
from py_local_git_pull.core.models import RepoOutcome, RepoStatus
from py_local_git_pull.core.repo_inspector import RepoInspector
from py_local_git_pull.core.sync_planner import build_sync_plan
from py_local_git_pull.ui.dashboard import (
    render_next_actions,
    render_plan_panel,
    render_summary_panel,
    render_sync_header,
)
from py_local_git_pull.ui.events import render_repo_events


def run_sync_flow(
    *,
    inspections: tuple,
    branch: tuple[str, ...],
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
) -> tuple[tuple, tuple]:
    outcomes: list[RepoOutcome] = []
    for inspection in inspections:
        plan = build_sync_plan(inspection, branches=branch, no_stash=no_stash)
        if plan.will_skip:
            outcomes.append(
                RepoOutcome(
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
            )
            continue

        manager = GitManager(inspection.path)
        outcomes.append(
            manager.sync_repo_for_task_console(
                branches=plan.target_branches,
                auto_upstream=auto_upstream,
                skip_non_exist=skip_non_exist,
                no_stash=no_stash,
                depth=depth,
            )
        )
    return inspections, tuple(outcomes)


def sync_command(
    path: Path,
    branch: Optional[List[str]] = typer.Option(None, "--branch", "-b"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    max_depth: int = typer.Option(3, "--max-depth"),
    auto_upstream: bool = typer.Option(False, "--auto-upstream"),
    skip_non_exist: bool = typer.Option(True, "--skip-non-exist/--no-skip-non-exist"),
    no_stash: bool = typer.Option(False, "--no-stash"),
    depth: int = typer.Option(1, "--depth"),
    interactive: bool = typer.Option(False, "--interactive"),
) -> None:
    console = Console()
    branches = tuple(branch or ())
    inspections = RepoInspector().inspect_path(str(path), recursive=recursive, max_depth=max_depth)
    inspections, outcomes = run_sync_flow(
        inspections=inspections,
        branch=branches,
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
        no_stash=no_stash,
        depth=depth,
    )
    render_sync_header(console, str(path), inspections, branches)
    render_plan_panel(console, inspections)
    render_repo_events(console, outcomes)
    render_summary_panel(console, outcomes)
    render_next_actions(console, outcomes)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/commands/test_sync_command.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add py_local_git_pull/ui py_local_git_pull/commands/sync.py tests/commands/test_sync_command.py
git commit -m "feat(sync): add task console dashboard and event stream"
```

## Task 7: Add Interactive Repo Selection

**Files:**
- Create: `py_local_git_pull/ui/prompts.py`
- Modify: `py_local_git_pull/commands/sync.py`
- Test: `tests/commands/test_sync_command.py`

- [ ] **Step 1: Write the failing interactive sync test**

```python
from typer.testing import CliRunner

from py_local_git_pull.commands.app import app


runner = CliRunner()


def test_sync_interactive_uses_prompt_selection(monkeypatch) -> None:
    from py_local_git_pull.core.models import RepoInspection, RiskLevel

    monkeypatch.setattr(
        "py_local_git_pull.commands.sync.RepoInspector.inspect_path",
        lambda self, path, recursive, max_depth: (
            RepoInspection(
                repo_name="demo",
                path="/tmp/demo",
                current_branch="main",
                is_git_repo=True,
                is_bare=False,
                has_changes=False,
                has_untracked_changes=False,
                detached_head=False,
                branches=(),
                risk_level=RiskLevel.LOW,
                risk_flags=(),
            ),
        ),
    )
    monkeypatch.setattr(
        "py_local_git_pull.commands.sync.choose_repo_paths",
        lambda inspections: ["/tmp/demo"],
    )
    monkeypatch.setattr(
        "py_local_git_pull.commands.sync.run_sync_flow",
        lambda **_: ((), ()),
    )

    result = runner.invoke(app, ["sync", "/tmp/demo", "--interactive"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/commands/test_sync_command.py -q`
Expected: FAIL with `ImportError` for `choose_repo_paths`

- [ ] **Step 3: Implement the Questionary prompt helper**

Create `py_local_git_pull/ui/prompts.py`:

```python
import questionary

from py_local_git_pull.core.models import RepoInspection


def choose_repo_paths(inspections: tuple[RepoInspection, ...]) -> list[str]:
    choices = [
        questionary.Choice(
            title=f"{inspection.repo_name} [{inspection.risk_level.value}]",
            value=inspection.path,
            checked=not inspection.risk_flags,
        )
        for inspection in inspections
    ]
    return questionary.checkbox(
        "Select repos to sync",
        choices=choices,
    ).ask() or []
```

- [ ] **Step 4: Apply interactive filtering inside the sync command**

Modify `py_local_git_pull/commands/sync.py`:

```python
from py_local_git_pull.ui.prompts import choose_repo_paths


if interactive:
    selected_paths = set(choose_repo_paths(inspections))
    inspections = tuple(item for item in inspections if item.path in selected_paths)

inspections, outcomes = run_sync_flow(
    inspections=inspections,
    branch=branches,
    auto_upstream=auto_upstream,
    skip_non_exist=skip_non_exist,
    no_stash=no_stash,
    depth=depth,
)
```

Place the interactive filter before `run_sync_flow(...)` so only selected repos are executed.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/commands/test_sync_command.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add py_local_git_pull/ui/prompts.py py_local_git_pull/commands/sync.py tests/commands/test_sync_command.py
git commit -m "feat(sync): add questionary-based repo selection"
```

## Task 8: Implement Real-Time `doctor` Diagnosis

**Files:**
- Create: `py_local_git_pull/ui/doctor_view.py`
- Modify: `py_local_git_pull/core/failure_catalog.py`
- Modify: `py_local_git_pull/commands/doctor.py`
- Test: `tests/commands/test_doctor_command.py`
- Test: `tests/ui/test_doctor_view.py`

- [ ] **Step 1: Write the failing doctor tests**

```python
from typer.testing import CliRunner

from py_local_git_pull.commands.app import app


runner = CliRunner()


def test_doctor_command_renders_problem_and_actions(monkeypatch) -> None:
    from py_local_git_pull.core.models import FailureKind, FailureRecord, SuggestedAction

    monkeypatch.setattr(
        "py_local_git_pull.commands.doctor.run_doctor_flow",
        lambda **_: [
            (
                "demo",
                FailureRecord(
                    kind=FailureKind.UPSTREAM_MISSING,
                    summary="current branch has no upstream",
                    detail="main is not tracking origin/main",
                    raw_error=None,
                    can_auto_fix=True,
                    suggested_actions=(
                        SuggestedAction(
                            label="set_upstream",
                            command="git branch --set-upstream-to=origin/main main",
                            description="set upstream for main",
                            auto_fixable=True,
                        ),
                    ),
                ),
            ),
        ],
    )

    result = runner.invoke(app, ["doctor", "/tmp/demo"])
    assert result.exit_code == 0
    assert "PROBLEM" in result.stdout
    assert "DO NOW" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/commands/test_doctor_command.py -q`
Expected: FAIL with `ImportError` for `doctor_view` or `run_doctor_flow`

- [ ] **Step 3: Extend the failure catalog with live inspection diagnosis**

Modify `py_local_git_pull/core/failure_catalog.py`:

```python
from .models import FailureKind, FailureRecord, RepoInspection, RiskFlag, SuggestedAction


def diagnose_inspection(inspection: RepoInspection) -> FailureRecord | None:
    if RiskFlag.NO_UPSTREAM in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.UPSTREAM_MISSING,
            summary="current branch has no upstream",
            detail="At least one local branch is not tracking a remote branch.",
            raw_error=None,
            can_auto_fix=True,
            suggested_actions=(
                SuggestedAction(
                    label="rerun_auto_upstream",
                    command="py-local-git-pull sync <path> --auto-upstream",
                    description="rerun sync and let the tool set upstream automatically",
                    auto_fixable=True,
                ),
            ),
        )

    if RiskFlag.REMOTE_BRANCH_MISSING in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.REMOTE_BRANCH_MISSING,
            summary="remote branch is missing",
            detail="A local branch does not exist on the configured remote.",
            raw_error=None,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="verify_remote_branch",
                    command="git branch -r",
                    description="verify the remote branch list before rerunning sync",
                    auto_fixable=False,
                ),
            ),
        )

    if RiskFlag.HAS_LOCAL_CHANGES in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.DIRTY_WORKTREE,
            summary="local changes need review before sync",
            detail="The repo has local modifications or untracked files.",
            raw_error=None,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="inspect_status",
                    command=f"git -C {inspection.path} status",
                    description="inspect local changes before choosing stash or commit",
                    auto_fixable=False,
                ),
            ),
        )

    return None
```

- [ ] **Step 4: Create the doctor renderer**

Create `py_local_git_pull/ui/doctor_view.py`:

```python
from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import FailureRecord


def render_doctor_result(console: Console, repo_name: str, failure: FailureRecord) -> None:
    lines = [
        f"PROBLEM: {failure.kind.value}",
        f"WHY: {failure.detail or failure.summary}",
        "DO NOW:",
    ]
    lines.extend(
        f"  {index}. {action.description}{f' -> {action.command}' if action.command else ''}"
        for index, action in enumerate(failure.suggested_actions, start=1)
    )
    console.print(Panel("\n".join(lines), title=f"REPO: {repo_name}", border_style="magenta"))
```

- [ ] **Step 5: Add a renderer smoke test**

Create `tests/ui/test_doctor_view.py`:

```python
from rich.console import Console

from py_local_git_pull.core.models import FailureKind, FailureRecord
from py_local_git_pull.ui.doctor_view import render_doctor_result


def test_render_doctor_result_contains_problem_and_why() -> None:
    console = Console(record=True)
    failure = FailureRecord(
        kind=FailureKind.UPSTREAM_MISSING,
        summary="current branch has no upstream",
        detail="main is not tracking origin/main",
        raw_error=None,
        can_auto_fix=True,
        suggested_actions=(),
    )
    render_doctor_result(console, "demo", failure)
    output = console.export_text()
    assert "PROBLEM: upstream_missing" in output
    assert "WHY: main is not tracking origin/main" in output
```

- [ ] **Step 6: Implement the doctor command**

Modify `py_local_git_pull/commands/doctor.py`:

```python
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from py_local_git_pull.core.failure_catalog import diagnose_inspection
from py_local_git_pull.core.repo_inspector import RepoInspector
from py_local_git_pull.ui.doctor_view import render_doctor_result


def run_doctor_flow(*, path: Path, repo: Optional[str], kind: Optional[str]) -> list[tuple[str, object]]:
    inspections = RepoInspector().inspect_path(str(path), recursive=True, max_depth=3)
    results = []
    for inspection in inspections:
        if repo and inspection.repo_name != repo:
            continue
        failure = diagnose_inspection(inspection)
        if failure is None:
            continue
        if kind and failure.kind.value != kind:
            continue
        results.append((inspection.repo_name, failure))
    return results


def doctor_command(
    path: Path,
    repo: Optional[str] = typer.Option(None, "--repo"),
    kind: Optional[str] = typer.Option(None, "--kind"),
) -> None:
    console = Console()
    for repo_name, failure in run_doctor_flow(path=path, repo=repo, kind=kind):
        render_doctor_result(console, repo_name, failure)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run --group dev pytest tests/commands/test_doctor_command.py tests/ui/test_doctor_view.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add py_local_git_pull/core/failure_catalog.py py_local_git_pull/ui/doctor_view.py py_local_git_pull/commands/doctor.py tests/commands/test_doctor_command.py tests/ui/test_doctor_view.py
git commit -m "feat(doctor): add real-time repo diagnosis"
```

## Task 9: Finalize the Breaking Change and Clean Up Legacy Paths

**Files:**
- Modify: `README.md`
- Modify: `py_local_git_pull/ui/__init__.py`
- Modify: `py_local_git_pull/core/__init__.py`
- Create: `tests/commands/test_readme_contract.py`
- Delete: `py_local_git_pull/config/cli_parser.py`
- Delete: `py_local_git_pull/core/result_model.py`
- Delete: `py_local_git_pull/ui/display.py`
- Delete: `py_local_git_pull/ui/progress.py`

- [ ] **Step 1: Write the failing documentation test**

```python
from pathlib import Path


def test_readme_uses_new_subcommands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "py-local-git-pull sync /path/to/repo" in readme
    assert "py-local-git-pull scan /path/to/repos -r" in readme
    assert "py-local-git-pull doctor /path/to/repos" in readme
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --group dev pytest tests/commands/test_readme_contract.py -q`
Expected: FAIL because README still documents the old command model

- [ ] **Step 3: Rewrite the README around the new command model**

Update `README.md` so the first usage section includes:

````markdown
## 使用方法

```bash
py-local-git-pull scan /path/to/repos -r
py-local-git-pull sync /path/to/repos -r -b main -b develop
py-local-git-pull doctor /path/to/repos
```

### 输出风格

- `scan`：预检和风险摘要
- `sync`：任务式输出，包含 PLAN / EXECUTION / SUMMARY / NEXT ACTIONS
- `doctor`：问题解释和下一步建议
````

- [ ] **Step 4: Remove legacy exports and dead modules**

Modify `py_local_git_pull/ui/__init__.py`:

```python
from .dashboard import render_next_actions, render_plan_panel, render_summary_panel, render_sync_header
from .doctor_view import render_doctor_result
from .events import render_repo_events
from .summary import render_scan_summary

__all__ = [
    "render_sync_header",
    "render_plan_panel",
    "render_summary_panel",
    "render_next_actions",
    "render_repo_events",
    "render_scan_summary",
    "render_doctor_result",
]
```

Delete legacy files:

```bash
git rm py_local_git_pull/config/cli_parser.py
git rm py_local_git_pull/core/result_model.py
git rm py_local_git_pull/ui/display.py
git rm py_local_git_pull/ui/progress.py
```

- [ ] **Step 5: Run the full verification suite**

Run:

```bash
uv run --group dev pytest -q
uv run --group dev ruff check .
python3 -m py_local_git_pull --help
python3 -m py_local_git_pull sync --help
python3 -m py_local_git_pull scan --help
python3 -m py_local_git_pull doctor --help
```

Expected:

```text
pytest: PASS
ruff: PASS
all help commands exit 0 and list the new subcommands or options
```

- [ ] **Step 6: Commit**

```bash
git add README.md py_local_git_pull/ui/__init__.py py_local_git_pull/core/__init__.py
git commit -m "refactor: finalize task console breaking redesign"
```

## Spec Coverage Check

### Covered spec requirements

- New command model: Task 1, Task 3, Task 6, Task 7
- Breaking CLI contract: Task 1, Task 8
- New shared models: Task 2
- Failure taxonomy and doctor flow: Task 2, Task 7
- Task-style sync UI: Task 6
- Real-time doctor diagnosis: Task 7
- Dependency strategy (`Typer`, `Questionary`, `Rich`): Task 1, Task 6, Task 7
- Cleanup of old parser/result/UI paths: Task 8
- Tests for commands, core, and UI: Tasks 1 through 8

### Gaps

```text
No spec coverage gaps remain.
```

## Placeholder Scan

Checked for:

- `TBD`
- `TODO`
- "implement later"
- "add appropriate error handling"
- "write tests for the above"

Result:

```text
No placeholders remain in the implementation steps.
```

## Type Consistency Check

Verified the plan uses the same names throughout:

- `RepoInspection`
- `RepoSyncPlan`
- `RepoOutcome`
- `FailureRecord`
- `FailureKind`
- `SuggestedAction`
- `RepoStatus`
- `BranchOutcome`

No later task renames these types.

## Recommended Implementation Order

```text
Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9
```

This order preserves the main rule:

```text
bootstrap the command shell
introduce the new shared semantics
build inspection and planning
adapt execution
then rebuild rendering and diagnosis
then delete the dead paths
```
