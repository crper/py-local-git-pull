import pytest

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.exceptions.errors import GitCommandError


def test_run_success(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    code, out, err = runner.run(["branch", "--show-current"])
    assert code == 0


def test_run_check_false_failure(tmp_path):
    runner = GitRunner(str(tmp_path))
    code, out, err = runner.run(["nonexistent"], check=False)
    assert code != 0
    assert err


def test_run_check_true_raises(tmp_path):
    runner = GitRunner(str(tmp_path))
    with pytest.raises(GitCommandError):
        runner.run(["nonexistent"], check=True)
