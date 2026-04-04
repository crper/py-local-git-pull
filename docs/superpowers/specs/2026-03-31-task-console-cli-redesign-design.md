# py-local-git-pull Modern CLI Redesign

Date: 2026-03-31
Status: Approved for spec review
Scope: Breaking redesign, pure CLI, human-first with stable machine output

## 1. Summary

`py-local-git-pull` will be redesigned from a batch `git pull` helper into a pure CLI Git task console.

The new product goal is:

```text
scan risk -> plan execution -> sync safely -> explain failures
```

This is a deliberate breaking change. We will not preserve the old command shape, old JSON schema, or the old result model if they block a cleaner structure.

## 2. Product Goals

### Goals

- Make multi-repo sync easy to understand at a glance.
- Make failures actionable, not just visible.
- Keep the tool pure CLI, no browser, no GUI.
- Default to human-friendly output while preserving stable JSON for automation.
- Reuse the existing Git execution core where it is already good enough.

### Non-Goals

- No full-screen heavy TUI.
- No local web dashboard.
- No Git hosting features such as PR, issue, or branch management.
- No multi-remote orchestration in this redesign.
- No hidden auto-fix behavior that mutates repos without explicit intent.

## 3. User and Primary Jobs

Primary user:

```text
Human user first
  -> scans many local repos
  -> wants clear status quickly
  -> needs help after failures

Machine user second
  -> consumes JSON output in scripts or CI
```

Primary jobs:

1. Find all repos under a path and understand which ones are safe to sync.
2. Run sync across one or many repos without losing track of what happened.
3. Diagnose failed repos and know the next command to run.

## 4. Breaking Changes

This redesign explicitly allows breaking changes.

### Command shape

Old:

```bash
py-local-git-pull /path/to/repo
```

New:

```bash
py-local-git-pull scan /path/to/repo
py-local-git-pull sync /path/to/repo
py-local-git-pull doctor /path/to/repo
```

### Parameter shape

- Remove `--branches`.
- Keep `-b/--branch` and allow repeated use.

Example:

```bash
py-local-git-pull sync ~/code -b main -b develop -b feature/x
```

### JSON shape

- Drop the old JSON contract.
- Introduce `schema_version = 2`.

### Result semantics

- Replace coarse `success: bool` repo semantics with:

```text
synced
partial
skipped
failed
```

## 5. Command Model

```text
scan
  inspect current repo state
  classify risk
  produce sync candidates

sync
  run scan
  build plan
  execute sync
  print summary and next actions

doctor
  inspect failed outcomes
  explain why they failed
  suggest exact next steps
```

### Recommended options

```text
Global-ish
  -r, --recursive
  --max-depth
  --output [table|json]
  --verbose

sync
  -b, --branch <name>  # repeatable
  --auto-upstream
  --skip-non-exist
  --no-stash
  --interactive

doctor
  --repo <name>
  --kind <failure-kind>
```

## 6. User Experience and Information Architecture

### Core output rules

```text
1. Show summary before details
2. Show repo-level status before branch-level detail
3. Show classified failures before raw stderr
4. Show next actions before noise
```

### `scan` output

```text
+------------------------------------------------------------------+
| py-local-git-pull scan                                           |
| path: ~/code    repos_found: 18    mode: recursive(max_depth=3)  |
+------------------------------------------------------------------+
| INVENTORY                                                        |
| total: 18   clean: 12   dirty: 3   bare: 1   inaccessible: 2     |
+------------------------------------------------------------------+
| RISKS                                                            |
| high:   2   detached_head / conflict risk                        |
| medium: 4   no_upstream / remote_missing / local changes         |
| low:   12   safe_to_sync                                         |
+------------------------------------------------------------------+
| NEXT                                                             |
| run: py-local-git-pull sync ~/code                               |
| run: py-local-git-pull sync ~/code --interactive                 |
+------------------------------------------------------------------+
```

### `sync` output

```text
+------------------------------------------------------------------+
| py-local-git-pull sync                                           |
| path: ~/code   repos: 18   branches: main,dev   mode: safe       |
+------------------------------------------------------------------+
| PLAN                                                             |
| safe: 12   attention: 4   skipped: 2                             |
| risks: dirty_worktree(3) upstream_missing(2) remote_missing(1)   |
+------------------------------------------------------------------+
| EXECUTION                                                        |
| [01/18] openclaw        synced           main                     |
| [02/18] blog            stashed+synced   main                     |
| [03/18] demo-api        skipped          no upstream              |
| [04/18] old-tool        failed           ff-only conflict         |
| [05/18] docs-site       running          fetching                 |
+------------------------------------------------------------------+
| SUMMARY                                                          |
| success: 14   skipped: 2   failed: 2                             |
| synced_branches: 21   stashed: 3                                 |
+------------------------------------------------------------------+
| NEXT ACTIONS                                                     |
| 2 failed repos -> run doctor                                     |
| 2 repos missing upstream -> rerun with --auto-upstream           |
+------------------------------------------------------------------+
```

