<!-- change spec: workspace-dashboard-usability-pass (sdd-spec ceremony artifact). Mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Open Questions). All MODIFIED requirements point to the canonical root at `openspec/specs/workspace/spec.md` (family-index source-of-truth); the ADDED requirement points to a new root-level REQ summary that sdd-archive will add to that file. -->
# workspace-dashboard-usability-pass — Spec Delta (change #N)

> **Change**: `workspace-dashboard-usability-pass`
> **Phase**: spec (3/7 of SDD cycle)
> **Author**: sdd-spec sub-agent
> **Date**: 2026-07-01
> **Project**: flow-engineering (v1.2.0)
> **Artifact store**: `openspec` (writes `openspec/changes/workspace-dashboard-usability-pass/specs/workspace-dashboard/spec.md` + Engram mirror)
> **Strict TDD**: ON (feature change — RED → GREEN → REFACTOR discipline required at apply phase; ×6 multiplier per drift-hardening precedent)
> **Builds on**: [`openspec/changes/workspace-dashboard-usability-pass/explore.md`](../explore.md) ← [`proposal.md`](../proposal.md)
> **Canonical deliverable**: [`openspec/specs/workspace/spec.md`](../../../../specs/workspace/spec.md) (root capability, family-index style; MODIFIED lines below extend existing REQs, the ADDED line is a new root-level REQ summary).

---

## Summary

Three cosmetic + usability fixes on the already-shipped read-only Rich dashboard (`flow workspace dashboard`):

1. **Output integrity** — terminal-safe on cp1252 + UTF-8; long names wrap (not truncate); the Unicode U+2026 ellipsis NEVER appears in dashboard output.
2. **Dot-prefix scan filter** — `.atl`, `.opencode`, `.venv`, `.pytest_cache`, etc. are tooling/config, never user projects. View-only filter (no deletion, no mutation).
3. **R1 detail** — when any project has R1 triggered, list dirty file paths in a new Section E; cap 20 files/project; ASCII `...` ellipsis; footer hint to run `git status` for the full list.

**Role of this file**: SDD ceremony artifact for traceability. The MODIFIED + ADDED sections below contain the canonical delta REQ wording that `sdd-archive` will merge into `openspec/specs/workspace/spec.md`. Per Project convention, the root spec anchors REQs via `Source:` lines pointing back to this delta.

---

## ADDED Requirements

### Requirement: REQ-WORKSPACE-DASHBOARD-R1-DETAIL

When at least one project has `R1: uncommitted work` triggered, the dashboard MUST render a **Section E** listing, per R1-triggered project, the list of dirty file paths as reported by `git status --porcelain`. The section MUST be omitted when no R1 is triggered.

**Constraints**:
- Per-project dirty file list MUST be **capped at 20 entries**. Projects with more than 20 dirty files MUST be rendered with a trailing ASCII `...` ellipsis and a footer hint reading `run `git status` for full list` (ASCII ellipsis only — NEVER the Unicode U+2026 character).
- The dirty-file list MUST come from the existing `git status --porcelain` subprocess already invoked by `_detect_project_markers` — the system MUST NOT issue a second subprocess per project to gather this data.
- The `dirty_files: list[str]` field on the `needs_attention` entry MUST be **additive** to the DS1 + DS2 envelope shape (`version: "1"` is preserved). Existing consumers that ignore unknown keys MUST continue working without modification.
- The dashboard MUST remain **read-only**. Section E surfaces information only; no mutation path is exposed.

#### Scenario: Section E renders when exactly one project has R1 triggered

- GIVEN the workspace contains 5 projects
- WHEN exactly one project has `dirty == True` and reports 3 dirty file paths via `git status --porcelain`
- AND the operator runs `flow workspace dashboard`
- THEN the rendered output contains a Section E titled `R1 dirty files`
- AND Section E lists the triggering project name
- AND Section E lists the 3 dirty file paths for that project
- AND Sections A/B/C/D continue to render in order (header / needs / archived / footer)

