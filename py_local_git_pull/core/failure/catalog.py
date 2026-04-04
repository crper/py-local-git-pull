"""Map raw git failures to user-facing categories."""

from py_local_git_pull.core.models import (
    FailureKind,
    FailureRecord,
    RepoInspection,
    RiskFlag,
    SuggestedAction,
)

_GIT_ERROR_FETCH_FAILED = "fetch failed"
_GIT_ERROR_NO_UPSTREAM = "no upstream"
_GIT_ERROR_NOT_FAST_FORWARD = "not possible to fast-forward"


def classify_git_failure(raw_error: str | None) -> FailureRecord:
    """Classify a raw git error into a structured failure record."""
    text = (raw_error or "").lower()

    if "fetch failed" in text:
        return FailureRecord(
            kind=FailureKind.FETCH_FAILED,
            summary="fetch failed before sync could start",
            detail="The remote could not be fetched successfully.",
            raw_error=raw_error,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="retry_fetch",
                    command=None,
                    description="verify network, auth, and remote URL, then retry the sync",
                    auto_fixable=False,
                ),
            ),
        )

    if "no upstream" in text:
        return FailureRecord(
            kind=FailureKind.UPSTREAM_MISSING,
            summary="current branch has no upstream",
            detail="The branch is not tracking a remote branch.",
            raw_error=raw_error,
            can_auto_fix=True,
            suggested_actions=(
                SuggestedAction(
                    label="set_upstream",
                    command=None,
                    description="rerun with --auto-upstream or set upstream manually",
                    auto_fixable=True,
                ),
            ),
        )

    if _GIT_ERROR_NOT_FAST_FORWARD in text:
        return FailureRecord(
            kind=FailureKind.PULL_FF_CONFLICT,
            summary="fast-forward only pull cannot continue",
            detail="Local and remote history diverged.",
            raw_error=raw_error,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="inspect_divergence",
                    command=None,
                    description="inspect local history and choose rebase, merge, or reset",
                    auto_fixable=False,
                ),
            ),
        )

    return FailureRecord(
        kind=FailureKind.UNKNOWN_GIT_ERROR,
        summary="git command failed",
        detail="The error did not match a known failure pattern.",
        raw_error=raw_error,
        can_auto_fix=False,
        suggested_actions=(
            SuggestedAction(
                label="rerun_manually",
                command=None,
                description="rerun the relevant git command manually to inspect full stderr",
                auto_fixable=False,
            ),
        ),
    )


def diagnose_inspection(inspection: RepoInspection) -> FailureRecord | None:
    """Derive a failure record from inspection risk flags."""
    if RiskFlag.NO_UPSTREAM in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.UPSTREAM_MISSING,
            summary="current branch has no upstream",
            detail="At least one local branch is not tracking a remote branch.",
            raw_error=None,
            can_auto_fix=True,
            suggested_actions=(
                SuggestedAction(
                    label="rerun_auto_upstream",
                    command="py-local-git-pull sync <path> --auto-upstream",
                    description="rerun sync and let the tool set upstream automatically",
                    auto_fixable=True,
                ),
            ),
        )

    if RiskFlag.REMOTE_BRANCH_MISSING in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.REMOTE_BRANCH_MISSING,
            summary="remote branch is missing",
            detail="A local branch does not exist on the configured remote.",
            raw_error=None,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="verify_remote_branch",
                    command="git branch -r",
                    description="verify the remote branch list before rerunning sync",
                    auto_fixable=False,
                ),
            ),
        )

    if RiskFlag.HAS_LOCAL_CHANGES in inspection.risk_flags:
        return FailureRecord(
            kind=FailureKind.DIRTY_WORKTREE,
            summary="local changes need review before sync",
            detail="The repo has local modifications or untracked files.",
            raw_error=None,
            can_auto_fix=False,
            suggested_actions=(
                SuggestedAction(
                    label="inspect_status",
                    command=f"git -C {inspection.path} status",
                    description="inspect local changes before choosing stash or commit",
                    auto_fixable=False,
                ),
            ),
        )

    return None
