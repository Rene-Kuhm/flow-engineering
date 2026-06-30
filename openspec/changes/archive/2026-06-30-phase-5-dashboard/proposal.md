# Proposal: phase-5-dashboard — Read-only Rich Dashboard (Approach E)

> **Change**: `phase-5-dashboard`
> **Phase**: Phase 5 of workspace-intelligence arc — FIRST FEATURE change after 4 deltas + 2 cleanup cycles + 1 surgical fix
> **User-locked approach**: Approach E (Rich only, read-only, zero-deps)
> **Artifact store**: openspec
> **Strict TDD**: ON (feature change; tests required)
> **LOC forecast**: 300–900 total; will exceed 400-line review budget; `size:exception` discussion required

## 1. Intent

Replace the `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` stub in `openspec/specs/workspace/spec.md` with a concrete, read-only `flow workspace dashboard` subcommand that renders consolidated workspace state (project list + needs-attention matrix + archived projects) using `rich` tables/panels/colors in the terminal. Mutations stay in the existing Phase 4 CLI verbs (`flow workspace fix`, `flow workspace archive`, `flow workspace restore`). This is the **first user interface** in the workspace-intelligence arc; the architecture principle is **observability first, interactivity second** (Pattern #536).

## 2. User-Locked Approach (Approach E — No New Framework)

| Constraint | Value | Source |
|---|---|---|
| Framework | **Rich only** (no TUI, no web, no new deps) | User lock + explore #535 verdict |
| Mutability | **Read-only** (no mutations from dashboard) | User lock |
| New deps | **Zero** — `rich` is already transitive via `uv.lock:1215` | User lock + pyproject.toml verification |
| Phase 5.2 | TUI/web deferred if MVP falls short | User lock |
| Architecture | Observability first, interactivity second | Pattern #536 |
| Wall-clock target | 7–13 hours (cheapest of 5 approaches) | Explore forecast |
| LOC target | 300–900 (likely exceeds 400-line budget) | Explore forecast |

**Why E over the other 4**:
- A (Textual TUI) — deferred to Phase 5.2 if E falls short
- B (FastAPI+HTMX) — deferred to Phase 5.2 if E falls short
- C (Streamlit) — deferred to Phase 5.2 if E falls short
- D (Hybrid) — deferred to Phase 5.2 if E falls short

**Rich dep verification**: `pyproject.toml` lines 9–16 lists 6 direct deps (`click`, `jinja2`, `watchdog`, `pydantic`, `pyyaml`, `numpy`). `rich` is **not** a direct dep. It appears in `uv.lock:1215` as a transitive dep (likely via click 8.1+). Promotion to direct dep is zero-cost; no new packages are installed. Must verify in `uv.lock` before commit.

## 3. Single CLI Subcommand

**Name**: `flow workspace dashboard`
**Registration**: `@workspace_group.command()` at `cli.py:2990` (same level as `status`, `fix`, `archive`, `archived`, `restore`)

```
flow workspace dashboard [--filter RULES] [--sort FIELD] [--no-color]
```

| Flag | Type | Default | Description |
|---|---|---|---|
| `--filter RULES` | optional | all | Show only projects matching needs-attention rules (R1, R2, R3, R4, R5; repeatable) |
| `--sort FIELD` | optional | `name` | Sort by `name` / `path` / `needs-count` |
| `--no-color` | flag | off | Disable Rich colors (for CI / piping) |

**No `--fix`, no `--archive` flags** — this command is read-only. Mutations stay in `flow workspace fix` / `flow workspace archive` / `flow workspace restore`.

## 4. Display Layout (Rich)

### Section A — Header Panel
- Total projects, total archived, total needs-attention, per-rule breakdown (R1: X, R2: Y, …)
- Run timestamp

### Section B — Needs-Attention Table
- Columns: `project name` | `path (truncated)` | R1 | R2 | R3 | R4 | R5 | `total-needs`
- Color coding: **red** ≥3 needs, **yellow** 1–2, **green** 0
- Sortable via `--sort`

### Section C — Archived Projects
- Simple list: name + path + archived_at + reason (from DS5 / registry)

### Section D — Footer
- Tip: `Run flow workspace status --json for JSON output`
- Tip: `Run flow workspace fix <project> --yes --backup to remediate`

## 5. Data Sources

| ID | Source | Use in dashboard |
|---|---|---|
| **DS1** | `flow projects ls --json` (subprocess) | Project list + 14 metadata fields |
| **DS2** | `flow workspace status --json` (subprocess) | 5-rule needs-attention aggregation |
| **DS5** | `~/.flow-engineering/registry.json` (direct read) | Archived projects list + reason |
| DS3 | `flow workspace {fix,archive,restore}` | **NOT used** — read-only MVP |
| DS4 | `flow where` | **NOT used** — deferred to Phase 5.2 if needed |

**Subprocess pattern**: `subprocess.run(["flow", "projects", "ls", "--json"], capture_output=True, text=True)` — same pattern as Phase 1/3 DS consumption.

**Registry read pattern**: `load_registry()` from `flow_engineering.registry` — already handles missing file → empty default.

## 6. New Files

| File | Role |
|---|---|
| `src/flow_engineering/dashboard.py` | New module: Rich rendering + subprocess wrappers + flag handling |
| `tests/unit/test_dashboard.py` | Unit tests: subprocess mocks, JSON parsing, filter/sort logic, Rich rendering, color logic |
| `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` | Delta spec (produced by sdd-spec) |
| `openspec/changes/phase-5-dashboard/design.md` | Architecture + data flow (produced by sdd-design) |
| `openspec/changes/phase-5-dashboard/tasks.md` | Task breakdown (produced by sdd-tasks) |

**Files modified**: `src/flow_engineering/cli.py` (one new `@workspace_group.command(name="dashboard")` handler, ~20 LOC)

**Files NOT modified**: `workspace_hygiene.py`, `registry.py`, existing Phase 1/2/3/4 CLI handlers, `pyproject.toml` (rich already transitive)

## 7. Acceptance Criteria

| # | Criterion | How verified |
|---|---|---|
| AC1 | `flow workspace dashboard` is registered as a Click command under `workspace_group` | `flow workspace --help` shows `dashboard` |
| AC2 | Default output is Rich table format (summary + needs-attention table + archived list) | Visual + snapshot test |
| AC3 | Subprocess call to `flow projects ls --json` succeeds | Mock subprocess; verify JSON parsing |
| AC4 | Subprocess call to `flow workspace status --json` succeeds | Mock subprocess; verify 5-rule aggregation |
| AC5 | Registry file read works (missing file → empty default) | Test with missing/malformed registry |
| AC6 | `--filter RULES` filters needs-attention table | e.g. `--filter R2` shows only no-git projects |
| AC7 | `--sort FIELD` sorts projects | by name / path / needs-count |
| AC8 | `--no-color` disables Rich colors | Capture output; verify no ANSI codes |
| AC10 | Color coding: red ≥3 needs, yellow 1–2, green 0 | Unit test on color assignment logic |
| AC11 | Zero new runtime deps (uses only `rich`, already transitive) | `uv pip install --dry-run rich` adds nothing new |
| AC12 | AC9 byte-identical guard preserved (no code modifications to existing tests) | Full suite 1513/1513 still passes |
| AC13 | Full suite 1513/1513 still passes | `uv run --frozen pytest` green |
| AC14 | `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` resolved with actual REQs | sdd-spec expands the placeholder |
| AC15 | `flow workspace status` text output unchanged | Dashboard is read-only consumer only |

## 8. Root REQs (resolve PLACEHOLDER)

This PR replaces `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` in `openspec/specs/workspace/spec.md` with:

| REQ-ID | Title | Summary |
|---|---|---|
| REQ-WORKSPACE-DASHBOARD-SURFACE | CLI subcommand exists | `flow workspace dashboard` under `workspace_group`; renders to terminal by default; visual output only (no `--json` — machine-readable output is `flow workspace status --json`) |
| REQ-WORKSPACE-DASHBOARD-READ-ONLY | No mutations | Dashboard consumes state only; mutations stay in `flow workspace fix/archive/restore`; no `--fix`/`--archive` flags |
| REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1 | Reads DS1 | Invokes `flow projects ls --json` for project list (v1 envelope) |
| REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2 | Reads DS2 | Invokes `flow workspace status --json` for 5-rule aggregation |
| REQ-WORKSPACE-DASHBOARD-RENDERS-RICH | Rich output | Default uses Rich tables/panels/colors; `--no-color` disables |
| REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE | Interactive deferred | TUI/web frameworks, real-time updates, interactive mutations → Phase 5.2 |

## 9. Out of Scope (explicit)

- NO TUI frameworks (Textual, urwid, Rich Live, prompt_toolkit, Blessed)
- NO web frameworks (FastAPI, Streamlit, Dash, Panel, Flask, Tauri)
- NO new runtime dependencies (`rich` already transitive)
- NO mutations from dashboard (read-only MVP)
- NO real-time updates / file watching / websocket
- NO interactive forms / prompts / buttons
- NO mobile support / i18n / theming
- NO historical data / audit log / trends
- NO multi-user support
- NO modifications to Phase 4 mutation gates (pollution-protocol triple, `MutationGateError`, `EmptyProjectError` stay intact)
- NO modifications to Phase 1/2/3 commands
- NO modifications to `openspec/changes/v1.1-followups/`
- NO `stash`-triggering words (§7 L300 of `workspace/spec.md` stays)

## 10. Open Questions (resolved)

| Q | Resolution |
|---|---|
| Q1 (TUI vs web) | Deferred to Phase 5.2; MVP is Rich-only enhanced CLI |
| Q2 (read-only vs interactive) | Read-only MVP; no mutations from UI |
| Q3 (real-time vs on-demand) | On-demand only (run command to refresh) |
| Q11 (new deps) | Zero-deps discipline preserved (uses only `rich` already transitive) |
| All others | Deferred to Phase 5.2 or N/A for MVP scope |
| Q: Why no `--json` on dashboard? | **One identity per command.** `flow workspace dashboard` is for human operators (visual). Machine-readable output stays at `flow workspace status --json` (existing Phase 3 endpoint). Adding `--json` to dashboard would duplicate `flow workspace status --json` AND blur the dashboard's identity as a visual tool. |

## 11. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| LOC exceeds 400-line review budget (forecast 300–900) | **HIGH** | `size:exception` per Phase 1 (543 LOC) + Phase 3 (735 LOC) precedent; OR chained PR |
| Subprocess latency (~100–200ms per DS1/DS2 call) | **MEDIUM** | Acceptable for on-demand; no daemon overhead |
| Windows cp1252 encoding on non-ASCII project names | **MEDIUM** | ASCII-safe fallback; `--no-color` for piping; Rich handles Unicode when console supports it |
| Rich output too wide for narrow terminals (>200 cols) | **MEDIUM** | Column truncation + responsive layout |
| Rich output hard to snapshot-test | **MEDIUM** | Golden text tests; plain-text rendering for CI |
| Color accessibility (colorblind users) | **LOW** | Text labels (R1, R2, …) alongside colors |
| Discovery: `dashboard` not found in `--help` | **LOW** | Ensure examples in help text |
| Rendering 100+ projects may be slow | **LOW** | Benchmark; lazy rendering if needed |

## 12. PR Strategy Decision

**Option A — Single PR with `size:exception`**: Matches Phase 1 (543 LOC) + Phase 3 (735 LOC) precedent. Simpler workflow. Approximate LOC: 300–900.

**Option B — Chained PR**:
- PR1: `flow workspace dashboard` skeleton + subprocess wrappers (DS1 + DS2 read)
- PR2: Rich rendering + color coding
- PR3: Filters + sort + `--no-color` + tests

Recommended: **Option A with `size:exception`** — Phase 1/3 precedent + single smaller scope than Approaches A–D.

## 13. Forecast

| Metric | Value |
|---|---|
| Total LOC | 300–900 (impl + tests) |
| New deps | 0 (rich already transitive) |
| Strict TDD | ON; tests required for subprocess wrappers, JSON parsing, Rich rendering, flag handling, filter/sort/color logic |
| Wall-clock | 7–13 hours total (explore: 1h + propose: 20m + spec: 30m + design: 45m + tasks: 20m + apply: 3–6h + verify: 1–2h + archive: 15m) |
| Phase 5.2 scope | TUI (Approach A/Textual) or web (Approach B/FastAPI+HTMX) if MVP insufficient |

## 14. Rollback Plan

- Revert: `git revert <sha>` — removes `dashboard.py` + CLI registration + tests
- No registry migrations (read-only consumer)
- No state migrations (no new files written by dashboard)
- Byte-identical guard on Phase 1/3/4 contracts preserved
