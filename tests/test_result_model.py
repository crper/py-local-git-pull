from py_local_git_pull.core.result_model import SyncResult


def test_mark_failed_should_set_success_and_keep_first_error() -> None:
    result = SyncResult(repo_name="demo", path="/tmp/demo")

    result.mark_failed("first")
    result.mark_failed("second")

    assert result.success is False
    assert result.error == "first"
