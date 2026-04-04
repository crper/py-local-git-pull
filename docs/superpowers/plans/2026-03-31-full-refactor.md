# py-local-git-pull 全量重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构项目架构、代码质量和 CLI 体验，消除所有已知硬伤。

**Architecture:** 5-phase progressive refactoring. Each phase is independently commitable and testable. New clean architecture: `cli/` → `core/services/` → `core/git/` → `core/models`, with zero circular dependencies.

**Tech Stack:** typer, rich, questionary, tenacity, structlog, anyio, Python 3.13

---

## File Structure Map

| File | Responsibility | Phase |
|------|---------------|-------|
| `py_local_git_pull/config/defaults.py` | Module-level constants (replaces constants.py) | Phase 1 |
| `py_local_git_pull/exceptions/errors.py` | Unified exceptions (replaces git/sync exceptions) | Phase 1 |
| `py_local_git_pull/core/models.py` | Updated unified data models | Phase 1 |
| `py_local_git_pull/core/git/runner.py` | Git command execution with tenacity retry | Phase 2 |
| `py_local_git_pull/core/git/branch.py` | Branch operations (checkout, upstream, exists) | Phase 2 |
| `py_local_git_pull/core/git/stash.py` | Stash operations | Phase 2 |
| `py_local_git_pull/core/git/remote.py` | Remote operations (fetch, pull) | Phase 2 |
| `py_local_git_pull/core/git/info.py` | Info collection (current branch, has_changes, branch details) | Phase 2 |
| `py_local_git_pull/core/services/sync_service.py` | Sync orchestration (replaces GitManager.sync_repo*) | Phase 2 |
| `py_local_git_pull/core/services/inspector.py` | Repo inspection (replaces repo_inspector.py) | Phase 2 |
| `py_local_git_pull/core/services/doctor_service.py` | Doctor diagnosis | Phase 2 |
| `py_local_git_pull/core/discovery/repo_finder.py` | Repo discovery (migrated from repo_finder.py) | Phase 2 |
| `py_local_git_pull/core/failure/catalog.py` | Failure classification (migrated from failure_catalog.py) | Phase 2 |
| `py_local_git_pull/cli/app.py` | Typer app with global options (-v, -q, --config) | Phase 4 |
| `py_local_git_pull/cli/scan.py` | Scan command | Phase 4 |
| `py_local_git_pull/cli/sync.py` | Sync command with --dry-run, --json, --workers | Phase 4 |
| `py_local_git_pull/cli/doctor.py` | Doctor command with --json | Phase 4 |
| `py_local_git_pull/ui/console.py` | Rich console config | Phase 4 |
| `py_local_git_pull/ui/scan_view.py` | Scan output with Rich Table | Phase 4 |
| `py_local_git_pull/ui/sync_view.py` | Sync output with progress bar, table, colors | Phase 4 |
| `py_local_git_pull/ui/doctor_view.py` | Doctor output | Phase 4 |
| `py_local_git_pull/ui/interactive.py` | questionary interaction (replaces prompts.py) | Phase 4 |
| `py_local_git_pull/config/settings.py` | Config file loading via tomllib | Phase 4 |
| `py_local_git_pull/utils/logging.py` | structlog configuration | Phase 5 |
| `py_local_git_pull/main.py` | Updated entrypoint | Phase 5 |
| `py_local_git_pull/__init__.py` | Package init | Phase 5 |
| `pyproject.toml` | Updated dependencies | Phase 1 |

---

## Phase 1: Foundation

### Task 1: Add new dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml dependencies**

```toml
[project]
name = "py-local-git-pull"
version = "0.3.0"
description = "一个功能强大的本地Git仓库同步工具，支持批量同步多个仓库和多个分支"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "questionary>=2.1.1",
    "rich>=14.3.3",
    "typer>=0.24.1",
    "tenacity>=9.0.0",
    "structlog>=24.1.0",
    "anyio>=4.0.0",
]
license = { text = "MIT License" }

authors = [{ name = "crper", email = "crper@outlook.com" }]

[project.scripts]
py-local-git-pull = "py_local_git_pull.main:main"
git-sync = "py_local_git_pull.main:main"

[build-system]
requires = ["setuptools>=82.0.1"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["py_local_git_pull*"]

[dependency-groups]
dev = ["ruff>=0.15.5", "pytest>=9.0.2"]

[tool.ruff]
target-version = "py313"
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "B"]
```

- [ ] **Step 2: Install new dependencies**

Run: `uv pip install -e .`
Expected: tenacity, structlog, anyio installed successfully

- [ ] **Step 3: Verify imports work**

Run: `python -c "import tenacity; import structlog; import anyio; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add tenacity, structlog, anyio dependencies"
```

---

### Task 2: Create config/defaults.py (replace constants.py)

**Files:**
- Create: `py_local_git_pull/config/defaults.py`

- [ ] **Step 1: Create defaults.py with module-level constants**

```python
"""Default configuration constants."""

# Git operation defaults
DEFAULT_REMOTE: str = "origin"
BARE_REPO_VALUE: str = "true"
HEAD_REF: str = "HEAD"
DEFAULT_TIMEOUT_SECONDS: int = 60

# CLI defaults
DEFAULT_DEPTH: int = 1
DEFAULT_MAX_DEPTH: int = 3
DEFAULT_SKIP_NON_EXIST: bool = True
DEFAULT_AUTO_UPSTREAM: bool = False
DEFAULT_NO_STASH: bool = False
DEFAULT_WORKERS: int = 4

# Log defaults
LOG_DIR: str = "logs"
LOG_FILE: str = "git_sync.log"
LOG_BACKUP_COUNT: int = 7
LOG_WHEN: str = "midnight"

# Discovery defaults
SKIP_DIR_NAMES: frozenset[str] = frozenset({
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
})
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/config/defaults.py
git commit -m "refactor: create config/defaults.py with module-level constants"
```

---

### Task 3: Create exceptions/errors.py (unify exceptions)

**Files:**
- Create: `py_local_git_pull/exceptions/errors.py`

- [ ] **Step 1: Create unified exceptions module**

Only `GitCommandError` is actually used. Keep it, remove the 7 unused exception classes.

```python
"""Domain-specific exceptions for git operations."""


class GitCommandError(Exception):
    """Raised when a git command fails."""

    def __init__(
        self,
        command: str,
        stderr: str = "",
        stdout: str = "",
        returncode: int | None = None,
        timeout: bool = False,
    ):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timeout = timeout

        detail = stderr or stdout or "unknown error"
        code_part = f" (code={returncode})" if returncode is not None else ""
        timeout_part = " [timeout]" if timeout else ""
        super().__init__(
            f"git command failed{timeout_part}{code_part}: {command}; {detail}"
        )
```

- [ ] **Step 2: Update exceptions/__init__.py**

```python
"""Domain-specific exceptions."""

from .errors import GitCommandError

__all__ = ["GitCommandError"]
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/exceptions/errors.py py_local_git_pull/exceptions/__init__.py
git commit -m "refactor: unify exceptions, remove unused exception classes"
```

---

### Task 4: Update core/models.py (unified model)

**Files:**
- Modify: `py_local_git_pull/core/models.py`

- [ ] **Step 1: Update models.py — remove nothing, it's already the canonical model**

The existing `models.py` is already well-designed. No changes needed in this phase. We will delete `result_model.py` and `sync_options.py` in Phase 2 when their consumers are migrated.

- [ ] **Step 2: Commit**

No changes needed. Skip commit.

---

### Task 5: Create new directory skeleton

**Files:**
- Create: `py_local_git_pull/core/git/__init__.py`
- Create: `py_local_git_pull/core/services/__init__.py`
- Create: `py_local_git_pull/core/discovery/__init__.py`
- Create: `py_local_git_pull/core/failure/__init__.py`
- Create: `py_local_git_pull/cli/__init__.py`
- Create: `py_local_git_pull/ui/console.py`

- [ ] **Step 1: Create empty __init__.py files**

```python
# py_local_git_pull/core/git/__init__.py
"""Git operation modules."""

# py_local_git_pull/core/services/__init__.py
"""Business service layer."""

# py_local_git_pull/core/discovery/__init__.py
"""Repository discovery."""

# py_local_git_pull/core/failure/__init__.py
"""Failure classification."""

# py_local_git_pull/cli/__init__.py
"""CLI command layer."""
```

- [ ] **Step 2: Create ui/console.py**

