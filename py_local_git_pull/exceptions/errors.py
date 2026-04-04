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
        super().__init__(f"git command failed{timeout_part}{code_part}: {command}; {detail}")