#### Scenario: Section E is hidden when no project has R1 triggered

- GIVEN the workspace contains N projects
- WHEN zero projects have `dirty == True`
- AND the operator runs `flow workspace dashboard`
- THEN the rendered output does NOT contain any Section E
- AND the output continues with Section C (archived) or Section D (footer) after Section B

#### Scenario: Section E caps at 20 dirty files per project with ASCII ellipsis

- GIVEN a single project has `dirty == True` and reports 25 dirty file paths via `git status --porcelain`
- WHEN the operator runs `flow workspace dashboard`
- THEN Section E lists exactly 20 of those paths for that project
- AND the last rendered entry of that project's list ends with `...` (three ASCII periods)
- AND a footer hint reading `run `git status` for full list` (or equivalent) appears for that project

#### Scenario: Section E handles a project with exactly 20 dirty files (no ellipsis)

- GIVEN a single project has `dirty == True` and reports exactly 20 dirty file paths via `git status --porcelain`
- WHEN the operator runs `flow workspace dashboard`
- THEN Section E lists all 20 paths for that project
- AND no `...` ellipsis appears (the cap is inclusive; 20 does not truncate)

#### Scenario: Section E for a project with 0 dirty files is hidden

- GIVEN a project has `R1: uncommitted work` triggered
- BUT `git status --porcelain` reports 0 dirty lines (boolean guard but empty list)
- WHEN the operator runs `flow workspace dashboard`
- THEN that project does NOT appear in Section E (Section E only lists projects with non-empty `dirty_files`)
- AND Sections A/B/C/D continue to render in order

#### Scenario: Section E renders ASCII `...` ellipsis when more than 20 dirty files

- GIVEN a project has 30 dirty file paths reported by `git status --porcelain`
- WHEN Section E is rendered for that project
- THEN the rendered output contains the ASCII 3-character sequence `...` (never the Unicode U+2026 ellipsis character) as the trailing marker after the 20th entry

#### Scenario: DS1 + DS2 envelopes remain schema-compatible with additive `dirty_files` field

- GIVEN `_detect_project_markers` now captures `dirty_files: list[str]` from `git status --porcelain` stdout
- WHEN `flow projects ls --json` is invoked
- THEN the v1 JSON envelope emits `version: "1"` as its first key
- AND each project entry MAY include an optional `dirty_files: [...]` array (omitted or empty when clean)
- WHEN `flow workspace status --json` is invoked
- THEN the `needs_attention` list MAY include an optional `dirty_files: [...]` array on entries where R1 triggered

#### Scenario: Existing pydantic / JSON consumers ignore the additive `dirty_files` key

- GIVEN a downstream consumer parses `flow projects ls --json` or `flow workspace status --json`
- WHEN the consumer uses `extra="ignore"` (pydantic default) or `JSONObject` key-iteration
- THEN the consumer continues to parse the envelope without error
- AND no existing REQ binding breaks

---

## MODIFIED Requirements

> Per the project's family-index style, the canonical REQ wording for the two requirements below lives at `openspec/specs/workspace/spec.md` §4. This delta extends each REQ with a sub-clause; the archive step will merge the sub-clause back into the root spec without duplicating the parent block.

