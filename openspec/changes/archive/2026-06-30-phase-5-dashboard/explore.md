<!-- explore.md: phase-5-dashboard. Source: sdd-explore for `phase-5-dashboard` (change #N+1, 2026-06-30). First feature change in the workspace-intelligence arc after 4 deltas + 2 cleanup cycles + 1 surgical fix. Read-only investigation; surfaces alternatives + tradeoffs for TUI vs web dashboard. User-locked: "Phase 5 define superficie de producto, no es cleanup mecánico." -->
# Explore: phase-5-dashboard — Phase 5 of workspace-intelligence

> Read-only investigation. NO source files modified. NO dependencies added. NO premature commitment.
>
> First feature change in the workspace-intelligence arc after 4 deltas (Phase 1 `projects-ls-extension`, Phase 2 `flow-where-cross-project`, Phase 3 `workspace-status`, Phase 4 `workspace-hygiene`) + 2 cleanup cycles (`workspace-capability-bootstrap`, `flow-where-cross-project-capability-merge`) + 1 surgical fix (`workspace-spec-cross-impact-cleanup`). User-locked mandate: "explorar TUI vs web dashboard ... No implementar todavía; primero sdd-explore con alternativas y tradeoffs."

## Goal

Surface **alternatives + tradeoffs** for a Phase 5 dashboard — the **first USER INTERFACE** surface in the workspace-intelligence arc. Phase 1-4 produced **read-side JSON envelopes + read-side aggregations + write-side mutation verbs**, all consumed from a terminal via `click.echo` text/JSON. Phase 5 introduces a **graphical** layer that visualizes workspace state (registry + needs_attention + per-project metadata + archived list + cross-project where hits) and optionally triggers mutations (`flow workspace fix`, `flow workspace archive`).

**This explore artifact does NOT pick a winner.** It surfaces 5 distinct approach candidates (2 TUI, 2 web, 1 hybrid), 4 hybrid alternatives, and 10+ open scope questions for the user to decide.

## Scope

### In (this explore phase)

- Inventory of existing data sources (5 commands + registry + graphify)
- Survey of TUI alternatives (Textual, Rich, urwid, prompt_toolkit, Blessed, textual-web)
- Survey of web dashboard alternatives (FastAPI+HTMX, FastAPI+React, Streamlit, Dash, Panel, Flask, Tauri)
- Hybrid alternatives (CLI-watch loop, native GUI, browser extension, JSON-RPC)
- Scope questions (8 single-axis forks)
- 5 approach candidates with full pros/cons/LOC/time-to-prototype/maintenance
- 10+ open questions for user
- Tech debt + dependency surface analysis
- Risk register
- Forecast for full SDD cycle (explore → propose → spec → design → tasks → apply → verify → archive)
- Verdict: recommend 2-3 candidates with rationale; **DO NOT pick a winner**

### Out (this explore phase)

- Any source code modification
- Any dependency addition to `pyproject.toml`
- Any spec.md / design.md / tasks.md artifacts (those land in later phases)
- Any test file modification
- Any archive move
- Touching `openspec/changes/v1.1-followups/` (explicitly off-limits)
- Touching any existing specs or code (explicitly off-limits)

### Out (Phase 5 proper — deferred to sdd-propose / sdd-spec)

- Implementation of any chosen approach
- Resolution of the open questions (those are user-decisions, not explore decisions)
- TDD task breakdown
- BDD scenario authoring
- Verify report authoring

## Existing Data Sources Inventory

The Phase 5 dashboard would consume (read) and possibly produce (write) data from 5 existing surfaces. Each is read-only-safe today; only `workspace_hygiene` carries mutation semantics.

### DS1: `flow projects ls [--json]` — project metadata enumeration (Phase 1)

| Field | Value |
|-------|-------|
| Command | `flow projects ls [--root PATH] [--json]` |
| Module | `src/flow_engineering/cli.py:3539` (`projects_ls`) |
| Helper | `_detect_project_markers(project_dir)` at `cli.py:3458` |
| Output shape (text) | 4-col fixed-width table: NAME, TYPE, FLOW, README |
| Output shape (JSON) | v1 envelope: `{"version": "1", "root": str, "projects": [14-field objects]}` |
| 14 fields per project | `name`, `path`, `has_git`, `branch`, `dirty`, `remote`, `stack`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`, `type`, `has_flow`, `readme_first_line` |
| Refresh rate | On-demand (no daemon) |
| Mutation capability | **Read-only** — does not create or modify the registry (REGRESSION GUARD) |
| Phase 1 contract | **AC9 byte-identical** — `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` remains green throughout Phase 5 |
| Approximate render time | ~50-200ms for 10-30 projects (3 git subprocess calls per project + 1 stack probe + 1 test-command probe) |

### DS2: `flow workspace status [--json]` — needs-attention aggregation (Phase 3)

| Field | Value |
|-------|-------|
| Command | `flow workspace status [--root PATH] [--json]` |
| Module | `src/flow_engineering/cli.py:2995` (`workspace_status`) + helpers `_summarize_workspace_status`, `_workspace_status_envelope`, `_workspace_status_tags`, `_render_workspace_status_text` at `cli.py:2877-2987` |
| Output shape (text) | Tagged list with `[DIRTY]`, `[NO-GIT]`, `[NO TESTS]`, `[NO OPENSPEC]` suffixes + SUMMARY block |
| Output shape (JSON) | v1 envelope: `{"version": "1", "root": str, "totals": {8 fields}, "projects": [...], "needs_attention": [{"name", "path", "reasons": [...]}]}` |
| 5 rules | R1 dirty-git (deferred remediation), R2 no-git, R3 no-tests, R4 no-openspec-on-SDD-stack, R5 no-graphify (informational only) |
| Refresh rate | On-demand (no daemon) |
| Mutation capability | **Read-only** |
| Phase 3 contract | **AC9 byte-identical** — JSON envelope for unchanged FS state is byte-deterministic (no timestamp fields; sorted project list) |
| Approximate render time | Sum of DS1 + O(N) classification pass |

### DS3: `flow workspace {fix,archive,archived,restore}` — write-side surface (Phase 4)

| Field | Value |
|-------|-------|
| Commands | 4 verbs attached to `workspace_group` at `cli.py:2990` |
| Module | `src/flow_engineering/cli.py:3156-3343` (4 Click handlers) + `src/flow_engineering/workspace_hygiene.py` (orchestrator) + `src/flow_engineering/registry.py` (pydantic models + atomic I/O) |
| Output shape (fix) | One-line text: `[DRY-RUN] {action_taken} on {project}: success={bool}` (NO `--json` per REQ-HYGIENE-NO-JSON-MVP) |
| Output shape (archive) | One-line text: `archived: {project} (reason: {reason})` |
| Output shape (archived) | 3-col text table (NAME, ARCHIVED_AT, REASON) or `(no archived projects)` |
| Output shape (restore) | One-line text: `restored: {project}` |
| Exit codes | 0 = success/dry-run, 2 = mutation-gate refusal / verify failure / `--yes` missing |
| Refresh rate | On-demand (no daemon) |
| Mutation capability | **WRITE** — `git init`, registry mutations; pollution-protocol triple; dry-run default; `--yes` + `--backup` gates |
| Registry schema v1 | `~/.flow-engineering/registry.json` — `version: 1`, `projects: [ProjectEntry]`, `archived: [ArchivedEntry]` |
| Registry fields per project | `name`, `path`, `has_git`, `has_openspec`, `has_tests`, `has_graphify`, `last_status_check` |
| Registry fields per archived | `name`, `path`, `archived_at`, `reason` |

### DS4: `flow where <query> [--root PATH] [--format text|json|tsv] [--regex]` — cross-project search (Phase 2)

| Field | Value |
|-------|-------|
| Command | `flow where "<query>" [--limit N] [--no-graph] [--root PATH] [--format text\|json\|tsv] [--regex] [--engram]` |
| Module | `src/flow_engineering/cli.py:685` (`where_cmd`) + `src/flow_engineering/where.py` (3 backends: grep_repo, grep_sdd_archive, grep_graphify + orchestrator) |
| Output shape (text) | ASCII-safe grouped text: per-project section + TOTAL line |
| Output shape (JSON) | v1 envelope: `{"version": "1", "root", "query", "format", "results": [...], "totals": {projects_searched, matches}, "engram": {enabled, phase}}` |
| Output shape (TSV) | Header `project\tfile\tline\ttype\tcontent` + rows |
| 6 dirs per project | `src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/` (locked; missing dirs silently skipped) |
| Refresh rate | On-demand (no daemon) |
| Mutation capability | **Read-only** — never mutates |
| Approximate render time | 100ms-2s for N=10-30 projects (rg subprocess fan-out) |
| Exit codes | 0 = matches, 1 = no matches, 2 = bad regex / unreadable root |

### DS5: Registry file at `~/.flow-engineering/registry.json` — persistent state

| Field | Value |
|-------|-------|
| Path | `~/.flow-engineering/registry.json` (via `registry_path()` at `registry.py:118`) |
| Schema version | 1 (pydantic `Literal[1]` discriminator; `extra="forbid"`) |
| Read-only consumer | `flow projects ls --json`, `flow workspace status` (MUST NOT write) |
| Write-only consumer | `flow workspace fix`, `flow workspace archive`, `flow workspace restore` |
| Atomic write | `tempfile.mkstemp` + `os.replace` + `os.fsync` (mirrors `project_aliases.save_aliases` precedent) |
| Missing-file behavior | Empty default `{version: 1, projects: [], archived: []}` for read; created on first mutation |
| Malformed behavior | `RegistryError` with user_message; CLI exits 2 |

### DS6: Backup directory at `~/.flow-engineering/backups/` (mutation-related)

| Field | Value |
|-------|-------|
| Path | `~/.flow-engineering/backups/<project_name>/<UTC-ISO-timestamp>/` |
| Layout | `manifest.json` + `files/` (recursive copy, `.git/` excluded) |
| Retention | INDEFINITE in MVP (no auto-cleanup; manual cleanup is operator's responsibility) |
| Mutation consumer | `_snapshot_project` at `workspace_hygiene.py:244` |

### Cross-cutting constraints (binding for Phase 5)

| Constraint | Source | Impact |
|------------|--------|--------|
| **AC9 byte-identical** on `flow projects ls --json` | Phase 1 verify-report | Phase 5 dashboard MUST NOT mutate the v1 envelope shape; reading is OK |
| **AC9 byte-identical** on `flow workspace status --json` | Phase 3 verify-report | Phase 5 dashboard MUST NOT mutate the v1 envelope shape; reading is OK |
| `flow where` argv-list seam (`_run_search`) | Phase 2 design D1 | Phase 5 dashboard MAY consume `where` orchestrator; MUST NOT touch private helpers |
| Pollution-protocol triple for write-side | Phase 4 design D2 | Phase 5 dashboard MAY trigger `flow workspace fix`; MUST NOT bypass gates |
| `--json` is INTENTIONALLY ABSENT from `flow workspace {fix,archive,restore}` | Phase 4 REQ-HYGIENE-NO-JSON-MVP | Dashboard triggering these via subprocess MAY NOT be able to parse status; needs text parsing OR refactor |
| Windows cp1252 encoding limit | Phase 2 verify-report S1 | Dashboard output MUST be ASCII-safe (no Unicode in fixed-width tables) |
| NO new runtime dependencies (all 6 prior cycles) | pyproject.toml precedent | Adding `textual` / `streamlit` / `fastapi` is a **HARD departure**; user-locked decisions needed |

## TUI Alternatives Survey

The 6 TUI candidates below differ in API surface, mouse support, async model, and learning curve. Each was evaluated against: (a) Python 3.12 compatibility, (b) maintenance burden, (c) data-shape fit, (d) prior art in flow-engineering.

### T1: Textual (https://textual.textualize.io/) — modern async-first TUI

| Field | Value |
|-------|-------|
| Version | v4.0.0+ (current as of 2026-01-26) |
| Python compat | Python 3.9+; **fully compatible with Python 3.12** (textualize/docs/getting_started.md) |
| API model | Async-first (textual `App` + `Widget` classes; uses `asyncio` internally) |
| Mouse support | Yes — full mouse events (`on_click`, `on_hover`, etc.) |
| Widget set | `DataTable` (column-sortable, cursor-aware), `Tree`, `ListView`, `Static`, `Input`, `Button`, `Select`, `TabbedContent`, `ModalScreen`, `LoadingIndicator` |
| CSS-like styling | Yes (`*.tcss` files — Textual CSS) |
| Cross-platform | Yes (Linux + macOS + Windows); Windows Terminal recommended on Win32 |
| Existing dep? | **NO** — would require adding `textual>=4.0` to `pyproject.toml` |
| Existing precedent in flow-engineering | **NO** — codebase is sync-first (no `asyncio` anywhere in `src/`) |
| Learn curve | Moderate — async + CSS + reactive properties is a triple learning surface |
| Render quality | Excellent for tabular data (DataTable widget supports sort/filter/cursor natively) |
| Test strategy | Textual ships `test-cli` snapshot harness; otherwise asyncio-based driving via Pilot |
| Maintenance | High — async surface + CSS coupling requires careful architecture |

**Key insight from Context7 docs**: `DataTable` natively supports column sort, row add/remove, cursor navigation, and `coordinate_to_cell_key` for click-driven selection. This is a strong fit for the workspace-status visualization (5 rules + tags per project).

**Async cost**: Textual requires async functions for most reactive operations. The current `cli.py` is fully sync. Mixing sync Click handlers with async Textual app requires an `asyncio.run()` bridge inside the `flow workspace tui` handler, which is non-trivial but well-documented in the Textual `App.run_async()` API.

**Verdict on T1**: Best widget richness, but highest paradigm shift. Strongest fit if the dashboard wants mouse-driven interactivity (click project → see details → click "archive" → invoke subprocess).

### T2: Rich (https://rich.readthedocs.io/) — formatting library (not full TUI)

| Field | Value |
|-------|-------|
| Version | v15.0.0 (current; matches `uv.lock:1215`) |
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| API model | Sync; rendering-focused (Live + Progress + Table + Layout) |
| Mouse support | **No** — Rich is one-way rendering, not a full TUI |
| Widget set | `Table`, `Panel`, `Tree`, `Layout` (split-screen), `Progress`, `Live`, `Markdown`, `Syntax`, `Console` |
| Existing dep? | **TRANSITIVE ONLY** — `rich` is in `uv.lock:1215` as a transitive dependency (likely via click 8.1+, jinja2, or pytest), **NOT** in `pyproject.toml:9-16` direct deps |
| Existing precedent | **NO direct use** in `flow_engineering/` |
| Learn curve | Low — markup + Console methods are intuitive |
| Render quality | Excellent for tabular data, colors, layouts; renders to any terminal |
| Test strategy | Snapshot rendering against golden output strings; no async |
| Maintenance | Low — sync API; no architectural change |

**Critical precedent**: `flow-where-mvp` proposal D9 explicitly chose **text-only output (NOT Rich)** for the dashboard density-vs-zero-deps tradeoff. Verbatim from `archive/2026-06-27-observability-pr1/design.md:751`:

> "Dashboard format choice — text-only (like `flow drift`) OR interactive (rich/tui)? **TEXT-ONLY via `click.echo`.** Verified `pyproject.toml` has NO `rich` runtime dep (only transitive via `uv.lock`); no new runtime dep added. Mirrors the precedent from `flow drift`, `flow status`, `flow snapshot list`. `rich` is on the v2 watch list if dashboard density grows."

This sets the **institutional precedent** that `rich` is deferred until dashboard density requires it. Phase 5 IS that moment — but the precedent also says "use Rich only for rendering density, not for full TUI". A middle-ground interpretation: use `rich.Table` + `rich.Layout` for the dashboard rendering, but NOT Textual (which is a full async TUI framework).

**Verdict on T2**: Strongest fit for the "rich text + dense tables" use case. Lowest paradigm shift. But lacks mouse + interactivity. Best as **Option E** (no new framework) with `rich` promoted from transitive to direct dep.

### T3: urwid — older but battle-tested TUI

| Field | Value |
|-------|-------|
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| API model | Sync; widget-tree based |
| Mouse support | Yes |
| Widget set | `ListBox`, `SimpleListWalker`, `Frame`, `Columns`, `Pile`, `Text`, `Edit`, `Button`, `CheckBox`, `RadioButton`, `AttrMap` |
| Existing dep? | **NO** — would require adding `urwid>=2.6` |
| Existing precedent | **NO** |
| Learn curve | Moderate-high — widget-tree API is verbose |
| Render quality | Excellent — palette + attribute model is mature |
| Test strategy | `urwid.testing` has `run_tui` + `urwid.command_map` for harness driving |
| Maintenance | High — verbose API; less idiomatic for modern async |

**Verdict on T3**: Mature but the API surface is verbose. urwid makes sense for a long-running full-screen console app, but is overkill for "render 30 rows of project state". Lower-priority than T1.

### T4: prompt_toolkit — interactive prompts (not full dashboards)

| Field | Value |
|-------|-------|
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| API model | Sync (uses `eventloop` for asyncio) |
| Mouse support | Yes |
| Widget set | `Prompt`, `Confirmation`, `CheckboxList`, `RadioList`, `Completions` |
| Existing dep? | **NO** — but very common |
| Existing precedent | **NO** |
| Learn curve | Low for prompts; high for full-screen apps |
| Render quality | Excellent for short interactions |
| Test strategy | `prompt_toolkit.input` fake creators |
| Maintenance | Low — well-maintained |

**Verdict on T4**: Wrong tool. prompt_toolkit is designed for **question/answer flows**, not **continuous dashboards**. Skip for Phase 5 unless the user wants a "click project → confirm archive" flow (and even then, Click's `click.confirm()` + `click.prompt()` are simpler).

### T5: Blessed — minimal terminal wrapper

| Field | Value |
|-------|-------|
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| API model | Sync; thin wrapper over curses |
| Mouse support | Limited (depends on terminal) |
| Widget set | Minimal — `Terminal` wrapper + style helpers |
| Existing dep? | **NO** — would require adding `blessed>=1.20` |
| Existing precedent | **NO** |
| Learn curve | Low |
| Render quality | Adequate |
| Test strategy | Mock terminal |
| Maintenance | Low |

**Verdict on T5**: Too low-level. The right tool for "draw a box + move cursor" but not for "render 30 rows + handle clicks". Skip.

### T6: textual-web / textual-serve — Textual in the browser via WebSocket

| Field | Value |
|-------|-------|
| Library | `textual-serve` / `textual-web` (textualize/textual-serve on Context7) |
| Mechanism | Runs the Textual app in a subprocess; exposes it via WebSocket + browser |
| Python compat | Same as Textual (3.9+) |
| Use case | Remote/sharing — same Textual code, browser-rendered |

**Verdict on T6**: Same Textual cost (async + CSS) but without the "browser opens automatically" tradeoff. Worth considering ONLY if the user wants TUI code with optional remote rendering. Adds the Web framework cost (FastAPI or Starlette) for the browser layer.

### TUI Summary

| Library | Verdict | When to choose |
|---------|---------|----------------|
| **Textual** | Best widget richness; high paradigm shift (async + CSS) | Dashboard needs mouse + multi-pane + sorting + filtering |
| **Rich** | Best fit for the "render density" use case; lowest cost; existing transitive dep | Dashboard is read-only visualization with colored tables |
| **urwid** | Mature but verbose; overkill | Long-running full-screen console app (out of scope) |
| **prompt_toolkit** | Wrong tool (prompts, not dashboards) | Skip |
| **Blessed** | Too low-level | Skip |
| **textual-web/serve** | Same Textual cost + remote rendering | Only if TUI code wants optional browser layer |

## Web Dashboard Alternatives Survey

The 8 web candidates differ in frontend complexity, deployment model, and Python-only vs split-stack.

### W1: FastAPI + HTMX — server-rendered, minimal JS

| Field | Value |
|-------|-------|
| FastAPI version | 0.115+ (current) |
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| Frontend | HTMX 1.x (~14KB) + Server-Sent Events (SSE) for live updates |
| Existing dep? | **NO** — would require adding `fastapi>=0.115` + `uvicorn[standard]>=0.30` + `jinja2>=3.1` (jinja2 IS already a dep) + `htmx` (served as static asset, no Python pkg) |
| Browser opens automatically | Yes — `flow workspace web --open` opens `http://localhost:PORT` in default browser |
| Local-only | Default (binds to `127.0.0.1`); `--host 0.0.0.0` for remote |
| Real-time updates | SSE is trivial in FastAPI (`StreamingResponse`); polling is fallback |
| Resource usage | Light — FastAPI idle ~30MB; HTMX page ~50KB |
| Test strategy | `fastapi.testclient.TestClient` + httpx async client; standard HTTP testing |
| Maintenance | Low-medium — server-rendered means no separate frontend build |

**Verdict on W1**: Best balance for a local-only dashboard. Server-rendered = no SPA build = simpler CI. SSE = trivial real-time updates. HTMX = minimal JS skill required. Strongest candidate if the user wants "browser opens, shows data, refresh button works".

### W2: FastAPI + React/Vue/Svelte — full SPA

| Field | Value |
|-------|-------|
| Python backend | Same as W1 (FastAPI) |
| Frontend | React 18 / Vue 3 / Svelte 4 + Vite build |
| Build complexity | High — Vite config, TypeScript, JSX, npm install, asset bundling |
| Existing dep? | **NO** — would require FastAPI + a frontend toolchain (`node`, `npm`, `vite`) |
| Browser opens automatically | Yes |
| Real-time updates | WebSocket from FastAPI; mature pattern |
| Resource usage | Medium — FastAPI + bundled JS |
| Test strategy | Backend: TestClient; Frontend: Vitest/Jest + Playwright |
| Maintenance | High — two languages, two build pipelines, two deploy units |

**Verdict on W2**: Maximum flexibility but maximum complexity. Overkill unless the user wants a Grafana-style dashboard with charts, multi-tab navigation, and rich interactions. The team would need JS/TS expertise; the codebase has zero JS today.

### W3: Streamlit — Python-only dashboards

| Field | Value |
|-------|-------|
| Version | 1.54.0+ (current per Context7) |
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| Frontend | None (Python-only; Streamlit renders React under the hood) |
| Existing dep? | **NO** — would require adding `streamlit>=1.54` + `streamlit-autorefresh` (for polling) |
| Browser opens automatically | Yes — Streamlit starts a local server, prints URL |
| Real-time updates | `st_autorefresh` for polling; manual rerun otherwise |
| Resource usage | Medium — Streamlit runtime ~80-150MB idle |
| Test strategy | `streamlit.testing.v1.AppTest` for unit testing |
| Maintenance | Low — Python-only; Streamlit updates handle frontend |

**Verdict on W3**: Fastest to prototype. Weakest customization (Streamlit's "form-driven" model limits free-form layout). If the dashboard is "show project table + filter + click to archive", Streamlit is 50-150 LOC. If the dashboard is "multi-pane with reactive updates", Streamlit fights you.

### W4: Dash (Plotly) — Python-only analytical dashboards

| Field | Value |
|-------|-------|
| Python compat | Python 3.8+; **fully compatible with Python 3.12** |
| Frontend | None (Dash renders React + Plotly.js) |
| Existing dep? | **NO** — would require `dash>=2.18` + `plotly>=5.24` |
| Real-time updates | `dcc.Interval` for polling; WebSocket via `dash-extensions` |
| Resource usage | Medium — Plotly.js is ~3MB; Dash runtime ~50MB |
| Test strategy | Selenium + Dash `dash.testing` |
| Maintenance | Medium — callback graph is powerful but complex |

**Verdict on W4**: Designed for analytical dashboards (charts, scatter plots, histograms). The workspace-state dashboard is **not analytical** — it's CRUD. Dash is overkill; use it only if the user wants graphs over time (e.g., "R2 count over last 30 days").

### W5: Panel (HoloViz) — Python-only similar to Dash

| Field | Value |
|-------|-------|
| Python compat | Python 3.9+; **fully compatible with Python 3.12** |
| Frontend | Bokeh.js (via Panel) |
| Existing dep? | **NO** — would require `panel>=1.5` + `bokeh>=3.6` |
| Real-time updates | `pn.state.add_periodic_callback` for polling |
| Maintenance | Medium — HoloViz ecosystem is mature but sprawling |

**Verdict on W5**: Similar to Dash. Overkill for CRUD; consider only if user wants Bokeh plots.

### W6: Flask + HTMX / Alpine.js — lightweight server-rendered

| Field | Value |
|-------|-------|
| Flask version | 3.0+ (current) |
| Existing dep? | **NO** — would require `flask>=3.0` |
| Comparison to FastAPI | Flask is simpler; FastAPI has better async + OpenAPI |

**Verdict on W6**: W1 is strictly better than W6 for this use case (FastAPI's async is needed for SSE; Flask would need `flask-sse` extension).

### W7: Static HTML page served by Flow — minimal HTML + JS

| Field | Value |
|-------|-------|
| Mechanism | `flow workspace web --static` writes `index.html` + reads `flow workspace status --json` |
| Existing dep? | **NO** — pure HTML + vanilla JS, no framework |
| Real-time updates | Polling (`setInterval` + fetch) |
| Maintenance | Very low |

**Verdict on W7**: Useful for "preview without a server" — the user opens `index.html` in a browser. But polling for 10s refresh = inefficient; requires the JSON envelope to be regenerated each time.

### W8: Tauri (Rust + WebView) — local-first desktop app

| Field | Value |
|-------|-------|
| Mechanism | Rust backend + WebView frontend (HTML/CSS/JS); bundles to .exe/.app/.deb |
| Existing dep? | **NO** — requires Rust toolchain + `cargo install tauri-cli` |
| Distribution | Binary distribution; needs code signing on macOS/Windows |
| Maintenance | High — Rust + JS + Tauri-specific config |

**Verdict on W8**: Adds an entire Rust toolchain to a Python codebase. Categorically too heavy for a Phase 5 dashboard.

### Web Summary

| Library | Verdict | When to choose |
|---------|---------|----------------|
| **FastAPI + HTMX** | Best balance for local-only dashboard | Local server, browser auto-opens, refresh + filter are the main UX |
| **FastAPI + React/Vue** | Maximum flexibility; maximum complexity | Multi-pane rich UX with charts/graphs |
| **Streamlit** | Fastest prototype; weakest customization | "I need this in 2 days, I don't care about UX perfection" |
| **Dash (Plotly)** | Overkill for CRUD | Analytical charts over time |
| **Panel (HoloViz)** | Overkill | Bokeh plots |
| **Flask + HTMX** | Inferior to FastAPI+HTMX | Skip |
| **Static HTML** | Limited (no live updates without polling) | Preview mode only |
| **Tauri** | Adds Rust toolchain | Categorically too heavy |

## Other / Hybrid Alternatives

### H1: CLI watch loop — `watch -n 5 flow workspace status`

| Field | Value |
|-------|-------|
| Mechanism | `watch -n 5 flow workspace status` (Linux/macOS) or `while ($true) { flow workspace status ; sleep 5 }` (PowerShell) |
| Dependency | None — just shell |
| Real-time updates | Polling at interval |
| Interactivity | None (read-only, refresh) |

**Verdict on H1**: Free. Zero new deps. No interactivity. Useful as a baseline UX but doesn't address "click to fix" or "filter by stack" use cases.

### H2: Native GUI — Tkinter, Qt (PySide6)

| Field | Value |
|-------|-------|
| Mechanism | Tkinter (stdlib) or PySide6 (heavy) |
| Existing dep? | Tkinter: yes (stdlib); PySide6: no |
| Cross-platform | Tkinter yes; PySide6 yes |
| Maintenance | High |

**Verdict on H2**: Categorical overkill. The codebase is terminal-first; adding a native GUI breaks the operator mental model. Skip.

### H3: Browser extension that reads JSON output — niche

| Field | Value |
|-------|-------|
| Mechanism | Chrome extension that POSTs `flow workspace status --json` output to a UI |
| Existing dep? | NO |
| Maintenance | Very high |

**Verdict on H3**: Maximum niche. The dashboard operator is the same person running `flow` — they'd need to copy-paste JSON between terminal and browser. Skip.

### H4: JSON-RPC server — infra-heavy

| Field | Value |
|-------|-------|
| Mechanism | `flow workspace serve --port 9999 --rpc` exposes JSON-RPC 2.0 endpoints |
| Existing dep? | NO (could implement with stdlib `xmlrpc.server` or `http.server`) |
| Use case | Other tools (editor plugins, scripts) integrate with workspace state |

**Verdict on H4**: Infra-heavy for a single-operator dashboard. If the user envisions integration with VS Code extensions or scripts, JSON-RPC is the right answer — but it's not a dashboard, it's an API. Combine with W1 for a hybrid: HTML dashboard that consumes the JSON-RPC.

### H5: Terminal-only enhancements — better CLI output + structured logs

| Field | Value |
|-------|-------|
| Mechanism | `flow workspace status --color --interactive --filter stack=Python`; structured JSON logs to `~/.flow-engineering/workspace.log` |
| Existing dep? | NO (or only ANSI escape codes via `colorama`) |
| Maintenance | Low |

**Verdict on H5**: The "no framework" path. Closest to the codebase's existing pattern (all output via `click.echo`). Could include `rich.Table` for density (promoting `rich` from transitive to direct dep — minimal cost).

### Hybrid Summary

| Alternative | Verdict | When to choose |
|-------------|---------|----------------|
| **H1: CLI watch loop** | Free baseline | "I just want auto-refresh, that's it" |
| **H2: Native GUI** | Overkill | Skip |
| **H3: Browser extension** | Niche | Skip |
| **H4: JSON-RPC server** | Infra-heavy | Future API integration (not Phase 5) |
| **H5: Terminal-only enhancements** | Lowest cost | Read-only visualization without leaving the terminal |

## Scope Questions (8 single-axis forks)

These questions are the **decision surface** for Phase 5. The explore artifact surfaces them; the user decides during propose phase.

| # | Question | Fork A | Fork B | Current state |
|---|----------|--------|--------|---------------|
| **SQ1** | **Single-user or multi-user?** | Local-only (one operator, one machine) | Shared team dashboard (network-served) | Codebase is single-user (all commands run from one terminal); SQ1a is the current assumption |
| **SQ2** | **Read-only or interactive?** | Read-only (visualization only) | Interactive (can trigger `flow workspace fix` from UI) | Phase 4 mutations exist; SQ2b unlocks the "click to fix" UX |
| **SQ3** | **Local-only or remote-capable?** | Local-only (`127.0.0.1:PORT`) | Network-served (`0.0.0.0:PORT` with auth) | SQ3a is the default for a CLI tool; SQ3b requires auth design |
| **SQ4** | **Real-time or on-demand?** | Real-time (WebSocket / SSE / file watch) | On-demand (manual reload / periodic poll) | DS1-DS4 are on-demand; real-time needs a daemon or watcher |
| **SQ5** | **Deployment model?** | `flow workspace tui` / `flow workspace web` subcommand opens ephemeral view | Always-on daemon watching `~/.flow-engineering/` | Subcommand is consistent with Phase 1-4 precedent; daemon is bigger scope |
| **SQ6** | **Visual priority — overview or detail?** | Many projects at once (overview: 30 rows, sortable, filterable) | One project at a time (detail: full status + recent activity) | Both are useful; depends on the operator's typical workflow |
| **SQ7** | **Historical data?** | Current state only (read DS2 + DS5) | Trends over time (audit log of fixes, archives, restores) | Phase 4 records `last_status_check` + `archived_at` but no event log; historical needs new data |
| **SQ8** | **Mobile-friendly or desktop-only?** | Mobile-friendly (responsive HTML) | Desktop-only (terminal / large browser) | Mobile adds CSS cost; dashboard density assumes desktop |

## Approach Candidates (5 distinct options)

Each candidate includes: stack, pros, cons, LOC estimate, time-to-prototype, maintenance burden, "when to choose this" guidance. Numbers are rough estimates based on similar codebases.

### Approach A — Textual TUI (in-shell dashboard, no browser)

| Aspect | Detail |
|--------|--------|
| **Stack** | `textual>=4.0` + `textual-serve>=1.0` (optional for remote) |
| **CLI** | `flow workspace tui [--root PATH]` |
| **Pros** | Stays in the operator's terminal (no context switch); mouse + keyboard input; rich widgets (DataTable for sortable projects, Tree for registry); mature async model; can subscribe to file-watch events |
| **Cons** | Adds 1 hard dependency (textual); paradigm shift to async; CSS coupling (`*.tcss` files); learning curve for the team; cp1252 Windows terminal caveats |
| **LOC estimate** | 800-1500 (200-300 app code + 200-300 widgets + 200-300 tests + 100-200 docs/CSS) |
| **Time-to-prototype** | 4-6 hours for a working table; 8-12 hours for interactive features (click-to-fix) |
| **Maintenance burden** | Medium-high — async + CSS + widget lifecycle |
| **When to choose** | Operator wants mouse-driven interactivity in the terminal; "I want to stay in my shell" mental model; multi-pane dashboard (projects on left, details on right, actions on bottom) |

### Approach B — FastAPI + HTMX (local web server, browser opens automatically)

| Aspect | Detail |
|--------|--------|
| **Stack** | `fastapi>=0.115` + `uvicorn[standard]>=0.30` + `jinja2>=3.1` (already dep) + HTMX (static asset) |
| **CLI** | `flow workspace web [--root PATH] [--port PORT] [--no-open]` |
| **Pros** | Browser auto-opens via `webbrowser.open(f"http://localhost:{port}")`; server-rendered = no SPA build pipeline; HTMX is minimal JS; SSE for real-time updates trivial in FastAPI; works on any OS with a browser; templates are Jinja2 (already in deps) |
| **Cons** | Adds 2 hard deps (fastapi + uvicorn); operator must leave terminal to browser; `--json` is INTENTIONALLY ABSENT from Phase 4 mutations → text parsing needed if dashboard triggers `flow workspace fix`; HTTP server lifecycle (start, stop, signal handling) |
| **LOC estimate** | 1000-2000 (300-500 routes + 300-500 templates + 300-500 tests + 100-200 lifecycle code) |
| **Time-to-prototype** | 6-10 hours for a working dashboard; 12-16 hours for interactive features |
| **Maintenance burden** | Medium — server-rendered is simpler than SPA; but HTTP server lifecycle adds a new surface |
| **When to choose** | Operator wants a richer UX than terminal can offer; willing to leave the shell for a browser tab; needs multi-pane layouts, color-coded statuses, visual buttons; team has web familiarity |

### Approach C — Streamlit (Python-only, fastest prototype)

| Aspect | Detail |
|--------|--------|
| **Stack** | `streamlit>=1.54` + `streamlit-autorefresh>=1.0` |
| **CLI** | `flow workspace web --streamlit` (subcommand variant) OR `python -m streamlit run flow_engineering.dashboard` |
| **Pros** | Fastest to prototype (50-150 LOC for basic dashboard); Python-only (no JS skill); Streamlit updates handle React frontend; auto-refresh via `st_autorefresh`; integrates with existing `_detect_project_markers` + `_summarize_workspace_status` helpers |
| **Cons** | Adds 2 hard deps; customization is limited (Streamlit's layout model is opinionated); "real" interactivity requires `st.session_state` tricks; dashboard is browser-only; Streamlit updates can break layouts |
| **LOC estimate** | 300-800 (200-400 dashboard script + 100-300 tests + 50-100 helpers) |
| **Time-to-prototype** | 2-4 hours for a working dashboard; 4-6 hours for filter + click-to-fix |
| **Maintenance burden** | Low — Python-only; Streamlit version bumps are stable |
| **When to choose** | Operator wants "it works today"; willing to accept Streamlit's UX limitations; "I don't care about polish, just give me visibility" |

### Approach D — Hybrid (Textual + FastAPI/HTMX for remote)

| Aspect | Detail |
|--------|--------|
| **Stack** | `textual>=4.0` + `textual-serve>=1.0` + FastAPI bridge |
| **CLI** | `flow workspace tui` (default) OR `flow workspace web [--serve]` |
| **Pros** | Best of both: TUI for in-shell use, web for sharing; shared data layer (`dashboard_state.py` module); common test fixtures |
| **Cons** | Highest LOC (both stacks); shared state needs careful design; two UX paths to maintain |
| **LOC estimate** | 1500-3000 (Textual app + FastAPI bridge + shared state + 2x tests) |
| **Time-to-prototype** | 12-18 hours for both surfaces; 20-30 hours for full feature parity |
| **Maintenance burden** | High — two stacks, two test suites, two UX paths |
| **When to choose** | Team wants both: operator uses TUI daily, occasional remote access for sharing/screenshots; long-term roadmap with both audiences |

### Approach E — No new framework (enhance CLI + promote `rich` to direct dep)

| Aspect | Detail |
|--------|--------|
| **Stack** | `rich>=15.0` (promoted from transitive to direct dep) + click (already dep) |
| **CLI** | `flow workspace status --colored --interactive` (new flags) + `flow workspace dashboard` (subcommand that prints a curated Rich view) |
| **Pros** | Lowest dependency cost (1 dep, already transitive); no paradigm shift; consistent with Phase 1-4 precedent; closest to existing `flow metrics summary` per-domain text dashboard; ASCII-safe by default; minimal new architecture |
| **Cons** | No mouse interactivity (Rich is render-only); "real-time" is `watch -n 5 flow workspace dashboard` from outside; cannot trigger mutations from UI; no remote/sharing |
| **LOC estimate** | 200-600 (100-200 dashboard rendering + 100-200 filters + 100-200 tests) |
| **Time-to-prototype** | 2-4 hours for a colored table; 4-6 hours for filter + multi-pane via Rich Layout |
| **Maintenance burden** | Lowest — pure CLI; consistent with all 4 prior cycles |
| **When to choose** | "Just give me visibility" with zero architectural change; consistent with the codebase's text-first DNA; the prior `flow-where-mvp` precedent explicitly deferred Rich but Phase 5 IS that watch-list moment |

### Approach Comparison Matrix

| Criterion | A: Textual | B: FastAPI+HTMX | C: Streamlit | D: Hybrid | E: Rich |
|-----------|------------|-----------------|--------------|-----------|---------|
| New deps | 1 (textual) | 2 (fastapi+uvicorn) | 2 (streamlit+autorefresh) | 3 | 0 (already transitive) |
| Mouse support | Yes | Yes (browser) | Yes (browser) | Both | No |
| Real-time updates | Native (file watch + reactive) | SSE/WebSocket | Autorefresh polling | Both | None (polling from outside) |
| Mobile-friendly | No | Yes (responsive HTML) | Yes | Yes (web half) | No |
| Interactive (trigger mutations) | Yes (subprocess) | Yes (form post → subprocess) | Yes (button click → subprocess) | Yes | No |
| Trigger mutation UX | Click button → subprocess | Click button → HTMX swap | Button click | Both | N/A |
| LOC estimate | 800-1500 | 1000-2000 | 300-800 | 1500-3000 | 200-600 |
| Time-to-prototype (hours) | 4-12 | 6-16 | 2-6 | 12-30 | 2-6 |
| Maintenance burden | Medium-high | Medium | Low | High | Lowest |
| Cp1252 Windows compatibility | Native (terminal) | Browser handles encoding | Browser handles encoding | Both | Native (terminal) |
| Consistent with `flow-where-mvp` D9 precedent (text-only) | NO | NO | NO | NO | YES |
| Consistent with `observability-pr1` design D8 (text-only summary) | NO | NO | NO | NO | YES |
| Team skill set required | Python async + CSS | Python web + HTML | Python only | Python async + CSS + web | Python only |
| Breaking changes to Phase 1-4 contracts | None | None | None | None | None |
| Browser opens automatically | N/A | Yes (via `webbrowser.open`) | Yes (Streamlit default) | Yes (web half) | N/A |

## Open Questions for the User (10+)

These are the explicit user-decision surface for Phase 5. Each question has a recommended default + rationale + counter-argument.

1. **Q1: TUI vs web — primary use case?**
   - **Recommended default**: **TUI (Approach E with `rich` promoted)** for read-only + **TUI/HTML hybrid (Approach B with FastAPI+HTMX)** for interactive.
   - **Tradeoff**: A TUI stays in the operator's shell (no context switch). A web dashboard is richer but requires browser. A hybrid gives both but doubles maintenance.
   - **Counter-argument**: "If I wanted a web UI, I'd use a web tool. The whole point of `flow` is that it's CLI-first."

2. **Q2: Interactive (mutations) vs read-only?**
   - **Recommended default**: **Interactive** — `flow workspace fix` and `flow workspace archive` should be triggerable from the dashboard.
   - **Tradeoff**: Read-only is simpler (no `--yes` / `--backup` / pollution-protocol to surface); interactive requires surfacing Phase 4 gates (dry-run, confirmation, error messages).
   - **Counter-argument**: "Read-only first; add mutations after I see value." This is the **MVP-first** path.

3. **Q3: Local-only vs remote-capable?**
   - **Recommended default**: **Local-only** (binds to `127.0.0.1`); `--host 0.0.0.0` opt-in for remote.
   - **Tradeoff**: Local-only is safe-by-default (no network exposure); remote-capable needs auth design (token? SSH tunnel?).
   - **Counter-argument**: "I want to view on my phone when I'm away from my desk" → requires remote + auth.

4. **Q4: Real-time vs on-demand?**
   - **Recommended default**: **On-demand with optional auto-refresh** (poll every N seconds; TUI uses `watchdog` event-driven if available).
   - **Tradeoff**: Real-time requires a daemon or persistent process (resource cost); on-demand requires user action.
   - **Counter-argument**: "I want the dashboard to update the second I run `git init` on a project" → real-time via file watch.

5. **Q5: What historical data to show?**
   - **Recommended default**: **Current state only** (read DS1-DS5); defer trends to a future `workspace-events` change.
   - **Tradeoff**: Historical data requires an event log (every `flow workspace {fix,archive,restore}` writes an event); current state is what the codebase has today.
   - **Counter-argument**: "Show me which projects were archived last week" → requires event log.

6. **Q6: Mobile support?**
   - **Recommended default**: **Desktop-only**; assume operator is at a desk with a real terminal or browser.
   - **Tradeoff**: Mobile adds responsive CSS cost + smaller-screen layouts; the dashboard density assumes 1200×800+.
   - **Counter-argument**: "I'm often at a coffee shop with just my phone" → requires mobile.

7. **Q7: Single-page or multi-page?**
   - **Recommended default**: **Single-page** with tabs/sections (Overview, Per-project detail, Archived, Where results).
   - **Tradeoff**: Single-page is simpler (one template); multi-page is more familiar (URL per view).
   - **Counter-argument**: "Multi-page with bookmarkable URLs is more usable" → requires routing.

8. **Q8: Theming/branding?**
   - **Recommended default**: **No theming** — use the framework's default (Textual default theme; Streamlit default; etc.).
   - **Tradeoff**: Theming adds CSS work; default is fine for an internal tool.
   - **Counter-argument**: "I want it to match my other dashboards" → theming.

9. **Q9: Accessibility?**
   - **Recommended default**: **Standard screen reader + keyboard navigation** (HTMX + semantic HTML gives this for free; Textual has built-in keyboard nav; Streamlit has limited a11y).
   - **Tradeoff**: Accessibility adds ARIA roles + keyboard test matrix.
   - **Counter-argument**: "I have a colleague who needs screen reader support" → accessibility work.

10. **Q10: i18n / internationalization?**
    - **Recommended default**: **English-only** (matches all 4 prior phases).
    - **Tradeoff**: i18n adds `gettext` + locale files + string externalization.
    - **Counter-argument**: "Operators may not speak English" → i18n work.

11. **Q11: New dependencies — yes or no?**
    - **Recommended default**: **Depends on approach**:
      - Approach A (Textual): 1 new dep (`textual`)
      - Approach B (FastAPI+HTMX): 2 new deps (`fastapi`, `uvicorn`)
      - Approach C (Streamlit): 2 new deps (`streamlit`, `streamlit-autorefresh`)
      - Approach D (Hybrid): 3 new deps
      - Approach E (No new framework): **0 new deps** (`rich` is already transitive; just promote to direct)
    - **Tradeoff**: All 4 prior cycles shipped "zero new runtime deps" as a deliberate constraint (`flow-where-mvp` D9 + `drift-hardening` design + `observability-pr1` design + `cross-project-federation` + `graph-snapshots` + `prompt-registry-pr1` + `decision-reality-drift` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups`). Adding ANY dep breaks the 10-cycle precedent.
    - **Counter-argument**: "The codebase needs to evolve; the zero-deps constraint was for MVPs." This is a **constitutional** question — does the project continue zero-deps or accept dependencies?

12. **Q12: Should the dashboard be a standalone binary or a subcommand?**
    - **Recommended default**: **Subcommand** (`flow workspace tui` or `flow workspace web`).
    - **Tradeoff**: Standalone binary (`flow-dashboard`) requires separate packaging + console_scripts entry + dist metadata; subcommand is consistent with all prior phases.
    - **Counter-argument**: "I want to run the dashboard without the `flow` prefix" → standalone binary.

## Tech Debt + Dependencies

### New dependencies by approach

| Approach | New deps | Adds to pyproject.toml | Transitive cost |
|----------|----------|------------------------|-----------------|
| **A (Textual)** | `textual>=4.0` | 1 direct dep | Pulls in `rich`, `markdown-it-py`, `linkify-it-py`, `mypy-extensions` (Textual transitive). Total ~5-10 transitive pkgs |
| **B (FastAPI+HTMX)** | `fastapi>=0.115`, `uvicorn[standard]>=0.30` | 2 direct deps | Pulls in `starlette`, `pydantic` (already dep), `httptools`, `uvloop`, `watchfiles`, `websockets`, etc. Total ~15-25 transitive pkgs |
| **C (Streamlit)** | `streamlit>=1.54`, `streamlit-autorefresh>=1.0` | 2 direct deps | Pulls in `altair`, `blinker`, `cachetools`, `gitpython`, `pyarrow`, `requests`, `tenacity`, `toml`, `tornado`, etc. Total ~30-50 transitive pkgs |
| **D (Hybrid)** | `textual` + `fastapi` + `uvicorn` | 3 direct deps | Largest transitive cost |
| **E (Rich only)** | None (promote `rich` from transitive to direct) | 0 new deps (just lift from `uv.lock`) | No new transitive cost |

### Maintenance burden by approach

| Approach | Maintenance | Team skill required |
|----------|-------------|---------------------|
| **A (Textual)** | Medium-high (async + CSS coupling) | Python async, CSS basics |
| **B (FastAPI+HTMX)** | Medium (HTTP server lifecycle, templates) | Python web, Jinja2, HTML/HTMX basics |
| **C (Streamlit)** | Low (Streamlit handles frontend) | Python only |
| **D (Hybrid)** | High (two stacks) | All of the above |
| **E (Rich only)** | Lowest (CLI-only, sync) | Python only |

### Test strategy by approach

| Approach | Test type | Difficulty |
|----------|-----------|------------|
| **A (Textual)** | `textual.testing` snapshot + async Pilot driving | Medium |
| **B (FastAPI+HTMX)** | `fastapi.testclient.TestClient` + httpx + golden HTML | Low-medium |
| **C (Streamlit)** | `streamlit.testing.v1.AppTest` | Low |
| **D (Hybrid)** | Both A and B test suites | High |
| **E (Rich only)** | Golden text output (like `flow metrics summary`) | Lowest |

### Documentation burden by approach

| Approach | Docs needed |
|----------|-------------|
| **A (Textual)** | User guide (key bindings, mouse actions) + screenshots |
| **B (FastAPI+HTMX)** | User guide + URL paths + screenshots |
| **C (Streamlit)** | User guide (Streamlit is self-documenting) |
| **D (Hybrid)** | 2x docs |
| **E (Rich only)** | Minimal (CLI is self-documenting via `--help`) |

### Strict-TDD feasibility

The preflight defaults have **Strict TDD: OFF** for now. If the user enables Strict TDD in the apply phase, here is the LOC multiplier:

| Approach | Impl LOC | Test LOC multiplier | Total LOC |
|----------|----------|---------------------|-----------|
| **A** | 800-1500 | ~2.5× strict-TDD | 2000-3750 |
| **B** | 1000-2000 | ~2.0× (HTTP tests cheaper than TUI) | 2000-4000 |
| **C** | 300-800 | ~1.5× (Streamlit AppTest is fast) | 450-1200 |
| **D** | 1500-3000 | ~2.0× | 3000-6000 |
| **E** | 200-600 | ~1.5× (text-table tests are fast) | 300-900 |

### Precedent for zero-deps constraint

All 4 prior workspace-intelligence cycles + 3 cleanup cycles have shipped with **zero new runtime deps**:

| Cycle | New deps | Source |
|-------|----------|--------|
| `workspace-intelligence` (Phase 1) | 0 | `proposal.md:91-92` |
| `flow-where-cross-project` (Phase 2) | 0 | `explore.md:23` |
| `flow-workspace-status` (Phase 3) | 0 | `proposal.md:dependencies` |
| `workspace-hygiene` (Phase 4) | 0 | `proposal.md:dependencies` |
| `workspace-capability-bootstrap` | 0 | doc-only |
| `flow-where-cross-project-capability-merge` | 0 | doc-only |
| `workspace-spec-cross-impact-cleanup` | 0 | doc-only |

Phase 5 is the **first cycle to consider adding deps**. This is a constitutional decision.

## Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **LOC exceeds 400-line review budget** | **HIGH** | Even the smallest approach (E: Rich) is 200-600 LOC + tests. Approaches A-D are 800-4000 LOC. Forced split into chained PRs or one sub-batch per approach. Ask-always per preflight C1 — surface the LOC estimate at the propose phase for user approval. |
| 2 | **New dependency breaks zero-deps precedent** | **HIGH** | All 4 prior cycles shipped zero-deps. Adding textual/fastapi/streamlit is a constitutional shift. Approach E (Rich only) preserves the precedent. Other approaches require explicit user approval. |
| 3 | **Triggering `flow workspace fix` from dashboard bypasses Phase 4 gates** | **HIGH** | The dashboard must call `flow workspace fix --yes --backup` as a subprocess with explicit gate flags; never bypass `MutationGateError` / `EmptyProjectError`. Pollution-protocol stays in `workspace_hygiene.py` (not duplicated). |
| 4 | **Subprocess return code handling for non-`--json` commands** | **MEDIUM** | Phase 4 mutations are TEXT-ONLY (no `--json` per REQ-HYGIENE-NO-JSON-MVP). Dashboard must parse the text output to surface success/error to the user. Alternative: refactor Phase 4 to add `--json` (BREAKING — needs user approval). |
| 5 | **Test coverage gaps for TUI / web behavior** | **MEDIUM** | TUI tests via Pilot (async) are flaky on CI; web tests via TestClient are deterministic. Approach E (text) is the easiest to test; approach A (Textual) is the hardest. |
| 6 | **Breaking changes to existing CLI commands** | **MEDIUM** | The dashboard READS DS1-DS4 but does not modify their contracts. AC9 byte-identical guards remain green. New subcommand (`flow workspace tui` or `flow workspace web`) is additive. |
| 7 | **Adoption risk — will operators actually use it?** | **MEDIUM** | If the dashboard lives in a browser, operators may not switch from `flow workspace status` text. If it's a TUI, the async + CSS overhead may deter adoption. Validate with user before commit. |
| 8 | **Windows cp1252 encoding issues** | **LOW-MEDIUM** | Phase 2 verify-report S1 documented this. TUI (Approach A) inherits the cp1252 limit (text-based terminal output); web (Approach B/C) sidesteps it (browser handles encoding). Approach E (text) inherits the limit but the operator can pipe to `Out-File -Encoding utf8`. |

## Forecast

### LOC estimates (impl + test, no strict-TDD multiplier)

| Approach | Impl LOC | Test LOC | Total | Vs 400-line budget |
|----------|----------|----------|-------|---------------------|
| **A (Textual)** | 800-1500 | 400-800 | 1200-2300 | 3-6× over |
| **B (FastAPI+HTMX)** | 1000-2000 | 500-1000 | 1500-3000 | 4-8× over |
| **C (Streamlit)** | 300-800 | 150-400 | 450-1200 | 1-3× over |
| **D (Hybrid)** | 1500-3000 | 800-1500 | 2300-4500 | 6-11× over |
| **E (Rich only)** | 200-600 | 100-300 | 300-900 | 0.75-2.25× over |

**Forecast verdict**: **EVERY approach exceeds the 400-line review budget from preflight**. This is expected for a feature change (per preflight C1: "ask-always" if the budget is exceeded). The user must approve either:
- (a) One of the smaller approaches (E: Rich, or C: Streamlit) and accept a single-PR review of 900-1200 LOC.
- (b) Chained PRs per the `chained-pr` skill (split each approach into 3-5 sub-PRs of ~400 LOC each).

### SDD cycle wall-clock estimates

| Phase | A (Textual) | B (FastAPI+HTMX) | C (Streamlit) | D (Hybrid) | E (Rich) |
|-------|-------------|------------------|---------------|-------------|----------|
| explore | 1h | 1h | 1h | 1h | 1h (this artifact) |
| propose | 30m | 30m | 30m | 30m | 20m |
| spec | 1h | 1h | 45m | 1.5h | 30m |
| design | 2h | 2h | 1h | 3h | 45m |
| tasks | 45m | 45m | 30m | 1h | 20m |
| apply | 12-18h | 14-22h | 4-8h | 20-30h | 3-6h |
| verify | 2-3h | 2-3h | 1-2h | 3-5h | 1-2h |
| archive | 30m | 30m | 20m | 45m | 15m |
| **Total** | **20-27h** | **22-31h** | **8-14h** | **30-44h** | **7-13h** |

### Chained PR strategy by approach

Per preflight C1 (ask-always), if LOC exceeds 400 lines:

| Approach | Sub-PRs needed | Sub-PR breakdown |
|----------|----------------|------------------|
| **A (Textual)** | 3-5 | (1) Data layer + read-side, (2) Table widget + sort/filter, (3) Detail view + interactive, (4) Optional: file-watch real-time, (5) Polish + docs |
| **B (FastAPI+HTMX)** | 4-7 | (1) FastAPI scaffold + lifecycle, (2) Read-side routes + templates, (3) Interactive triggers + Phase 4 gates, (4) SSE for real-time, (5) Polish, (6) Docs |
| **C (Streamlit)** | 1-3 | (1) Scaffold + project list, (2) Detail + filter, (3) Interactive triggers |
| **D (Hybrid)** | 6-10 | All of A + B sub-PRs, plus shared state |
| **E (Rich only)** | 1-2 | (1) Rich promotion + `flow workspace dashboard` subcommand, (2) Optional: filters + colored tags |

### Deliverables by approach

| Approach | Subcommands | Files created | Files modified |
|----------|-------------|---------------|----------------|
| **A** | `flow workspace tui` | `src/flow_engineering/dashboard/` (~5 files) + `tests/unit/test_dashboard_tui.py` | `cli.py`, `pyproject.toml` |
| **B** | `flow workspace web` | `src/flow_engineering/dashboard/` (~8 files) + `tests/unit/test_dashboard_web.py` + `templates/` | `cli.py`, `pyproject.toml` |
| **C** | `flow workspace web --streamlit` | `src/flow_engineering/dashboard.py` + `tests/unit/test_dashboard_streamlit.py` | `cli.py`, `pyproject.toml` |
| **D** | `flow workspace {tui,web}` | Both of A and B | `cli.py`, `pyproject.toml` |
| **E** | `flow workspace dashboard` | `src/flow_engineering/dashboard.py` + `tests/unit/test_dashboard.py` | `cli.py`, `pyproject.toml` (promote rich) |

### Migration risk (switching stacks later)

| Approach | Migration cost to switch to another approach |
|----------|-----------------------------------------------|
| **A (Textual)** | High — async + CSS rewrites if switching to web |
| **B (FastAPI+HTMX)** | Medium — Jinja2 templates are reusable; FastAPI is industry-standard |
| **C (Streamlit)** | Low — Streamlit is a thin layer; data layer (`dashboard.py`) is portable |
| **D (Hybrid)** | N/A — already both |
| **E (Rich)** | Lowest — pure Python rendering, easily re-targeted to Streamlit or web |

## Verdict (Recommendations, NOT a winner-pick)

Per the user-locked instruction "Phase 5 define superficie de producto, no es cleanup mecánico" + the explore philosophy of "Surface alternatives + tradeoffs. NO implementation yet. NO premature commitment to one option":

**This artifact recommends 2 of the 5 candidates for the user's consideration** based on (a) alignment with the codebase's zero-deps precedent + (b) alignment with the Phase 1-4 contract preservation + (c) cost-to-value ratio.

### Top Pick (Conservative): **Approach E — Rich only (no new framework)**

**Rationale**:
1. **Preserves zero-deps precedent** — 10 prior cycles shipped without new deps; `rich` is already transitive (promotion is zero-cost).
2. **Lowest LOC** (300-900) — fits the chained-PR budget without forced splits.
3. **Lowest maintenance burden** — sync CLI rendering, consistent with all 4 prior workspace phases.
4. **Lowest team skill required** — Python only; no CSS, no JS, no async, no HTTP.
5. **Phase 1-4 contract preservation** — reads DS1-DS4 via existing CLI handlers; never modifies envelopes.
6. **Validates the "watch list" moment** — `flow-where-mvp` design D9 explicitly deferred Rich to "if dashboard density grows". Phase 5 IS that moment.

**Trade-off accepted**: No mouse interactivity, no real-time updates, no remote/sharing, no rich visuals (colored tables only). These can land in future cycles if the operator finds the dashboard insufficient.

**When NOT to choose E**: If the operator explicitly wants browser-based interactivity (`flow workspace web --port 9999` then click "Archive" in a button) or remote access (share with a colleague). Then E is insufficient; escalate to B or C.

### Runner-up (Aggressive): **Approach C — Streamlit**

**Rationale**:
1. **Fastest prototype** (8-14h total cycle) — operator gets a working dashboard in 2 days.
2. **Python-only** — no JS skill required; consistent with codebase DNA.
3. **Auto-browser** — Streamlit opens the browser automatically.
4. **Reasonable LOC** (450-1200) — fits the chained-PR budget.

**Trade-off accepted**: Streamlit's UX is opinionated; customization is limited. Adds 2 deps. Breaks zero-deps precedent. Streamlit version bumps may shift layouts.

**When to choose C**: If the operator says "I want a dashboard THIS WEEK and I don't care about polish" or "I need to demo this to stakeholders next Friday".

### Conditional Picks (User-Decision Required)

The remaining 3 approaches (A, B, D) are **conditional** on user answers to the open questions:

- **Approach A (Textual)** is the right pick ONLY IF Q1 = TUI + Q2 = Interactive + Q4 = Real-time + Q11 = "yes, 1 new dep is OK". Strong "stay in shell" UX but async paradigm shift.
- **Approach B (FastAPI+HTMX)** is the right pick ONLY IF Q1 = Web + Q2 = Interactive + Q3 = Local-or-remote + Q11 = "yes, 2 new deps are OK". Best balance for rich UX but adds the most deps.
- **Approach D (Hybrid)** is the right pick ONLY IF the operator wants BOTH TUI daily + occasional remote. Highest cost; reserve for v2 or beyond.

### What the user should decide

Before sdd-propose, the user should answer **at minimum**:

1. **Q1** (TUI vs web primary use case)
2. **Q2** (read-only vs interactive)
3. **Q11** (new dependencies — yes or no)

These 3 answers narrow the candidate set:
- TUI + read-only + no new deps → **E (Rich)** is forced
- TUI + interactive + 1 new dep OK → **A (Textual)** is the choice
- Web + interactive + 2 new deps OK → **B (FastAPI+HTMX)** or **C (Streamlit)** (depends on Q6 polish vs Q7 speed)

If the user answers "I don't know" or "you decide", the recommend **E (Rich only)** is the safest default — preserves all 10 prior cycles' precedent and ships in 7-13 hours.

## Discoveries / Gotchas

- **Zero-deps precedent is institutional, not accidental**: 10 prior cycles (4 deltas + 3 cleanup + 3 followups) shipped without new runtime deps. The `flow-where-mvp` design D9 explicitly deferred `rich` to "if dashboard density grows". Phase 5 IS that moment — but the precedent says to promote `rich` (already transitive) rather than adopt a new framework.
- **`rich` is in `uv.lock:1215` as a transitive dependency**: Adding it as a direct dep in `pyproject.toml` has zero transitive cost. Verified — no new packages will be installed.
- **`flow workspace status` is already ASCII-safe**: Phase 3 verified byte-identical JSON envelope; the text output uses ASCII-only tags (`[DIRTY]`, `[NO-GIT]`, etc.). Phase 5 can read both without Windows cp1252 issues.
- **Phase 4 mutations are TEXT-ONLY**: `--json` is INTENTIONALLY ABSENT per REQ-HYGIENE-NO-JSON-MVP. If the dashboard wants to surface mutation success/error to the user, it must either (a) parse text output or (b) trigger the mutation as a subprocess and check the exit code. Both are workable.
- **The workspace status JSON envelope is byte-identical for unchanged FS state**: This means the dashboard can cache the JSON and only re-fetch when something changes (file watch). Approach A (Textual) + watchdog is the natural fit for this pattern.
- **`flow where` argv-list seam is preserved**: Phase 2's `_run_search` uses argv list (not shell), so the dashboard can compose queries without escaping concerns.
- **Textual requires async**: The current `cli.py` is fully sync. Adding Textual requires an `asyncio.run()` bridge in the Click handler — a non-trivial but well-documented pattern.
- **Streamlit autorefresh is polling-only**: True real-time updates require `st.experimental_connection` or `streamlit-webrtc`. The "refresh every 5 seconds" pattern is the practical default.
- **FastAPI + HTMX can serve SSE trivially**: `StreamingResponse(generator())` is one of FastAPI's best patterns. For a dashboard, this means real-time updates without WebSocket complexity.

## Next Steps (for the orchestrator + user)

1. **User picks an approach** by answering the 3 minimum open questions (Q1, Q2, Q11).
2. **User reviews the LOC forecast** (300-4500 depending on approach) and approves chained-PR strategy if > 400 lines.
3. **User commits to the zero-deps precedent** or explicitly approves new deps.
4. **Orchestrator launches `sdd-propose`** for the chosen approach — produces `proposal.md` with the locked CLI shape, scope, dependencies, ACs.
5. **Orchestrator launches `sdd-spec`** — produces `specs/workspace-dashboard/spec.md` with the REQ-WORKSPACE-DASHBOARD-* family and Given/When/Then scenarios.
6. **Orchestrator launches `sdd-design`** — produces `design.md` with file changes, sequence diagrams, architecture decisions.
7. **Orchestrator launches `sdd-tasks`** — produces `tasks.md` with chained-PR sub-batches (if approach exceeds 400 lines).
8. **Orchestrator launches `sdd-apply`** — implementation with RED → GREEN → REFACTOR per task (Strict TDD can be re-evaluated here).
9. **Orchestrator launches `sdd-verify`** — proves implementation matches spec + design + tasks.
10. **Orchestrator launches `sdd-archive`** — merges deltas into `openspec/specs/workspace/spec.md`, removes Phase 5 placeholder from §7, adds to §3 sub-capabilities table.

## Files

This explore artifact (NEW):

- `openspec/changes/phase-5-dashboard/explore.md` (this file)

Files read in full during investigation (READ-ONLY):

- `openspec/specs/workspace/spec.md` (315 LF — workspace family root spec)
- `openspec/specs/flow-where/spec.md` (346 LF — flow-where family root spec)
- `src/flow_engineering/cli.py` (5006 LF — full CLI; `workspace_group` at L2990, `workspace_status` at L2995, 4 mutation verbs at L3156-3343, `_detect_project_markers` at L3458)
- `src/flow_engineering/workspace_hygiene.py` (586 LF — Phase 4 orchestrator)
- `src/flow_engineering/registry.py` (218 LF — Phase 4 registry)
- `openspec/changes/archive/2026-06-30-workspace-hygiene/proposal.md` (281 LF — prior change pattern)
- `openspec/changes/archive/2026-06-30-workspace-hygiene/explore.md` (264 LF — explore format precedent)
- `pyproject.toml` (91 LF — dependency surface)

Engram observations consulted (READ-ONLY):

- `#484` — Pattern: Fix orphan capability roots before more deltas
- `#490` — `sdd/workspace-capability-bootstrap/spec`
- `#492` — `sdd/workspace-capability-bootstrap/design` (the 7 verify checks pattern)
- `#494` — `sdd/workspace-capability-bootstrap/tasks`
- `#506` — `sdd/flow-where-cross-project-capability-merge/spec`
- `#513` — `sdd/flow-where-cross-project-capability-merge/verify-report`
- `#531` — `sdd/workspace-spec-cross-impact-cleanup/archive-report`
- `#533` — Pattern: Same preflight defaults, different reasoning per phase type

External docs consulted (Context7):

- `/textualize/textual` — Textual v4.0.0+ requirements + DataTable widget
- `/textualize/rich` — Rich v15.0.0 capabilities
- `/streamlit/streamlit` — Streamlit 1.54.0+ capabilities