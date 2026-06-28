<!-- tasks.md: drift-hardening. Source: sdd-tasks sub-agent. -->
# Tasks: drift-hardening

**Change:** `drift-hardening` (change #8)
**Builds on:** `proposal.md` (#223) — Approach A: single PR with 4 sequential apply batches; `design.md` (#229) — D1-D12 + 10 open questions resolved; `spec.md` (#227) — 5 REQs (REQ-55..59), 21 BDD scenarios
**Date:** 2026-06-27
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (single PR, 4 sequential batches)
**Strict TDD:** ON (per `decision-code-linking` archive-report #119 S3 precedent; RED → GREEN → REFACTOR cycle per task)
**Delivery strategy:** single-pr (per proposal #223; ×5.7 strict-TDD multiplier maps ~1 913 forecast to ~9 700 realistic — below the observability ~10 910 chained-PR threshold)

> **REQ-label note**: this artifact's batch structure mirrors the orchestrator's task brief. Canonical REQ labels per design #229 / spec #227:
> REQ-55 = JSONL + silence; REQ-56 = dataclass migration; REQ-57 = BDD coverage;
> REQ-58 = snapshot field reconciliation; REQ-59 = W23 deprecation + S2 stderr WARN.

---

```yaml
status: success
confidence: high
total_tasks: 22  # T1.1..T1.5 + T2.1..T2.6 + T3.1..T3.6 + T4.1..T4.5
pr_split: single PR (4 sequential apply batches: A → B → C → D)
forecast_loc_production: ~300   # per spec §"File plan" net prod
forecast_loc_test: ~1855         # per spec §"File plan" net test (includes BDD scenarios + step glue)
forecast_loc_grand_total: ~2173  # ~300 prod + ~1855 test + ~18 archived spec/design
forecast_loc_realistic_x5_7: ~9700
batches:
  batch_a: 5 tasks   # T1.1..T1.5   — REQ-55 W6 silence + REQ-58 spec/design reconciliation
  batch_b: 6 tasks   # T2.1..T2.6   — REQ-55 JSONL + REQ-59 W23 + REQ-59 S2 stderr + REQ-58 W25/W26
  batch_c: 6 tasks   # T3.1..T3.6   — REQ-57 BDD coverage (21 NEW + 2 extended)
  batch_d: 5 tasks   # T4.1..T4.5   — REQ-56 dataclass migration + CHANGELOG v0.8.0 + SKILL.md + pyproject
review_workload_forecast:
  single_pr_400_line_budget_risk: high
  single_pr_realistic_loc: ~9700  # ×5.7 per design §"Structured Metadata"
  decision_needed_before_apply: no  # explicit in proposal #223 §"Approach matrix"
strict_tdd: on
bdd_feature_files: 6 NEW (req10 + req11 + req12 + req13 + req14 + req16) + 1 EXTENDED (req15_drift_daemon)
bdd_scenarios: 21 NEW (REQ-10:9 + REQ-11:3 + REQ-12:3 + REQ-13:3 + REQ-14:4 + REQ-16:2) - 3 folded = 21; plus 2 extended REQ-15 JSONL scenarios = 23 total
file_created: C:\dev\proyects\flow-engineering\openspec\changes\drift-hardening\tasks.md
next_recommended: sdd-apply drift-hardening batch A (T1.1..T1.5)
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×5.7) |
|----|------|-------|--------------|----------------------|
| **PR#1** (drift-hardening) | REQ-55..59 (all 5) | T1.1..T4.5 (22 tasks across 4 sequential apply batches) | ~300 prod / ~1855 test / ~18 archived spec-design = ~2173 | ~9 700 |
| **Total** | **5 REQs** | **22 tasks** | **~2 173** | **~9 700** |

**Rationale**: Single PR per proposal #223 Approach A. Bundles REQ-56 (W8) breaking dataclass migration with REQ-55 (W5/W6) JSONL + silence, REQ-57 (W4) BDD coverage, REQ-58 (W25/W26) snapshot spec reconciliation, and REQ-59 (W23+S2) closeout into one v0.8.0 release. One migration event = one migration guide = one PR review. Per-commit work-unit splits per `work-unit-commits` skill (12-14 commits each ≤400 LOC across 4 batches per design D12).

---

## Dependency Graph

```
Batch A — REQ-55 W6 silence rule + REQ-58 spec/design reconciliation (4-5 tasks)
  T1.1 (daemon.py silence + 3 unit tests)
    ↓
  T1.2 (archived spec/design docs-only: REQ-15 event-log + silence reconciliation)
  T1.3 (archived spec/design docs-only: snapshot field-name reconciliation REQ-58)
    ↓
  T1.4 (CHANGELOG v0.8.0-dev section placeholder)
  T1.5 (test_decision_drift rename smoke tests for `unable_to_verify` accessor)

Batch B — REQ-55 JSONL writer + REQ-59 W23 + S2 stderr + REQ-58 W25/W26 (5-6 tasks)
  T2.1 (NEW drift_event_log.py: record_drift_event + iter_drift_events + 10MB rotation + 5 unit tests)
    ↓
  T2.2 (daemon.py wire record_drift_event + CLI --drift-event-log flag + 3 unit tests)
    ↓
  T2.3 (extend req15_drift_daemon.feature with 2 JSONL scenarios + step glue extension)
    ↓
  T2.4 (docs-only snapshot field-name update: SnapshotMeta.size_bytes + PruneResult.freed_bytes in archived spec/design)
  T2.5 (_write_back_findings S2 stderr WARN + _get_skip_warn_threshold helper + 2 unit tests)
  T2.6 (CHANGELOG v0.6.0 Notes section W23 deprecation note)

Batch C — REQ-57 BDD coverage: 21 NEW + 2 extended scenarios (6-8 tasks)
  T3.1 (req10_drift_cli.feature 9 scenarios — flow drift <change> CLI surface)
  T3.2 (req11_drift_exit.feature 3 scenarios — exit codes 0/1/2)
  T3.3 (req12_drift_counters.feature 3 scenarios — 8 drift_*_total counters)
  T3.4 (req13_drift_metadata.feature 3 scenarios — update_observation_metadata)
  T3.5 (req14_drift_resilience.feature 4 scenarios — non-breaking behavior)
  T3.6 (req16_skill_prose.feature 2 scenarios — SKILL.md drift detection hook + extend step glue ~400 LOC)

Batch D — REQ-56 dataclass migration + closeout (4-5 tasks)
  T4.1 (Finding dataclass: decision_id int + __post_init__ coercion + 4 unit tests)
  T4.2 (DriftReport dataclass: scanned_at str ISO + unable_to_verify + unable_reason + from_scanned() + @property graph_unavailable alias + 4 unit tests)
  T4.3 (classify_binding(ref, graph_nodes) 2-arg signature + 2 unit tests)
  T4.4 (update all callers in daemon.py + cli.py + observability.py + remove legacy shims)
  T4.5 (CHANGELOG v0.8.0 entry + BREAKING section + 6 SKILL.md runtime updates + pyproject 0.7.0→0.8.0 + openspec/specs/drift-hardening/spec.md bootstrap + 4 unit/grep tests)

[Apply batch merge after each batch → final PR merge]
```

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 22 (T1.1..T1.5, T2.1..T2.6, T3.1..T3.6, T4.1..T4.5) |
| Forecast LOC production | ~300 |
| Forecast LOC test (unit + BDD) | ~1 855 |
| Forecast LOC grand total | **~2 173** |
| Forecast LOC realistic (×5.7 TDD multiplier per design §"Structured Metadata") | **~9 700** |
| BDD feature files | 6 NEW (req10..req16) + 1 EXTENDED (req15_drift_daemon) |
| BDD scenarios | 21 NEW + 2 EXTENDED = 23 (REQ-10:9 + REQ-11:3 + REQ-12:3 + REQ-13:3 + REQ-14:4 + REQ-16:2 + REQ-15:+2) |
| New source files | 1 (`src/flow_engineering/drift_event_log.py`) + 1 capability spec (`openspec/specs/drift-hardening/spec.md`) |
| Modified source files | 5 (`decision_drift.py`, `daemon.py`, `cli.py`, `observability.py`, `pyproject.toml`) + 4 archived spec/design + 1 CHANGELOG + 6 SKILL.md |
| New test files | 1 unit (`test_drift_event_log.py`) + 6 BDD step glue (`test_req10_steps.py`..`test_req16_steps.py`) + 4 unit/grep (`test_changelog_drift_hardening.py`, `test_pyproject_version.py`, `test_skill_md_drift_hooks.py`, `test_drift_hardening_steps.py`) |
| Chained PRs recommended | **No** (single PR per proposal #223; ×5.7 realistic LOC below observability's ~10 910 chained-PR threshold) |
| Chain strategy | N/A (single PR; per-commit work-unit splits per `work-unit-commits`) |
| 400-line budget risk | **High** (single PR ~2 173 forecast / ~9 700 realistic) — mitigated by 12-14 work-unit commits each ≤400 LOC |
| Decision needed before apply | **No** (single-pr is explicit in proposal #223 §"Approach matrix"; per-commit splits mitigate review budget) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A (single PR)
400-line budget risk: High

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC | spec §"File plan" + design §"Module/File Layout" (drift_event_log.py ~150 + decision_drift.py +40/-20 + daemon.py +30/-10 + cli.py +45/-10 + observability.py +15 + 4 archived spec/design +18 net + CHANGELOG +43 + pyproject +1/-1 + 6 SKILL.md +80) | ~300 |
| Test LOC | spec §"File plan" (test_drift_event_log.py +180 + 5 MODIFY unit tests +80 + 6 NEW BDD feature files ~700 + step glue +400 + 4 closeout unit/grep +400) | ~1 855 |
| Realistic ×5.7 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113) per design §"Structured Metadata": `decision-code-linking` precedent sets strict-TDD band | ×5.7 → ~9 700 grand total realistic |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (#112): ≤3 tasks OR ≤150 LOC prod per delegation, default runtime ~15 min | batch C at ~100 prod + 800 test is the **TIMEOUT RISK BATCH** |
| Risk: batch C BDD coverage | 6 NEW .feature files + 6 step glue at ~6 LOC/min = ~30min, but BDD quality gate (D5) adds review cycle | **QUALITY RISK** — keep 3 scenarios per file; quality gate spot-check 3 random scenarios for business-domain phrasing |
| Risk: 400-line review budget | Single PR ~2 173 LOC > 400-line budget | Mitigated by 12-14 work-unit commits per `work-unit-commits` convention; per-commit diffs ≤400 LOC |

### Suggested Work Units

Single PR (no chained PR split per proposal #223 + design D12). Per-delegation batching (≤3 tasks / ≤150 LOC prod) still required at apply phase because delegate runtime is ~15 min.

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|----------------|----------|-----|
| **A** | T1.1 + T1.2 + T1.3 + T1.4 + T1.5 | ~30 | ~50 | Silence rule in `daemon.py:handle_apply_progress_event` + 4 archived spec/design docs-only edits + CHANGELOG v0.8.0-dev placeholder + rename smoke tests |
| **B** | T2.1 + T2.2 + T2.3 | ~180 | ~280 | NEW `drift_event_log.py` + daemon wiring + `--drift-event-log` CLI flag + 2 BDD scenarios for req15_drift_daemon — atomic foundation |
| **C** | T2.4 + T2.5 + T2.6 | ~50 | ~50 | Snapshot field-name docs-only + S2 stderr WARN in `_write_back_findings` + CHANGELOG v0.6.0 Notes W23 entry |
| **D** | T3.1 + T3.2 + T3.3 | ~50 | ~250 | 3 of 6 NEW BDD feature files (req10/req11/req12 = 15 scenarios) + 3 step glue files |
| **E** | T3.4 + T3.5 + T3.6 | ~50 | ~250 | Remaining 3 NEW BDD feature files (req13/req14/req16 = 9 scenarios) + 3 step glue files + extend `req15_drift_daemon` + extend consolidated step glue |
| **F** | T4.1 + T4.2 | ~80 | ~150 | Finding + DriftReport dataclass shape migration + `__post_init__`/`from_scanned()`/`@property` aliases + 8 unit tests |
| **G** | T4.3 + T4.4 + T4.5 | ~80 | ~150 | `classify_binding` 2-arg signature + caller updates + CHANGELOG v0.8.0 + 6 SKILL.md hooks + pyproject bump + spec bootstrap + 4 closeout tests |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 13 items are explicitly deferred per spec §"Out of Scope" + design §"Out-of-Scope (consolidated)" — apply must NOT introduce code for them:

- **`flow drift events` CLI command** (read-side surface for `drift_events.jsonl`) — deferred per OQ-9; consumers use `cat ~/.flow-engineering/drift_events.jsonl | jq` or `flow metrics --domain drift`
- **`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` / `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` env vars** — deferred per OQ-2; hardcoded 10 MB mirrors `metrics.jsonl`; joint with REQ-44 v1.1
- **`FindingLegacy` dataclass shim** (OQ-1 rejected option c) — the 1-release `@property graph_unavailable` + `__post_init__` coercion IS the migration path; v1.0 removes both
- **Mypy strict-mode adapter for `decision_id: int | str`** — v0.8.0 ships `int`-only; legacy callers update by v1.0
- **Cross-project federation for drift events** (`flow drift events --project=<key>`) — deferred to `federated-drift-events` follow-up
- **OpenTelemetry push for drift events** — deferred; Prometheus textfile (REQ-38) covers v1 export
- **Per-finding graph_unavailable classification** — `classify_binding` handles it at report level only; v2
- **Auto-daily snapshot trigger** (`trigger="auto"`) — already deferred in `graph-snapshots` archive; unchanged
- **Snapshot export/import for sharing** — already deferred in `graph-snapshots` archive; unchanged
- **`flow drift events --format=prometheus|csv`** — raw JSONL is the only v0.8.0 output format
- **Runtime WARN on `flow metrics` for legacy `snapshot_pruned_total`** (OQ-7 rejected) — CHANGELOG-only documentation preserves audit trail
- **Dataclass migration tooling** — no automated migration; the 1-release deprecation aliases + CHANGELOG BREAKING section is the migration path
- **Async drift-on-save** (`flow drift scan` triggered on `mem_save`) — deferred; daemon tick + on-demand pattern preserved

---

## Patterns Honored

- `apply-batches-split-into-6-tasks-per-delegation` (Engram #112): each apply batch ≤3 tasks / ≤150 LOC prod
- `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): design ×5.7 multiplier is the project-specific band; BDD-heavy batches may run ×4-5
- `work-unit-commits` skill: 12-14 work-unit commits per PR, each ≤400 LOC
- `stacked-to-main-requires-merging-prior-pr-before-next-apply` (#114): N/A here (single PR)
- `openspec/specs/` bootstrap pattern (design D12): new capability spec at `openspec/specs/drift-hardening/spec.md` mirrors observability change #6 precedent
- `decision-code-linking` archive-report #119 S3 precedent: 5-6× strict-TDD multiplier

---

## Task list (22 tasks, single PR, 4 sequential batches)

### Batch A — REQ-55 W6 silence rule + REQ-58 spec/design reconciliation (5 tasks)

#### T1.1 — Modify `daemon.py:handle_apply_progress_event` to suppress summary line when `total == 0 and not unable_to_verify` (REQ-55 W6, D4)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~15 impl + ~80 tests = ~95
- **Files:**
  - `src/flow_engineering/decision_drift.py` (modify — minimal partial migration: rename `graph_unavailable: bool` → `unable_to_verify: bool` + add `unable_reason: str | None`; `@property graph_unavailable` retains 1-release deprecation alias per design D2; ~+10/-2 LOC delta)
  - `src/flow_engineering/daemon.py` (modify — `handle_apply_progress_event` adds `if report.total == 0 and not report.unable_to_verify: return report` (W6 silence rule); preserves unable_to_verify summary line; ~+5/-2 LOC delta)
  - `tests/unit/test_daemon_drift_events.py` (modify — +3 RED fixtures: silence rule fires, unable_to_verify edge case preserves line, mixed-class breakdown still emitted)
- **Dependencies:** none (minimal partial REQ-56 surface: `unable_to_verify` rename + `@property graph_unavailable` alias)
- **Acceptance criteria:**
  - [ ] RED: `test_handle_apply_progress_event_total_zero_not_unable_to_verify_suppresses_summary` fails; `test_handle_apply_progress_event_total_zero_unable_to_verify_emits_summary` fails; `test_handle_apply_progress_event_total_nonzero_emits_class_breakdown` fails
  - [ ] GREEN: W6 silence rule per design D4: when `report.total == 0 and not report.unable_to_verify`, the outer `on_summary` callback is NOT invoked (no stdout summary); JSONL append via `record_drift_event()` (T2.1 wiring) still happens unconditionally for audit trail completeness
  - [ ] GREEN: When `unable_to_verify=True`, the unable_to_verify summary line IS emitted with `unable_reason` (per design §"Still-valid silence rule" edge cases)
  - [ ] GREEN: When `total > 0`, the class breakdown is emitted (STILL_VALID count + non-still-valid counts)
  - [ ] GREEN: `@property graph_unavailable` retained on `DriftReport` for 1 release with `DeprecationWarning` (per design D2 / OQ-1)
  - [ ] GREEN: All existing 947 tests pass without modification
- **Commits:**
  1. `test(unit): RED fixtures for W6 silence rule + unable_to_verify edge case + class breakdown`
  2. `feat(daemon): handle_apply_progress_event suppresses outer summary on still-valid silence (D4)`
  3. `feat(decision_drift): DriftReport.unable_to_verify rename + @property graph_unavailable 1-release alias (REQ-56 partial)`

#### T1.2 — Reconcile archived `decision-reality-drift/spec.md` + `design.md` for REQ-15 event-log + silence contract (DOCS ONLY)

- **Type:** docs
- **TDD phase:** N/A (docs-only — no production code, no commits required)
- **LOC:** ~5 spec + ~10 design = ~15 docs
- **Files:**
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` (modify — REQ-15 daemon seam scenario reconciled with new `unable_to_verify` field name; ~+3/-2 LOC delta)
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` (modify — dataclass type signatures at lines 134-155 reconciled to `unable_to_verify` + `unable_reason`; ~+5/-5 LOC delta)
- **Dependencies:** T1.1 (must establish `unable_to_verify` as canonical field name first)
- **Acceptance criteria:**
  - [ ] GREEN: `archive/2026-06-26-decision-reality-drift/spec.md` REQ-15 scenarios reference `unable_to_verify` (NOT `graph_unavailable`)
  - [ ] GREEN: `archive/2026-06-26-decision-reality-drift/design.md` lines 134-155 show `DriftReport.unable_to_verify: bool` + `unable_reason: str | None` as the canonical shape
  - [ ] GREEN: No production code change; 0 tests (verified via grep)
  - [ ] GREEN: SDD governance invariant preserved (archived = immutable except for carry-forward resolution)
- **Commits:** NONE (docs-only; bundled with T1.4 CHANGELOG commit)

#### T1.3 — Reconcile archived `graph-snapshots/spec.md` + `design.md` for snapshot field names (REQ-58 docs portion)

- **Type:** docs
- **TDD phase:** N/A (docs-only — no production code, no commits required)
- **LOC:** ~3 spec + ~5 design = ~8 docs
- **Files:**
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (modify — REQ-34 `PruneResult` field declaration at line 230 reconciled: `freed_bytes_estimate` → `freed_bytes`; ~+2/-2 LOC delta)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` (modify — `SnapshotMeta` contract block at line 271: `file_size_bytes` → `size_bytes` + add `pinned: bool` retention-pin field documentation; ~+3/-3 LOC delta)
- **Dependencies:** none (parallel to T1.1; both archives edited simultaneously)
- **Acceptance criteria:**
  - [ ] GREEN: `archive/2026-06-27-graph-snapshots/spec.md` line 230 declares `freed_bytes: int` (not `freed_bytes_estimate`)
  - [ ] GREEN: `archive/2026-06-27-graph-snapshots/design.md` line 271 documents `SnapshotMeta.size_bytes: int` + `SnapshotMeta.pinned: bool`
  - [ ] GREEN: Zero production code change (impl at `snapshot_manager.py:100-121 + 209-247` already correct per design §"Files Affected")
  - [ ] GREEN: SDD governance: archived = immutable except for carry-forward resolution
- **Commits:** NONE (docs-only; bundled with T1.4 CHANGELOG commit)

#### T1.4 — Add CHANGELOG v0.8.0-dev section noting upcoming breaking change + v0.6.0 W23 deprecation placeholder

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~15 CHANGELOG
- **Files:**
  - `CHANGELOG.md` (modify — add `## [0.8.0] - in development` section above `[0.7.0]`; placeholder note that REQ-56 dataclass migration + BREAKING section arrive in T4.5; ~+15 LOC delta)
- **Dependencies:** T1.1, T1.2, T1.3 (must reference the partial REQ-56 field rename + REQ-58 spec reconciliation)
- **Acceptance criteria:**
  - [ ] GREEN: `CHANGELOG.md` has `## [0.8.0] - in development` section above `[0.7.0]` with placeholder note
  - [ ] GREEN: Notes the upcoming BREAKING change (REQ-56 dataclass shape migration arriving in T4.5)
  - [ ] GREEN: The v0.6.0 Notes section W23 deprecation entry lands in T2.6 (Batch B); this task creates the v0.8.0-dev placeholder only
- **Commits:**
  1. `docs(changelog): v0.8.0-dev placeholder + reference to upcoming REQ-56 BREAKING`

#### T1.5 — Add `DriftReport.unable_to_verify` accessor smoke tests + migration shim verification

- **Type:** test (verification of T1.1)
- **TDD phase:** GREEN (verification of T1.1 partial migration)
- **LOC:** ~30 tests
- **Files:**
  - `tests/unit/test_decision_drift.py` (modify — +3 RED fixtures for `unable_to_verify` direct access, `@property graph_unavailable` DeprecationWarning capture, `unable_reason: str | None` default `None`; ~+30 LOC delta)
- **Dependencies:** T1.1 (must establish the partial migration)
- **Acceptance criteria:**
  - [ ] GREEN: `DriftReport(unable_to_verify=True, unable_reason="graph_json_missing")` constructs without error
  - [ ] GREEN: `report.unable_to_verify == True` direct field access works
  - [ ] GREEN: `report.graph_unavailable` returns `True` AND emits `DeprecationWarning` with message `"DriftReport.graph_unavailable is deprecated; use unable_to_verify (REQ-56)."`
  - [ ] GREEN: `unable_reason` defaults to `None` when not passed (covers "graph unavailable, no further detail" case)
  - [ ] GREEN: All 947 existing tests still pass (the partial migration is additive on top of the legacy alias)
- **Commits:**
  1. `test(unit): unable_to_verify accessor + graph_unavailable deprecation alias + unable_reason default tests`

---

### Batch B — REQ-55 JSONL writer + REQ-59 W23 + S2 stderr + REQ-58 W25/W26 (6 tasks)

#### T2.1 — Create `src/flow_engineering/drift_event_log.py` with `DriftEventLog` class + append-only writer + 10MB rotation (REQ-55 W5, D3 + D11)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~180 tests = ~330
- **Files:**
  - `src/flow_engineering/drift_event_log.py` (NEW — `record_drift_event(report, *, path=None)` + `iter_drift_events(*, since_iso, change)` + `DEFAULT_PATH` + `ROTATE_BYTES` (10 * 1024 * 1024) + `_utc_iso()` + `_rotate_if_needed()` private helpers; ~150 LOC)
  - `tests/unit/test_drift_event_log.py` (NEW — 5 RED fixtures: rotation at exactly 10 MB, append idempotency, schema `{ts, change, decision_id, binding_id, class, detected_at}`, counter increment, `try/except OSError` disk-full path)
- **Dependencies:** T1.1 (consumes post-partial-migration `DriftReport.unable_to_verify`)
- **Acceptance criteria:**
  - [ ] RED: `test_record_drift_event_writes_one_jsonl_per_finding` fails; `test_record_drift_event_rotates_at_10mb_threshold` fails; `test_record_drift_event_schema_matches_spec` fails; `test_record_drift_event_oserror_on_disk_full_does_not_raise` fails; `test_iter_drift_events_filters_by_change_and_since_iso` fails
  - [ ] GREEN: `record_drift_event(report, *, path=None)` writes one JSON line per finding (post-REQ-56 partial: `decision_id: int`, `scanned_at: str ISO`) with schema `{ts, change, decision_id, binding_id, class, detected_at}` per design §"JSONL append-only writer"
  - [ ] GREEN: `_rotate_if_needed(path)` rotates at `>= ROTATE_BYTES (10 * 1024 * 1024)` to `drift_events.<ISO-no-colons>.jsonl` (lex-sortable) + fresh `drift_events.jsonl`
  - [ ] GREEN: `try/except OSError` wraps the append — on disk full / permission denied, logs WARN to stderr and returns without raising (D11 best-effort, never crashes caller; matches `observability.increment()` policy)
  - [ ] GREEN: `iter_drift_events(*, since_iso, change)` reads JSONL with lex-sortable ISO `ts` filter + exact-match `change` filter
  - [ ] GREEN: Single-threaded assumption per D11 (daemon is single-process Python watchdog loop; no file lock)
- **Commits:**
  1. `test(unit): RED fixtures for record_drift_event + iter_drift_events + 10MB rotation + OSError path`
  2. `feat(drift_event_log): NEW module — record_drift_event + iter_drift_events + 10MB rotation + OSError best-effort (REQ-55 W5)`

#### T2.2 — Wire `daemon.py` to call `DriftEventLog.append()` per finding + `--drift-event-log[=<path>]` CLI flag (REQ-55 W6 + CLI surface)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 impl + ~40 tests = ~70
- **Files:**
  - `src/flow_engineering/daemon.py` (modify — wire `record_drift_event(report)` into `handle_apply_progress_event` AFTER the W6 silence gate; ~+15/-5 LOC delta)
  - `src/flow_engineering/cli.py` (modify — `--drift-event-log[=<path>]` flag (default-on, default path `~/.flow-engineering/drift_events.jsonl`) + `--no-drift-event-log` opt-out on `flow drift daemon` subcommand; ~+15/-5 LOC delta)
  - `tests/unit/test_daemon_drift_events.py` (extend — +2 RED fixtures: `record_drift_event` called after silence gate; `--no-drift-event-log` disables append)
  - `tests/unit/test_cli_watch_drift.py` (extend — +1 RED fixture: `--drift-event-log=<path>` parses correctly + `--no-drift-event-log` opt-out)
- **Dependencies:** T2.1 (`drift_event_log` module must exist)
- **Acceptance criteria:**
  - [ ] RED: `test_handle_apply_progress_event_invokes_record_drift_event_when_findings_present` fails; `test_handle_apply_progress_event_no_driff_event_log_flag_skips_append` fails; `test_cli_watch_drift_event_log_flag_default_on` fails
  - [ ] GREEN: `handle_apply_progress_event` calls `record_drift_event(report)` AFTER `record_drift_summary(report)`; wrapped in `try/except` (defense in depth per D11); respects `--drift-event-log` flag from CLI config
  - [ ] GREEN: `--drift-event-log=<path>` opt-in flag with default path `~/.flow-engineering/drift_events.jsonl`; `--no-drift-event-log` opt-out disables append
  - [ ] GREEN: BDD scenario coverage deferred to T2.3 (focus on unit-level wiring first)
- **Commits:**
  1. `test(unit): RED fixtures for daemon wiring + --drift-event-log CLI flag`
  2. `feat(daemon): wire record_drift_event into handle_apply_progress_event (REQ-55 W6 wiring)`
  3. `feat(cli): --drift-event-log[=<path>] flag + --no-drift-event-log opt-out (REQ-55 CLI surface)`

#### T2.3 — Extend `tests/bdd/req15_drift_daemon.feature` with 2 JSONL event-log scenarios (REQ-55 BDD)

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 BDD scenarios + ~30 step glue = ~110
- **Files:**
  - `tests/bdd/req15_drift_daemon.feature` (modify — +2 BDD scenarios: REQ-55 scenario #1 JSONL line per finding + REQ-55 scenario #2 JSONL silent on still-valid)
  - `tests/bdd/test_decision_reality_drift_steps.py` (extend — +30 LOC step glue for the 2 new scenarios; reuse existing step defs from `req9_drift_detection.feature` and `req15_drift_daemon.feature`)
- **Dependencies:** T2.1, T2.2 (JSONL writer + daemon wiring must be GREEN)
- **Acceptance criteria:**
  - [ ] RED: `Scenario: REQ-55 — Daemon emits one JSONL line per finding with required keys` fails; `Scenario: REQ-55 — Daemon emits no JSONL line on still-valid silence` fails
  - [ ] GREEN: Scenario #1 verbatim from spec §"Batch B / REQ-55 / BDD Scenarios":
    - Given 3 bindings (2 STALE + 1 MISSING) + fresh `drift_events.jsonl`
    - When `flow drift daemon --drift --drift-event-log` runs one tick
    - Then 3 JSONL lines present + each line has keys `ts, change, decision_id, binding_id, class, detected_at` + ts is ISO 8601 UTC Z-suffixed + decision_id is int + class is one of `STALE, MISSING, ORPHAN, UNABLE_TO_VERIFY` (NOT `STILL_VALID`)
    - And counter `drift_event_log_total{change="obs"}` increments by 3
  - [ ] GREEN: Scenario #2 verbatim from spec §"Batch B / REQ-55 / BDD Scenarios":
    - Given 3 bindings (all STILL_VALID) + fresh `drift_events.jsonl`
    - When daemon runs one tick
    - Then 0 JSONL lines + outer `drift: obs 0 findings (no classes)` line SUPPRESSED (W6 silence rule)
    - And counter `drift_event_log_total{change="obs"}` does NOT increment
  - [ ] GREEN: Step glue uses business-domain Given/When/Then phrasing (D5 quality gate)
- **Commits:**
  1. `test(bdd): req15_drift_daemon.feature +2 JSONL scenarios + step glue extension`

#### T2.4 — Verify `SnapshotMeta.size_bytes` / `pinned` / `PruneResult.freed_bytes` impl already correct (DOCS-ONLY verification)

- **Type:** docs (verification)
- **TDD phase:** N/A (verification only)
- **LOC:** ~5 docs (already done in T1.3) + 0 code
- **Files:** NONE — verification task only
- **Dependencies:** T1.3 (archived spec/design docs reconciliation)
- **Acceptance criteria:**
  - [ ] GREEN: Confirmed via grep on `src/flow_engineering/snapshot_manager.py`: `SnapshotMeta.size_bytes` field exists at line ~100; `SnapshotMeta.pinned` field exists at line ~120; `PruneResult.freed_bytes` field exists at line ~209
  - [ ] GREEN: Zero production code change (impl already correct per design §"Files Affected" + design §"Module/File Layout")
  - [ ] GREEN: The grep verification is documented in the PR description for reviewer confidence
- **Commits:** NONE (verification documented in PR description)

#### T2.5 — Add stderr WARN to `_write_back_findings` for skipped non-int `decision_id` (S2, D8)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~20 impl + ~50 tests = ~70
- **Files:**
  - `src/flow_engineering/cli.py` (modify — at end of `_write_back_findings(report)`, compute `skipped_total = sum(1 for f in report.findings if not isinstance(int(f.decision_id), int))`; when `skipped_total >= _get_skip_warn_threshold()`, print `WARN: drift write-back skipped {N} non-int decision_ids` to `sys.stderr` ONCE per batch; add `_get_skip_warn_threshold()` helper that parses `FLOW_DRIFT_SKIP_WARN_THRESHOLD` env var (default 3; 0 = always; -1 = never; parse error → 3); ~+20/-2 LOC delta)
  - `tests/unit/test_cli_drift.py` (extend — +2 RED fixtures: stderr WARN captured via `capsys` when `skipped_total >= threshold`; threshold=0 emits every batch; threshold=-1 emits never)
- **Dependencies:** T1.1 (consumes post-partial-migration `DriftReport`)
- **Acceptance criteria:**
  - [ ] RED: `test_write_back_findings_emits_stderr_warn_on_threshold` fails; `test_get_skip_warn_threshold_default_3` fails
  - [ ] GREEN: Per design D8: stderr WARN emitted ONCE per batch (NOT per skipped row) when `skipped_total >= threshold`; threshold default 3
  - [ ] GREEN: `FLOW_DRIFT_SKIP_WARN_THRESHOLD=0` → WARN every batch with `skipped_total > 0`
  - [ ] GREEN: `FLOW_DRIFT_SKIP_WARN_THRESHOLD=-1` → WARN never
  - [ ] GREEN: `FLOW_DRIFT_SKIP_WARN_THRESHOLD=garbage` → falls back to default 3 (parse error tolerance)
  - [ ] GREEN: WARN is additive on top of existing silent-skip behavior (no behavior change for the write itself)
- **Commits:**
  1. `test(unit): RED fixtures for S2 stderr WARN + threshold env var + per-batch cadence`
  2. `feat(cli): _write_back_findings stderr WARN + _get_skip_warn_threshold helper (REQ-59 S2, D8)`

#### T2.6 — Add CHANGELOG v0.6.0 Notes section entry for W23 dual-name coexistence

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~10 CHANGELOG
- **Files:**
  - `CHANGELOG.md` (modify — add 3-line entry to `## [0.6.0]` Notes section documenting `snapshot_pruned_total` ↔ `snapshot_prune_total` coexistence + REQ-37 `--domain snapshot` filter recommendation; ~+10 LOC delta)
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] GREEN: `CHANGELOG.md` `## [0.6.0]` Notes section has W23 coexistence entry
  - [ ] GREEN: Recommends REQ-37 `--domain snapshot` filter (which matches BOTH names by `snapshot_` prefix per observability D5)
  - [ ] GREEN: Documents optional `sed -i 's/snapshot_pruned_total/snapshot_prune_total/g' ~/.flow-engineering/metrics.jsonl` one-line migration
  - [ ] GREEN: No runtime WARN (CHANGELOG-only per design D7 / OQ-7)
- **Commits:**
  1. `docs(changelog): v0.6.0 Notes section W23 coexistence entry + REQ-37 filter recommendation`

---

### Batch C — REQ-57 BDD coverage: 21 NEW scenarios across 6 feature files (6 tasks)

#### T3.1 — Create `tests/bdd/req10_drift_cli.feature` with 9 scenarios for `flow drift <change>` CLI surface

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~250 BDD scenarios + ~150 step glue = ~400
- **Files:**
  - `tests/bdd/req10_drift_cli.feature` (NEW — 9 scenarios verbatim from spec §"Batch C / REQ-10 / BDD Scenarios": text default, `--json`, `--include-obsolete`, default excludes OBSOLETE, `--since=<iso>` text, `--since=<iso> --json`, `--write-back`, `--graph-json=<path>`, unknown change name + exit 3)
  - `tests/bdd/test_req10_drift_cli_steps.py` (NEW — step glue per design D10 per-REQ split; ~150 LOC; uses `tmp_path` + `CliRunner` + `InMemoryBackend` seed pattern from `test_graph_snapshots_steps.py`)
- **Dependencies:** T1.1, T1.5 (consume `unable_to_verify` field)
- **Acceptance criteria:**
  - [ ] RED: All 9 scenarios fail (no `flow` CLI surface yet bound to Gherkin)
  - [ ] GREEN: All 9 scenarios verbatim from spec §"Batch C / REQ-10" — business-domain Given/When/Then phrasing (D5 quality gate: NOT unit-test phrasing like "Given a fixture dict X"; spot-checked by sdd-verify Step 6b)
  - [ ] GREEN: Step glue translates business-domain language to existing pytest fixtures (`@scenario` + `@given`/`@when`/`@then`); ~150 LOC
  - [ ] GREEN: Each scenario uses `json.loads(stdout)` for JSON assertions (NOT substring matches — per spec §"Edge cases / error modes")
- **Commits:**
  1. `test(bdd): req10_drift_cli.feature 9 scenarios + test_req10_drift_cli_steps.py step glue`

#### T3.2 — Create `tests/bdd/req11_drift_exit.feature` with 3 scenarios for exit codes (0/1/2)

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~90 BDD scenarios + ~80 step glue = ~170
- **Files:**
  - `tests/bdd/req11_drift_exit.feature` (NEW — 3 scenarios verbatim from spec §"Batch C / REQ-11 / BDD Scenarios": exit 0 still-valid, exit 1 stale, exit 2 unable_to_verify)
  - `tests/bdd/test_req11_drift_exit_steps.py` (NEW — step glue per design D10; ~80 LOC)
- **Dependencies:** T3.1 (shares business-domain language patterns)
- **Acceptance criteria:**
  - [ ] RED: All 3 scenarios fail
  - [ ] GREEN: All 3 scenarios verbatim from spec §"Batch C / REQ-11" — exit-code assertions via `result.exit_code` (NOT stdout substring)
  - [ ] GREEN: Step glue translates exit-code expectations to `CliRunner.invoke(...).exit_code`
- **Commits:**
  1. `test(bdd): req11_drift_exit.feature 3 scenarios + test_req11_drift_exit_steps.py step glue`

#### T3.3 — Create `tests/bdd/req12_drift_counters.feature` with 3 scenarios for 8 `drift_*_total` counters via `record_drift_summary`

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~90 BDD scenarios + ~80 step glue = ~170
- **Files:**
  - `tests/bdd/req12_drift_counters.feature` (NEW — 3 scenarios verbatim from spec §"Batch C / REQ-12 / BDD Scenarios": 8 counters emitted per scan, idempotent on repeat calls, `drift_unable_to_verify_total` increments on `unable_to_verify=True`)
  - `tests/bdd/test_req12_drift_counters_steps.py` (NEW — step glue per design D10; ~80 LOC)
- **Dependencies:** T1.1 (consumes `unable_to_verify` field for the 3rd scenario)
- **Acceptance criteria:**
  - [ ] RED: All 3 scenarios fail
  - [ ] GREEN: Scenario 1: `DriftReport(3 findings: 1 STILL_VALID + 1 STALE + 1 MISSING)` + `record_drift_summary(report)` → 1 event each for `drift_invoked_total`, `drift_still_valid_total`, `drift_stale_total`, `drift_missing_total`, etc. (total 8 counter events)
  - [ ] GREEN: Scenario 2: same report called twice → 2 events (NOT 1; helper increments per-call)
  - [ ] GREEN: Scenario 3: `DriftReport(unable_to_verify=True, unable_reason="graph_json_missing")` → 1 event for `drift_unable_to_verify_total{reason="graph_json_missing"}`
- **Commits:**
  1. `test(bdd): req12_drift_counters.feature 3 scenarios + test_req12_drift_counters_steps.py step glue`

#### T3.4 — Create `tests/bdd/req13_drift_metadata.feature` with 3 scenarios for `update_observation_metadata`

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~90 BDD scenarios + ~80 step glue = ~170
- **Files:**
  - `tests/bdd/req13_drift_metadata.feature` (NEW — 3 scenarios verbatim from spec §"Batch C / REQ-13 / BDD Scenarios": append drift metadata, idempotent key overwrite, unknown observation_id raises `ObservationNotFoundError`)
  - `tests/bdd/test_req13_drift_metadata_steps.py` (NEW — step glue per design D10; ~80 LOC)
- **Dependencies:** none (covers REQ-13 metadata helper)
- **Acceptance criteria:**
  - [ ] RED: All 3 scenarios fail
  - [ ] GREEN: All 3 scenarios verbatim from spec §"Batch C / REQ-13"
- **Commits:**
  1. `test(bdd): req13_drift_metadata.feature 3 scenarios + test_req13_drift_metadata_steps.py step glue`

#### T3.5 — Create `tests/bdd/req14_drift_resilience.feature` with 4 scenarios for non-breaking behavior

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~120 BDD scenarios + ~100 step glue = ~220
- **Files:**
  - `tests/bdd/req14_drift_resilience.feature` (NEW — 4 scenarios verbatim from spec §"Batch C / REQ-14 / BDD Scenarios": per-row IOError doesn't crash, read-only by default, partial write-back success, graph_unavailable helpful error)
  - `tests/bdd/test_req14_drift_resilience_steps.py` (NEW — step glue per design D10; ~100 LOC)
- **Dependencies:** T1.1 (consumes `unable_to_verify` for scenario 4)
- **Acceptance criteria:**
  - [ ] RED: All 4 scenarios fail
  - [ ] GREEN: All 4 scenarios verbatim from spec §"Batch C / REQ-14" — covers resilience paths (per-row error isolation, read-only default, partial success, helpful error)
- **Commits:**
  1. `test(bdd): req14_drift_resilience.feature 4 scenarios + test_req14_drift_resilience_steps.py step glue`

#### T3.6 — Create `tests/bdd/req16_skill_prose.feature` with 2 scenarios for SKILL.md drift detection hook + extend `test_decision_reality_drift_steps.py`

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~60 BDD scenarios + ~60 step glue + ~400 extended step glue = ~520
- **Files:**
  - `tests/bdd/req16_skill_prose.feature` (NEW — 2 scenarios verbatim from spec §"Batch C / REQ-16 / BDD Scenarios": sdd-verify Step 6a grep + drift detection hook references decision-reality-drift)
  - `tests/bdd/test_req16_skill_prose_steps.py` (NEW — step glue per design D10; ~60 LOC; uses `Path.exists` + `Path.read_text` + `re.search` for the SKILL.md grep)
  - `tests/bdd/test_decision_reality_drift_steps.py` (modify — EXTEND (NOT split, per design D10 note) with shared step glue for REQ-15 daemon JSONL scenarios from T2.3 + any cross-feature glue; ~+400 LOC; conservative — split into per-REQ files IF the file exceeds 1 000 LOC post-batch)
- **Dependencies:** T2.3 (REQ-15 daemon JSONL scenarios must exist for shared glue)
- **Acceptance criteria:**
  - [ ] RED: All 2 scenarios fail
  - [ ] GREEN: Scenario 1: SKILL.md file exists + sdd-verify Step 6a runs grep → match line contains `"drift"` + sdd-verify exits 0
  - [ ] GREEN: Scenario 2: grep match references `REQ-9` OR `openspec/changes/archive/2026-06-26-decision-reality-drift/`
  - [ ] GREEN: `test_decision_reality_drift_steps.py` grows by ≤400 LOC; if post-batch the file exceeds 1 000 LOC, SPLIT into per-REQ step glue per design D10 risk mitigation
- **Commits:**
  1. `test(bdd): req16_skill_prose.feature 2 scenarios + test_req16_skill_prose_steps.py step glue`
  2. `test(bdd): extend test_decision_reality_drift_steps.py with shared glue for REQ-15 JSONL scenarios`

---

### Batch D — REQ-56 dataclass migration + CHANGELOG v0.8.0 + SKILL.md + pyproject bump + spec bootstrap (5 tasks)

#### T4.1 — Migrate `Finding` dataclass: `decision_id: int` + `__post_init__` str coercion + DeprecationWarning (REQ-56 W8 part 1, D2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 impl + ~80 tests = ~110
- **Files:**
  - `src/flow_engineering/decision_drift.py` (modify — `Finding.decision_id: int` (was implicit `str`); add `__post_init__` that accepts legacy numeric `str` inputs and coerces via `int()` with `DeprecationWarning`; non-numeric `str` raises `ValueError`; ~+25/-5 LOC delta)
  - `tests/unit/test_decision_drift.py` (modify — +4 RED fixtures: `decision_id=42` (int) no warning; `decision_id="42"` (numeric str) coerced + `DeprecationWarning`; `decision_id="not-a-number"` raises `ValueError`; round-trip preserves int after coercion)
- **Dependencies:** T1.1, T1.5 (uses the partial migration as the baseline)
- **Acceptance criteria:**
  - [ ] RED: All 4 RED fixtures fail
  - [ ] GREEN: `Finding(decision_id=42, ...)` constructs without warning (post-migration canonical)
  - [ ] GREEN: `Finding(decision_id="42", ...)` constructs with coerced `decision_id=42` + emits `DeprecationWarning` with message `"Finding.decision_id: str is deprecated; pass int (REQ-56)."`
  - [ ] GREEN: `Finding(decision_id="not-a-number", ...)` raises `ValueError` with message `"decision_id must be int or numeric str, got 'not-a-number'"`
  - [ ] GREEN: `Finding.__post_init__` coercion is removed in v1.0 (1-release migration per design D2)
- **Commits:**
  1. `test(unit): RED fixtures for Finding.decision_id int + __post_init__ str coercion + ValueError`
  2. `feat(decision_drift): Finding.decision_id int + __post_init__ str coercion + DeprecationWarning (REQ-56 W8 part 1)`

#### T4.2 — Migrate `DriftReport` dataclass: `scanned_at: str ISO` + `unable_to_verify` + `unable_reason` + `from_scanned()` + `@property graph_unavailable` alias (REQ-56 W8 part 2, D2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~40 impl + ~120 tests = ~160
- **Files:**
  - `src/flow_engineering/decision_drift.py` (modify — extend the T1.1 partial migration: add `from_scanned(*, change_name, scanned_at: float | str, graph_mtime, unable_to_verify, unable_reason, ...)` classmethod that accepts legacy `float` epoch inputs and coerces to ISO `str` via `datetime.fromtimestamp(..., tz=UTC).strftime(...)` (no warning — it IS the explicit migration path); `DriftReport.scanned_at: str` ISO 8601 UTC; `DriftReport.graph_mtime: str | None` ISO; `@property graph_unavailable` retained per T1.1; ~+35/-5 LOC delta)
  - `tests/unit/test_decision_drift.py` (extend — +4 RED fixtures: `scanned_at` str ISO direct; `from_scanned(scanned_at=1751000000.0)` coerces to ISO `"2025-06-27T16:53:20Z"`; `from_scanned(scanned_at="2026-06-27T12:34:56Z")` no-op; `from_scanned` does NOT emit DeprecationWarning)
- **Dependencies:** T1.1 (T1.1 partial migration establishes the `unable_to_verify` rename baseline)
- **Acceptance criteria:**
  - [ ] RED: All 4 RED fixtures fail
  - [ ] GREEN: `DriftReport(scanned_at="2026-06-27T12:34:56Z")` constructs directly without warning
  - [ ] GREEN: `DriftReport.from_scanned(scanned_at=1751000000.0)` coerces to ISO `"2025-06-27T16:53:20Z"` (no warning — explicit migration path)
  - [ ] GREEN: `from_scanned(scanned_at="2026-06-27T12:34:56Z")` is no-op (str input passes through)
  - [ ] GREEN: `from_scanned()` is removed in v1.0 (1-release migration per design D2)
- **Commits:**
  1. `test(unit): RED fixtures for DriftReport.scanned_at str ISO + from_scanned() float coercion + round-trip`
  2. `feat(decision_drift): DriftReport.scanned_at str ISO + from_scanned() classmethod + @property graph_unavailable (REQ-56 W8 part 2)`

#### T4.3 — Update `classify_binding(ref, graph_nodes)` to 2-arg signature (REQ-56 W8 part 3, OQ-10 clean break)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 impl + ~60 tests = ~90
- **Files:**
  - `src/flow_engineering/decision_drift.py` (modify — `classify_binding(ref: BindingRef, graph_nodes: dict[str, GraphNode])` 2-arg (was 3-arg `classify_binding(ref, graph_nodes, current_id_map)`); `current_id_map` is derived INSIDE from `{node.id: (node.file, node.line, node.label) for node in graph_nodes}`; 3-arg callers get `TypeError` (clean break per design D2 / OQ-10); ~+25/-15 LOC delta)
  - `tests/unit/test_decision_drift.py` (extend — +2 RED fixtures: 2-arg `classify_binding(ref, graph_nodes)` for STALE_LOCATION classification; 3-arg `classify_binding(ref, graph_nodes, current_id_map)` raises `TypeError`)
- **Dependencies:** T4.1, T4.2 (must complete Finding + DriftReport migration first)
- **Acceptance criteria:**
  - [ ] RED: All 2 RED fixtures fail
  - [ ] GREEN: `classify_binding(ref, graph_nodes)` 2-arg signature works for all 5 drift classes (STILL_VALID, LABEL_DRIFT, STALE_LOCATION, STALE_ID, UNABLE_TO_VERIFY); current_id_map derived INSIDE in O(N) at function entry
  - [ ] GREEN: 3-arg `classify_binding(ref, graph_nodes, current_id_map)` raises `TypeError` (clean break per OQ-10)
  - [ ] GREEN: No optional 3rd-arg compat (silent fall-through would mask migration errors)
  - [ ] GREEN: All existing callers in `daemon.py` + `cli.py` + `observability.py` updated to 2-arg (handled in T4.4)
- **Commits:**
  1. `test(unit): RED fixtures for classify_binding 2-arg signature + 3-arg TypeError clean break`
  2. `feat(decision_drift): classify_binding(ref, graph_nodes) 2-arg signature + current_id_map derived inside (REQ-56 W8 part 3)`

#### T4.4 — Update all callers in `daemon.py` + `cli.py` + `observability.py` to use new signatures + remove T1.1's interim `unable_to_verify` partial migration smoke

- **Type:** code (call-site refactor)
- **TDD phase:** GREEN (driven by T4.1..T4.3 RED → GREEN)
- **LOC:** ~20 impl across 3 files
- **Files:**
  - `src/flow_engineering/daemon.py` (modify — call sites in `handle_apply_progress_event` updated for new `unable_to_verify` semantics + `int(finding.decision_id)` no longer needs `try/except` for legacy str coercion; ~+5/-10 LOC delta)
  - `src/flow_engineering/cli.py` (modify — `_write_back_findings` updates for `int(finding.decision_id)` direct access (post-`__post_init__` coercion means only truly non-numeric str inputs reach the skip path); ~+10/-15 LOC delta)
  - `src/flow_engineering/observability.py` (modify — `record_drift_event()` helper now passes `decision_id` as int directly (post-REQ-56); +5 LOC delta)
- **Dependencies:** T4.1, T4.2, T4.3 (all dataclass migrations complete)
- **Acceptance criteria:**
  - [ ] GREEN: All callers updated; no `DeprecationWarning` raised on the new canonical paths
  - [ ] GREEN: 3-arg `classify_binding` callers updated to 2-arg (via grep + manual verification)
  - [ ] GREEN: All existing 947 tests pass without modification (verified via `uv run pytest`)
  - [ ] GREEN: `ruff check` clean on all changed files
- **Commits:**
  1. `refactor: update daemon.py + cli.py + observability.py callers for new dataclass signatures (REQ-56 cascade)`

#### T4.5 — CHANGELOG v0.8.0 entry + 6 SKILL.md runtime updates + pyproject 0.7.0→0.8.0 bump + `openspec/specs/drift-hardening/spec.md` bootstrap + 4 closeout unit/grep tests

- **Type:** docs + integration
- **TDD phase:** N/A (docs) + RED → GREEN (closeout tests)
- **LOC:** ~50 CHANGELOG + ~80 SKILL.md (6 × ~13) + ~1 pyproject + ~250 spec + ~400 closeout tests = ~780
- **Files:**
  - `CHANGELOG.md` (modify — add `## [0.8.0] - <date>` section above `[0.8.0] - in development` placeholder from T1.4; list all 5 REQs with one-line summaries; add `BREAKING:` section with 4 migration steps per spec §"Batch D acceptance criteria"; ~+50 LOC delta)
  - `pyproject.toml` (modify — `version = "0.8.0"` per design D9 + spec §"Batch D acceptance criteria"; ~+1/-1 LOC delta)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify — +drift-hardening hook prose; ~+13 LOC)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify — +drift-hardening hook prose; ~+13 LOC)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify — +drift-hardening hook prose; ~+13 LOC)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify — +drift-hardening hook prose; ~+13 LOC)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify — +drift-hardening hook prose + BDD Step 6b cluster-count assertion; ~+20 LOC)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify — +drift-hardening hook prose; ~+13 LOC)
  - `openspec/specs/drift-hardening/spec.md` (NEW — capability spec cataloging REQ-55..59 with all 21 BDD scenarios + dataclass shape contract + counter catalog; bootstraps `openspec/specs/` baseline mirroring observability change #6 pattern; ~+250 LOC)
  - `tests/unit/test_changelog_drift_hardening.py` (NEW — CHANGELOG v0.8.0 entry exists + `BREAKING:` section has 4 steps + v0.6.0 Notes has W23 entry; ~+100 LOC)
  - `tests/unit/test_pyproject_version.py` (NEW — `pyproject.toml` version == "0.8.0"; ~+20 LOC)
  - `tests/unit/test_skill_md_drift_hooks.py` (NEW — all 6 SKILL.md files have the drift-hardening hook prose section; ~+120 LOC)
  - `tests/bdd/test_drift_hardening_steps.py` (NEW — BDD Step 6b cluster-count assertion: verifies 21 new scenarios across the 6 new feature files; ~+160 LOC)
- **Dependencies:** T4.1, T4.2, T4.3, T4.4 (all REQ-56 dataclass migrations complete)
- **Acceptance criteria:**
  - [ ] GREEN: `CHANGELOG.md` `## [0.8.0]` entry lists all 5 REQs (REQ-55/56/57/58/59) + `BREAKING:` section with 4 migration steps (per spec §"Batch D acceptance criteria"): `decision_id: str→int`, `scanned_at: float→str`, `graph_unavailable→unable_to_verify+unable_reason`, `classify_binding` 3→2 args
  - [ ] GREEN: `pyproject.toml` `version = "0.8.0"` (1 line change; per design D9 SemVer minor bump for public API break)
  - [ ] GREEN: All 6 SKILL.md files have the drift-hardening hook prose section (~13 LOC each, ~80 total; mirror observability change #6 pattern)
  - [ ] GREEN: `sdd-verify` SKILL.md gains BDD Step 6b cluster-count assertion: verifies 21 new scenarios in 6 NEW feature files
  - [ ] GREEN: `openspec/specs/drift-hardening/spec.md` exists + catalogs REQ-55..59 with all 21 BDD scenarios + dataclass shape contract + counter catalog
  - [ ] GREEN: All closeout tests pass: `test_changelog_drift_hardening.py` (CHANGELOG structure), `test_pyproject_version.py` (version == "0.8.0"), `test_skill_md_drift_hooks.py` (6 SKILL.md files), `test_drift_hardening_steps.py` (BDD Step 6b cluster-count)
  - [ ] GREEN: All 947 existing tests + 21 new BDD scenarios + 30+ new unit tests pass; `ruff check` clean on all changed files
- **Commits:**
  1. `docs(release): CHANGELOG v0.8.0 entry + BREAKING section + 6 SKILL.md drift-hardening hooks + pyproject bump`
  2. `docs(spec): bootstrap openspec/specs/drift-hardening/spec.md capability catalog (mirrors observability change #6)`
  3. `test(unit): CHANGELOG v0.8.0 structure + pyproject version + 6 SKILL.md hook presence tests`
  4. `test(bdd): Step 6b cluster-count assertion — verifies 21 new scenarios in 6 NEW feature files`

---

## Open follow-ups for sdd-archive (after PR#1 merge)

- Spec catalog baseline retro-fill for prior capability specs (REQ-9..16, REQ-28..34)
- MEMORY.md/AGENTS.md update for new flow drift event log workflow
- Cross-impact verification for all 5 prior changes (decision-reality-drift, vector-semantic-search, cross-project-federation, graph-snapshots, observability)
- README updates for new `--drift-event-log` flag + `drift_events.jsonl` audit trail
- v1.0 follow-up change for: REQ-55 read-side `flow drift events` CLI, JSONL rotation env vars, `FindingLegacy` removal, `Finding.__post_init__` removal, `@property graph_unavailable` removal, `from_scanned()` removal, mypy strict adapter
- Cross-impact verification: prompt-registry change #7 archive must precede this change's apply (REQ-55 numbering preservation per Engram #183 + #201)

---

## Coordination notes

- **MANDATORY**: prompt-registry change #7 MUST archive BEFORE drift-hardening apply starts (preserves REQ-55..59 numbering; REQ-45..54 reserved for prompt-registry per Engram #183 + #201)
- **Apply sequencing**: A → B → C → D is strict (per design D12). Each batch merges before the next starts.
- **Per-batch commit splits** per `work-unit-commits` skill: 12-14 commits total across 4 batches (3-4 per batch), each ≤400 LOC
- **Single-PR strategy** per proposal #223 + design #1497-1513: ~9 700 realistic LOC just below observability's ~10 910 chained-PR threshold

---

## Session: flow-engineering-sdd-tasks-drift-hardening-2026-06-27
## Project: flow-engineering
## Topic: sdd/drift-hardening/tasks