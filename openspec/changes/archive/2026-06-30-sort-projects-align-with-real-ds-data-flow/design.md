# Design: sort-projects-align-with-real-ds-data-flow

## Header

- **Change**: `sort-projects-align-with-real-ds-data-flow`
- **Phase**: design (4/8 of SDD cycle)
- **Strict TDD**: ON — RED → GREEN → REFACTOR per task (described here, applied in `sdd-tasks` + `sdd-apply`)
- **Design philosophy**: "resolve ambiguities in design, not rushed in apply" (Pattern #558)
- **Inputs**: spec #566 (1 ADDED `REQ-DASHBOARD-SORT-DATA-FLOW` + 1 MODIFIED `REQ-DASHBOARD-FLAGS`), proposal #564 (Option A locked, 9 ACs, 5 risks), explore #562 (4 options surveyed)
- **Output**: this `design.md` — locks the **`project` vs `name` key ambiguity**, the `needs_by_name` keyword-only pattern, the `DeprecationWarning` semantics, the caller contract, and the two follow-up changes
- **Forecast**: ~8 min wall-time for design; ~30 min remaining for tasks/apply/verify/archive (per §14)

---

## 2. Architecture overview

Small contract fix. The design's only non-mechanical job is to **RESOLVE** the `project` vs `name` ambiguity in `needs_attention` entries (the spec's `{project: name, ...} (or {name: ...})` phrasing was deliberately left open for design to lock). Once locked, `sdd-tasks` derives tasks mechanically, and `sdd-apply` follows a tight RED → GREEN → REFACTOR cycle. Reference: Pattern #558 (resolve ambiguities in design, not apply).

Data flow after the fix:

```
flow workspace status --json
        │
        ▼
_summary (cli.py:2913-2919)   ── builds entries with key="name", NEVER "project"
        │
        ▼
status_envelope["needs_attention"]   ── List[{"name": str, "path": str, "reasons": List[str]}]
        │
        ▼
workspace_dashboard_cmd (cli.py:3065-3069)
        │
        ├─ filter_by_rules(projects, needs_attention, ...)  ── already reads entry["name"] (dashboard.py:242)
        │
        ▼
build_needs_by_name(needs_attention)   ── INLINE for this change; EXTRACT in follow-up
        │     keys: project name (entry["name"])
        │     values: list[str] of reasons
        ▼
sort_projects(projects, field, *, needs_by_name=...)   ── dashboard.py:259 (with new kw-only param)
```

---

## 3. THE AMBIGUITY: `project` vs `name` — **RESOLVED: `name`**

### 3.1 The problem (now closed)

The spec #566 L56 phrased the entry shape as `{project: name, reasons: [...]} (or {name: ...})` — deliberately open for this design to lock. The proposal's code-block already used `name`; the design must confirm authoritatively.

### 3.2 Investigation (evidence chain)

| Source | Location | What it shows |
|---|---|---|
| **Producer** `_summarize_workspace_status` | `cli.py:2913-2919` | Builds entries with keys `"name"`, `"path"`, `"reasons"` — **NO `"project"` key** |
| **Producer's producer** `_workspace_status_envelope` | `cli.py:2932-2938` | Forwards `summary["needs_attention"]` verbatim — no key munging |
| **Test fixture** `test_workspace_status_json_envelope_and_r4` | `test_cli_workspace_status.py:62` | `by_name = {item["name"]: item for item in payload["needs_attention"]}` — the production test indexes by `name` (not `project`) |
| **Existing consumer** `filter_by_rules` | `dashboard.py:242-244` | `name = entry.get("name")` — the only consumer of `needs_attention` already reads `name` |
| **Test helper** `_make_needs` | `test_cli_dashboard.py:42-44` | Returns `{"name": name, "reasons": reasons}` — test fixtures use `name` |
| **Proposal code block** | `proposal.md:107` | `project_name = need.get("name", "")` — proposal itself uses `name` |
| **Spec #566** | `specs/workspace-dashboard/spec.md:56, 57, 59` | Phrases `{project: name, ...} (or {name: ...})` — **the open phrasing that triggered this design lock** |

### 3.3 Decision (LOCKED)

