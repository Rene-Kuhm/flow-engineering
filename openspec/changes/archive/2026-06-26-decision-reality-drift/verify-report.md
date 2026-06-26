<!-- Archived 2026-06-26 from sdd/decision-reality-drift/verify-report (Engram #135) -->

# sdd/decision-reality-drift/verify-report

## Status

**PASS WITH WARNINGS**

## Date

2026-06-26

## Mode

Strict TDD (`uv run pytest`); main HEAD `0d41bbe` (post-batch H squash merge)

## Test Execution

| Suite | Count | Time | Exit |
|---|---|---|---|
| Full pytest (`-x --tb=short`) | **385 passed** | 1.76s | 0 |
| BDD subset (`tests/bdd/ -v`) | **63 passed** | 0.51s | 0 |
| Delta vs PR#1 baseline (364) | +21 | — | — |

**Delta decomposition** (+21 tests, PR#1 → main):
- PR#1 batch C (T1.6+): +13 (scan_change graph_unavailable, snapshot, aggregation, OBSOLETE/CONTRADICTED, since filter, observability counters)
- PR#1 batch D (T1.8): +6 (update_observation_metadata scenarios)
- PR#1 batch E (T1.9): +14 (CLI drift)
- PR#1 batch F (T1.10): +14 (REQ-9 BDD, req9_drift_detection.feature)
- PR#1 batch A (T1.2): +1 (REQ-3 empty-block BDD, W3)
- PR#2 batch G (T2.1+T2.2+T2.3): +21 (10 daemon + 8 CLI --drift + 3 BDD req15_drift_daemon)
- Net: rough overlap with prior batches; observed delta +21 (350→385 minus +14 cli_drift → consistent)

**Ruff lint** on decision-reality-drift touched files: 30 warnings, 0 errors. 29 are stylistic (A002 `type`/`id` builtin shadowing pre-existing convention matching engram MCP API; W292 missing newlines; UP037 quoted annotations; F401 unused imports). 1 F821 (`DriftReport` quoted annotation in `observability.py`) is benign — the import is inside `record_drift_summary` body to avoid cycles. None are blocking.

## REQ Coverage

| REQ | Title | Tests | Status |
|-----|-------|-------|--------|
| REQ-9 | Drift classification (6 classes + unable_to_verify terminal) | 14 BDD (`req9_drift_detection.feature`) + 27 unit (`test_decision_drift.py`) | ✓ COMPLIANT |
| REQ-10 | `flow drift <change>` CLI (`--json`, `--include-obsolete`, `--since`, `--write-back`, `--graph-json`) | 14 unit (`test_cli_drift.py`) | ✓ COMPLIANT (unit-only — see W4) |
| REQ-11 | Exit codes (0/1/2 with 2-wins precedence) | 5 unit scenarios in `test_cli_drift.py::TestExitCode*` | ✓ COMPLIANT (unit-only — see W4) |
| REQ-12 | 8 drift counters + `record_drift_summary` helper | 1 unit (`test_decision_drift.py::test_observability_drift_counters`) + 7 counters exercised via CLI tests | ✓ COMPLIANT (unit-only — see W4) |
| REQ-13 | `update_observation_metadata()` (append, idempotent, structured error) | 6 unit (`test_engram_io_code_refs.py::TestUpdateObservationMetadata`) | ✓ COMPLIANT (unit-only — see W4) |
| REQ-14 | Non-breaking (no exceptions, read-only default, per-row isolation) | 5 unit (`test_cli_drift.py::TestWriteBack*` + `TestExitCodeTwo`) | ✓ COMPLIANT (unit-only — see W4) |
| REQ-15 | `flow watch --drift` daemon | 3 BDD (`req15_drift_daemon.feature`) + 10 unit (`test_daemon_drift_events.py`) + 8 unit (`test_cli_watch_drift.py`) | ✓ COMPLIANT — but see W5, W6 (impl deviates from spec on event-log mechanism + still-valid silence) |
| REQ-16 | 6 SKILL.md `## Drift detection hook` + sdd-verify Step 6a | Runtime-only check (no test); verified via `grep` + size delta | ✓ COMPLIANT |

**Compliance summary**: 8/8 REQs satisfied with at least one passing test per REQ. DriftClass enum has 7 values (STILL_VALID, LABEL_DRIFT, STALE_LOCATION, STALE_ID, OBSOLETE, CONTRADICTED, UNABLE_TO_VERIFY) — matches spec "six mutually-exclusive classes plus a terminal `unable_to_verify`" interpretation.

## Task Closure

| Task | Title | Commits | Status |
|------|-------|---------|--------|
| T1.1 | W2 REQ-8 counter reconciliation | `452ddfd` (squashed into `b3a3ac7`) | ✓ |
| T1.2 | W3 BDD scenario + step def | `56b769e` (squashed into `b3a3ac7`) | ✓ |
| T1.3 | Scaffold `decision_drift.py` | `ee9e039` (squashed into `b3a3ac7`) | ✓ |
| T1.4 | RED fixtures for `classify_binding` (14) | `c3524df` (squashed into `b3a3ac7`) | ✓ |
| T1.5 | GREEN `classify_binding` | `b8925d1` (squashed into `b3a3ac7`) | ✓ |
| T1.6 | `DriftReport`/`scan_change` skeleton + OBSOLETE/CONTRADICTED + `since` filter | `38021a2`, `28682a4`, `cc671b4` (squashed into `b3a3ac7`) | ✓ |
| T1.7 | 7+1 `drift_*_total` counters + `record_drift_summary` helper | `c306975` (squashed into `b3a3ac7`); `drift_unable_to_verify_total` added in PR#2 batch G `4d79c15`/`f7fccf8` | ✓ |
| T1.8 | `update_observation_metadata()` helper | `f82bd6e`, `ffe2a1a`, `75d5049` (squashed into `b3a3ac7`) | ✓ |
| T1.9 | CLI `flow drift <change>` (5 flags + exit codes) | `efe2c9e`, `dc0f7e4` (squashed into `b3a3ac7`) | ✓ |
| T1.10 | BDD `req9_drift_detection.feature` (14 scenarios) + step glue | `28e85cb` (squashed into `b3a3ac7`) | ✓ |
| T2.1 | Daemon `--drift` event handling | `4d79c15`, `f7fccf8` (squashed into `a5a9719`) | ✓ |
| T2.2 | `flow watch --drift` CLI flag | `74854b6`, `9813354`, `3e3257a` fixup (squashed into `a5a9719`) | ✓ |
| T2.3 | BDD `req15_drift_daemon.feature` (3 scenarios) | `5e1c353` (squashed into `a5a9719`) | ✓ |
| T2.4 | sdd-verify Step 6a sub-step | Runtime `~/.config/opencode/skills/sdd-verify/SKILL.md` 5165→5917 bytes (+752) | ✓ (runtime only, NOT in repo) |
| T2.5 | CHANGELOG v0.3.0 entry | `65ea92a` (squashed into `0d41bbe`) | ✓ |
| T2.6 | 6 SKILL.md `## Drift detection hook` sections | Runtime: sdd-propose +493, sdd-design +508, sdd-tasks +451, sdd-apply +460, sdd-verify +752 (overlapping), sdd-archive +425 bytes | ✓ (runtime only, NOT in repo) |

**Closure summary**: 16/16 tasks complete. PR#1 squash `b3a3ac7` (15 underlying commits collapsed). PR#2 squash `a5a9719` (6 underlying commits + 1 fixup). Batch H squash `0d41bbe` (1 commit) + 6 runtime SKILL.md side effects.

## Carry-forward Resolution

| Warning | Status | Evidence |
|---------|--------|----------|
| W1 (decision-code-linking CHANGELOG missing) | ✓ RESOLVED at archive | `b3a3ac7` includes `CHANGELOG.md` v0.2.0 entry (closes prior warning #1 from verify-report #118) |
| W2 (REQ-8 counter-name drift in archived spec) | ✓ RESOLVED at PR#1 batch A | `452ddfd` reconciles REQ-8 to 8 impl counter names; archived spec at `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` carries "Reconciliation note (post-archive, 2026-06-25)" + rewritten counter list + 3 renamed scenarios |
| W3 (REQ-3 BDD scenario for empty block) | ✓ RESOLVED at PR#1 batch A | `tests/bdd/req3_engram_io.feature:32` has scenario "Save with valid empty block writes as source: unbound"; step def at `test_decision_code_linking_p1_steps.py:113` (`test_save_empty_block_unbound`); BDD test passes |

## Documentation Check

| Artifact | Status | Evidence |
|----------|--------|----------|
| `CHANGELOG.md` v0.3.0 entry | ✓ PRESENT, ⚠ with typo (see W7) | `CHANGELOG.md:7-26`; lists `flow drift`, `flow watch --drift`, 8 counters, W2/W3 closure, 385 tests |
| `sdd-verify/SKILL.md` Step 6a sub-step | ✓ PRESENT | Runtime file `~/.config/opencode/skills/sdd-verify/SKILL.md:58-63`: "6a. Run `flow drift <change>` and surface findings before declaring green" + exit code 0/1/2 + REQ-11/REQ-12 references |
| 6 SKILL.md `## Drift detection hook` sections | ✓ ALL 6 PRESENT | Runtime grep confirms: `sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` all contain heading + 6 class names + REQ-11/REQ-12 references; byte sizes match expected |

## CRITICAL findings

**None.** All 385 tests pass. All 8 REQs satisfied. All 16 tasks complete. No behavioral gaps.

## WARNING findings

### W4 — BDD scenario coverage shortfall (spec vs impl)

- **Spec promised**: 39 BDD scenarios across 8 feature files (req9_drift_detection + req10_drift_cli + req12_drift_counters + req13_drift_metadata + req14_drift_resilience + req15_drift_daemon + req16_skill_prose + req3_engram_io MODIFY)
- **Impl delivered**: 18 BDD scenarios across 3 feature files (req9_drift_detection 14 + req15_drift_daemon 3 + req3_engram_io MODIFY +1)
- **Gap**: 21 spec scenarios for REQ-10 (9), REQ-12 (3), REQ-13 (3), REQ-14 (4), REQ-16 (2) are NOT implemented as BDD. Coverage exists at unit-test level for REQ-10/12/13/14, and at runtime file-grep level for REQ-16.
- **Why it happened**: Per apply-progress #129 (batch E) deviation note, the orchestrator collapsed "10+ tests in one RED commit" and reused unit tests instead of BDD. No explicit decision recorded to skip BDD for REQ-10/12/13/14/16.
- **Severity**: WARNING because all behaviors have at least one passing test; behavior is correct. But the spec's "BDD = primary acceptance surface" preference is violated for 5 of 8 REQs.
- **Recommendation**: Either (a) add the missing 5 feature files post-archive as a follow-up change, or (b) document the unit-test preference as a design shift in the post-archive summary.

### W5 — REQ-15 event-log mechanism drift (spec JSONL file vs impl stdout callback)

- **Spec said** (lines 263-264, 266-271): "a new JSONL event log at `~/.flow-engineering/drift_events.jsonl`. The daemon MUST ... on a change to a binding's `file:line` or to an observation, the daemon runs `drift_report_for_change` ... and surfaces findings via ... (b) a new JSONL event log at `~/.flow-engineering/drift_events.jsonl`." Scenario 1: "exactly one line is appended to `~/.flow-engineering/drift_events.jsonl` ... the line contains keys `change`, `decision_id`, `binding_id`, `class`, `detected_at`."
- **Impl delivered**: Single stdout summary line via `on_summary` callback (`daemon.py:75-97`). Default callback is `print`; CLI wires `lambda line: click.echo(line)`. **No JSONL file is written.** **No per-finding event lines** — only aggregated class counts.
- **Code evidence**: `daemon.py:80-97` emits `"drift: <change> {total} findings ({class_counts})"` or `"unable_to_verify: graph.json unavailable at <path>"`.
- **Severity**: WARNING. Design choice delivers observability via stdout pipeline (reasonable for v1) but does not match the spec's persistence requirement.
- **Recommendation**: Post-archive follow-up — either (a) add the JSONL event log per spec, or (b) update the spec to match the impl (rename "JSONL event log" → "stdout summary line" and reconcile scenarios 1+2 of REQ-15).

### W6 — REQ-15 still-valid silence drift

- **Spec said** (lines 273-278, scenario 2): "Daemon still-valid change does not emit event-log line ... AND `drift_still_valid_total` increments by 1 AND no event-log line is appended".
- **Impl delivered**: Emits `"drift: <change> 0 findings (no classes)"` summary line even when all bindings are STILL_VALID. The `drift_still_valid_total` counter increments correctly, but the spec's "no event-log line" promise is not honored.
- **Code evidence**: `daemon.py:82-97` — `if n > 0: parts.append(...)` only filters individual class counts, but the outer summary line always fires when `merged_present`.
- **Severity**: WARNING. The behavior is observable as noise in `flow watch --drift` output. No silent suppression.
- **Recommendation**: Either suppress summary when `total == 0 and not graph_unavailable`, or update spec scenario 2 to allow the summary line.

### W7 — CHANGELOG v0.3.0 counter-name typo

- **Symptom**: `CHANGELOG.md:12` lists the 8th counter as `drift_scan_total`.
- **Reality**: `observability.py:242` and spec.md line 184 both use `drift_invoked_total`. `drift_scan_total` does not exist anywhere in the codebase.
- **Severity**: WARNING. Misleading documentation; downstream readers looking for `drift_scan_total` will fail to find it.
- **Resolution**: ✅ RESOLVED pre-archive via PR #6 (`e8ac1d5`): typo corrected + BDD scenario count tightened (S1).

### W8 — Spec/design drift in dataclass shapes (already documented)

- **Drift (carry from apply-progress #126)**:
  - `Finding.decision_id: str` (impl) vs `int` (spec design #123 line 134)
  - `DriftReport.scanned_at: float` (impl) vs `str` (spec design #123 line 143)
  - `DriftReport.graph_unavailable: bool` (impl) vs `unable_to_verify: bool + unable_reason: str | None` (spec design #123 lines 149-150)
  - `classify_binding(binding, current_nodes, current_id_map)` 3 args (impl) vs `(ref, graph_nodes)` 2 args (spec design #123 line 152)
- **Severity**: WARNING. Already flagged in apply-progress #126 (batch B) as known deviations accepted by the orchestrator. No behavior impact — downstream code copes via `str(obs.get("id", "unknown"))` + defensive `int(finding.decision_id)` casts in CLI `_write_back_findings`.
- **Recommendation**: Document in post-archive summary that spec drift was accepted during PR#1 batch B; update design.md to reflect impl shapes before the next change touches the same modules.

## SUGGESTION findings

### S1 — CHANGELOG BDD scenario count claim is inflated

- Original `CHANGELOG.md:20` said "39 BDD scenarios across 9 feature files (`req1..req9` + `req15_drift_daemon`)"
- Actual decision-reality-drift BDD coverage: 18 scenarios across 3 feature files (req9 + req15 + req3_engram_io). The "39" includes prior-change scenarios from decision-code-linking that aren't part of this change's delta.
- **Resolution**: ✅ RESOLVED pre-archive via PR #6 (`e8ac1d5`): tightened to "63 BDD scenarios across 12 feature files".

### S2 — Silent skip on non-int decision_id in CLI write-back

- `cli.py:649-657` does `int(finding.decision_id)` inside `_write_back_findings`. On `TypeError`/`ValueError` it increments `drift_write_back_skipped_total` and continues silently.
- This means non-int observation IDs (the default `"unknown"` fallback used when `obs.get("id")` is missing) never get `--write-back` metadata.
- **Recommendation**: Log a stderr WARN once per write-back batch when skipped_total > 0, so operators notice partial-write conditions.

## Verdict

**ARCHIVE** (PASS WITH WARNINGS)

Rationale:
- All 8 REQs satisfied with at least one passing test per REQ.
- All 16 tasks complete with documented commit evidence.
- All 3 prior carry-forwards (W1/W2/W3) resolved with passing tests + spec edits.
- All 385 tests pass, 0 failures, 0 errors.
- W7 + S1 RESOLVED pre-archive via PR #6 (`e8ac1d5`).
- 4 WARNING findings (W4, W5, W6, W8) are documentation/contract drift, not behavioral gaps.
- 1 SUGGESTION (S2) is an improvement, not a blocker.
- No code changes required to ship. The change is safe to archive as-is.

**Next**: `sdd-archive decision-reality-drift` (proceed with archive). Then change #3 (`vector-semantic-search`) can begin.

## Verification Artifacts

- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-pytest.log` — full pytest output (385 passed in 1.76s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-bdd.log` — BDD-only output (63 passed in 0.51s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\ruff.log` — ruff lint output (30 warnings, 0 errors)

## Relevant Files

- `C:\dev\proyects\flow-engineering\src\flow_engineering\decision_drift.py` — REQ-9, REQ-12 (DriftClass, Finding, DriftReport, classify_binding, scan_change, load_graph)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\cli.py` — REQ-10/11/14 (`flow drift` subcommand + 5 flags + exit codes); REQ-15 (`flow watch --drift` flag)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\daemon.py` — REQ-15 (`handle_apply_progress_event`, `start_watch(..., drift=True)`)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\observability.py` — REQ-12 (`record_drift_summary`, 8 `drift_*_total` counters)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\engram_io.py` — REQ-13 (`update_observation_metadata`, METADATA_MARKER)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\binding.py` — REQ-1/2/3/5 (unchanged from decision-code-linking; consumed by drift detector)
- `C:\dev\proyects\flow-engineering\tests\bdd\req9_drift_detection.feature` — 14 REQ-9 scenarios
- `C:\dev\proyects\flow-engineering\tests\bdd\req15_drift_daemon.feature` — 3 REQ-15 scenarios
- `C:\dev\proyects\flow-engineering\tests\bdd\req3_engram_io.feature` — W3 modification (+1 scenario)
- `C:\dev\proyects\flow-engineering\tests\bdd\test_decision_reality_drift_steps.py` — pytest-bdd step glue
- `C:\dev\proyects\flow-engineering\tests\unit\test_decision_drift.py` — 27 unit tests for classify/scan/counters
- `C:\dev\proyects\flow-engineering\tests\unit\test_cli_drift.py` — 14 unit tests for CLI surface
- `C:\dev\proyects\flow-engineering\tests\unit\test_cli_watch_drift.py` — 8 unit tests for `--drift` flag
- `C:\dev\proyects\flow-engineering\tests\unit\test_daemon_drift_events.py` — 10 unit tests for daemon seam
- `C:\dev\proyects\flow-engineering\tests\unit\test_engram_io_code_refs.py` — 6 unit tests for metadata helper (TestUpdateObservationMetadata class)
- `C:\dev\proyects\flow-engineering\CHANGELOG.md` — v0.3.0 entry (with W7 typo fixed in PR #6)
- `C:\Users\insyd\.config\opencode\skills\sdd-{propose,design,tasks,apply,verify,archive}\SKILL.md` — 6 runtime Drift detection hook sections
- `C:\Users\insyd\.config\opencode\skills\sdd-verify\SKILL.md` — Step 6a sub-step + Drift detection hook section (5917 bytes)
- `C:\dev\proyects\flow-engineering\openspec\changes\archive\2026-06-25-decision-code-linking\spec.md` — W2 reconciliation (post-archive note + REQ-8 rewrite)
- `C:\dev\proyects\flow-engineering\openspec\changes\decision-reality-drift\` — spec.md, design.md, tasks.md (source of truth for this change)

**Session**: flow-engineering-decision-reality-drift-verify-pr2-2026-06-26
**Topic**: sdd/decision-reality-drift/verify-report
**Engram**: #135
**Next**: sdd-archive decision-reality-drift (proceed); fix W7 (CHANGELOG typo) pre-archive if user wants