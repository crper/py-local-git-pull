# py-local-git-pull 全量重构设计

> **状态:** 草稿，待用户审阅
> **日期:** 2026-03-31
> **范围:** 架构、代码、CLI 体验全量重构

---

## 1. 背景与目标

### 1.1 当前问题

项目存在三类核心问题：

**架构层：**
- `GitManager` 是 595 行的上帝类，承担 7+ 种职责
- `GitManager` ↔ `BranchSyncer` 构造期循环依赖
- `result_model.py`（旧模型）与 `models.py`（新模型）并存，`BranchStatus` 同名但值不同
- `config/constants.py` 是 Java 风格反模式，AGENTS.md 标记 legacy 但仍有 6 个文件引用
- `RepoInspector` 直接 `GitManager(repo_path)` 构造，无法 mock

**代码层：**
- 类型注解不统一：旧式 `List/Optional` vs PEP 604 `list[str] | None`
- `get_branch_details` 每分支 3-4 次 subprocess 调用（N+1 问题）
- `configure_logging()` 从未被调用，日志系统形同虚设
- `stashed=False if no_stash else False`（git_manager.py:535）永远为 False
- 中英文混用：docstring、错误消息语言不一致

**CLI 体验层：**
- 缺少 `--dry-run`，同步操作无安全网
- 无进度条，多仓库同步时体验极差
- 无状态颜色/图标，`synced/failed/skipped` 全靠肉眼
- 缺少 `--verbose/-q`，无法控制输出详细度
- 缺少配置文件，每次重复传参
- `sync` 错误信息笼统："同步失败: {exc}"

### 1.2 重构目标

1. 消除架构硬伤（双模型、循环依赖、上帝类）
2. 引入现代化库提升代码质量
3. 全面改善 CLI 交互体验
4. 统一代码风格和类型注解
5. 补全测试覆盖

---

## 2. 技术选型

### 2.1 新增依赖

| 库 | 用途 | 替代 |
|---|---|---|
| `tenacity>=9.0.0` | 指数退避重试（fetch/pull） | 手动重试逻辑 |
| `structlog>=24.1.0` | 结构化日志 | `GitLogger` 薄包装 |
| `anyio>=4.0.0` | 异步并发调度 | 串行执行 |

### 2.2 内置能力（零新增依赖）

| 能力 | 来源 | 用途 |
|------|------|------|
| `tomllib` | Python 3.11+ 标准库 | 配置文件解析 |
| `rich.progress` | rich 内置 | 同步进度条 |
| `rich.table` | rich 内置 | 表格输出 |
| `rich.status` | rich 内置 | 实时状态指示 |
| `concurrent.futures` | 标准库 | 线程池回退 |

### 2.3 不引入的库

| 库 | 原因 |
|---|---|
| `GitPython` | subprocess 方案足够，GitPython 增加复杂度和版本绑定 |
| `pydantic` | 当前 `dataclass(frozen=True)` + `Enum` 组合已足够简洁 |
| `textual` | 项目定位为 CLI 工具，不需要 TUI |

---

## 3. 目标架构

### 3.1 目录结构