### Requirement: REQ-WORKSPACE-DASHBOARD-RENDERS-RICH (EXTEND — output integrity sub-clause)

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-RENDERS-RICH`](../../../../specs/workspace/spec.md#req-workspace-dashboard-renders-rich)
**Source delta**: `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` (REQ-DASHBOARD-RENDERING + REQ-DASHBOARD-FLAGS + REQ-DASHBOARD-ZERO-DEPS).
**Previously**: rendering covered Rich tables/panels/colors and `--no-color`; column widths defaulted to Rich auto-sizing with Unicode U+2026 ellipsis truncation on overflow.

**Extension (new sub-clause §4.1 "Output integrity")**:

The dashboard MUST render correctly on terminals using cp1252 or UTF-8 encoding; long project names MUST wrap (not truncate) within their column bounds; the Unicode U+2026 ellipsis MUST NOT appear in dashboard output. Specifically:

- The CLI handler MUST attempt `sys.stdout.reconfigure(encoding="utf-8")` wrapped in `try/except OSError`; the encoding MUST default to UTF-8 when reconfigure succeeds and fall back to current behavior when it does not.
- The `rich.console.Console` MUST be instantiated with `soft_wrap=True` and an explicit `width` (terminal-detected with a sensible default).
- Section B, Section C, and Section E columns MUST declare explicit `min_width` + `max_width` + `overflow=OverflowMethod.fold` (wrap) or `OverflowMethod.crop` (no ellipsis); the Unicode U+2026 ellipsis MUST NEVER appear in any rendered column.

#### Scenario: UTF-8 terminal renders long + ASCII project names without replacement chars

- GIVEN the terminal codec is `utf-8`
- AND a project is named `Gestor-de-Contrase-as` (21 ASCII chars)
- WHEN the operator runs `flow workspace dashboard` against a workspace containing that project
- THEN the rendered project name in Section B contains no `\ufffd` (U+FFFD) replacement characters
- AND the project name either fits the column (unmodified) OR wraps onto multiple lines (folded)
- AND no `...` (or `...`) ellipsis appears in the name cell

#### Scenario: cp1252 terminal renders long + non-ASCII project name without replacement chars

- GIVEN the terminal codec is `cp1252`
- AND a project is named `Gestor-de-Contrasenas` (21 chars)
- AND `sys.stdout.reconfigure(encoding="utf-8")` succeeds
- WHEN the operator runs `flow workspace dashboard` against a workspace containing that project
- THEN the rendered project name in Section B contains no `\ufffd` (U+FFFD) replacement characters
- AND the name is rendered faithfully (cp1252 sees UTF-8 bytes when stream is reconfigured)

#### Scenario: Legacy terminal where `sys.stdout.reconfigure` raises `OSError` does not crash

- GIVEN `sys.stdout.reconfigure(encoding="utf-8")` raises `OSError` (e.g., redirected pipe or non-TTY)
- WHEN the operator runs `flow workspace dashboard`
- THEN the dashboard handler does NOT raise; it falls back to current behavior using the default stream encoding
- AND no `\ufffd` (U+FFFD) replacement characters appear in stdout for ASCII-only project names
- AND the handler completes with exit code 0

#### Scenario: Column overflow folds rather than truncates with Unicode ellipsis

- GIVEN a Section B column has `max_width=20` and `overflow=OverflowMethod.fold`
- AND a project name is 35 characters long
- WHEN the dashboard renders Section B
- THEN the name cell wraps the visible content across at least 2 lines
- AND the rendered output contains NO Unicode `\u2026` (`...`) ellipsis character anywhere in the cell

#### Scenario: `--no-color` still disables ANSI codes after the encoding fix

- GIVEN the operator passes `--no-color`
- WHEN the operator runs `flow workspace dashboard`
- THEN the rendered output contains no Rich ANSI escape sequences (`\x1b[`)
- AND the encoding + width sub-clause remains in effect (ASCII-safe, no `...` ellipsis in any cell)
- AND Sections A/B/C/D (+E when R1 triggered) still render in order

#### Scenario: Console `width` defaults reasonably on narrow terminals

- GIVEN the terminal reports `os.get_terminal_size().columns = 80`
- WHEN the operator runs `flow workspace dashboard`
- THEN `Console(width=<auto-detected or 120>, soft_wrap=True)` is used
- AND Section B wraps columns to fit
- AND no `...` ellipsis appears in any table cell under `width=80`

---

### Requirement: REQ-WORKSPACE-PROJECT-IDENTITY (MODIFY — dot-prefix excluded)

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-PROJECT-IDENTITY**](../../../../specs/workspace/spec.md#req-workspace-project-identity)
**Source delta**: `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` (REQ-FIELD-EXTENSION + REQ-SCHEMA-VERSIONING + REQ-DETERMINISTIC-ORDER).
**Previously**: a project is identified by 11 static metadata fields emitted by `flow projects ls`. No explicit enumeration-source statement at root REQ level.

**Sub-clause addition**: The list of projects enumerated by `flow projects ls` (and the workspace-status summaries derived from it) MUST be the set of immediate subdirectories of the projects root, EXCLUDING any entry whose name starts with `.` (dot). Dot-prefix entries (`.atl`, `.opencode`, `.venv`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.specify`, `.github`, etc.) are tooling/config and never user projects.

