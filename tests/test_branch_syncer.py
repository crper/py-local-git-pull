from py_local_git_pull.config.constants import BranchStatus
from py_local_git_pull.core.branch_syncer import BranchSyncer
from py_local_git_pull.core.result_model import SyncResult
from py_local_git_pull.core.sync_options import SyncOptions


class DummyLogger:
    def warning(self, message: str) -> None:
        return None


class DummyGitManager:
    def __init__(self, local_exists: bool, remote_exists: bool, checkout_ok: bool = True) -> None:
        self.local_exists = local_exists
        self.remote_exists = remote_exists
        self.checkout_ok = checkout_ok
        self.logger = DummyLogger()

    def branch_exists_locally(self, branch: str) -> bool:
        return self.local_exists

    def branch_exists_remotely(self, branch: str) -> bool:
        return self.remote_exists

    def checkout_branch(self, branch: str, create_if_not_exist: bool):
        if self.checkout_ok:
            return True, None
        return False, "checkout failed"

    def set_upstream(self, branch: str, auto_upstream: bool):
        return False, "", None

    def pull(self):
        return True, None


def test_sync_single_branch_should_skip_missing_remote_when_configured() -> None:
    manager = DummyGitManager(local_exists=True, remote_exists=False)
    syncer = BranchSyncer(manager)
    result = SyncResult(repo_name="demo", path="/tmp/demo")
    options = SyncOptions(path="/tmp/demo", auto_upstream=False, skip_non_exist=True)

    detail = syncer.sync_single_branch("feature/x", options, result)

    assert detail is not None
    assert detail.status == BranchStatus.SKIPPED
    assert detail.error == "远程分支不存在"
    assert result.skipped_branches == ["feature/x"]


def test_sync_single_branch_should_mark_result_failed_on_checkout_error() -> None:
    manager = DummyGitManager(local_exists=False, remote_exists=True, checkout_ok=False)
    syncer = BranchSyncer(manager)
    result = SyncResult(repo_name="demo", path="/tmp/demo")
    options = SyncOptions(path="/tmp/demo", auto_upstream=False, skip_non_exist=False)

    detail = syncer.sync_single_branch("feature/x", options, result)

    assert detail is not None
    assert detail.status == BranchStatus.ERROR
    assert result.success is False
    assert result.error == "checkout failed"
