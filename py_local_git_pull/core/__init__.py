"""核心功能模块"""

from .git_manager import GitManager
from .repo_finder import find_git_repos, is_git_repo
from .result_model import SyncResult, BranchDetail

__all__ = [
    "GitManager",
    "find_git_repos",
    "is_git_repo",
    "SyncResult",
    "BranchDetail",
]