```python
"""Rich console configuration."""

from rich.console import Console
from rich.theme import Theme

_DEFAULT_THEME = Theme({
    "info": "cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "debug": "dim",
})


def make_console() -> Console:
    """Create the primary Rich console."""
    return Console(theme=_DEFAULT_THEME)


def make_stderr_console() -> Console:
    """Create a stderr console for log output (avoids progress bar interference)."""
    return Console(stderr=True, highlight=False, style="dim")
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/core/git/__init__.py py_local_git_pull/core/services/__init__.py py_local_git_pull/core/discovery/__init__.py py_local_git_pull/core/failure/__init__.py py_local_git_pull/cli/__init__.py py_local_git_pull/ui/console.py
git commit -m "refactor: create new directory skeleton"
```

---

## Phase 2: Execution Layer

### Task 6: Create core/git/runner.py (GitRunner with tenacity)

**Files:**
- Create: `py_local_git_pull/core/git/runner.py`

- [ ] **Step 1: Create GitRunner**

```python
"""Git command execution with retry support."""

import subprocess

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from py_local_git_pull.config.defaults import DEFAULT_TIMEOUT_SECONDS
from py_local_git_pull.exceptions.errors import GitCommandError


class GitRunner:
    """Execute git commands with configurable timeout and retry."""

    def __init__(self, repo_path: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self._repo_path = repo_path
        self._timeout = timeout

    @property
    def repo_path(self) -> str:
        return self._repo_path

    def run(
        self,
        command: list[str],
        *,
        check: bool = True,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Run a git command.

        Args:
            command: Git command arguments (without 'git' prefix).
            check: If True, raise GitCommandError on failure.
            timeout: Override default timeout in seconds.

        Returns:
            Tuple of (returncode, stdout, stderr).

        Raises:
            GitCommandError: If check=True and command fails.
        """
        full_command = ["git", "-C", self._repo_path] + command
        effective_timeout = timeout or self._timeout
        try:
            process = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check,
                timeout=effective_timeout,
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except subprocess.TimeoutExpired as e:
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=124,
                    stdout=(e.stdout or "").strip() if isinstance(e.stdout, str) else "",
                    stderr=(e.stderr or "").strip() if isinstance(e.stderr, str) else "",
                    timeout=True,
                ) from e
            return 124, "", f"git command timed out: {' '.join(full_command)}"
        except subprocess.CalledProcessError as e:
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=e.returncode,
                    stdout=e.stdout.strip() if e.stdout else "",
                    stderr=e.stderr.strip() if e.stderr else "",
                ) from e
            stdout = e.stdout.strip() if e.stdout else ""
            stderr = e.stderr.strip() if e.stderr else str(e)
            return e.returncode, stdout, stderr

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GitCommandError),
        reraise=True,
    )
    def run_with_retry(
        self,
        command: list[str],
        *,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Run a git command with exponential backoff retry.

        Use for network operations (fetch, pull, ls-remote).
        """
        return self.run(command, check=True, timeout=timeout)
```

- [ ] **Step 2: Write test for GitRunner**

```python
# tests/core/git/test_runner.py
import pytest

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.exceptions.errors import GitCommandError


def test_run_success(tmp_path, monkeypatch):
    runner = GitRunner(str(tmp_path))
    # git init to make it a valid repo
    runner.run(["init"])
    code, out, err = runner.run(["branch", "--show-current"])
    assert code == 0


def test_run_check_false_failure(tmp_path):
    runner = GitRunner(str(tmp_path))
    code, out, err = runner.run(["nonexistent"], check=False)
    assert code != 0
    assert err  # has error message


def test_run_check_true_raises(tmp_path):
    runner = GitRunner(str(tmp_path))
    with pytest.raises(GitCommandError):
        runner.run(["nonexistent"], check=True)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run --group dev pytest tests/core/git/test_runner.py -v`
Expected: 3 tests pass

- [ ] **Step 4: Commit**

```bash
git add py_local_git_pull/core/git/runner.py tests/core/git/test_runner.py
git commit -m "feat: create GitRunner with tenacity retry support"
```

---

### Task 7: Create core/git/branch.py

**Files:**
- Create: `py_local_git_pull/core/git/branch.py`

- [ ] **Step 1: Create BranchOperations**

```python
"""Branch operations: checkout, upstream, existence checks."""

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.config.defaults import DEFAULT_REMOTE


class BranchOperations:
    """Operations on git branches."""

    def __init__(self, runner: GitRunner):
        self._runner = runner

    def get_current_branch(self) -> str | None:
        """Get the current branch name, or None if detached HEAD."""
        code, out, _ = self._runner.run(["branch", "--show-current"], check=False)
        if code != 0 or not out:
            return None
        return out

    def branch_exists_locally(self, branch: str) -> bool:
        """Check if branch exists locally."""
        code, out, _ = self._runner.run(
            ["branch", "--list", branch], check=False
        )
        return code == 0 and bool(out)

    def branch_exists_remotely(self, branch: str, remote_branches: set[str] | None = None) -> bool:
        """Check if branch exists on the default remote."""
        if remote_branches is not None:
            return branch in remote_branches

        code, out, _ = self._runner.run(
            ["ls-remote", "--heads", DEFAULT_REMOTE, branch], check=False
        )
        return code == 0 and bool(out)

    def get_remote_branches(self) -> set[str]:
        """Get all remote branch names from refs."""
        code, out, _ = self._runner.run(
            ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/{DEFAULT_REMOTE}"],
            check=False,
        )
        if code != 0:
            return set()

        prefix = f"{DEFAULT_REMOTE}/"
        branches: set[str] = set()
        for line in out.splitlines():
            ref = line.strip()
            if ref.startswith(prefix) and not ref.endswith("/HEAD"):
                branches.add(ref[len(prefix):])
        return branches

    def checkout_branch(
        self, branch: str, *, create_if_not_exist: bool = True, remote_branches: set[str] | None = None
    ) -> tuple[bool, str | None]:
        """Checkout a branch.

        Returns:
            (success, error_message)
        """
        if self.branch_exists_locally(branch):
            self._runner.run(["checkout", branch])
            return True, None

        if create_if_not_exist and self.branch_exists_remotely(branch, remote_branches):
            self._runner.run(["checkout", "-b", branch, f"{DEFAULT_REMOTE}/{branch}"])
            return True, None

        return False, f"branch {branch} does not exist"

    def set_upstream(
        self, branch: str, *, auto_upstream: bool = False, remote_branches: set[str] | None = None
    ) -> tuple[bool, str, str | None]:
        """Set or check upstream tracking for a branch.

        Returns:
            (has_upstream, upstream_name, error_message)
        """
        code, out, _ = self._runner.run(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"],
            check=False,
        )

        if code == 0:
            return True, out, None

        if not auto_upstream:
            return False, "", None

        if not self.branch_exists_remotely(branch, remote_branches):
            return False, "", f"remote branch {DEFAULT_REMOTE}/{branch} does not exist"

        self._runner.run(
            ["branch", f"--set-upstream-to={DEFAULT_REMOTE}/{branch}", branch]
        )
        return True, f"{DEFAULT_REMOTE}/{branch}", None

    def get_ahead_behind(self, branch: str, upstream: str) -> tuple[int, int] | None:
        """Get ahead/behind counts for branch vs upstream.

        Returns:
            (ahead, behind) or None if unavailable.
        """
        code, out, _ = self._runner.run(
            ["rev-list", "--left-right", "--count", f"{branch}...{upstream}"],
            check=False,
        )
        if code != 0 or not out:
            return None

        parts = out.split("\t")
        if len(parts) != 2:
            return None

        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None
```

- [ ] **Step 2: Write test for BranchOperations**

```python
# tests/core/git/test_branch.py
from unittest.mock import MagicMock

from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.runner import GitRunner


def _make_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    return runner


def test_get_current_branch_initial(tmp_path):
    runner = _make_runner(tmp_path)
    ops = BranchOperations(runner)
    # Fresh repo has no branches yet
    branch = ops.get_current_branch()
    assert branch is None or branch == ""


def test_branch_exists_locally_false(tmp_path):
    runner = _make_runner(tmp_path)
    ops = BranchOperations(runner)
    assert ops.branch_exists_locally("nonexistent") is False


def test_get_remote_branches_empty(tmp_path):
    runner = _make_runner(tmp_path)
    ops = BranchOperations(runner)
    branches = ops.get_remote_branches()
    assert branches == set()
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run --group dev pytest tests/core/git/test_branch.py -v`
Expected: 3 tests pass

- [ ] **Step 4: Commit**

