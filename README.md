# py-local-git-pull

一个纯 CLI 的 Git 任务控制台，用来扫描、同步、诊断一批本地仓库，并记录每次同步运行的事件与结果。

## 功能特点

- **任务式 CLI**：命令模型是 `scan / sync / doctor / runs`
- **多仓库支持**：可以指定单仓库，也可以递归扫描目录下所有仓库
- **多分支支持**：`-b/--branch` 可重复传入多个目标分支
- **风险预检**：`scan` 会先识别 dirty worktree、缺失 upstream、裸仓库等风险
- **事件驱动同步**：`sync` 通过事件流执行，并默认输出 `PLAN / EXECUTION / SUMMARY / NEXT ACTIONS`
- **现代化交互选择**：`sync --interactive` 支持轻控制台式仓库选择、风险预览、推荐动作排序
- **策略化执行**：支持 `--policy safe|careful|force`
- **基于证据的诊断**：`doctor` 默认优先诊断最近一次失败运行，可用 `--last` 或 `--run`
- **可机读输出**：支持 `--output json` 和 `--output jsonl`
- **阶段耗时观测**：`sync --profile-inspect` 可显示 inspection / picker / execution 阶段耗时
- **运行历史**：`runs list` / `runs show <run-id>` 可查看历史同步结果和单次运行详情
- **更严谨的同步策略**：`pull --ff-only` 避免隐式合并
- **跨平台兼容**：支持 macOS、Linux、Windows

## 系统要求

- Python 3.13 或更高版本
- Git 命令行工具

## 快速开始

### 在仓库里直接运行，最省脑子

如果你只是刚 clone 下来，想立刻试一下，不要直接敲：

```bash
py-local-git-pull scan ~/code
```

也不要默认直接敲：

```bash
python -m py_local_git_pull scan ~/code
```

因为这时依赖通常还没有进入当前 Python 环境。最稳的做法是始终走 `uv run`：

```bash
git clone https://github.com/crper/py-local-git-pull.git
cd py-local-git-pull
uv sync --group dev

uv run py-local-git-pull scan ~/code -r
uv run py-local-git-pull sync ~/code -r -b main --policy safe
uv run py-local-git-pull doctor ~/code --last
uv run py-local-git-pull runs list
uv run python -m py_local_git_pull --help
```

### 安装成全局命令，最适合日常使用

```bash
uv tool install git+https://github.com/crper/py-local-git-pull.git

# 安装后可以直接运行
py-local-git-pull scan ~/code -r
```

如果你已经安装过旧版本：

```bash
uv tool upgrade py-local-git-pull
```

## 安装

### 安装到当前环境

```bash
# 推荐
uv pip install git+https://github.com/crper/py-local-git-pull.git

# 或者
pip install git+https://github.com/crper/py-local-git-pull.git
```

### 本地可编辑安装

```bash
# 克隆仓库
git clone https://github.com/crper/py-local-git-pull.git
cd py-local-git-pull

# 安装到当前虚拟环境
uv pip install -e .

# 或者
pip install -e .
```

## 使用方法

### 基本命令

如果你已经用 `uv tool install ...` 装成了全局命令，可以直接运行 `py-local-git-pull ...`。  
如果你是在仓库里开发或只是临时试用，请默认写成 `uv run py-local-git-pull ...`。

```bash
py-local-git-pull scan /path/to/repos -r
py-local-git-pull sync /path/to/repo
py-local-git-pull doctor /path/to/repos
py-local-git-pull runs list
```

### 常见示例

```bash
# 递归扫描一批仓库，先看风险
py-local-git-pull scan /path/to/repos -r

# 同步单个仓库当前分支
py-local-git-pull sync /path/to/repo

# 使用安全策略同步一批仓库
py-local-git-pull sync /path/to/repos -r --policy safe

# 同步多个分支
py-local-git-pull sync /path/to/repos -r -b main -b develop

# 进入交互选择模式，只同步选中的仓库
py-local-git-pull sync /path/to/repos -r --interactive

# 查看 interactive / inspection / execution 各阶段耗时
py-local-git-pull sync /path/to/repos -r --interactive --profile-inspect

# 自动补 upstream 后再同步
py-local-git-pull sync /path/to/repo --auto-upstream

# 输出 JSON
py-local-git-pull scan /path/to/repos -r --output json
py-local-git-pull scan /path/to/repos -r --output jsonl
py-local-git-pull sync /path/to/repo --output json
py-local-git-pull sync /path/to/repo --output jsonl
py-local-git-pull sync /path/to/repos -r --interactive --profile-inspect --output json

# 优先诊断最近一次运行中的失败项
py-local-git-pull doctor /path/to/repos --last
py-local-git-pull doctor /path/to/repos --run 20260401T103012Z
py-local-git-pull doctor /path/to/repos --repo demo-api

# 查看运行历史
py-local-git-pull runs list
py-local-git-pull runs show 20260401T103012Z-abcdef12
```

### 关键参数

