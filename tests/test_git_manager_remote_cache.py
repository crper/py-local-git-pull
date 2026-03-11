from py_local_git_pull.core.git_manager import GitManager


class FakeExecutor:
    def __init__(self) -> None:
        self.for_each_ref_calls = 0
        self.ls_remote_calls = 0

    def run(self, command, check=True, timeout=None):
        if command[0] == "for-each-ref":
            self.for_each_ref_calls += 1
            return 0, "origin/main\norigin/dev\norigin/HEAD", ""
        if command[0] == "ls-remote":
            self.ls_remote_calls += 1
            return 0, "", ""
        return 0, "", ""


def test_branch_exists_remotely_should_use_cache_after_first_load() -> None:
    manager = GitManager("/tmp/repo")
    manager.executor = FakeExecutor()

    assert manager.branch_exists_remotely("main") is True
    assert manager.branch_exists_remotely("dev") is True
    assert manager.branch_exists_remotely("feature/x") is False

    assert manager.executor.for_each_ref_calls == 1
    assert manager.executor.ls_remote_calls == 0
