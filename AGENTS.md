# Repository Guidelines

## Project Structure & Module Organization
- `py_local_git_pull/` is the main package.
- `core/` contains sync logic (`git_manager.py`, `repo_finder.py`, `branch_syncer.py`, `git_executor.py`, `result_model.py`).
- `config/` holds CLI parsing and constants.
- `ui/` contains Rich-based terminal display and progress rendering.
- `utils/` handles logging setup and logger helpers; runtime logs are written to `logs/git_sync.log`.
- `exceptions/` defines domain-specific Git/sync exceptions.
- Root files: `pyproject.toml` (project metadata/tooling), `setup.py`, `README.md`, and `uv.lock`.

## Build, Test, and Development Commands
- `uv pip install -e .` (or `pip install -e .`): install in editable mode for development.
- `py-local-git-pull /path/to/repo`: run CLI entry point.
- `python -m py_local_git_pull /path/to/repos -r --max-depth 3`: run as module and recursively scan repos.
- `ruff check .` (or `uv run ruff check .`): run lint checks configured in `pyproject.toml`.
- `python -m py_local_git_pull --help`: quick smoke check for CLI wiring.

## Coding Style & Naming Conventions
- Target runtime is Python 3.13 (`requires-python >=3.13`).
- Use 4-space indentation and keep lines within 100 chars.
- Follow Ruff lint set: `E`, `F`, `B`.
- Naming: `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep command orchestration in `main.py`, and put reusable business logic in `core/`.

## Testing Guidelines
- There is currently no committed `tests/` suite.
- For non-trivial changes, add `pytest` tests under `tests/` with `test_*.py` names (for example, `tests/core/test_repo_finder.py`).
- Before opening a PR, run lint and perform at least one manual CLI regression against a real local Git repo.

## Commit & Pull Request Guidelines
- Follow concise Conventional Commit style seen in history, e.g. `refactor: 优化代码结构和格式`.
- Recommended prefixes: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- PRs should include: purpose, key behavior changes, reproduction/verification commands, and linked issue(s).
- If terminal UI output changes, include a screenshot or before/after output snippet.