### `doctor` output

```text
+------------------------------------------------------------------+
| py-local-git-pull doctor                                         |
| path: ~/code    targets: 2 failed repos                          |
+------------------------------------------------------------------+
| REPO: old-tool                                                   |
| PROBLEM: pull_ff_conflict                                        |
| WHY: local branch diverged from origin/main                      |
| DO NOW:                                                          |
|   1. git -C /repo status                                         |
|   2. git -C /repo log --oneline --graph --decorate --all -20     |
|   3. choose rebase / merge / reset                               |
+------------------------------------------------------------------+
```

### Detail levels

```text
Default
  -> summary + repo-level events

--verbose
  -> summary + repo-level events + branch detail + raw stderr
```

## 7. Interaction Model

The tool remains pure CLI. Interactivity is optional and intentionally limited.

### `--interactive` boundary

Allowed:

- Choose repo subset
- Choose risk threshold
- Confirm execution

Not allowed:

- Heavy full-screen TUI
- Multi-panel live navigation
- Persistent dashboard sessions

### Interactive flow

```text
scan complete
18 repos found

Select target set:
  1. all safe repos
  2. safe + medium risk repos
  3. custom selection
  4. abort

> 1

Plan:
  selected: 12 repos
  skipped: 6 repos

Continue?
  yes / no
```

After confirmation, the tool returns to the standard `sync` execution view.

## 8. Dependency Strategy

### Keep

- `rich`

### Add

- `typer`
- `questionary`

### Do not add now

- `GitPython`
- `pydantic`
- `textual`
- `orjson`

### Rationale

```text
Typer
  -> cleaner subcommands
  -> typed options
  -> better help and completion

Questionary
  -> enough for light selection and confirmation

Rich
  -> already present
  -> sufficient for the redesigned output
```

Rule:

```text
Modernize the CLI layer
Do not complicate the Git core
```

## 9. Architecture

### Target structure

```text
py_local_git_pull/
├── commands/
│   ├── app.py
│   ├── scan.py
│   ├── sync.py
│   └── doctor.py
├── core/
│   ├── models.py
│   ├── repo_finder.py
│   ├── repo_inspector.py
│   ├── sync_planner.py
│   ├── failure_catalog.py
│   ├── git_manager.py
│   └── branch_syncer.py
├── ui/
│   ├── dashboard.py
│   ├── events.py
│   ├── summary.py
│   ├── doctor_view.py
│   └── prompts.py
└── main.py
```

### Responsibility map

```text
commands/*
  parse options
  call services
  choose renderers

core/repo_inspector.py
  inspect current repo state

core/sync_planner.py
  turn inspections into execution plans

core/git_manager.py
core/branch_syncer.py
  execute Git operations

core/failure_catalog.py
  map low-level failures to stable user-facing categories

ui/*
  render summary, event stream, and diagnosis
```

### Layer diagram

```text
+---------+     +------------+     +-----------+     +----------+
| Typer   | --> | Services   | --> | Outcome   | --> | Renderer |
+---------+     +------------+     +-----------+     +----------+
     |
     └--> questionary (only when interactive)
```

Rule:

```text
commands do not hold Git logic
ui does not infer business state
core does not emit rich text
```

## 10. Data Model

### Core models

```text
RepoInspection
RepoSyncPlan
RepoOutcome
FailureRecord
```

### Flow

```text
RepoInspection
    │
    ▼
RepoSyncPlan
    │
    ▼
RepoOutcome
    ├─ BranchOutcome[]
    └─ FailureRecord?
```

### Inspection models

```python
RepoInspection
  repo_name
  path
  current_branch
  is_git_repo
  is_bare
  has_changes
  has_untracked_changes
  detached_head
  branches[]
  risk_level
  risk_flags[]
```

### Plan models

```python
RepoSyncPlan
  repo_name
  path
  target_branches[]
  action
  stash_strategy
  will_skip
  skip_reason
  needs_attention
  attention_reason
```

### Outcome models

```python
RepoOutcome
  repo_name
  path
  status
  current_branch
  target_branches[]
  synced_branches[]
  skipped_branches[]
  stashed
  branch_outcomes[]
  failure?
  notes[]
```

### Repo status

```text
synced
partial
skipped
failed
```

## 11. Failure Taxonomy and Diagnosis

### Failure kinds

```text
dirty_worktree
stash_failed
fetch_failed
checkout_failed
upstream_missing
remote_branch_missing
pull_ff_conflict
pull_rejected
bare_repository
repo_not_found
permission_denied
unknown_git_error
```

### Risk vs failure

```text
RiskFlag
  signals potential trouble before execution

FailureKind
  classifies what actually failed
```

### Diagnosis contract

Every failure becomes:

```python
FailureRecord
  kind
  summary
  detail
  raw_error
  can_auto_fix
  suggested_actions[]
```

### Suggested action contract