```
py_local_git_pull/
├── main.py                      # 入口：from .cli.app import app
├── __init__.py
├── __main__.py
│
├── cli/                         # CLI 层（原 commands/）
│   ├── app.py                   # Typer app + 全局选项 (-v/--quiet/--config)
│   ├── scan.py                  # scan 命令
│   ├── sync.py                  # sync 命令（加 --dry-run, --workers, --json）
│   └── doctor.py                # doctor 命令（加 --json）
│
├── core/                        # 业务逻辑层
│   ├── models.py                # 统一数据模型（保留现有 models.py，删除 result_model/sync_options）
│   │
│   ├── git/                     # Git 操作层（拆分 GitManager）
│   │   ├── runner.py            # 命令执行（原 git_executor.py + tenacity 重试）
│   │   ├── branch.py            # 分支操作（checkout、upstream、exists）
│   │   ├── stash.py             # Stash 操作
│   │   ├── remote.py            # 远程操作（fetch、pull）
│   │   └── info.py              # 信息收集（get_current_branch、has_changes、get_branch_details）
│   │
│   ├── services/                # 业务服务层
│   │   ├── sync_service.py      # 同步编排（原 GitManager.sync_repo* 逻辑）
│   │   ├── inspector.py         # 仓库检查（原 repo_inspector.py）
│   │   └── doctor_service.py    # 诊断服务
│   │
│   ├── discovery/               # 仓库发现
│   │   └── repo_finder.py       # 原 repo_finder.py
│   │
│   └── failure/                 # 失败分类
│       └── catalog.py           # 原 failure_catalog.py
│
├── ui/                          # 渲染层
│   ├── console.py               # Rich console 配置
│   ├── scan_view.py             # scan 输出（加 Rich Table）
│   ├── sync_view.py             # sync 输出（进度条、表格、颜色）
│   ├── doctor_view.py           # doctor 输出
│   └── interactive.py           # questionary 交互（原 prompts.py）
│
├── config/                      # 配置层（新增）
│   ├── settings.py              # tomllib 读取配置文件
│   └── defaults.py              # 默认值常量（原 constants.py 精简版）
│
├── utils/                       # 工具层
│   └── logging.py               # structlog 配置（原 logger.py + logging_config.py）
│
└── exceptions/                  # 异常层
    └── errors.py                # 精简异常定义
```

### 3.2 模块依赖图

```
cli/  ──────────────────────────────────────────────────────┐
  ├── core/services/  ──── core/git/                        │
  ├── core/discovery/ ──── core/git/                        │
  ├── core/failure/  (无外部依赖)                            │
  ├── ui/  ──── core/models.py                              │
  └── config/  (无外部依赖)                                  │
                                                             ▼
core/services/ ──── core/git/ + core/models + core/failure  │
core/git/      ──── core/models + config/defaults            │
core/discovery/──── core/models + core/git/info              │
core/failure/  ──── core/models                              │
                                                         无循环
```

所有依赖单向向下，无循环依赖。

---

## 4. 核心设计决策

### 4.1 统一数据模型

**决策：** 保留 `models.py` 中的新模型体系，删除 `result_model.py` 和 `sync_options.py`。

**理由：**
- `models.py` 的 `dataclass(frozen=True)` + `Enum` 组合已经足够清晰
- `result_model.py` 的 `SyncResult` 使用可变 `List`，与新模型不可变设计冲突
- `SyncOptions` 的 `from_cli_args` 引用了不存在的 `args.branches` 属性
- 两处 `BranchStatus` 同名但值不同（`ERROR` vs `FAILED`）

**迁移路径：**
- `SyncResult` → 由 `RepoOutcome` + `BranchOutcome` 替代
- `BranchDetail` → 由 `BranchInspection` + `BranchOutcome` 替代
- `AheadBehind` → 内联到 `BranchInspection` 的 `ahead`/`behind` 字段
- `SyncOptions` → CLI 参数直接传递，不需要中间模型

### 4.2 拆分 GitManager

**决策：** 将 595 行的 `GitManager` 拆分为 5 个职责单一的模块。

**拆分方案：**

| 新模块 | 职责 | 来源方法 |
|--------|------|---------|
| `core/git/runner.py` | 命令执行 | 原 `GitExecutor` |
| `core/git/branch.py` | 分支操作 | `checkout_branch`, `branch_exists_locally`, `branch_exists_remotely`, `set_upstream`, `get_current_branch` |
| `core/git/stash.py` | Stash 管理 | `stash_changes`, `pop_stash` |
| `core/git/remote.py` | 远程操作 | `fetch`, `pull` |
| `core/git/info.py` | 信息收集 | `has_changes`, `get_branch_details`, bare 检查 |

**依赖注入：**
```python
# 不再循环依赖，各模块通过 GitRunner 通信
class BranchOperations:
    def __init__(self, runner: GitRunner, repo_path: str):
        self._runner = runner
        self._repo_path = repo_path

class StashOperations:
    def __init__(self, runner: GitRunner, repo_path: str):
        self._runner = runner
        self._repo_path = repo_path
```

### 4.3 异步并发

**决策：** 使用 `anyio` 包装 `subprocess` 调用，支持多仓库并行同步。

