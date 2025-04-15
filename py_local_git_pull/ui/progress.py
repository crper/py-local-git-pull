"""
进度显示模块

提供用于显示进度的功能。
"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

logger = logging.getLogger(__name__)


def create_progress(console: Console, description: str = "处理中") -> Progress:
    """
    创建一个进度条对象

    Args:
        console: 控制台对象
        description: 进度条描述

    Returns:
        Progress: 进度条对象
    """
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=50),  # 固定进度条宽度
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed}/{task.total}"),  # 添加完成计数
        console=console,
        expand=True,  # 确保进度条占满整个宽度
        refresh_per_second=10,  # 提高刷新率，使进度条更流畅
    )


def create_status_panel(title: str, message: str, style: str = "blue") -> Panel:
    """
    创建一个状态面板

    Args:
        title: 面板标题
        message: 面板内容
        style: 面板样式

    Returns:
        Panel: 面板对象
    """
    return Panel(
        message,
        title=f"[bold {style}]{title}[/bold {style}]",
        border_style=style,
        padding=(1, 2),
    )
