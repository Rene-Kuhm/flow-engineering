# Design: flow-workspace-status

## Technical Approach

Add a new top-level `flow workspace status` command that reuses Phase 1 project detection (`_detect_project_markers`) and synthesizes a needs-attention report. The command is read-only: it scans the projects root once, computes `totals` and `needs_attention`, then renders either text or deterministic JSON.

The v1 JSON envelope intentionally has **no timestamp fields**. This preserves byte-identical output for unchanged fixture roots and repeats the AC8 lesson from `workspace-intelligence`.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Command surface | `flow workspace status` | `flow projects status`, `flow workspace list` | `workspace` is the aggregation layer; `projects ls` remains raw inventory. |
| Data source | Direct `_detect_project_markers()` calls | Subprocess `flow projects ls --json` | Single in-process scan avoids stale data and subprocess overhead. |
| Root resolution | Extract `_resolve_projects_root(root)` from `projects_ls` | Duplicate root fallback logic | Keeps `FLOW_PROJECTS_ROOT` / Windows / POSIX defaults in one place. |
| Summary helper | `_summarize_workspace_status(projects)` | Inline aggregation in Click command | Pure helper is easy to unit test and keeps renderer thin. |
| JSON determinism | No `generated_at`; fixed key order | Timestamped envelope | Timestamp makes byte-identical output impossible. |
| R5 behavior | `has_graphify == false` informational-only | Count graphify stub as needs-attention | Phase 1 graphify probe is stubbed; counting it would create false alarms. |

## Data Flow

```text
flow workspace status [--root PATH] [--json]
        |
        v
_resolve_projects_root(root)
        |
        v
sorted(root.iterdir()) -> _detect_project_markers(project)
        |
        v
_summarize_workspace_status(projects)
        |
        +--> _render_workspace_status_text(summary)
        |
        +--> _workspace_status_envelope(root, projects, summary) -> json.dumps(...)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `src/flow_engineering/cli.py` | Modify | Add `workspace` group, `status` command, root resolver, summary helper, text renderer, JSON envelope builder. |
| `tests/unit/_workspace_fixtures.py` | Create/extend | Shared fake workspace helpers reused by projects/status tests. |
| `tests/unit/test_cli_workspace_status.py` | Create | Unit tests for R1-R5, text output, JSON envelope, empty root, deterministic bytes, and Phase 1 preservation. |

## Interfaces / Contracts

### `_resolve_projects_root`

```python
def _resolve_projects_root(root: Path | None) -> Path:
    """Resolve explicit root, FLOW_PROJECTS_ROOT, Windows default, or POSIX default."""
```

`projects_ls` and `workspace status` both call this helper. Existing error behavior stays at command level: if resolved root is not a directory, emit `projects root not found: <root>` and exit 1.

### `_summarize_workspace_status`

```python
def _summarize_workspace_status(projects: list[dict[str, Any]]) -> dict[str, Any]:
    """Return totals plus needs_attention entries for R1-R4; R5 informational only."""
```

Summary shape:

```python
{
    "totals": {
        "projects": int,
        "dirty": int,
        "no_git": int,
        "no_tests": int,
        "has_openspec": int,
        "has_graphify": int,
        "has_engram": int,
        "needs_attention": int,
    },
    "needs_attention": [
        {"name": str, "path": str, "reasons": list[str]},
    ],
}
```

Rules:
- R1: `has_git and dirty` -> `R1: uncommitted work`
- R2: `not has_git` -> `R2: no version control`
- R3: `test_commands == []` -> `R3: no tests detected`
- R4: `not has_openspec and stack in {"Python", "Go", "Rust"}` -> `R4: SDD-adjacent stack missing openspec`
- R5: graphify stub is informational only; do not add to `needs_attention`.

### JSON Envelope

Top-level key order:

```json
{
  "version": "1",
  "root": "<path>",
  "totals": {},
  "projects": [],
  "needs_attention": []
}
```

`projects` is the verbatim list returned by `_detect_project_markers`, sorted by name. No `generated_at` in v1.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `_summarize_workspace_status` R1-R5 | Direct helper tests with dict fixtures. |
| CLI text | `flow workspace status` | `CliRunner` + `tmp_path` fake workspace; assert tags `[DIRTY]`, `[NO-GIT]`, `[NO TESTS]`, summary. |
| CLI JSON | Envelope shape/key order/totals | `json.loads` and first-key assertions; no timestamp fields. |
| Determinism | Two `--json` invocations | Compare stdout bytes exactly on unchanged fixture root. |
| Phase 1 guard | `flow projects ls --json` unchanged | Existing tests plus one smoke assertion if needed; do not mutate Phase 1 schema. |
| Empty root | No subdirectories | Text `(no projects to report)` and JSON `totals.projects == 0`. |

## Migration / Rollout

No migration required. This is an additive CLI command. Existing `flow projects ls` and `flow where` behavior remains unchanged.

## Open Questions

None.
