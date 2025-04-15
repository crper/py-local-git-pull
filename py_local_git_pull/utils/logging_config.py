"""
日志配置模块

配置日志系统，提供统一的日志格式和输出方式。
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Tuple

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.traceback import install


def configure_logging(
    log_dir: str = "logs", log_level: int = logging.INFO
) -> Tuple[Console, Console]:
    """
    配置日志系统

    Args:
        log_dir: 日志文件目录
        log_level: 日志级别

    Returns:
        Tuple[Console, Console]: 主控制台和日志控制台
    """
    # 安装Rich的异常处理
    install()

    # 创建自定义主题，使日志颜色更加协调
    custom_theme = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "debug": "dim",
            "success": "bold green",
        }
    )

    # 创建主控制台，用于UI显示
    main_console = Console(theme=custom_theme)

    # 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 创建一个单独的日志控制台，输出到stderr，避免与进度条混杂
    log_console = Console(stderr=True, highlight=False, style="dim")

    # 配置日志系统
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # 使用自定义的RichHandler，将日志输出到stderr
            RichHandler(
                console=log_console,
                rich_tracebacks=True,
                markup=True,
                show_time=False,
                show_path=False,
            ),
            # 文件日志处理器
            logging.handlers.TimedRotatingFileHandler(
                log_path / "git_sync.log",
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            ),
        ],
    )

    # 设置第三方库的日志级别更高，减少干扰
    logging.getLogger("git").setLevel(logging.WARNING)

    return main_console, log_console
