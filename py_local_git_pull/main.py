"""
主模块

提供命令行入口点和主要功能流程。
"""

import logging
import os
import json
import sys
from typing import List

from rich.panel import Panel
from rich.text import Text
from rich.console import Console

from py_local_git_pull.config.cli_parser import parse_args
from py_local_git_pull.core import (
    GitManager,
    SyncOptions,
    SyncResult,
    find_git_repos,
    is_git_repo,
)
from py_local_git_pull.ui import create_progress, display_sync_results
from py_local_git_pull.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def format_results_json(results: List[SyncResult]) -> str:
    """
    将同步结果序列化为 JSON 字符串。
    """
    return json.dumps([result.to_dict() for result in results], ensure_ascii=False)


def git_sync(
    options: SyncOptions,
    main_console: Console | None = None,
    log_console: Console | None = None,
) -> List[SyncResult]:
    """
    执行Git仓库同步操作

    Args:
        options: 核心同步配置

    Returns:
        List[SyncResult]: 同步结果列表
    """
    if main_console is None or log_console is None:
        main_console, log_console = configure_logging()
    results = []
    render_ui = options.output != "json"

    try:
        # 确定要处理的仓库列表
        repos = []
        if options.recursive:
            # 递归查找Git仓库
            if render_ui:
                with main_console.status(f"[bold blue]正在搜索Git仓库 ({options.path})..."):
                    repos = find_git_repos(options.path, options.max_depth)
            else:
                repos = find_git_repos(options.path, options.max_depth)

            if not repos:
                if render_ui:
                    main_console.print(
                        f"[bold yellow]警告: 在路径 {options.path} 下未找到任何Git仓库"
                    )
                return []

            if render_ui:
                main_console.print(f"[bold green]找到 {len(repos)} 个Git仓库")
        else:
            # 单个仓库模式 - 非递归
            if is_git_repo(options.path):
                repos = [options.path]
            else:
                if render_ui:
                    main_console.print(f"[bold red]错误: 路径 {options.path} 不是Git仓库")
                if render_ui and os.path.isdir(options.path):
                    msg = (
                        "[bold yellow]提示: 如果要搜索该目录下的Git仓库，"
                        "请使用 --recursive 或 -r 参数"
                    )
                    main_console.print(msg)
                return []

        # 同步每个仓库，按输出模式决定是否渲染 Rich UI
        if render_ui:
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
                    result = git_manager.sync_repo(options)
                    results.append(result)

                    # 在仓库处理完成后添加更美观的分隔线
                    if repo_path != repos[-1]:  # 如果不是最后一个仓库
                        main_console.print(
                            Panel("", title="", border_style="dim", padding=0, height=1)
                        )

                    progress.advance(task)
        else:
            for repo_path in repos:
                git_manager = GitManager(repo_path, log_console)
                result = git_manager.sync_repo(options)
                results.append(result)

        return results

    except Exception as e:
        if render_ui:
            main_console.print_exception()
        logger.error(f"同步失败: {e}")
        return results


def main() -> None:
    """
    主函数

    负责初始化日志配置并启动同步流程。
    """
    # 解析命令行参数
    args = parse_args()
    if not args:
        return
    options = SyncOptions.from_cli_args(args)

    # 配置日志：
    # - verbose: DEBUG
    # - json 输出: 默认 WARNING，避免干扰结果消费
    # - 其他: INFO
    if options.verbose:
        log_level = logging.DEBUG
    elif options.output == "json":
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    main_console, log_console = configure_logging(log_level=log_level)

    if options.output != "json":
        # 显示欢迎信息
        welcome_text = Text()
        welcome_text.append("本地Git仓库同步工具\n", style="bold cyan")
        welcome_text.append(f"版本: {sys.modules['py_local_git_pull'].__version__}\n", style="dim")
        welcome_text.append(f"目标路径: {options.path}\n", style="bold green")

        if options.recursive:
            msg = f"递归模式: 是 (最大深度: {options.max_depth})\n"
            welcome_text.append(msg, style="bold green")
        else:
            welcome_text.append("递归模式: 否\n", style="dim")

        # 显示分支参数
        if options.branches:
            welcome_text.append(f"多分支模式: {', '.join(options.branches)}\n", style="bold green")
        elif options.branch:
            welcome_text.append(f"指定分支: {options.branch}\n", style="bold green")
        else:
            welcome_text.append("分支模式: 当前分支\n", style="dim")

        welcome_text.append(
            f"自动关联上游: {'是' if options.auto_upstream else '否'}\n", style="bold green"
        )

        if options.no_stash:
            welcome_text.append("跳过暂存: 是\n", style="bold yellow")

        welcome_text.append(f"获取深度: {options.depth}\n", style="bold green")
        main_console.print(Panel(welcome_text, title="配置信息", border_style="blue"))

    try:
        # 执行同步操作
        results = git_sync(options, main_console=main_console, log_console=log_console)

        if options.output == "json":
            print(format_results_json(results))
            return

        if not results:
            main_console.print("[bold yellow]没有找到可同步的Git仓库")
            return

        # 显示同步结果
        display_sync_results(results, main_console)
        main_console.print("[bold green]同步任务已完成，详细日志见 logs/git_sync.log")

    except Exception as e:
        if options.output != "json":
            main_console.print_exception()
        else:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        logger.error(f"同步失败: {e}")
        if options.output != "json":
            # 即使异常也输出空表格
            display_sync_results([], main_console)
            main_console.print("[bold red]同步任务异常终止，详细日志见 logs/git_sync.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
