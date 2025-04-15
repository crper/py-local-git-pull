"""
仓库查找器模块

提供查找Git仓库的功能。
"""

import logging
import os
import subprocess
from typing import List

logger = logging.getLogger(__name__)


def is_git_repo(path: str) -> bool:
    """
    检查指定路径是否为Git仓库

    Args:
        path: 要检查的路径

    Returns:
        bool: 是否为Git仓库
    """
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except subprocess.SubprocessError as e:
        logger.debug(f"检查Git仓库时出错: {e}")
        return False


def find_git_repos(base_path: str, max_depth: int = 3) -> List[str]:
    """
    递归查找指定路径下的所有Git仓库

    Args:
        base_path: 基础路径
        max_depth: 最大递归深度

    Returns:
        List[str]: 找到的Git仓库路径列表
    """
    repos = []
    logger.debug(f"开始在 {base_path} 中查找Git仓库，最大深度: {max_depth}")

    # 检查路径是否存在并且可访问
    if not os.path.exists(base_path):
        logger.warning(f"路径 {base_path} 不存在")
        return repos

    if not os.path.isdir(base_path):
        logger.warning(f"路径 {base_path} 不是目录")
        # 如果是文件，检查它的父目录是否是Git仓库
        parent_dir = os.path.dirname(base_path)
        if is_git_repo(parent_dir):
            repos.append(parent_dir)
        return repos

    # 检查基础路径是否为Git仓库
    if is_git_repo(base_path):
        logger.debug(f"找到Git仓库: {base_path}")
        repos.append(base_path)
        return repos  # 如果基础路径是Git仓库，直接返回

    # 如果达到最大深度，停止递归
    if max_depth <= 0:
        logger.debug(f"达到最大递归深度，停止在 {base_path} 中搜索")
        return repos

    # 递归搜索子目录
    try:
        logger.debug(f"递归搜索 {base_path} 的子目录 (当前深度: {max_depth})")
        with os.scandir(base_path) as entries:
            for entry in entries:
                # 跳过隐藏目录和文件
                if entry.name.startswith("."):
                    continue

                if entry.is_dir():
                    sub_path = entry.path
                    try:
                        # 先检查子目录是否是Git仓库
                        if is_git_repo(sub_path):
                            logger.debug(f"找到Git仓库: {sub_path}")
                            repos.append(sub_path)
                        else:
                            # 递归查找子目录中的仓库，减少深度
                            sub_repos = find_git_repos(sub_path, max_depth - 1)
                            if sub_repos:
                                logger.debug(
                                    f"在子目录 {sub_path} 中找到 {len(sub_repos)} 个Git仓库"
                                )
                                repos.extend(sub_repos)
                    except (PermissionError, FileNotFoundError) as e:
                        logger.warning(f"无法访问子目录 {sub_path}: {e}")
    except (PermissionError, FileNotFoundError, NotADirectoryError) as e:
        logger.warning(f"无法访问目录 {base_path}: {e}")
    except Exception as e:
        logger.error(f"查找Git仓库时发生未知错误: {e}")

    logger.debug(f"在 {base_path} 中找到总共 {len(repos)} 个Git仓库")
    return repos
