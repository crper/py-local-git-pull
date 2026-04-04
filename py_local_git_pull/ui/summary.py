"""Compatibility wrapper for scan summary rendering."""

from rich.console import Console

from py_local_git_pull.core.models import RepoInspection
from py_local_git_pull.ui.scan_view import render_scan_summary as render_scan_summary

__all__ = ["render_scan_summary", "Console", "RepoInspection"]
