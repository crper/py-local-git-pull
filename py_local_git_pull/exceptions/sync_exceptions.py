"""同步操作相关异常"""


class SyncError(Exception):
    """同步操作错误"""
    def __init__(self, repo_path: str, reason: str):
        self.repo_path = repo_path
        self.reason = reason
        super().__init__(f"同步仓库 {repo_path} 失败: {reason}")


class BranchSyncError(Exception):
    """分支同步错误"""
    def __init__(self, branch: str, reason: str):
        self.branch = branch
        self.reason = reason
        super().__init__(f"同步分支 {branch} 失败: {reason}")
