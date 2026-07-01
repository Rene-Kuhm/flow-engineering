# Proposal: sort-projects-align-with-real-ds-data-flow

## Intent

Fix the data flow mismatch in `sort_projects` so `--sort needs-count` actually orders projects by their real DS1/DS2 reasons count. Currently `_needs_count` reads `project.get("reasons", [])` — a field that does NOT exist on real DS1 project dicts; reasons live in the DS2 `needs_attention` list keyed by project name. The sort silently no-ops in production (all counts = 0). **Foundation fix before Phase 5.2 (TUI/web).**

> "Si la base ordena mal, cualquier UI encima miente más lindo."

## Scope

### In Scope
- `src/flow_engineering/dashboard.py` — add `needs_by_name` keyword-only param to `sort_projects`; inline `_needs_count` as closure; add `DeprecationWarning` fallback
- `src/flow_engineering/cli.py` — build `needs_by_name` from `summary["needs_attention"]` at `workspace_dashboard_cmd` L3069 and pass to `sort_projects`
- `tests/unit/test_dashboard.py` — rewrite `test_sort_by_needs_count_descending` (T5) to use real DS1 data shape + 2 new tests
- `tests/unit/test_cli_dashboard.py` — update `_make_project` helper (remove inline `reasons`) + update T12.3 integration test
- Strict TDD RED → GREEN → REFACTOR cycle
- Backward-compat: `DeprecationWarning` when `needs_by_name=None` and `reasons` fallback fires

### Out of Scope
- NO new runtime deps (rich is transitive, preserve)
- NO `extract-build-needs-by-name-helper` change (deferred to Phase 5.2 prep as follow-up `extract-build-needs-by-name-helper`)
- NO modifications to PR1 commit `6651add` / PR2 commit `95e8579` / PR3 commit `778efdb`
- NO touch of `openspec/changes/v1.1-followups/`
- NO modifications to Phase 4 mutation gates or existing CLI commands
- NO modifications to `fetch_project_list` / `fetch_status_summary` (data layer locked from PR1)

## Approach

