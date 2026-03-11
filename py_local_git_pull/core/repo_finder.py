"""仓库查找器模块。"""

import logging
import os
import subprocess
from collections import deque
from pathlib import Path
from typing import Deque, List, Set, Tuple

logger = logging.getLogger(__name__)

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
}


def is_git_repo(path: str) -> bool:
    """
    检查指定路径是否为Git仓库

    Args:
        path: 要检查的路径

    Returns:
        bool: 是否为Git仓库
    """
    target = Path(path)
    if not target.exists() or not target.is_dir():
        return False

    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        # 仅当 path 为仓库根目录时视为“仓库路径”，避免把普通子目录识别成仓库。
        repo_root = Path(result.stdout.strip())
        return repo_root.resolve() == target.resolve()
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
    repos: Set[str] = set()
    root = Path(base_path).expanduser()
    logger.debug(f"开始在 {root} 中查找Git仓库，最大深度: {max_depth}")

    if not root.exists():
        logger.warning(f"路径 {root} 不存在")
        return []

    if root.is_file():
        parent_dir = root.parent
        return [str(parent_dir.resolve())] if is_git_repo(str(parent_dir)) else []

    if is_git_repo(str(root)):
        return [str(root.resolve())]

    queue: Deque[Tuple[Path, int]] = deque([(root, 0)])
    visited: Set[Path] = set()

    while queue:
        current, depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        if depth > max_depth:
            continue

        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if entry.name in SKIP_DIR_NAMES:
                        continue
                    if entry.name.startswith("."):
                        continue

                    sub_path = Path(entry.path)
                    if is_git_repo(str(sub_path)):
                        repos.add(str(sub_path.resolve()))
                        # 仓库目录不再继续向下扫描，避免重复和无效遍历。
                        continue

                    queue.append((sub_path, depth + 1))
        except (PermissionError, FileNotFoundError, NotADirectoryError) as e:
            logger.warning(f"无法访问目录 {current}: {e}")
        except Exception as e:
            logger.error(f"扫描目录 {current} 时发生未知错误: {e}")

    sorted_repos = sorted(repos)
    logger.debug(f"在 {root} 中找到总共 {len(sorted_repos)} 个Git仓库")
    return sorted_repos
