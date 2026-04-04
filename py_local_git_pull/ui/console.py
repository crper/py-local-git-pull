"""Rich console configuration."""

from rich.console import Console
from rich.theme import Theme

_DEFAULT_THEME = Theme(
    {
        "info": "cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "debug": "dim",
    }
)


def make_console() -> Console:
    """Create the primary Rich console."""
    return Console(theme=_DEFAULT_THEME)


def make_stderr_console() -> Console:
    """Create a stderr console for log output (avoids progress bar interference)."""
    return Console(stderr=True, highlight=False, style="dim")
