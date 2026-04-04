from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.info import InfoOperations


def _make_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    return runner


def test_is_bare_false(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    assert ops.is_bare() is False


def test_has_changes_false_initially(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    assert ops.has_changes() is False


def test_has_changes_true_after_modify(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    (tmp_path / "file.txt").write_text("hello")
    assert ops.has_changes() is True


def test_get_local_branches_empty(tmp_path):
    runner = _make_runner(tmp_path)
    ops = InfoOperations(runner)
    branches = ops.get_local_branches()
    assert branches == []
