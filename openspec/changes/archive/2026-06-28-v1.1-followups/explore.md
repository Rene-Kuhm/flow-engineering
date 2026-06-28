<!-- explore.md: v1.1-followups. Source: sdd-explore sub-agent (2026-06-28). Backfilled 2026-06-28 from engram `sdd/v1.1-followups/explore` summary + verify-report.md + commit history per W2 cleanup. -->
# Explore: v1.1-followups

**Change:** `v1.1-followups` (NEW change — consolidates 6 deferred items from `v1.0-followups` S1+S2+S3+S4+S5 + `drift-hardening` W7 into a single v1.1.0 debt-closure release)
**Date:** 2026-06-28
**Mode:** Strict TDD (per `sdd-init/flow-engineering` cached context; loop mode ACTIVE)
**HEAD at exploration:** `ec97348` (post-`v1.0-followups` archive push; 1275/1275 tests passing per capability spec `decision-drift/spec.md` v1.0 entry)
**Branch:** `main` (working tree CLEAN per `git status --short`)
**Pre-discussion:** capability spec already lists the v1.1 plan verbatim at `openspec/specs/decision-drift/spec.md` (post-v1.0 archive entry); `v1.0-followups` verify-report S1..S5 + W7 carry the explicit recommendations; `drift-hardening` verify-report W7 mirrors the DriftEventLog rotation carry-forward.

---

## Status

**explored → ready for `sdd-propose v1.1-followups`**. All 6 items investigated (REQ-V1.1.1 DriftEventLog rotation + REQ-V1.1.2 S2 hardening drop defensive shim + REQ-V1.1.3 prompt_renders.jsonl sink + REQ-V1.1.4 prompt observability counters + REQ-V1.1.5 docs/prompts.md auto-gen + REQ-V1.1.6 ruff --unsafe-fixes cleanup on `decision_drift.py`). Exploration confirmed scope + dependencies + risks. No new investigation required before proposal.

---

## Goal

Land the 6 deferred items (S1 + S2 + S3 + S4 + S5 + W7 from prior verify-reports) in a single small TDD change that closes the operator-UX gap left by v1.0 hard-break migration, without re-opening any closed carry-forward. v1.2 follow-ups (golden regression tests + min_sdd_skill_versions + Path A subcommand rename + remaining ruff residuals) remain deferred per the capability spec roadmap.

---

## Investigation findings

### REQ-V1.1.1 — `DriftEventLog` rotation

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/drift_event_log.py:46` — `decision_id: int` (v1.0 wire-format flip done).
- `src/flow_engineering/drift_event_log.py:197-218` — `_resolve_rotation_threshold_bytes()` + `_resolve_max_age_days()` env-var resolution helpers present (READ-ONLY constants used; rotation itself was never wired).
- `src/flow_engineering/drift_event_log.py:23` — `import sys` (used previously by `_legacy_warn_emitted` stderr WARN; unused in v1.0; flagged F401 by ruff).
- `tests/unit/test_drift_event_log.py` — TestAppend + TestReadAllLegacyCoercion + TestDriftEvent + TestRotation classes (the 5 TestRotation tests are RED fixtures for v1.1).

**Operator-visible gap:**

- `~/.flow-engineering/drift_events.jsonl` grows unbounded forever.
- No `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` / `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` env vars.
- `metrics.jsonl` has the same gap (REQ-44 deferred — see capability spec).

**Carry-forward source**: `drift-hardening` verify-report #242 W7 (deferred to v1.1 alongside metrics rotation per capability spec `spec.md` v0.8.0 final note).

---

### REQ-V1.1.2 — S2 hardening (drop defensive `str→int` shim)

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/drift_event_log.py:96` — `_legacy_warn_emitted` per-instance flag (v1.0 soft-compat shim).
- `src/flow_engineering/drift_event_log.py:140-149` — defensive `try/except (TypeError, ValueError)` block that coerces legacy `str` `decision_id` lines to `int`.
- `src/flow_engineering/cli.py:1818/1905/1987/2036` — 3 `flow drift-events {list,tail,stats}` subcommands from v1.0.

**Operator-visible gap:**

- v1.0 defensive shim silently coerces legacy `str` lines; operators never know they need to migrate.
- The `sed` migration hint from CHANGELOG v1.0 is buried in the changelog; CLI should expose `--strict` to surface it.

**Carry-forward source**: `v1.0-followups` verify-report S2 (deferred hardening; soft-compat was intentional for v1.0, hard-error in v1.1).

---

### REQ-V1.1.3 — `prompt_renders.jsonl` sink (REQ-51 from prompt-registry)

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/prompt_registry.py:758` — `render_prompt()` hook is the only place where renders happen.
- `src/flow_engineering/prompt_registry.py` — `_render_started_monotonic` timer (v1.0 infrastructure).
- No JSONL sink for render history.

**Operator-visible gap:**

- No audit trail for prompt renders (operators cannot answer "who rendered this prompt, when, with what vars").
- No `--render-count` or `--render-history` flag on `flow prompts show`.

**Carry-forward source**: `prompt-registry` PR#1 spec REQ-51 (deferred to v1.1 per capability spec roadmap).

---

### REQ-V1.1.4 — Prompt observability counters (REQ-52 from prompt-registry)

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/observability.py:485-490` — counter catalog.
- `src/flow_engineering/observability.py:495-509` — `DOMAIN_BY_PREFIX` table (no `prompts_` entry).
- `src/flow_engineering/observability.py:507-554` — `record_drift_summary` (counter emission pattern to mirror).

