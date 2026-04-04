from pathlib import Path

from py_local_git_pull.state.paths import build_state_paths


def test_build_state_paths_under_custom_root(tmp_path: Path) -> None:
    paths = build_state_paths(tmp_path)

    assert paths.state_dir == tmp_path
    assert paths.runs_dir == tmp_path / "runs"
    assert paths.logs_dir == tmp_path / "logs"
    assert paths.config_file == tmp_path / "config.toml"


def test_build_state_paths_prefers_env_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PY_LOCAL_GIT_PULL_STATE_DIR", str(tmp_path))

    paths = build_state_paths()

    assert paths.state_dir == tmp_path
    assert paths.runs_dir == tmp_path / "runs"
