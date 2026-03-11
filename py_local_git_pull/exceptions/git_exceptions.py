"""Git 操作相关异常"""


class GitCommandError(Exception):
    """Git 命令执行错误"""

    def __init__(
        self,
        command: str,
        stderr: str = "",
        stdout: str = "",
        returncode: int | None = None,
        timeout: bool = False,
    ):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timeout = timeout

        detail = stderr or stdout or "未知错误"
        code_part = f" (code={returncode})" if returncode is not None else ""
        timeout_part = " [timeout]" if timeout else ""
        super().__init__(f"Git命令执行失败{timeout_part}{code_part}: {command}; {detail}")


class GitBranchNotFoundError(Exception):
    """Git 分支未找到错误"""
    def __init__(self, branch: str):
        self.branch = branch
        super().__init__(f"分支 {branch} 不存在")


class GitCheckoutError(Exception):
    """Git 切换分支错误"""
    def __init__(self, branch: str, reason: str):
        self.branch = branch
        self.reason = reason
        super().__init__(f"切换到分支 {branch} 失败: {reason}")


class GitPullError(Exception):
    """Git 拉取错误"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"拉取更新失败: {reason}")


class GitFetchError(Exception):
    """Git 获取错误"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"获取远程更新失败: {reason}")


class GitStashError(Exception):
    """Git Stash 操作错误"""
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(f"Stash {operation} 失败: {reason}")