The filter is **view-only**: dot-prefix directories MUST NOT be deleted, archived, moved, or otherwise mutated by this change. They remain on disk in their original location; the filter only excludes them from the enumerated project list.

#### Scenario: Workspace with only real projects (no dot-prefix) returns the same set as before

- GIVEN the projects root contains N subdirectories, none starting with `.`
- WHEN `flow projects ls` runs
- THEN the returned project list is identical (modulo sorting) to the pre-change behavior for those N directories
- AND `flow projects ls --json` still emits `version: "1"` as the first key

#### Scenario: Workspace with mixed children (regular + dot-prefix) returns only the regular ones

- GIVEN the projects root contains subdirectories: 3 regular (`alpha`, `beta`, `gamma`) and 5 dot-prefix (`.atl`, `.opencode`, `.venv`, `.pytest_cache`, `.github`)
- WHEN `flow projects ls` runs
- THEN the returned project list contains exactly 3 entries: `alpha`, `beta`, `gamma`
- AND none of `.atl`, `.opencode`, `.venv`, `.pytest_cache`, `.github` appear in the returned list

#### Scenario: Dot-prefix filter applies to `flow workspace status` totals

- GIVEN the projects root contains 3 regular + 5 dot-prefix subdirectories (as above)
- WHEN `flow workspace status` runs
- THEN the `totals` block reports `projects: 3` (NOT 8)
- AND `flow workspace status --json` reports `totals.projects: 3`
- AND the `needs_attention` list (and any per-rule aggregates) is computed from the 3 regular projects only

#### Scenario: Dot-prefix filter applies to the dashboard render

- GIVEN `flow projects ls --json` reports 3 projects (after filtering)
- WHEN the operator runs `flow workspace dashboard`
- THEN Section B (needs-attention table) iterates exactly 3 projects
- AND Section C (archived projects list) shows only archived entries — unaffected by the scan filter (archived projects come from `~/.flow-engineering/registry.json`, not from the on-disk scan)
- AND the header panel totals reflect the filtered count

#### Scenario: Dot-prefix filter preserves byte-identical JSON for `flow projects ls --json` shape (no schema change)

- GIVEN the projects root contains the same N regular subdirectories as pre-change
- WHEN `flow projects ls --json` runs
- THEN the JSON envelope keys are unchanged: `version`, `projects`, each entry has the 11 static metadata fields
- AND no `dot_prefix_excluded` count, path, or debug key is added to the envelope
- AND the additive model (consumers ignore unknown keys; unknown keys are NEVER added by this filter) is preserved

---

## Additive DS2 envelope change (no formal REQ modification)

`flows workspace status --json` envelope shape is preserved at `version: "1"`. The `needs_attention` list entries gain an **optional** `dirty_files: list[str]` field when R1 triggered:

```jsonc
{
  "version": "1",
  "totals": { /* unchanged 8 integer fields */ },
  "projects": [ /* unchanged from Phase 1 detector */ ],
  "needs_attention": [
    {
      "name": "flow-engineering",
      "path": "C:/dev/proyects/flow-engineering",
      "reasons": ["R1: uncommitted work"],
      "dirty_files": [" M src/foo.py", "?? src/bar.py"]   // ADDITIVE
    }
  ]
}
```

