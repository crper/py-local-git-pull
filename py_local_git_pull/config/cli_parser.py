"""
命令行参数解析模块

此模块负责解析和验证命令行参数。
"""

import argparse
import os
import re
import sys
from typing import Optional

from .constants import DefaultConfig


def is_valid_branch_name(branch: str) -> bool:
    """
    验证分支名是否合法

    Args:
        branch: 分支名

    Returns:
        bool: 分支名是否合法
    """
    return bool(re.match(r"^[A-Za-z0-9._\-/]+$", branch))


def _positive_int(value: str) -> int:
    """校验正整数参数（>=1）"""
    int_value = int(value)
    if int_value < 1:
        raise argparse.ArgumentTypeError("必须是大于等于 1 的整数")
    return int_value


def _non_negative_int(value: str) -> int:
    """校验非负整数参数（>=0）"""
    int_value = int(value)
    if int_value < 0:
        raise argparse.ArgumentTypeError("必须是大于等于 0 的整数")
    return int_value


def parse_args(args=None) -> Optional[argparse.Namespace]:
    """
    解析命令行参数

    Args:
        args: 命令行参数列表，默认为None（使用sys.argv）

    Returns:
        Optional[argparse.Namespace]: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description="同步本地Git仓库与远程仓库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 基本参数
    parser.add_argument("path", help="Git仓库路径，可以是单个仓库路径或包含多个仓库的目录")

    # 分支参数
    branch_group = parser.add_argument_group("分支选项")
    branch_group.add_argument(
        "-b",
        "--branch",
        help="要切换的分支名称。如果分支不存在，程序会根据设置决定是否创建并关联上游分支",
    )
    branch_group.add_argument("--branches", nargs="+", help="要拉取的多个分支名称，用空格分隔")
    branch_group.add_argument(
        "--auto-upstream",
        action="store_true",
        help="自动设置关联上游分支，如果本地分支没有关联远程分支",
        default=False,
    )
    branch_group.add_argument(
        "--skip-non-exist",
        action="store_true",
        help="跳过不存在于远程的分支",
        default=DefaultConfig.DEFAULT_SKIP_NON_EXIST,
    )

    # Git操作选项
    git_group = parser.add_argument_group("Git操作选项")
    git_group.add_argument(
        "--depth",
        type=_positive_int,
        help="指定fetch操作的深度，用于限制获取的提交历史数量。设置为1时只获取最新提交，适用于大仓库的快速同步",
        default=DefaultConfig.DEFAULT_DEPTH,
    )
    git_group.add_argument(
        "--no-stash",
        action="store_true",
        help="跳过stash操作，即使有未提交的更改也不会自动暂存。注意：这可能导致checkout失败",
        default=False,
    )

    # 搜索选项
    search_group = parser.add_argument_group("仓库搜索选项")
    search_group.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="递归搜索指定路径下的所有Git仓库",
        default=False,
    )
    search_group.add_argument(
        "--max-depth",
        type=_non_negative_int,
        help="递归搜索的最大深度，仅在使用--recursive参数时有效",
        default=DefaultConfig.DEFAULT_MAX_DEPTH,
    )

    # 输出选项
    output_group = parser.add_argument_group("输出选项")
    output_group.add_argument(
        "--verbose", "-v", action="store_true", help="显示详细日志信息", default=False
    )
    output_group.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="输出格式：table(默认) 或 json",
    )

    try:
        parsed_args = parser.parse_args(args)

        # 路径校验
        if not os.path.exists(parsed_args.path):
            print(f"错误: 路径 '{parsed_args.path}' 不存在")
            sys.exit(1)
        if not (os.path.isdir(parsed_args.path) or os.path.isfile(parsed_args.path)):
            print(f"错误: 路径 '{parsed_args.path}' 不是有效的文件夹或文件")
            sys.exit(1)
        parsed_args.path = os.path.abspath(parsed_args.path)

        # 分支参数一致性校验
        if parsed_args.branch and parsed_args.branches:
            print("警告: 同时指定了--branch和--branches参数，将优先使用--branches参数")

        # 分支名合法性校验
        if parsed_args.branch and not is_valid_branch_name(parsed_args.branch):
            print(f"错误: 分支名 '{parsed_args.branch}' 不合法")
            sys.exit(1)
        if parsed_args.branches:
            # 去重并保持顺序，避免重复同步同一分支
            parsed_args.branches = list(dict.fromkeys(parsed_args.branches))
            for b in parsed_args.branches:
                if not is_valid_branch_name(b):
                    print(f"错误: 分支名 '{b}' 不合法")
                    sys.exit(1)

        return parsed_args
    except (argparse.ArgumentError, SystemExit) as e:
        if isinstance(e, SystemExit):
            # 对于argparse内部的错误（如--help），直接抛出以正常退出
            raise
        print(f"参数错误: {str(e)}")
        parser.print_help()
        sys.exit(1)
    except Exception as e:
        print(f"解析参数时发生未知错误: {str(e)}")
        sys.exit(1)
