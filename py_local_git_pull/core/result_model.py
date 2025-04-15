"""
结果数据模型模块

定义了同步操作的结果数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AheadBehind:
    """
    分支领先/落后信息
    """

    ahead: int = 0
    behind: int = 0


@dataclass
class BranchDetail:
    """
    分支详细信息
    """

    name: str
    status: str = "pending"  # pending, synced, skipped, error
    is_current: bool = False
    exists_locally: bool = True
    exists_remotely: bool = True
    has_upstream: bool = False
    upstream_name: Optional[str] = None
    auto_set_success: bool = False
    ahead_behind: Optional[AheadBehind] = None
    error: Optional[str] = None


@dataclass
class SyncResult:
    """
    仓库同步结果
    """

    repo_name: str
    path: str
    success: bool = True
    current_branch: Optional[str] = None
    stashed: bool = False
    synced_branches: List[str] = field(default_factory=list)
    skipped_branches: List[str] = field(default_factory=list)
    branch_details: List[BranchDetail] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_upstream(self) -> bool:
        """
        检查当前分支是否有上游关联
        """
        if not self.current_branch:
            return False

        for branch in self.branch_details:
            if branch.name == self.current_branch:
                return branch.has_upstream

        return False

    def to_dict(self) -> Dict:
        """
        转换为字典格式
        """
        return {
            "repo_name": self.repo_name,
            "path": self.path,
            "success": self.success,
            "branch": self.current_branch,
            "stashed": self.stashed,
            "has_upstream": self.has_upstream,
            "synced_branches": self.synced_branches,
            "skipped_branches": self.skipped_branches,
            "branch_details": [
                {
                    "name": b.name,
                    "status": b.status,
                    "is_current": b.is_current,
                    "exists_locally": b.exists_locally,
                    "exists_remotely": b.exists_remotely,
                    "has_upstream": b.has_upstream,
                    "upstream_name": b.upstream_name,
                    "auto_set_success": b.auto_set_success,
                    "ahead_behind": vars(b.ahead_behind) if b.ahead_behind else None,
                    "error": b.error,
                }
                for b in self.branch_details
            ],
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SyncResult":
        """
        从字典创建实例
        """
        result = cls(
            repo_name=data["repo_name"],
            path=data["path"],
            success=data["success"],
            current_branch=data.get("branch"),
            stashed=data.get("stashed", False),
            synced_branches=data.get("synced_branches", []),
            skipped_branches=data.get("skipped_branches", []),
            error=data.get("error"),
        )

        for branch_data in data.get("branch_details", []):
            ahead_behind = None
            if branch_data.get("ahead_behind"):
                ahead_behind = AheadBehind(
                    ahead=branch_data["ahead_behind"].get("ahead", 0),
                    behind=branch_data["ahead_behind"].get("behind", 0),
                )

            branch_detail = BranchDetail(
                name=branch_data["name"],
                status=branch_data.get("status", "pending"),
                is_current=branch_data.get("is_current", False),
                exists_locally=branch_data.get("exists_locally", True),
                exists_remotely=branch_data.get("exists_remotely", True),
                has_upstream=branch_data.get("has_upstream", False),
                upstream_name=branch_data.get("upstream_name"),
                auto_set_success=branch_data.get("auto_set_success", False),
                ahead_behind=ahead_behind,
                error=branch_data.get("error"),
            )
            result.branch_details.append(branch_detail)

        return result