| 参数 | 说明 |
| --- | --- |
| `path` | Git 仓库路径，或包含多个仓库的目录 |
| `-b, --branch` | 目标分支，可重复传入 |
| `-r, --recursive` | 递归搜索指定路径下所有 Git 仓库 |
| `--max-depth` | 递归最大深度 |
| `--policy` | 执行策略，支持 `safe`、`careful`、`force` |
| `--auto-upstream` | 缺失 upstream 时自动设置 |
| `--skip-non-exist` | 跳过不存在于远程的分支 |
| `--no-stash` | 禁用自动 stash |
| `--depth` | `fetch` 深度 |
| `--interactive` | 交互式选择要同步的仓库 |
| `--profile-inspect` | 输出 lightweight inspect / picker / full inspect / execution 阶段耗时 |
| `--output` | `table`、`json` 或 `jsonl` |
| `--verbose` | 展开更详细的排障信息 |

## 输出风格

- `scan`：预检和风险摘要
- `sync`：事件驱动任务输出，包含 `PLAN / EXECUTION / SUMMARY / NEXT ACTIONS`
- `doctor`：优先读取最近一次运行的失败证据，再给出问题解释和下一步建议
- `runs`：列出历史运行，或查看单次运行详情

如果使用 `--output json`，会输出 schema v3 的结构化结果，便于脚本处理。  
如果使用 `scan --output jsonl`，会逐条输出 `repo_scanned` 和最终 `scan_summary` 事件。  
如果使用 `sync --output jsonl`，会实时输出每个 `RunEvent`，适合 shell 管道和日志采集。
如果使用 `sync --profile-inspect`，table 输出会额外显示 `TIMINGS` 面板；JSON 输出会带上 `timings` 字段。

## 排障

### `zsh: command not found: py-local-git-pull`

这说明命令本身还没安装到当前 shell 的 PATH 里。常见原因：

1. 你只是 clone 了仓库，但还没安装
2. 你装在虚拟环境里了，但当前 shell 没激活那个环境

最快的解决方式：

```bash
uv run py-local-git-pull scan ~/code -r
```

如果你想以后直接全局用：

```bash
uv tool install git+https://github.com/crper/py-local-git-pull.git
```

### `python -m py_local_git_pull` 跑不起来

这通常不是模块名错了，而是你当前这个 Python 环境里还没装依赖。

最稳的做法：

```bash
uv sync --group dev
uv run python -m py_local_git_pull --help
```

如果你只是想用，不想关心当前解释器环境，直接用：

```bash
uv run py-local-git-pull scan ~/code -r
```

### 我到底该用哪种方式？

```text
只是试用 / 在仓库里开发
  -> uv run py-local-git-pull ...

想把它当日常命令长期使用
  -> uv tool install ...

已经有自己的虚拟环境
  -> uv pip install -e . 或 pip install -e .

想用模块方式运行
  -> uv run python -m py_local_git_pull ...
```

## 日志与运行记录

日志文件保存在`logs/git_sync.log`，每天自动轮换，保留最近7天的日志。  
同步运行记录会持久化到用户状态目录，用于 `doctor --last` 和 `runs` 子命令读取。  
`--output json` 或 `--output jsonl` 且未指定 `--verbose` 时，默认仅输出 `WARNING` 及以上日志，避免污染结构化输出。

## 开发与测试

```bash
# 代码质量检查
uv run --group dev ruff check .

# 单元测试
uv run --group dev pytest -q
```

## 项目架构

```
.
├── py_local_git_pull/
│   ├── cli/                   # Typer CLI 入口
│   ├── core/
│   │   ├── models.py          # Inspection / Plan / Outcome / Run 模型
│   │   ├── git/               # Git 子操作封装
│   │   ├── discovery/         # 仓库发现
│   │   ├── failure/           # 失败分类
│   │   └── services/          # inspection / sync 服务
│   ├── runtime/               # executor / journal / doctor 运行时
│   ├── state/                 # config / state 路径
│   ├── exceptions/            # 自定义异常
│   ├── ui/
│   │   ├── live.py            # sync Live 事件视图
│   │   ├── scan_view.py       # scan 表格视图
│   │   ├── doctor_view.py     # doctor 输出
│   │   ├── runs_view.py       # runs 输出
│   │   └── interactive.py     # 轻控制台式交互选择
│   ├── utils/
│   │   ├── logging_config.py  # 日志配置
│   │   └── logger.py          # 统一日志入口
│   ├── __init__.py
│   ├── __main__.py
│   └── main.py
├── tests/                     # 单元测试
└── README.md
```

核心运行链路：

```text
discover repos
  -> inspect repo state
  -> build sync plan
  -> execute with event stream
  -> persist run journal
  -> doctor / runs consume recorded evidence
```

设计与实施文档：

```text
当前生效设计:
  docs/superpowers/specs/2026-04-01-event-driven-cli-2.0-design.md
  docs/superpowers/plans/2026-04-01-event-driven-cli-2.0.md

历史文档:
  2026-03-31 的 task-console / full-refactor 文档保留作演进记录
```

## 贡献

欢迎提交问题和功能请求！如果你想贡献代码，请先开 issue 讨论改动方向。  
仓库协作规范见 [AGENTS.md](AGENTS.md)。

## 许可证

[MIT](LICENSE)
