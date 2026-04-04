"""Filesystem locations for config, state, and run journals."""

from dataclasses import dataclass
import os
from pathlib import Path

try:
    from platformdirs import PlatformDirs
except ImportError:  # pragma: no cover - fallback for offline/dev environments
    PlatformDirs = None


APP_NAME = "py-local-git-pull"
APP_AUTHOR = "crper"


@dataclass(frozen=True)
class StatePaths:
    state_dir: Path
    runs_dir: Path
    logs_dir: Path
    config_file: Path


def build_state_paths(base_dir: Path | None = None) -> StatePaths:
    root = base_dir or _default_state_dir()
    return StatePaths(
        state_dir=root,
        runs_dir=root / "runs",
        logs_dir=root / "logs",
        config_file=root / "config.toml",
    )


def get_state_paths() -> StatePaths:
    paths = build_state_paths()
    for directory in (paths.state_dir, paths.runs_dir, paths.logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def _default_state_dir() -> Path:
    env_override = os.environ.get("PY_LOCAL_GIT_PULL_STATE_DIR")
    if env_override:
        return Path(env_override).expanduser()

    if PlatformDirs is not None:
        return Path(PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR).user_state_dir)

    home = Path.home()
    if (home / "Library").exists():
        return home / "Library" / "Application Support" / APP_NAME
    return home / ".local" / "state" / APP_NAME
