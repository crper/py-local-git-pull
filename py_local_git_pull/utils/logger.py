"""统一日志工具

提供统一的日志记录接口，避免代码重复。
"""

import logging
from typing import Optional

from rich.console import Console


class GitLogger:
    """
    Git 操作日志记录器
    """

    def __init__(self, name: str, log_console: Optional[Console] = None):
        """
        初始化日志记录器

        Args:
            name: 日志记录器名称
            log_console: 日志控制台对象
        """
        self.logger = logging.getLogger(name)
        self.log_console = log_console

    def _log(self, level: int, message: str, color: str) -> None:
        """
        内部日志方法

        Args:
            level: 日志级别
            message: 日志消息
            color: Rich 颜色标签
        """
        # 统一交给 logging handler 输出，避免 RichHandler 和手动 print 双重输出。
        self.logger.log(level, message)

    def info(self, message: str) -> None:
        """
        记录信息日志

        Args:
            message: 日志消息
        """
        self._log(logging.INFO, message, "green")

    def warning(self, message: str) -> None:
        """
        记录警告日志

        Args:
            message: 日志消息
        """
        self._log(logging.WARNING, message, "yellow")

    def error(self, message: str) -> None:
        """
        记录错误日志

        Args:
            message: 日志消息
        """
        self._log(logging.ERROR, message, "red")