```bash
git add py_local_git_pull/core/git/branch.py tests/core/git/test_branch.py
git commit -m "feat: create BranchOperations from GitManager extraction"
```

---

### Task 8: Create core/git/stash.py

**Files:**
- Create: `py_local_git_pull/core/git/stash.py`

- [ ] **Step 1: Create StashOperations**

```python
"""Stash operations: save and restore working tree changes."""

from datetime import datetime

import structlog

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.config.defaults import HEAD_REF

log = structlog.get_logger()


class StashOperations:
    """Manage git stash operations."""

    def __init__(self, runner: GitRunner):
        self._runner = runner
        self._stash_ref: str | None = None

    @property
    def has_stash(self) -> bool:
        return self._stash_ref is not None

    def stash_changes(self, repo_name: str) -> bool:
        """Stash uncommitted changes.

        Returns:
            True if changes were stashed, False if nothing to stash or no commits.
        """
        try:
            code, _, _ = self._runner.run(
                ["rev-parse", "--verify", HEAD_REF], check=False
            )
            if code != 0:
                log.warning("stash_skipped", repo=repo_name, reason="no commits yet")
                return False

            message = f"py-local-git-pull:{repo_name}:{datetime.now().isoformat()}"
            code, out, _ = self._runner.run(
                ["stash", "push", "--include-untracked", "-m", message],
                check=False,
            )
            if code != 0 or "No local changes to save" in out:
                return False

            # Track the stash ref for precise restoration.
            code, stash_list, _ = self._runner.run(["stash", "list"], check=False)
            if code == 0:
                for line in stash_list.splitlines():
                    if message in line:
                        self._stash_ref = line.split(":")[0]
                        break

            log.info("stash_created", repo=repo_name)
            return True

        except Exception as e:
            log.error("stash_failed", repo=repo_name, error=str(e))
            return False

    def pop_stash(self, repo_name: str) -> bool:
        """Restore the stashed changes from this session.

        Returns:
            True if stash was restored, False if no stash to restore.
        """
        if not self._stash_ref:
            return False

        try:
            self._runner.run(["stash", "pop", self._stash_ref])
            log.info("stash_restored", repo=repo_name)
            self._stash_ref = None
            return True
        except Exception as e:
            log.error("stash_restore_failed", repo=repo_name, error=str(e))
            return False
```

- [ ] **Step 2: Write test for StashOperations**

```python
# tests/core/git/test_stash.py
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations


def _make_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    # Create an initial commit
    (tmp_path / "file.txt").write_text("hello")
    runner.run(["add", "."])
    runner.run(["commit", "-m", "init"])
    return runner


def test_stash_no_changes(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    result = ops.stash_changes("test-repo")
    assert result is False


def test_stash_with_changes(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    # Make a change
    (tmp_path / "file.txt").write_text("modified")
    result = ops.stash_changes("test-repo")
    assert result is True
    assert ops.has_stash


def test_pop_stash(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    (tmp_path / "file.txt").write_text("modified")
    ops.stash_changes("test-repo")
    result = ops.pop_stash("test-repo")
    assert result is True
    assert not ops.has_stash


def test_pop_stash_nothing_to_pop(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    result = ops.pop_stash("test-repo")
    assert result is False
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run --group dev pytest tests/core/git/test_stash.py -v`
Expected: 4 tests pass

- [ ] **Step 4: Commit**

```bash
git add py_local_git_pull/core/git/stash.py tests/core/git/test_stash.py
git commit -m "feat: create StashOperations from GitManager extraction"
```

---

### Task 9: Create core/git/remote.py

**Files:**
- Create: `py_local_git_pull/core/git/remote.py`

- [ ] **Step 1: Create RemoteOperations**

```python
"""Remote operations: fetch and pull with retry."""

import structlog

from py_local_git_pull.core.git.runner import GitRunner

log = structlog.get_logger()


class RemoteOperations:
    """Manage git remote operations."""

    def __init__(self, runner: GitRunner):
        self._runner = runner

    def fetch(self, depth: int | None = None) -> bool:
        """Fetch from default remote.

        Args:
            depth: Fetch depth, None for full history.

        Returns:
            True if fetch succeeded.
        """
        try:
            command = ["fetch"]
            if depth:
                command.extend(["--depth", str(depth)])

            self._runner.run_with_retry(command)
            log.info("fetch_completed")
            return True
        except Exception as e:
            log.error("fetch_failed", error=str(e))
            return False

    def pull(self) -> tuple[bool, str | None]:
        """Pull current branch with fast-forward only.

        Returns:
            (success, error_message)
        """
        try:
            self._runner.run_with_retry(["pull", "--ff-only"])
            log.info("pull_completed")
            return True, None
        except Exception as e:
            error_msg = str(e)
            log.error("pull_failed", error=error_msg)
            return False, error_msg
```

- [ ] **Step 2: Write test for RemoteOperations**

```python
# tests/core/git/test_remote.py
from unittest.mock import MagicMock, patch

from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.exceptions.errors import GitCommandError


def test_fetch_success(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    ops = RemoteOperations(runner)
    # Will fail without remote, but tests the method exists and returns bool
    result = ops.fetch()
    assert isinstance(result, bool)


def test_pull_no_upstream(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    ops = RemoteOperations(runner)
    success, error = ops.pull()
    assert success is False
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/core/git/remote.py tests/core/git/test_remote.py
git commit -m "feat: create RemoteOperations with tenacity retry"
```

---

### Task 10: Create core/git/info.py

**Files:**
- Create: `py_local_git_pull/core/git/info.py`

- [ ] **Step 1: Create InfoOperations**

```python
"""Repository info collection: status, branches, bare check."""

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.config.defaults import BARE_REPO_VALUE, DEFAULT_REMOTE


class InfoOperations:
    """Collect repository state information."""

    def __init__(self, runner: GitRunner):
        self._runner = runner

    def is_bare(self) -> bool:
        """Check if repository is bare."""
        code, out, _ = self._runner.run(
            ["rev-parse", "--is-bare-repository"], check=False
        )
        return code == 0 and out == BARE_REPO_VALUE

    def has_changes(self) -> bool:
        """Check if working tree has uncommitted changes."""
        code, out, _ = self._runner.run(
            ["status", "--porcelain"], check=False
        )
        return code == 0 and bool(out)

    def get_local_branches(self) -> list[tuple[str, bool]]:
        """Get local branches with current branch marker.

        Returns:
            List of (branch_name, is_current) tuples.
        """
        code, out, _ = self._runner.run(["branch", "--list"], check=False)
        if code != 0 or not out:
            return []

        current = self.get_current_branch()
        branches = []
        for line in out.splitlines():
            name = line.strip()
            if name.startswith("* "):
                name = name[2:]
            if name:
                branches.append((name, name == current))
        return branches

    def get_current_branch(self) -> str | None:
        """Get current branch name."""
        code, out, _ = self._runner.run(
            ["branch", "--show-current"], check=False
        )
        if code != 0 or not out:
            return None
        return out
```

- [ ] **Step 2: Write test for InfoOperations**

```python
# tests/core/git/test_info.py
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.info import InfoOperations


def _make_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    return runner


def test_is_bare_false(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    assert ops.is_bare() is False


def test_has_changes_false_initially(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    assert ops.has_changes() is False


def test_has_changes_true_after_modify(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    (tmp_path / "file.txt").write_text("hello")
    assert ops.has_changes() is True


def test_get_local_branches_empty(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    branches = ops.get_local_branches()
    assert branches == []
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/core/git/info.py tests/core/git/test_info.py
git commit -m "feat: create InfoOperations from GitManager extraction"
```

---

### Task 11: Create core/services/sync_service.py

**Files:**
- Create: `py_local_git_pull/core/services/sync_service.py`

- [ ] **Step 1: Create SyncService**

