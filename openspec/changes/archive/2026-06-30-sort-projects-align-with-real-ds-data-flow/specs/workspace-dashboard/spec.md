<!-- change spec: sort-projects-align-with-real-ds-data-flow (sdd-spec ceremony artifact). Mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Cross-References). Authoritative source: openspec/changes/sort-projects-align-with-real-ds-data-flow/proposal.md (Option A locked). -->
# sort-projects-align-with-real-ds-data-flow (change)

> **Change**: `sort-projects-align-with-real-ds-data-flow`
> **Phase**: spec (3/7 of SDD cycle)
> **Author**: sdd-spec sub-agent
> **Date**: 2026-06-30
> **Project**: flow-engineering (v1.2.0, main HEAD `5f28f68`)
> **Artifact store**: `openspec` (writes `openspec/changes/sort-projects-align-with-real-ds-data-flow/specs/workspace-dashboard/spec.md` + Engram mirror)
> **Strict TDD**: ON (CODE change — RED → GREEN → REFACTOR discipline mandatory at apply phase)
> **User reasoning**: *"corrige el contrato antes de que el dashboard crezca"* — fix the contract before the dashboard grows
> **Status**: COMPLETE — ready for design phase

---

## Summary

`sort_projects` (`src/flow_engineering/dashboard.py`) currently reads reasons via `project.get("reasons", [])` — a field that does NOT exist on real DS1 project dicts. Real reasons live on entries in `summary["needs_attention"]` keyed by project name. The sort silently no-ops in production (all counts = 0 → tied → stable input order). This change adds an explicit `needs_by_name` parameter so `sort_projects` reads reasons from the correct DS2 data source. No spec-level behavior change for operators (`--sort needs-count` still orders descending); only the count source is corrected.

**Approach (Option A locked)**: `sort_projects` gains keyword-only `needs_by_name: Mapping[str, list[str]] | None = None`. Caller in `workspace_dashboard_cmd` builds it from `summary["needs_attention"]`. Backward-compat: `needs_by_name=None` falls back to inline `reasons` with `DeprecationWarning`.

**Design note carry-forward**: Phase 5.2 (TUI/web) will need the same `needs_by_name` derivation. Track as separate follow-up `extract-build-needs-by-name-helper`.

## ADDED Requirements

### Requirement: REQ-DASHBOARD-SORT-DATA-FLOW

`sort_projects` MUST resolve the `needs-count` source from a name-keyed reasons map (`needs_by_name`) rather than from an inline `reasons` field on each project dict. Real DS1 envelope shape does NOT carry `reasons`; reasons live on entries in `summary["needs_attention"]`. The caller (`workspace_dashboard_cmd`) MUST derive `needs_by_name` from DS2 and pass it as a keyword-only argument.

When `needs_by_name` is `None`, the function MAY fall back to `len(project.get("reasons", []))` AND MUST emit `DeprecationWarning` to surface stale call sites. The fallback SHALL be removed in the next minor refactor (`extract-build-needs-by-name-helper` follow-up).

#### Scenario: Sort by needs-count descending using real DS2 reasons

- GIVEN a list of project dicts with the real DS1 envelope shape (no `reasons` field)
- AND a `needs_by_name` map derived from `summary["needs_attention"]`
- WHEN the caller invokes `sort_projects(projects, "needs-count", needs_by_name=needs_by_name)`
- THEN projects MUST be ordered by `len(needs_by_name.get(project["name"], []))` DESCENDING

#### Scenario: Backward-compat fallback emits DeprecationWarning

- GIVEN project dicts that carry inline `reasons` (legacy / pre-refactor shape)
- AND `needs_by_name` is `None` (the default)
- WHEN the caller invokes `sort_projects(projects, "needs-count")`
- THEN the function MUST read `len(project.get("reasons", []))` per project
- AND MUST emit `DeprecationWarning` once per call (stacklevel 2) signaling the inline-`reasons` shape is deprecated

#### Scenario: Empty needs_by_name returns stable input order

- GIVEN project dicts with no matching needs (none present in `needs_by_name`)
- WHEN the caller invokes `sort_projects(projects, "needs-count", needs_by_name={})`
- THEN all counts resolve to 0
- AND the result preserves the original input order (Python `sorted` is stable for equal keys)

#### Scenario: Caller derives needs_by_name from summary["needs_attention"]

- GIVEN `summary["needs_attention"]` as a list of `{project: name, reasons: [...]}` (or `{name: ...}`) dicts
- WHEN `workspace_dashboard_cmd` prepares the sort input
- THEN it MUST build `needs_by_name` keyed by project name with the corresponding `reasons` list
- AND pass it as `sort_projects(projects, sort, needs_by_name=needs_by_name)` (keyword-only)