```python
SuggestedAction
  label
  command
  description
  auto_fixable
```

### Auto-fix policy

```text
Safe auto-fix
  upstream_missing

Confirm-before-fix
  dirty_worktree
  stash-related retry flows

Manual only
  pull_ff_conflict
  pull_rejected
  unknown_git_error
```

Rule:

```text
doctor explains first
doctor does not silently mutate repos
```

## 12. JSON Schema v2

The new JSON output is the machine-readable projection of the same core models.

Example:

```json
{
  "schema_version": 2,
  "command": "sync",
  "path": "/Users/me/code",
  "summary": {
    "total_repos": 18,
    "synced": 14,
    "partial": 1,
    "skipped": 2,
    "failed": 1
  },
  "repos": [
    {
      "repo_name": "demo-api",
      "path": "/Users/me/code/demo-api",
      "status": "failed",
      "current_branch": "main",
      "target_branches": ["main"],
      "stashed": false,
      "risk_level": "medium",
      "risk_flags": ["no_upstream"],
      "failure": {
        "kind": "upstream_missing",
        "summary": "current branch has no upstream",
        "detail": "branch main is not tracking origin/main",
        "raw_error": null,
        "can_auto_fix": true,
        "suggested_actions": [
          {
            "label": "set_upstream",
            "command": "git -C /Users/me/code/demo-api branch --set-upstream-to=origin/main main",
            "description": "set upstream for the current branch",
            "auto_fixable": true
          }
        ]
      },
      "branch_outcomes": []
    }
  ]
}
```

## 13. Migration Strategy

### Preserve with adaptation

- `core/repo_finder.py`
- `core/git_manager.py`
- `core/branch_syncer.py`
- `core/sync_options.py`
- `utils/*`
- `exceptions/*`

### Replace or split

- `config/cli_parser.py` -> `commands/*`
- `core/result_model.py` -> `core/models.py`
- `ui/display.py` -> `ui/summary.py` + `ui/doctor_view.py`
- `ui/progress.py` -> `ui/dashboard.py` + `ui/events.py`

### Migration diagram

```text
OLD
main.py
  -> cli_parser.py
  -> git_manager.py
  -> display.py

NEW
main.py
  -> commands/app.py
      -> commands/sync.py
      -> commands/scan.py
      -> commands/doctor.py
          -> core/*
          -> ui/*
```

## 14. Delivery Plan

### Phase 1

Goal: establish the new architecture and a full `sync` loop.

Deliver:

- `typer` command app
- `scan/sync/doctor` command shells
- `core/models.py`
- `core/repo_inspector.py`
- `core/failure_catalog.py`
- redesigned `sync` output
- JSON schema v2

Acceptance:

```text
1. sync works end to end with new command model
2. output includes Header / Plan / Execution / Summary / Next Actions
3. failure classification covers common cases
4. JSON v2 is stable
```

### Phase 2

Goal: make the CLI feel modern and selective.

Deliver:

- full `scan`
- stronger `doctor`
- `questionary`
- `sync --interactive`
- diagnosis filters

### Phase 3

Goal: polish, cleanup, and documentation.

Deliver:

- README rewrite
- richer examples
- UI polish
- dead code removal
- broader tests

## 15. Testing Strategy

### Target test layout

```text
tests/
├── commands/
│   ├── test_scan_command.py
│   ├── test_sync_command.py
│   └── test_doctor_command.py
├── core/
│   ├── test_repo_inspector.py
│   ├── test_sync_planner.py
│   ├── test_failure_catalog.py
│   └── test_models.py
└── ui/
    ├── test_summary_render.py
    └── test_doctor_view.py
```

### What to test

- subcommand help and option parsing
- repeated branch options
- inspection and risk classification
- plan generation
- failure classification
- renderer structure and key text
- JSON v2 shape

Rule:

```text
test output structure
not decorative styling
```

## 16. Risks and Mitigations

### Risk 1: users lose old command habits

Mitigation:

- update README front page with old vs new examples
- document the breaking change loudly

### Risk 2: scripts break on JSON changes

Mitigation:

- document `schema_version = 2`
- include a machine-readable example in README

### Risk 3: business logic leaks into CLI code

Mitigation:

- enforce command/service/renderer boundaries

### Risk 4: redesign becomes an excuse to rewrite everything

Mitigation:

- keep Git execution core unless there is a concrete defect
- spend the change budget on CLI, planning, failure handling, and rendering

## 17. What Is Not in Scope

- backward compatibility shims
- dual JSON schemas
- heavy TUI
- auto-fix framework
- browser reports
- multi-remote support

## 18. Final Recommendation

This redesign should proceed as a bold but disciplined refactor.

Recommended execution:

```text
pure CLI
breaking change allowed
Typer + Rich + Questionary
new command model
new result model
new failure taxonomy
Phase 1 first, Phase 2 next
```

This is the shortest path to a cleaner, more modern, more maintainable tool.
