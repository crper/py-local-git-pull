"""Git command execution with retry support."""

import subprocess

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
            stdout = self._extract_output(e.stdout)
            stderr = self._extract_output(e.stderr)
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=124,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=True,
                ) from e
            return 124, "", f"git command timed out: {' '.join(full_command)}"
        except subprocess.CalledProcessError as e:
            stdout = self._extract_output(e.stdout)
            stderr = self._extract_output(e.stderr) or str(e)
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=e.returncode,
                    stdout=stdout,
                    stderr=stderr,
                ) from e
            return e.returncode, stdout, stderr

    @staticmethod
    def _extract_output(output: str | bytes | None) -> str:
        """Extract string output from subprocess result."""
        if output is None:
            return ""
        if isinstance(output, str):
            return output.strip()
        return output.decode("utf-8", errors="replace").strip()

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
