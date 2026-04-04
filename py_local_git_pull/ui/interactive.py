"""Interactive sync picker with preview-first selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from py_local_git_pull.core.models import RepoInspection, RiskFlag, RiskLevel


class PickerPreset(str, Enum):
    ALL_SAFE = "all_safe"
    RISKY_ONLY = "risky_only"


@dataclass(frozen=True)
class PickerEntry:
    inspection: RepoInspection
    label: str
    checked: bool
    recommended_action: str


RISK_FLAG_LABELS: dict[RiskFlag, str] = {
    RiskFlag.HAS_LOCAL_CHANGES: "local changes",
    RiskFlag.DETACHED_HEAD: "detached head",
    RiskFlag.NO_UPSTREAM: "no upstream",
    RiskFlag.REMOTE_BRANCH_MISSING: "remote branch missing",
    RiskFlag.BARE_REPOSITORY: "bare repository",
    RiskFlag.UNKNOWN_STATE: "unknown state",
}


def recommended_action_for_repo(inspection: RepoInspection) -> str:
    """Return the primary recommendation shown in the picker."""
    if inspection.risk_level is RiskLevel.HIGH:
        return "review before sync"
    if inspection.risk_level is RiskLevel.MEDIUM:
        return "double-check before sync"
    return "sync now"


def _picker_sort_key(inspection: RepoInspection) -> tuple[int, int, str]:
    """Sort safer repos first, then by risk level, then name."""
    action_rank = {
        "sync now": 0,
        "double-check before sync": 1,
        "review before sync": 2,
    }
    risk_rank = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
    }
    action = recommended_action_for_repo(inspection)
    return (
        action_rank[action],
        risk_rank[inspection.risk_level],
        inspection.repo_name.lower(),
    )


def _build_entry_label(inspection: RepoInspection) -> str:
    """Build compact label for picker entry."""
    branch = inspection.current_branch or "detached"
    changes = "dirty" if inspection.has_changes else "clean"
    flags = ",".join(flag.name for flag in inspection.risk_flags[:2]) or "safe"
    action = recommended_action_for_repo(inspection)
    return (
        f"{inspection.repo_name:<24} "
        f"{action:<24} "
        f"{inspection.risk_level.value.upper():<6} "
        f"{branch:<16} "
        f"{changes:<5} "
        f"{flags}"
    ).rstrip()


def build_picker_entries(inspections: tuple[RepoInspection, ...]) -> tuple[PickerEntry, ...]:
    """Build picker entries with compact labels and default selection state."""
    entries: list[PickerEntry] = []
    for inspection in sorted(inspections, key=_picker_sort_key):
        label = _build_entry_label(inspection)
        entries.append(
            PickerEntry(
                inspection=inspection,
                label=label,
                checked=not inspection.risk_flags,
                recommended_action=recommended_action_for_repo(inspection),
            )
        )
    return tuple(entries)


def format_repo_preview(inspection: RepoInspection) -> str:
    """Render a detail preview for the currently highlighted repo."""
    branch = inspection.current_branch or "detached"
    flags = [
        RISK_FLAG_LABELS.get(flag, flag.value.replace("_", " "))
        for flag in inspection.risk_flags
    ]
    risk_detail = ", ".join(flags) if flags else "safe to sync"
    branch_names = ", ".join(branch_info.name for branch_info in inspection.branches) or branch

    recommended = recommended_action_for_repo(inspection)

    lines = [
        f"repo: {inspection.repo_name}",
        f"path: {inspection.path}",
        f"branch: {branch}",
        f"branches: {branch_names}",
        f"risk: {inspection.risk_level.value.upper()}",
        f"details: {risk_detail}",
        f"changes: {'yes' if inspection.has_changes else 'no'}",
        f"recommended: {recommended}",
    ]
    return "\n".join(lines)


def select_paths_for_preset(
    inspections: tuple[RepoInspection, ...],
    preset: PickerPreset,
) -> set[str]:
    """Return selected paths for a shortcut preset."""
    if preset is PickerPreset.ALL_SAFE:
        return {inspection.path for inspection in inspections if not inspection.risk_flags}
    return {inspection.path for inspection in inspections if inspection.risk_flags}


def choose_repo_paths(inspections: tuple[RepoInspection, ...]) -> list[str]:
    """Show interactive repo selection with preview, using the best available UI."""
    if not inspections:
        return []

    entries = build_picker_entries(inspections)
    try:
        return _choose_repo_paths_prompt_toolkit(entries)
    except ModuleNotFoundError:
        return _choose_repo_paths_basic(entries)


def _parse_selection_input(raw: str, default: str, entries: tuple[PickerEntry, ...]) -> set[str]:
    """Parse user selection input and return selected paths."""
    if not raw:
        raw = default or "safe"

    inspections = tuple(entry.inspection for entry in entries)
    safe_paths = select_paths_for_preset(inspections, PickerPreset.ALL_SAFE)
    risky_paths = select_paths_for_preset(inspections, PickerPreset.RISKY_ONLY)
    all_paths = {entry.inspection.path for entry in entries}

    preset_map = {
        "safe": safe_paths,
        "risky": risky_paths,
        "all": all_paths,
        "none": set(),
    }

    if raw in preset_map:
        return preset_map[raw]

    selected = set()
    for token in raw.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        offset = int(token) - 1
        if 0 <= offset < len(entries):
            selected.add(entries[offset].inspection.path)
    return selected


def _print_picker_entries(entries: tuple[PickerEntry, ...]) -> None:
    """Print picker entries to console."""
    print("py-local-git-pull sync picker")
    print("")
    for index, entry in enumerate(entries, start=1):
        mark = "x" if entry.checked else " "
        print(f"{index:>2}. [{mark}] {entry.label}")
    print("")
    print("Type repo numbers separated by commas, or one of: safe, risky, all, none.")


def _choose_repo_paths_basic(entries: tuple[PickerEntry, ...]) -> list[str]:
    """Fallback selector for environments without prompt_toolkit."""
    _print_picker_entries(entries)

    default = ",".join(
        str(index) for index, entry in enumerate(entries, start=1) if entry.checked
    )
    raw = input(f"Selection [{default or 'safe'}]: ").strip().lower()

    selected = _parse_selection_input(raw, default, entries)
    all_paths = {entry.inspection.path for entry in entries}
    return [p for p in all_paths if p in selected]


def _choose_repo_paths_prompt_toolkit(entries: tuple[PickerEntry, ...]) -> list[str]:
    """Interactive picker backed by prompt_toolkit."""
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style
    from prompt_toolkit.widgets import Frame

    inspections = tuple(entry.inspection for entry in entries)
    selected_paths = {entry.inspection.path for entry in entries if entry.checked}
    cursor = 0
    result: list[str] = []

    def current_entry() -> PickerEntry:
        return entries[cursor]

    def repo_list_text():
        fragments: list[tuple[str, str]] = []
        for index, entry in enumerate(entries):
            focused = index == cursor
            checked = entry.inspection.path in selected_paths
            prefix = ">" if focused else " "
            mark = "x" if checked else " "
            style = "class:cursor" if focused else ""
            fragments.append((style, f"{prefix} [{mark}] {entry.label}\n"))
        return fragments

    def preview_text():
        return format_repo_preview(current_entry().inspection)

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _move_up(event) -> None:
        nonlocal cursor
        cursor = (cursor - 1) % len(entries)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _move_down(event) -> None:
        nonlocal cursor
        cursor = (cursor + 1) % len(entries)
        event.app.invalidate()

    @kb.add("space")
    def _toggle(event) -> None:
        path = current_entry().inspection.path
        if path in selected_paths:
            selected_paths.remove(path)
        else:
            selected_paths.add(path)
        event.app.invalidate()

    @kb.add("a")
    def _select_safe(event) -> None:
        selected_paths.clear()
        selected_paths.update(select_paths_for_preset(inspections, PickerPreset.ALL_SAFE))
        event.app.invalidate()

    @kb.add("r")
    def _select_risky(event) -> None:
        selected_paths.clear()
        selected_paths.update(select_paths_for_preset(inspections, PickerPreset.RISKY_ONLY))
        event.app.invalidate()

    @kb.add("enter")
    def _accept(event) -> None:
        result[:] = [
            entry.inspection.path
            for entry in entries
            if entry.inspection.path in selected_paths
        ]
        event.app.exit()

    @kb.add("escape")
    @kb.add("q")
    def _cancel(event) -> None:
        result[:] = []
        event.app.exit()

    root_container = HSplit(
        [
            Window(
                FormattedTextControl(
                    text="py-local-git-pull sync picker",
                ),
                height=1,
            ),
            VSplit(
                [
                    Frame(
                        Window(
                            content=FormattedTextControl(repo_list_text),
                            wrap_lines=False,
                            always_hide_cursor=True,
                        ),
                        title="Repo List",
                    ),
                    Frame(
                        Window(
                            content=FormattedTextControl(preview_text),
                            always_hide_cursor=True,
                        ),
                        title="Preview",
                    ),
                ]
            ),
            Window(
                FormattedTextControl(
                    text=(
                        "space toggle  a all-safe  r risky-only  "
                        "enter sync  q quit"
                    )
                ),
                height=1,
            ),
        ]
    )

    style = Style.from_dict(
        {
            "frame.label": "bold",
            "cursor": "reverse",
        }
    )

    app = Application(
        layout=Layout(root_container),
        key_bindings=kb,
        full_screen=False,
        style=style,
    )
    app.run()
    return result


__all__ = [
    "PickerEntry",
    "PickerPreset",
    "build_picker_entries",
    "choose_repo_paths",
    "format_repo_preview",
    "recommended_action_for_repo",
    "select_paths_for_preset",
]
