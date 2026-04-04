"""Repository inspection service."""

from pathlib import Path

from py_local_git_pull.core.git.branch import BranchOperations
from py_local_git_pull.core.git.info import InfoOperations
from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.core.models import (
    BranchInspection,
    RepoInspection,
    RiskFlag,
    RiskLevel,
)
from py_local_git_pull.core.discovery.repo_finder import find_git_repos, is_git_repo


def derive_risk_state(
    *,
    has_changes: bool,
    detached_head: bool,
    is_bare: bool,
    branches_have_missing_upstream: bool,
    branches_have_missing_remote: bool,
) -> tuple[RiskLevel, tuple[RiskFlag, ...]]:
    """Derive risk level and flags from repository state."""
    flags: list[RiskFlag] = []

    if has_changes:
        flags.append(RiskFlag.HAS_LOCAL_CHANGES)
    if detached_head:
        flags.append(RiskFlag.DETACHED_HEAD)
    if is_bare:
        flags.append(RiskFlag.BARE_REPOSITORY)
    if branches_have_missing_upstream:
        flags.append(RiskFlag.NO_UPSTREAM)
    if branches_have_missing_remote:
        flags.append(RiskFlag.REMOTE_BRANCH_MISSING)

    if RiskFlag.DETACHED_HEAD in flags or RiskFlag.BARE_REPOSITORY in flags:
        level = RiskLevel.HIGH
    elif flags:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return level, tuple(flags)


class RepoInspector:
    """Inspect repositories and derive risk state."""

    def inspect_repo(
        self,
        repo_path: str,
        *,
        include_branch_deltas: bool = True,
    ) -> RepoInspection:
        """Inspect a single repository."""
        runner = GitRunner(repo_path)
        info_ops = InfoOperations(runner)
        branch_ops = BranchOperations(runner)

        current_branch = info_ops.get_current_branch()
        is_bare = info_ops.is_bare()
        has_changes = info_ops.has_changes()

        remote_branches = branch_ops.get_remote_branches()
        local_branches = info_ops.get_local_branches()

        branches = []
        for name, is_current in local_branches:
            exists_remote = name in remote_branches
            has_upstream, upstream_name, _ = branch_ops.set_upstream(name, auto_upstream=False)
            ahead_behind = None
            if has_upstream and include_branch_deltas:
                ahead_behind = branch_ops.get_ahead_behind(name, upstream_name)

            branches.append(
                BranchInspection(
                    name=name,
                    is_current=is_current,
                    exists_locally=True,
                    exists_remotely=exists_remote,
                    has_upstream=has_upstream,
                    upstream_name=upstream_name,
                    ahead=ahead_behind[0] if ahead_behind else None,
                    behind=ahead_behind[1] if ahead_behind else None,
                )
            )

        level, flags = derive_risk_state(
            has_changes=has_changes,
            detached_head=current_branch is None,
            is_bare=is_bare,
            branches_have_missing_upstream=any(not b.has_upstream for b in branches),
            branches_have_missing_remote=any(not b.exists_remotely for b in branches),
        )

        return RepoInspection(
            repo_name=Path(repo_path).name,
            path=str(Path(repo_path).resolve()),
            current_branch=current_branch,
            is_git_repo=True,
            is_bare=is_bare,
            has_changes=has_changes,
            has_untracked_changes=has_changes,
            detached_head=current_branch is None,
            branches=tuple(branches),
            risk_level=level,
            risk_flags=flags,
        )

    def inspect_path(
        self,
        path: str,
        *,
        recursive: bool,
        max_depth: int,
        include_branch_deltas: bool = True,
    ) -> tuple[RepoInspection, ...]:
        """Scan a path for repositories and inspect each one."""
        if recursive:
            repo_paths = find_git_repos(path, max_depth)
        else:
            repo_paths = [path] if is_git_repo(path) else []

        return tuple(
            self.inspect_repo(rp, include_branch_deltas=include_branch_deltas)
            for rp in repo_paths
        )
