# Agent Learnings

## 2026-04-03

- `uv` in the Codex sandbox can fail on `~/.cache/uv`; use `UV_CACHE_DIR=/tmp/uv-cache` for lint and test commands.
- Subagent `502` and stream disconnect errors can be infrastructure noise; retry with a fresh agent before treating them as repository issues.
