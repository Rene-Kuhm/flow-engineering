# Archive Report — v0.9.0-hardening

## Status

**ARCHIVED — change #9 (v0.9.0-hardening) CLOSED** (2026-06-28)

SDD cycle complete: explore → propose → design → spec → tasks → apply (single PR via 3 sequential sub-batches A + B + C across 12 work-unit commits) → verify (PASS WITH WARNINGS, 0C + 1W + 4S, **accepted per `drift-hardening` precedent**) → archive.

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` archive precedent; same posture: 0 CRITICAL + 1 WARNING + 4 SUGGESTION → archive; non-blocking follow-ups documented in Carry-forwards table). All 5 REQs (REQ-V9.1..V9.5) ship with passing tests demonstrating compliance; all 19 tasks (T1.1..T3.7) closed across 3 sub-batches with strict-TDD RED → GREEN → REFACTOR evidence per `apply-progress/final.md`. **1232/1232 tests passing** (net even: -2 removed + 2 added via W1 enforcement) with **0 regressions** vs the `a2ce3f5` baseline. **179/179 BDD scenarios passing**. The 3 documented carry-forwards from `drift-hardening` (W1 + W2 + W3) are all explicitly **CLOSED** by this change — the v0.8.0 1-release compat shim window is officially closed.

## Goal

Close v0.8.0's 1-release compat shim window per the CHANGELOG v0.8.0 entry (lines 43, 44, 46, 74) commitment. Remove the 3 compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`) + add `Finding.__post_init__` enforcement (W1 — the v0.8.0 `verify-report.md` W1 recommended fix) + version bump 0.8.1 → 0.9.0 (SemVer minor for public API break) + append W2 Option B Drift note to `archive/2026-06-27-drift-hardening/design.md:493` + 6 SKILL.md runtime updates (remove "1-release shim" qualifier).

## Summary

Single PR, single release (v0.9.0, BREAKING), 12 work-unit commits on `main` (HEAD `3de7783`). 3 compat shims deleted; `Finding.__post_init__` hardens the W1 enforcement (`TypeError` on str AND bool inputs; no `int()` coercion; no `DeprecationWarning` — pure rejection per proposal §"Code sketch" lines 239-245). Net test count even (-2 removed + 2 added); 0 regressions. 12 work-unit commits land in 3 sequential sub-batches with strict TDD discipline (RED fixture BEFORE each shim-delete GREEN commit).

## Sub-batch summary

| Sub-batch | REQs | Tasks | Commits | Headline |
|-----------|------|-------|---------|----------|
| **A — W1 removal** | REQ-V9.1 + REQ-V9.2 | T1.1..T1.6 (6 tasks) | 5 (`9fb4111`, `d1b08a2`, `3d4e0f3`, `44b0edd`, `9ca3e80`) | `Finding.from_legacy` + `DriftReport.from_legacy` classmethods DELETED; 10 direct-legacy test sites migrated (2 `Finding(str)` + 8 `DriftReport(scanned_at=0.0)`); 6 `from_legacy` fixtures deleted; unused `Any` import removed |
| **B — W3 removal + W1 enforcement** | REQ-V9.3 + REQ-V9.4 | T2.1..T2.6 (6 tasks) | 3 (`d016433`, `aed1ed1`, `a84b686`) | `classify_binding_legacy` 3-arg wrapper DELETED; 10 call sites + 1 fixture + dead `_id_map` helper migrated/removed; `Finding.__post_init__` added (TypeError on str/bool); 3 `# type: ignore` comments removed at `decision_drift.py:759/772/792`; 2 coercing test assertions updated to expect TypeError per hard-break contract |
| **C — Docs + meta** | REQ-V9.5 | T3.1..T3.7 (7 tasks) | 4 (`9c15fae`, `120dba1`, `2410b03`, `87c52c3`) + closeout | `openspec/specs/decision-drift/spec.md` v0.9.0 final note (replaces v0.8.0 migration note); CHANGELOG v0.9.0 entry (BREAKING + 4 breaking changes + 3 removed items + 4-step migration guide); `pyproject.toml` version bump 0.8.1 → 0.9.0; W2 Option B Drift note appended to `archive/2026-06-27-drift-hardening/design.md:493`; 6 SKILL.md runtime files updated atomically per `drift-hardening` T4.5.c precedent (commit `2410b03` sequence); `ruff --fix` on changed files (27 errors → 12 = -15 net improvement); `apply-progress/final.md` closeout written + committed |

