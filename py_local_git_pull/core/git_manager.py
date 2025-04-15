"""
Git管理器模块

提供Git操作的核心功能。
"""

import logging
import os
import subprocess
from argparse import Namespace
from typing import List, Optional, Tuple

from rich.console import Console

from .result_model import AheadBehind, BranchDetail, SyncResult

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
        
    def log_info(self, message: str) -> None:
        """
        记录信息日志
        
        Args:
            message: 日志消息
        """
        logger.info(message)
        if self.log_console:
            self.log_console.print(f"[green]信息: {message}")
            
    def log_warning(self, message: str) -> None:
        """
        记录警告日志
        
        Args:
            message: 日志消息
        """
        logger.warning(message)
        if self.log_console:
            self.log_console.print(f"[yellow]警告: {message}")
            
    def log_error(self, message: str) -> None:
        """
        记录错误日志
        
        Args:
            message: 日志消息
        """
        logger.error(message)
        if self.log_console:
            self.log_console.print(f"[red]错误: {message}")
    
    def run_git_command(self, command: List[str], check: bool = True) -> Tuple[int, str, str]:
        """
        执行Git命令
        
        Args:
            command: 命令参数列表
            check: 是否检查命令执行状态
            
        Returns:
            Tuple[int, str, str]: 返回码、标准输出、标准错误
            
        Raises:
            subprocess.CalledProcessError: 如果check=True且命令执行失败
        """
        try:
            full_command = ["git", "-C", self.repo_path] + command
            process = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check,
            )
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except subprocess.CalledProcessError as e:
            if check:
                raise
            return e.returncode, "", e.stderr.strip() if e.stderr else str(e)
            
    def get_current_branch(self) -> str:
        """
        获取当前分支名
        
        Returns:
            str: 当前分支名
        """
        _, stdout, _ = self.run_git_command(["branch", "--show-current"])
        return stdout
        
    def has_changes(self) -> bool:
        """
        检查是否有未提交的更改
        
        Returns:
            bool: 是否有未提交的更改
        """
        _, stdout, _ = self.run_git_command(["status", "--porcelain"], check=False)
        return bool(stdout)
        
    def stash_changes(self) -> bool:
        """
        暂存未提交的更改
        
        Returns:
            bool: 是否成功暂存
        """
        try:
            # 检查是否存在初始提交
            has_commits = self.run_git_command(["rev-parse", "--verify", "HEAD"], check=False)[0] == 0
            
            if not has_commits:
                self.log_warning(f"仓库 {self.repo_name} 没有初始提交，跳过stash操作")
                return False
                
            self.run_git_command(["stash"])
            self.log_info(f"在仓库 {self.repo_name} 中暂存了本地更改")
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"暂存本地更改失败: {e}")
            return False
            
    def pop_stash(self) -> bool:
        """
        恢复暂存的更改
        
        Returns:
            bool: 是否成功恢复
        """
        try:
            # 检查是否有stash
            _, stdout, _ = self.run_git_command(["stash", "list"], check=False)
            if not stdout:
                self.log_warning(f"仓库 {self.repo_name} 没有可恢复的stash，跳过恢复操作")
                return False
                
            self.run_git_command(["stash", "pop"])
            self.log_info(f"在仓库 {self.repo_name} 中恢复了暂存的本地更改")
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"恢复暂存的本地更改失败: {e}")
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
                
            self.run_git_command(command)
            self.log_info(f"在仓库 {self.repo_name} 中完成Git fetch操作")
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"Git fetch操作失败: {e}")
            return False
            
    def branch_exists_locally(self, branch: str) -> bool:
        """
        检查分支是否存在于本地
        
        Args:
            branch: 分支名
            
        Returns:
            bool: 分支是否存在
        """
        _, stdout, _ = self.run_git_command(["branch", "--list", branch], check=False)
        return bool(stdout)
        
    def branch_exists_remotely(self, branch: str) -> bool:
        """
        检查分支是否存在于远程
        
        Args:
            branch: 分支名
            
        Returns:
            bool: 分支是否存在
        """
        returncode, stdout, _ = self.run_git_command(
            ["ls-remote", "--heads", "origin", branch], 
            check=False
        )
        return returncode == 0 and bool(stdout)
        
    def checkout_branch(self, branch: str, create_if_not_exist: bool = True) -> Tuple[bool, Optional[str]]:
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
                self.run_git_command(["checkout", branch])
                self.log_info(f"切换到分支: {branch}")
                return True, None
            elif create_if_not_exist and self.branch_exists_remotely(branch):
                self.run_git_command(["checkout", "-b", branch, f"origin/{branch}"])
                self.log_info(f"创建并切换到分支: {branch}")
                return True, None
            else:
                error_msg = f"分支 {branch} 不存在"
                self.log_warning(error_msg)
                return False, error_msg
        except subprocess.CalledProcessError as e:
            error_msg = str(e)
            self.log_error(f"切换分支失败: {error_msg}")
            return False, error_msg
            
    def set_upstream(self, branch: str, auto_upstream: bool = False) -> Tuple[bool, str, Optional[str]]:
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
            returncode, stdout, _ = self.run_git_command(
                ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"],
                check=False
            )
            
            # 如果已设置上游分支，返回成功
            if returncode == 0:
                upstream = stdout
                self.log_info(f"分支 {branch} 已关联上游分支: {upstream}")
                return True, upstream, None
                
            # 如果未设置上游分支且不自动设置，返回失败
            if not auto_upstream:
                self.log_warning(f"分支 {branch} 未关联上游分支，且未启用自动关联")
                return False, "", None
                
            # 检查远程分支是否存在
            if not self.branch_exists_remotely(branch):
                error_msg = f"远程分支 origin/{branch} 不存在"
                self.log_warning(f"{error_msg}，无法设置上游分支")
                return False, "", error_msg
                
            # 设置上游分支
            self.run_git_command(["branch", f"--set-upstream-to=origin/{branch}", branch])
            upstream = f"origin/{branch}"
            self.log_info(f"成功设置分支 {branch} 的上游分支为 {upstream}")
            return True, upstream, None
        except subprocess.CalledProcessError as e:
            error_msg = str(e)
            self.log_error(f"设置上游分支失败: {error_msg}")
            return False, "", error_msg
            
    def pull(self) -> Tuple[bool, Optional[str]]:
        """
        执行pull操作
        
        Returns:
            Tuple[bool, Optional[str]]: 是否成功和错误信息
        """
        try:
            self.run_git_command(["pull"])
            self.log_info(f"成功同步当前分支")
            return True, None
        except subprocess.CalledProcessError as e:
            error_msg = str(e)
            self.log_error(f"拉取更新失败: {error_msg}")
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
        _, local_branches_output, _ = self.run_git_command(["branch", "--list"], check=False)
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
                status="pending",
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
                    _, output, _ = self.run_git_command(
                        ["rev-list", "--left-right", "--count", f"{branch_name}...{upstream_name}"],
                        check=False
                    )
                    if output:
                        counts = output.split("\t")
                        if len(counts) == 2:
                            branch_detail.ahead_behind = AheadBehind(
                                ahead=int(counts[0]),
                                behind=int(counts[1]),
                            )
                except (subprocess.CalledProcessError, ValueError):
                    # 如果无法获取ahead/behind信息，保持为None
                    pass
                    
            branch_details.append(branch_detail)
            
        return branch_details
    
    def sync_repo(self, args: Namespace) -> SyncResult:
        """
        同步仓库
        
        Args:
            args: 命令行参数
            
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
        
        try:
            # 检查仓库状态
            is_bare = False
            returncode, stdout, _ = self.run_git_command(["rev-parse", "--is-bare-repository"], check=False)
            if returncode == 0 and stdout == "true":
                is_bare = True
                self.log_warning(f"仓库 {self.repo_name} 是裸仓库，将跳过stash等操作")
                
            # 执行fetch操作
            if not self.fetch(args.depth):
                result.success = False
                result.error = "Fetch操作失败"
                return result
                
            # 处理本地更改
            stashed = False
            if not is_bare and self.has_changes() and not args.no_stash:
                stashed = self.stash_changes()
                result.stashed = stashed
                
            # 根据参数选择操作模式
            if args.branches:
                # 多分支模式
                self._sync_multiple_branches(args, result)
            elif args.branch:
                # 单一指定分支模式
                self._sync_single_branch(args.branch, args, result)
            else:
                # 当前分支模式
                self._sync_current_branch(args, result)
                
            # 恢复原始分支
            if current_branch and current_branch != self.get_current_branch():
                success, error = self.checkout_branch(current_branch, False)
                if not success:
                    self.log_warning(f"无法返回原始分支 {current_branch}: {error}")
                    
            # 恢复暂存的更改
            if stashed:
                self.pop_stash()
                
            return result
            
        except Exception as e:
            self.log_error(f"同步仓库 {self.repo_name} 时发生错误: {e}")
            result.success = False
            result.error = str(e)
            return result
            
    def _sync_current_branch(self, args: Namespace, result: SyncResult) -> None:
        """
        同步当前分支
        
        Args:
            args: 命令行参数
            result: 同步结果对象
        """
        branch = self.get_current_branch()
        if not branch:
            self.log_error("无法确定当前分支")
            result.success = False
            result.error = "无法确定当前分支"
            return
            
        branch_detail = BranchDetail(
            name=branch,
            is_current=True,
            status="pending",
        )
        
        # 设置上游分支
        has_upstream, upstream_name, error = self.set_upstream(branch, args.auto_upstream)
        branch_detail.has_upstream = has_upstream
        branch_detail.upstream_name = upstream_name
        
        if error:
            branch_detail.error = error
            
        if has_upstream:
            # 执行pull操作
            success, pull_error = self.pull()
            if success:
                result.synced_branches.append(branch)
                branch_detail.status = "synced"
            else:
                result.skipped_branches.append(branch)
                branch_detail.status = "error"
                branch_detail.error = pull_error
                result.success = False
                result.error = pull_error
        else:
            result.skipped_branches.append(branch)
            branch_detail.status = "skipped"
            branch_detail.error = "无上游分支"
            
        result.branch_details.append(branch_detail)
        
    def _sync_single_branch(self, branch: str, args: Namespace, result: SyncResult) -> None:
        """
        同步单个指定分支
        
        Args:
            branch: 分支名
            args: 命令行参数
            result: 同步结果对象
        """
        # 检查分支是否存在
        branch_detail = BranchDetail(
            name=branch,
            status="pending",
        )
        
        # 检查分支是否存在于本地
        branch_detail.exists_locally = self.branch_exists_locally(branch)
        
        # 检查分支是否存在于远程
        branch_detail.exists_remotely = self.branch_exists_remotely(branch)
        
        # 如果分支不存在于本地也不存在于远程，跳过
        if not branch_detail.exists_locally and not branch_detail.exists_remotely:
            self.log_warning(f"分支 {branch} 在本地和远程都不存在，跳过切换")
            result.skipped_branches.append(branch)
            branch_detail.status = "skipped"
            branch_detail.error = "分支不存在"
            result.branch_details.append(branch_detail)
            return
            
        # 切换到分支
        success, error = self.checkout_branch(branch, True)
        if not success:
            result.skipped_branches.append(branch)
            branch_detail.status = "error"
            branch_detail.error = error
            result.branch_details.append(branch_detail)
            return
            
        # 标记为当前分支
        branch_detail.is_current = True
        
        # 设置上游分支
        has_upstream, upstream_name, error = self.set_upstream(branch, args.auto_upstream)
        branch_detail.has_upstream = has_upstream
        branch_detail.upstream_name = upstream_name
        
        if error:
            branch_detail.error = error
            
        if has_upstream:
            # 执行pull操作
            success, pull_error = self.pull()
            if success:
                result.synced_branches.append(branch)
                branch_detail.status = "synced"
            else:
                result.skipped_branches.append(branch)
                branch_detail.status = "error"
                branch_detail.error = pull_error
                result.success = False
                result.error = pull_error
        else:
            result.skipped_branches.append(branch)
            branch_detail.status = "skipped"
            branch_detail.error = "无上游分支"
            
        result.branch_details.append(branch_detail)
        
    def _sync_multiple_branches(self, args: Namespace, result: SyncResult) -> None:
        """
        同步多个分支
        
        Args:
            args: 命令行参数
            result: 同步结果对象
        """
        if not args.branches:
            return
            
        # 记录原始分支，用于操作结束后恢复
        original_branch = self.get_current_branch()
        
        for branch in args.branches:
            branch_detail = BranchDetail(
                name=branch,
                status="pending",
            )
            
            # 检查分支是否存在于本地
            branch_detail.exists_locally = self.branch_exists_locally(branch)
            
            # 检查分支是否存在于远程
            branch_detail.exists_remotely = self.branch_exists_remotely(branch)
            
            # 如果远程分支不存在，跳过
            if not branch_detail.exists_remotely:
                self.log_warning(f"远程分支 origin/{branch} 不存在，跳过")
                result.skipped_branches.append(branch)
                branch_detail.status = "skipped"
                branch_detail.error = "远程分支不存在"
                result.branch_details.append(branch_detail)
                continue
                
            # 如果本地分支不存在且配置了跳过不存在的分支
            if not branch_detail.exists_locally and args.skip_non_exist:
                self.log_warning(f"本地分支 {branch} 不存在，跳过")
                result.skipped_branches.append(branch)
                branch_detail.status = "skipped"
                branch_detail.error = "本地分支不存在"
                result.branch_details.append(branch_detail)
                continue
                
            # 切换到分支
            success, error = self.checkout_branch(branch, not args.skip_non_exist)
            if not success:
                result.skipped_branches.append(branch)
                branch_detail.status = "error"
                branch_detail.error = error
                result.branch_details.append(branch_detail)
                continue
                
            # 标记为当前分支
            branch_detail.is_current = True
            
            # 设置上游分支
            has_upstream, upstream_name, error = self.set_upstream(branch, args.auto_upstream)
            branch_detail.has_upstream = has_upstream
            branch_detail.upstream_name = upstream_name
            
            if error:
                branch_detail.error = error
                
            if has_upstream:
                # 执行pull操作
                success, pull_error = self.pull()
                if success:
                    result.synced_branches.append(branch)
                    branch_detail.status = "synced"
                else:
                    result.skipped_branches.append(branch)
                    branch_detail.status = "error"
                    branch_detail.error = pull_error
            else:
                result.skipped_branches.append(branch)
                branch_detail.status = "skipped"
                branch_detail.error = "无上游分支"
                
            result.branch_details.append(branch_detail)
            
        # 恢复原始分支
        if original_branch:
            success, _ = self.checkout_branch(original_branch, False)
            if not success:
                self.log_warning(f"无法返回原始分支 {original_branch}")
                # 在这里不设置result.success = False，因为这只是一个次要错误