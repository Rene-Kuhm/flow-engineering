# Tasks: sort-projects-align-with-real-ds-data-flow

## Header

- **Change**: `sort-projects-align-with-real-ds-data-flow`
- **Phase**: tasks (5/8 of SDD cycle)
- **Strict TDD**: ON — every task is RED → GREEN → REFACTOR
- **Inputs**: design #568 (ambiguities LOCKED — `name` key, kw-only `needs_by_name`, DeprecationWarning semantics, caller contract); spec #566 (REQ-DASHBOARD-SORT-DATA-FLOW + REQ-DASHBOARD-FLAGS modified); proposal #564 (Option A, 9 ACs)
- **Output**: this `tasks.md` — 7 mechanical tasks, single PR, ~85 LOC total
- **Delivery strategy** (orchestrator-cached): `single-pr`
- **Artifact store**: `openspec` (write file) + `hybrid` (mirror to Engram with `capture_prompt: false`)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~85 LOC (additions + deletions) |
| `src/flow_engineering/dashboard.py` | ~25 LOC (new signature + closure + `import warnings` + `from collections.abc import Mapping`; net ~+22 after removing `_needs_count` helper) |
| `src/flow_engineering/cli.py` | ~10 LOC (inline `needs_by_name` builder + kwarg pass) |
| `tests/unit/test_dashboard.py` | ~40 LOC (T1+T2+T3 new + rewrite of `test_sort_by_needs_count_descending`) |
| `tests/unit/test_cli_dashboard.py` | ~20 LOC (T4 new + `_make_project` helper drop of `reasons`) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR, single atomic commit |
| Delivery strategy | `single-pr` |
| Chain strategy | N/A — single PR |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Rationale: 85 LOC is well under the 400-line single-PR budget. All 4 file changes land together as one atomic commit per `work-unit-commits` skill ("commit by work unit"; tests stay with the code they verify; one clear purpose: contract fix). No `size:exception` needed.

---

## Task summary

| T# | Title | Action type | Verifies (ACs) |
|----|-------|-------------|----------------|
| T-1 | RED `test_sort_by_needs_count_uses_needs_by_name` → GREEN replace `sort_projects` with kw-only `needs_by_name` signature + closure | RED → GREEN | AC1, AC2, AC3, AC4, AC6 |
| T-2 | RED `test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning` (warning emission test) | RED → GREEN (prod code from T-1) | AC1, AC5 |
| T-3 | RED `test_sort_with_empty_needs_by_name_returns_zero_count` (empty-dict behavior documentation) | RED → GREEN (no prod code change) | AC1 (backward-compat) |
| T-4 | RED `test_caller_passes_needs_by_name_to_sort_projects` (integration) → GREEN update `workspace_dashboard_cmd` to build + pass `needs_by_name` | RED → GREEN | AC7 |
| T-5 | Remove `_needs_count` module-level helper from `dashboard.py` (cleanup after inlining as closure) | REFACTOR | (structural cleanup, no AC delta) |
| T-6 | Update `_make_project` helper in `test_cli_dashboard.py` to NOT include inline `reasons` (real DS1 shape) + adapt T12.3 integration test | REFACTOR | AC7 (caller contract honored end-to-end) |
| T-7 | Rewrite `test_sort_by_needs_count_descending` in `test_dashboard.py` to use real DS1 shape + explicit `needs_by_name=` (anchor for AC4) | RED → GREEN → REFACTOR | AC4 (the test that proves the bug fix) |

---

## Task definitions

### T-1 — Replace `sort_projects` with kw-only `needs_by_name` signature (RED → GREEN)

**Goal**: Add the keyword-only `needs_by_name` parameter to `sort_projects` so it reads reasons from the real DS2 `needs_attention` list (keyed by `name`) instead of from the non-existent inline `reasons` field on each project dict. Inline the `_needs_count` helper as a closure that branches on `needs_by_name is None`. Keep `name` and `path` sorts unchanged.

**RED step**: Write the failing test FIRST. Add to `tests/unit/test_dashboard.py` inside `class TestSortProjects` (after `test_sort_by_path`, before `test_sort_by_invalid_field_raises_ValueError`):

