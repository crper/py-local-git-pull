"""
显示模块

提供显示同步结果的功能。
"""

import logging
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.result_model import BranchDetail, SyncResult
from ..config.constants import BranchStatus

logger = logging.getLogger(__name__)


def _create_branch_display(branch_detail: BranchDetail, result: SyncResult) -> dict:
    """
    创建分支显示信息
    """
    branch_name = branch_detail.name
    is_current = branch_detail.is_current or branch_name == result.current_branch

    # 设置分支名称显示
    branch_display = f"[bold blue]{branch_name}" if is_current else branch_name

    # 设置已同步/跳过分支
    if branch_name in result.synced_branches:
        synced = branch_name
        skipped = "无"
    elif branch_name in result.skipped_branches:
        synced = "无"
        skipped = branch_name
    else:
        synced = "无"
        skipped = "无"

    return {
        "branch_display": branch_display,
        "synced": synced,
        "skipped": skipped,
    }


def _get_upstream_info(branch_detail: BranchDetail) -> Tuple[str, str]:
    """
    获取上游关联信息和 ahead/behind 信息
    """
    # 设置上游关联状态
    upstream_info = "[yellow]未关联"
    ahead_behind_info = "[blue]同步"  # 默认显示同步状态

    if branch_detail.has_upstream:
        upstream_name = branch_detail.upstream_name
        upstream_info = f"[green]已关联 ({upstream_name})"

        # 提取ahead/behind信息
        if branch_detail.ahead_behind:
            ahead = branch_detail.ahead_behind.ahead
            behind = branch_detail.ahead_behind.behind
            if ahead > 0 and behind > 0:
                ahead_behind_info = f"[yellow]领先{ahead}/落后{behind}"
            elif ahead > 0:
                ahead_behind_info = f"[green]领先{ahead}"
            elif behind > 0:
                ahead_behind_info = f"[red]落后{behind}"
            else:
                ahead_behind_info = "[blue]同步"
    elif branch_detail.auto_set_success:
        upstream_info = "[blue]自动关联成功"

    return upstream_info, ahead_behind_info


def _get_branch_details_text(branch_detail: BranchDetail) -> str:
    """
    获取分支详细信息文本
    """
    details = ""
    if branch_detail.error:
        details += f"错误: {branch_detail.error} "
    if branch_detail.status == BranchStatus.ERROR:
        details += "拉取失败 "
    elif branch_detail.status == BranchStatus.SKIPPED:
        details += "已跳过 "

    return details


def _add_branch_row_to_table(
    table: Table,
    result: SyncResult,
    branch_detail: BranchDetail,
    stashed: str,
) -> None:
    """
    添加分支行到表格
    """
    # 获取分支显示信息
    branch_info = _create_branch_display(branch_detail, result)

    # 获取上游信息
    upstream_info, ahead_behind_info = _get_upstream_info(branch_detail)

    # 获取详细信息
    details = _get_branch_details_text(branch_detail)

    # 添加行到表格
    table.add_row(
        result.repo_name,
        "[green]成功" if result.success else "[red]失败",
        branch_info["branch_display"],
        branch_info["synced"],
        branch_info["skipped"],
        upstream_info,
        ahead_behind_info,
        stashed,
        details,
    )


def _add_empty_branch_rows(
    table: Table,
    result: SyncResult,
    stashed: str,
) -> None:
    """
    添加空分支行到表格
    """
    current_branch = result.current_branch or "无"
    synced = ", ".join(result.synced_branches) if result.synced_branches else "无"
    skipped = ", ".join(result.skipped_branches) if result.skipped_branches else "无"

    # 设置上游关联状态
    upstream_info = "[green]已关联" if result.has_upstream else "[yellow]未关联"
    ahead_behind_info = "[blue]同步"

    # 设置详细信息
    details = f"错误: {result.error}" if result.error else ""

    table.add_row(
        result.repo_name,
        "[green]成功" if result.success else "[red]失败",
        current_branch,
        synced,
        skipped,
        upstream_info,
        ahead_behind_info,
        stashed,
        details,
    )


def _create_stats_text(results: List[SyncResult], success_count: int) -> Text:
    """
    创建统计信息文本
    """
    stats_text = Text()
    stats_text.append(f"总仓库数: {len(results)}\n", style="bold")
    stats_text.append(f"成功: {success_count}\n", style="bold green")

    fail_count = len(results) - success_count
    stats_text.append(
        f"失败: {fail_count}\n",
        style="bold red" if fail_count > 0 else "dim",
    )

    return stats_text


def create_result_table(results: List[SyncResult]) -> Tuple[Table, int]:
    """
    创建同步结果表格

    Args:
        results: 仓库同步结果列表

    Returns:
        Tuple[Table, int]: 表格对象和成功计数
    """
    # 创建结果表格
    table = Table(title="同步结果汇总", show_lines=True)
    table.add_column("仓库名", style="cyan")
    table.add_column("状态", justify="center")
    table.add_column("当前分支", style="blue")
    table.add_column("已同步分支", style="green")
    table.add_column("跳过分支", style="yellow")
    table.add_column("上游关联", justify="center")
    table.add_column("领先/落后", justify="center")
    table.add_column("Stash状态", justify="center")
    table.add_column("详细信息", style="dim")

    success_count = sum(1 for r in results if r.success)

    for result in results:
        # 增强Stash状态显示
        if result.stashed:
            stashed = "[green]已暂存"
        else:
            stashed = "[blue]无需暂存"

        # 处理每个分支的详细信息
        if result.branch_details:
            for branch_detail in result.branch_details:
                _add_branch_row_to_table(table, result, branch_detail, stashed)
        else:
            # 处理没有分支详情的情况
            _add_empty_branch_rows(table, result, stashed)

    return table, success_count


def display_sync_results(results: List[SyncResult], console: Console) -> None:
    """
    显示同步结果

    Args:
        results: 仓库同步结果列表
        console: 控制台对象
    """
    if not results:
        # 输出空表格或友好提示
        table = Table(title="同步结果汇总", show_lines=True)
        table.add_column("仓库名")
        table.add_column("状态")
        table.add_row("无", "[yellow]未找到可同步的Git仓库或分支")
        console.print(table)

        stats_text = Text()
        stats_text.append("总仓库数: 0\n", style="bold")
        stats_text.append("成功: 0\n", style="bold green")
        stats_text.append("失败: 0\n", style="dim")

        details_panel = Panel(stats_text, title="统计信息", border_style="green")
        console.print(details_panel)
        return

    # 创建并显示结果表格
    table, success_count = create_result_table(results)
    console.print(table)

    # 显示统计信息
    stats_text = _create_stats_text(results, success_count)

    # 添加详细信息面板
    details_panel = Panel(stats_text, title="统计信息", border_style="green")
    console.print(details_panel)