**Option A locked** (explore #562, 4 options surfaced, user explicit):
`sort_projects` gains keyword-only `needs_by_name: Mapping[str, list[str]] | None = None` parameter.

**Why Option A over B/C/D:**
- **A vs B**: B pushes the data-flow contract to every caller; Phase 5.2 (TUI/web) faces the same coupling risk. A exposes the dependency at the signature — self-documenting.
- **A vs C**: C is over-engineered for 1 caller; refactors PR1's data layer for marginal benefit.
- **A vs D**: D doesn't fix the bug; user explicitly wants the fix.
- **Architecture principle**: "fix the foundation before the UI" (Pattern #555). `sort_projects` is the lone outlier — `filter_by_rules`, `render_needs_table`, and `render_dashboard` ALL take `projects` AND `needs_attention` (or equivalent) explicitly.

### New signature

```python
from collections.abc import Mapping
from typing import Any
import warnings

def sort_projects(
    projects: list[dict[str, Any]],
    field: str,
    *,
    needs_by_name: Mapping[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Sort projects by field.

    For ``field="needs-count"``, the count source depends on ``needs_by_name``:
    - If provided: ``len(needs_by_name.get(project["name"], []))`` (real DS2 data flow)
    - If None: falls back to ``len(project.get("reasons", []))`` with a
      ``DeprecationWarning`` (backward-compat for pre-refactor callers)

    Args:
        projects: DS1 envelope shape (name, path, has_git, has_openspec,
            has_tests, has_graphify, last_status_check — NO ``reasons`` field).
        field: Sort key: "name", "path", or "needs-count".
        needs_by_name: Optional name-keyed reasons map derived from DS2
            ``needs_attention`` list. Required for accurate "needs-count" sort.

    Returns:
        New sorted list (input not mutated).

    Raises:
        ValueError: ``field`` not in {"name", "path", "needs-count"}.
    """
    if field not in _VALID_SORT_FIELDS:
        valid_list = ", ".join(sorted(_VALID_SORT_FIELDS))
        raise ValueError(f"Unsupported sort field: {field!r}. Valid: {valid_list}.")

    if field == "name":
        return sorted(projects, key=lambda p: p.get("name", ""))
    if field == "path":
        return sorted(projects, key=lambda p: p.get("path", ""))

    # field == "needs-count"
    def needs_count(p: dict[str, Any]) -> int:
        name = p.get("name", "")
        if needs_by_name is not None:
            reasons = needs_by_name.get(name, [])
            return len(reasons) if isinstance(reasons, list) else 0
        # Deprecated fallback path
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

### Caller update (`workspace_dashboard_cmd` in cli.py L3069)

```python
# Build needs_by_name from DS2 needs_attention (keyed by project name)
# Each entry: {"name": "...", "reasons": ["R1: ...", ...]}
needs_attention = status_envelope.get("needs_attention", [])
needs_by_name: dict[str, list[str]] = {}
for need in needs_attention:
    project_name = need.get("name", "")
    reasons = need.get("reasons", [])
    if project_name and isinstance(reasons, list):
        needs_by_name[project_name] = reasons

if filter_rules:
    projects, needs_attention = filter_by_rules(projects, needs_attention, list(filter_rules))
projects = sort_projects(projects, sort, needs_by_name=needs_by_name)
```

## Capabilities

### Modified Capabilities
- `workspace-dashboard` (from `openspec/specs/workspace/spec.md`): `sort_projects` internal data flow corrected to read from real DS2 `needs_attention`. No spec-level behavior change — the `--sort needs-count` flag still orders descending; only the count source is corrected.

### New Capabilities
- None (this is a bug-fix refactor; no new capability surface).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/dashboard.py` | Modified | `sort_projects` gains `needs_by_name` kw-only param; `_needs_count` inlined as closure; `DeprecationWarning` on fallback |
| `src/flow_engineering/cli.py` | Modified | `workspace_dashboard_cmd` builds `needs_by_name` from `summary["needs_attention"]` and passes to `sort_projects` |
| `tests/unit/test_dashboard.py` | Modified | T5 rewritten + 2 new tests; real DS1 data shape, no inline `reasons` |
| `tests/unit/test_cli_dashboard.py` | Modified | `_make_project` helper drops `reasons`; T12.3 updated for real data flow |

## 9 Acceptance Criteria

- **AC1**: `sort_projects(projects, "needs-count", *, needs_by_name=...)` signature accepted; backward-compatible (existing positional callers unchanged)
- **AC2**: When `field="name"`, sort ascending by `p.get("name", "")`
- **AC3**: When `field="path"`, sort ascending by `p.get("path", "")`
- **AC4**: When `field="needs-count"` and `needs_by_name` is provided, sort descending by `len(needs_by_name.get(name, []))`
- **AC5**: When `field="needs-count"` and `needs_by_name` is None, fall back to `len(p.get("reasons", []))` AND emit `DeprecationWarning`
- **AC6**: When `field` is invalid, raise `ValueError("Unsupported sort field: ...")`
- **AC7**: `workspace_dashboard_cmd` builds `needs_by_name` from `summary["needs_attention"]` and passes to `sort_projects` (no more inline `reasons` in caller)
- **AC8**: AC9 byte-identical guard preserved — `flow projects ls --json` and `flow workspace status --json` code paths unchanged
- **AC9**: Full suite 1547 tests (1513 main + 30 dashboard + 4 CLI dashboard) still passing; plus 2-3 new sort tests

## Tests to Add (TDD RED → GREEN → REFACTOR)

1. `test_sort_by_needs_count_uses_needs_by_name` — real DS1 data shape, `needs_by_name` passed explicitly; asserts correct descending order
2. `test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning` — inline `reasons` on projects, `needs_by_name=None`; asserts `DeprecationWarning` fires
3. `test_sort_with_empty_needs_by_name_returns_zero_count` — `needs_by_name={}` (empty dict); projects with no needs sort as 0
4. `test_caller_passes_needs_by_name_to_sort_projects` — integration test: `workspace_dashboard_cmd` with mock DS1+DS2 data; verify `sort_projects` received `needs_by_name` kwarg
5. `test_make_project_helper_no_longer_includes_reasons` — `_make_project` returns dict WITHOUT `reasons` key (real DS1 shape)

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `_needs_count` removal breaks other call sites | LOW | Audit confirmed only L295 uses it |
| `DeprecationWarning` missed by callers | LOW | Single internal caller (`workspace_dashboard_cmd`) updated in same PR |
| Test fixture shape change breaks unrelated tests | LOW | 3 affected tests audited; no cross-dependencies |
| Phase 5.2 needs same `needs_by_name` derivation | LOW | Design note: extract `build_needs_by_name(needs_attention)` helper as Phase 5.2 prep follow-up |
| Real DS2 envelope shape differs from assumption | LOW | Tests use realistic mock data; verify-checks.sh Check 1 still passes |

## Rollback Plan

1. Revert `dashboard.py` to L253-295 state (remove `needs_by_name` param, restore `_needs_count` helper)
2. Revert `cli.py` L3069 to `sort_projects(projects, sort)` (remove `needs_by_name` dict comprehension)
3. Revert `test_dashboard.py` T5 to inline-`reasons` fixture shape
4. Revert `test_cli_dashboard.py` `_make_project` to include `reasons`; restore T12.3 original shape
5. Run full suite — expect 1547 + 30 dashboard + 4 CLI dashboard passing

## Dependencies

- PR1+PR2+PR3 dashboard commits (`6651add`, `95e8579`, `778efdb`) — LOCKED, not modified
- `fetch_status_summary` DS2 envelope shape — assumed stable per PR1 data layer lock

## Success Criteria

- [ ] `sort_projects` accepts `needs_by_name` kw-only param without breaking existing callers
- [ ] `--sort needs-count` orders by real DS2 reasons count in production (not inline `reasons`)
- [ ] `DeprecationWarning` fires on fallback path (backward-compat documented)
- [ ] Full suite 1547 + 30 + 4 tests pass
- [ ] Zero new runtime deps
- [ ] PR1+PR2+PR3 dashboard commits byte-identical after apply
- [ ] Design note carry-forward for Phase 5.2: `extract-build-needs-by-name-helper` follow-up documented
