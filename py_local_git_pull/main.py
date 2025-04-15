"""
主模块

提供命令行入口点和主要功能流程。
"""

import logging
import os
import sys
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from py_local_git_pull.config.cli_parser import parse_args
from py_local_git_pull.core import GitManager, SyncResult, find_git_repos, is_git_repo
from py_local_git_pull.ui import create_progress, display_sync_results
from py_local_git_pull.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def git_sync(args) -> List[SyncResult]:
    """
    执行Git仓库同步操作

    Args:
        args: 命令行参数

    Returns:
        List[SyncResult]: 同步结果列表
    """
    # 创建控制台对象
    main_console, log_console = configure_logging()
    results = []

    try:
        # 确定要处理的仓库列表
        repos = []
        if args.recursive:
            # 递归查找Git仓库
            with main_console.status(f"[bold blue]正在搜索Git仓库 ({args.path})..."):
                repos = find_git_repos(args.path, args.max_depth)

            if not repos:
                main_console.print(
                    f"[bold yellow]警告: 在路径 {args.path} 下未找到任何Git仓库"
                )
                return []

            main_console.print(f"[bold green]找到 {len(repos)} 个Git仓库")
        else:
            # 单个仓库模式 - 非递归
            if is_git_repo(args.path):
                repos = [args.path]
            else:
                main_console.print(f"[bold red]错误: 路径 {args.path} 不是Git仓库")
                if os.path.isdir(args.path):
                    main_console.print(
                        f"[bold yellow]提示: 如果要搜索该目录下的Git仓库，请使用 --recursive 或 -r 参数"
                    )
                return []

        # 同步每个仓库，使用更美观的进度条
        progress = create_progress(main_console, "同步Git仓库")

        with progress:
            task = progress.add_task("[cyan]同步Git仓库", total=len(repos))

            for repo_path in repos:
                repo_name = os.path.basename(repo_path)
                progress.update(task, description=f"[cyan]同步仓库 {repo_name}")

                # 使用Panel包装仓库信息，使界面更整洁
                main_console.print(
                    Panel(
                        f"正在处理仓库: {repo_name}",
                        title="[bold cyan]仓库同步[/bold cyan]",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )

                # 同步单个仓库
                git_manager = GitManager(repo_path, log_console)
                result = git_manager.sync_repo(args)
                results.append(result)

                # 在仓库处理完成后添加更美观的分隔线
                if repo_path != repos[-1]:  # 如果不是最后一个仓库
                    main_console.print(
                        Panel("", title="", border_style="dim", padding=0, height=1)
                    )

                progress.advance(task)

        return results

    except Exception as e:
        main_console.print_exception()
        logger.error(f"同步失败: {e}")
        return results


def main() -> None:
    """
    主函数

    负责初始化日志配置并启动同步流程。
    """
    # 配置日志
    main_console, _ = configure_logging()

    # 解析命令行参数
    args = parse_args()
    if not args:
        return

    # 显示欢迎信息
    welcome_text = Text()
    welcome_text.append("本地Git仓库同步工具\n", style="bold cyan")
    welcome_text.append(
        f"版本: {sys.modules['py_local_git_pull'].__version__}\n", style="dim"
    )
    welcome_text.append(f"目标路径: {args.path}\n", style="bold green")

    if args.recursive:
        welcome_text.append(
            f"递归模式: 是 (最大深度: {args.max_depth})\n", style="bold green"
        )
    else:
        welcome_text.append("递归模式: 否\n", style="dim")

    # 显示分支参数
    if args.branches:
        welcome_text.append(
            f"多分支模式: {', '.join(args.branches)}\n", style="bold green"
        )
    elif args.branch:
        welcome_text.append(f"指定分支: {args.branch}\n", style="bold green")
    else:
        welcome_text.append("分支模式: 当前分支\n", style="dim")

    welcome_text.append(
        f"自动关联上游: {'是' if args.auto_upstream else '否'}\n", style="bold green"
    )

    if args.no_stash:
        welcome_text.append(f"跳过暂存: 是\n", style="bold yellow")

    welcome_text.append(f"获取深度: {args.depth}\n", style="bold green")

    main_console.print(Panel(welcome_text, title="配置信息", border_style="blue"))

    try:
        # 执行同步操作
        results = git_sync(args)

        if not results:
            main_console.print("[bold yellow]没有找到可同步的Git仓库")
            return

        # 显示同步结果
        display_sync_results(results, main_console)
        main_console.print("[bold green]同步任务已完成，详细日志见 logs/git_sync.log")

    except Exception as e:
        main_console.print_exception()
        logger.error(f"同步失败: {e}")
        # 即使异常也输出空表格
        display_sync_results([], main_console)
        main_console.print("[bold red]同步任务异常终止，详细日志见 logs/git_sync.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
