import subprocess
from pathlib import Path

from py_local_git_pull.core.discovery.repo_finder import is_git_repo


def test_is_git_repo_should_only_match_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(
        ["git", "-C", str(repo_root), "init"],
        check=True,
        capture_output=True,
        text=True,
    )

    child = repo_root / "src"
    child.mkdir()

    assert is_git_repo(str(repo_root)) is True
    assert is_git_repo(str(child)) is False