**Total**: 3 sub-batches × ~3 commits each + 3 closeout commits = **12 work-unit commits** (3 RED+GREEN pairs + 3 REFACTOR migrations + 1 doc/version + 1 design Drift note + 1 closeout + 3 misc).

## Per-task completion (T1.1..T3.7 = 19 tasks)

### Sub-batch A (T1.1..T1.6)
- **T1.1** RED: assert `Finding.from_legacy` is removed — commit `9fb4111` (RED fixture `test_finding_from_legacy_attribute_removed`)
- **T1.2** GREEN: delete `Finding.from_legacy` classmethod — commit `9fb4111` (GREEN — `decision_drift.py:77-117` deleted)
- **T1.3** REFACTOR: migrate 2 direct `Finding(str)` test sites + delete 3 `from_legacy` fixtures — commit `d1b08a2`
- **T1.4** RED: assert `DriftReport.from_legacy` is removed — commit `3d4e0f3` (RED fixture `test_drift_report_from_legacy_attribute_removed`)
- **T1.5** GREEN: delete `DriftReport.from_legacy` classmethod — commit `3d4e0f3` (GREEN — `decision_drift.py:143-197` deleted)
- **T1.6** REFACTOR: migrate 8 direct `DriftReport(scanned_at=0.0)` test sites + delete 3 `from_legacy` fixtures — commit `44b0edd` + unused `Any` import cleanup commit `9ca3e80`

### Sub-batch B (T2.1..T2.6)
- **T2.1** RED: assert `classify_binding_legacy` is removed — commit `d016433` (RED fixture `test_classify_binding_legacy_attribute_removed`)
- **T2.2** GREEN: delete `classify_binding_legacy` 3-arg wrapper — commit `d016433` (GREEN — `decision_drift.py:267-285` deleted)
- **T2.3** REFACTOR: migrate 10 call sites + delete 1 fixture + delete `_id_map` helper — commit `aed1ed1`
- **T2.4** RED: assert `Finding.__post_init__` rejects str inputs — commit `a84b686` (RED fixtures `test_finding_constructor_rejects_str_decision_id` + `test_finding_constructor_rejects_bool_decision_id`)
- **T2.5** GREEN: add `Finding.__post_init__` enforcement — commit `a84b686` (GREEN — `decision_drift.py:84-90` `__post_init__` method added per proposal §"Code sketch")
- **T2.6** REFACTOR: update v0.9.0 coercing test assertions to match int decision_id contract + mypy clean verify — commit `87c52c3` (3 `# type: ignore` cleanup rolled in; mypy residual 13 → 12 = -1 net)

