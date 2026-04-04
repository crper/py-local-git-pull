from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner


def test_fetch_success(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    ops = RemoteOperations(runner)
    result = ops.fetch()
    assert isinstance(result, bool)


def test_pull_no_upstream(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    ops = RemoteOperations(runner)
    success, error = ops.pull()
    assert success is False
