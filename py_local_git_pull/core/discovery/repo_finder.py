"""Repository discovery via BFS directory scanning."""

import os
from collections import deque
from pathlib import Path
import subprocess

import structlog

from py_local_git_pull.config.defaults import SKIP_DIR_NAMES

log = structlog.get_logger()


def looks_like_git_repo_candidate(path: Path) -> bool:
    """Fast filesystem check before running git commands."""
    git_dir = path / ".git"
    if git_dir.exists():
        return True

    try:
        return (
            path.joinpath("HEAD").is_file()
            and path.joinpath("objects").is_dir()
            and path.joinpath("refs").is_dir()
        )
    except (OSError, PermissionError):
        return False


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


def _should_skip_directory(entry: os.DirEntry, visited: set[Path]) -> bool:
    """Check if directory should be skipped during scan."""
    if not entry.is_dir(follow_symlinks=False):
        return True
    if entry.name in SKIP_DIR_NAMES:
        return True
    if entry.name.startswith("."):
        return True
    sub_path = Path(entry.path)
    if sub_path in visited:
        return True
    return False


def _try_add_git_repo(path: Path, repos: set[str]) -> bool:
    """Try to add a git repository to the set. Returns True if successful."""
    if looks_like_git_repo_candidate(path) and is_git_repo(str(path)):
        repos.add(str(path.resolve()))
        return True
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
                    if _should_skip_directory(entry, visited):
                        continue

                    sub_path = Path(entry.path)
                    if _try_add_git_repo(sub_path, repos):
                        continue

                    queue.append((sub_path, depth + 1))
        except (PermissionError, FileNotFoundError, NotADirectoryError) as e:
            log.warning("dir_access_error", path=str(current), error=str(e))
        except Exception as e:
            log.error("scan_error", path=str(current), error=str(e))

    return sorted(repos)