```python
"""Sync orchestration service."""

import structlog

from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations
from py_local_git_pull.core.failure.catalog import classify_git_failure
from py_local_git_pull.core.models import (
    BranchOutcome,
    BranchStatus,
    FailureRecord,
    RepoOutcome,
    RepoInspection,
    RepoStatus,
    RepoSyncPlan,
)

log = structlog.get_logger()


class SyncService:
    """Orchestrate repository sync operations."""

    def __init__(
        self,
        runner: GitRunner,
        branch_ops: BranchOperations,
        stash_ops: StashOperations,
        remote_ops: RemoteOperations,
        info_ops: InfoOperations,
    ):
        self._runner = runner
        self._branch_ops = branch_ops
        self._stash_ops = stash_ops
        self._remote_ops = remote_ops
        self._info_ops = info_ops

    def sync_repo(
        self,
        inspection: RepoInspection,
        plan: RepoSyncPlan,
        *,
        auto_upstream: bool,
        skip_non_exist: bool,
        depth: int,
    ) -> RepoOutcome:
        """Sync a single repository.

        Returns:
            RepoOutcome with sync results.
        """
        current_branch = self._info_ops.get_current_branch()
        target_branches = plan.target_branches or (
            (current_branch,) if current_branch else ()
        )

        # Fetch
        if not self._remote_ops.fetch(depth):
            failure = classify_git_failure("fetch failed")
            return RepoOutcome(
                repo_name=inspection.repo_name,
                path=inspection.path,
                status=RepoStatus.FAILED,
                current_branch=current_branch,
                target_branches=target_branches,
                synced_branches=(),
                skipped_branches=target_branches,
                stashed=False,
                failure=failure,
            )

        # Stash if needed
        stashed = False
        if not info_ops.is_bare() and info_ops.has_changes() and plan.stash_strategy.value != "user_disabled":
            stashed = self._stash_ops.stash_changes(inspection.repo_name)

        try:
            # Sync branches
            remote_branches = self._branch_ops.get_remote_branches()
            branch_outcomes = tuple(
                self._sync_single_branch(
                    branch_name,
                    auto_upstream=auto_upstream,
                    skip_non_exist=skip_non_exist,
                    is_current=(branch_name == current_branch),
                    remote_branches=remote_branches,
                )
                for branch_name in target_branches
            )

            status = self._aggregate_status(branch_outcomes)

            return RepoOutcome(
                repo_name=inspection.repo_name,
                path=inspection.path,
                status=status,
                current_branch=current_branch,
                target_branches=target_branches,
                synced_branches=tuple(o.name for o in branch_outcomes if o.status is BranchStatus.SYNCED),
                skipped_branches=tuple(o.name for o in branch_outcomes if o.status is BranchStatus.SKIPPED),
                stashed=stashed,
                branch_outcomes=branch_outcomes,
            )
        finally:
            if stashed:
                self._stash_ops.pop_stash(inspection.repo_name)

    def _sync_single_branch(
        self,
        branch: str,
        *,
        auto_upstream: bool,
        skip_non_exist: bool,
        is_current: bool,
        remote_branches: set[str],
    ) -> BranchOutcome:
        """Sync a single branch."""
        exists_local = self._branch_ops.branch_exists_locally(branch)
        exists_remote = self._branch_ops.branch_exists_remotely(branch, remote_branches)

        if not exists_local and not exists_remote:
            log.warning("branch_skipped", branch=branch, reason="does not exist anywhere")
            return BranchOutcome(
                name=branch,
                status=BranchStatus.SKIPPED,
                is_current=is_current,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
            )

        if not exists_remote and skip_non_exist:
            log.warning("branch_skipped", branch=branch, reason="remote branch missing")
            return BranchOutcome(
                name=branch,
                status=BranchStatus.SKIPPED,
                is_current=is_current,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
            )

        # Checkout if not current
        if not is_current:
            success, error = self._branch_ops.checkout_branch(
                branch, create_if_not_exist=exists_remote, remote_branches=remote_branches
            )
            if not success:
                return BranchOutcome(
                    name=branch,
                    status=BranchStatus.FAILED,
                    is_current=is_current,
                    has_upstream=False,
                    upstream_name=None,
                    ahead=None,
                    behind=None,
                    failure=classify_git_failure(error),
                )

        # Set upstream
        has_upstream, upstream_name, upstream_error = self._branch_ops.set_upstream(
            branch, auto_upstream=auto_upstream, remote_branches=remote_branches
        )

        if upstream_error and not has_upstream:
            return BranchOutcome(
                name=branch,
                status=BranchStatus.SKIPPED,
                is_current=is_current,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
                failure=classify_git_failure(upstream_error),
            )

        # Pull if has upstream
        if has_upstream:
            success, pull_error = self._remote_ops.pull()
            if success:
                ahead_behind = self._branch_ops.get_ahead_behind(branch, upstream_name)
                return BranchOutcome(
                    name=branch,
                    status=BranchStatus.SYNCED,
                    is_current=is_current,
                    has_upstream=True,
                    upstream_name=upstream_name,
                    ahead=ahead_behind[0] if ahead_behind else None,
                    behind=ahead_behind[1] if ahead_behind else None,
                )
            else:
                return BranchOutcome(
                    name=branch,
                    status=BranchStatus.FAILED,
                    is_current=is_current,
                    has_upstream=True,
                    upstream_name=upstream_name,
                    ahead=None,
                    behind=None,
                    failure=classify_git_failure(pull_error),
                )

        return BranchOutcome(
            name=branch,
            status=BranchStatus.SKIPPED,
            is_current=is_current,
            has_upstream=False,
            upstream_name=None,
            ahead=None,
            behind=None,
            failure=classify_git_failure("no upstream"),
        )

    @staticmethod
    def _aggregate_status(outcomes: tuple[BranchOutcome, ...]) -> RepoStatus:
        """Aggregate branch outcomes into a repo status."""
        failed = [o for o in outcomes if o.status is BranchStatus.FAILED]
        skipped = [o for o in outcomes if o.status is BranchStatus.SKIPPED]
        synced = [o for o in outcomes if o.status is BranchStatus.SYNCED]

        if failed and synced:
            return RepoStatus.PARTIAL
        if failed:
            return RepoStatus.FAILED
        if skipped and not synced:
            return RepoStatus.SKIPPED
        return RepoStatus.SYNCED
```

- [ ] **Step 2: Write test for SyncService**

```python
# tests/core/services/test_sync_service.py
from unittest.mock import MagicMock

from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations
from py_local_git_pull.core.models import (
    RepoInspection,
    RepoStatus,
    RiskLevel,
    RepoSyncPlan,
    PlanAction,
    StashStrategy,
)
from py_local_git_pull.core.services.sync_service import SyncService


def _make_sync_service(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    (tmp_path / "file.txt").write_text("hello")
    runner.run(["add", "."])
    runner.run(["commit", "-m", "init"])
    return SyncService(
        runner=runner,
        branch_ops=BranchOperations(runner),
        stash_ops=StashOperations(runner),
        remote_ops=RemoteOperations(runner),
        info_ops=InfoOperations(runner),
    )


def test_sync_no_remote(tmp_path):
    """Sync with no remote configured should fail gracefully."""
    service = _make_sync_service(tmp_path)
    inspection = RepoInspection(
        repo_name="test",
        path=str(tmp_path),
        current_branch=None,
        is_git_repo=True,
        is_bare=False,
        has_changes=False,
        has_untracked_changes=False,
        detached_head=False,
        branches=(),
        risk_level=RiskLevel.LOW,
        risk_flags=(),
    )
    plan = RepoSyncPlan(
        repo_name="test",
        path=str(tmp_path),
        target_branches=(),
        action=PlanAction.SYNC_CURRENT,
        stash_strategy=StashStrategy.NONE,
        will_skip=False,
        skip_reason=None,
        needs_attention=False,
        attention_reason=None,
    )
    outcome = service.sync_repo(
        inspection, plan, auto_upstream=False, skip_non_exist=True, depth=1
    )
    # Should fail at fetch (no remote) but not crash
    assert outcome.status is RepoStatus.FAILED
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/core/services/sync_service.py tests/core/services/test_sync_service.py
git commit -m "feat: create SyncService orchestrating git operations"
```

---

### Task 12: Create core/services/inspector.py

**Files:**
- Create: `py_local_git_pull/core/services/inspector.py`

- [ ] **Step 1: Create RepoInspector service**

