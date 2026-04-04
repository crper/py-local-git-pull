from rich.console import Console

from py_local_git_pull.core.models import RepoInspection, RiskLevel
from py_local_git_pull.ui.summary import render_scan_summary


def test_render_scan_summary_contains_title() -> None:
    console = Console(record=True)
    inspection = RepoInspection(
        repo_name="demo",
        path="/tmp/demo",
        current_branch="main",
        is_git_repo=True,
        is_bare=False,
        has_changes=False,
        has_untracked_changes=False,
        detached_head=False,
        branches=(),
        risk_level=RiskLevel.LOW,
        risk_flags=(),
    )
    render_scan_summary(console, (inspection,), path="/tmp/demo", recursive=False, max_depth=3)
    output = console.export_text()
    assert "INVENTORY" in output
    assert "RISKS" in output
    assert "NEXT" in output
    assert "total: 1" in output
