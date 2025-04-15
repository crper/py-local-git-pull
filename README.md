# py-local-git-pull

一个功能强大的本地Git仓库同步工具，支持批量同步多个仓库和多个分支。

## 功能特点

- **多仓库支持**：可以指定单个仓库或递归搜索目录下的所有Git仓库
- **多分支支持**：可以同时同步多个分支，自动处理分支切换和还原
- **智能暂存**：自动暂存本地更改，拉取更新后还原暂存
- **上游分支管理**：可选择是否自动关联上游分支
- **详细状态报告**：提供每个分支的上游关联状态、领先/落后提交数信息
- **美观界面**：使用rich库提供进度条、彩色表格等美化界面
- **详细日志**：提供详细的操作日志和错误信息
- **跨平台兼容**：支持Windows、macOS和Linux系统

## 系统要求

- Python 3.13 或更高版本
- Git 命令行工具

## 安装

### 方式一：通过pip安装

```bash
pip install git+https://github.com/yourusername/py-local-git-pull.git
```

### 方式二：本地开发安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/py-local-git-pull.git
cd py-local-git-pull

# 安装依赖
pip install -e .

# 或使用uv (更快)
uv pip install -e .
```

## 使用方法

### 基本用法

```bash
# 同步单个仓库
py-local-git-pull /path/to/repo

# 或使用模块方式运行
python -m py_local_git_pull /path/to/repo

# 递归搜索并同步多个仓库
py-local-git-pull /path/to/repos --recursive
```

### 命令行参数

```
参数                    说明
----------------------------------------------------------------------------------
path                    Git仓库路径，可以是单个仓库路径或包含多个仓库的目录
-b, --branch            要切换的分支名称。如果分支不存在，程序会根据设置决定是否创建并关联上游分支
--branches              要拉取的多个分支名称，用空格分隔
--depth                 指定fetch操作的深度，用于限制获取的提交历史数量。设置为1时只获取最新提交，适用于大仓库的快速同步
--no-stash              跳过stash操作，即使有未提交的更改也不会自动暂存。注意：这可能导致checkout失败
--recursive, -r         递归搜索指定路径下的所有Git仓库
--max-depth             递归搜索的最大深度，仅在使用--recursive参数时有效，默认为3
--auto-upstream         自动设置关联上游分支，如果本地分支没有关联远程分支
--skip-non-exist        跳过不存在于远程的分支
--verbose, -v           显示详细日志信息
```

## 使用示例

### 同步单个仓库的当前分支

```bash
py-local-git-pull /path/to/repo
```

### 同步单个仓库的指定分支

```bash
py-local-git-pull /path/to/repo -b main
```

### 同步多个分支

```bash
py-local-git-pull /path/to/repo --branches main develop feature/x
```

### 递归搜索并同步所有仓库

```bash
py-local-git-pull /path/to/repos -r
```

### 指定递归搜索的最大深度

```bash
# 搜索深度设为5，在大型项目目录中非常有用
py-local-git-pull /path/to/repos -r --max-depth 5
```

### 自动关联上游分支

```bash
py-local-git-pull /path/to/repo --auto-upstream
```

### 不暂存本地更改

```bash
py-local-git-pull /path/to/repo --no-stash
```

### 限制获取的提交历史数量

```bash
py-local-git-pull /path/to/repo --depth 1
```

### 完整示例：递归查找并同步所有仓库的多个分支，自动设置上游，限制获取深度

```bash
py-local-git-pull /path/to/repos -r --branches main develop --auto-upstream --depth 1 --max-depth 4
```

## 输出说明

工具执行完成后会显示一个表格，包含以下信息：

- **仓库名**：Git仓库的名称
- **状态**：同步是否成功
- **当前分支**：当前所在的分支
- **已同步分支**：成功同步的分支列表
- **跳过分支**：由于各种原因被跳过的分支列表
- **上游关联**：分支是否关联了上游分支
- **领先/落后**：与上游分支相比，本地分支领先或落后的提交数
- **Stash状态**：是否暂存了本地更改
- **详细信息**：包含错误信息等其他细节

## 日志

日志文件保存在`logs/git_sync.log`，每天自动轮换，保留最近7天的日志。

## 项目架构

```
py_local_git_pull/
├── config/           # 配置相关模块
│   └── cli_parser.py # 命令行参数解析
├── core/             # 核心功能模块
│   ├── git_manager.py   # Git操作管理器
│   ├── repo_finder.py   # 仓库查找器
│   └── result_model.py  # 结果数据模型
├── ui/               # 用户界面模块
│   ├── display.py    # 结果显示
│   └── progress.py   # 进度显示
├── utils/            # 工具函数模块
│   └── logging_config.py # 日志配置
├── __init__.py       # 包初始化
├── __main__.py       # 入口点
└── main.py           # 主函数
```

## 贡献

欢迎提交问题和功能请求！如果你想贡献代码，请先开issue讨论你想改变的内容。

## 许可证

[MIT](LICENSE)