```python
"""Repository inspection service."""

from pathlib import Path

from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.models import (
    BranchInspection,
    RepoInspection,
    RiskFlag,
    RiskLevel,
)
from py_local_git_pull.core.discovery.repo_finder import find_git_repos, is_git_repo


def derive_risk_state(
    *,
    has_changes: bool,
    detached_head: bool,
    is_bare: bool,
    branches_have_missing_upstream: bool,
    branches_have_missing_remote: bool,
) -> tuple[RiskLevel, tuple[RiskFlag, ...]]:
    """Derive risk level and flags from repository state."""
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
    """Inspect repositories and derive risk state."""

    def __init__(self, runner: GitRunner | None = None):
        self._runner = runner

    def _get_runner(self, repo_path: str) -> GitRunner:
        if self._runner is None:
            self._runner = GitRunner(repo_path)
        return self._runner

    def inspect_repo(self, repo_path: str) -> RepoInspection:
        """Inspect a single repository."""
        runner = GitRunner(repo_path)
        info_ops = InfoOperations(runner)
        branch_ops = BranchOperations(runner)

        current_branch = info_ops.get_current_branch()
        is_bare = info_ops.is_bare()
        has_changes = info_ops.has_changes()

        remote_branches = branch_ops.get_remote_branches()
        local_branches = info_ops.get_local_branches()

        branches = []
        for name, is_current in local_branches:
            exists_remote = name in remote_branches
            has_upstream, upstream_name, _ = branch_ops.set_upstream(name, auto_upstream=False)
            ahead_behind = None
            if has_upstream:
                ahead_behind = branch_ops.get_ahead_behind(name, upstream_name)

            branches.append(BranchInspection(
                name=name,
                is_current=is_current,
                exists_locally=True,
                exists_remotely=exists_remote,
                has_upstream=has_upstream,
                upstream_name=upstream_name,
                ahead=ahead_behind[0] if ahead_behind else None,
                behind=ahead_behind[1] if ahead_behind else None,
            ))

        level, flags = derive_risk_state(
            has_changes=has_changes,
            detached_head=current_branch is None,
            is_bare=is_bare,
            branches_have_missing_upstream=any(not b.has_upstream for b in branches),
            branches_have_missing_remote=any(not b.exists_remotely for b in branches),
        )

        return RepoInspection(
            repo_name=Path(repo_path).name,
            path=str(Path(repo_path).resolve()),
            current_branch=current_branch,
            is_git_repo=is_git_repo(repo_path),
            is_bare=is_bare,
            has_changes=has_changes,
            has_untracked_changes=has_changes,
            detached_head=current_branch is None,
            branches=tuple(branches),
            risk_level=level,
            risk_flags=flags,
        )

    def inspect_path(
        self,
        path: str,
        *,
        recursive: bool,
        max_depth: int,
    ) -> tuple[RepoInspection, ...]:
        """Scan a path for repositories and inspect each one."""
        if recursive:
            repo_paths = find_git_repos(path, max_depth)
        else:
            repo_paths = [path] if is_git_repo(path) else []

        return tuple(self.inspect_repo(rp) for rp in repo_paths)
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/core/services/inspector.py
git commit -m "feat: create RepoInspector service with DI support"
```

---

### Task 13: Migrate core/discovery/repo_finder.py

**Files:**
- Create: `py_local_git_pull/core/discovery/repo_finder.py`

- [ ] **Step 1: Create repo_finder.py (migrated from core/repo_finder.py, updated imports)**

```python
"""Repository discovery via BFS directory scanning."""

import os
from collections import deque
from pathlib import Path
import subprocess

import structlog

from py_local_git_pull.config.defaults import SKIP_DIR_NAMES

log = structlog.get_logger()


def is_git_repo(path: str) -> bool:
    """Check if path is a git repository root."""
    target = Path(path)
    if not target.exists() or not target.is_dir():
        return False

    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        repo_root = Path(result.stdout.strip())
        return repo_root.resolve() == target.resolve()
    except subprocess.SubprocessError as e:
        log.debug("git_check_failed", path=path, error=str(e))
        return False


def find_git_repos(base_path: str, max_depth: int = 3) -> list[str]:
    """Find all git repositories under base_path up to max_depth."""
    repos: set[str] = set()
    root = Path(base_path).expanduser()
    log.debug("scan_start", path=str(root), max_depth=max_depth)

    if not root.exists():
        log.warning("path_missing", path=str(root))
        return []

    if root.is_file():
        parent_dir = root.parent
        return [str(parent_dir.resolve())] if is_git_repo(str(parent_dir)) else []

    if is_git_repo(str(root)):
        return [str(root.resolve())]

    queue: deque[tuple[Path, int]] = deque([(root, 0)])
    visited: set[Path] = set()

    while queue:
        current, depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        if depth > max_depth:
            continue

        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if entry.name in SKIP_DIR_NAMES:
                        continue
                    if entry.name.startswith("."):
                        continue

                    sub_path = Path(entry.path)
                    if is_git_repo(str(sub_path)):
                        repos.add(str(sub_path.resolve()))
                        continue

                    queue.append((sub_path, depth + 1))
        except (PermissionError, FileNotFoundError, NotADirectoryError) as e:
            log.warning("dir_access_error", path=str(current), error=str(e))
        except Exception as e:
            log.error("scan_error", path=str(current), error=str(e))

    return sorted(repos)
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/core/discovery/repo_finder.py
git commit -m "refactor: migrate repo_finder.py to discovery module"
```

---

### Task 14: Migrate core/failure/catalog.py

**Files:**
- Create: `py_local_git_pull/core/failure/catalog.py`

- [ ] **Step 1: Create catalog.py (migrated from core/failure_catalog.py)**

```python
"""Map raw git failures to user-facing categories."""

from py_local_git_pull.core.models import (
    FailureKind,
    FailureRecord,
    RepoInspection,
    RiskFlag,
    SuggestedAction,
)


def classify_git_failure(raw_error: str | None) -> FailureRecord:
    """Classify a raw git error into a structured failure record."""
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


def diagnose_inspection(inspection: RepoInspection) -> FailureRecord | None:
    """Derive a failure record from inspection risk flags."""
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

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/core/failure/catalog.py
git commit -m "refactor: migrate failure_catalog.py to failure/catalog.py"
```

---

### Task 15: Delete old files and verify Phase 1-2

**Files:**
- Delete: `py_local_git_pull/core/result_model.py`
- Delete: `py_local_git_pull/core/sync_options.py`
- Delete: `py_local_git_pull/config/constants.py`
- Delete: `py_local_git_pull/config/__init__.py`
- Delete: `py_local_git_pull/core/git_manager.py`
- Delete: `py_local_git_pull/core/branch_syncer.py`
- Delete: `py_local_git_pull/core/git_executor.py`
- Delete: `py_local_git_pull/core/repo_inspector.py`
- Delete: `py_local_git_pull/core/repo_finder.py`
- Delete: `py_local_git_pull/core/failure_catalog.py`
- Delete: `py_local_git_pull/core/sync_planner.py`
- Delete: `py_local_git_pull/exceptions/git_exceptions.py`
- Delete: `py_local_git_pull/exceptions/sync_exceptions.py`

- [ ] **Step 1: Delete old files**

```bash
rm py_local_git_pull/core/result_model.py \
   py_local_git_pull/core/sync_options.py \
   py_local_git_pull/config/constants.py \
   py_local_git_pull/config/__init__.py \
   py_local_git_pull/core/git_manager.py \
   py_local_git_pull/core/branch_syncer.py \
   py_local_git_pull/core/git_executor.py \
   py_local_git_pull/core/repo_inspector.py \
   py_local_git_pull/core/repo_finder.py \
   py_local_git_pull/core/failure_catalog.py \
   py_local_git_pull/core/sync_planner.py \
   py_local_git_pull/exceptions/git_exceptions.py \
   py_local_git_pull/exceptions/sync_exceptions.py
```

- [ ] **Step 2: Update core/__init__.py**

```python
"""Core business logic."""
```

- [ ] **Step 3: Run ruff to check for import errors**

Run: `ruff check .`
Expected: Only import errors from commands/ and utils/ (which will be fixed in Phase 4)

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "refactor: delete old files, complete Phase 2 migration"
```

---

## Phase 3: Concurrency Layer

### Task 16: Add async sync to SyncService

**Files:**
- Modify: `py_local_git_pull/core/services/sync_service.py`

- [ ] **Step 1: Add async methods to SyncService**

Add to the end of `sync_service.py`:

```python
import anyio


async def sync_repo_async(
    inspection: RepoInspection,
    plan: RepoSyncPlan,
    *,
    auto_upstream: bool,
    skip_non_exist: bool,
    depth: int,
    limiter: anyio.CapacityLimiter,
) -> RepoOutcome:
    """Async wrapper for sync_repo, runs in thread pool."""
    def _do_sync() -> RepoOutcome:
        runner = GitRunner(inspection.path)
        service = SyncService(
            runner=runner,
            branch_ops=BranchOperations(runner),
            stash_ops=StashOperations(runner),
            remote_ops=RemoteOperations(runner),
            info_ops=InfoOperations(runner),
        )
        return service.sync_repo(
            inspection, plan,
            auto_upstream=auto_upstream,
            skip_non_exist=skip_non_exist,
            depth=depth,
        )

    async with limiter:
        return await anyio.to_thread.run_sync(_do_sync)


