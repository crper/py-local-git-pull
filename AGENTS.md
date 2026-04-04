# Repository Guidelines

## Project Structure & Module Organization
- `py_local_git_pull/` is the main package.
- `cli/` owns the Typer CLI entrypoints (`scan`, `sync`, `doctor`, `runs`) and option wiring.
- `core/` owns shared models plus Git-facing domain logic used by the CLI runtime.
- `runtime/` owns event-driven execution, run journals, and evidence-based diagnosis.
- `state/` owns config/state path resolution for run history and future local settings.
- `ui/` owns Rich-based task console rendering, summary panels, live event views, and prompt helpers.
- `utils/` handles logging setup and logger helpers; runtime logs are written to `logs/git_sync.log`.
- `exceptions/` defines domain-specific Git/sync exceptions.
- `config/` is legacy and should be removed as part of the redesign unless a file is still needed during migration.
- Root files: `pyproject.toml` (project metadata/tooling), `setup.py`, `README.md`, and `uv.lock`.

## Build, Test, and Development Commands
- `uv pip install -e .` (or `pip install -e .`): install in editable mode for development.
- `uv sync --group dev`: create a runnable local dev environment with all CLI dependencies.
- `uv run py-local-git-pull scan /path/to/repos -r`: inspect repositories without mutating them.
- `uv run py-local-git-pull sync /path/to/repos -r -b main`: run the task-console sync flow.
- `uv run py-local-git-pull doctor /path/to/repos`: diagnose repos with actionable suggestions.
- `uv run py-local-git-pull runs list`: inspect persisted run history from the local state dir.
- `uv run python -m py_local_git_pull --help`: smoke check the Typer app wiring through uv.
- `ruff check .` (or `uv run ruff check .`): run lint checks configured in `pyproject.toml`.
- `uv run --group dev pytest -q`: run the test suite.
- `PY_LOCAL_GIT_PULL_STATE_DIR=/tmp/py-local-git-pull-smoke uv run py-local-git-pull ...`: use an isolated writable state dir for smoke tests in restricted environments.

## Coding Style & Naming Conventions
- Target runtime is Python 3.13 (`requires-python >=3.13`).
- Use 4-space indentation and keep lines within 100 chars.
- Follow Ruff lint set: `E`, `F`, `B`.
- Naming: `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep Typer command wiring in `cli/`, reusable business logic in `core/` and `runtime/`, and Rich rendering in `ui/`.
- Favor `dataclass` + `Enum` for shared CLI/task-console models unless a real need emerges for something heavier.
- Breaking changes are allowed in this redesign. Prefer a clean final structure over compatibility shims.

## Testing Guidelines
- Use TDD for behavior changes: write the failing test, watch it fail, then implement the minimum code.
- Add `pytest` tests under `tests/` with `test_*.py` names grouped by responsibility (`tests/commands`, `tests/core`, `tests/ui`).
- Before opening a PR, run lint and perform at least one manual CLI regression against a real local Git repo.
- For CLI changes, verify `scan`, `sync`, and `doctor` help output plus at least one real command path.

## Commit & Pull Request Guidelines
- Follow concise Conventional Commit style seen in history, e.g. `refactor: 优化代码结构和格式`.
- Recommended prefixes: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- PRs should include: purpose, key behavior changes, reproduction/verification commands, and linked issue(s).
- If terminal UI output changes, include a screenshot or before/after output snippet.

## Current Redesign Direction
- The tool is being rebuilt as a pure CLI Git task console.
- Current architecture direction: event-driven CLI runtime with `discovery -> inspection -> policy -> plan -> execution -> diagnosis`.
- Command model: `scan`, `sync`, `doctor`, with `runs` as an allowed follow-up command if run history lands in this redesign.
- Preferred libraries for this redesign: `typer`, `rich`, `anyio`, `prompt_toolkit`, `platformdirs`, `structlog`.
- Interactive sync is now a lightweight preview-first picker. Keep new interactive work in `ui/interactive.py` and avoid reintroducing `questionary`.
- Keep inspection read-only, execution event-driven, and rendering separate from Git orchestration.
- Do not introduce heavy frameworks like `GitPython`, `pydantic`, or `textual` in phase 1 unless the user explicitly reopens that decision.
