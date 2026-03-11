import json

from py_local_git_pull.core.result_model import SyncResult
from py_local_git_pull.main import format_results_json


def test_format_results_json_should_serialize_results() -> None:
    results = [
        SyncResult(repo_name="a", path="/tmp/a", success=True),
        SyncResult(repo_name="b", path="/tmp/b", success=False, error="failed"),
    ]

    payload = format_results_json(results)
    data = json.loads(payload)

    assert isinstance(data, list)
    assert data[0]["repo_name"] == "a"
    assert data[1]["success"] is False
    assert data[1]["error"] == "failed"
