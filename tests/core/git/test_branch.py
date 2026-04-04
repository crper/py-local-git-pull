"""Tests for BranchOperations."""

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
    # Fresh repo returns default branch name (master/main) or None
    branch = ops.get_current_branch()
    assert branch is None or isinstance(branch, str)


def test_branch_exists_locally_false(tmp_path):
    runner = _make_runner(tmp_path)
    ops = BranchOperations(runner)
    assert ops.branch_exists_locally("nonexistent") is False


def test_get_remote_branches_empty(tmp_path):
    runner = _make_runner(tmp_path)
    ops = BranchOperations(runner)
    branches = ops.get_remote_branches()
    assert branches == set()