**Each `needs_attention` entry uses key `"name"` — and ONLY `"name"`.** The key `"project"` does NOT exist anywhere in the codebase:

- it is NOT set by any producer (searched 28 references to `needs_attention` across `src/` and `tests/`)
- it is NOT read by any consumer
- it is NOT asserted in any test
- it is NOT used in any fixture

There is no "leftover from an earlier version" — there is no `project` key at all. The proposal's defensive fallback `need.get("project") or need.get("name", "")` would silently resolve to `""` because `need.get("project")` always returns `None`. The correct pattern is the simpler `need.get("name", "")` (which the proposal's own code block already uses).

**Resolution**: the spec's open phrasing at L56 collapses to `{name: <project name>, path: <path>, reasons: [strings]}`. The contract is **bilateral**: producers MUST emit `"name"`; consumers MUST read `"name"`. Future changes that introduce `"project"` as a separate key would be a breaking change requiring spec amendment + migration.

### 3.4 Downstream impact

- The caller in `workspace_dashboard_cmd` MUST read `need["name"]` (not `need.get("project")`)
- The test fixtures MUST use `{"name": ..., "reasons": ...}` shape
- Future cross-check: if any new code touches `needs_attention` entries, it MUST read `name`. Add to code review checklist for the PR.

---

## 4. The `needs_by_name` keyword-only pattern (LOCKED from proposal #564)

### Signature

```python
from collections.abc import Mapping
from typing import Any

def sort_projects(
    projects: list[dict[str, Any]],
    field: str,
    *,
    needs_by_name: Mapping[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
```

### Rationale

| Choice | Why |
|---|---|
| `Mapping` (not `dict`) | Accepts any mapping type (`dict`, `OrderedDict`, future `MappingProxyType`); cheap duck-typed API |
| Keyword-only `*` | Future-proofs Phase 5.2 (TUI/web); explicit signature; no positional ambiguity; existing positional callers (`sort_projects(projects, "name")`) unchanged |
| `| None` default | Backward-compat: callers that haven't migrated still work, get `DeprecationWarning` |
| Keys = project names (the resolved `name` from §3) | Single source of truth — DS2 envelope's `name` field |
| Values = `list[str]` of reasons | Mirrors `_summarize_workspace_status` shape (line 2917); preserves rule-prefix semantics for AC4 |

---

## 5. DeprecationWarning semantics (LOCKED from proposal #564)

### Trigger condition

`needs_by_name is None` **AND** `field == "needs-count"` (only the count path needs reasons; `name`/`path` sorts never read `reasons`).

### Warning message (exact text — locked here, copy verbatim in apply)

```
"sort_projects: needs_by_name=None is deprecated; pass it derived from DS2 needs_attention list. Remove the fallback in the next follow-up."
```

### Configuration

| Field | Value | Why |
|---|---|---|
| Category | `DeprecationWarning` | Standard library category; pytest can filter via `recwarn` |
| `stacklevel` | `2` | Points to the **caller** of `sort_projects`, not to `sort_projects` itself — exactly the surface that needs fixing |

### Behavior contract

