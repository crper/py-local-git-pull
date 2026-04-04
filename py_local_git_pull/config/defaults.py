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

# Discovery defaults
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
    }
)
