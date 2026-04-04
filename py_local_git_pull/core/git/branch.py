"""Branch operations: checkout, upstream, existence checks."""

from py_local_git_pull.core.git.runner import GitRunner
from py_local_git_pull.config.defaults import DEFAULT_REMOTE


class BranchOperations:
    """Operations on git branches."""

    def __init__(self, runner: GitRunner):
        self._runner = runner

    def _run_check(self, cmd: list[str]) -> bool:
        code, out, _ = self._runner.run(cmd, check=False)
        return code == 0 and bool(out)

    def get_current_branch(self) -> str | None:
        """Get the current branch name, or None if detached HEAD."""
        code, out, _ = self._runner.run(["branch", "--show-current"], check=False)
        if code != 0 or not out:
            return None
        return out

    def branch_exists_locally(self, branch: str) -> bool:
        """Check if branch exists locally."""
        return self._run_check(["branch", "--list", branch])

    def branch_exists_remotely(self, branch: str, remote_branches: set[str] | None = None) -> bool:
        """Check if branch exists on the default remote."""
        if remote_branches is not None:
            return branch in remote_branches

        return self._run_check(["ls-remote", "--heads", DEFAULT_REMOTE, branch])

    def get_remote_branches(self) -> set[str]:
        """Get all remote branch names from refs."""
        code, out, _ = self._runner.run(
            ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/{DEFAULT_REMOTE}"],
            check=False,
        )
        if code != 0:
            return set()

        prefix = f"{DEFAULT_REMOTE}/"
        branches: set[str] = set()
        for line in out.splitlines():
            ref = line.strip()
            if ref.startswith(prefix) and not ref.endswith("/HEAD"):
                branches.add(ref[len(prefix) :])
        return branches

    def checkout_branch(
        self,
        branch: str,
        *,
        create_if_not_exist: bool = True,
        remote_branches: set[str] | None = None,
    ) -> tuple[bool, str | None]:
        """Checkout a branch.

        Returns:
            (success, error_message)
        """
        if self.branch_exists_locally(branch):
            self._runner.run(["checkout", branch])
            return True, None

        if create_if_not_exist and self.branch_exists_remotely(branch, remote_branches):
            self._runner.run(["checkout", "-b", branch, f"{DEFAULT_REMOTE}/{branch}"])
            return True, None

        return False, f"branch {branch} does not exist"

    def set_upstream(
        self, branch: str, *, auto_upstream: bool = False, remote_branches: set[str] | None = None
    ) -> tuple[bool, str, str | None]:
        """Set or check upstream tracking for a branch.

        Returns:
            (has_upstream, upstream_name, error_message)
        """
        code, out, _ = self._runner.run(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{u}}"],
            check=False,
        )

        if code == 0:
            return True, out, None

        if not auto_upstream:
            return False, "", None

        if not self.branch_exists_remotely(branch, remote_branches):
            return False, "", f"remote branch {DEFAULT_REMOTE}/{branch} does not exist"

        self._runner.run(["branch", f"--set-upstream-to={DEFAULT_REMOTE}/{branch}", branch])
        return True, f"{DEFAULT_REMOTE}/{branch}", None

    def get_ahead_behind(self, branch: str, upstream: str) -> tuple[int, int] | None:
        """Get ahead/behind counts for branch vs upstream.

        Returns:
            (ahead, behind) or None if unavailable.
        """
        code, out, _ = self._runner.run(
            ["rev-list", "--left-right", "--count", f"{branch}...{upstream}"],
            check=False,
        )
        if code != 0 or not out:
            return None

        parts = out.split("\t")
        if len(parts) != 2:
            return None

        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None
