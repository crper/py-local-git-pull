"""Sync orchestration service."""

import structlog

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
    RepoOutcome,
    RepoStatus,
    RepoSyncPlan,
    RiskFlag,
    StashStrategy,
    SyncOptions,
)

log = structlog.get_logger()


class SyncService:
    """Orchestrate repository sync operations."""

    def __init__(
        self,
        runner: GitRunner,
        branch_ops: BranchOperations,
        stash_ops: StashOperations,
        remote_ops: RemoteOperations,
        info_ops: InfoOperations,
    ):
        self._runner = runner
        self._branch_ops = branch_ops
        self._stash_ops = stash_ops
        self._remote_ops = remote_ops
        self._info_ops = info_ops

    def sync_repo(
        self,
        inspection: RepoInspection,
        plan: RepoSyncPlan,
        options: SyncOptions,
    ) -> RepoOutcome:
        """Sync a single repository.

        Returns:
            RepoOutcome with sync results.
        """
        current_branch = self._info_ops.get_current_branch()
        target_branches = plan.target_branches or ((current_branch,) if current_branch else ())

        if not self._remote_ops.fetch(options.depth):
            failure = classify_git_failure("fetch failed")
            return RepoOutcome(
                repo_name=inspection.repo_name,
                path=inspection.path,
                status=RepoStatus.FAILED,
                current_branch=current_branch,
                target_branches=target_branches,
                synced_branches=(),
                skipped_branches=target_branches,
                stashed=False,
                failure=failure,
            )

        stashed = False
        if (
            not self._info_ops.is_bare()
            and self._info_ops.has_changes()
            and plan.stash_strategy != StashStrategy.USER_DISABLED
        ):
            stashed = self._stash_ops.stash_changes(inspection.repo_name)

        try:
            remote_branches = self._branch_ops.get_remote_branches()
            branch_outcomes = tuple(
                self._sync_single_branch(
                    branch_name,
                    options=options,
                    is_current=(branch_name == current_branch),
                    remote_branches=remote_branches,
                )
                for branch_name in target_branches
            )

            status = self._aggregate_status(branch_outcomes)

            return RepoOutcome(
                repo_name=inspection.repo_name,
                path=inspection.path,
                status=status,
                current_branch=current_branch,
                target_branches=target_branches,
                synced_branches=tuple(
                    o.name for o in branch_outcomes if o.status is BranchStatus.SYNCED
                ),
                skipped_branches=tuple(
                    o.name for o in branch_outcomes if o.status is BranchStatus.SKIPPED
                ),
                stashed=stashed,
                branch_outcomes=branch_outcomes,
            )
        finally:
            if stashed:
                self._stash_ops.pop_stash(inspection.repo_name)

    def _sync_single_branch(
        self,
        branch: str,
        options: SyncOptions,
        is_current: bool,
        remote_branches: set[str],
    ) -> BranchOutcome:
        """Sync a single branch."""
        exists_local = self._branch_ops.branch_exists_locally(branch)
        exists_remote = self._branch_ops.branch_exists_remotely(branch, remote_branches)

        skip_reason = self._get_skip_reason(exists_local, exists_remote, options)
        if skip_reason:
            log.warning("branch_skipped", branch=branch, reason=skip_reason)
            return self._create_skipped_outcome(branch, is_current)

        if not is_current:
            checkout_result = self._try_checkout(branch, exists_remote, remote_branches)
            if checkout_result:
                return checkout_result

        return self._sync_with_upstream(branch, is_current, options, remote_branches)

    def _get_skip_reason(
        self, exists_local: bool, exists_remote: bool, options: SyncOptions
    ) -> str | None:
        """Determine if branch should be skipped and why."""
        if not exists_local and not exists_remote:
            return "does not exist anywhere"
        if not exists_remote and options.skip_non_exist:
            return "remote branch missing"
        return None

    def _try_checkout(
        self, branch: str, exists_remote: bool, remote_branches: set[str]
    ) -> BranchOutcome | None:
        """Attempt to checkout branch. Returns outcome on failure, None on success."""
        success, error = self._branch_ops.checkout_branch(
            branch,
            create_if_not_exist=exists_remote,
            remote_branches=remote_branches,
        )
        if not success:
            return self._create_failed_outcome(branch, False, classify_git_failure(error))
        return None

    def _sync_with_upstream(
        self,
        branch: str,
        is_current: bool,
        options: SyncOptions,
        remote_branches: set[str],
    ) -> BranchOutcome:
        """Sync branch with its upstream."""
        has_upstream, upstream_name, upstream_error = self._branch_ops.set_upstream(
            branch, auto_upstream=options.auto_upstream, remote_branches=remote_branches
        )

        if upstream_error and not has_upstream:
            return self._create_skipped_outcome(
                branch, is_current, classify_git_failure(upstream_error)
            )

        if not has_upstream:
            return self._create_skipped_outcome(
                branch, is_current, classify_git_failure("no upstream")
            )

        return self._execute_pull(branch, is_current, upstream_name)

    def _execute_pull(self, branch: str, is_current: bool, upstream_name: str) -> BranchOutcome:
        """Execute pull and return appropriate outcome."""
        success, pull_error = self._remote_ops.pull()
        if not success:
            return self._create_failed_outcome(
                branch, is_current, classify_git_failure(pull_error), upstream_name
            )

        ahead_behind = self._branch_ops.get_ahead_behind(branch, upstream_name)
        return BranchOutcome(
            name=branch,
            status=BranchStatus.SYNCED,
            is_current=is_current,
            has_upstream=True,
            upstream_name=upstream_name,
            ahead=ahead_behind[0] if ahead_behind else None,
            behind=ahead_behind[1] if ahead_behind else None,
        )

    @staticmethod
    def _create_skipped_outcome(
        branch: str, is_current: bool, failure=None
    ) -> BranchOutcome:
        """Create a skipped branch outcome."""
        return BranchOutcome(
            name=branch,
            status=BranchStatus.SKIPPED,
            is_current=is_current,
            has_upstream=False,
            upstream_name=None,
            ahead=None,
            behind=None,
            failure=failure,
        )

    @staticmethod
    def _create_failed_outcome(
        branch: str, is_current: bool, failure, upstream_name: str | None = None
    ) -> BranchOutcome:
        """Create a failed branch outcome."""
        return BranchOutcome(
            name=branch,
            status=BranchStatus.FAILED,
            is_current=is_current,
            has_upstream=upstream_name is not None,
            upstream_name=upstream_name,
            ahead=None,
            behind=None,
            failure=failure,
        )

    @staticmethod
    def _aggregate_status(outcomes: tuple[BranchOutcome, ...]) -> RepoStatus:
        """Aggregate branch outcomes into a repo status."""
        has_failed = any(outcome.status is BranchStatus.FAILED for outcome in outcomes)
        has_skipped = any(outcome.status is BranchStatus.SKIPPED for outcome in outcomes)
        has_synced = any(outcome.status is BranchStatus.SYNCED for outcome in outcomes)

        if has_failed and has_synced:
            return RepoStatus.PARTIAL
        if has_failed:
            return RepoStatus.FAILED
        if has_skipped and not has_synced:
            return RepoStatus.SKIPPED
        return RepoStatus.SYNCED


