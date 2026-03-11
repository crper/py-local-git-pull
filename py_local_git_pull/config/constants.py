"""常量配置中心

集中管理所有硬编码的常量配置，提高代码可维护性。
"""

from enum import Enum
from typing import Final


# 分支状态枚举
class BranchStatus(str, Enum):
    """分支状态枚举"""
    PENDING = "pending"
    SYNCED = "synced"
    SKIPPED = "skipped"
    ERROR = "error"


# 同步结果状态枚举
class SyncStatus(str, Enum):
    """同步结果状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"


# Git 相关常量
class GitConstants:
    """Git 操作相关常量"""
    DEFAULT_REMOTE: Final[str] = "origin"
    BARE_REPO_VALUE: Final[str] = "true"
    HEAD_REF: Final[str] = "HEAD"
    DEFAULT_TIMEOUT_SECONDS: Final[int] = 60


# 日志相关常量
class LogConstants:
    """日志配置常量"""
    LOG_DIR: Final[str] = "logs"
    LOG_FILE: Final[str] = "git_sync.log"
    BACKUP_COUNT: Final[int] = 7
    WHEN: Final[str] = "midnight"


# 默认配置
class DefaultConfig:
    """默认配置"""
    DEFAULT_DEPTH: Final[int] = 1
    DEFAULT_MAX_DEPTH: Final[int] = 3
    DEFAULT_SKIP_NON_EXIST: Final[bool] = True
    DEFAULT_AUTO_UPSTREAM: Final[bool] = False
    DEFAULT_NO_STASH: Final[bool] = False
