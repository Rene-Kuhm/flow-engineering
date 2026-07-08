# Design: drift-jsonl-rotation-helper

## Outcome

Extract verbatim-duplicated JSONL rotation logic from `drift_event_log.py` and
`observability.py` into one private helper at
`src/flow_engineering/_jsonl_rotation.py`. Zero operator-visible change: env-var
names, defaults, ISO-stamp format, glob prefix, and lock semantics are preserved
exactly. ~100 LOC total, comfortably under the 400-LOC single-PR budget.

## Quick path

1. Add `src/flow_engineering/_jsonl_rotation.py` with `_rotate_jsonl_if_needed` + 2 resolvers.
2. Replace the body of `drift_event_log._rotate_if_needed` (lines 196-254) with a single helper call inside the existing `with self._lock:` block.
3. Replace the body of `observability._rotate_metrics_if_needed` (lines 223-311) with a single helper call.
4. Land RED-first `tests/unit/test_jsonl_rotation.py`; existing 12 rotation tests + `req44_metrics_rotation.feature` stay green with zero edits.

## Technical approach

**One private module, one helper, two call-site shims.** The helper
parameterises only the operator-visible knobs: glob prefix, two env-var names,
two default constants. All FS logic, error handling, and timestamp formatting
lives inside the helper so a future third JSONL sink (e.g. `prompt_renders.jsonl`)
opts in by passing a new `glob_prefix`.

The helper takes **no lock**; both call sites keep their existing concurrency
shape verbatim. `DriftEventLog.append` wraps the helper inside `with self._lock:`
(D11 contract preserved). `observability.increment` calls it outside any lock
(single-process sink, same as today).

## Architecture decisions

| Decision | Choice | Tradeoff | Rationale |
|---|---|---|---|
| Module shape | One private module `_jsonl_rotation.py` | Adds 1 file vs. inlining | Easier to test in isolation; mirrors `_resolve_*` convention |
| Helper style | Function with keyword-only args, not a class | Article IV: only 2 callers today | A class hierarchy would distort `DriftEventLog` (stateful) vs `observability.increment` (stateless) |
| Lock acquisition | None — helper is pure FS | Caller must wrap | Preserves D11 lock contract for `DriftEventLog`; matches existing `observability` (no lock) |
| Env-var passing | Caller passes `max_bytes_env` / `max_age_days_env` strings | More kwargs at call site | Keeps each call site self-describing; no env coupling inside helper |
| ISO stamp source | Private `_stamp_now()` inside helper module | Tiny extra function | Single source of truth — both sinks stay byte-identical |
| Age loop location | Inlined in helper (not a separate `_delete_stale_siblings`) | Loses a private extraction | Mirrors current `drift_event_log.py` shape; `observability._delete_stale_metrics_siblings` is the only deletion that goes away |
| Public API | None — module is private (`_`-prefix) | No `__all__` churn | All consumers are internal; pre-empts accidental third-party import |

## Data flow

```
DriftEventLog.append                      observability.increment
  │                                              │
  │  with self._lock:                            │  (no lock)
  ▼                                              ▼
_rotate_jsonl_if_needed(path,                _rotate_jsonl_if_needed(path,
  glob_prefix="drift_events",                  glob_prefix="metrics",
  max_bytes_env="FLOW_DRIFT_EVENT_LOG_MAX_BYTES",  max_bytes_env="FLOW_METRICS_LOG_MAX_BYTES",
  max_age_days_env="FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS",  max_age_days_env="FLOW_METRICS_LOG_MAX_AGE_DAYS",
  default_max_bytes=ROTATE_BYTES_DEFAULT,        default_max_bytes=METRICS_ROTATE_BYTES_DEFAULT,
  default_max_age_days=ROTATE_AGE_DAYS_DEFAULT)  default_max_age_days=METRICS_ROTATE_AGE_DAYS_DEFAULT)
  │                                              │
  ├─ _resolve_jsonl_rotation_threshold_bytes(…)  ├─ _resolve_jsonl_rotation_threshold_bytes(…)
  ├─ if size ≥ threshold:                        ├─ if size ≥ threshold:
  │     rename → "<prefix>.<ISO-stamp>.jsonl"    │     rename → "<prefix>.<ISO-stamp>.jsonl"
  └─ _resolve_jsonl_max_age_days(…)              └─ _resolve_jsonl_max_age_days(…)
        glob walk + unlink stale siblings            glob walk + unlink stale siblings
```

## File changes

| File | Action | Description |
|------|--------|-------------|
| `src/flow_engineering/_jsonl_rotation.py` | Create | New private module: `_rotate_jsonl_if_needed` + 2 resolvers + `_stamp_now` (~50 LOC) |
| `src/flow_engineering/drift_event_log.py` | Modify | Remove `_resolve_rotation_threshold_bytes` (196-205), `_resolve_max_age_days` (208-217), `_rotate_if_needed` (220-254); add `from flow_engineering._jsonl_rotation import _rotate_jsonl_if_needed`; replace call site at line 141 |
| `src/flow_engineering/observability.py` | Modify | Remove `_resolve_metrics_rotation_threshold_bytes` (223-237), `_resolve_metrics_max_age_days` (240-254), `_delete_stale_metrics_siblings` (257-284), `_rotate_metrics_if_needed` (287-311); update 4 docstring cross-references (lines 226, 243, 262, 290); add helper import; replace call site at line 211 |
| `tests/unit/test_jsonl_rotation.py` | Create | RED-first contract tests (~50 LOC) covering both env-var schemes |
| `tests/unit/test_drift_event_log.py` | **No edit** | Strict regression gate |
| `tests/unit/test_observability.py` | **No edit** | Strict regression gate |
| `tests/bdd/req44_metrics_rotation.feature` | **No edit** | Strict regression gate |
| `src/flow_engineering/prompt_render_log.py` | **No edit** | No rotation today; explicitly out of scope (REQ-JRH-3) |