```python
def test_sort_by_needs_count_uses_needs_by_name(self) -> None:
    """sort_projects with explicit needs_by_name reads from real DS2 shape
    (no inline reasons) and orders DESCENDING by len(needs_by_name[name])."""
    projects = [
        {"name": "alpha", "path": "/path/alpha"},
        {"name": "beta",  "path": "/path/beta"},
        {"name": "gamma", "path": "/path/gamma"},
    ]
    needs_by_name = {
        "alpha": ["R1", "R2", "R3"],  # 3 needs
        "beta":  ["R1"],               # 1 need
        "gamma": [],                   # 0 needs
    }
    result = sort_projects(projects, "needs-count", needs_by_name=needs_by_name)
    # Descending: alpha (3) > beta (1) > gamma (0).
    assert [p["name"] for p in result] == ["alpha", "beta", "gamma"]
```

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects::test_sort_by_needs_count_uses_needs_by_name -v`
Expected: **FAIL** — current signature does not accept `needs_by_name=` (TypeError: unexpected keyword argument).

**GREEN step**: In `src/flow_engineering/dashboard.py`:

1. Add module-top imports (preserving existing ordering):
   ```python
   from collections.abc import Mapping
   import warnings
   ```
2. Replace `sort_projects` (currently at L259-295) with the locked design signature + closure. Remove the module-level `_needs_count` helper (currently L253-256) — its logic moves INSIDE `sort_projects` as a closure that branches on `needs_by_name is None`:
   ```python
   def sort_projects(
       projects: list[dict[str, Any]],
       field: str,
       *,
       needs_by_name: Mapping[str, list[str]] | None = None,
   ) -> list[dict[str, Any]]:
       """Return ``projects`` sorted by ``field``.

       For ``field="needs-count"``, the count source is the name-keyed
       ``needs_by_name`` map (real DS2 data flow). When ``needs_by_name``
       is ``None``, falls back to ``len(project.get("reasons", []))``
       with a ``DeprecationWarning`` — backward-compat for stale callers.
       Removal target: v1.3.0 (see follow-up
       ``remove-sort-projects-deprecation-fallback``).
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
       def needs_count(p: dict[str, Any]) -> int:
           if needs_by_name is not None:
               reasons = needs_by_name.get(p.get("name", ""), [])
               return len(reasons) if isinstance(reasons, list) else 0
           warnings.warn(
               "sort_projects: needs_by_name=None is deprecated; pass it derived "
               "from DS2 needs_attention list. Remove the fallback in the next follow-up.",
               DeprecationWarning,
               stacklevel=2,
           )
           reasons = p.get("reasons", [])
           return len(reasons) if isinstance(reasons, list) else 0

       return sorted(projects, key=needs_count, reverse=True)
   ```

3. DELETE the module-level `_needs_count` helper (L253-256). It's now inlined as the `needs_count` closure.

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects -v`
Expected: T1 PASS. Existing `test_sort_by_name_default` + `test_sort_by_path` + `test_sort_by_invalid_field_raises_ValueError` still pass. `test_sort_by_needs_count_descending` still passes (uses inline `reasons` fallback path → emits DeprecationWarning, but the assertion only checks order).

**REFACTOR step**: Run `uv run --frozen ruff check src/flow_engineering/dashboard.py` and `uv run --frozen mypy src/flow_engineering/dashboard.py`. If `Mapping` import is unused anywhere else, leave it (future-proofs the closure return type). No other refactor needed — the closure is the simplest implementation.

**Files affected**: `src/flow_engineering/dashboard.py` (signature, closure, import, helper deletion) + `tests/unit/test_dashboard.py` (new test).

**Pre-requisites**: none (first task).

**Acceptance criteria**: AC1 (signature accepted), AC2 (name sort), AC3 (path sort), AC4 (needs-count with needs_by_name orders correctly), AC6 (ValueError still raised for invalid field).

**Risk notes**:
- LOW — `Mapping` import: ensure `from collections.abc import Mapping` is added at the top, alphabetically ordered if the file uses `isort` (ruff `I` rule).
- LOW — `import warnings`: same import-order discipline.
- LOW — Removing `_needs_count`: confirmed by design §10 only L295 uses it. Run a final grep after applying to be safe: `grep -n "_needs_count" src/`.

---

### T-2 — Verify `DeprecationWarning` fires when `needs_by_name=None` (RED → GREEN, prod code reused from T-1)

**Goal**: Lock the DeprecationWarning contract — when the legacy fallback path is taken, a `DeprecationWarning` is emitted so stale callers surface in tests. This is the AC5 anchor.

**RED step**: Add to `tests/unit/test_dashboard.py` inside `class TestSortProjects`:

```python
def test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning(self) -> None:
    """Backward-compat: needs_by_name=None falls back to project['reasons']
    AND emits DeprecationWarning so stale callers surface in test runs."""
    projects = [
        {"name": "alpha", "path": "/path/alpha", "reasons": ["R1", "R2"]},
        {"name": "beta",  "path": "/path/beta",  "reasons": []},
    ]
    with pytest.warns(DeprecationWarning, match="needs_by_name=None is deprecated"):
        result = sort_projects(projects, "needs-count")  # no needs_by_name
    # Sort descending by len(reasons): alpha (2) > beta (0).
    assert [p["name"] for p in result] == ["alpha", "beta"]
```

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects::test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning -v`
Expected: **FAIL** — current code (post T-1 GREEN) emits the warning, BUT this test ASSUMES T-1's GREEN step is in place. If T-1 has not been applied yet, FAIL is "TypeError: unexpected keyword argument `needs_by_name`" from T-1's RED assertion. If T-1 is applied but warning not emitted, FAIL is "DID NOT WARN". Either way RED is achieved.

**GREEN step**: No new production code. The `warnings.warn(...)` block is already in T-1's GREEN closure. Re-run the test — expect PASS.

If `pyproject.toml` has `filterwarnings = ["error::DeprecationWarning,..."]` for `tests/`, the warning will be RAISED as an error and the test will FAIL unexpectedly. Mitigation: T-1's GREEN step should NOT change `pyproject.toml`. If the existing config already escalates `DeprecationWarning` to error, scope it per-test using `pytest.warns(...)` context manager — pytest's `pytest.warns` automatically suppresses the escalation inside the `with` block. Verify this in the apply phase.

**REFACTOR step**: None — the warning message is already verbatim from design §5.

**Files affected**: `tests/unit/test_dashboard.py` (test only).

**Pre-requisites**: T-1 (closure with `warnings.warn(...)` must exist).

**Acceptance criteria**: AC1 (backward-compat path), AC5 (DeprecationWarning emitted on fallback path).

**Risk notes**:
- MEDIUM — `pyproject.toml` `filterwarnings` config could escalate the warning to error. Apply-phase gate: verify `pyproject.toml` does NOT contain `error::DeprecationWarning` for `tests/` paths before declaring GREEN. If it does, document the per-test `pytest.warns` workaround.

---

### T-3 — Document empty-dict `needs_by_name` behavior (RED → GREEN, no prod change)

**Goal**: Lock the empty-dict edge case — `needs_by_name={}` is a valid signal that the caller has no needs info at all; all projects must sort with count 0, and Python's stable `sorted` preserves the original input order.

**RED step**: Add to `tests/unit/test_dashboard.py` inside `class TestSortProjects`:

```python
def test_sort_with_empty_needs_by_name_returns_zero_count(self) -> None:
    """Empty needs_by_name dict (not None) returns 0 for all projects;
    Python's sorted() is stable so input order is preserved."""
    projects = [
        {"name": "alpha", "path": "/path/alpha"},
        {"name": "beta",  "path": "/path/beta"},
        {"name": "gamma", "path": "/path/gamma"},
    ]
    result = sort_projects(projects, "needs-count", needs_by_name={})
    # All counts 0; stable sort preserves input order.
    assert [p["name"] for p in result] == ["alpha", "beta", "gamma"]