- **Still computes the correct value**: `len(p.get("reasons", []))` (legacy path) — no silent regression
- **One warning per call** (Python's default for `warnings.warn` without a `skip_file_prefixes` filter) — acceptable; the call is rare (dashboard command)
- **No test should `warnings.simplefilter("error", DeprecationWarning)` globally** — use `pytest.warns(DeprecationWarning)` per-test or `filterwarnings("default")` in `pyproject.toml` (verify existing config in apply phase)

### Planned removal (target version v1.3.0)

When the follow-up `remove-sort-projects-deprecation-fallback` lands, the entire `needs_by_name is None` branch is deleted and the signature tightens to `needs_by_name: Mapping[str, list[str]]` (no `| None`). See §8.

---

## 6. Caller contract (LOCKED with the resolved key from §3)

### Caller identity

`workspace_dashboard_cmd` at `src/flow_engineering/cli.py:3049-3072`.

### Data source

`status_envelope["needs_attention"]` — the DS2 envelope's `needs_attention` list, fetched via `fetch_status_summary()` (cli.py:3063).

### Builder (inline for this change; extracted in follow-up §7)

```python
# Inserted at cli.py:3065-3068 (between `needs_attention` extraction and the filter/sort block)
needs_attention = status_envelope.get("needs_attention", [])
needs_by_name: dict[str, list[str]] = {}
for need in needs_attention:
    name = need.get("name", "")          # LOCKED key (§3); defensive default ""
    reasons = need.get("reasons", [])
    if name and isinstance(reasons, list):
        needs_by_name[name] = reasons
```

### Call site (cli.py:3069, replaced)

```python
projects = sort_projects(projects, sort, needs_by_name=needs_by_name)
```

### Defensive default rationale

`need.get("name", "")` (NOT `need["name"]`) preserves the contract for malformed envelopes (empty list, missing key) — defensive without hiding bugs. Empty `""` keys are dropped by the `if name` guard. This pattern matches `_summarize_workspace_status` discipline: silently tolerates malformed upstream data, never crashes.

### Out of contract (do NOT do this)

- ❌ Do NOT use `need.get("project") or need.get("name", "")` (the defensive fallback from proposal speculation) — it adds no value because `project` never exists
- ❌ Do NOT key by `path` (some needs-attention entries have `path`; spec and tests use `name`)
- ❌ Do NOT mutate `needs_attention` in place — `needs_by_name` is a fresh dict

---

## 7. Follow-up #1: `extract-build-needs-by-name-helper` (DOCUMENTED, NOT IMPLEMENTED)

| Field | Value |
|---|---|
| **Change name** | `extract-build-needs-by-name-helper` |
| **Goal** | Extract the builder from §6 ("Builder") into a shared module so Phase 5.2 (TUI/web) can reuse it without duplicating the 4-line dict-comprehension |
| **Target module** | New file `src/flow_engineering/dashboard_data.py` (preferred — namespace aligns with `dashboard.py` family) OR a function in `dashboard.py` exported alongside `sort_projects`. Decision deferred to that change's exploration. |
| **Public API** | `build_needs_by_name(needs_attention: Iterable[Mapping[str, Any]]) -> Mapping[str, tuple[str, ...]]` — returns reasons as immutable tuple; preserves rule prefixes |
| **Test responsibility** | The helper gets its own dedicated unit tests in the follow-up; the call-site test in this change verifies the caller passes the helper's output to `sort_projects` |
| **Why deferred** | This change is a small contract fix (~85 LOC); extracting a helper now adds a new module + import path + test file — out of scope. The inline version is fine for 1 caller. Extraction is justified at 2+ callers (workspace_dashboard_cmd + Phase 5.2's TUI/web). |
| **Trigger** | When Phase 5.2 starts OR when a 3rd caller of `sort_projects` appears |
| **Carry-forward** | This design.md + Engram #562 (explore) + follow-up placeholder in `design` topic |

---

## 8. Follow-up #2: `remove-sort-projects-deprecation-fallback` (DOCUMENTED, NOT IMPLEMENTED)

| Field | Value |
|---|---|
| **Change name** | `remove-sort-projects-deprecation-fallback` |
| **Goal** | Remove the `needs_by_name is None` branch in `sort_projects` (the inline-`reasons` fallback + `DeprecationWarning`); tighten signature to `needs_by_name: Mapping[str, list[str]]` (no `| None`) |
| **Why deferred** | This change is small; bundling the fix + the cleanup doubles blast radius. After all callers pass `needs_by_name` explicitly, the fallback can be safely removed in a focused PR. |
| **Trigger** | When ALL of (a) `workspace_dashboard_cmd` passes `needs_by_name` (this change), (b) Phase 5.2 TUI/web passes `needs_by_name` (Phase 5.2), (c) no other internal callers exist |
| **Target version** | **v1.3.0** — gives one minor release cycle (v1.2.x) for any missed external callers to surface `DeprecationWarning` |
| **Pre-conditions** | Grep confirms no callers of `sort_projects` pass only 2 positional args; CHANGELOG entry adds the `Deprecated since 1.2.0` notice |
| **Carry-forward** | This design.md + Engram #564 (proposal §DeprecationWarning) + placeholder in `design` topic |

---

## 9. Tests to add (described; RED → GREEN → REFACTOR per task in `sdd-tasks`)

Per proposal #564 "Tests to Add" + spec #566 Scenarios 1-4:

| ID | Test | Asserts | TDD stage |
|---|---|---|---|
| T1 | `test_sort_by_needs_count_uses_needs_by_name` | Real DS1 shape (no `reasons`), explicit `needs_by_name=...` → correct descending order | RED → GREEN |
| T2 | `test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning` | Inline `reasons` + `needs_by_name=None` → `pytest.warns(DeprecationWarning)` fires; value still correct | RED → GREEN |
| T3 | `test_sort_with_empty_needs_by_name_returns_zero_count` | `needs_by_name={}` → all counts = 0, input order preserved (Python `sorted` is stable) | RED → GREEN |
| T4 | `test_caller_passes_needs_by_name_to_sort_projects` (integration) | Monkey-patch `sort_projects`; invoke `workspace_dashboard_cmd` with mock DS1+DS2; assert `sort_projects` was called with `needs_by_name=` keyword whose keys match `need["name"]` | RED → GREEN |
| T5 | `test_make_project_helper_no_longer_includes_reasons` | `_make_project` returns dict WITHOUT `reasons` key (real DS1 shape); `_make_needs` already uses `name` key (no change needed) | REFACTOR-stage assertion |

**Test runner**: `uv run --frozen pytest tests/unit/test_dashboard.py tests/unit/test_cli_dashboard.py -v`

**Preset fixture shape change**: T5 (`test_sort_by_needs_count_descending` at `test_dashboard.py:458-472`) MUST be rewritten to use real DS1 shape + explicit `needs_by_name=...` — not just patched inline-`reasons`. This is the test that proves the bug is fixed (AC4).

---

## 10. File changes (atomic, single PR)

| File | Action | LOC est. | Description |
|---|---|---|---|
| `src/flow_engineering/dashboard.py` | MODIFY (L253-295 → ~L253-300) | ~20 | Inline `_needs_count` as closure inside `sort_projects`; add `*, needs_by_name=None`; emit `DeprecationWarning` on fallback. Header imports: `from collections.abc import Mapping`, `import warnings`. Remove the now-unused module-level `_needs_count` helper. |
| `src/flow_engineering/cli.py` | MODIFY (L3065-3069) | ~8 | After `needs_attention = status_envelope.get(...)`, append 4-line builder from §6; update `sort_projects(projects, sort)` → `sort_projects(projects, sort, needs_by_name=needs_by_name)`. |
| `tests/unit/test_dashboard.py` | MODIFY (T5 at L458-472) + ADD (T1, T2, T3 at end of `TestSortProjects`) | ~40 | Rewrite T5 to use real DS1 shape; add 3 new tests from §9. |
| `tests/unit/test_cli_dashboard.py` | MODIFY (`_make_project` at L37-39) + ADD (T4 at end of file) | ~25 | `_make_project` drops `reasons`; update T12.3 to assert no `reasons` in projects; add integration test for call-site wiring. |

**Net LOC delta**: ~85 LOC (matches exploration #562 forecast). PR is single-commit; well under chained-PR threshold of 400.

**Out of scope (DO NOT MODIFY)**:
- PR1 commit `6651add` (data layer) — byte-identical
- PR2 commit `95e8579` (logic + rendering) — byte-identical
- PR3 commit `778efdb` (Click wiring + verify + ACs) — byte-identical (Pattern #548)
- `openspec/changes/v1.1-followups/` — untouched
- `fetch_project_list` / `fetch_status_summary` — untouched
- `render_needs_table` / `render_dashboard` — untouched

---

## 11. Out of Scope (explicit, mirror of proposal §Out of Scope + spec §Out of Scope)

- NO new runtime dependencies (`rich` is transitive, preserved)
- NO modifications to PR1 / PR2 / PR3 dashboard commits (Pattern #548)
- NO `extract-build-needs-by-name-helper` implementation (deferred to §7)
- NO `remove-sort-projects-deprecation-fallback` (deferred to §8)
- NO modifications to `workspace/spec.md` §3 / §5 / §7 deferred text (that is the `workspace-dashboard-section-cleanup` change, separate)
- NO new verify checks (8 existing checks from phase-5-dashboard design #492 still cover this change's structure)
- NO `--json` flag on dashboard (Pattern #538)
- NO `stash`-triggering words in any new code
- NO touch of `openspec/changes/v1.1-followups/`

---

## 12. Tech debt (informational, NOT addressed by this change)

3 pre-existing lint errors (OOS):
- `cli.py:683` — `RET504` (unnecessary assignment before return)
- `test_cli_where_cross_project.py:33` — `UP035` (`typing.List` → `list`)
- `test_cli_where_cross_project.py:295` — `W292` (no newline at end of file)

4 pre-existing reindex test failures (OOS, sqlite-vec opt-in not enabled in CI)
2 pre-existing mypy yaml-stub errors (OOS)

All pre-existing — NOT introduced by this change. Documented for next session's hygiene pass.

---

## 13. Migration / Rollout

**No migration required.** This is a bug-fix refactor:

- **API surface change**: 1 new keyword-only parameter (`needs_by_name`). Existing positional callers (`sort_projects(projects, "name")`) UNCHANGED. No public semver bump.
- **Data shape change**: NONE. The envelope shape (`{"name": ..., "reasons": [...]}`) is unchanged; only the consumer reads the shape correctly now.
- **Operator behavior change**: `--sort needs-count` now ACTUALLY orders by reason count (previously silently no-oped). This is the desired bug fix, not a regression.
- **Rollback**: revert the 2 source files + 2 test files. The `_needs_count` helper removal is the only structural change; restoring it is a 4-line revert. (See proposal §Rollback.)

**DeprecationSunset**: see §8 — `remove-sort-projects-deprecation-fallback` in v1.3.0 after all callers migrate.

---

## 14. Wall-time forecast (remaining phases)

| Phase | Estimated wall-time | Reason |
|---|---|---|
| `sdd-tasks` | ~5 min | Mechanical derivation from this locked design (4 file changes → 4-6 tasks grouped by TDD stage) |
| `sdd-apply` | ~15 min | RED → GREEN → REFACTOR per task; ~85 LOC across 4 files; ~5 new tests; 1 fixture rewrite |
| `sdd-verify` | ~5 min | Confirm AC1-AC9 + preservation gates (PR1/PR2/PR3 byte-identical; 8 verify checks pass) |
| `sdd-archive` | ~2 min | Single-PR archive; merge deltas into `specs/workspace-dashboard/spec.md` |
| **Total remaining** | **~30 min** | |

---

## 15. Commit plan (per work-unit-commits skill)

**Single PR, single commit** (change is < 400 LOC).

**Message** (Conventional Commits):

```
fix(dashboard): align sort_projects with real DS1/DS2 data flow

sort_projects reads reasons via project['reasons'] (a legacy field that
does not exist on real DS1 project dicts) -- silently no-oping
--sort needs-count in production. Add keyword-only needs_by_name parameter
so it reads from the real DS2 needs_attention list (keyed by 'name').

Caller workspace_dashboard_cmd builds needs_by_name from
summary['needs_attention']. Backward-compat fallback emits
DeprecationWarning (target removal v1.3.0). Phase 5.2 helper extraction
tracked as extract-build-needs-by-name-helper follow-up.
```

- NO AI attribution (per repo policy)
- Atomic — all 4 file changes in 1 commit
- Mirror as `openspec/changes/sort-projects-align-with-real-ds-data-flow/` already exists

---

## 16. Open questions

None. All 4 ambiguities from the proposal surface are locked here:

1. **§3 — `project` vs `name` key in `needs_attention` entries** — LOCKED to `name` (with evidence chain)
2. **§4 — `sort_projects` signature** — LOCKED to keyword-only `needs_by_name: Mapping[str, list[str]] | None = None`
3. **§5 — DeprecationWarning semantics** — LOCKED (exact message text + stacklevel + trigger condition)
4. **§6 — caller contract** — LOCKED (inline builder at cli.py:3065-3068; defensive `need.get("name", "")`)

Two follow-up changes documented (§7, §8).

Ready for `sdd-tasks`.
