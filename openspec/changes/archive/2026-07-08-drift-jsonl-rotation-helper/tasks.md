# Tasks: drift-jsonl-rotation-helper (Slice 2)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~100 (50 prod + 50 test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | auto-forecast |
| Chain strategy | not selected |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Out of scope: `prompt_render_log.py` has no rotation today; hypothetical `prompt_renders.jsonl` is a future feature — do NOT introduce it. `flow archive rotate` is separate.

## Phase 1 — RED tests first

- [x] 1.1 Create `tests/unit/test_jsonl_rotation.py` with `monkeypatch.setenv` fixtures for both `glob_prefix` schemes ("drift_events" + "metrics").
- [x] 1.2 RED — size threshold rename produces `f"{glob_prefix}.<ISO-stamp>.jsonl"` + fresh active file (both schemes).
- [x] 1.3 RED — env-var isolation: only `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` set rotates the drift sink, NOT metrics.
- [x] 1.4 RED — `Path.rename` monkey-patched to raise `OSError` returns `None` without raising.
- [x] 1.5 RED — age cutoff unlinks a 60-day-old sibling; recent sibling + active file remain.
- [x] 1.6 RED — `MAX_AGE_DAYS=0` (or `max_age_days <= 0`) skips age cleanup.

## Phase 2 — GREEN helper module

- [x] 2.1 Create `src/flow_engineering/_jsonl_rotation.py` with `_rotate_jsonl_if_needed(path, *, glob_prefix, max_bytes_env, max_age_days_env, default_max_bytes, default_max_age_days)` + `_resolve_jsonl_rotation_threshold_bytes` + `_resolve_jsonl_max_age_days` + `_stamp_now` (`%Y%m%dT%H%M%SZ` UTC).
- [x] 2.2 Guard age cleanup with explicit `if max_age_days <= 0: return` BEFORE `parent.glob(...)` so disabled/negative age skips cleanup without touching FS.
- [x] 2.3 Wrap every FS call (`stat`, `rename`, `glob`, `unlink`) in `try/except OSError`; helper acquires NO lock.
- [x] 2.4 Verify Phase 1 tests turn GREEN: `uv run --frozen pytest tests/unit/test_jsonl_rotation.py -q`.

## Phase 3 — GREEN call-site swaps (drift_event_log)

- [x] 3.1 Add `from flow_engineering._jsonl_rotation import _rotate_jsonl_if_needed` to `src/flow_engineering/drift_event_log.py`; replace `_rotate_if_needed(self.path)` at line 141 with a helper call passing drift-event kwargs (per REQ-JRH-2 table). Keep `with self._lock:` wrapping the helper call (D11 preserved).
- [x] 3.2 Delete unused private helpers `_resolve_rotation_threshold_bytes` (196-205), `_resolve_max_age_days` (208-217), `_rotate_if_needed` (220-254); update `__all__` (line 191-192) only if no internal caller references the dropped names.

## Phase 4 — GREEN call-site swaps (observability)

- [x] 4.1 Add the same helper import to `src/flow_engineering/observability.py`; replace `_rotate_metrics_if_needed(path)` at line 211 with a helper call passing metrics kwargs (per REQ-JRH-2 table). No lock wrapper (single-process sink, unchanged).
- [x] 4.2 Delete `_resolve_metrics_rotation_threshold_bytes` (223-237), `_resolve_metrics_max_age_days` (240-254), `_delete_stale_metrics_siblings` (257-284), `_rotate_metrics_if_needed` (287-311); rewrite the 4 docstring cross-references (lines 226, 243, 262, 290) to point at `_rotate_jsonl_if_needed`.

## Phase 5 — VERIFY regression gates + boundary

- [x] 5.1 `uv run --frozen pytest tests/unit/test_drift_event_log.py tests/unit/test_observability.py -q` — 5 `TestRotation` + 7 `TestMetricsRotation` stay GREEN with ZERO edits (strict gate).
- [x] 5.2 `uv run --frozen pytest tests/bdd -q` — `req44_metrics_rotation.feature` stays GREEN with ZERO edits.
- [x] 5.3 `uv run --frozen ruff check` + `uv run --frozen mypy src` — clean on the 3 touched files.
- [x] 5.4 Boundary (REQ-JRH-3, corrected command): assert `grep -rn "_jsonl_rotation" src/flow_engineering/prompt_render_log.py` returns NO matches. Do NOT search importers of `prompt_render_log`; do NOT introduce `prompt_renders.jsonl`.
