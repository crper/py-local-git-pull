"""Git 命令执行器

封装所有 Git 命令的执行逻辑，与业务逻辑分离。
"""

import subprocess
from typing import List, Optional, Tuple

from ..config.constants import GitConstants
from ..exceptions import GitCommandError


class GitExecutor:
    """
    Git 命令执行器

    负责执行 Git 命令并返回结果。
    """

    def __init__(self, repo_path: str):
        """
        初始化 Git 执行器

        Args:
            repo_path: Git 仓库路径
        """
        self.repo_path = repo_path

    def run(
        self,
        command: List[str],
        check: bool = True,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str, str]:
        """
        执行 Git 命令

        Args:
            command: 命令参数列表
            check: 是否检查命令执行状态
            timeout: 命令超时时间（秒），None 时使用默认值

        Returns:
            Tuple[int, str, str]: 返回码、标准输出、标准错误

        Raises:
            GitCommandError: 如果 check=True 且命令执行失败
        """
        full_command = ["git", "-C", self.repo_path] + command
        try:
            process = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout or GitConstants.DEFAULT_TIMEOUT_SECONDS,
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except subprocess.TimeoutExpired as e:
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=124,
                    stdout=(e.stdout or "").strip() if isinstance(e.stdout, str) else "",
                    stderr=(e.stderr or "").strip() if isinstance(e.stderr, str) else "",
                    timeout=True,
                ) from e
            return 124, "", f"Git命令执行超时: {' '.join(full_command)}"
        except subprocess.CalledProcessError as e:
            if check:
                raise GitCommandError(
                    command=" ".join(full_command),
                    returncode=e.returncode,
                    stdout=e.stdout.strip() if e.stdout else "",
                    stderr=e.stderr.strip() if e.stderr else "",
                ) from e
            stdout = e.stdout.strip() if e.stdout else ""
            stderr = e.stderr.strip() if e.stderr else str(e)
            return e.returncode, stdout, stderr
