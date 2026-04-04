"""Shared task-console models."""

from dataclasses import dataclass
from enum import Enum


class RepoStatus(str, Enum):
    SYNCED = "synced"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    FAILED = "failed"


class BranchStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    SKIPPED = "skipped"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskFlag(str, Enum):
    HAS_LOCAL_CHANGES = "has_local_changes"
    DETACHED_HEAD = "detached_head"
    NO_UPSTREAM = "no_upstream"
    REMOTE_BRANCH_MISSING = "remote_branch_missing"
    BARE_REPOSITORY = "bare_repository"
    UNKNOWN_STATE = "unknown_state"


class FailureKind(str, Enum):
    DIRTY_WORKTREE = "dirty_worktree"
    STASH_FAILED = "stash_failed"
    FETCH_FAILED = "fetch_failed"
    CHECKOUT_FAILED = "checkout_failed"
    UPSTREAM_MISSING = "upstream_missing"
    REMOTE_BRANCH_MISSING = "remote_branch_missing"
    PULL_FF_CONFLICT = "pull_ff_conflict"
    PULL_REJECTED = "pull_rejected"
    BARE_REPOSITORY = "bare_repository"
    REPO_NOT_FOUND = "repo_not_found"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_GIT_ERROR = "unknown_git_error"


class PlanAction(str, Enum):
    SYNC_CURRENT = "sync_current"
    SYNC_BRANCHES = "sync_branches"
    SKIP = "skip"


class StashStrategy(str, Enum):
    NONE = "none"
    AUTO_STASH = "auto_stash"
    USER_DISABLED = "user_disabled"


class PolicyMode(str, Enum):
    SAFE = "safe"
    CAREFUL = "careful"
    FORCE = "force"


class RunEventType(str, Enum):
    RUN_STARTED = "run_started"
    REPO_QUEUED = "repo_queued"
    REPO_BLOCKED = "repo_blocked"
    REPO_STARTED = "repo_started"
    REPO_COMPLETED = "repo_completed"
    REPO_FAILED = "repo_failed"
    RUN_COMPLETED = "run_completed"


@dataclass(frozen=True)
class SuggestedAction:
    label: str
    command: str | None
    description: str
    auto_fixable: bool = False


@dataclass(frozen=True)
class FailureRecord:
    kind: FailureKind
    summary: str
    detail: str | None
    raw_error: str | None
    can_auto_fix: bool
    suggested_actions: tuple[SuggestedAction, ...] = ()


@dataclass(frozen=True)
class BranchInspection:
    name: str
    is_current: bool
    exists_locally: bool
    exists_remotely: bool
    has_upstream: bool
    upstream_name: str | None
    ahead: int | None
    behind: int | None


@dataclass(frozen=True)
class RepoInspection:
    repo_name: str
    path: str
    current_branch: str | None
    is_git_repo: bool
    is_bare: bool
    has_changes: bool
    has_untracked_changes: bool
    detached_head: bool
    branches: tuple[BranchInspection, ...]
    risk_level: RiskLevel
    risk_flags: tuple[RiskFlag, ...]


@dataclass(frozen=True)
class RepoSyncPlan:
    repo_name: str
    path: str
    target_branches: tuple[str, ...]
    action: PlanAction
    stash_strategy: StashStrategy
    will_skip: bool
    skip_reason: str | None
    needs_attention: bool
    attention_reason: str | None


@dataclass(frozen=True)
class BranchOutcome:
    name: str
    status: BranchStatus
    is_current: bool
    has_upstream: bool
    upstream_name: str | None
    ahead: int | None
    behind: int | None
    failure: FailureRecord | None = None


@dataclass(frozen=True)
class RepoOutcome:
    repo_name: str
    path: str
    status: RepoStatus
    current_branch: str | None
    target_branches: tuple[str, ...]
    synced_branches: tuple[str, ...]
    skipped_branches: tuple[str, ...]
    stashed: bool
    branch_outcomes: tuple[BranchOutcome, ...] = ()
    failure: FailureRecord | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunEvent:
    run_id: str
    event_type: RunEventType
    ts: str
    repo_name: str | None = None
    repo_path: str | None = None
    message: str | None = None
    status: str | None = None
    failure_kind: str | None = None


@dataclass(frozen=True)
class RunSummary:
    synced: int
    partial: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    command: str
    path: str
    policy: PolicyMode
    started_at: str
    finished_at: str | None
    events: tuple[RunEvent, ...]
    outcomes: tuple[RepoOutcome, ...]
    summary: RunSummary


@dataclass(frozen=True)
class SyncOptions:
    auto_upstream: bool = False
    skip_non_exist: bool = False
    depth: int = 1
