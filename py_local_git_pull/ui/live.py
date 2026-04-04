"""Rich Live sync renderer driven by RunEvents."""

from __future__ import annotations

from collections import deque

from rich.columns import Columns
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from py_local_git_pull.core.models import RunEvent, RunEventType


def summarize_live_state(events: tuple[RunEvent, ...]) -> dict[str, int]:
    """Summarize repo progress from the latest event per repo."""
    latest_by_repo: dict[str, RunEvent] = {}
    for event in events:
        if event.repo_name:
            latest_by_repo[event.repo_name] = event

    summary = {
        "total": len(latest_by_repo),
        "queued": 0,
        "running": 0,
        "synced": 0,
        "partial": 0,
        "skipped": 0,
        "failed": 0,
    }

    for event in latest_by_repo.values():
        if event.event_type is RunEventType.REPO_QUEUED:
            summary["queued"] += 1
        elif event.event_type is RunEventType.REPO_STARTED:
            summary["running"] += 1
        elif event.event_type is RunEventType.REPO_BLOCKED or event.status == "skipped":
            summary["skipped"] += 1
        elif event.event_type is RunEventType.REPO_FAILED or event.status == "failed":
            summary["failed"] += 1
        elif event.status == "partial":
            summary["partial"] += 1
        else:
            summary["synced"] += 1

    return summary


class LiveSyncRenderer:
    def __init__(self, console, max_events: int = 12):
        self._console = console
        self._events: deque[RunEvent] = deque(maxlen=max_events)
        self._all_events: list[RunEvent] = []
        self._live: Live | None = None

    def __enter__(self):
        self._live = Live(console=self._console, refresh_per_second=8)
        self._live.__enter__()
        self._live.update(self._render())
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._live is not None:
            self._live.__exit__(exc_type, exc, tb)

    def push(self, event: RunEvent) -> None:
        self._events.append(event)
        self._all_events.append(event)
        if self._live is not None:
            self._live.update(self._render())

    def _build_progress_table(self, summary: dict[str, int]) -> Table:
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right")
        for key in ("total", "queued", "running", "synced", "partial", "skipped", "failed"):
            table.add_row(key.replace("_", " "), str(summary[key]))
        return table

    def _build_recent_events_table(self) -> Table:
        table = Table(title="RECENT EVENTS")
        table.add_column("Time", width=10)
        table.add_column("Repo", width=20)
        table.add_column("Event", width=18)
        table.add_column("Detail")
        for event in self._events:
            table.add_row(
                event.ts.split("T")[-1][:8],
                event.repo_name or "-",
                event.event_type.value,
                event.message or event.status or event.failure_kind or "-",
            )
        return table

    def _render(self):
        summary = summarize_live_state(tuple(self._all_events))
        progress = self._build_progress_table(summary)
        recent = self._build_recent_events_table()

        top = Columns(
            [
                Panel(progress, title="PROGRESS", border_style="cyan"),
                Panel(
                    "queued: waiting for worker\n"
                    "running: currently syncing\n"
                    "partial: mixed branch outcome\n"
                    "failed: inspect with doctor",
                    title="STATUS LEGEND",
                    border_style="blue",
                ),
            ],
            equal=True,
            expand=True,
        )

        return Group(
            Panel(top, title="py-local-git-pull sync", border_style="cyan"),
            Panel(recent, border_style="white"),
        )


__all__ = ["LiveSyncRenderer", "summarize_live_state"]
