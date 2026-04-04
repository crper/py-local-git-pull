from pathlib import Path


def test_readme_uses_new_subcommands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "py-local-git-pull sync /path/to/repo" in readme
    assert "py-local-git-pull scan /path/to/repos -r" in readme
    assert "py-local-git-pull doctor /path/to/repos" in readme
    assert "py-local-git-pull runs list" in readme
    assert "py-local-git-pull runs show" in readme
    assert "--policy safe" in readme
    assert "--output jsonl" in readme
    assert "repo_scanned" in readme