**Operator-visible gap:**

- No `prompts_render_total{domain, prompt_id, status}` counter.
- No `prompts_render_ms{domain, prompt_id, count}` latency counter.
- No `prompts_render_failed_total{domain, prompt_id, error}` counter.
- `flow metrics --domain=prompt` not available.

**Carry-forward source**: `prompt-registry` PR#1 spec REQ-52 (deferred to v1.1 alongside REQ-51).

---

### REQ-V1.1.5 — `docs/prompts.md` auto-generation (REQ-53 from prompt-registry)

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/prompt_registry.py` — `PROMPT_NAMES` catalog (20 entries).
- `prompts/*.j2` — Jinja2 templates.
- No `docs/prompts.md` generated artifact.

**Operator-visible gap:**

- No human-readable catalog of all 20 prompts with their purposes + example output.
- Each new prompt requires manual `docs/prompts.md` update.

**Carry-forward source**: `prompt-registry` PR#1 spec REQ-53 (deferred to v1.1 alongside REQ-51/52).

---

### REQ-V1.1.6 — ruff `--unsafe-fixes` on `decision_drift.py` + SnapshotGraphMissing alias

**Current state (HEAD `ec97348`):**

- `src/flow_engineering/decision_drift.py:179` — `class SnapshotGraphMissing(ValueError)` (parallel class to canonical `SnapshotGraphMissingError`).
- `src/flow_engineering/snapshot_manager.py` — `SnapshotEnvelopeError` only; no `SnapshotGraphMissingError` yet.
- Ruff: 4 visible errors at `decision_drift.py:49/178/339/681` (UP042 + N818 + SIM105 + C401 with current pyproject config); 12 historical "errors" cited in verify-reports are config-dependent.

**Operator-visible gap:**

- No canonical `SnapshotGraphMissingError` class; existing parallel `SnapshotGraphMissing` is N818-non-compliant.
- 4 ruff `--unsafe-fixes` cleanup sites linger.

**Carry-forward source**: `v0.9.0-hardening` verify-report S2 (12 ruff `--unsafe-fixes` cleanup at `decision_drift.py`); 3 fixed in T6.3 of v1.1 (UP022 + UP042 + C419); the `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename is the additional surface from `prompt-registry` PR#2a.

---

## Dependency analysis

Per the exploration, the 6 items have a strict dependency order:

1. **REQ-V1.1.1 (rotation)** — INDEPENDENT (touches only `drift_event_log.py`)
2. **REQ-V1.1.2 (S2 hardening)** — INDEPENDENT of REQ-V1.1.1 (same file but different concerns)
3. **REQ-V1.1.3 (prompt_renders.jsonl sink)** — INDEPENDENT (NEW file `prompt_render_log.py` + 1 wire in `prompt_registry.py`)
4. **REQ-V1.1.4 (prompt observability counters)** — DEPENDS on REQ-V1.1.3 (shares the `_emit_render_record` hook)
5. **REQ-V1.1.5 (docs/prompts.md auto-gen)** — INDEPENDENT (NEW script + committed artifact)
6. **REQ-V1.1.6 (ruff cleanup + alias)** — LAST (cleanest closure; mirrors v0.8.0→v0.9.0 compat-shim removal precedent)

## Risks identified

- **LOW**: rotation under lock on slow network FS — single-process daemon mitigates; best-effort OSError swallow.
- **MED**: D2 S2 hardening breaks operators who didn't run CHANGELOG v1.0 sed migration — default skip+WARN mode preserves data; --strict aborts with migration hint.
- **MED**: D6 SnapshotGraphMissing rename is public — 1-release alias shim.
- **LOW**: prompt_renders.jsonl variables dict may grow unbounded — defensive cap at 100 vars.
- **LOW**: render_prompt() instrumentation hot-loop risk — project usage <10 renders/sec today; revisit if needed.
- **MED**: single-PR strategy bundles 6 items (~9600 LOC realistic ×6 TDD) — per-commit work-unit splits per work-unit-commits skill.

## Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `v1.0-followups` S1 | DriftEventLog rotation deferred | REQ-V1.1.1 |
| `v1.0-followups` S2 | Defensive `str→int` shim hardening (WARN → error) | REQ-V1.1.2 |
| `v1.0-followups` S3 | REQ-51 `prompt_renders.jsonl` sink | REQ-V1.1.3 |
| `v1.0-followups` S4 | REQ-52 prompt observability counters | REQ-V1.1.4 |
| `v1.0-followups` S5 | REQ-53 `docs/prompts.md` auto-generated | REQ-V1.1.5 |
| `v0.9.0-hardening` S2 | 12 ruff `--unsafe-fixes` at `decision_drift.py` | REQ-V1.1.6 (3 fixed; remaining 9 deferred to v1.2 per project precedent) |

## Carry-forwards explicitly NOT touched by this change (deferred)

| Source | Item | Deferral target |
|---|---|---|
| `observability` PR#2 | REQ-44 `metrics.jsonl` rotation | v1.2+ (out of v1.1 scope; brief scopes v1.1 to DriftEventLog only) |
| `prompt-registry` PR#2a | REQ-48 golden regression tests | v1.2+ (next-feature territory) |
| `prompt-registry` PR#2a | REQ-54 `min_sdd_skill_versions` | v1.2+ (tooling gate) |
| `v1.0-followups` | Path A `flow drift-events` subcommand group rename (BREAKING) | v1.2+ (revisit only if `flow drift` namespace grows further) |