<!-- spec.md: workspace capability catalog (root). Source: sdd-spec for `workspace-capability-bootstrap` (change #N, 2026-06-30). Family-index bootstrap — anchors 3 prior deltas (Phase 1/3/4) + Phase 5 dashboard placeholder. Mirrors `flow-where/spec.md` style (family index, not canonical source for delta REQs). -->
# Workspace Capability Spec

> **Family index, not canonical source.** Canonical requirements live in delta specs under `openspec/changes/<change-name>/specs/<sub-capability>/spec.md` and `openspec/changes/archive/<date>-<change>/specs/<sub-capability>/spec.md`. This file anchors the workspace capability family and provides cross-references for navigation. Each root-level REQ cites its delta source via the `Source:` field. Do not treat this file as the source of truth for delta REQ wording — that is what the delta specs are for.

## Archive status (2026-06-30)

**`workspace-capability-bootstrap` (#N) SHIPPED as the workspace-family anchor — single file, single PR, 1 work-unit commit on `main`.**

**Role**: This is the **first** root capability spec for `workspace`. Before this change, four workspace-intelligence arc deltas (Phase 1 `projects-ls-extension`, Phase 2 `flow-where-cross-project`, Phase 3 `workspace-status`, Phase 4 `workspace-hygiene`) landed as orphans with no root to anchor them. Phase 2 has since been reclassified to `flow-where` (see Cross-Impact §6); the workspace family is **3 confirmed sub-capabilities + 1 placeholder (Phase 5 dashboard)**.

**Verdict at archive**: **PASS — doc-only, zero code touched**. Per `openspec/changes/workspace-capability-bootstrap/verify-report.md` (forthcoming): all 11 acceptance criteria (AC1–AC11) met; AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` still green; full suite 1513/1513 still passing on `main` HEAD `d077d75` + post-archive commit.

**Findings tally**: **0 CRITICAL + 0 WARNING + 0 SUGGESTION** (doc-only change; no behavior moved; pre-existing 3 lint errors at `cli.py:682 RET504` + `test_cli_where_cross_project.py:{33,295}` remain OOS per Phase 4 close-out precedent).

**Carry-forwards documented in Future Changes** (§7): Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.

## 1. Purpose

Cross-version capability spec for the **workspace** subsystem — the
inventory/status/hygiene surface for the projects under the configured
projects root. The capability:

- enumerates projects with **11 static metadata fields** (`flow projects ls [--json]`);
- aggregates per-project signals into a **5-rule needs-attention report** (`flow workspace status [--json]`) — R1 dirty-committed, R2 no-git, R3 no-tests, R4 no-openspec on SDD-adjacent stacks, R5 no-graphify (informational only in v1);
- remediates R2 (no-git → `git init`) and provides a registry-mediated archive/restore escape hatch for projects the user no longer maintains (`flow workspace {fix,archive,archived,restore}`);
- persists a **registry v1** at `~/.flow-engineering/registry.json` for the `projects[]` + `archived[]` split (atomic writes; read-only consumers do not create it);
- visualizes workspace state in a read-only Rich dashboard for human operators (flow workspace dashboard with --filter RULES, --sort FIELD, --no-color; no --json per Pattern #538).

**What `workspace` is NOT**: a content search/retrieval surface. Cross-project code/archive search belongs to `flow-where` (Phase 2 reclassification — see §6). The two capabilities have different verbs (CRUD vs. search), different mental models (project identity & state vs. file content traversal), and different change cadences (workspace mutations vs. append-heavy search indexes).

## 2. Capability boundary

```
                ┌──────────────────────────────────────────────────┐
                │            workspace  (this spec)                │
                │  "inventario / estado / higiene del workspace"   │
                │                                                  │
                │  • project identity (name, path, has_git, …)     │
                │  • project state  (R1–R5 needs_attention)        │
                │  • project hygiene (fix / archive / restore)     │
                │  • registry v1 (atomic writes)                   │
                └──────────────────────────────────────────────────┘
                                       │
                                       │  NO OVERLAP
                                       ▼
                ┌──────────────────────────────────────────────────┐
                │                  flow-where                       │
                │  "búsqueda / retrieval de contenido"             │
                │                                                  │
                │  • repo grep (rg-or-grep over src/, tests/)      │
                │  • SDD archive grep                              │
                │  • graphify Jaccard (fail-open)                  │
                │  • Phase 2: cross-project search --root PATH     │
                └──────────────────────────────────────────────────┘
```

**Boundary rule (user-locked)**: *"no mezclar 'inventario/estado/higiene del workspace' con 'búsqueda/retrieval de contenido'."* Anything that operates on project identity, project state, or project lifecycle belongs here. Anything that operates on file contents within projects belongs to `flow-where`.

**Boundary stress tests**:

| Scenario | workspace? | Why |
|----------|------------|-----|
| "What projects do I have?" | ✅ YES | Project discovery (Phase 1) |
| "Which projects need attention?" | ✅ YES | Project status aggregation (Phase 3) |
| "Init git on the no-git project `mockup`." | ✅ YES | Project hygiene (Phase 4) |
| "Find where I implemented X across projects." | ❌ `flow-where` | Cross-project content search (Phase 2) |
| "Archive `mockup` — I no longer maintain it." | ✅ YES | Project hygiene (Phase 4) |
| "Show me a TUI of my workspace." | ✅ YES (Phase 5) | Project dashboard |

## 3. Sub-capabilities

The workspace family has **4 confirmed sub-capabilities**:

| Phase | Sub-capability | CLI surface | Role | Status | Delta spec |
|-------|---------------|-------------|------|--------|------------|
| 1 | `projects-ls-extension` | `flow projects ls [--json]` | Read discovery — project metadata enumeration | ✅ Shipped (local-only branch `codex/workspace-intelligence`) | `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` |
| 3 | `workspace-status` | `flow workspace status [--json]` | Read aggregation — 5 needs-attention rules R1–R5 | ✅ Shipped (local-only branch `codex/flow-workspace-status`) | `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` |
| 4 | `workspace-hygiene` | `flow workspace {fix,archive,archived,restore}` | Write/mutation — registry-mediated lifecycle (R2 + archive) | ✅ Shipped + archived at `d077d75` | `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` |
| 5 | `workspace-dashboard` | `flow workspace dashboard` | Visualization — read-only Rich MVP for human operators; supports `--filter RULES`, `--sort FIELD`, `--no-color` (no `--json` — Pattern #538) | ✅ Shipped + archived at `phase-5-dashboard` | `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` |

**Phase 2 is OUT of this family** — see §6 Cross-Impact.

**Artifact-hygiene note**: Phases 1 and 3 live in `openspec/changes/{workspace-intelligence,flow-workspace-status}/` (not yet moved to `archive/`); Phase 4 is already archived at `openspec/changes/archive/2026-06-30-workspace-hygiene/`. Per user-locked constraint, **no archive-move work is in scope for this change**.

## 4. Requirements

The 7 root-level REQs below are **synthesized family-level summaries**. Canonical wording, Given/When/Then scenarios, and acceptance criteria live in the delta specs cited under each REQ's `Source:` line. When a delta REQ evolves, the corresponding root REQ summary should be reviewed for drift.

---

### REQ-WORKSPACE-PROJECT-IDENTITY

A project is identified by 11 static metadata fields emitted by `flow projects ls`/`flow projects ls --json`: `name`, `path`, `has_git`, `branch`, `dirty`, `remote`, `stack`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`. The v1 JSON envelope uses `version: "1"` as its first key. The `projects` array is sorted alphabetically by `name`. Missing data is represented by JSON `null` (not `""` or omitted). The `has_engram` field is a documented stub (always `false` until a later phase un-stubs it).

**Source:** `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` → REQ-`--json`-FLAG + REQ-FIELD-EXTENSION + REQ-HAS-ENGRAM-STUB + REQ-SCHEMA-VERSIONING + REQ-DETERMINISTIC-ORDER.

**Out of scope:** The specific git-detection subprocess mechanics; the stack-detection heuristics; the Phase 1 un-stubbing of `has_engram` (deferred).

---

### REQ-WORKSPACE-STATUS-DISCOVERY

The `flow workspace status` subcommand surfaces 5 needs-attention rules:

- **R1**: `has_git == true AND dirty == true` → "R1: uncommitted work" (deferred for remediation — see REQ-WORKSPACE-R1-DEFERRED; surface-only in status).
- **R2**: `has_git == false` → "R2: no version control".
- **R3**: `test_commands == []` → "R3: no tests detected".
- **R4**: `has_openspec == false AND stack in {Python, Go, Rust}` → "R4: SDD-adjacent stack missing openspec".
- **R5**: `has_graphify == false` → informational only in v1 (does NOT add to `needs_attention`).

The status envelope (`--json`) is byte-identical for unchanged filesystem states (no timestamp fields; `version: "1"` first key; `totals` with 8 integer fields; `projects` verbatim from Phase 1's detector; `needs_attention` items with `name` + `reasons[]` + `path`).

**Source:** `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` → REQ-R1-DIRTY-COMMITTED + REQ-R2-NO-GIT + REQ-R3-NO-TESTS + REQ-R4-NO-OPENSPEC-SDD-STACK + REQ-R5-NO-GRAPHIFY-INFORMATIONAL + REQ-WS-JSON-ENVELOPE + REQ-WS-TEXT-DEFAULT + REQ-WS-EMPTY-ROOT.

**Out of scope:** R1 remediation (deferred); R3/R4 bootstrap actions; Phase 5 dashboard integration; the `has_graphify` stub un-blocking.

---

### REQ-WORKSPACE-MUTATION-SAFETY

Every workspace mutation executes the **pollution-protocol triple**: `_snapshot_project` (when `--backup` is set) → `_apply_rule` → `_verify_post_mutation`. If verification fails, the system restores from the snapshot and exits with code 2. `flow workspace fix` refuses to mutate a non-empty project unless `--backup` is passed (non-empty = no `.git/` AND has visible user files; hidden system files `.DS_Store`, `Thumbs.db`, `desktop.ini` are excluded). Backups are stored at `~/.flow-engineering/backups/<project>/<UTC-ISO-timestamp>/` with a `manifest.json`; retention is **INDEFINITE** in MVP (manual cleanup is the operator's responsibility).

**Source:** `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-POLLUTION-PROTOCOL + REQ-HYGIENE-BACKUP-LAYOUT + REQ-HYGIENE-BACKUP-GATE-NONEMPTY.

**Out of scope:** Backup pruning / TTL (deferred to `backup-retention-policy` follow-up — see §7); R1 remediation in the fix command.

---

### REQ-WORKSPACE-DRY-RUN-DEFAULT

`flow workspace fix` and `flow workspace archive` default to **dry-run** mode (plan only, exit 0, no filesystem or registry mutation). Passing `--yes` switches to execute mode. Both commands refuse to mutate without `--yes` (exit non-zero, stderr mentions `--yes`).

**Source:** `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-DRY-RUN-DEFAULT.

**Out of scope:** `--yes` gating on `flow workspace restore` and `flow workspace archived` (those are not mutation-level — restore only flips registry lists, archived is read-only).

---

### REQ-WORKSPACE-R1-DEFERRED

R1 dirty-git remediation is **OUT OF SCOPE** for the workspace-hygiene MVP. `flow workspace fix` SHALL NOT execute any R1 remediation — no working-tree manipulation, no untracked-file handling, no index changes. R3 no-tests and R4 no-openspec bootstrap are also deferred. These are future changes; status surfaces them; remediation does not act on them.

**Source:** `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-R1-EXPLICITLY-OUT.

**Out of scope:** R1 implementation; R3/R4 bootstrap implementation.

---

### REQ-WORKSPACE-REGISTRY-V1

The system persists a registry at `~/.flow-engineering/registry.json` with schema:

```json
{
  "version": 1,
  "projects":  [ { "name": "...", "path": "...", "added_at": "..." } ],
  "archived":  [ { "name": "...", "path": "...", "archived_at": "...", "reason": "..." } ]
}
```

Missing file → empty default (`{version: 1, projects: [], archived: []}`). Malformed JSON → exit non-zero with a clear error. Writes are atomic via `tempfile.NamedTemporaryFile` + `os.replace` (precedent: `project_aliases.save_aliases` at `src/flow_engineering/project_aliases.py:164`). Read-only consumers (`flow projects ls --json`, `flow workspace status`) MUST NOT create or modify the registry.

**Source:** `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-REGISTRY-V1.

**Out of scope:** Registry schema v2 (future change); registry migration tooling from v0; cross-platform `%APPDATA%` resolution (uses `Path.home()`).

---

### REQ-WORKSPACE-DASHBOARD-SURFACE

A new CLI subcommand `flow workspace dashboard` is registered under `workspace_group` (alongside `status`, `fix`, `archive`, `archived`, `restore`). Default output is visual (Rich tables/panels/colors) for human operators; machine-readable output stays at `flow workspace status --json` — the dashboard command deliberately omits `--json` to preserve a single identity per command (visual for humans vs. structured for tools).

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-COMMAND-NAME + REQ-DASHBOARD-FLAGS.

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** CLI handler signature details (see delta REQ-DASHBOARD-COMMAND-NAME); individual flag semantics (see delta REQ-DASHBOARD-FLAGS); the choice of `rich` as the rendering engine (already transitive per `pyproject.toml`).

---

### REQ-WORKSPACE-DASHBOARD-READ-ONLY

The dashboard consumes workspace state but does not mutate it. All mutations stay in the existing Phase 4 verbs (`flow workspace fix`, `flow workspace archive`, `flow workspace restore`) which retain their pollution-protocol triple, `--yes` dry-run gating, and backup semantics. The dashboard subcommand SHALL NOT expose mutation flags (`--fix`, `--archive`, `--restore`, `--yes`).

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-READ-ONLY.

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** Mutation CLI handlers (Phase 4 — `flow workspace fix/archive/restore`); pollution-protocol triple (Phase 4 stays intact); `MutationGateError` and `EmptyProjectError` (Phase 4 gates unchanged); interactive triggers from UI (deferred to Phase 5.2).

---

### REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1

The dashboard invokes `flow projects ls --json` via `subprocess.run(["flow", "projects", "ls", "--json"], capture_output=True, text=True)` to consume the Phase 1 v1 JSON envelope (11 static metadata fields: `name`, `path`, `has_git`, `branch`, `dirty`, `remote`, `stack`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`).

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-DATA-SOURCES (DS1).

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** `flow projects ls` text output (dashboard parses JSON only); the 11 project metadata fields (defined at REQ-WORKSPACE-PROJECT-IDENTITY); `flow where` cross-project search (DS4, deferred to Phase 5.2).

---

### REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2

The dashboard invokes `flow workspace status --json` via `subprocess.run(["flow", "workspace", "status", "--json"], capture_output=True, text=True)` to consume the Phase 3 5-rule needs-attention aggregation (R1 dirty-committed, R2 no-git, R3 no-tests, R4 no-openspec on SDD-adjacent stacks, R5 no-graphify informational).

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-DATA-SOURCES (DS2).

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** The 5-rule logic itself (defined at REQ-WORKSPACE-STATUS-DISCOVERY); R1 remediation behavior (deferred — REQ-WORKSPACE-R1-DEFERRED); R3/R4 bootstrap (deferred).

---

### REQ-WORKSPACE-DASHBOARD-RENDERS-RICH

Default output uses `rich` tables/panels/colors structured as 4 sections: **A** header panel (totals + per-rule breakdown + timestamp), **B** needs-attention table (project × R1–R5 matrix, color-coded red ≥3 needs, yellow 1–2, green 0), **C** archived projects list (name + path + archived_at + reason from DS5), **D** footer with tip pointers. The `--no-color` flag disables Rich ANSI color codes for CI / piping. `rich` is already a transitive dependency via `uv.lock:1215`; promoting it to a direct dep in `pyproject.toml` is zero-cost (no new packages installed).

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-RENDERING + REQ-DASHBOARD-FLAGS (`--no-color`) + REQ-DASHBOARD-ZERO-DEPS.

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** Rich color-accessibility hardening (text labels stay alongside colors per the Phase 5 proposal §11 risk register); Rich output width on narrow terminals (column truncation handles this at render time); snapshot-testing strategy for Rich output (golden-text approach — handled in delta REQ-DASHBOARD-RENDERING).

---

### REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE

TUI frameworks (Textual, urwid, prompt_toolkit, Blessed), web frameworks (FastAPI, Streamlit, Dash, Panel, Flask, Tauri), real-time updates, file watching, websocket-style streams, interactive forms / prompts / buttons, mobile support, i18n, theming, historical data / audit logs / trend lines, and multi-user support are ALL deferred to Phase 5.2 (or later). The MVP is strictly read-only, on-demand refresh (operator re-invokes the command), single-user.

**Source:** `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` → REQ-DASHBOARD-DEFER-INTERACTIVE.

**Wording:** The canonical wording lives at the source delta spec. This root-level summary exists for navigation only.

**Out of scope:** TUI framework selection; web framework selection; interactive mutation paths from UI; real-time update mechanism; multi-user authentication / authorization; i18n / theming infrastructure; historical telemetry.

## 4.1 Sub-capability relationship graph

```
                          ┌──────────────────────────────────────────┐
                          │  openspec/specs/workspace/spec.md (NEW)   │
                          │  root capability — anchors family          │
                          └────────────┬───────────────┬───────────────┘
                                         │               │
                          references     │               │    references
                                         ▼               ▼
               ┌─────────────────────────────────┐  ┌─────────────────────────────┐
               │  projects-ls-extension (P1)    │  │  workspace-status (P3)       │
               │  flow projects ls [--json]     │  │  flow workspace status [--json]│
               │  Phase 1: 5 REQs                │  │  Phase 3: 8 REQs incl.       │
               │  Source: workspace-intelligence │  │  R1–R5 rules                 │
               └──────────────┬──────────────────┘  └──────────────┬──────────────┘
                              │                                     │
                              │ _detect_project_markers (shared     │
                              │  helper, read-only on P1 surface)   │
                              └─────────────────┬───────────────────┘
                                                ▼
                              ┌──────────────────────────────────────┐
                              │  workspace-hygiene (P4)               │
                              │  flow workspace {fix,archive,          │
                              │    archived,restore}                   │
                              │  Phase 4: 12 REQs incl. pollution-     │
                              │  protocol + registry v1 + dry-run     │
                              └──────────────────┬───────────────────┘
                                                 ▲
                                                 │ Phase 5 (future)
                                                 │
                              ┌──────────────────────────────────────┐
                              │  workspace-dashboard (P5)             │
                              │  flow workspace dashboard             │
                              │  Phase 5: 6 REQs incl. Rich MVP +     │
                              │  --filter RULES / --sort FIELD /      │
                              │  --no-color (no --json per #538)      │
                              │  Source: phase-5-dashboard (shipped)  │
                              └──────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │  flow-where (EXISTING capability, OUTSIDE workspace family)        │
   │  Phase 2 (flow-where-cross-project) reclassified HERE              │
   │  See §6.1 Cross-Impact for rationale + §7 for the                  │
   │  flow-where-cross-project-capability-merge follow-up.              │
   └──────────────────────────────────────────────────────────────────┘
```

**No cycles in the family.** The dependency chain is strictly additive:

- Phase 3 depends on Phase 1 helper (`_detect_project_markers`, read-only).
- Phase 4 depends on Phase 3 registry gating + Phase 1 helper (read-only).
- Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).

## 4.2 Versioning

The workspace family does not currently expose a single `workspace: v1.x` envelope — each sub-capability owns its own versioned envelope (`flow projects ls --json` carries `version: "1"`; `flow workspace status --json` carries `version: "1"`; the registry carries `version: 1`). A future family-level version bump would be triggered by a breaking change to a workspace-primitive (registry schema v2, mutation-protocol change, etc.).

| Family event | Trigger | Impact on root spec |
|--------------|---------|---------------------|
| Phase 5 dashboard ships | New sub-capability added | Add sub-capability row to §3, remove from §7 Future Changes, add a new `REQ-WORKSPACE-DASHBOARD-*` block to §4 |
| Registry schema v2 | Breaking change to `~/.flow-engineering/registry.json` | Bump `REQ-WORKSPACE-REGISTRY-V1` → `REQ-WORKSPACE-REGISTRY-V2`; add migration REQ |
| New mutation verb (e.g., `flow workspace lock`) | New write-side verb | Add to §3 sub-capabilities + §5 CLI surface; new mutation inherits `REQ-WORKSPACE-MUTATION-SAFETY` + `REQ-WORKSPACE-DRY-RUN-DEFAULT` |
| R1 remediation ships | `workspace-hygiene-r1` change | Remove `REQ-WORKSPACE-R1-DEFERRED` (the R1 row is then a real REQ with a delta source) |
| Phase 2 follow-up lands | `flow-where-cross-project-capability-merge` | No change to workspace root spec; `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` |

## 5. Public CLI surface

The `workspace` capability exposes these user-facing commands (no new Python public API beyond the existing `flow` Click subcommands):

| Command | Subcommand | Phase | Purpose |
|---------|-----------|-------|---------|
| `flow projects ls` | (Phase 1) | 1 | Enumerate projects; `--json` for the v1 envelope |
| `flow workspace status` | `--json` (Phase 3) | 3 | Read needs-attention report |
| `flow workspace fix` | `<project> [--yes] [--backup]` (Phase 4) | 4 | R2 remediation (no-git → `git init`) |
| `flow workspace archive` | `<project> [--reason TEXT] --yes` (Phase 4) | 4 | Move project to `registry.archived[]` |
| `flow workspace archived` | (Phase 4) | 4 | TEXT-only listing of archived projects |
| `flow workspace restore` | `<project> --yes` (Phase 4) | 4 | Move project back to `registry.projects[]` |
| `flow workspace dashboard` | `[--filter RULES] [--sort FIELD] [--no-color]` (Phase 5) | 5 | Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no `--json` (Pattern #538) |

**Exit codes (workspace mutations)**:

- `0` — success (including dry-run plan-only output)
- `1` — refused: missing `--yes`, missing `--backup` on non-empty fix, target not in workspace root, etc.
- `2` — verify failure during pollution-protocol execution (project state restored from snapshot)

**No new Python deps** — all capabilities ship with the existing `click` + `pydantic>=2.5.0` stack from `pyproject.toml`.

## 6. Cross-Impact

| Capability | Direction | Notes |
|------------|-----------|-------|
| `flow-where` (v0.8.2+, REQ-V1.0.1..V1.0.4) | **Sibling — Phase 2 reclassification lives here** | Phase 2 (`flow-where-cross-project`) was historically filed under the "workspace-intelligence" arc but **belongs to `flow-where`, NOT `workspace`**. See §6.1 below. |
| `decision-drift` (v0.8.0+, v0.9.0) | Unrelated | `flow workspace status` does NOT surface drift events; workspace mutations do NOT touch `drift_event_log.jsonl` |
| `observability` (v0.7.0+) | Unrelated | Workspace mutations do NOT emit metrics counters; the 4 pre-existing observability window-filter test failures are unrelated to workspace |
| `prompt-registry` (v0.8.0+) | Unrelated | Workspace commands do NOT consume or render `PROMPT_NAMES` entries |

### 6.1 Phase 2 reclassification (the most important cross-impact)

Phase 2 (`flow-where-cross-project`) **belongs to `flow-where`, not `workspace`**. This is a documentation statement only — no files are moved in this PR.

**Rationale (user-locked quote)**: *"no mezclar 'inventario/estado/higiene del workspace' con 'búsqueda/retrieval de contenido'."*

**Evidence** (from Engram #456 + proposal #455 + the surviving `status.md`):

1. Phase 2's own proposal #455 states it is *"ADDITIVE to where_cmd — do NOT replace existing where.py module API"*. It is an extension of `flow where`, not a workspace primitive.
2. Phase 2 reuses `_run_search` from `where.py` (read-only on the existing `flow-where` module).
3. Phase 2's 6 search directories — `src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/` — are **code+archive content** targets, not project-metadata targets.
4. **Semantic test**: Phase 2's REQs would make sense if the `workspace` capability never existed. "Find code across projects" is a `flow-where` concern.
5. Phase 2's delta spec is **MISSING locally** (only `status.md` survives at `openspec/changes/flow-where-cross-project/`). Full REQ content preserved in **Engram #456** (6 REQs: REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN; 7 BDD scenarios).

**Action in this PR**: Document only. No files moved. No modifications to any archived Phase 2 artifact. The reclassification is recorded here so future readers understand why Phase 2 is absent from the workspace family.

**Follow-up** (`flow-where-cross-project-capability-merge`): See §7 Future Changes.

**[2026-06-30 update — RESOLVED]**: The `flow-where-cross-project-capability-merge` follow-up has landed via the change of the same name. The Phase 2 delta spec was regenerated **byte-identical** from git commit `27111ed` (2026-06-29) to `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` (155 lines; 6 ADDED REQs; 13 Given/When/Then scenarios; 10 acceptance criteria). The 6 REQs were integrated additively into `openspec/specs/flow-where/spec.md` as `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN`, each with a `Source:` line pointing to the regenerated delta. Merge SHA is `[future-commit-sha]` (placeholder until the apply phase produces the concrete commit). This §6.1 reclassification is now **RESOLVED**; the 5 evidence points above are preserved verbatim and continue to describe *why* Phase 2 belongs to `flow-where`, while this paragraph records *when* the reclassification finally executed. See also §7 row #1 (this follow-up is now removed from Future Changes).

## 7. Future Changes

| # | Change | Scope | Priority | Trigger |
|---|--------|-------|----------|---------|
| 2 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability for the write-side if the delta grows further. | Low | Phase 4 follow-up #2 in archive-report #477 |
| 3 | `backup-retention-policy` | Currently INDEFINITE in Phase 4 (per locked constraint #12). Needs pruning/TTL strategy at scale. | Low | Operator concern; not blocking |
| 4 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation: stash/worktree handling, interactive prompts, status integration. Explicitly OUT of Phase 4. | Low | Future change if requested |
| 5 | `workspace-hygiene-r3` + `workspace-hygiene-r4` (deferred) | R3 no-tests bootstrap (template-dependent) + R4 no-openspec bootstrap (semantic scaffold). | Low | Future change if requested |
| 6 | Artifact-hygiene move | Phases 1 + 3 still in `openspec/changes/{workspace-intelligence,flow-workspace-status}/` (not yet in `archive/`). | Low | Out of scope for this change; separate cleanup |

## 8. Drift Detection

> **How drift is mitigated between this root and the delta specs.**

- **Source-of-truth rule**: Each `REQ-WORKSPACE-*` block in §4 carries a `Source:` line citing the exact delta spec path + REQ ID. Canonical wording lives at the source; root-level summaries exist for navigation only.
- **Acceptance check**: `sdd-verify` validates that every `REQ-WORKSPACE-*` block in this file has a `Source:` line, and that the cited delta spec path exists. (Acceptance criterion AC2 in `openspec/changes/workspace-capability-bootstrap/proposal.md`.)
- **Delta-evolution protocol**: When a delta REQ is updated (or a new delta is added), the corresponding root REQ summary should be reviewed for drift. If the delta is added to the family, add a corresponding `REQ-WORKSPACE-*` summary here with a new `Source:` line.
- **Family-shape protocol**: When a new sub-capability is added (e.g., Phase 5 dashboard), update §3 (Sub-capabilities), §5 (Public CLI surface), and §7 (Future Changes → remove the placeholder entry from Future Changes and add it to §3).
- **Open improvement (out of scope for this change)**: automated drift detection via `sdd-verify` — could parse `Source:` lines and confirm path validity + the cited REQ still exists in the delta spec. Deferred until a CI hook for OpenSpec specs exists.

> **Reviewer hint**: When reviewing a workspace-related PR, start at this root spec for the family shape, then follow each `Source:` line to the canonical delta REQ for full Given/When/Then scenarios and acceptance criteria. Do not edit root-level wording without checking the delta first.