```

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects::test_sort_with_empty_needs_by_name_returns_zero_count -v`
Expected: **PASS** on first run (T-1's closure already returns 0 for all when `needs_by_name={}` and `needs_by_name is not None`). This is intentional — the test DOCUMENTS the behavior so a future regression (e.g., someone adding a `KeyError` for missing keys) will be caught.

If for any reason it fails (e.g., a defensive guard returns `None` somewhere), add minimal production code to fix it. The TDD discipline here is: write the assertion, watch it pass, lock the behavior.

**GREEN step**: No production change. Run test → PASS.

**REFACTOR step**: None.

**Files affected**: `tests/unit/test_dashboard.py` (test only).

**Pre-requisites**: T-1 (closure must accept `needs_by_name={}` without erroring).

**Acceptance criteria**: AC1 (backward-compat — empty dict is a valid input, not None).

**Risk notes**:
- LOW — Stable-sort behavior is a Python language contract, not a project-specific invariant. If this test ever fails, it's a Python upgrade regression, not a code bug.

---

### T-4 — Update `workspace_dashboard_cmd` to build + pass `needs_by_name` (RED → GREEN, integration)

**Goal**: Wire the locked caller contract — `workspace_dashboard_cmd` derives `needs_by_name` from `status_envelope["needs_attention"]` (keyed by `need["name"]`) and passes it to `sort_projects` as a keyword argument. This is the AC7 anchor and proves the bug fix end-to-end.

**RED step**: Add to `tests/unit/test_cli_dashboard.py` at the end of the file (after `test_workspace_dashboard_cmd_with_no_color_suppresses_ansi`):

```python
def test_workspace_dashboard_cmd_passes_needs_by_name_to_sort_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller builds needs_by_name from summary['needs_attention'] and passes
    it as keyword to sort_projects. Real DS1 envelope: project dicts do NOT
    carry inline 'reasons' — only needs_attention entries do."""
    captured: dict = {}

    def fake_sort(
        projects: list[dict], field: str, *, needs_by_name=None
    ) -> list[dict]:
        captured["field"] = field
        captured["needs_by_name"] = needs_by_name
        return projects  # identity; we only assert the call shape

    # Real DS1 envelope shape — no 'reasons' key on project dicts.
    projects = [
        {"name": "alpha", "path": "/path/alpha", "has_git": True,
         "has_openspec": False, "has_tests": False, "has_graphify": False,
         "last_status_check": ""},
        {"name": "beta", "path": "/path/beta", "has_git": True,
         "has_openspec": True, "has_tests": True, "has_graphify": False,
         "last_status_check": ""},
    ]
    # Real DS2 envelope shape — needs_attention entries have name + reasons.
    needs_attention = [
        {"name": "alpha", "path": "/path/alpha",
         "reasons": ["R1: uncommitted work", "R2: not a git repository"]},
        {"name": "beta", "path": "/path/beta", "reasons": []},
    ]
    summary = {
        "totals": {"projects": 2, "needs_attention": 1, "dirty": 1,
                   "no_git": 1, "no_tests": 0},
        "needs_attention": needs_attention,
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])
    monkeypatch.setattr(dashboard_mod, "sort_projects", fake_sort)

    result = runner.invoke(main, ["workspace", "dashboard", "--sort", "needs-count"])

    assert result.exit_code == 0, result.output
    assert captured["field"] == "needs-count"
    assert captured["needs_by_name"] == {"alpha": needs_attention[0]["reasons"]}
    # Critical: the call uses the 'name' key, NOT 'project'.
    assert "beta" not in captured["needs_by_name"]  # beta has empty reasons → excluded by guard
```

Invoke: `uv run --frozen pytest tests/unit/test_cli_dashboard.py::test_workspace_dashboard_cmd_passes_needs_by_name_to_sort_projects -v`
Expected: **FAIL** — current `workspace_dashboard_cmd` calls `sort_projects(projects, sort)` with no kwargs; the `fake_sort` will not receive `needs_by_name`. The assertion `captured["needs_by_name"] == {...}` will fail with `None != {...}`.

**GREEN step**: In `src/flow_engineering/cli.py` at L3065-3069, replace the block between `needs_attention = status_envelope.get(...)` and `projects = sort_projects(...)`:

```python
    needs_attention = status_envelope.get("needs_attention", [])

    # Build needs_by_name from DS2 needs_attention list (keyed by 'name' —
    # the canonical key resolved in design §3). Empty-name entries are
    # dropped to avoid colliding with the closure's fallback path. Helper
    # extraction deferred to follow-up 'extract-build-needs-by-name-helper'.
    needs_by_name: dict[str, list[str]] = {}
    for need in needs_attention:
        name = need.get("name", "")
        reasons = need.get("reasons", [])
        if name and isinstance(reasons, list):
            needs_by_name[name] = reasons

    if filter_rules:
        projects, needs_attention = filter_by_rules(projects, needs_attention, list(filter_rules))
    projects = sort_projects(projects, sort, needs_by_name=needs_by_name)
```

Critical: use `need.get("name", "")` — NOT `need.get("project") or need.get("name", "")` (no defensive magic, per user explicit).

Invoke: `uv run --frozen pytest tests/unit/test_cli_dashboard.py -v`
Expected: T4 PASS. Existing `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` STILL passes IF and only if T-6 has been applied (the existing test uses inline `reasons` on `_make_project`, which after T-6 will be dropped). Otherwise it still passes via the DeprecationWarning fallback path. Order of T-4 vs T-6: apply T-6 first to avoid transient noise.

**REFACTOR step**: None — the 4-line builder is intentionally inline (per design §6; helper extraction deferred to `extract-build-needs-by-name-helper`).

**Files affected**: `src/flow_engineering/cli.py` (4-line builder + kwarg) + `tests/unit/test_cli_dashboard.py` (new integration test).

**Pre-requisites**: T-1 (signature must accept `needs_by_name=`); T-6 (`_make_project` should already drop `reasons` to avoid transient test pollution, but T-6 only affects T12.3, not T4).

**Acceptance criteria**: AC7 (caller builds + passes `needs_by_name` correctly). Implicit: AC8 (no inline `reasons` in caller-side computation).

**Risk notes**:
- MEDIUM — `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` (existing T12.3) uses `_make_project("zeta", reasons=[...])`. After T-6 drops `reasons` from `_make_project`, T12.3 will need to pass `needs_by_name` separately via `_make_needs`. **Apply T-6 BEFORE T-4's GREEN step** to avoid transient failures (or accept that T12.3 still passes via the DeprecationWarning fallback during T-4).
- LOW — Mock data shape: the fake `needs_by_name` assertion uses `needs_attention[0]["reasons"]` rather than re-listing strings — keeps the test robust to internal reason-text tweaks.

---

### T-5 — Remove `_needs_count` module-level helper from `dashboard.py` (REFACTOR)

**Goal**: After T-1 inlines the helper as a closure inside `sort_projects`, the module-level `_needs_count` function is dead code. Delete it.

**RED step**: Confirm `_needs_count` is no longer used anywhere:

```
grep -rn "_needs_count" src/ tests/
```

Expected: only the definition at `src/flow_engineering/dashboard.py:253-256` remains. No call sites.

**GREEN step**: Delete the 4-line helper at L253-256 in `src/flow_engineering/dashboard.py`:

```python
def _needs_count(project: dict[str, Any]) -> int:
    """Return the needs-attention count for a project (used by sort + render)."""
    reasons = project.get("reasons", [])
    return len(reasons) if isinstance(reasons, list) else 0
```

Verify: `grep -n "_needs_count" src/flow_engineering/dashboard.py` returns nothing.

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py -v`
Expected: all `TestSortProjects` tests still pass.

**REFACTOR step**: None — the helper's logic was already inlined in T-1's GREEN.

**Files affected**: `src/flow_engineering/dashboard.py` (4-line deletion).

**Pre-requisites**: T-1 (closure must exist before helper can be safely deleted).

**Acceptance criteria**: structural cleanup, no AC delta. The follow-up `remove-sort-projects-deprecation-fallback` will further tighten the closure signature.

**Risk notes**:
- LOW — Verified by design §10: only L295 (now the closure site) used `_needs_count`. The grep audit at RED step is the safety net.

---

### T-6 — Drop `reasons` from `_make_project` helper (REFACTOR)

**Goal**: Align the test fixture with real DS1 envelope shape — project dicts do NOT carry inline `reasons`. Update `_make_project` in `tests/unit/test_cli_dashboard.py` so all existing tests start using realistic data; adapt `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` (T12.3) to pass reasons via `_make_needs` → `_needs_by_name` builder in the caller.

**RED step**: Modify `_make_project` at L37-39:

```python
def _make_project(name: str, *, path: str = "/p") -> dict:
    """Build a minimal project dict matching the REAL DS1 envelope shape.

    No 'reasons' key — reasons live on needs_attention entries only.
    """
    return {"name": name, "path": f"{path}/{name}"}
```

Run the full `tests/unit/test_cli_dashboard.py` suite. Expected: `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` FAILS because:
1. `_make_project("zeta", reasons=[...])` no longer accepts `reasons` kwarg → TypeError on construction.
2. Even after dropping `reasons=[...]` from `_make_project` calls, the projects dicts have no `reasons`, so `sort_projects` reads them via `needs_by_name` (which the caller doesn't pass yet — T-4 hasn't landed).

**GREEN step**: Adapt `test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending` (L125-174) so the `projects` list no longer passes `reasons` to `_make_project`, AND the `needs_attention` list continues to use `_make_needs(name, [...])`. The test then relies on T-4's caller contract — but T-4 has not landed yet, so this test will FAIL after the `_make_project` change until T-4 applies.

**Strategy**: Apply T-4 BEFORE running this test green. The recommended task ORDER in apply is T-1 → T-5 → T-2 → T-3 → T-6 → T-4 → T-7. After T-4 lands, T-6's adapted T12.3 will pass.

Alternatively, if T-4 is applied immediately after T-6, the failure window is transient and acceptable. Document this ordering dependency in the apply phase.

Invoke after T-4: `uv run --frozen pytest tests/unit/test_cli_dashboard.py -v`
Expected: all tests pass.

**REFACTOR step**: Verify `_make_needs` (L42-44) is unchanged — it already uses `{"name": name, "reasons": reasons}`, matching design §3 LOCKED key. No change.

**Files affected**: `tests/unit/test_cli_dashboard.py` (`_make_project` signature change + T12.3 fixture adaptation).

**Pre-requisites**: T-1 (signature), T-4 (caller passes `needs_by_name`).

**Acceptance criteria**: AC7 (caller contract honored end-to-end via fixture). Aligns with design §11: "Test fixture shape change breaks unrelated tests — LOW — 3 affected tests audited".

**Risk notes**:
- LOW — Only `_make_project` callers are within this file. External callers don't exist (helper is `_*` private).
- MEDIUM — Apply-order dependency on T-4: if T-6 lands alone, T12.3 fails. Apply T-4 in the same commit as T-6, OR apply T-6 before T-4 and accept transient T12.3 failure as the test signals the contract mismatch.

---

### T-7 — Rewrite `test_sort_by_needs_count_descending` to use real DS1 shape (RED → GREEN → REFACTOR)

**Goal**: The existing `test_sort_by_needs_count_descending` (at `test_dashboard.py:458-472`) currently uses inline `reasons` on each project dict — the legacy shape that triggered the bug. Rewrite it to use real DS1 shape (no `reasons`) + explicit `needs_by_name` — this becomes the anchor that proves AC4 is satisfied.

**RED step**: Read current test at `test_dashboard.py:458-472`. Identify that the projects list has `"reasons": [...]` inline, and that `sort_projects` is called WITHOUT `needs_by_name`. After T-1 lands, this test STILL PASSES via the DeprecationWarning fallback path. To prove the bug fix, the test must be rewritten.

The "RED" here is conceptual: the test is currently an INACCURATE witness of the contract (it doesn't fail when `needs_by_name` is broken). Rewrite it so that:
- Without `needs_by_name=...`, the test FAILS (wrong order — all counts 0 from empty defaults).
- With `needs_by_name=...`, the test PASSES (correct order).

**GREEN step**: Replace `test_sort_by_needs_count_descending` (L458-472) with:

```python
def test_sort_by_needs_count_descending(self) -> None:
    """``--sort needs-count`` orders by needs-count DESCENDING (noisiest
    first). Uses REAL DS1 envelope shape (no inline 'reasons') + explicit
    ``needs_by_name`` derived from the DS2 needs_attention list — this
    mirrors production data flow and proves the bug fix."""
    projects = [
        {"name": "clean",  "path": "/p/clean"},
        {"name": "noisy",  "path": "/p/noisy"},
        {"name": "medium", "path": "/p/medium"},
    ]
    needs_by_name = {
        "clean":  [],
        "noisy":  ["R1", "R2", "R3", "R4"],
        "medium": ["R1", "R2"],
    }
    result = sort_projects(projects, "needs-count", needs_by_name=needs_by_name)
    assert [p["name"] for p in result] == ["noisy", "medium", "clean"]
```

Invoke: `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects::test_sort_by_needs_count_descending -v`
Expected: **PASS** (post T-1). Before T-1, **FAIL** with TypeError (signature mismatch).

**REFACTOR step**: Add a brief docstring note in the test explaining why the rewrite matters — it locks the contract that "reasons must come from DS2, not inline". This is the documentation hook that future readers will see.

**Files affected**: `tests/unit/test_dashboard.py` (one test rewritten).

**Pre-requisites**: T-1 (closure must accept `needs_by_name=`).

**Acceptance criteria**: AC4 (the test that proves the bug fix is real, not just a behavior preservation).

**Risk notes**:
- LOW — This test is the SINGLE anchor for AC4. After T-7, design §9 row "T5" (the design-doc test T5) is replaced by this rewrite + T-1's new test. Both T1 and T7 prove AC4 from different angles: T1 uses `name` as the canonical key; T7 mirrors the production data flow with a realistic 3-project fixture.

---

## Per-task dependency graph

```
                ┌─────────────────────────────┐
                │ T-1 sort_projects signature │  (foundation: closure + kw-only param)
                │ + closure + DeprecationWarn │
                └──────────────┬──────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐         ┌──────────────┐
│ T-2 Deprec.  │       │ T-3 Empty    │         │ T-5 Remove   │
│ Warning test │       │ dict doc     │         │ _needs_count │
│ (test only)  │       │ (test only)  │         │ (cleanup)    │
└──────────────┘       └──────────────┘         └──────────────┘

                ┌─────────────────────────────┐
                │ T-4 caller integration       │  (depends on T-1; pairs with T-6)
                │ workspace_dashboard_cmd      │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │ T-6 _make_project helper     │  (depends on T-4 for green)
                │ drops inline reasons         │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │ T-7 rewrite existing sort    │  (depends on T-1)
                │ test to real DS1 shape       │
                └─────────────────────────────┘
```

Apply order recommendation: **T-1 → T-5 → T-2 → T-3 → T-4 → T-6 → T-7**

| Task | Depends on | Can run in parallel with |
|------|-----------|--------------------------|
| T-1  | none      | — (foundation) |
| T-5  | T-1       | T-2, T-3 |
| T-2  | T-1       | T-3, T-5 |
| T-3  | T-1       | T-2, T-5 |
| T-4  | T-1       | T-6 (but T-6 needs T-4 for green) |
| T-6  | T-1, T-4  | — (must follow T-4) |
| T-7  | T-1       | T-2, T-3, T-4, T-5, T-6 |

---

## Forecast (LOC totals)

| File | LOC delta | Notes |
|------|-----------|-------|
| `src/flow_engineering/dashboard.py` | +22 | New imports (`Mapping`, `warnings`); new closure; deleted `_needs_count` (-4) |
| `src/flow_engineering/cli.py` | +8 | 4-line builder + kwarg |
| `tests/unit/test_dashboard.py` | +40 | T1 + T2 + T3 new (~30 LOC); T7 rewrite (~+10 over existing) |
| `tests/unit/test_cli_dashboard.py` | +20 | T4 new (~30 LOC); `_make_project` shrink (-2); T12.3 fixture tweak (~-8 net) |
| **Total** | **~85 LOC** | Well under 400-line single-PR budget |

---

## Suggested task ordering for chained PRs

N/A — single PR. The work-unit-commits skill groups all 4 file changes into one atomic commit per the design §15 plan.

---

## Out-of-scope task reminders

The following are NOT tasks in this change (do not introduce):

- ❌ NO tasks for code modification outside the 4 files (`dashboard.py`, `cli.py`, `test_dashboard.py`, `test_cli_dashboard.py`).
- ❌ NO new verify checks (8 existing from phase-5-dashboard design #492 cover this change).
- ❌ NO modifications to `openspec/changes/v1.1-followups/`.
- ❌ NO `extract-build-needs-by-name-helper` implementation (follow-up #1, documented in design §7).
- ❌ NO `remove-sort-projects-deprecation-fallback` implementation (follow-up #2, target v1.3.0, documented in design §8).
- ❌ NO `workspace-dashboard-section-cleanup` work (separate change).
- ❌ NO modifications to PR1/PR2/PR3 dashboard commits (Pattern #548 — locked).
- ❌ NO `--json` flag on dashboard (Pattern #538).
- ❌ NO `stash`-triggering words in any new code.
- ❌ NO new runtime dependencies.
- ❌ NO drift-detection invocation (this change doesn't move code locations or rename identifiers).

---

## Commit plan (per work-unit-commits skill)

**Single PR, single commit** (atomic; ~85 LOC; well under 400-line budget).

**Message** (Conventional Commits, no AI attribution):

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

Atomic — all 4 file changes in 1 commit. Tests stay with the code they verify.

---

## Pre-existing failures (out-of-scope reminder, NOT introduced by this change)

| Issue | Source | Status |
|-------|--------|--------|
| `RET504` unnecessary assignment before return | `cli.py:683` | Pre-existing |
| `UP035` `typing.List` → `list` | `test_cli_where_cross_project.py:33` | Pre-existing |
| `W292` no newline at end of file | `test_cli_where_cross_project.py:295` | Pre-existing |
| 4 reindex test failures | sqlite-vec opt-in not enabled in CI | Pre-existing |
| 2 mypy yaml-stub errors | yaml-stub package | Pre-existing |

All pre-existing. Apply phase MUST NOT regress the baseline.

---

## Acceptance criteria → REQ + task mapping

| AC | Description | Spec REQ | Verifying task(s) |
|----|-------------|----------|-------------------|
| AC1 | `sort_projects(projects, field, *, needs_by_name=...)` signature accepted; backward-compat | REQ-DASHBOARD-SORT-DATA-FLOW (general) | T-1, T-2, T-3 |
| AC2 | `field="name"` → sort ascending by `p.get("name", "")` | (unchanged) | T-1 (existing test still passes) |
| AC3 | `field="path"` → sort ascending by `p.get("path", "")` | (unchanged) | T-1 (existing test still passes) |
| AC4 | `field="needs-count"` + `needs_by_name` → sort descending by `len(needs_by_name.get(name, []))` | REQ-DASHBOARD-SORT-DATA-FLOW scenario 1 | T-1 (T1 new test), T-7 (anchor rewrite) |
| AC5 | `needs_by_name=None` + `needs-count` → fallback + `DeprecationWarning` | REQ-DASHBOARD-SORT-DATA-FLOW scenario 2 | T-2 |
| AC6 | invalid `field` → `ValueError("Unsupported sort field: ...")` | (unchanged) | T-1 (existing test still passes) |
| AC7 | `workspace_dashboard_cmd` builds + passes `needs_by_name` | REQ-DASHBOARD-SORT-DATA-FLOW scenario 4 | T-4 (integration), T-6 (fixture alignment) |
| AC8 | PR1/PR2/PR3 byte-identical guard preserved | (carry-forward from PR3) | verify phase |
| AC9 | Full suite 1547 + 30 + 4 still passing + 2-3 new tests | (carry-forward from PR3) | verify phase |

---

## Risk summary

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| 1 | `_needs_count` removal breaks other call sites | LOW | grep audit confirms only L295 (now closure site) used it; T-5 RED step re-verifies |
| 2 | `DeprecationWarning` missed by callers | LOW | Single internal caller updated in T-4; follow-up `remove-sort-projects-deprecation-fallback` targets v1.3.0 |
| 3 | Test fixture shape change breaks unrelated tests | LOW | 3 affected tests audited (T12.3 in T-6; T5 in T-7); no cross-dependencies |
| 4 | `pyproject.toml` `filterwarnings` escalates `DeprecationWarning` to error | MEDIUM | T-2 risk note: verify config in apply phase; use `pytest.warns` context to suppress |
| 5 | `name` vs `project` ambiguity reintroduced by future code | LOW (this PR) / MEDIUM (future) | Design §3 locks bilateral contract; PR review checklist includes "any new code touching `needs_attention` MUST read `name`" |
| 6 | T-6 ordering dependency on T-4 | LOW | Apply T-4 immediately after T-6 to avoid transient T12.3 failure; documented in T-6 risk note |

---

## Carry-forward to verify phase

The verify sub-agent MUST confirm:
- AC1–AC7 (functional acceptance from proposal)
- AC8 byte-identical guard: PR1 (`6651add`), PR2 (`95e8579`), PR3 (`778efdb`) commits are byte-identical after apply (Pattern #548)
- AC9 full suite: 1547 main + 30 dashboard + 4 CLI dashboard tests pass + new T1+T2+T3+T4 (3 + 1 integration = 4 new tests, NOT 2-3 as estimated — adjust counts)
- Pre-existing failures (3 lint + 4 reindex + 2 mypy) NOT regressed
- No `stash`-triggering words in any new code
- `openspec/changes/v1.1-followups/` untouched

---

## Ready for `sdd-apply`

This tasks artifact locks the 7 mechanical steps. The apply sub-agent will execute them in the order documented above, following strict RED → GREEN → REFACTOR discipline per task.