def _create_bare_repo_plan(inspection: RepoInspection) -> RepoSyncPlan:
    """Create a plan for bare repositories that cannot be synced."""
    return RepoSyncPlan(
        repo_name=inspection.repo_name,
        path=inspection.path,
        target_branches=(),
        action=PlanAction.SKIP,
        stash_strategy=StashStrategy.NONE,
        will_skip=True,
        skip_reason="bare repository",
        needs_attention=True,
        attention_reason="bare repository cannot follow the standard task flow",
    )


def _determine_stash_strategy(no_stash: bool, has_changes: bool) -> StashStrategy:
    """Determine the appropriate stash strategy based on options and state."""
    if no_stash:
        return StashStrategy.USER_DISABLED
    if has_changes:
        return StashStrategy.AUTO_STASH
    return StashStrategy.NONE


def _format_attention_reason(risk_flags: tuple[RiskFlag, ...]) -> str | None:
    """Format risk flags into human-readable attention reason."""
    if not risk_flags:
        return None
    return ", ".join(flag.value for flag in risk_flags)


def build_sync_plan(
    inspection: RepoInspection,
    *,
    branches: tuple[str, ...],
    no_stash: bool,
) -> RepoSyncPlan:
    """Build a sync plan from an inspection."""
    if RiskFlag.BARE_REPOSITORY in inspection.risk_flags:
        return _create_bare_repo_plan(inspection)

    target_branches = branches or (
        (inspection.current_branch,) if inspection.current_branch else ()
    )
    action = PlanAction.SYNC_BRANCHES if branches else PlanAction.SYNC_CURRENT
    stash_strategy = _determine_stash_strategy(no_stash, inspection.has_changes)

    return RepoSyncPlan(
        repo_name=inspection.repo_name,
        path=inspection.path,
        target_branches=tuple(b for b in target_branches if b),
        action=action,
        stash_strategy=stash_strategy,
        will_skip=False,
        skip_reason=None,
        needs_attention=bool(inspection.risk_flags),
        attention_reason=_format_attention_reason(inspection.risk_flags),
    )