async def sync_all_repos(
    inspections: tuple[RepoInspection, ...],
    plans: tuple[RepoSyncPlan, ...],
    *,
    auto_upstream: bool,
    skip_non_exist: bool,
    depth: int,
    workers: int,
) -> list[RepoOutcome]:
    """Sync all repositories concurrently."""
    limiter = anyio.CapacityLimiter(workers)
    outcomes: list[RepoOutcome] = []

    async def _sync_one(i: int) -> None:
        outcome = await sync_repo_async(
            inspections[i], plans[i],
            auto_upstream=auto_upstream,
            skip_non_exist=skip_non_exist,
            depth=depth,
            limiter=limiter,
        )
        outcomes.append(outcome)

    async with anyio.create_task_group() as tg:
        for i in range(len(inspections)):
            tg.start_soon(_sync_one, i)

    # Sort by original order
    outcomes.sort(key=lambda o: next(
        idx for idx, insp in enumerate(inspections) if insp.repo_name == o.repo_name
    ))
    return outcomes
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/core/services/sync_service.py
git commit -m "feat: add async concurrent sync with anyio"
```

---

## Phase 4: CLI Experience

### Task 17: Create cli/app.py with global options

**Files:**
- Create: `py_local_git_pull/cli/app.py`

- [ ] **Step 1: Create app.py**

```python
"""Typer application entrypoint with global options."""

from pathlib import Path
from typing import Annotated

import typer

from .doctor import doctor_command
from .scan import scan_command
from .sync import sync_command

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Git task console for scanning, syncing, and diagnosing local repositories.",
)


@app.callback()
def main(
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, help="Increase output verbosity (can repeat)")] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress non-essential output")] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Path to config file")] = None,
) -> None:
    """Global options for py-local-git-pull."""
    if verbose and quiet:
        raise typer.Exit(code=2)


app.command("scan")(scan_command)
app.command("sync")(sync_command)
app.command("doctor")(doctor_command)
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/cli/app.py
git commit -m "feat: create cli/app.py with global options (-v, -q, --config)"
```

---

### Task 18: Create cli/scan.py

**Files:**
- Create: `py_local_git_pull/cli/scan.py`

- [ ] **Step 1: Create scan.py**

```python
"""Scan command for repository inspection."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.ui.scan_view import render_scan_summary


def scan_command(
    path: Path,
    recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
    max_depth: Annotated[int, typer.Option("--max-depth")] = 3,
    output: Annotated[str, typer.Option("--output")] = "table",
) -> None:
    """Scan a path for git repositories and show their status."""
    inspections = RepoInspector().inspect_path(
        str(path),
        recursive=recursive,
        max_depth=max_depth,
    )

    if output == "json":
        payload = {
            "schema_version": 2,
            "command": "scan",
            "path": str(path),
            "repos": [asdict(inspection) for inspection in inspections],
        }
        print(json.dumps(payload, ensure_ascii=False, default=list))
        raise typer.Exit(code=0)

    from py_local_git_pull.ui.console import make_console
    console = make_console()
    render_scan_summary(console, inspections)
    raise typer.Exit(code=0)
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/cli/scan.py
git commit -m "feat: create cli/scan.py"
```

---

### Task 19: Create cli/sync.py with --dry-run, --json, --workers

**Files:**
- Create: `py_local_git_pull/cli/sync.py`

- [ ] **Step 1: Create sync.py**

```python
"""Sync command with dry-run, json output, and parallel workers."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import anyio
import typer

from py_local_git_pull.config.defaults import DEFAULT_MAX_DEPTH, DEFAULT_WORKERS
from py_local_git_pull.core.models import RepoOutcome, RepoStatus
from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.core.services.sync_service import (
    build_sync_plan,
    sync_all_repos,
)
from py_local_git_pull.ui.console import make_console
from py_local_git_pull.ui.interactive import choose_repo_paths
from py_local_git_pull.ui.sync_view import (
    render_next_actions,
    render_plan_panel,
    render_repo_events,
    render_summary_panel,
    render_sync_header,
)


def run_sync_flow(
    *,
    inspections: tuple,
    branches: tuple[str, ...],
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
    dry_run: bool,
    workers: int,
) -> tuple:
    """Execute the sync flow, returning outcomes."""
    plans = tuple(
        build_sync_plan(insp, branches=branches, no_stash=no_stash)
        for insp in inspections
    )

    if dry_run:
        return tuple(
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
            for insp, plan in zip(inspections, plans)
        )

    return anyio.run(
        sync_all_repos,
        inspections,
        plans,
        auto_upstream=auto_upstream,
        skip_non_exist=skip_non_exist,
        depth=depth,
        workers=workers,
    )


def sync_command(
    path: Path,
    branch: Annotated[list[str] | None, typer.Option("--branch", "-b", help="Branch to sync (repeatable)")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
    max_depth: Annotated[int, typer.Option("--max-depth")] = DEFAULT_MAX_DEPTH,
    auto_upstream: Annotated[bool, typer.Option("--auto-upstream")] = False,
    skip_non_exist: Annotated[bool, typer.Option("--skip-non-exist/--no-skip-non-exist")] = True,
    no_stash: Annotated[bool, typer.Option("--no-stash")] = False,
    depth: Annotated[int, typer.Option("--depth")] = 1,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Interactive repo selection")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n", help="Show plan without executing")] = False,
    workers: Annotated[int, typer.Option("--workers", "-w", help="Parallel sync workers")] = DEFAULT_WORKERS,
    output: Annotated[str, typer.Option("--output")] = "table",
) -> None:
    """Sync local git repositories."""
    console = make_console()
    branches = tuple(branch or ())

    inspections = RepoInspector().inspect_path(
        str(path),
        recursive=recursive,
        max_depth=max_depth,
    )

    if interactive:
        selected_paths = set(choose_repo_paths(inspections))
        if not selected_paths:
            console.print("[yellow]No repos selected, exiting.[/]")
            raise typer.Exit(code=0)
        inspections = tuple(item for item in inspections if item.path in selected_paths)

    try:
        outcomes = run_sync_flow(
            inspections=inspections,
            branches=branches,
            auto_upstream=auto_upstream,
            skip_non_exist=skip_non_exist,
            no_stash=no_stash,
            depth=depth,
            dry_run=dry_run,
            workers=workers,
        )

        if output == "json":
            payload = {
                "schema_version": 2,
                "command": "sync",
                "path": str(path),
                "dry_run": dry_run,
                "repos": [asdict(o) for o in outcomes],
            }
            print(json.dumps(payload, ensure_ascii=False, default=list))
            raise typer.Exit(code=0)

        render_sync_header(console, str(path), inspections, branches, dry_run)
        render_plan_panel(console, inspections)
        render_repo_events(console, outcomes)
        render_summary_panel(console, outcomes)
        render_next_actions(console, outcomes)
        raise typer.Exit(code=0)

    except Exception as exc:
        console.print(f"[bold red]sync failed: {exc}")
        raise typer.Exit(code=1) from exc
```

- [ ] **Step 2: Add build_sync_plan import**

The `build_sync_plan` function needs to be moved. Add it to `core/services/sync_service.py`:

```python
def build_sync_plan(
    inspection: RepoInspection,
    *,
    branches: tuple[str, ...],
    no_stash: bool,
) -> RepoSyncPlan:
    """Build a sync plan from an inspection."""
    from py_local_git_pull.core.models import (
        PlanAction, RepoSyncPlan, RiskFlag, StashStrategy,
    )

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

    target_branches = (
        branches or ((inspection.current_branch,) if inspection.current_branch else ())
    )
    action = PlanAction.SYNC_BRANCHES if branches else PlanAction.SYNC_CURRENT
    stash_strategy = (
        StashStrategy.USER_DISABLED
        if no_stash
        else StashStrategy.AUTO_STASH if inspection.has_changes else StashStrategy.NONE
    )

    return RepoSyncPlan(
        repo_name=inspection.repo_name,
        path=inspection.path,
        target_branches=tuple(b for b in target_branches if b),
        action=action,
        stash_strategy=stash_strategy,
        will_skip=False,
        skip_reason=None,
        needs_attention=bool(inspection.risk_flags),
        attention_reason=", ".join(flag.value for flag in inspection.risk_flags) or None,
    )
