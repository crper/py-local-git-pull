from py_local_git_pull.core.models import (
    BranchInspection,
    PlanAction,
    RepoInspection,
    RiskFlag,
    RiskLevel,
    StashStrategy,
)
from py_local_git_pull.core.services.sync_service import build_sync_plan


def _inspection(*, risk_flags=(), has_changes=False) -> RepoInspection:
    return RepoInspection(
        repo_name="demo",
        path="/tmp/demo",
        current_branch="main",
        is_git_repo=True,
        is_bare=False,
        has_changes=has_changes,
        has_untracked_changes=has_changes,
        detached_head=False,
        branches=(
            BranchInspection(
                name="main",
                is_current=True,
                exists_locally=True,
                exists_remotely=True,
                has_upstream=True,
                upstream_name="origin/main",
                ahead=0,
                behind=0,
            ),
        ),
        risk_level=RiskLevel.MEDIUM if risk_flags else RiskLevel.LOW,
        risk_flags=tuple(risk_flags),
    )


def test_build_sync_plan_for_current_branch() -> None:
    plan = build_sync_plan(_inspection(), branches=(), no_stash=False)
    assert plan.action is PlanAction.SYNC_CURRENT
    assert plan.stash_strategy is StashStrategy.NONE


def test_build_sync_plan_for_dirty_repo_uses_auto_stash() -> None:
    plan = build_sync_plan(_inspection(has_changes=True), branches=("main",), no_stash=False)
    assert plan.action is PlanAction.SYNC_BRANCHES
    assert plan.stash_strategy is StashStrategy.AUTO_STASH


def test_build_sync_plan_skips_bare_repo() -> None:
    plan = build_sync_plan(
        _inspection(risk_flags=(RiskFlag.BARE_REPOSITORY,)),
        branches=(),
        no_stash=False,
    )
    assert plan.will_skip is True
    assert plan.action is PlanAction.SKIP
