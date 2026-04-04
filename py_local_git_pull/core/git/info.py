"""Repository info collection: status, branches, bare check."""

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.config.defaults import BARE_REPO_VALUE


class InfoOperations:
    """Collect repository state information."""

    def __init__(self, runner: GitRunner):
        self._runner = runner

    def is_bare(self) -> bool:
        """Check if repository is bare."""
        code, out, _ = self._runner.run(["rev-parse", "--is-bare-repository"], check=False)
        return code == 0 and out == BARE_REPO_VALUE

    def has_changes(self) -> bool:
        """Check if working tree has uncommitted changes."""
        code, out, _ = self._runner.run(["status", "--porcelain"], check=False)
        return code == 0 and bool(out)

    def get_local_branches(self) -> list[tuple[str, bool]]:
        """Get local branches with current branch marker.

        Returns:
            List of (branch_name, is_current) tuples.
        """
        code, out, _ = self._runner.run(["branch", "--list"], check=False)
        if code != 0 or not out:
            return []

        current = self.get_current_branch()
        branches = []
        for line in out.splitlines():
            name = line.strip()
            if name.startswith("* "):
                name = name[2:]
            if name:
                branches.append((name, name == current))
        return branches

    def get_current_branch(self) -> str | None:
        """Get current branch name."""
        code, out, _ = self._runner.run(["branch", "--show-current"], check=False)
        if code != 0 or not out:
            return None
        return out
