"""Tests for SyncService."""

from py_local_git_pull.core.failure.catalog import classify_git_failure
from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.remote import RemoteOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.git.stash import StashOperations
from py_local_git_pull.core.models import (
    BranchOutcome,
    BranchStatus,
    PlanAction,
    RepoInspection,
    RepoStatus,
    RepoSyncPlan,
    RiskFlag,
    RiskLevel,
    StashStrategy,
    SyncOptions,
)
from py_local_git_pull.core.services.sync_service import SyncService, build_sync_plan


def _make_git_runner(tmp_path):
    runner = GitRunner(str(tmp_path))
    runner.run(["init"])
    runner.run(["config", "user.email", "test@test.com"])
    runner.run(["config", "user.name", "Test"])
    (tmp_path / "file.txt").write_text("hello")
    runner.run(["add", "."])
    runner.run(["commit", "-m", "init"])
    return runner


def _make_sync_service(tmp_path):
    runner = _make_git_runner(tmp_path)
    return SyncService(
        runner=runner,
        branch_ops=BranchOperations(runner),
        stash_ops=StashOperations(runner),
        remote_ops=RemoteOperations(runner),
        info_ops=InfoOperations(runner),
    )


def _make_inspection(tmp_path, **overrides):
    defaults = dict(
        repo_name="test",
        path=str(tmp_path),
        current_branch="master",
        is_git_repo=True,
        is_bare=False,
        has_changes=False,
        has_untracked_changes=False,
        detached_head=False,
        branches=(),
        risk_level=RiskLevel.LOW,
        risk_flags=(),
    )
    defaults.update(overrides)
    return RepoInspection(**defaults)


def _make_plan(tmp_path, **overrides):
    defaults = dict(
        repo_name="test",
        path=str(tmp_path),
        target_branches=(),
        action=PlanAction.SYNC_CURRENT,
        stash_strategy=StashStrategy.NONE,
        will_skip=False,
        skip_reason=None,
        needs_attention=False,
        attention_reason=None,
    )
    defaults.update(overrides)
    return RepoSyncPlan(**defaults)


class TestSyncServiceSyncRepo:
    def test_sync_no_remote_fails_gracefully(self, tmp_path):
        """Sync with no remote configured should fail gracefully."""
        service = _make_sync_service(tmp_path)
        inspection = _make_inspection(tmp_path)
        plan = _make_plan(tmp_path)
        outcome = service.sync_repo(
            inspection, plan, SyncOptions(auto_upstream=False, skip_non_exist=True, depth=1)
        )
        assert outcome.status is RepoStatus.SKIPPED
        assert outcome.stashed is False
        assert "master" in outcome.skipped_branches

    def test_sync_bare_repo_is_skipped(self, tmp_path):
        """Bare repositories should be skipped."""
        service = _make_sync_service(tmp_path)
        inspection = _make_inspection(
            tmp_path,
            is_bare=True,
            risk_flags=(RiskFlag.BARE_REPOSITORY,),
            risk_level=RiskLevel.HIGH,
        )
        plan = _make_plan(
            tmp_path,
            target_branches=(),
            action=PlanAction.SKIP,
            will_skip=True,
            skip_reason="bare repository",
            needs_attention=True,
        )
        outcome = service.sync_repo(
            inspection, plan, SyncOptions(auto_upstream=False, skip_non_exist=True, depth=1)
        )
        assert outcome.status is RepoStatus.SKIPPED
        assert "master" in outcome.skipped_branches

    def test_sync_empty_target_branches_uses_current(self, tmp_path):
        """When plan has no target branches, should use current branch."""
        service = _make_sync_service(tmp_path)
        inspection = _make_inspection(tmp_path, current_branch="master")
        plan = _make_plan(tmp_path, target_branches=())
        outcome = service.sync_repo(
            inspection, plan, SyncOptions(auto_upstream=False, skip_non_exist=True, depth=1)
        )
        assert outcome.status is RepoStatus.SKIPPED
        assert outcome.current_branch == "master"
        assert "master" in outcome.target_branches


class TestSyncServiceSyncSingleBranch:
    def test_sync_branch_not_exist_anywhere(self, tmp_path):
        """Branch that does not exist locally or remotely should be skipped."""
        service = _make_sync_service(tmp_path)
        outcome = service._sync_single_branch(
            "nonexistent",
            options=SyncOptions(auto_upstream=False, skip_non_exist=True),
            is_current=False,
            remote_branches=set(),
        )
        assert outcome.status is BranchStatus.SKIPPED
        assert outcome.name == "nonexistent"
        assert outcome.has_upstream is False

    def test_sync_branch_remote_missing_with_skip(self, tmp_path):
        """Branch with no remote and skip_non_exist=True should be skipped."""
        service = _make_sync_service(tmp_path)
        outcome = service._sync_single_branch(
            "master",
            options=SyncOptions(auto_upstream=False, skip_non_exist=True),
            is_current=False,
            remote_branches=set(),
        )
        assert outcome.status is BranchStatus.SKIPPED