## MODIFIED Requirements

### Requirement: REQ-DASHBOARD-FLAGS

Three flags supported:

- **`--filter RULES`** (optional, repeatable): Filter needs-attention table by rules R1/R2/R3/R4/R5 (Phase 3 rule set). Default: all rules surfaced.
- **`--sort FIELD`** (optional, default `name`): Sort by `name` / `path` / `needs-count`. For `needs-count`, the sort resolves per **`REQ-DASHBOARD-SORT-DATA-FLOW`** — reasons are read from DS2 `needs_attention`, NOT from inline project dict fields.
- **`--no-color`** (optional, off by default): Disable Rich ANSI color codes for CI / piping / non-TTY environments.

**No `--json` flag.** The dashboard is for human operators (visual); machine-readable output stays at `flow workspace status --json`. Pattern #538 (one identity per command).
(Previously: `--sort FIELD` described sort semantics without specifying the data source contract — added explicit reference to `REQ-DASHBOARD-SORT-DATA-FLOW` to lock the DS2-keyed derivation.)

#### Scenario: --sort needs-count uses real DS2 reasons (anchor unchanged)

- GIVEN the dashboard renders a project × R1–R5 table
- WHEN operator invokes `flow workspace dashboard --sort needs-count`
- THEN projects with the most real DS2 needs-attention reasons appear at the top of the table

## REMOVED Requirements

None. No existing requirement is deprecated or removed by this change.

## BDD Scenarios

Four scenarios covered under `REQ-DASHBOARD-SORT-DATA-FLOW` (above): descending sort, deprecation fallback, empty-map stability, caller derivation. All four are testable via pytest under strict TDD at the apply phase. No Gherkin `.feature` file needed for this internal-correctness fix.

## Out of Scope

- **No new runtime dependencies** (rich is transitive, preserved).
- **No `--json` flag on dashboard** (Pattern #538 — still enforced).
- **No modification of PR1 commit `6651add` / PR2 commit `95e8579` / PR3 commit `778efdb`** (Pattern #548 — dashboard commits stay byte-identical).
- **No touch of `openspec/changes/v1.1-followups/`** (sacred territory).
- **No extraction of `build_needs_by_name(needs_attention)` helper in this change** — deferred to Phase 5.2 prep follow-up `extract-build-needs-by-name-helper`.
- **No modifications to `fetch_project_list` / `fetch_status_summary`** (PR1 data layer locked).
- **No modifications to `render_needs_table` / `render_dashboard`** (rendering layer already iterates over `needs_attention` correctly — only `sort_projects` had the data flow bug).
- **No removal of the `DeprecationWarning` fallback in this PR** — kept for one minor cycle to surface stale call sites; documented removal in the follow-up.

## Cross-References

- **Proposal** (authoritative): `openspec/changes/sort-projects-align-with-real-ds-data-flow/proposal.md` (Option A locked; 9 ACs AC1–AC9; rollback plan; 5 risks LOW except #4 MEDIUM mitigated).
- **Explore**: Engram `#562` (4 options A/B/C/D surveyed; Option A chosen for `filter_by_rules` pattern alignment).
- **Verify-report carry-forward**: Engram `#557` (Phase 5 PR3 §"DESIGN NOTE Carry-Forward" — origin of this change).
- **Canonical root REQ** (unchanged): `openspec/specs/workspace/spec.md` §4 `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` (color-coded rendering) — this delta does NOT modify the root REQ; only the delta-internal `REQ-DASHBOARD-FLAGS`.
- **Delta-internal source**: `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` → `REQ-DASHBOARD-FLAGS` (modified) + new `REQ-DASHBOARD-SORT-DATA-FLOW`.
- **Code target**: `src/flow_engineering/dashboard.py` L253–295 (`_needs_count` helper + `sort_projects`); `src/flow_engineering/cli.py` L3034–3072 (`workspace_dashboard_cmd`).
- **Test targets**: `tests/unit/test_dashboard.py` L458–472 (T5 sort test rewrite) + 2 new tests; `tests/unit/test_cli_dashboard.py` L37–39 (`_make_project` helper) + T12.3 integration test rewrite.
- **Sibling patterns cited**: Engram `#548` (don't touch green commits), Engram `#554` (process not obedience), Engram `#555` (fix foundation before UI).
- **Follow-up**: `extract-build-needs-by-name-helper` (Phase 5.2 prep) — extract shared helper to prevent Phase 5.2 TUI/web callers from re-implementing the `needs_by_name` derivation.
- **Engram mirror** (this spec): topic_key `sdd/sort-projects-align-with-real-ds-data-flow/spec`; type `architecture`; `capture_prompt: false`; project `insyd`.