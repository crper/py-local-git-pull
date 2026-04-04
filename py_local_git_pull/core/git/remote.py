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