## Interfaces / contracts

```python
# src/flow_engineering/_jsonl_rotation.py

def _rotate_jsonl_if_needed(
    path: Path,
    *,
    glob_prefix: str,
    max_bytes_env: str,
    max_age_days_env: str,
    default_max_bytes: int,
    default_max_age_days: int,
) -> None:
    """Best-effort size + age rotation for any JSONL sink.

    Sequence: resolve size threshold → if size ≥ threshold: rename
    ``path`` to ``f"{glob_prefix}.{ISO-stamp}.jsonl"``; then resolve
    age threshold → unlink siblings older than the cutoff. Every FS
    call is wrapped in ``try/except OSError``. Acquires NO lock.
    """

def _resolve_jsonl_rotation_threshold_bytes(*, env: str, default: int) -> int:
    """Missing/empty/invalid → default. Negative → 0 (disabled)."""

def _resolve_jsonl_max_age_days(*, env: str, default: int) -> int:
    """Missing/empty/invalid → default. Negative → 0 (disabled)."""

def _stamp_now() -> str:
    """Return ``%Y%m%dT%H%M%SZ`` formatted UTC stamp (single source of truth)."""
```

**Call-site shape (locked):**

```python
# drift_event_log.py — inside DriftEventLog.append
with self._lock:
    _rotate_jsonl_if_needed(
        self.path,
        glob_prefix="drift_events",
        max_bytes_env="FLOW_DRIFT_EVENT_LOG_MAX_BYTES",
        max_age_days_env="FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS",
        default_max_bytes=ROTATE_BYTES_DEFAULT,
        default_max_age_days=ROTATE_AGE_DAYS_DEFAULT,
    )
    with self.path.open("a", encoding="utf-8") as fh: ...

# observability.py — inside increment
path = _resolve_path()
_rotate_jsonl_if_needed(
    path,
    glob_prefix="metrics",
    max_bytes_env=METRICS_LOG_MAX_BYTES_ENV,
    max_age_days_env=METRICS_LOG_MAX_AGE_DAYS_ENV,
    default_max_bytes=METRICS_ROTATE_BYTES_DEFAULT,
    default_max_age_days=METRICS_ROTATE_AGE_DAYS_DEFAULT,
)
```

## Testing strategy

| Layer | What | Approach |
|---|---|---|
| Unit (RED-first) | Helper contract: size threshold triggers rename; age threshold deletes old siblings; env-var defaults; env-var invalid → default; `MAX_AGE_DAYS=0` disables cleanup; rename `OSError` swallowed; env-var schemes stay isolated | `tests/unit/test_jsonl_rotation.py` covers both `glob_prefix="drift_events"` and `glob_prefix="metrics"` via `monkeypatch.setenv` |
| Unit (regression) | `TestRotation` (5 tests) + `TestMetricsRotation` (7 tests) | Strict gate — **zero edits** to `tests/unit/test_drift_event_log.py` + `tests/unit/test_observability.py` |
| BDD (regression) | `tests/bdd/req44_metrics_rotation.feature` | Strict gate — BDD collector run, no edits |
| Lint / type | `ruff` + `mypy` clean on the 3 touched files | `uv run --frozen ruff check` + `uv run --frozen mypy src` |

## Open questions

None. The helper signature, the two call-site shapes, the no-lock contract, the
ISO-stamp format, the env-var names, and the regression gates are all locked
by the proposal + spec. Apply phase has no ambiguity to resolve.

## Next step

Hand off to `sdd-tasks`. The implementation tasks follow the RED-first ordering
already mapped in `explore.md §5`: T1.1 RED → T1.2 GREEN → T2.1 RED (regression
assertions) → T2.2 GREEN (`drift_event_log.py` swap) → T2.3 GREEN
(`observability.py` swap) → T2.4 REFACTOR (drop unused private helpers) → T3.1
VERIFY (ruff + mypy + 12 existing tests + BDD scenarios).

## Checklist for the apply phase

- [ ] `tests/unit/test_jsonl_rotation.py` written FIRST and red
- [ ] `_jsonl_rotation.py` lands with the exact signature above
- [ ] `drift_event_log.py` import + single helper call; 3 private helpers removed; `with self._lock:` still wraps the call
- [ ] `observability.py` import + single helper call; 4 private helpers removed; 4 docstring cross-references rewritten to point at the unified helper
- [ ] `tests/unit/test_drift_event_log.py`, `tests/unit/test_observability.py`, `tests/bdd/req44_metrics_rotation.feature` all green with **zero edits**
- [ ] `uv run --frozen ruff check` + `uv run --frozen mypy src` clean
- [ ] `grep -rn "from flow_engineering.prompt_render_log" src/` shows no `_jsonl_rotation` import (REQ-JRH-3 boundary)
