# JSONL Rotation Helper Specification

## Purpose

Cross-version capability spec for the `jsonl-rotation-helper` — a single private helper that powers best-effort size + age rotation for any append-only JSONL sink. It consolidates the two verbatim-duplicated rotation implementations (`drift_event_log._rotate_if_needed` introduced by REQ-V1.1.1, and `observability._rotate_metrics_if_needed` introduced by REQ-V1.2.1) into one module so future JSONL sinks can opt-in by passing a `glob_prefix`.

This is a **pure refactor**: the operator contract (env-var names, defaults, ISO-stamp format, glob prefix, lock semantics, best-effort error handling) is preserved verbatim. The change ships no new public API and no new operator-visible behavior.

## Source

`openspec/changes/drift-jsonl-rotation-helper/{proposal,exploration}.md` (Slice 2 of `drift-detection`, Approach B). Predecessor contracts: REQ-V1.1.1 (`decision-drift/spec.md`) and REQ-V1.2.1 (`observability/spec.md` v1.2.0a archive).

## Requirements

### REQ-JRH-1 — Shared rotation helper

The system SHALL expose `_rotate_jsonl_if_needed(path, *, glob_prefix, max_bytes_env, max_age_days_env, default_max_bytes, default_max_age_days) -> None` plus two private env-var resolvers at `flow_engineering._jsonl_rotation`. It MUST rename `path` to `f"{glob_prefix}.<ISO-stamp>.jsonl"` when `st_size >= threshold` and MUST `parent.glob(f"{glob_prefix}.*.jsonl")` to unlink siblings older than the cutoff. Every FS call MUST be wrapped in `try/except OSError` (best-effort); the helper MUST NOT acquire any lock.

### REQ-JRH-2 — Operator contract verbatim preservation

The helper MUST keep every element of the existing operator contract unchanged:

| Surface | Drift-event sink (`drift_event_log.py`) | Metrics sink (`observability.py`) |
|---|---|---|
| `glob_prefix` | `drift_events` | `metrics` |
| size env var | `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` | `FLOW_METRICS_LOG_MAX_BYTES` |
| age env var | `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` | `FLOW_METRICS_LOG_MAX_AGE_DAYS` |
| size default | `10485760` (10 MB) | `10485760` (10 MB) |
| age default | `30` | `30` |
| ISO stamp | `%Y%m%dT%H%M%SZ` | `%Y%m%dT%H%M%SZ` |
| lock semantics | call wrapped inside `DriftEventLog._lock` | none (single-process sink) |
| error handling | best-effort `try/except OSError` swallow | best-effort `try/except OSError` swallow |

### REQ-JRH-3 — Scope boundaries

The helper MUST NOT be imported by `src/flow_engineering/prompt_render_log.py` (no rotation today; separate future feature). The helper MUST NOT be used by `flow archive rotate` (`cli/rotation.py`), which rotates `openspec/changes/archive/` directories.

### REQ-JRH-4 — Strict TDD posture + regression gates

The helper MUST land RED-first via `tests/unit/test_jsonl_rotation.py` covering both env-var schemes. The 12 existing rotation tests (5 `TestRotation` + 7 `TestMetricsRotation`) and `tests/bdd/req44_metrics_rotation.feature` MUST stay green with ZERO edits (strict regression gate).

## Scenarios

### Scenario: helper rotates at the size threshold (both schemes)

- GIVEN two tmp sinks — `<tmp>/drift_events.jsonl` with `FLOW_DRIFT_EVENT_LOG_MAX_BYTES=1024` and `<tmp>/metrics.jsonl` with `FLOW_METRICS_LOG_MAX_BYTES=1` — both pre-sized to 2048 bytes
- WHEN `_rotate_jsonl_if_needed(...)` runs once per sink with the matching `glob_prefix` + env-var names + defaults
- THEN each invocation produces exactly one rotated sibling (`drift_events.<stamp>.jsonl` or `metrics.<stamp>.jsonl`) and the active file is fresh.

### Scenario: env-var schemes stay isolated

- GIVEN only `FLOW_DRIFT_EVENT_LOG_MAX_BYTES=10` set
- WHEN the helper is invoked for both `glob_prefix="drift_events"` and `glob_prefix="metrics"`
- THEN only the drift-event invocation rotates; the metrics invocation is a no-op.

### Scenario: best-effort rename failure does not raise

- GIVEN `Path.rename` monkey-patched to raise `OSError`
- WHEN the helper runs on a sink that meets the size threshold
- THEN the helper returns `None` without raising.

### Scenario: age-based cleanup honours cutoff

- GIVEN `MAX_AGE_DAYS=30` and two pre-existing siblings (mtime 60 d ago + mtime today)
- WHEN the helper runs
- THEN the 60-day-old sibling is unlinked; the recent sibling + active file remain.

### Scenario: age cleanup disabled via env var (`MAX_AGE_DAYS=0`)

- GIVEN `MAX_AGE_DAYS=0` and a 5-year-old rotated sibling
- WHEN the helper runs
- THEN no sibling is unlinked.

### Scenario: `prompt_render_log.py` stays untouched

- GIVEN a regex search of `src/flow_engineering/prompt_render_log.py`
- WHEN the apply phase completes
- THEN no `_jsonl_rotation` import is present.

### Scenario: regression gates stay green

- GIVEN the 5 `TestRotation` + 7 `TestMetricsRotation` tests + `tests/bdd/req44_metrics_rotation.feature`
- WHEN `uv run pytest tests/unit/test_drift_event_log.py tests/unit/test_observability.py` + BDD collector run
- THEN every test passes with ZERO edits to those files.
