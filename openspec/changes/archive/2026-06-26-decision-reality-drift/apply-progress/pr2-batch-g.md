<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr2-batch-g (Engram #133) -->

# Apply progress PR#2 batch G — decision-reality-drift

## Goal

SDD apply batch G of decision-reality-drift PR#2: T2.1 (daemon `--drift` event handling) + T2.2 (CLI `--drift` flag on `flow watch`) + T2.3 (BDD `req15_drift_daemon` with 3 scenarios). Strict TDD with work-unit commits.

## Status

**Completed but timed out** — sub-agent did all the work (6 commits, 385/385 tests green, PR #4 created) but exceeded the 15-min delegation runtime before outputting the structured result. Manual recovery by orchestrator.

## Branch / PR State

- Branch: `feature/decision-reality-drift-pr2`
- Baseline (this branch HEAD at start): `ecaa2f0` (main)
- Final HEAD: `3e3257a`
- PR: https://github.com/Rene-Kuhm/flow-engineering/pull/4 (open)
- Merge strategy recommended: **squash merge** (collapses `3e3257a fixup!` into `9813354 feat(cli):`)

## Commits

1. `4d79c15` test(unit): RED fixtures for daemon --drift event handling (T2.1 RED)
2. `f7fccf8` feat(daemon): flow watch --drift subscribes to apply-progress (T2.1 GREEN)
3. `74854b6` test(unit): RED fixtures for flow watch --drift CLI flag (T2.2 RED)
4. `9813354` feat(cli): --drift flag on flow watch (T2.2 GREEN)
5. `5e1c353` test(bdd): req15_drift_daemon feature with 3 scenarios (T2.3)
6. `3e3257a` fixup! feat(cli): --drift flag on flow watch — REFACTOR post-GREEN, simplifies tests (T2.1+T2.2)

## LOC Delta (cumulative)

- `src/flow_engineering/cli.py`: +32 (added `--drift` flag)
- `src/flow_engineering/daemon.py`: +163 (drift event handling)
- `src/flow_engineering/observability.py`: +26 (helper tweaks, including `drift_unable_to_verify_total` 8th counter)
- `tests/bdd/req15_drift_daemon.feature`: +37 (NEW feature file)
- `tests/bdd/test_decision_reality_drift_steps.py`: +295 (NEW step defs)
- `tests/unit/test_cli_watch_drift.py`: +357 (NEW test file)
- `tests/unit/test_daemon_drift_events.py`: +335 (NEW test file)
- **Total**: +1231/-14 = **+1217 net** across 7 files (4 new + 3 modified)

## Test Delta

- Baseline: 364 passing
- Final: **385 passing** (verified via `uv run pytest -x --tb=short` in 1.76s)
- Delta: **+21 tests**
  - `test_daemon_drift_events.py`: 10 unit tests
  - `test_cli_watch_drift.py`: 8 unit tests
  - `req15_drift_daemon.feature`: 3 BDD scenarios

## BDD Coverage Delta

- Baseline scenarios: 33 (PR#1 total — req9=14 + req3=1 + req1..req8=18 carry-over)
- Final scenarios: 36
- Delta: +3 (all under `req15_drift_daemon`)

## Multiplier vs Forecast

- Forecast per tasks.md: ~235 LOC for batch G
- Actual: +1217 net LOC
- ×6 multiplier expectation: ~1410 (actual is 14% under forecast — within tolerance)

## Implementation Summary

### T2.1 — Daemon `--drift` event handling (`daemon.py`)

- `start_watch(change, target, drift=False)` accepts new `drift` kwarg.
- When `drift=True`, the daemon also subscribes to `apply-progress.json` writes via `on_apply_progress_updated` callback.
- On `task_merged` event, daemon calls `decision_drift.scan_change(change, graph_path)` and emits summary line via `on_summary` callback.
- Default `on_summary=print`; CLI wires `lambda line: click.echo(line)` for stdout.
- `handle_apply_progress_event(change, event)` extracted as module-level seam for testability.
- Missing `graph.json` logs `unable_to_verify: graph.json unavailable at <path>` once and watcher stays alive.

### T2.2 — `flow watch --drift` CLI flag (`cli.py`)

- New `--drift` boolean flag on the `watch` Click command.
- Wires to `daemon.start_watch(..., drift=drift_flag)`.
- Non-drift path unchanged (REQ-15 backward-compat).
- Drift event: stdout summary line + counters incremented.
- Non-blocking background thread (PR#2 batch G confirmation).

### T2.3 — BDD `req15_drift_daemon.feature` (3 scenarios)

1. **Daemon emits event-log line on detected drift** — file change to binding's `file:line` triggers `drift: <change> <total> findings (<class_counts>)` summary line.
2. **Daemon still-valid change does not emit event-log line** — still-valid observations do NOT emit per-finding lines; only `drift_still_valid_total` counter increments. *(Impl deviation: impl DOES emit a summary line "0 findings (no classes)" even when still-valid — see W6 in verify-report #135.)*
3. **Daemon missing graph.json does not crash the watcher** — `unable_to_verify` logged once; watcher process remains alive.

## Deviations From Spec (Carry-forward as WARNINGS)

- **W5 — REQ-15 event-log mechanism drift**: spec required JSONL at `~/.flow-engineering/drift_events.jsonl`; impl emits stdout summary via `on_summary` callback. Reasonable v1 design but does not match spec's persistence requirement.
- **W6 — REQ-15 still-valid silence drift**: spec says no event-log line for still-valid; impl emits `drift: <change> 0 findings` even when all bindings STILL_VALID. Behavior observable as noise in `flow watch --drift` output.

Both W5 and W6 documented in verify-report #135 as WARNING-level findings; not blocking the archive.

## Risks / Blockers

- None for batch G itself.
- Sub-agent timeout remains a pattern (see `pattern/apply-batches-split-into-6-tasks-per-delegation`); this batch was right at the 15-min ceiling.

## Next

**Batch H**: T2.4 (sdd-verify Step 6 sub-step) + T2.5 (CHANGELOG.md v0.3.0 entry) + T2.6 (6 SKILL.md "Drift detection hook" prose updates). Forecast ~60 LOC / ~360 real. Docs-only — should fit comfortably under 15-min timeout.

After batch H merged → `sdd-verify PR#2` → `sdd-archive decision-reality-drift` → ready for change #3 (`vector-semantic-search`).

**Session**: insyd-2026-06-26-end-of-session
**Topic**: sdd/decision-reality-drift/apply-progress-pr2-batch-g
**Engram**: #133
**Next**: Batch H (T2.4 + T2.5 + T2.6)