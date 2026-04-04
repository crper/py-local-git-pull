from py_local_git_pull.core.models import RiskFlag, RiskLevel
from py_local_git_pull.core.services.inspector import RepoInspector, derive_risk_state


def test_local_changes_raise_medium_risk() -> None:
    level, flags = derive_risk_state(
        has_changes=True,
        detached_head=False,
        is_bare=False,
        branches_have_missing_upstream=False,
        branches_have_missing_remote=False,
    )
    assert level is RiskLevel.MEDIUM
    assert RiskFlag.HAS_LOCAL_CHANGES in flags


def test_detached_head_raises_high_risk() -> None:
    level, flags = derive_risk_state(
        has_changes=False,
        detached_head=True,
        is_bare=False,
        branches_have_missing_upstream=False,
        branches_have_missing_remote=False,
    )
    assert level is RiskLevel.HIGH
    assert RiskFlag.DETACHED_HEAD in flags


def test_inspect_repo_can_skip_ahead_behind_for_lightweight_mode(monkeypatch) -> None:
    calls = {"ahead_behind": 0}

    class FakeInfoOps:
        def __init__(self, runner) -> None:
            pass

        def get_current_branch(self) -> str | None:
            return "main"

        def is_bare(self) -> bool:
            return False

        def has_changes(self) -> bool:
            return False

        def get_local_branches(self) -> list[tuple[str, bool]]:
            return [("main", True)]

    class FakeBranchOps:
        def __init__(self, runner) -> None:
            pass

        def get_remote_branches(self) -> set[str]:
            return {"main"}

        def set_upstream(self, branch: str, *, auto_upstream: bool = False):
            return True, "origin/main", None

        def get_ahead_behind(self, branch: str, upstream: str):
            calls["ahead_behind"] += 1
            return (0, 0)

    monkeypatch.setattr(
        "py_local_git_pull.core.services.inspector.GitRunner",
        lambda path: object(),
    )
    monkeypatch.setattr("py_local_git_pull.core.services.inspector.InfoOperations", FakeInfoOps)
    monkeypatch.setattr(
        "py_local_git_pull.core.services.inspector.BranchOperations",
        FakeBranchOps,
    )

    inspection = RepoInspector().inspect_repo("/tmp/demo", include_branch_deltas=False)

    assert inspection.current_branch == "main"
    assert calls["ahead_behind"] == 0
