from py_local_git_pull.core.result_model import SyncResult
from py_local_git_pull.ui.display import create_result_table


def test_create_result_table_should_count_repo_level_success() -> None:
    results = [
        SyncResult(repo_name="a", path="/tmp/a", success=True),
        SyncResult(repo_name="b", path="/tmp/b", success=False),
        SyncResult(repo_name="c", path="/tmp/c", success=True),
    ]

    _, success_count = create_result_table(results)
    assert success_count == 2