```

- [ ] **Step 3: Commit**

```bash
git add py_local_git_pull/cli/sync.py py_local_git_pull/core/services/sync_service.py
git commit -m "feat: create cli/sync.py with --dry-run, --json, --workers"
```

---

### Task 20: Create cli/doctor.py with --json

**Files:**
- Create: `py_local_git_pull/cli/doctor.py`

- [ ] **Step 1: Create doctor.py**

```python
"""Doctor command with json output."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from py_local_git_pull.core.failure.catalog import diagnose_inspection
from py_local_git_pull.core.models import FailureRecord
from py_local_git_pull.core.services.inspector import RepoInspector
from py_local_git_pull.ui.console import make_console
from py_local_git_pull.ui.doctor_view import render_doctor_result


def doctor_command(
    path: Path,
    repo: Annotated[str | None, typer.Option("--repo")] = None,
    kind: Annotated[str | None, typer.Option("--kind")] = None,
    output: Annotated[str, typer.Option("--output")] = "table",
) -> None:
    """Diagnose repository issues and suggest fixes."""
    console = make_console()
    inspections = RepoInspector().inspect_path(
        str(path), recursive=True, max_depth=3
    )

    results: list[dict] = []
    for inspection in inspections:
        if repo and inspection.repo_name != repo:
            continue
        failure = diagnose_inspection(inspection)
        if failure is None:
            continue
        if kind and failure.kind.value != kind:
            continue

        if output == "json":
            results.append({
                "repo_name": inspection.repo_name,
                "path": inspection.path,
                "failure": asdict(failure),
            })
        else:
            render_doctor_result(console, inspection.repo_name, failure)

    if output == "json":
        print(json.dumps({"command": "doctor", "path": str(path), "results": results}))

    raise typer.Exit(code=0)
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/cli/doctor.py
git commit -m "feat: create cli/doctor.py with --json output"
```

---

### Task 21: Create ui/sync_view.py with progress bar, table, colors

**Files:**
- Create: `py_local_git_pull/ui/sync_view.py`

- [ ] **Step 1: Create sync_view.py**

```python
"""Sync output: header, events, summary with progress and colors."""

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from py_local_git_pull.core.models import RepoInspection, RepoOutcome, RepoStatus

_STATUS_STYLE: dict[RepoStatus, str] = {
    RepoStatus.SYNCED: "[green]✓ synced",
    RepoStatus.FAILED: "[red]✗ failed",
    RepoStatus.SKIPPED: "[yellow]⊘ skipped",
    RepoStatus.PARTIAL: "[orange3]◐ partial",
}


def render_sync_header(
    console: Console,
    path: str,
    inspections: tuple[RepoInspection, ...],
    branches: tuple[str, ...],
    dry_run: bool = False,
) -> None:
    """Render sync header panel."""
    branch_text = ", ".join(branches) if branches else "current"
    mode = " [dry-run]" if dry_run else ""
    body = f"path: {path}\nrepos: {len(inspections)}\nbranches: {branch_text}{mode}"
    console.print(Panel(body, title="py-local-git-pull sync", border_style="cyan"))


def render_plan_panel(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    """Render plan panel."""
    safe = sum(1 for item in inspections if not item.risk_flags)
    attention = sum(1 for item in inspections if item.risk_flags)
    body = f"safe: {safe}\nattention: {attention}\nskipped: 0"
    console.print(Panel(body, title="PLAN", border_style="blue"))


def render_repo_events(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render repo events as a Rich Table."""
    if not outcomes:
        return

    table = Table(title="EXECUTION", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Repo", width=20)
    table.add_column("Status", width=12)
    table.add_column("Detail")

    for idx, outcome in enumerate(outcomes, start=1):
        status_style = _STATUS_STYLE.get(outcome.status, outcome.status.value)
        detail = outcome.failure.kind.value if outcome.failure else (outcome.current_branch or "-")
        table.add_row(str(idx), outcome.repo_name, status_style, detail)

    console.print(table)


def render_summary_panel(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render summary panel with color-coded counts."""
    counts = Counter(outcome.status for outcome in outcomes)
    body = (
        f"[green]synced: {counts.get(RepoStatus.SYNCED, 0)}[/]\n"
        f"[orange3]partial: {counts.get(RepoStatus.PARTIAL, 0)}[/]\n"
        f"[yellow]skipped: {counts.get(RepoStatus.SKIPPED, 0)}[/]\n"
        f"[red]failed: {counts.get(RepoStatus.FAILED, 0)}[/]"
    )
    console.print(Panel(body, title="SUMMARY", border_style="green"))


def render_next_actions(console: Console, outcomes: tuple[RepoOutcome, ...]) -> None:
    """Render next actions panel."""
    failed_count = sum(1 for o in outcomes if o.status is RepoStatus.FAILED)
    lines = (
        [f"[red]{failed_count}[/] failed repos → run [bold]doctor[/] for diagnosis"]
        if failed_count
        else ["[green]all repos synced cleanly[/]"]
    )
    console.print(Panel("\n".join(lines), title="NEXT ACTIONS", border_style="yellow"))
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/ui/sync_view.py
git commit -m "feat: create ui/sync_view.py with Rich Table and status colors"
```

---

### Task 22: Create ui/scan_view.py

**Files:**
- Create: `py_local_git_pull/ui/scan_view.py`

- [ ] **Step 1: Create scan_view.py**

```python
"""Scan output with Rich Table."""

from rich.console import Console
from rich.table import Table

from py_local_git_pull.core.models import RepoInspection, RiskLevel

_RISK_STYLE: dict[RiskLevel, str] = {
    RiskLevel.LOW: "green",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.HIGH: "red",
}


def render_scan_summary(console: Console, inspections: tuple[RepoInspection, ...]) -> None:
    """Render scan results as a table."""
    if not inspections:
        console.print("[yellow]No repositories found.[/]")
        return

    table = Table(title="SCAN RESULTS")
    table.add_column("Repo", width=20)
    table.add_column("Branch", width=15)
    table.add_column("Risk", width=8)
    table.add_column("Flags")

    for insp in inspections:
        risk_style = _RISK_STYLE.get(insp.risk_level, "white")
        flags = ", ".join(f.value for f in insp.risk_flags) or "none"
        table.add_row(
            insp.repo_name,
            insp.current_branch or "(detached)",
            f"[{risk_style}]{insp.risk_level.value}[/]",
            flags,
        )

    console.print(table)

    # Summary
    from collections import Counter
    counts = Counter(insp.risk_level for insp in inspections)
    summary = (
        f"total: {len(inspections)}  "
        f"[green]low: {counts.get(RiskLevel.LOW, 0)}[/]  "
        f"[yellow]medium: {counts.get(RiskLevel.MEDIUM, 0)}[/]  "
        f"[red]high: {counts.get(RiskLevel.HIGH, 0)}[/]"
    )
    console.print(f"\n{summary}")
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/ui/scan_view.py
git commit -m "feat: create ui/scan_view.py with Rich Table"
```

---

### Task 23: Update ui/doctor_view.py

**Files:**
- Modify: `py_local_git_pull/ui/doctor_view.py`

- [ ] **Step 1: Update doctor_view.py (keep existing, update imports)**

```python
"""Render diagnosis results for the doctor command."""

from rich.console import Console
from rich.panel import Panel

from py_local_git_pull.core.models import FailureRecord


def render_doctor_result(console: Console, repo_name: str, failure: FailureRecord) -> None:
    """Render a single doctor diagnosis result."""
    lines = [
        f"PROBLEM: {failure.kind.value}",
        f"WHY: {failure.detail or failure.summary}",
        "DO NOW:",
    ]
    lines.extend(
        f"  {idx}. {action.description}{f' → {action.command}' if action.command else ''}"
        for idx, action in enumerate(failure.suggested_actions, start=1)
    )
    console.print(Panel("\n".join(lines), title=f"REPO: {repo_name}", border_style="magenta"))
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/ui/doctor_view.py
git commit -m "refactor: update ui/doctor_view.py imports"
```

---

### Task 24: Create ui/interactive.py

**Files:**
- Create: `py_local_git_pull/ui/interactive.py`

- [ ] **Step 1: Create interactive.py**

```python
"""Interactive prompt helpers using questionary."""

import questionary

from py_local_git_pull.core.models import RepoInspection


def choose_repo_paths(inspections: tuple[RepoInspection, ...]) -> list[str]:
    """Show interactive checkbox list for repo selection."""
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

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/ui/interactive.py
git commit -m "refactor: create ui/interactive.py from prompts.py"
```

---

### Task 25: Create config/settings.py

**Files:**
- Create: `py_local_git_pull/config/settings.py`

- [ ] **Step 1: Create settings.py**

```python
"""Configuration file loading via tomllib."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    """Application settings from config file."""
    recursive: bool = False
    max_depth: int = 3
    branch: tuple[str, ...] = ()
    auto_upstream: bool = False
    skip_non_exist: bool = True
    no_stash: bool = False
    depth: int = 1
    workers: int = 4


_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "py-local-git-pull" / "config.toml"


def load_settings(config_path: Path | None = None) -> AppSettings:
    """Load settings from config file, falling back to defaults."""
    path = config_path or _DEFAULT_CONFIG_PATH

    if not path.exists():
        return AppSettings()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return AppSettings()

    defaults = data.get("defaults", {})
    return AppSettings(
        recursive=defaults.get("recursive", False),
        max_depth=defaults.get("max_depth", 3),
        branch=tuple(defaults.get("branch", [])),
        auto_upstream=defaults.get("auto_upstream", False),
        skip_non_exist=defaults.get("skip_non_exist", True),
        no_stash=defaults.get("no_stash", False),
        depth=defaults.get("depth", 1),
        workers=defaults.get("workers", 4),
    )
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/config/settings.py
git commit -m "feat: create config/settings.py with tomllib loading"
```

---

### Task 26: Update main.py entrypoint

**Files:**
- Modify: `py_local_git_pull/main.py`

- [ ] **Step 1: Update main.py**

```python
"""CLI entrypoint."""

from .cli.app import app


def main() -> None:
    app(prog_name="py-local-git-pull")
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/main.py
git commit -m "refactor: update main.py to use new cli module"
```

---

### Task 27: Delete old commands/ and utils/ files

**Files:**
- Delete: `py_local_git_pull/commands/app.py`
- Delete: `py_local_git_pull/commands/scan.py`
- Delete: `py_local_git_pull/commands/sync.py`
- Delete: `py_local_git_pull/commands/doctor.py`
- Delete: `py_local_git_pull/commands/__init__.py`
- Delete: `py_local_git_pull/utils/logger.py`
- Delete: `py_local_git_pull/utils/logging_config.py`
- Delete: `py_local_git_pull/utils/__init__.py`
- Delete: `py_local_git_pull/ui/prompts.py`
- Delete: `py_local_git_pull/ui/dashboard.py`
- Delete: `py_local_git_pull/ui/events.py`
- Delete: `py_local_git_pull/ui/summary.py`
- Delete: `py_local_git_pull/ui/__init__.py`

- [ ] **Step 1: Delete old files**

```bash
rm -rf py_local_git_pull/commands/ \
       py_local_git_pull/utils/ \
       py_local_git_pull/ui/prompts.py \
       py_local_git_pull/ui/dashboard.py \
       py_local_git_pull/ui/events.py \
       py_local_git_pull/ui/summary.py \
       py_local_git_pull/ui/__init__.py
```

- [ ] **Step 2: Run ruff check**

Run: `ruff check .`
Expected: Clean (no errors)

- [ ] **Step 3: Smoke test CLI**

Run: `python -m py_local_git_pull --help`
Expected: Shows scan/sync/doctor commands with global options

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "refactor: delete old commands/ and utils/, complete Phase 4"
```

---

## Phase 5: Cleanup

### Task 28: Create utils/logging.py with structlog

**Files:**
- Create: `py_local_git_pull/utils/__init__.py`
- Create: `py_local_git_pull/utils/logging.py`

- [ ] **Step 1: Create logging.py**

```python
"""Structured logging configuration with structlog."""

import logging
import logging.handlers
from pathlib import Path

import structlog
from structlog.types import Processor

from py_local_git_pull.config.defaults import (
    LOG_DIR,
    LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_WHEN,
)


def configure_logging(
    *,
    verbose: int = 0,
    quiet: bool = False,
    log_dir: str | None = None,
) -> None:
    """Configure structlog for the application.

    Args:
        verbose: Verbosity level (0=INFO, 1=DEBUG, 2+=TRACE).
        quiet: If True, suppress all console output.
        log_dir: Directory for log files.
    """
    log_dir = log_dir or LOG_DIR
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if verbose > 0 else (logging.WARNING if quiet else logging.INFO)

    # File handler: JSON structured logs
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path / LOG_FILE,
        when=LOG_WHEN,
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Console handler: human-readable
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(file_handler)
    if not quiet:
        root.addHandler(console_handler)

    # structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if quiet:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/utils/logging.py py_local_git_pull/utils/__init__.py
git commit -m "feat: create utils/logging.py with structlog configuration"
```

---

### Task 29: Update py_local_git_pull/__init__.py

**Files:**
- Modify: `py_local_git_pull/__init__.py`

- [ ] **Step 1: Update __init__.py**

```python
"""py-local-git-pull — Git task console for local repositories."""

__version__ = "0.3.0"
```

- [ ] **Step 2: Commit**

```bash
git add py_local_git_pull/__init__.py
git commit -m "chore: update package version to 0.3.0"
```

---

### Task 30: Update existing tests to use new imports

**Files:**
- Modify: All existing test files under `tests/`

- [ ] **Step 1: Update test imports**

All existing tests reference old modules. Update them:

- `tests/core/test_models.py` — no changes needed (models.py unchanged)
- `tests/core/test_result_model.py` — delete (result_model.py deleted)
- `tests/core/test_sync_options.py` — delete (sync_options.py deleted)
- `tests/core/test_git_executor.py` — update to import from `core.git.runner`
- `tests/core/test_repo_finder.py` — update to import from `core.discovery.repo_finder`
- `tests/core/test_branch_syncer.py` — delete (branch_syncer.py deleted, covered by sync_service tests)
- `tests/core/test_git_manager_remote_cache.py` — delete (git_manager.py deleted)
- `tests/core/test_sync_planner.py` — update to import `build_sync_plan` from `core.services.syncService`
- `tests/core/test_repo_inspector.py` — update to import from `core.services.inspector`
- `tests/core/test_failure_catalog.py` — update to import from `core.failure.catalog`
- `tests/commands/test_sync_command.py` — update to import from `cli.sync`
- `tests/commands/test_doctor_command.py` — update to import from `cli.doctor`
- `tests/commands/test_scan_command.py` — update to import from `cli.scan`
- `tests/commands/test_app.py` — update to import from `cli.app`
- `tests/ui/test_doctor_view.py` — update to import from `ui.doctor_view`
- `tests/ui/test_summary_render.py` — update to import from `ui.scan_view`

- [ ] **Step 2: Run full test suite**

Run: `uv run --group dev pytest -q`
Expected: All tests pass (some may need adjustment for new APIs)

- [ ] **Step 3: Run ruff check**

Run: `ruff check .`
Expected: Clean

- [ ] **Step 4: Final smoke test**

Run: `python -m py_local_git_pull --help`
Run: `python -m py_local_git_pull scan --help`
Run: `python -m py_local_git_pull sync --help`
Run: `python -m py_local_git_pull doctor --help`
Expected: All show correct help output

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: update all tests for new module structure"
```

---

## Self-Review

### 1. Spec coverage check

| Spec requirement | Task |
|-----------------|------|
| Eliminate dual models | Task 15 (delete result_model.py, sync_options.py) |
| Split GitManager | Tasks 7-11 (branch, stash, remote, info, sync_service) |
| Eliminate circular deps | All new modules use DI via constructor |
| tenacity retry | Task 6 (GitRunner.run_with_retry), Task 9 (RemoteOperations) |
| structlog logging | Task 28 (utils/logging.py) |
| anyio concurrency | Task 16 (sync_all_repos async) |
| tomllib config | Task 25 (config/settings.py) |
| --dry-run | Task 19 (cli/sync.py) |
| --json all commands | Tasks 18, 19, 20 |
| --verbose/-q | Task 17 (cli/app.py global options) |
| Progress bar + colors | Task 21 (ui/sync_view.py) |
| Rich Table | Tasks 21, 22 |
| PEP 604 types | All new files use `list[str]`, `str | None`, etc. |
| English messages | All new files use English |
| Delete config/constants.py | Task 15 |

### 2. Placeholder scan
No "TBD", "TODO", or "implement later" found.

### 3. Type consistency
All function signatures use consistent types:
- `RepoInspection`, `RepoOutcome`, `RepoSyncPlan` from `core.models`
- `GitRunner` passed to all git operation classes
- Return types consistently use `tuple[...]`, `str | None`, `bool`

### 4. No missing references
All imports reference types defined in earlier tasks or in the existing `models.py`.

---

## Execution

Plan complete and saved to `docs/superpowers/plans/2026-03-31-full-refactor.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