**设计：**
```python
import anyio
from anyio import CapacityLimiter

async def sync_repo_async(
    inspection: RepoInspection,
    plan: RepoSyncPlan,
    *,
    auto_upstream: bool,
    skip_non_exist: bool,
    no_stash: bool,
    depth: int,
    limiter: CapacityLimiter,
) -> RepoOutcome:
    async with limiter:
        return await anyio.to_thread.run_sync(
            lambda: _sync_repo_sync(
                inspection, plan, auto_upstream, skip_non_exist, no_stash, depth
            )
        )

async def sync_all_repos(inspections, plans, *, workers: int, ...) -> list[RepoOutcome]:
    limiter = CapacityLimiter(workers)
    async with anyio.create_task_group() as tg:
        results = []
        for insp, plan in zip(inspections, plans):
            tg.start_soon(...)
    return results
```

**为什么用 `anyio.to_thread.run_sync` 而非原生 async subprocess：**
- Git 操作是 CPU-bound + I/O-bound 混合，subprocess 本身不阻塞 event loop
- `anyio` 提供统一的并发原语（CapacityLimiter、TaskGroup），比裸 `asyncio` 更安全
- 未来如需迁移到 Trio 也无需改业务代码

### 4.4 重试机制

**决策：** 使用 `tenacity` 为网络操作（fetch/pull）添加指数退避重试。

**设计：**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RemoteOperations:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GitCommandError),
        reraise=True,
    )
    def fetch(self, depth: int | None = None) -> bool:
        ...
```

### 4.5 配置文件

**决策：** 使用 `tomllib`（Python 3.11+ 内置）读取 `~/.config/py-local-git-pull/config.toml`。

**配置文件格式：**
```toml
[defaults]
recursive = true
max_depth = 5
branch = ["main"]
auto_upstream = true
skip_non_exist = true
no_stash = false
depth = 1
workers = 4

[paths]
work = "~/projects/work"
personal = "~/projects/personal"
```

**CLI 合并优先级：** CLI 参数 > 配置文件 > 代码默认值

### 4.6 结构化日志

**决策：** 使用 `structlog` 替代 `GitLogger`。

**设计：**
```python
import structlog

log = structlog.get_logger()

# 使用示例
log.info("sync_started", repo_name=repo_name, path=repo_path)
log.info("branch_synced", repo_name=repo_name, branch=branch, behind=3)
log.warning("sync_failed", repo_name=repo_name, failure_kind="fetch_failed")
```

**日志输出：**
- 开发模式：彩色控制台输出
- 生产模式：JSON 格式写入 `logs/git_sync.log`

### 4.7 CLI 体验改进

**新增全局选项（app.py）：**
```python
@app.callback()
def main(
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
    config: Annotated[Path | None, typer.Option("--config")] = None,
):
    ...
```

**sync 命令新增参数：**
```python
def sync_command(
    ...
    dry_run: Annotated[bool, typer.Option("--dry-run", "-n")] = False,
    workers: Annotated[int, typer.Option("--workers", "-w")] = 4,
    output: Annotated[str, typer.Option("--output")] = "table",
):
    ...
```

**进度条设计：**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("{task.completed}/{task.total}"),
) as progress:
    task = progress.add_task("Syncing repos...", total=len(inspections))
    for outcome in outcomes:
        progress.update(task, description=f"Syncing {outcome.repo_name}...")
        progress.advance(task)
```

**状态颜色：**
```python
STATUS_STYLE = {
    RepoStatus.SYNCED: "[green]✓ synced",
    RepoStatus.FAILED: "[red]✗ failed",
    RepoStatus.SKIPPED: "[yellow]⊘ skipped",
    RepoStatus.PARTIAL: "[orange]◐ partial",
}
```

---

## 5. 渐进式重构顺序

### Phase 1: 地基（可独立提交）

1. 安装新依赖（tenacity, structlog, anyio）
2. 创建新目录骨架（`cli/`, `core/git/`, `core/services/`, `core/discovery/`, `core/failure/`, `config/`）
3. 统一数据模型：删除 `result_model.py`、`sync_options.py`、`config/constants.py`
4. 精简异常定义：合并 `sync_exceptions.py` + `git_exceptions.py` → `exceptions/errors.py`
5. 创建 `config/defaults.py`：模块级常量替代类包裹常量

### Phase 2: 执行层（可独立提交）

