# Exploration: `sort-projects-align-with-real-ds-data-flow`

> **Change**: `sort-projects-align-with-real-ds-data-flow`
> **Phase**: explore (single artifact)
> **Mode**: hybrid (OpenSpec file + Engram mirror)
> **Project**: flow-engineering v1.2.0
> **Origin**: PR3 verify-report #557 §"DESIGN NOTE Carry-Forward" (Pattern #548 + #554)
> **Scope lock**: CODE CHANGE only. NO doc changes (workspace-dashboard-section-cleanup is a separate change per Pattern #555).

---

## 1. Goal

Fix the data flow mismatch in `sort_projects` so that `--sort needs-count` actually orders projects by their real reasons count when run against the real DS1/DS2 data flow (not just the in-test workaround).

The fix MUST land **before Phase 5.2 (TUI/web/interactive)** so the dashboard is internally consistent — TUI/web readers will face the same data flow issue otherwise.

---

## 2. Scope

### 2.1 In scope

- `src/flow_engineering/dashboard.py` — refactor `_needs_count` and/or `sort_projects` to read reasons from the real DS2 envelope (`needs_attention`), not from a non-existent `reasons` field on the project dict.
- `src/flow_engineering/cli.py` — update the `workspace_dashboard_cmd` call site at L3069 to pass the real reasons data.
- `tests/unit/test_dashboard.py` — update `test_sort_by_needs_count_descending` (T5) to exercise the real data flow.
- `tests/unit/test_cli_dashboard.py` — update `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` (T12.3) and the `_make_project` helper so the test does not bake `reasons=[]` into project dicts (the test workaround).

### 2.2 Out of scope (NON-NEGOTIABLE)

- NO doc changes (workspace-dashboard-section-cleanup comes next, separate change per Pattern #555).
- NO modifications to `workspace/spec.md` §3/§5/§7 deferred text.
- NO modifications to PR1/PR2/PR3 dashboard commits (LOCKED per Pattern #548).
- NO touch of `openspec/changes/v1.1-followups/`.
- NO new runtime deps (rich is transitive; preserve per AC11).

---

## 3. Current `sort_projects` Analysis

### 3.1 Function signature

`src/flow_engineering/dashboard.py:259-295`:

```python
def sort_projects(
    projects: list[dict[str, Any]], field: str
) -> list[dict[str, Any]]:
```

Valid fields: `"name"`, `"path"`, `"needs-count"` (set `_VALID_SORT_FIELDS` at L250).

### 3.2 `_needs_count` helper (L253-256)

```python
def _needs_count(project: dict[str, Any]) -> int:
    """Return the needs-attention count for a project (used by sort + render)."""
    reasons = project.get("reasons", [])
    return len(reasons) if isinstance(reasons, list) else 0
```

`sort_projects` dispatches to `_needs_count` via `sorted(projects, key=_needs_count, reverse=True)` at L295.

### 3.3 Data access pattern

`sort_projects` reads the following fields from each `project` dict:

| Field | Where | For |
|---|---|---|
| `name` | `p.get("name", "")` (L291) | `name` sort key |
| `path` | `p.get("path", "")` (L293) | `path` sort key |
| `reasons` | `project.get("reasons", [])` via `_needs_count` (L255) | `needs-count` sort key |

**The bug lives at the third row**: `reasons` does NOT exist on real DS1 project dicts.

### 3.4 Bug description

The real DS1 envelope (`flow projects ls --json`) returns project dicts with fields like `name`, `path`, `has_git`, `dirty`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`, `stack` — **NOT** `reasons`. Reasons are populated in a separate `needs_attention` list inside the DS2 envelope (`flow workspace status`), keyed by project name, with shape:

```python
{"name": "<project>", "path": "<path>", "reasons": ["R1: ...", "R2: ..."]}
```

Constructed at `src/flow_engineering/cli.py:2892-2919` (`_summarize_workspace_status`) — reasons are computed per-project, then attached to a `needs_attention` entry, never to the project dict itself.

**Consequence**: when `sort_projects(projects, "needs-count")` runs against real DS data, `project.get("reasons", [])` returns `[]` for every project → `_needs_count` returns `0` for every project → `sorted(..., reverse=True)` is a no-op (all tied at 0). The `--sort needs-count` flag **silently does nothing** in production. This is exactly the bug documented in PR3 verify-report #557 §"DESIGN NOTE Carry-Forward".

### 3.5 Test workaround

Two tests bake the workaround into fixtures:

**Unit test `tests/unit/test_dashboard.py:458-472` (`test_sort_by_needs_count_descending`)**:

```python
projects = [
    {"name": "clean", "path": "/p/clean", "reasons": []},
    {"name": "noisy", "path": "/p/noisy",
     "reasons": ["R1", "R2", "R3", "R4"]},
    {"name": "medium", "path": "/p/medium",
     "reasons": ["R1", "R2"]},
]
```

Each project dict carries an **inline** `reasons` list that does not exist in real DS1 data. The test passes only because `_needs_count` happens to read from this non-existent field.

**Click test `tests/unit/test_cli_dashboard.py:37-39` (`_make_project` helper)**:

```python
def _make_project(name: str, *, path: str = "/p", reasons: list[str] | None = None) -> dict:
    """Build a minimal project dict matching the DS1/DS2 contract shape."""
    return {"name": name, "path": f"{path}/{name}", "reasons": reasons or []}
```

Same workaround — the helper ALWAYS includes `"reasons": reasons or []` on each project dict. The docstring's claim of "matching the DS1/DS2 contract shape" is misleading: the real DS1 envelope (per `_workspace_status_envelope` at `cli.py:2926-2938`) returns the project dicts directly via `envelope["projects"]` — and those dicts do NOT have `reasons`.

The T12.3 test at L139-143 then sorts using both the inline `reasons` on each project dict AND a parallel `needs_attention` list — the inline `reasons` is what makes the sort work; the `needs_attention` list is only consulted by `render_needs_table` (which correctly indexes by `name`).

### 3.6 Call site

`src/flow_engineering/cli.py:3049-3072` (`workspace_dashboard_cmd`):

```python
projects = fetch_project_list()                                              # L3062
status_envelope = fetch_status_summary()                                    # L3063
archived = fetch_archived_projects()                                         # L3064
needs_attention = status_envelope.get("needs_attention", [])                # L3065

if filter_rules:
    projects, needs_attention = filter_by_rules(projects, needs_attention, list(filter_rules))
projects = sort_projects(projects, sort)                                    # L3069  ← needs needs_attention!
```

At L3069 the caller has BOTH `projects` AND `needs_attention` available but `sort_projects` ignores `needs_attention`. The real reasons data is one import-scope away — the call site has everything it needs to feed the correct data into `sort_projects`.

---

## 4. Fix Options

### Option A — `sort_projects` accepts optional `needs_by_name` parameter (recommended)

**Change to `dashboard.py`**:
- `_needs_count` becomes either (a) inline lambda in `sort_projects` reading from a closure-bound `needs_by_name`, or (b) `_needs_count(project, needs_by_name)` — accept the mapping.
- `sort_projects` signature gains a keyword-only `needs_by_name: Mapping[str, list[str]] | None = None` parameter.
- When `field == "needs-count"`:
  - If `needs_by_name is None`: raise `ValueError` (explicit failure — current silent-no-op is worse than loud failure), OR fall back to project["reasons"] for back-compat with the existing test workaround (warn at module-level deprecation).
  - Else: read `len(needs_by_name.get(project.get("name", ""), []))`.
- Docstring updated to declare the new parameter and the contract.

**Change to `cli.py`**:
- L3069: `projects = sort_projects(projects, sort, needs_by_name={n["name"]: n.get("reasons", []) for n in needs_attention if isinstance(n.get("name"), str)})` — pre-compute the lookup dict at the call site.

**Change to `test_dashboard.py`**:
- Rewrite `test_sort_by_needs_count_descending` to construct the real data shape: project dicts WITHOUT inline `reasons`, and pass a `needs_by_name` dict to `sort_projects`.
- Add `test_sort_by_needs_count_missing_name_uses_zero` (real DS1 may have projects without any needs_attention entry — must sort as 0, not raise).
- Add `test_sort_by_needs_count_without_needs_by_name_raises_or_falls_back` (explicit decision documented in a test).

**Change to `test_cli_dashboard.py`**:
- Update `_make_project` to NOT include `reasons` (remove the field entirely — it does not exist on real DS1 project dicts).
- T12.3 test then exercises the real data flow (reasons live only in `needs_attention`, sort reads via `needs_by_name`).

**LOC estimate**: ~25 src + ~60 tests = **~85 LOC total**.

**Pros**:
- **Smallest LOC** for the actual semantic fix in `dashboard.py` (~15 LOC net change).
- **Cleanest API**: `sort_projects` stays a pure function with explicit data dependencies.
- **Most testable**: can unit-test `sort_projects` with or without `needs_by_name` in isolation, without touching `cli.py`.
- **Best aligns with the project's existing pattern**: `filter_by_rules(projects, needs_attention, rules)` (L189), `render_needs_table(projects, needs_attention, *, no_color)` (L417), and `render_dashboard(projects, summary, archived, needs_attention, *, no_color)` (L579) ALL take both `projects` and `needs_attention` explicitly. `sort_projects` is the lone outlier — Option A makes it consistent.
- **No mutation**: caller never has to inject `reasons` into project dicts — the project dicts stay "pure data" matching the real DS1 envelope.

**Cons**:
- One extra parameter on a public function — but it's keyword-only and defaulted, so backward-compatible at call sites.
- Requires the unit test to be rewritten (test_workaround must be replaced by real-data-flow fixture) — but this is desirable, not a downside.

### Option B — Pre-derive reasons in caller

**Change to `cli.py`**:
- Before L3069: `for p, n in zip(projects, needs_attention): p["reasons"] = n.get("reasons", []) if isinstance(n, dict) else []` — or build a name-keyed lookup and inject per-project.
- `sort_projects` itself: ZERO changes (keeps reading `project.get("reasons", [])`).

**Change to `tests`**:
- `test_cli_dashboard.py::_make_project` no longer needs to include `reasons` (the caller injects them at call time).
- Add `test_workspace_dashboard_cmd_injects_reasons_into_project_dicts` to assert the injection contract.

**LOC estimate**: ~10 src + ~50 tests = **~60 LOC total**.

**Pros**:
- **Smallest absolute LOC** (~60 vs Option A's ~85).
- **Zero changes to `dashboard.py`** (sort_projects untouched).
- Backward-compatible: any other caller of `sort_projects` that already pre-derives keeps working.

**Cons**:
- **Caller complexity**: `workspace_dashboard_cmd` now mutates the input list (or creates a copy — adds ceremony). This is the "slight caller complexity" the user flagged.
- **Implicit contract**: `sort_projects` docstring says nothing about needing `reasons` pre-derived — future callers (TUI/web in Phase 5.2) must rediscover this requirement.
- **Cross-cutting mutation**: every new caller that wants `needs-count` sorting must remember to inject. Easy to forget; easy to introduce the same bug again in Phase 5.2.
- **Coupling inversion**: `sort_projects` knows about a field (`reasons`) that lives on a different data structure in reality — the data shape coupling is now in the caller instead of the callee, but it doesn't go away.

### Option C — Refactor `fetch_status_summary` to return a flat `project_reasons` dict

**Change to `dashboard.py`**:
- Add a new `fetch_project_reasons()` function that wraps `fetch_status_summary` and returns `{name: list[reasons]}`.
- Refactor `sort_projects` to optionally accept the flat dict.

**Change to `cli.py`**:
- L3069: also call `fetch_project_reasons()` and pass the flat dict.

**LOC estimate**: ~30 src + ~70 tests = **~100 LOC total**.

**Pros**:
- Normalizes the data flow at the data layer (single source of truth).

**Cons**:
- **Highest LOC and widest blast radius** (touches `fetch_status_summary` + new function + 2 callers + tests).
- `fetch_status_summary` is PR1 byte-identical preserved; adding a wrapper is fine but the chain count grows.
- The dashboard already has the raw `needs_attention` list via `status_envelope.get("needs_attention", [])` at L3065 — wrapping it again is over-engineering for a 1-caller use case.
- Phase 5.2 (TUI/web) will likely want the full envelope, not a flat reason dict — Option C forces a view-shape choice prematurely.

**Verdict**: REJECTED. Over-engineered for a 1-caller use case. Phase 5.2 may want a different shape; locking in now creates Option B's coupling problem at the data layer instead.

### Option D — Document the workaround as the contract (do not actually fix)

**Change to `dashboard.py`**:
- Update `sort_projects` docstring to say: "Caller is responsible for pre-deriving `reasons` onto each project dict (via `needs_attention`). See `workspace_dashboard_cmd` for the canonical pre-derivation pattern."

**Change to `tests`**: NONE (existing workaround preserved).

**LOC estimate**: ~5 src + 0 tests = **~5 LOC total**.

**Pros**:
- Smallest absolute LOC.
- Zero risk of regression (no code changes).

**Cons**:
- **Does NOT fix the bug** — `--sort needs-count` still silently does nothing in production.
- The user explicitly said: "The user wants this fix BEFORE Phase 5.2 ... to prevent the dashboard from having an internal inconsistency." Documentation is not a fix.
- Hides the smell — anyone reading `sort_projects` thinks it works as designed.

**Verdict**: REJECTED. The user's stated goal is the fix, not the documentation.

---

## 5. Recommended Option: **Option A**

### 5.1 Rationale

| Criterion | Option A | Option B | Option C | Option D |
|---|---|---|---|---|
| LOC (src) | ~25 | ~10 | ~30 | ~5 |
| LOC (tests) | ~60 | ~50 | ~70 | 0 |
| LOC (total) | ~85 | ~60 | ~100 | ~5 |
| Bug actually fixed? | **YES** | **YES** | **YES** | NO |
| `sort_projects` stays pure | **YES** | NO (caller mutates) | **YES** | N/A |
| Consistent with project pattern (filter_by_rules, render_needs_table, render_dashboard all take both data sources explicitly) | **YES** | NO | **YES** | N/A |
| Backward-compatible at the call signature | **YES** (keyword-only + default) | NO (caller must inject) | **YES** | N/A |
| Cross-caller future-proofing (Phase 5.2 TUI/web) | **YES** (explicit signature) | NO (implicit pre-derivation contract) | **YES** | NO |
| Testability in isolation | **YES** (unit-test the function alone) | MEDIUM (must test caller injection too) | **YES** | N/A |
| Risk of regression | LOW | MEDIUM (mutation pattern) | MEDIUM (new data layer function) | NONE |

**Verdict**: Option A is the right choice. It costs ~25 more LOC than Option B but eliminates the cross-caller coupling problem that will resurface in Phase 5.2 (TUI/web). The pattern alignment with `filter_by_rules` / `render_needs_table` / `render_dashboard` is the strongest argument — those functions all take `projects` AND `needs_attention` explicitly; making `sort_projects` follow the same pattern is the natural conclusion.

### 5.2 Why Option B is rejected despite smaller LOC

The 25-LOC savings of Option B come at the cost of pushing the data-flow contract into every caller. Phase 5.2 will add at least one new caller (TUI or web reader); with Option B that caller must remember to pre-derive `reasons` onto project dicts before calling `sort_projects`. Forgetting reintroduces the exact bug we're fixing — silently. With Option A, the signature documents the contract: pass `needs_by_name` (or accept the loud failure).

### 5.3 Sketch (illustrative — design phase will produce final shape)

```python
# dashboard.py
from typing import Mapping

def sort_projects(
    projects: list[dict[str, Any]],
    field: str,
    *,
    needs_by_name: Mapping[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Sort ``projects`` by ``field``.

    For ``field == "needs-count"`` the count is derived from
    ``needs_by_name[project["name"]]`` — the canonical place where reasons
    live in the real DS1/DS2 data flow. When ``needs_by_name`` is ``None``
    the function falls back to ``project.get("reasons", [])`` for
    backward-compat with pre-refactor callers (see PR3 verify-report #557
    §"DESIGN NOTE Carry-Forward" for the historical rationale).
    """
    if field not in _VALID_SORT_FIELDS:
        valid_list = ", ".join(sorted(_VALID_SORT_FIELDS))
        raise ValueError(
            f"Unknown sort field: {field!r}. Valid fields: {valid_list}."
        )

    if field == "name":
        return sorted(projects, key=lambda p: p.get("name", ""))
    if field == "path":
        return sorted(projects, key=lambda p: p.get("path", ""))

    # field == "needs-count"
    if needs_by_name is None:
        # Backward-compat path — pre-refactor callers inject reasons inline.
        return sorted(projects, key=lambda p: _reasons_len(p.get("reasons")), reverse=True)

    def _count(project: dict[str, Any]) -> int:
        name = project.get("name", "")
        if not isinstance(name, str):
            return 0
        reasons = needs_by_name.get(name, [])
        return len(reasons) if isinstance(reasons, list) else 0

    return sorted(projects, key=_count, reverse=True)


def _reasons_len(reasons: Any) -> int:
    """Defensive length of a reasons field (list-like or missing)."""
    return len(reasons) if isinstance(reasons, list) else 0
```

```python
# cli.py (L3069)
needs_by_name = {
    n["name"]: n.get("reasons", [])
    for n in needs_attention
    if isinstance(n, dict) and isinstance(n.get("name"), str)
}
projects = sort_projects(projects, sort, needs_by_name=needs_by_name)
```

The 2-line `needs_by_name` derivation matches the same defensive pattern used by `render_needs_table` at L442-446 — internally consistent.

---

## 6. Open Questions

1. **Should `sort_projects` raise `ValueError` when called with `field="needs-count"` and `needs_by_name=None`?**
   - Pro: forces every caller to be explicit; eliminates silent no-op bug.
   - Con: stricter than the current behavior; any pre-refactor caller fails fast.
   - Recommendation: keep the back-compat fallback for now (one release), add a `DeprecationWarning` when `needs_by_name=None` AND `field == "needs-count"`, then make it required in the next change. Mirrors Pattern #551 ("guards as instruments") + project precedent at `color_code` defensive default.

2. **Should `_needs_count` helper be kept, inlined, or renamed?**
   - It is currently called only by `sort_projects` (per grep at L253-256 — used only at L295).
   - Recommendation: inline it inside `sort_projects` as a closure (Option A sketch does this). Removes the orphan helper; the closure name `_count` is private to the function. If a second caller emerges later, extract it then (YAGNI).

3. **Should the T12.3 click test (`test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending`) also be updated to use the real data flow?**
   - Yes — the test currently bakes the workaround into `_make_project` (L37-39), masking the bug. After Option A lands, `_make_project` should NOT include `reasons`; the test should construct `projects` and `needs_attention` separately and let `sort_projects` read from `needs_by_name` (via the call site wiring). The T5 unit test gets the same treatment.
   - This is the test_workaround removal the user flagged.

4. **Is the dashboard's `--sort` field choice list per design §3 already documented as including `needs-count`?**
   - Yes — PR3 verify-report #557 §"ACs verified" confirmed AC7 lists `name`/`path`/`needs-count` as valid Click choices at `cli.py:3045`. The choice list does NOT change in this fix; only the data flow that backs `needs-count` becomes correct.

5. **Should we add a `tests/unit/test_dashboard.py::test_sort_projects_with_needs_by_name_*` family alongside the existing T5 tests, or rename T5 entirely?**
   - Recommendation: keep T5's name (`test_sort_projects_*`), rewrite the body to use `needs_by_name`, and add 2 new tests (`test_sort_by_needs_count_missing_name_uses_zero`, `test_sort_by_needs_count_without_needs_by_name_falls_back`). T5's count stays at 4; net test count stays ~+3 from PR2.

---

## 7. Tech Debt

### 7.1 Other dashboard functions that might have similar data flow issues

Grep for `project.get(...)` patterns in `dashboard.py` to identify any other field reads that might not exist on real DS1 project dicts:

- L246: `p.get("name") in matched_names` — `name` IS on real DS1 dicts ✓
- L291: `p.get("name", "")` — same ✓
- L293: `p.get("path", "")` — `path` IS on real DS1 dicts ✓
- L255: `project.get("reasons", [])` — **BUG** (this fix)
- L460: `project.get("name", "")` (in `render_needs_table`) — ✓
- L460: `project.get("path", "")` — ✓

**Only `_needs_count` is affected.** No other function reads `reasons` directly from a project dict.

### 7.2 `summary` dict structure documentation

The DS2 envelope structure is documented inline at `cli.py:2880-2923` (`_summarize_workspace_status`) and at `dashboard.py:150-157` (`fetch_status_summary` docstring) — the latter is **minimal** (mentions "totals + projects + needs_attention" without listing the per-entry shape). A follow-up docstring improvement could spell out the `needs_attention` entry shape, but that's a docs change → out of scope for this code-only fix.

### 7.3 Test fixture pattern (inline reasons)

The inline-`reasons` pattern appears in:
- `test_dashboard.py:458-472` (`test_sort_by_needs_count_descending`) — unit test
- `test_cli_dashboard.py:37-39` (`_make_project` helper) — every click test

Both will be updated in this fix. No new fixture helper is needed; the real-data-flow shape is simpler (just `{"name": ..., "path": ...}`).

### 7.4 `filter_by_rules` symmetry

`filter_by_rules` at `dashboard.py:189-247` correctly takes BOTH `projects` and `needs_attention` and indexes by name internally — it does NOT suffer from the same data-flow bug. This change brings `sort_projects` into parity with `filter_by_rules`.

### 7.5 Pre-existing ruff/mypy debt (NOT touched)

3 ruff errors + 2 mypy errors at known locations (per archive-report #557 §8.1) are OOS for this change. This fix does not introduce or touch any of them.

---

## 8. Forecast

| Metric | Estimate |
|---|---|
| Total LOC (src + tests) | ~85 |
| Forecast vs. PR3-style 600 LOC guard | 85 < 600 ✓ (single PR suffices) |
| Chained PR strategy | **single PR** (Option A is < 400 LOC; `ask-always` strategy has the answer from this exploration as "single" since total LOC is well under budget) |
| Files affected | 4 — `src/flow_engineering/dashboard.py` (modify) + `src/flow_engineering/cli.py` (modify, 1 line + 2-line dict comprehension) + `tests/unit/test_dashboard.py` (modify T5 + 2 new tests) + `tests/unit/test_cli_dashboard.py` (modify `_make_project` + T12.3) |
| New runtime deps | 0 |
| Wall-clock (full cycle) | ~65 min (explore 10 [done] + propose 10 + spec 10 + design 8 + tasks 5 + apply 15 + verify 5 + archive 2) |

---

## 9. Risks

| # | Severity | Description | Mitigation |
|---|---|---|---|
| 1 | LOW | `sort_projects` signature gains a parameter — any external caller passing positional args (`sort_projects(projects, "needs-count")`) still works because the new param is keyword-only. | The change uses `*, needs_by_name: ...` (keyword-only). All current callers (1, at `cli.py:3069`) will be updated in the same PR. |
| 2 | LOW | The `_needs_count` helper becomes redundant (inlined as a closure). Removing it is a soft API break if anyone imports it from `flow_engineering.dashboard`. | Grep confirmed it is only used inside `dashboard.py` at L295. Remove it (private helper, no `__all__` entry). |
| 3 | LOW | Test fixtures change (T5 + T12.3 + `_make_project`) — if any test relies on the inline-`reasons` shape for unrelated assertions, those assertions must be updated. | The 3 affected tests are precisely the sort-related ones. Audit confirmed no other test uses `_make_project` for sort assertions. |
| 4 | MEDIUM | Backward-compat fallback (when `needs_by_name=None`) is a latent footgun — callers who forget the parameter still get a silent no-op (just like today). | Add a `DeprecationWarning` in the fallback path; document in the docstring; follow-up change removes the fallback. |
| 5 | LOW | Phase 5.2 (TUI/web) will need to do the same `needs_by_name` derivation at the call site — minor copy-paste risk if multiple callers diverge. | Design phase should extract a helper `build_needs_by_name(needs_attention)` so the derivation is shared. Out of scope for THIS fix but worth noting. |

---

## 10. Verdict

**Recommended option: Option A** — `sort_projects` accepts optional keyword-only `needs_by_name: Mapping[str, list[str]] | None = None`.

**Why**:
1. **Smallest semantic fix in `dashboard.py`** (~15 LOC net change).
2. **Aligns with the project's existing pattern**: `filter_by_rules`, `render_needs_table`, and `render_dashboard` ALL take both `projects` and `needs_attention` (or equivalent) explicitly. `sort_projects` is the lone outlier — Option A makes it consistent.
3. **Future-proofs Phase 5.2** (TUI/web) — explicit signature documents the contract; new callers can't reintroduce the bug by forgetting to pre-derive.
4. **Testable in isolation** — unit tests can exercise the function with or without `needs_by_name` without touching the CLI layer.
5. **No data mutation** — keeps project dicts as "pure data" matching the real DS1 envelope.

**Tradeoff accepted**: ~25 LOC more than Option B for the cross-caller future-proofing and the pattern consistency.

**Single PR forecast**: ~85 LOC total (src + tests) is well under the 400-line PR budget and the 600-line PR3-style guard — no chained PR needed. The user's `ask-always` chained-PR strategy has the answer baked into this exploration: "ask once, answer = single".

---

## 11. Ready for Proposal

**YES** — the orchestrator should launch `sdd-propose` next with these inputs:

- **Change name**: `sort-projects-align-with-real-ds-data-flow`
- **Goal**: align `sort_projects` with the real DS1/DS2 data flow so `--sort needs-count` actually orders by real needs.
- **Approach (locked)**: Option A — `sort_projects` gains keyword-only `needs_by_name: Mapping[str, list[str]] | None = None`.
- **Scope (locked)**: 4 files modified (dashboard.py, cli.py, test_dashboard.py, test_cli_dashboard.py). No new files. No doc changes.
- **Forecast**: ~85 LOC, single PR, ~65 min wall-clock for full cycle.
- **Acceptance criteria** (proposal phase will refine):
  - AC1: `sort_projects(projects, "needs-count", needs_by_name=...)` orders projects by descending `len(needs_by_name[name])`.
  - AC2: `sort_projects(projects, "needs-count")` with `needs_by_name=None` falls back to legacy `project["reasons"]` behavior with a `DeprecationWarning`.
  - AC3: `sort_projects` raises `ValueError` for unknown `field` (existing behavior preserved).
  - AC4: The T12.3 click test exercises the real data flow (no inline `reasons` on project dicts).
  - AC5: The T5 unit test exercises the real data flow (no inline `reasons` on project dicts).
  - AC6: Full suite passes (1490 + 2 skipped baseline preserved).
  - AC7: PR1+PR2+PR3 dashboard commits remain LOCKED (Pattern #548).
  - AC8: Zero new runtime deps.
  - AC9: `workspace/spec.md` §3/§5/§7 unchanged (separate change).

---

## 12. References

- `src/flow_engineering/dashboard.py` — `sort_projects` at L259-295, `_needs_count` at L253-256, `filter_by_rules` at L189-247 (pattern reference)
- `src/flow_engineering/cli.py` — `workspace_dashboard_cmd` at L3040-3072, `_summarize_workspace_status` at L2880-2923 (DS2 envelope shape)
- `tests/unit/test_dashboard.py` — T5 at L458-472 (test workaround)
- `tests/unit/test_cli_dashboard.py` — `_make_project` at L37-39, T12.3 at L125-174 (click test workaround)
- `openspec/changes/archive/2026-06-30-phase-5-dashboard/archive-report.md` — §9.3 "sort_projects Data-Flow Mismatch" carry-forward
- Engram #557 — `sdd/phase-5-dashboard/verify-report-pr3` (DESIGN NOTE origin)
- Engram #550 — `sdd/phase-5-dashboard/apply-progress-pr2` (sort_projects implementation origin)
- Pattern #548 — "Don't touch green commits for aesthetic reasons" (PR1+PR2+PR3 LOCKED)
- Pattern #554 — "Use the process, don't obey blindly" (this fix follows the process, not the original design)
- Pattern #555 — "Solo el primero ahora, no mezclemos los dos" (CODE change only; doc cleanup is separate)

---

*Generated by the sdd-explore executor. This artifact persists to `openspec/changes/sort-projects-align-with-real-ds-data-flow/explore.md` and mirrors to Engram with topic_key `sdd/sort-projects-align-with-real-ds-data-flow/explore`, type `architecture`, project `insyd`, `capture_prompt: false`.*