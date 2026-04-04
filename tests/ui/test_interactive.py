from py_local_git_pull.core.models import RepoInspection, RiskFlag, RiskLevel
from py_local_git_pull.ui.interactive import (
    PickerPreset,
    build_picker_entries,
    format_repo_preview,
    recommended_action_for_repo,
    select_paths_for_preset,
)


def _inspection(
    *,
    name: str,
    path: str,
    branch: str | None = "main",
    risk_level: RiskLevel = RiskLevel.LOW,
    risk_flags: tuple[RiskFlag, ...] = (),
    has_changes: bool = False,
) -> RepoInspection:
    return RepoInspection(
        repo_name=name,
        path=path,
        current_branch=branch,
        is_git_repo=True,
        is_bare=False,
        has_changes=has_changes,
        has_untracked_changes=has_changes,
        detached_head=branch is None,
        branches=(),
        risk_level=risk_level,
        risk_flags=risk_flags,
    )


def test_build_picker_entries_preselects_safe_repos() -> None:
    inspections = (
        _inspection(name="alpha", path="/tmp/alpha"),
        _inspection(
            name="beta",
            path="/tmp/beta",
            risk_level=RiskLevel.HIGH,
            risk_flags=(RiskFlag.NO_UPSTREAM,),
        ),
    )

    entries = build_picker_entries(inspections)

    assert [entry.checked for entry in entries] == [True, False]
    assert entries[0].inspection.repo_name == "alpha"
    assert entries[0].recommended_action == "sync now"
    assert entries[1].recommended_action == "review before sync"
    assert "main" in entries[0].label
    assert "sync now" in entries[0].label
    assert "NO_UPSTREAM" in entries[1].label


def test_format_repo_preview_includes_risk_summary_and_actions() -> None:
    inspection = _inspection(
        name="beta",
        path="/tmp/beta",
        risk_level=RiskLevel.HIGH,
        risk_flags=(RiskFlag.NO_UPSTREAM, RiskFlag.HAS_LOCAL_CHANGES),
        has_changes=True,
    )

    preview = format_repo_preview(inspection)

    assert "repo: beta" in preview
    assert "risk: HIGH" in preview
    assert "no upstream" in preview
    assert "local changes" in preview
    assert "recommended: review before sync" in preview


def test_recommended_action_matches_risk_profile() -> None:
    assert recommended_action_for_repo(_inspection(name="alpha", path="/tmp/alpha")) == "sync now"
    assert (
        recommended_action_for_repo(
            _inspection(
                name="beta",
                path="/tmp/beta",
                risk_level=RiskLevel.MEDIUM,
                risk_flags=(RiskFlag.HAS_LOCAL_CHANGES,),
            )
        )
        == "double-check before sync"
    )
    assert (
        recommended_action_for_repo(
            _inspection(
                name="gamma",
                path="/tmp/gamma",
                risk_level=RiskLevel.HIGH,
                risk_flags=(RiskFlag.NO_UPSTREAM,),
            )
        )
        == "review before sync"
    )


def test_select_paths_for_preset_filters_safe_and_risky() -> None:
    inspections = (
        _inspection(name="alpha", path="/tmp/alpha"),
        _inspection(
            name="beta",
            path="/tmp/beta",
            risk_level=RiskLevel.MEDIUM,
            risk_flags=(RiskFlag.NO_UPSTREAM,),
        ),
    )

    assert select_paths_for_preset(inspections, PickerPreset.ALL_SAFE) == {"/tmp/alpha"}
    assert select_paths_for_preset(inspections, PickerPreset.RISKY_ONLY) == {"/tmp/beta"}
