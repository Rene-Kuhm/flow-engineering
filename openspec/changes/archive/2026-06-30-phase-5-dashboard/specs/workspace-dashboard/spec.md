<!-- change spec: phase-5-dashboard (sdd-spec ceremony artifact). Mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Open Questions). All ADDED Requirements point to the canonical root at `openspec/specs/workspace/spec.md` (the actual deliverable). -->
# phase-5-dashboard (change #N)

> **Change**: `phase-5-dashboard`
> **Phase**: spec (3/7 of SDD cycle)
> **Author**: sdd-spec sub-agent
> **Date**: 2026-06-30
> **Project**: flow-engineering (v1.2.0, main HEAD `6133e70`)
> **Artifact store**: `openspec` (writes `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` + Engram mirror)
> **Strict TDD**: ON (feature change — RED → GREEN → REFACTOR discipline required at apply phase)
> **Status**: COMPLETE — ready for design phase
> **Canonical deliverable**: [`openspec/specs/workspace/spec.md`](../../../../specs/workspace/spec.md) (placeholder REQ block replaced with 6 concrete REQs; 377 LF after edit)

---

## Summary

This change resolves `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` in `openspec/specs/workspace/spec.md` by replacing the placeholder stub with 6 concrete root-level REQs that anchor the Phase 5 `workspace-dashboard` sub-capability. The change ships a new CLI subcommand `flow workspace dashboard` that consumes Phase 1 + Phase 3 + the registry (DS1/DS2/DS5) and renders consolidated workspace state using Rich tables/panels/colors in the terminal. Per user-locked Approach E: Rich only, read-only, zero-deps. Per user adjustment: NO `--json` flag on dashboard (one identity per command — visual for humans, machine-readable stays at `flow workspace status --json`).

**Role of this file**: SDD ceremony artifact for traceability. The **canonical** content lives at `openspec/specs/workspace/spec.md`. This file mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Open Questions) so downstream phases (`sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`) can mechanically discover what this change adds.

## ADDED Requirements

> Each root-level REQ is fully specified at the canonical location. This file records the cross-reference so sdd-verify can confirm coverage.

### Requirement: REQ-WORKSPACE-DASHBOARD-SURFACE

