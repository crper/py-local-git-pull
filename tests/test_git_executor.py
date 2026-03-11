import subprocess

import pytest

from py_local_git_pull.core.git_executor import GitExecutor
from py_local_git_pull.exceptions import GitCommandError


def test_run_should_raise_git_command_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0],
            output="",
            stderr="fatal: bad revision",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    executor = GitExecutor("/tmp/repo")
    with pytest.raises(GitCommandError) as exc_info:
        executor.run(["rev-parse", "--verify", "HEAD"], check=True)

    assert "fatal: bad revision" in str(exc_info.value)
    assert exc_info.value.returncode == 1
