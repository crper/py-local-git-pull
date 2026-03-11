"""分支同步器

封装分支同步的核心逻辑，从 GitManager 中拆分。
"""

from typing import Optional

from .result_model import BranchDetail, SyncResult
from .sync_options import SyncOptions
from ..config.constants import BranchStatus


class BranchSyncer:
    """
    分支同步器

    负责处理单个分支的同步逻辑。
    """

    def __init__(self, git_manager):
        """
        初始化分支同步器

        Args:
            git_manager: GitManager 实例
        """
        self.git_manager = git_manager

    def sync_single_branch(
        self,
        branch: str,
        options: SyncOptions,
        result: SyncResult,
        is_current: bool = False,
    ) -> Optional[BranchDetail]:
        """
        同步单个分支

        Args:
            branch: 分支名
            options: 核心同步配置
            result: 同步结果对象
            is_current: 是否为当前分支

        Returns:
            Optional[BranchDetail]: 分支详情对象
        """
        branch_detail = BranchDetail(
            name=branch,
            status=BranchStatus.PENDING,
        )
        branch_detail.is_current = is_current

        # 检查分支是否存在
        branch_detail.exists_locally = self.git_manager.branch_exists_locally(branch)
        branch_detail.exists_remotely = self.git_manager.branch_exists_remotely(branch)

        # 本地和远程都不存在，直接跳过
        if not branch_detail.exists_locally and not branch_detail.exists_remotely:
            self.git_manager.logger.warning(f"分支 {branch} 在本地和远程都不存在，跳过")
            result.skipped_branches.append(branch)
            branch_detail.status = BranchStatus.SKIPPED
            branch_detail.error = "分支不存在"
            return branch_detail

        # 远程不存在时按参数策略处理
        if not branch_detail.exists_remotely and options.skip_non_exist:
            self.git_manager.logger.warning(f"远程分支 origin/{branch} 不存在，按参数跳过")
            result.skipped_branches.append(branch)
            branch_detail.status = BranchStatus.SKIPPED
            branch_detail.error = "远程分支不存在"
            return branch_detail

        # 切换到分支（如果不是当前分支）
        if not is_current:
            success, error = self.git_manager.checkout_branch(
                branch,
                create_if_not_exist=branch_detail.exists_remotely,
            )
            if not success:
                result.skipped_branches.append(branch)
                branch_detail.status = BranchStatus.ERROR
                branch_detail.error = error
                result.mark_failed(error)
                return branch_detail

        # 设置上游分支
        has_upstream, upstream_name, error = self.git_manager.set_upstream(
            branch, options.auto_upstream
        )
        branch_detail.has_upstream = has_upstream
        branch_detail.upstream_name = upstream_name

        if error:
            branch_detail.error = error

        # 如果有上游分支，执行 pull 操作
        if has_upstream:
            success, pull_error = self.git_manager.pull()
            if success:
                branch_detail.status = BranchStatus.SYNCED
                result.synced_branches.append(branch)
            else:
                branch_detail.status = BranchStatus.ERROR
                branch_detail.error = pull_error
                result.skipped_branches.append(branch)
                result.mark_failed(branch_detail.error)
        else:
            branch_detail.status = BranchStatus.SKIPPED
            if not branch_detail.error:
                branch_detail.error = "无上游分支"
            result.skipped_branches.append(branch)

        return branch_detail
