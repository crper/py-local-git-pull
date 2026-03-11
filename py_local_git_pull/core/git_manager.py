"""
Git管理器模块

提供Git操作的核心功能。
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Set, Tuple

from rich.console import Console

from .git_executor import GitExecutor
from .branch_syncer import BranchSyncer
from .result_model import AheadBehind, BranchDetail, SyncResult
from .sync_options import SyncOptions
from ..config.constants import GitConstants, BranchStatus
from ..exceptions import GitCommandError
from ..utils.logger import GitLogger

logger = logging.getLogger(__name__)


class GitManager:
    """
    Git操作管理器

    负责处理Git仓库的各种操作，包括分支切换、拉取更新等。
    """

    def __init__(self, repo_path: str, log_console: Optional[Console] = None):
        """
        初始化Git管理器

        Args:
            repo_path: 仓库路径
            log_console: 日志控制台
        """
        self.repo_path = repo_path
        self.repo_name = os.path.basename(repo_path)
        self.log_console = log_console
        self.logger = GitLogger(__name__, log_console)
        self.executor = GitExecutor(repo_path)
        self.branch_syncer = BranchSyncer(self)
        self._managed_stash_ref: Optional[str] = None
        self._remote_branches_cache: Optional[Set[str]] = None

    @staticmethod
    def _format_git_error(error: Exception) -> str:
        """统一格式化 Git 异常信息。"""
        if isinstance(error, GitCommandError):
            return error.stderr or error.stdout or str(error)
        return str(error)

    def _invalidate_remote_cache(self) -> None:
        self._remote_branches_cache = None

    def _load_remote_branches_cache(self) -> bool:
        """
        读取远程分支缓存（基于本地 refs/remotes 数据）。
        """
        returncode, stdout, stderr = self.executor.run(
            [
                "for-each-ref",
                "--format=%(refname:short)",
                f"refs/remotes/{GitConstants.DEFAULT_REMOTE}",
            ],
            check=False,
        )
        if returncode != 0:
            self.logger.warning(f"读取远程分支缓存失败: {stderr or stdout}")
            return False

        prefix = f"{GitConstants.DEFAULT_REMOTE}/"
        branches: Set[str] = set()
        for line in stdout.splitlines():
            ref_name = line.strip()
            if not ref_name.startswith(prefix):
                continue
            branch = ref_name[len(prefix) :]
            if not branch or branch == "HEAD":
                continue
            branches.add(branch)

        self._remote_branches_cache = branches
        return True


    def get_current_branch(self) -> str:
        """
        获取当前分支名

        Returns:
            str: 当前分支名
        """
        _, stdout, _ = self.executor.run(["branch", "--show-current"])
        return stdout

    def has_changes(self) -> bool:
        """
        检查是否有未提交的更改

        Returns:
            bool: 是否有未提交的更改
        """
        _, stdout, _ = self.executor.run(["status", "--porcelain"], check=False)
        return bool(stdout)

    def stash_changes(self) -> bool:
        """
        暂存未提交的更改

        Returns:
            bool: 是否成功暂存
        """
        try:
            # 检查是否存在初始提交
            has_commits = self.executor.run(
                ["rev-parse", "--verify", GitConstants.HEAD_REF],
                check=False,
            )[0] == 0

            if not has_commits:
                self.logger.warning(f"仓库 {self.repo_name} 没有初始提交，跳过stash操作")
                return False

            stash_message = f"py-local-git-pull:{self.repo_name}:{datetime.now().isoformat()}"
            _, stdout, _ = self.executor.run(
                ["stash", "push", "--include-untracked", "-m", stash_message]
            )
            if "No local changes to save" in stdout:
                return False

            returncode, stash_list, _ = self.executor.run(["stash", "list"], check=False)
            if returncode == 0:
                for line in stash_list.splitlines():
                    if stash_message in line:
                        self._managed_stash_ref = line.split(":")[0]
                        break

            self.logger.info(f"在仓库 {self.repo_name} 中暂存了本地更改")
            return True
        except GitCommandError as e:
            self.logger.error(f"暂存本地更改失败: {self._format_git_error(e)}")
            return False

    def pop_stash(self) -> bool:
        """
        恢复暂存的更改

        Returns:
            bool: 是否成功恢复
        """
        try:
            if not self._managed_stash_ref:
                return False

            # 精确恢复本次创建的 stash，避免误恢复到历史记录。
            self.executor.run(["stash", "pop", self._managed_stash_ref])
            self.logger.info(f"在仓库 {self.repo_name} 中恢复了暂存的本地更改")
            self._managed_stash_ref = None
            return True
        except GitCommandError as e:
            self.logger.error(f"恢复暂存的本地更改失败: {self._format_git_error(e)}")
            return False

    def fetch(self, depth: Optional[int] = None) -> bool:
        """
        执行fetch操作

        Args:
            depth: 获取深度，None表示获取全部历史

        Returns:
            bool: 是否成功
        """
        try:
            command = ["fetch"]
            if depth:
                command.extend(["--depth", str(depth)])

            self.executor.run(command)
            self._invalidate_remote_cache()
            self._load_remote_branches_cache()
            self.logger.info(f"在仓库 {self.repo_name} 中完成Git fetch操作")
            return True
        except GitCommandError as e:
            self.logger.error(f"Git fetch操作失败: {self._format_git_error(e)}")
            return False

    def branch_exists_locally(self, branch: str) -> bool:
        """
        检查分支是否存在于本地

        Args:
            branch: 分支名

        Returns:
            bool: 分支是否存在
        """
        _, stdout, _ = self.executor.run(["branch", "--list", branch], check=False)
        return bool(stdout)

    def branch_exists_remotely(self, branch: str) -> bool:
        """
        检查分支是否存在于远程

        Args:
            branch: 分支名

        Returns:
            bool: 分支是否存在
        """
        if self._remote_branches_cache is not None:
            return branch in self._remote_branches_cache

        if self._load_remote_branches_cache():
            return branch in (self._remote_branches_cache or set())

        # 缓存不可用时回退到实时查询。
        returncode, stdout, _ = self.executor.run(
            ["ls-remote", "--heads", GitConstants.DEFAULT_REMOTE, branch], check=False
        )
        exists = returncode == 0 and bool(stdout)
        if exists and self._remote_branches_cache is not None:
            self._remote_branches_cache.add(branch)
        return exists

    def checkout_branch(
        self, branch: str, create_if_not_exist: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        切换到指定分支

        Args:
            branch: 分支名
            create_if_not_exist: 如果分支不存在是否创建

        Returns:
            Tuple[bool, Optional[str]]: 是否成功和错误信息
        """
        try:
            if self.branch_exists_locally(branch):
                self.executor.run(["checkout", branch])
                self.logger.info(f"切换到分支: {branch}")
                return True, None
            elif create_if_not_exist and self.branch_exists_remotely(branch):
                self.executor.run(
                    ["checkout", "-b", branch, f"{GitConstants.DEFAULT_REMOTE}/{branch}"]
                )
                self.logger.info(f"创建并切换到分支: {branch}")
                return True, None
            else:
                error_msg = f"分支 {branch} 不存在"
                self.logger.warning(error_msg)
                return False, error_msg
        except GitCommandError as e:
            error_msg = self._format_git_error(e)
            self.logger.error(f"切换分支失败: {error_msg}")
            return False, error_msg

    def set_upstream(
        self, branch: str, auto_upstream: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        设置分支的上游分支

        Args:
            branch: 分支名
            auto_upstream: 是否自动设置上游分支

        Returns:
            Tuple[bool, str, Optional[str]]: 是否有上游分支、上游分支名称和错误信息
        """
        try:
            # 检查是否已设置上游分支
            returncode, stdout, _ = self.executor.run(
                ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"],
                check=False,
            )

            # 如果已设置上游分支，返回成功
            if returncode == 0:
                upstream = stdout
                self.logger.info(f"分支 {branch} 已关联上游分支: {upstream}")
                return True, upstream, None

            # 如果未设置上游分支且不自动设置，返回失败
            if not auto_upstream:
                return False, "", None

            # 检查远程分支是否存在
            if not self.branch_exists_remotely(branch):
                error_msg = f"远程分支 {GitConstants.DEFAULT_REMOTE}/{branch} 不存在"
                self.logger.warning(f"{error_msg}，无法设置上游分支")
                return False, "", error_msg

            # 设置上游分支
            self.executor.run(
                [
                    "branch",
                    f"--set-upstream-to={GitConstants.DEFAULT_REMOTE}/{branch}",
                    branch,
                ]
            )
            upstream = f"{GitConstants.DEFAULT_REMOTE}/{branch}"
            self.logger.info(f"成功设置分支 {branch} 的上游分支为 {upstream}")
            return True, upstream, None
        except GitCommandError as e:
            error_msg = self._format_git_error(e)
            self.logger.error(f"设置上游分支失败: {error_msg}")
            return False, "", error_msg

    def pull(self) -> Tuple[bool, Optional[str]]:
        """
        执行pull操作

        Returns:
            Tuple[bool, Optional[str]]: 是否成功和错误信息
        """
        try:
            self.executor.run(["pull", "--ff-only"])
            self.logger.info("成功同步当前分支")
            return True, None
        except GitCommandError as e:
            error_msg = self._format_git_error(e)
            self.logger.error(f"拉取更新失败: {error_msg}")
            return False, error_msg

    def get_branch_details(self) -> List[BranchDetail]:
        """
        获取所有分支的详细信息

        Returns:
            List[BranchDetail]: 分支详细信息列表
        """
        branch_details = []
        current_branch = self.get_current_branch()

        # 获取本地分支列表
        _, local_branches_output, _ = self.executor.run(["branch", "--list"], check=False)
        if not local_branches_output:
            return branch_details

        # 解析分支输出
        local_branches = []
        for line in local_branches_output.split("\n"):
            if line.strip():
                # 去除前导的'*'和空格
                branch_name = line.strip()
                if branch_name.startswith("* "):
                    branch_name = branch_name[2:]
                local_branches.append(branch_name)

        # 处理每个分支
        for branch_name in local_branches:
            is_current = branch_name == current_branch

            branch_detail = BranchDetail(
                name=branch_name,
                is_current=is_current,
                exists_locally=True,
                status=BranchStatus.PENDING,
            )

            # 检查远程分支是否存在
            branch_detail.exists_remotely = self.branch_exists_remotely(branch_name)

            # 检查是否有上游分支
            has_upstream, upstream_name, error = self.set_upstream(branch_name, False)
            branch_detail.has_upstream = has_upstream
            branch_detail.upstream_name = upstream_name

            # 如果有上游分支，获取ahead/behind信息
            if has_upstream:
                try:
                    _, output, _ = self.executor.run(
                        ["rev-list", "--left-right", "--count", f"{branch_name}...{upstream_name}"],
                        check=False,
                    )
                    if output:
                        counts = output.split("\t")
                        if len(counts) == 2:
                            branch_detail.ahead_behind = AheadBehind(
                                ahead=int(counts[0]),
                                behind=int(counts[1]),
                            )
                except (GitCommandError, ValueError):
                    # 如果无法获取ahead/behind信息，保持为None
                    pass

            branch_details.append(branch_detail)

        return branch_details

    def sync_repo(self, options: SyncOptions) -> SyncResult:
        """
        同步仓库

        Args:
            options: 核心同步配置

        Returns:
            SyncResult: 同步结果
        """
        # 初始化结果对象
        result = SyncResult(
            repo_name=self.repo_name,
            path=self.repo_path,
        )

        # 记录当前分支，用于操作结束后恢复
        current_branch = self.get_current_branch()
        result.current_branch = current_branch

        stashed = False
        try:
            # 检查仓库状态
            is_bare = False
            returncode, stdout, _ = self.executor.run(
                ["rev-parse", "--is-bare-repository"], check=False
            )
            if returncode == 0 and stdout == GitConstants.BARE_REPO_VALUE:
                is_bare = True
                self.logger.warning(f"仓库 {self.repo_name} 是裸仓库，将跳过stash等操作")

            # 执行fetch操作
            if not self.fetch(options.depth):
                result.mark_failed("Fetch操作失败")
                return result

            # 处理本地更改
            if not is_bare and self.has_changes() and not options.no_stash:
                stashed = self.stash_changes()
                result.stashed = stashed

            # 根据参数选择操作模式
            if options.branches:
                # 多分支模式
                self._sync_multiple_branches(options, result)
            elif options.branch:
                # 单一指定分支模式
                self._sync_single_branch(options.branch, options, result)
            else:
                # 当前分支模式
                self._sync_current_branch(options, result)

            return result

        except Exception as e:
            self.logger.error(f"同步仓库 {self.repo_name} 时发生错误: {e}")
            result.mark_failed(str(e))
            return result
        finally:
            if current_branch:
                try:
                    active_branch = self.get_current_branch()
                    if active_branch and current_branch != active_branch:
                        success, error = self.checkout_branch(current_branch, False)
                        if not success:
                            self.logger.warning(f"无法返回原始分支 {current_branch}: {error}")
                except Exception as restore_branch_error:
                    self.logger.error(f"恢复原始分支失败: {restore_branch_error}")

            if stashed and not options.no_stash:
                self.pop_stash()

    def _sync_current_branch(self, options: SyncOptions, result: SyncResult) -> None:
        """
        同步当前分支

        Args:
            options: 核心同步配置
            result: 同步结果对象
        """
        branch = self.get_current_branch()
        if not branch:
            self.logger.error("无法确定当前分支")
            result.mark_failed("无法确定当前分支")
            return

        branch_detail = self.branch_syncer.sync_single_branch(
            branch, options, result, is_current=True
        )
        if branch_detail:
            result.branch_details.append(branch_detail)

    def _sync_single_branch(
        self,
        branch: str,
        options: SyncOptions,
        result: SyncResult,
    ) -> None:
        """
        同步单个指定分支

        Args:
            branch: 分支名
            options: 核心同步配置
            result: 同步结果对象
        """
        branch_detail = self.branch_syncer.sync_single_branch(branch, options, result)
        if branch_detail:
            result.branch_details.append(branch_detail)

    def _sync_multiple_branches(self, options: SyncOptions, result: SyncResult) -> None:
        """
        同步多个分支

        Args:
            options: 核心同步配置
            result: 同步结果对象
        """
        if not options.branches:
            return

        for branch in options.branches:
            # 使用 branch_syncer 同步
            sync_result = self.branch_syncer.sync_single_branch(
                branch, options, result
            )
            if sync_result:
                result.branch_details.append(sync_result)