- Field type: `list[str]` where each element is one line of `git status --porcelain` output verbatim (2-char XY status + space + path).
- Default when clean / not R1-triggered: field absent (not `null`).
- Consumers that ignore unknown keys (pydantic `extra="ignore"`, JSON-object iteration) MUST continue working unchanged.

#### Scenario: `flow workspace status --json` includes `dirty_files` for R1-triggered project

- GIVEN a project has `R1: uncommitted work` triggered and `git status --porcelain` returns 5 lines
- WHEN the operator runs `flow workspace status --json`
- THEN the entry for that project in `needs_attention` contains a `dirty_files` field
- AND the field is a JSON array of 5 strings
- AND each string matches the verbatim output of `git status --porcelain` (2-char status + space + path)

#### Scenario: `flow workspace status --json` omits `dirty_files` when R1 not triggered

- GIVEN a project has only R3 + R4 triggered (no R1)
- WHEN the operator runs `flow workspace status --json`
- THEN the entry for that project does NOT contain a `dirty_files` key
- AND the entry's keys are exactly `name`, `path`, `reasons` (3 keys, not 4)

#### Scenario: Byte-identical existing-key guard for JSON envelope consumers

- GIVEN the v1 envelope has been consumed by other tools in past versions
- WHEN `flow workspace status --json` is invoked against the same workspace
- THEN every previously-existing key (`version`, `totals.<8 fields>`, `projects[].*`, `needs_attention[].name/path/reasons`) is byte-identical to its pre-change representation
- AND any new `dirty_files` field is optional + additive (its presence does NOT alter the meaning or order of existing keys)

---

## Regression Scenarios (existing behavior preserved)

> These scenarios assert that no existing dashboard behavior, CLI behavior, or JSON envelope shape is REGRESSED by this change. `sdd-verify` will run them as part of the verification phase.

#### Scenario: 4-section structure (A/B/C/D) still renders in order when no archive present

- GIVEN the workspace contains N projects and ZERO archived projects
- WHEN the operator runs `flow workspace dashboard`
- THEN the rendered output contains Section A (header panel) → Section B (needs-attention table) → Section D (footer)
- AND Section C (archived) is omitted (no archive)
- AND the order A → B → D is preserved

#### Scenario: 4-section structure (A/B/C/D) still renders with archive present

- GIVEN the workspace contains 1 archived project in `~/.flow-engineering/registry.json`
- WHEN the operator runs `flow workspace dashboard`
- THEN the rendered output contains Section A → Section B → Section C (archived) → Section D (footer)
- AND Section C shows exactly the 1 archived project entry

#### Scenario: `--filter RULES` flag behavior preserved (per R1..R5 rule filter)

- GIVEN the operator passes `--filter R2`
- WHEN the operator runs `flow workspace dashboard`
- THEN Section B only shows projects that triggered R2
- AND all other section ordering + widths apply normally
- AND the change introduces NO new flag values

#### Scenario: `--sort FIELD` flag behavior preserved (per name/path/needs-count)

- GIVEN the operator passes `--sort path`
- WHEN the operator runs `flow workspace dashboard`
- THEN Section B projects are sorted ascending by `path`
- AND all other section ordering + widths apply normally
- AND the change introduces NO new flag values

#### Scenario: `--no-color` flag behavior preserved

- GIVEN the operator passes `--no-color`
- WHEN the operator runs `flow workspace dashboard`
- THEN no ANSI color codes appear in stdout
- AND all section ordering + widths apply normally

#### Scenario: JSON identity at `flow workspace status --json` for non-R1 projects

- GIVEN a project has only R2 triggered (no R1)
- WHEN `flow workspace status --json` runs
- THEN the project's `needs_attention` entry has EXACTLY 3 keys: `name`, `path`, `reasons`
- AND no `dirty_files` key is present
- AND the rest of the envelope is byte-identical to pre-change JSON output