6. 重写 `core/git/runner.py`：从 `git_executor.py` 迁移 + tenacity 重试装饰器
7. 拆分 `core/git/branch.py`：从 `GitManager` 提取分支操作
8. 拆分 `core/git/stash.py`：从 `GitManager` 提取 stash 操作
9. 拆分 `core/git/remote.py`：从 `GitManager` 提取 fetch/pull
10. 拆分 `core/git/info.py`：从 `GitManager` 提取信息收集
11. 重写 `core/services/sync_service.py`：编排层，DI 注入各操作模块
12. 修复 `stashed=False if no_stash else False` bug

### Phase 3: 并发层（可独立提交）

13. 重写 `core/services/sync_service.py` 添加 async 版本
14. 更新 `commands/sync.py` 使用 `anyio.run()` 调度并行同步
15. 添加 `--workers` 参数控制并发数

### Phase 4: CLI 体验（可独立提交）

16. 重写 `cli/app.py`：添加全局选项（-v, -q, --config）
17. 重写 `cli/sync.py`：添加 --dry-run, --json, --output
18. 重写 `cli/doctor.py`：添加 --json 输出
19. 重写 `ui/sync_view.py`：进度条、表格、状态颜色
20. 重写 `ui/scan_view.py`：Rich Table 替代 Panel
21. 创建 `config/settings.py`：配置文件读取

### Phase 5: 清理（可独立提交）

22. 统一类型注解为 PEP 604 风格
23. 统一错误消息为英文
24. 重写 `utils/logging.py`：structlog 配置
25. 删除旧文件（`config/`, `result_model.py`, `sync_options.py`, `commands/`, 旧 `utils/`）
26. 补全测试

---

## 6. 接口契约

### 6.1 GitRunner（命令执行）

```python
class GitRunner:
    def __init__(self, repo_path: str, timeout: int = 60): ...

    def run(
        self,
        command: list[str],
        *,
        check: bool = True,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """执行 git 命令，返回 (returncode, stdout, stderr)。"""
        ...
```

### 6.2 SyncService（同步编排）

```python
class SyncService:
    def __init__(
        self,
        runner: GitRunner,
        branch_ops: BranchOperations,
        stash_ops: StashOperations,
        remote_ops: RemoteOperations,
    ): ...

    def sync_repo(
        self,
        inspection: RepoInspection,
        plan: RepoSyncPlan,
        *,
        auto_upstream: bool,
        skip_non_exist: bool,
        no_stash: bool,
        depth: int,
    ) -> RepoOutcome:
        """同步单个仓库，返回结果。"""
        ...
```

### 6.3 RepoInspector（仓库检查）

```python
class RepoInspector:
    def __init__(self, runner: GitRunner): ...

    def inspect_repo(self, repo_path: str) -> RepoInspection: ...

    def inspect_path(
        self,
        path: str,
        *,
        recursive: bool,
        max_depth: int,
    ) -> tuple[RepoInspection, ...]: ...
```

### 6.4 配置文件 API

```python
@dataclass(frozen=True)
class AppSettings:
    recursive: bool = False
    max_depth: int = 3
    branch: tuple[str, ...] = ()
    auto_upstream: bool = False
    skip_non_exist: bool = True
    no_stash: bool = False
    depth: int = 1
    workers: int = 4

def load_settings(config_path: Path | None = None) -> AppSettings:
    """加载配置文件，合并默认值。"""
    ...
```

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 重构过程中破坏现有功能 | 高 | 每个 Phase 独立提交，可随时回退 |
| anyio 异步改造引入 bug | 中 | Phase 3 单独测试，保留同步回退路径 |
| structlog 日志格式变化 | 低 | 保持 JSON 输出兼容现有日志分析 |
| 新依赖安装失败 | 低 | tenacity/structlog/anyio 都是成熟库，pin 版本号 |

---

## 8. 成功标准

1. `ruff check .` 零报错
2. 所有现有测试通过
3. `scan`/`sync`/`doctor` 三个命令行为不变（向后兼容）
4. `--dry-run` 显示计划但不执行
5. 多仓库同步有进度条和状态颜色
6. 无循环依赖（`importlib` 检查通过）
7. `GitManager` 类不存在
