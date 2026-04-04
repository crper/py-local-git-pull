from rich.console import Console

from py_local_git_pull.core.models import FailureKind, FailureRecord
from py_local_git_pull.ui.doctor_view import render_doctor_result


def test_render_doctor_result_contains_problem_and_why() -> None:
    console = Console(record=True)
    failure = FailureRecord(
        kind=FailureKind.UPSTREAM_MISSING,
        summary="current branch has no upstream",
        detail="main is not tracking origin/main",
        raw_error=None,
        can_auto_fix=True,
        suggested_actions=(),
    )
    render_doctor_result(console, "demo", failure)
    output = console.export_text()
    assert "PROBLEM: upstream_missing" in output
    assert "WHY: main is not tracking origin/main" in output
