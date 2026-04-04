"""Stash operations: save and restore working tree changes."""

from datetime import UTC, datetime

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
            code, _, _ = self._runner.run(["rev-parse", "--verify", HEAD_REF], check=False)
            if code != 0:
                log.warning("stash_skipped", repo=repo_name, reason="no commits yet")
                return False

            message = f"py-local-git-pull:{repo_name}:{datetime.now(UTC).isoformat()}"
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
