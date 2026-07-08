# Proposal: drift-jsonl-rotation-helper (Slice 2)

## Intent

Extract the duplicated JSONL rotation logic from `drift_event_log.py` and `observability.py` into a single shared helper, eliminating ~58 LOC of verbatim duplication. Zero behavior change for operators — env-var names, defaults, glob prefixes, ISO-stamp format, and lock semantics are preserved exactly.

## Scope

### In Scope
- New `src/flow_engineering/_jsonl_rotation.py` containing `_rotate_jsonl_if_needed` + two parameterized env-var resolvers.
- `drift_event_log.py`: replace `_rotate_if_needed` + 2 private resolvers with one helper call.
- `observability.py`: replace `_rotate_metrics_if_needed` + 3 private helpers with one helper call.
- New `tests/unit/test_jsonl_rotation.py`: RED-first contract tests exercising both env-var schemes.

### Out of Scope
- Slice 3 (`graph_unavailable` per-finding refinement) — separate change.
- `prompt_render_log.py` rotation — no rotation helper exists there today; adding one is a new feature.
- `flow archive rotate` (read-only archive preview) — not JSONL rotation; different concern.
- Changes to existing rotation tests (`TestRotation`, `TestMetricsRotation`) or BDD scenarios.

## Approach

**Approach B — Single shared helper** (recommended by explore §3; accepted here verbatim):

```
src/flow_engineering/_jsonl_rotation.py   (~50 LOC)
  ├── _rotate_jsonl_if_needed(path, *, glob_prefix, max_bytes_env,
  │      max_age_days_env, default_max_bytes, default_max_age_days) -> None
  ├── _resolve_jsonl_rotation_threshold_bytes(*, env, default) -> int
  └── _resolve_jsonl_max_age_days(*, env, default) -> int
```

Each call site passes its own env-var name + default constant:
- `DriftEventLog.append` → `glob_prefix="drift_events"`, env vars `FLOW_DRIFT_EVENT_LOG_MAX_BYTES / MAX_AGE_DAYS`, defaults `ROTATE_BYTES_DEFAULT / ROTATE_AGE_DAYS_DEFAULT`
- `observability.increment` → `glob_prefix="metrics"`, env vars `FLOW_METRICS_LOG_MAX_BYTES / MAX_AGE_DAYS`, defaults `METRICS_ROTATE_BYTES_DEFAULT / METRICS_ROTATE_AGE_DAYS_DEFAULT`

**No class hierarchy** (Article IV anti-abstraction: only 2 callers today). Helper is keyword-only args, private module, no new public exports.

## Capabilities

### New Capabilities
- `<jsonl-rotation-helper>`: Shared `_rotate_jsonl_if_needed` function for any JSONL sink to opt-in by passing `glob_prefix`.

### Modified Capabilities
- None — pure refactor, REQ-V1.1.1 + REQ-V1.2.1 wording stays valid.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/_jsonl_rotation.py` | New | Shared helper module (~50 LOC) |
| `src/flow_engineering/drift_event_log.py` | Modified | Remove 3 private helpers; add 1 import + 1 helper call |
| `src/flow_engineering/observability.py` | Modified | Remove 4 private helpers; add 1 import + 1 helper call |
| `tests/unit/test_jsonl_rotation.py` | New | RED-first contract tests for the helper |
| `tests/unit/test_drift_event_log.py` | None | Strict regression gate only — zero edits |
| `tests/unit/test_observability.py` | None | Strict regression gate only — zero edits |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Helper signature mismatch with caller env-var names | Low | RED tests exercising both schemes (`FLOW_DRIFT_EVENT_LOG_*` + `FLOW_METRICS_LOG_*`) before GREEN implementation |
| ISO-stamp format divergence after refactor | Low | Extract `_stamp_now()` inside helper module as single source of truth |
| `prompt_render_log.py` confusion (no rotation there) | Low | Docstring explicitly states "JSONL file rotation"; exploration corrects prior incorrect "3rd copy" claim |
| Lock semantics broken in `DriftEventLog` | Low | Helper takes no lock; `with self._lock:` wrapper stays in `DriftEventLog.append` exactly as today |

## Rollback Plan

`git revert <merge-commit>` removes the helper module and restores the original helper definitions in both `drift_event_log.py` and `observability.py`. The revert is safe because helpers are additive-only (no schema migration, no data migration).

## Dependencies

- Slice 1 (`drift-detection`) already shipped at `cf7a052` — no dependency on it; Slice 2 is independent.

## Success Criteria

- [ ] `ruff` and `mypy` clean on `_jsonl_rotation.py`, `drift_event_log.py`, `observability.py`
- [ ] `tests/unit/test_jsonl_rotation.py` RED tests written first (TDD), then GREEN implementation
- [ ] Existing 5 `TestRotation` tests + 7 `TestMetricsRotation` tests + `req44_metrics_rotation.feature` all green
- [ ] `DriftEventLog._lock` contract unchanged (rotation still inside `with self._lock:`)
- [ ] ISO-stamp format unchanged (`%Y%m%dT%H%M%SZ`)
- [ ] LOC delta: ~50 production + ~50 test = ~100 total (well under 400-LOC budget)

## Size Estimate

| Layer | LOC |
|-------|-----|
| Production helpers | ~50 |
| New test file | ~50 |
| **Total** | **~100** |

**Budget risk**: Low. ~75% headroom under 400-LOC single-PR budget.