#### Scenario: JSON identity at `flow projects ls --json` is preserved (no schema change)

- GIVEN a workspace with N projects (after dot-prefix filter)
- WHEN `flow projects ls --json` runs
- THEN the v1 envelope emits `version: "1"` first
- AND each project entry has the 11 static metadata fields
- AND no new top-level keys (no `dot_prefix_excluded`, no per-project `dot_prefix` flag)

#### Scenario: Dashboard remains read-only — no mutation paths exposed

- GIVEN the dashboard command is `flow workspace dashboard`
- WHEN the operator runs `flow workspace dashboard --help`
- THEN the help text lists `--filter`, `--sort`, `--no-color` (no `--fix`, no `--archive`, no `--restore`, no `--yes`, no `--detail`, no `--encoding`, no `--show-dirty`, no `--json`)
- AND exit code is 0

#### Scenario: No new runtime dependencies introduced

- GIVEN `pyproject.toml` at v1.2.0
- WHEN this change is applied
- THEN `rich` MAY be promoted to a direct dependency (zero-cost: already transitive)
- AND no other package is added to `pyproject.toml` `dependencies` or `[dependency-groups]`

---

## Out of Scope

Hard constraints (per `proposal.md` §2.2 and preflight):

- **No TUI / web / interactive surfaces** — Textual, urwid, prompt_toolkit, Blessed; FastAPI, Streamlit, Dash, Panel; real-time updates, file watching, websocket, interactive forms (Phase 5.2 territory).
- **No new subcommands** beyond `flow workspace dashboard`.
- **No new flags** on the dashboard (`--detail`, `--encoding`, `--show-dirty`, etc. are all explicitly absent per Pattern #538 + read-only constraint).
- **No mutations** to the registry, the filesystem, or any project directory.
- **No modifications** to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) / 3 prior follow-up commits (Pattern #548).
- **No touch** of `openspec/changes/v1.1-followups/` (sacred territory).
- **No modifications** to `openspec/specs/workspace/spec.md` directly (deferred to the next cleanup cycle; this delta only adds an ADDED REQ summary at archive time).
- **No new runtime dependencies** (`rich` promotion is zero-cost).
- **No `stash`-triggering words** in any new code or commit message.
- **No AI attribution** in commits (per `AGENTS.md`).
- **No modifications** to Phase 1/2/3/4 mutation gates or existing CLI commands.
- **No audit-only exceptions to `where.py:461`** — the dot-prefix filter does NOT apply to `flow where` cross-project search in this change. Audit flagged for `flow-where-followup`.

---

## Acceptance Criteria (16 ACs)

| AC | Description | Verification |
|----|-------------|--------------|
| **AC1** | UTF-8 terminal renders ASCII project names with no `\ufffd` chars | Snapshot test with `Console(width=40, no_color=True, soft_wrap=True)` + `sys.stdout.reconfigure` succeeds |
| **AC2** | cp1252 terminal reconfigure succeeds and renders no `\ufffd` chars | Snapshot test with cp1252 codec fixture |
| **AC3** | `OSError` on reconfigure falls back gracefully | Mock `sys.stdout.reconfigure` raising `OSError`; assert exit 0 and no crash |
| **AC4** | Section B column overflow folds (NOT truncates) | Test against `OverflowMethod.fold` + 35-char name + 20-char `max_width` |
| **AC5** | `--no-color` still disables ANSI codes after fix | Capture stdout, assert no `\x1b[` |
| **AC6** | Dot-prefix scan filter excludes mixed children | `tmp_path` fixture: 3 regular + 5 dot-prefix dirs; `flow projects ls` returns 3 |
| **AC7** | Workspace status totals reflect filtered project count | `--json` envelope reports `totals.projects: 3` |
| **AC8** | Existing `flow projects ls --json` envelope shape unchanged | Byte-identical guard (no new top-level keys) |
| **AC9** | Section E renders for one R1 project | Snapshot test on `render_dashboard` with 1 R1-triggered project |
| **AC10** | Section E hidden when no R1 triggered | Snapshot test on `render_dashboard` with no R1 |
| **AC11** | Section E caps at 20 dirty files with ASCII `...` | Fixture: project with 25 dirty files; assert exactly 20 listed + `...` marker |
| **AC12** | Footer hint appears for capped projects | Capture Section E footer text |
| **AC13** | `dirty_files` field is additive on DS2 envelope | JSON parse; assert `version: "1"` preserved; assert key absent for non-R1 |
| **AC14** | Dashboard remains read-only (`flow workspace dashboard --help`) | String-match help text against exact substring |
| **AC15** | No new runtime deps (`pyproject.toml` byte-compare for `[dependency-groups]`) | `git diff pyproject.toml -- dependencies` |
| **AC16** | 4-section structure preserved (A/B/C/D order + content) | Snapshot test against `render_dashboard` |

---

## Open Questions (resolved at spec phase)

| Q | Question | Resolution |
|---|----------|------------|
| Q1 | `Console.width` — auto-detect vs explicit? | **Explicit default `120` + best-effort auto-detect override** (mirrors `test_dashboard.py:87` snapshot pattern) |
| Q2 | Dot-prefix filter — apply to `flow where` too? | **Out of scope** for this change. Audit `where.py:461` separately; flagged for `flow-where-followup` |
| Q3 | R1 footer hint — generic or specific to Section E? | **Amend render_footer to add Section E pointer** when R1-triggered projects exist (3rd tip line) |
| Q4 | `_detect_project_markers` — capture `dirty_files` only when dirty=True, or always? | **Always (empty list when clean)** — cheaper to consume downstream |
| Q5 | Real `.config` project caveat? | **Caveat acknowledged in changelog, NOT a fail-case** in the spec. All 3 retrospective cycles confirm no real dot-prefix project. Filter is view-only (no deletion). |

---

## Known Caveats (documented for downstream consumers)

1. **Dot-prefix filter excludes real dot-prefix projects** — if the operator has a real project named `.config`, `.private`, etc., it will be hidden from `flow projects ls`, `flow workspace status`, and `flow workspace dashboard`. No data loss (filter is view-only); reveal via direct filesystem or by renaming. Document in changelog.
2. **`flow where` cross-project search is NOT filtered** — `where.py:461` still iterates all subdirs. Audit deferred to `flow-where-followup`.
3. **DS2 envelope additive field** — `dirty_files` is a new key. Consumers pinned to the v1 envelope by structural key check (not just `extra="ignore"`) MAY need a whitelist update. Out-of-scope to detect; documented in changelog.

---

## Constraints honored (per preflight)

- ASCII-only ellipsis (`...`); the Unicode U+2026 character is forbidden in any example or scenario title.
- Cap 20 files per R1 detail.
- No new CLI flags.
- No mutations to registry or filesystem.
- No new runtime deps (`rich` already transitive; promotion is zero-cost).
- No `stash`-triggering words.
- No AI attribution in commits.
- No touch of `v1.1-followups/`.
- No modifications to PR1/PR2/PR3/sort-projects/3-prior follow-ups.
- Pattern #538 (one identity per command) preserved — `--json` stays absent from dashboard.
- Pattern #548 (don't touch green commits) preserved.
- Pattern #551 (guards as instruments) applied to `sys.stdout.reconfigure`.
- Strict TDD ×6 multiplier forecast (≈930 LOC) tracked for `sdd-tasks` PR-budget gate.

---

## Next SDD Phase

`sdd-design` — write the technical design document for this change. The orchestrator dispatches `sdd-tasks` after both `sdd-design` and this spec return.

---

*Generated by the `sdd-spec` sub-agent for `workspace-dashboard-usability-pass`. Spec artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-usability-pass/spec"`, `type: "architecture"`, `capture_prompt: false`, `project: flow-engineering`.*