A new CLI subcommand `flow workspace dashboard` is registered under `workspace_group` (alongside `status`, `fix`, `archive`, `archived`, `restore`). Default output is visual (Rich tables/panels/colors) for human operators; machine-readable output stays at `flow workspace status --json`. The dashboard command deliberately omits `--json` to preserve a single identity per command (visual for humans vs. structured for tools).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-SURFACE](../../../../specs/workspace/spec.md#req-workspace-dashboard-surface)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-COMMAND-NAME + REQ-DASHBOARD-FLAGS).

### Requirement: REQ-WORKSPACE-DASHBOARD-READ-ONLY

The dashboard consumes workspace state but does not mutate it. All mutations stay in the existing Phase 4 verbs (`flow workspace fix`, `flow workspace archive`, `flow workspace restore`) which retain their pollution-protocol triple, `--yes` dry-run gating, and backup semantics. The dashboard subcommand SHALL NOT expose mutation flags (`--fix`, `--archive`, `--restore`, `--yes`).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-READ-ONLY](../../../../specs/workspace/spec.md#req-workspace-dashboard-read-only)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-READ-ONLY).

### Requirement: REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1

The dashboard invokes `flow projects ls --json` via `subprocess.run(["flow", "projects", "ls", "--json"], capture_output=True, text=True)` to consume the Phase 1 v1 JSON envelope (11 static metadata fields: `name`, `path`, `has_git`, `branch`, `dirty`, `remote`, `stack`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1](../../../../specs/workspace/spec.md#req-workspace-dashboard-consumes-ds1)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-DATA-SOURCES → DS1).

### Requirement: REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2

The dashboard invokes `flow workspace status --json` via `subprocess.run(["flow", "workspace", "status", "--json"], capture_output=True, text=True)` to consume the Phase 3 5-rule needs-attention aggregation (R1 dirty-committed, R2 no-git, R3 no-tests, R4 no-openspec on SDD-adjacent stacks, R5 no-graphify informational).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2](../../../../specs/workspace/spec.md#req-workspace-dashboard-consumes-ds2)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-DATA-SOURCES → DS2).

### Requirement: REQ-WORKSPACE-DASHBOARD-RENDERS-RICH

Default output uses `rich` tables/panels/colors structured as 4 sections: **A** header panel (totals + per-rule breakdown + timestamp), **B** needs-attention table (project × R1–R5 matrix, color-coded red ≥3 needs, yellow 1–2, green 0), **C** archived projects list (name + path + archived_at + reason from DS5), **D** footer with tip pointers. The `--no-color` flag disables Rich ANSI color codes for CI / piping. `rich` is already a transitive dependency via `uv.lock:1215`; promoting it to a direct dep in `pyproject.toml` is zero-cost (no new packages installed).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-RENDERS-RICH](../../../../specs/workspace/spec.md#req-workspace-dashboard-renders-rich)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-RENDERING + REQ-DASHBOARD-FLAGS → `--no-color` + REQ-DASHBOARD-ZERO-DEPS).

### Requirement: REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE

TUI frameworks (Textual, urwid, prompt_toolkit, Blessed), web frameworks (FastAPI, Streamlit, Dash, Panel, Flask, Tauri), real-time updates, file watching, websocket-style streams, interactive forms / prompts / buttons, mobile support, i18n, theming, historical data / audit logs / trend lines, and multi-user support are ALL deferred to Phase 5.2 (or later). The MVP is strictly read-only, on-demand refresh (operator re-invokes the command), single-user.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE](../../../../specs/workspace/spec.md#req-workspace-dashboard-defer-interactive)
**Source delta**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-DEFER-INTERACTIVE).

## Delta-internal requirements (referenced by the 6 root REQs above)

The 6 root REQs above cite this delta spec as the canonical source of canonical wording. The delta-internal requirements below are the granular source-of-truth statements. They are NOT root-level REQs — they are the underlying contract for this delta and feed sdd-design + sdd-tasks + sdd-apply + sdd-verify. Each one corresponds to the citation in the corresponding root REQ's `Source:` line.

### REQ-DASHBOARD-COMMAND-NAME

`flow workspace dashboard` is registered as a Click command under the existing `workspace_group` at `src/flow_engineering/cli.py` (decorator `@workspace_group.command(name="dashboard")` placed alongside `status`, `fix`, `archive`, `archived`, `restore`). Signature: `flow workspace dashboard [--filter RULES] [--sort FIELD] [--no-color]`. Registration is the only modification to `cli.py` (~20 LOC). No new Python public API beyond the new CLI subcommand.

### REQ-DASHBOARD-FLAGS

Three flags supported:

- **`--filter RULES`** (optional, repeatable): Filter needs-attention table by rules R1/R2/R3/R4/R5 (Phase 3 rule set). Comma-separated OR repeatable values per Click convention. Default: all rules surfaced.
- **`--sort FIELD`** (optional, default `name`): Sort by `name` / `path` / `needs-count`.
- **`--no-color`** (optional, off by default): Disable Rich ANSI color codes for CI / piping / non-TTY environments.

**No `--json` flag.** The dashboard is for human operators (visual); machine-readable output stays at `flow workspace status --json` (existing Phase 3 endpoint). Adding `--json` to dashboard would (a) duplicate `flow workspace status --json`, (b) blur the dashboard's identity as a visual tool, (c) increase surface area to maintain (output format, schema versioning, edge cases). Per Pattern #538 (one identity per command).

### REQ-DASHBOARD-READ-ONLY

Dashboard is read-only. It consumes state but does NOT mutate. Mutations stay in `flow workspace fix` / `flow workspace archive` / `flow workspace restore` CLI commands. The pollution-protocol triple (Phase 4), `MutationGateError`, `EmptyProjectError`, and `--yes` dry-run gating stay intact and untouched.

**Forbidden flags**: no `--fix`, `--archive`, `--restore`, `--yes`. The dashboard NEVER triggers mutations — operators wishing to remediate a needs-attention project follow the Section D footer tip and run `flow workspace fix <project> --yes --backup` manually.

### REQ-DASHBOARD-DATA-SOURCES

Dashboard consumes 3 data sources via subprocess + direct read:

- **DS1**: `subprocess.run(["flow", "projects", "ls", "--json"], capture_output=True, text=True)` → v1 JSON envelope (11 metadata fields per Phase 1 REQ-WORKSPACE-PROJECT-IDENTITY).
- **DS2**: `subprocess.run(["flow", "workspace", "status", "--json"], capture_output=True, text=True)` → 5-rule aggregation (Phase 3 REQ-WORKSPACE-STATUS-DISCOVERY; needs_attention items with `name` + `reasons[]` + `path`).
- **DS5**: `load_registry()` from `flow_engineering.registry` → archived projects list (`archived[]` entries with `name` + `path` + `archived_at` + `reason`).

Dashboard MUST NOT consume DS3 (`flow workspace {fix,archive,restore}` — mutations) or DS4 (`flow where` cross-project search) in MVP. Subprocess failure MUST produce a clear stderr message + non-zero exit code; partial JSON MUST NOT be silently accepted.

### REQ-DASHBOARD-RENDERING

Default output uses `rich` structured as 4 sections:

- **Section A — Header panel**: workspace summary (total projects + total archived + total needs-attention + per-rule breakdown R1: X, R2: Y, R3: Z, R4: W, R5: V + run timestamp).
- **Section B — Needs-attention table**: `project name | path (truncated) | R1 | R2 | R3 | R4 | R5 | total-needs`. Color-coded per-row: **red** if `total-needs >= 3`, **yellow** if `1 <= total-needs <= 2`, **green** if `total-needs == 0`. Columns respect terminal width; path truncation at 60 chars by default with ellipsis.
- **Section C — Archived projects list** (if any): `name | path | archived_at | reason` rendered as a Rich table. Empty section → omit.
- **Section D — Footer**: tip pointer lines:
  - `Run 'flow workspace status --json' for machine-readable output`
  - `Run 'flow workspace fix <project> --yes --backup' to remediate`

`--no-color` disables ANSI color codes (sets `rich.console.Console.no_color = True`); layout and structure unchanged.

### REQ-DASHBOARD-ZERO-DEPS

Dashboard uses ONLY `rich` (already transitive via `uv.lock:1215`). NO new runtime dependencies added to `pyproject.toml` `dependencies` list. `rich` MAY be promoted to a direct dep (zero transitive cost) for clarity; verification required before commit (run `uv pip install --dry-run rich` and confirm no new packages).

### REQ-DASHBOARD-DEFER-INTERACTIVE

TUI frameworks, web frameworks, real-time updates, file watching, interactive mutations, multi-user support — ALL deferred to Phase 5.2 (or later). MVP is strictly read-only, on-demand refresh, single-user. If Phase 5.1 MVP proves insufficient for operator workflows, Phase 5.2 evaluation criteria include: operator usage frequency of dashboard, feature requests for interactive mutation triggers, frequency of cross-project filter / sort workflows. Trigger criteria documented for future Phase 5.2 planning.

## MODIFIED Requirements

None. This change is **purely additive at the canonical level** — `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` is replaced by 6 concrete REQs in `openspec/specs/workspace/spec.md` §4. No existing root-level REQ in `openspec/specs/workspace/spec.md` is modified. No existing root-level REQ in any other capability spec (`flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`) is touched. No existing CLI command (DS1 `flow projects ls`, DS2 `flow workspace status`, DS3 `flow workspace {fix,archive,archived,restore}`, DS4 `flow where`) is modified.

## REMOVED Requirements

None. No REQ is deprecated or removed by this change. `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` is **replaced** (not removed) — see Out of Scope below for the §3/§5/§7 cleanup follow-up.

## BDD Scenarios

None for MVP. The proposal (`openspec/changes/phase-5-dashboard/proposal.md` §7 acceptance criteria AC1–AC15) is testable via pytest with subprocess mocks + JSON parsing + Rich rendering snapshot tests. No Given/When/Then BDD feature file is created in this PR because:

1. The MVP is a single CLI subcommand with well-defined subprocess + JSON + Rich contract; pytest covers the test surface cleanly.
2. The 16 BDD scenarios from Phase 4 (`tests/bdd/workspace_hygiene.feature`) + the 7 from Phase 3 (`tests/bdd/`) remain canonical and untouched.
3. The AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` stays green (no code modifications to existing tests).
4. Strict TDD at apply phase requires pytest coverage for: subprocess wrappers (DS1/DS2 success + failure), JSON parsing (envelope shape + version key), Rich rendering (Section A/B/C/D structure), filter logic (R1/R2/R3/R4/R5), sort logic (name/path/needs-count), color logic (red/yellow/green threshold), `--no-color` flag (no ANSI codes in output).

## Out of Scope

Per `openspec/changes/phase-5-dashboard/proposal.md` §9 — encoded as 14 user-locked constraints. Cross-references to source artifacts:

- **No TUI frameworks** — Textual, urwid, Rich Live, prompt_toolkit, Blessed (constraint #13 from proposal §9).
- **No web frameworks** — FastAPI, Streamlit, Dash, Panel, Flask, Tauri (constraint #13).
- **No new runtime dependencies** — `rich` is already transitive; promotion to direct dep is zero-cost; no new packages installed (constraint #11 + zero-deps discipline).
- **No mutations from dashboard** — read-only MVP; mutations stay in `flow workspace fix/archive/restore` (constraint #12).
- **No real-time updates / file watching / websocket** — on-demand only (operator re-invokes the command) (constraint #12).
- **No interactive forms / prompts / buttons** — CLI-only MVP; no prompts beyond standard Click help output (constraint #12).
- **No mobile support / i18n / theming** — desktop / terminal / ASCII-default; English text only (constraint #12).
- **No historical data / audit log / trends** — current state only; no SQLite / DuckDB / telemetry persistence (constraint #12).
- **No multi-user support** — single-user; no auth; no per-user registry split (constraint #12).
- **No modifications to Phase 4 mutation gates** — pollution-protocol triple, `MutationGateError`, `EmptyProjectError` stay intact (constraint #12).
- **No modifications to Phase 1/2/3/4 CLI commands** — DS1-DS4 stay as they are; dashboard is additive consumer only (constraint #16).
- **No touching** `openspec/changes/v1.1-followups/` — sacred territory (constraint #14).
- **No `stash`-triggering words** — §7 L301 of `workspace/spec.md` "stash/worktree handling" stays byte-identical (Batch E #18).
- **No `size:exception` debate in this spec phase** — single-PR-size-exception discussion happens at design phase (per Phase 1/3 precedent); LOC forecast 300–900.

**Section cleanup follow-up (deferred)**: §3 (Sub-capabilities table row 5 "placeholder"), §5 (Public CLI surface row "tui (future)"), §7 (Future Changes row #2 "workspace-dashboard") in `openspec/specs/workspace/spec.md` will become stale-but-protected by the §8 Family-shape protocol when the change ships. A future `workspace-dashboard-section-cleanup` change (or extension of this PR at apply phase) is required to update those sections. **OUT OF SCOPE for this PR** to preserve byte-identical preservation checks per the user's locked constraint.

## Open Questions (resolved)

The open questions from the proposal (`openspec/changes/phase-5-dashboard/proposal.md` §10) are resolved before this spec was written. Restated here for traceability:

| # | Question | Answer |
|---|----------|--------|
| Q1 | TUI vs web dashboard? | **Deferred to Phase 5.2.** MVP is Rich-only enhanced CLI (Approach E). |
| Q2 | Read-only vs interactive mutations? | **Read-only MVP.** No mutations from UI; operators reach for `flow workspace fix/archive/restore` manually. |
| Q3 | Real-time vs on-demand updates? | **On-demand only.** Operator re-invokes the command to refresh state. |
| Q11 | New runtime dependencies? | **Zero new deps.** `rich` is already transitive via `uv.lock:1215`. Promotion to direct dep is zero-cost. |
| **Q-NEW** | Why no `--json` on dashboard? | **One identity per command** (Pattern #538). `flow workspace dashboard` is for human operators (visual); machine-readable output stays at `flow workspace status --json` (existing Phase 3 endpoint). Adding `--json` to dashboard would (a) duplicate `flow workspace status --json`, (b) blur the dashboard's identity as a visual tool, (c) increase surface area to maintain. User removed `--json` from the dashboard MVP flags; signature is now `flow workspace dashboard [--filter RULES] [--sort FIELD] [--no-color]`. |
| All others | — | Deferred to Phase 5.2 or N/A for MVP scope. |

## Cross-References

- **Canonical deliverable**: [`openspec/specs/workspace/spec.md`](../../../../specs/workspace/spec.md) (placeholder REQ block replaced with 6 concrete REQs; 377 LF after edit).
- **Proposal** (authoritative source): `openspec/changes/phase-5-dashboard/proposal.md` (Approach E locked, `--json` REMOVED per user adjustment, 15 acceptance criteria AC1–AC15, 14 user-locked constraints).
- **Explore**: `openspec/changes/phase-5-dashboard/explore.md` (5 approach candidates surfaced; Approach E picked as lowest-cost; Pattern #536 "observability first" cited).
- **Phase 1 delta spec** (source of REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1): `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`.
- **Phase 3 delta spec** (source of REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2): `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md`.
- **Phase 4 delta spec** (source of REQ-WORKSPACE-DASHBOARD-READ-ONLY context — pollution-protocol triple): `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md`.
- **Registry module** (source of REQ-WORKSPACE-DASHBOARD-CONSUMES-DS5 — DS5 archived list): `src/flow_engineering/registry.py:144` (`load_registry()`).
- **CLI registration target**: `src/flow_engineering/cli.py:2990` (`@main.group(name="workspace") def workspace_group()`).
- **Sibling patterns cited**: Engram #535 (explore artifact), Engram #536 (observability-first pattern), Engram #537 (proposal mirror), Engram #538 (one-identity-per-command pattern).
- **Engram mirror** (this spec): topic_key `sdd/phase-5-dashboard/spec`; type `architecture`; `capture_prompt: false`; project `insyd`.