class TestSyncServiceAggregateStatus:
    def test_all_synced(self):
        outcomes = (
            BranchOutcome(
                name="main",
                status=BranchStatus.SYNCED,
                is_current=True,
                has_upstream=True,
                upstream_name="origin/main",
                ahead=0,
                behind=0,
            ),
        )
        assert SyncService._aggregate_status(outcomes) is RepoStatus.SYNCED

    def test_all_failed(self):
        outcomes = (
            BranchOutcome(
                name="main",
                status=BranchStatus.FAILED,
                is_current=True,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
                failure=classify_git_failure("fetch failed"),
            ),
        )
        assert SyncService._aggregate_status(outcomes) is RepoStatus.FAILED

    def test_partial_sync(self):
        outcomes = (
            BranchOutcome(
                name="main",
                status=BranchStatus.SYNCED,
                is_current=True,
                has_upstream=True,
                upstream_name="origin/main",
                ahead=0,
                behind=0,
            ),
            BranchOutcome(
                name="dev",
                status=BranchStatus.FAILED,
                is_current=False,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
                failure=classify_git_failure("fetch failed"),
            ),
        )
        assert SyncService._aggregate_status(outcomes) is RepoStatus.PARTIAL

    def test_all_skipped(self):
        outcomes = (
            BranchOutcome(
                name="main",
                status=BranchStatus.SKIPPED,
                is_current=True,
                has_upstream=False,
                upstream_name=None,
                ahead=None,
                behind=None,
            ),
        )
        assert SyncService._aggregate_status(outcomes) is RepoStatus.SKIPPED


class TestBuildSyncPlan:
    def test_build_plan_for_bare_repo(self, tmp_path):
        """Bare repos should produce skip plans."""
        inspection = _make_inspection(
            tmp_path,
            is_bare=True,
            risk_flags=(RiskFlag.BARE_REPOSITORY,),
        )
        plan = build_sync_plan(inspection, branches=(), no_stash=False)
        assert plan.will_skip is True
        assert plan.action is PlanAction.SKIP
        assert plan.skip_reason == "bare repository"

    def test_build_plan_for_normal_repo(self, tmp_path):
        """Normal repos should produce sync plans."""
        inspection = _make_inspection(tmp_path, current_branch="main")
        plan = build_sync_plan(inspection, branches=(), no_stash=False)
        assert plan.will_skip is False
        assert plan.action is PlanAction.SYNC_CURRENT
        assert plan.target_branches == ("main",)

    def test_build_plan_with_explicit_branches(self, tmp_path):
        """Explicit branches should override current branch."""
        inspection = _make_inspection(tmp_path, current_branch="main")
        plan = build_sync_plan(inspection, branches=("dev", "feature"), no_stash=False)
        assert plan.action is PlanAction.SYNC_BRANCHES
        assert plan.target_branches == ("dev", "feature")

    def test_build_plan_with_no_stash(self, tmp_path):
        """no_stash=True should set USER_DISABLED strategy."""
        inspection = _make_inspection(tmp_path, has_changes=True)
        plan = build_sync_plan(inspection, branches=(), no_stash=True)
        assert plan.stash_strategy is StashStrategy.USER_DISABLED

    def test_build_plan_with_changes(self, tmp_path):
        """Repos with changes should get AUTO_STASH strategy."""
        inspection = _make_inspection(tmp_path, has_changes=True)
        plan = build_sync_plan(inspection, branches=(), no_stash=False)
        assert plan.stash_strategy is StashStrategy.AUTO_STASH

    def test_build_plan_without_changes(self, tmp_path):
        """Clean repos should get NONE stash strategy."""
        inspection = _make_inspection(tmp_path, has_changes=False)
        plan = build_sync_plan(inspection, branches=(), no_stash=False)
        assert plan.stash_strategy is StashStrategy.NONE

    def test_build_plan_with_risk_flags(self, tmp_path):
        """Risk flags should set needs_attention."""
        inspection = _make_inspection(
            tmp_path,
            risk_flags=(RiskFlag.NO_UPSTREAM,),
        )
        plan = build_sync_plan(inspection, branches=(), no_stash=False)
        assert plan.needs_attention is True
        assert "no_upstream" in plan.attention_reason
