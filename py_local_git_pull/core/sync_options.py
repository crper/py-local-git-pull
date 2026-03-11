"""同步选项模型。"""

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from ..config.constants import DefaultConfig


@dataclass(frozen=True)
class SyncOptions:
    """
    核心同步配置。

    与 argparse 解耦，便于测试和后续 API 复用。
    """

    path: str
    recursive: bool = False
    max_depth: int = DefaultConfig.DEFAULT_MAX_DEPTH
    branch: Optional[str] = None
    branches: Tuple[str, ...] = ()
    auto_upstream: bool = DefaultConfig.DEFAULT_AUTO_UPSTREAM
    skip_non_exist: bool = DefaultConfig.DEFAULT_SKIP_NON_EXIST
    depth: int = DefaultConfig.DEFAULT_DEPTH
    no_stash: bool = DefaultConfig.DEFAULT_NO_STASH
    verbose: bool = False
    output: str = "table"

    @classmethod
    def from_cli_args(cls, args: Any) -> "SyncOptions":
        """
        从 CLI 参数对象构建 SyncOptions。
        """
        return cls(
            path=args.path,
            recursive=bool(args.recursive),
            max_depth=int(args.max_depth),
            branch=args.branch,
            branches=tuple(args.branches or ()),
            auto_upstream=bool(args.auto_upstream),
            skip_non_exist=bool(args.skip_non_exist),
            depth=int(args.depth),
            no_stash=bool(args.no_stash),
            verbose=bool(args.verbose),
            output=str(args.output),
        )