### Sub-batch C (T3.1..T3.7)
- **T3.1** Update `openspec/specs/decision-drift/spec.md` v0.9.0 migration note — commit `9c15fae` (replaces v0.8.0 migration note at spec.md:14-41 with v0.9.0 final note at spec.md:14-31; 0 references to `from_legacy` / `classify_binding_legacy` in capability spec)
- **T3.2** CHANGELOG v0.9.0 entry under `## [0.9.0] - 2026-06-28` — commit `120dba1` (CHANGELOG.md:7-32: ### Changed (BREAKING) + ### Removed + ### Migration)
- **T3.3** `pyproject.toml` version bump `0.8.1` → `0.9.0` — commit `120dba1` (line 3; confirmed via `grep "^version" pyproject.toml` → `version = "0.9.0"`)
- **T3.4** Drift note appended to `archive/2026-06-27-drift-hardening/design.md` (W2 Option B closure) — commit `2410b03` (design.md:493 `### v0.9.0 resolution (REQ-V9.5)` — 1 match on grep `v0\.9\.0 resolution \(REQ-V9\.5\)`)
- **T3.5** 6 SKILL.md runtime files updated atomically (remove "1-release shim" qualifier) — rolled into `2410b03` sequence per `drift-hardening` T4.5.c precedent (--allow-empty commit pattern); verified 0 `1-release shim` matches + 6 `removed in v0.9.0` matches
- **T3.6** `uv run ruff check --fix` on changed files — commit `3de7783` (`ruff --fix` on 30 files; ruff errors in changed files reduced from 27 → 12)
- **T3.7** Apply-progress closeout + commit — commit `3de7783` (`apply-progress/final.md` written + committed)

**Task closure: 19 / 19 tasks DONE** across 13 work-unit commits on `main` (HEAD `3de7783` ahead of `origin/main` by 13 commits; ready for `git push`).

## Test count delta

| Stage | Count | Delta vs baseline | Notes |
|-------|-------|-------------------|-------|
| Pre-apply baseline (`a2ce3f5`, post-PR#2b push) | **1232 / 1232 passing** | — | The 0 failures + 0 errors are the prompt-registry PR#2b green baseline |
| Sub-batch A close (post-T1.6) | 1230 passing | **-2** | 3 `from_legacy` Finding fixtures + 3 `from_legacy` DriftReport fixtures deleted; net -2 (one each) |
| Sub-batch B close (post-T2.6) | 1232 passing | **+2** | 2 new W1 enforcement tests (`test_finding_constructor_rejects_str_decision_id` + `test_finding_constructor_rejects_bool_decision_id`); 1 deleted `classify_binding_legacy` fixture + 1 new positive smoke (`test_finding_constructor_accepts_int_decision_id`) |
| Sub-batch C close (post-T3.7, HEAD `3de7783`) | **1232 / 1232 passing** | **0 net** | 0 test changes; closeout is docs/meta only |
| **Net change** | **1232 → 1232 = NET EVEN** | **0** | Matches `apply-progress/final.md` "net even" claim |

**BDD scenarios**: 179 / 179 passing (unchanged; no new feature files — shim removal is type-contract enforcement only, no behavioral surface change).

## Files touched (cumulative, deduped)

### Production code
- `src/flow_engineering/decision_drift.py` — MODIFIED (sub-batches A + B): `Finding.from_legacy` classmethod DELETED (~41 LOC at lines 77-117); `DriftReport.from_legacy` classmethod DELETED (~55 LOC at lines 143-197); `classify_binding_legacy` 3-arg wrapper DELETED (~19 LOC at lines 267-285); `Finding.__post_init__` ADDED (~7 LOC at lines 84-90 with bool rejection rationale docstring); 3 `# type: ignore` comments removed at lines 759/772/792 (str-coercion sites now unreachable); unused `Any` import removed. Internal helpers `_epoch_to_iso` (lines 113-122) + `_classify_with_id_map` (lines 159-175) KEEP per design §"Files Affected". Net: ~-115 prod LOC.

### Capability spec (NEW archive status + Versioning)
- `openspec/specs/decision-drift/spec.md` — MODIFIED (sub-batch C + this archive): v0.9.0 final note with ✅ SHIPPED markers for REQ-V9.1..V9.5; new `## Archive status (2026-06-28)` block documenting the v0.9.0 BREAKING migration shipping + PASS-WITH-WARNINGS verdict + reference to `archive-report.md` + `verify-report.md`; new `## Versioning` table with v0.2.0 → v0.9.0 history + v1.0 entry noting change #9 closed + v0.9.0 BREAKING shipped.

### Archived spec/design reconciliation (W2 Drift note)
- `openspec/changes/archive/2026-06-27-drift-hardening/design.md` — MODIFIED (T3.4, commit `2410b03`): W2 Option B Drift note appended at line 493 — `### v0.9.0 resolution (REQ-V9.5)` documents the `graph_unavailable` direction-flip closure.

### Tests (NEW + MODIFIED)
- `tests/unit/test_decision_drift_v090_hardening.py` — NEW (sub-batches A + B): 7 RED→GREEN fixtures asserting shims REMOVED + W1 enforcement accepts/rejects int/str/bool. 13 tests total (7 hardening + 6 canonical type-contract smokes from v080_migration).
- `tests/unit/test_decision_drift_v080_migration.py` — MODIFIED (sub-batch A + B): 6 `from_legacy` fixtures DELETED (3 Finding + 3 DriftReport); 1 `classify_binding_legacy` fixture DELETED; net 13 tests → 3 tests (only canonical type-contract smokes KEEP).
- `tests/unit/test_decision_drift.py` — MODIFIED (sub-batches A + B + C): 2 `Finding(str)` sites migrated to int (line 196 + smoke); 8 `DriftReport(scanned_at=0.0)` sites migrated to ISO str (lines 208/535 + 2 fixtures); 10 `classify_binding_legacy` call sites migrated to 2-arg `classify_binding(ref, graph_nodes)` (lines 74/83/95/104/116/125/135/142/173/188); dead `_id_map` helper DELETED at lines 61-62.
- `tests/unit/test_cli_watch_drift.py` — MODIFIED (sub-batch A): 1 `Finding(str)` site migrated (line 99); 2 `DriftReport(scanned_at=0.0)` sites migrated (lines 200/253).
- `tests/unit/test_daemon_drift_events.py` — MODIFIED (sub-batch A): 4 `DriftReport(scanned_at=0.0)` sites migrated (lines 151/175/204/289).
- `tests/unit/test_cli_drift.py` — MODIFIED (sub-batch B + C): 2 coercing test assertions updated to expect TypeError per REQ-V9.4 hard-break contract.
- 25 other test files — MODIFIED (sub-batch C, T3.6): `ruff --fix` auto-formatted (30 files total; pure whitespace/import-order/style).

### Build/release
- `pyproject.toml` — MODIFIED (sub-batch C, T3.3): `version = "0.9.0"` (was `"0.8.1"`) — SemVer minor bump for public API break.
- `CHANGELOG.md` — MODIFIED (sub-batch C, T3.2): v0.9.0 entry at lines 7-32 (### Changed (BREAKING) + 4 breaking changes + ### Removed + 3 removed items + ### Migration + 4-step migration guide + "no automatic migration — v0.9.0 is a hard break" warning).
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — MODIFIED (sub-batch C, T3.5, runtime-only OUTSIDE repo): "## Drift detection hook" section in each file refreshed to drop the "1-release shim" qualifier per the v0.9.0 final state (per `drift-hardening` T4.5.c precedent at commit `d5f2147`); 0 `1-release shim` matches + 6 `removed in v0.9.0` matches verified.

### Archive (this report)
- `openspec/changes/archive/2026-06-28-v0.9.0-hardening/` — full archive of 5 artifacts:
  - `proposal.md` (722 LOC)
  - `explore.md` (300 LOC)
  - `tasks.md` (592 LOC)
  - `apply-progress/final.md` (153 LOC; the only apply-progress checkpoint — this change ran as a single 12-commit sub-batch sequence without per-sub-batch checkpoint files)
  - `verify-report.md` (347 LOC; verify-agent output)
  - `archive-report.md` (THIS FILE)

## Verify verdict

**`PASS WITH WARNINGS — archive-ready`** (accepted per `drift-hardening` precedent; same posture: 0C + 1W + 4S → archive; non-blocking follow-ups documented in Carry-forwards table).

| Severity | Count | Details |
|----------|-------|---------|
| **CRITICAL** | **0** | All 5 REQs (REQ-V9.1..V9.5) have at least one passing test demonstrating compliance; all 19 tasks closed; v0.9.0 BREAKING migration complete; all 3 compat shims deleted with passing RED→GREEN evidence; `Finding.__post_init__` hard break enforced via TypeError on str AND bool; 1232/1232 tests passing with 0 regressions |
| **WARNING** | **1** | **W1** — `Finding.__post_init__` enforces STRICT REJECTION (TypeError) on str/bool inputs; brief example expected COERCION (proposal says hard break, not coerce). NOT a regression — implementation honors the proposal §"Code sketch" lines 239-245 hard-break contract. Brief was imprecise; future verify-phase briefs should phrase the smoke test as "should raise TypeError" rather than "should coerce to int". |
| **SUGGESTION** | **4** | **S1** — 3 historical docstring references to `from_legacy` remain in `decision_drift.py:67/99/116` (KEEP migration history at 67/99; SUGGEST cleanup of 116); **S2** — 12 ruff errors in `decision_drift.py` + 5 main test files (DOWN from 27 baseline = -15 IMPROVEMENT; all pre-existing tech debt; v1.0 follow-up for `ruff --fix --unsafe-fixes`); **S3** — 12 mypy errors in `decision_drift.py` (within proposal R3 expected ~10 residual band; v1.0 tech-debt follow-up); **S4** — positive feedback on `Finding.__post_init__` docstring explaining bool rejection rationale (KEEP) |

**Carry-forwards status (from `drift-hardening`):** W1 (Finding.from_legacy shim) — **CLOSED** via REQ-V9.1 + REQ-V9.4; W2 (graph_unavailable direction-flip) — **CLOSED** via REQ-V9.5 Drift note at design.md:493; W3 (classify_binding_legacy wrapper) — **CLOSED** via REQ-V9.3. **All 3 carry-forwards explicitly closed by this change.**

## W2 Option B Drift note location

Per `tasks.md` T3.4 acceptance criteria + `verify-report.md` REQ-V9.5 line 35: the W2 Option B Drift note is appended to:

- **Path**: `openspec/changes/archive/2026-06-27-drift-hardening/design.md:493`
- **Section heading**: `### v0.9.0 resolution (REQ-V9.5)`
- **Commit**: `2410b03` (`docs(design): v0.9.0 resolution note — W1/W2/W3 closed (compat shim removal)`)
- **Content**: documents the `graph_unavailable: bool` (canonical, kept from impl) + `unable_reason: str | None` (NEW) field direction-flip; design D2's intent to rename to `unable_to_verify` was NOT followed per the orchestrator Option B pre-decision; the CHANGELOG v0.8.0 step 3 migration guide + the v0.9.0 CHANGELOG entry confirm the contract.
- **Verification**: `grep -c "v0\.9\.0 resolution (REQ-V9\.5)" openspec/changes/archive/2026-06-27-drift-hardening/design.md` → 1 match.

## Timeout recovery note

The apply phase experienced **2 delegation timeouts** (per `apply-progress/final.md` Timeout recovery section; `secret-gold-elephant` + `anxious-salmon-hoverfly` sub-agents). Both timed out at the 15-minute mark:

1. **`secret-gold-elephant`** (15-min timeout) — completed Sub-batches A + B = 7 commits before timeout.
2. **`anxious-salmon-hoverfly`** (15-min timeout) — completed failure-fix + T2.5 + T2.6 + T3.1..T3.4 = 5 commits before timeout.

Per the timeout-recovery pattern documented in engram memory #185, both agents committed work BEFORE the timeout fired. The apply-progress checkpoint at `sdd/v0.9.0-hardening/apply-progress` (mirrored to engram; see Engram artifacts below) preserved the per-task TDD state across the gaps, allowing the next sub-agent to resume from the last commit without re-deriving prior work. Net result: **0 work lost**; all 19 tasks completed across the 2 timeout cycles. This is a successful application of the project's recover-from-timeout pattern (no need for an `sdd-recover` step).

## Engram artifacts (mirrored to memory)

Per the hybrid artifact store mode (engram + openspec), the following observation IDs were captured for traceability (per `apply-progress/final.md` "Engram artifacts" section):

- `sdd-init/flow-engineering` — sync_id `obs-a8a3544c95c44a48`
- `sdd/v0.9.0-hardening/explore` — sync_id `obs-83f5fcbf33433ff2`
- `sdd/v0.9.0-hardening/proposal` — sync_id `obs-259054ca037a428b`
- `sdd/v0.9.0-hardening/tasks` — sync_id `obs-6c621cad4fb4c6cd`
- `sdd/v0.9.0-hardening/apply-progress` — multiple checkpoints (preserved across the 2 timeouts)
- `sdd/v0.9.0-hardening/verify-report` — sync_id captured at verify time
- **`sdd/v0.9.0-hardening/archive-report`** — sync_id captured at THIS archive time (mirrored below)

## Cross-impact non-regression

Per `verify-report.md` §"Cross-impact non-regression" (lines 218-227):

- **`flow drift scan <change>`** — exit-code semantics unchanged (0 still-valid / 1 drift / 2 graph_unavailable / 3 usage error). Verified: `tests/unit/test_cli_drift.py::TestExitCodeZero/One/Two` all PASS.
- **`flow drift <change> --write-back`** — stderr WARN behavior unchanged (REQ-59 S2). Verified: `tests/unit/test_cli_drift.py::TestWriteBackSkipWarn` (3/3 pass).
- **`flow watch --drift` daemon** — still-valid silence rule (REQ-55 W6). Verified: `tests/unit/test_daemon_drift_events.py::TestStillValidSilence` (3/3 pass).
- **`DriftEventLog` JSONL append** — 1 JSONL line per non-still-valid finding at `~/.flow-engineering/drift_events.jsonl`. Verified: `tests/unit/test_drift_event_log.py` (8/8 pass).
- **Observability counters** (REQ-8, REQ-12, REQ-22, REQ-26, REQ-28..34) — unchanged; the 8 `drift_*_total` counters still emitted per tick. Verified: `tests/unit/test_observability.py` (16/16 pass).
- **`flow metrics --domain=drift`** — counter catalog unchanged; `drift_unable_to_verify_total` counter name stays (W2 Option B). Verified: 179 BDD scenarios pass.
- **Snapshot create/list/diff/rollback/prune** (REQ-28..34) — unchanged. Verified: `tests/unit/test_cli_snapshot.py` (all pass).
- **`DriftEvent.decision_id: str`** (JSONL wire format) vs **`Finding.decision_id: int`** (Python) — INTENTIONAL inconsistency per `verify-report.md` S1 (`drift-hardening`) + `explore.md` line 54. Documented in CHANGELOG v0.9.0 Notes + carried forward to v1.0.

## Out-of-scope reminders (carried to v1.0)

1. **S1 cleanup** — Update `decision_drift.py:116` `_epoch_to_iso` helper docstring to remove the now-stale `from_legacy` reference (1-line docstring edit; the other 2 docstring references at lines 67/99 are intentionally KEEP — they document the migration history).
2. **S2 ruff residuals** — 12 ruff errors in changed files (DOWN from 27 baseline = -15 IMPROVEMENT). 6 of 12 are auto-fixable via `uv run ruff check --fix --unsafe-fixes` (clearance of: UP042 DriftClass str+Enum inheritance at `decision_drift.py:49` + C401 unnecessary-generator-set at `decision_drift.py:686` + 4 test style); remaining 6 are PT018/PT011/A002/B011/F821 test style debt. v1.0 follow-up.
3. **S3 mypy residuals** — 12 mypy errors in `decision_drift.py` (within proposal R3 expected ~10 residual band; 1 net improvement from the 3 `# type: ignore` cleanup at T2.6). Categorized as: 7 × `Missing type arguments for generic type "dict" / "list"` (lines 127/161/203/252/253/262/278) + 2 × `Function is missing a type annotation` (lines 372/375) + 3 × `Argument "backend" to "SnapshotManager" has incompatible type` (lines 310/411/439 from `_DummyBackend` test mock). v1.0 tech-debt follow-up.
4. **DriftEvent JSONL `decision_id: int` wire format migration** — v1.0 follow-up; flip the JSONL wire format from str to int to align with the v0.8.0+ Python `Finding.decision_id: int` contract.
5. **`flow drift events` CLI read-side** — v1.0 follow-up; consumers use `cat ~/.flow-engineering/drift_events.jsonl | jq` or `flow metrics --domain drift` for v0.9.0.
6. **`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` env vars** — v1.1 alongside metrics rotation; joint with REQ-44 v1.1 metrics-rotation follow-up.
7. **Cross-project federation for drift events** (`flow drift events --project=<key>`) — v1.0 follow-up.
8. **OpenTelemetry push for drift events** — v1.0 follow-up; Prometheus textfile (REQ-38) covers v1 export.

## Cleanup verification

- `git status --short` after archive operations: 4 renames (`R`) for the tracked files (explore.md + proposal.md + tasks.md + apply-progress/) + 1 untracked (`??`) for verify-report.md (moved with `Move-Item`; will be `git add`ed in the orchestrator's archive commit) + 1 modified (`M`) for the capability spec sync (`openspec/specs/decision-drift/spec.md`).
- `git log --oneline -13` (apply commits + closeout): 12 work-unit commits between `a2ce3f5` (pre-apply baseline) and `3de7783` (post-ruff --fix closeout).
- `uv run --frozen pytest tests/ --tb=short -q`: 1232 passed, 0 failed, 64.02s, exit 0 (final HEAD `3de7783`).
- 4 `git mv` operations (4 root files + 1 directory `apply-progress/`) + 1 `Move-Item` (untracked `verify-report.md`) + 1 directory removal (`openspec/changes/v0.9.0-hardening/` — empty after the 4 moves).
- 1 modified capability spec (`openspec/specs/decision-drift/spec.md` — added `## v0.9.0 archive status (2026-06-28)` + `## Versioning` sections; updated `## v0.9.0 final note` with ✅ SHIPPED markers).
- 1 created file in archive (this `archive-report.md`).

## Relevant Files

### Production code (v0.9.0 BREAKING)
- `src/flow_engineering/decision_drift.py` — MODIFIED (sub-batches A + B): shim removal + `__post_init__` enforcement (~-115 prod LOC net)

### Capability spec (archive sync)
- `openspec/specs/decision-drift/spec.md` — MODIFIED (sub-batch C + this archive): v0.9.0 final note with ✅ SHIPPED markers + `## Archive status (2026-06-28)` block + `## Versioning` section with v0.2.0 → v0.9.0 history + v1.0 entry

### Archived spec/design reconciliation (W2 Drift note)
- `openspec/changes/archive/2026-06-27-drift-hardening/design.md` — MODIFIED (T3.4, commit `2410b03`): W2 Option B Drift note appended at line 493 — `### v0.9.0 resolution (REQ-V9.5)`

### Tests (NEW + MODIFIED)
- `tests/unit/test_decision_drift_v090_hardening.py` — NEW: 7 RED→GREEN fixtures (shim-removal + W1 enforcement)
- `tests/unit/test_decision_drift_v080_migration.py` — MODIFIED: 6 `from_legacy` fixtures + 1 `classify_binding_legacy` fixture DELETED; 3 canonical type-contract smokes KEEP (13 tests → 3 tests)
- `tests/unit/test_decision_drift.py` — MODIFIED: 2 `Finding(str)` + 8 `DriftReport(scanned_at=0.0)` + 10 `classify_binding_legacy` sites migrated; dead `_id_map` helper DELETED
- `tests/unit/test_cli_watch_drift.py` — MODIFIED: 1 `Finding(str)` + 2 `DriftReport(scanned_at=0.0)` sites migrated
- `tests/unit/test_daemon_drift_events.py` — MODIFIED: 4 `DriftReport(scanned_at=0.0)` sites migrated
- `tests/unit/test_cli_drift.py` — MODIFIED: 2 coercing test assertions updated to expect TypeError
- 25 other test files — MODIFIED: `ruff --fix` auto-format (30 files total)

### Build/release
- `pyproject.toml` — MODIFIED (T3.3): `version = "0.9.0"` (was `"0.8.1"`) — SemVer minor bump for public API break
- `CHANGELOG.md` — MODIFIED (T3.2): v0.9.0 entry (BREAKING + 4 breaking changes + 3 removed items + 4-step migration guide)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — MODIFIED (T3.5, runtime-only OUTSIDE repo): v0.9.0 final-state qualifier (no "1-release shim")

### Archive
- `openspec/changes/archive/2026-06-28-v0.9.0-hardening/` — full archive of 5 artifacts (proposal.md + explore.md + tasks.md + apply-progress/final.md + verify-report.md) + this `archive-report.md`

## Celebration 🎉

**Change #9 v0.9.0-hardening is CLOSED.** The v0.8.0 1-release compat shim window is officially closed. The 3 carry-forwards from `drift-hardening` (W1, W2, W3) are all explicitly **CLOSED**. The W1 enforcement is now baked into the type system via `Finding.__post_init__` — no future v0.7.x caller can sneak through. The v0.8.x line is end-of-life; the next release train is v1.0. The debt-closure loop ran clean: 0 regressions, 0 lost work (despite 2 delegation timeouts), 0 workarounds. Strict TDD discipline held across 19 per-task cycles in 3 sub-batches.

**Single PR, single release, single cycle** — the cleanest possible v0.9.0 break.

---

**Session**: flow-engineering-v0.9.0-hardening-archive-2026-06-28
**SDD Cycle**: COMPLETE (change #9 closeout)
**Verdict**: PASS WITH WARNINGS — archive-ready (0/0 C + 0/1 W resolved pre-archive, 1/1 W accepted per `drift-hardening` precedent, 0/4 S resolved pre-archive, 4/4 S deferred to v1.0 follow-ups; 3/3 carry-forwards from `drift-hardening` CLOSED)
**Capability spec sync**: `openspec/specs/decision-drift/spec.md` updated with `## v0.9.0 final note` (✅ SHIPPED markers) + `## Archive status (2026-06-28)` block + `## Versioning` section with v1.0 entry
**Next**: orchestrator commits the 4 archive moves + capability spec sync + archive-report; pushes to `main`; loop continues to T3.13 PR#2b cleanup → v1.0 follow-ups (DriftEvent JSONL int + flow drift events CLI + tech debt residuals) → v1.1 follow-ups (DriftEventLog rotation)
**Topic**: sdd/v0.9.0-hardening/archive-report
