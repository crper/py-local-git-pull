from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations


def _make_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    # Create an initial commit
    (tmp_path / "file.txt").write_text("hello")
    runner.run(["add", "."])
    runner.run(["commit", "-m", "init"])
    return runner


def test_stash_no_changes(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    result = ops.stash_changes("test-repo")
    assert result is False


def test_stash_with_changes(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    # Make a change
    (tmp_path / "file.txt").write_text("modified")
    result = ops.stash_changes("test-repo")
    assert result is True
    assert ops.has_stash


def test_pop_stash(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    (tmp_path / "file.txt").write_text("modified")
    ops.stash_changes("test-repo")
    result = ops.pop_stash("test-repo")
    assert result is True
    assert not ops.has_stash


def test_pop_stash_nothing_to_pop(tmp_path):
    runner = _make_runner(tmp_path)
    ops = StashOperations(runner)
    result = ops.pop_stash("test-repo")
    assert result is False
