<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-e (Engram #129) -->

# Apply progress PR#1 batch E — decision-reality-drift

## Goal

Ship the `flow drift <change>` CLI subcommand with the full exit-code contract (REQ-10/11/14) plus all five flags (`--json`, `--include-obsolete`, `--write-back`, `--since`, `--graph-json`). Closes T1.9 of PR#1.

## Mode

Strict TDD (vertical slices collapsed per orchestrator's "10+ tests in one RED commit, then one GREEN commit" instruction).

## Commits Added (2)

| SHA | Type | Subject |
|-----|------|---------|
| `efe2c9e` | test  | test(cli): RED tests for flow drift subcommand (failing) |
| `dc0f7e4` | feat  | feat(cli): implement flow drift subcommand with exit codes + --json + --write-back (green) |

## LOC Delta

| File | Action | LOC |
|------|--------|-----|
| `src/flow_engineering/cli.py` | MODIFY | +212 / -1 |
| `tests/unit/test_cli_drift.py` | NEW + MODIFY | +224 / -9 (RED commit 580 LOC; GREEN commit -9 LOC for monkeypatch fix) |

**Total**: +436 LOC across 2 files (both commits combined). Net relative to main: **+227 lines on the feature branch** (cli.py +212, test_cli_drift.py +215 net of monkeypatch-target correction).

## Test Counts

- Pre-batch E baseline: **336** (after batch D)
- Post-batch E: **350** (+14 new tests)
  - 10 spec'd scenarios (exit codes 0/1/2 + json + since + include-obsolete + write-back x2 + table + help)
  - 4 triangulation cases (label_drift exits 1, graph_unavailable wins over drift findings, since happy-path epoch seconds, default read-only)
- 0 regressions

## CLI Coverage (14 scenarios)

### Exit-code contract (REQ-11) — 5 scenarios

1. `test_drift_all_still_valid_exits_0` — exit 0 when every binding STILL_VALID.
2. `test_drift_with_stale_id_exits_1` — exit 1 on first non-valid class.
3. `test_drift_with_label_drift_exits_1` — triangulates exit 1 with LABEL_DRIFT.
4. `test_drift_graph_unavailable_exits_2` — terminal unable_to_verify exits 2.
5. `test_drift_graph_unavailable_wins_over_drift_findings` — **REQ-11 precedence: 2 wins over 1 even when non-valid findings present**.

### `--since` filter (REQ-10) — 2 scenarios

6. `test_drift_since_invalid_exits_2` — bad ISO 8601 → stderr + exit 2 + `scan_change` is NOT called.
7. `test_drift_since_passes_epoch_seconds` — happy path: naive date defaults to UTC midnight, propagates as float to `scan_change`.

### `--json` output (REQ-10) — 1 scenario

8. `test_drift_json_output_parseable` — DriftReport JSON with `findings[]` embedding CodeRef as dict + DriftClass values as strings.

### `--include-obsolete` flag — 1 scenario

9. `test_drift_include_obsolete_triggers_obsolete_check` — flag propagates to `scan_change` kwarg.

### `--write-back` write contract (REQ-14) — 3 scenarios

10. `test_drift_write_back_calls_update_metadata` — each finding yields one `update_observation_metadata(obs_id, {last_verified_at, last_drift_class})` call.
11. `test_drift_write_back_per_row_error_isolated` — **per-row errors MUST NOT abort the loop**: row 10 raises, row 11 still succeeds.
12. `test_drift_no_write_back_default_is_read_only` — default mode (no `--write-back`) MUST NOT call `update_observation_metadata` at all (REQ-14 read-only default).

### Pretty table output (REQ-10) — 1 scenario

13. `test_drift_table_output_format` — default mode renders a fixed-width table with `decision_id · binding.id · binding.label · drift_class · detail`.

### Help text contract — 1 scenario

14. `test_drift_help_text_includes_exit_codes` — `--help` documents the 0/1/2 contract.

## Design Decisions Respected

- **Design #123 decision 1** (snapshot-once): `drift` invokes `scan_change` which already loads `graph.json` once and includes `graph_mtime` in the report — no per-binding disk reads.
- **Design #123 decision 5** (seam for graph-snapshots): `graph_json_path` is a parameter passed through; `--graph-json` CLI flag exposes it for v1 defaults, future snapshot pinning without code change.
- **REQ-11 exit precedence** (2 > 1 > 0): `_drift_exit_code()` walks `report.graph_unavailable` first, then `class_counts`, then default 0.
- **REQ-14 fail-open**: `--since` parse error caught at CLI boundary with stderr + exit 2 (NOT propagated as traceback); `scan_change` itself is fail-open by design (returns DriftReport even on internal errors).
- **REQ-14 per-row isolation** in `_write_back_findings`: each `update_observation_metadata` call wrapped in its own `except Exception`, with `drift_write_back_failed_total` counter and `drift_write_back_skipped_total` for non-int decision_id rows.
- **REQ-14 read-only default**: `if write_back:` guard means the helper is never called unless the flag is explicit.

## Deviations From Prompt

- Orchestrator's prompt listed 10 tests; shipped 14 (10 spec'd + 4 triangulation). The 4 extras each pin down a behavior the spec explicitly states (REQ-11 precedence, REQ-14 read-only default, --since happy-path epoch propagation, exit-1 with a different drift class).
- `_parse_since` defaults naive ISO 8601 strings (e.g. `2026-06-15`) to **UTC midnight**, not local time. This matches CI determinism: `--since 2026-06-15` should mean the same instant on a runner in Berlin and a runner in Tokyo. The spec example (`--since 2026-06-15`) is consistent with UTC interpretation.
- `decision_id` from `Finding` is `str` (per `scan_change` contract: `str(obs.get("id", "unknown"))`); the CLI does `int(finding.decision_id)` defensively in `_write_back_findings`. Non-int values increment `drift_write_back_skipped_total` and skip — no abort.
- `_now_iso` is defined locally in cli.py (same shape as `observability._now_iso`, kept private to that module). The helper is small and the alternative (exposing it from observability) felt like premature widening of the public surface.

## Handoff for Batch F (T1.10: BDD `req9_drift_detection`)

Files to create:
- `tests/bdd/req9_drift_detection.feature` (NEW) — 14 REQ-9 scenarios + 1 unable_to_verify round-trip per design #123.
- `tests/bdd/test_decision_reality_drift_steps.py` (NEW) — step defs reusing `binding.extract` and the existing `in_memory_backend` fixture.

Upstream dependencies already satisfied this batch:
- `flow drift <change>` exits with REQ-11 contract.
- `--since` ISO 8601 parses with UTC-naive default.
- `--include-obsolete` flag plumbs to `scan_change`.
- `--write-back` calls `EngramClient.update_observation_metadata` with per-row isolation.
- `--json` emits parseable DriftReport.
- 7 `drift_*_total` counters fire via `observability.record_drift_summary` (covers REQ-12 contract).
- `decision_drift.scan_change` returns a `DriftReport` aggregating all six classes + `graph_unavailable`.

Downstream wiring for batch F:
- Step defs should invoke `runner.invoke(main, ["drift", change, ...])` with the same `FLOW_METRICS_PATH` env-override pattern used in `tests/unit/test_cli_inspect.py`.
- For "graph.json missing" scenarios, write an empty `tmp_path/graph.json` AFTER the step runs `Path(graph_json).unlink()` — `scan_change` already returns `graph_unavailable=True` cleanly.
- For OBSOLETE scenarios, mock `graphify_query.query_nodes` (already a stub-friendly seam in `decision_drift.scan_change`).

## TDD Cycle Evidence

| Task | Test file | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| T1.9 | `tests/unit/test_cli_drift.py` | Unit (Click CLI runner) | ✅ 14 RED (AttributeError + NoCommand) | ✅ 14 pass | ➖ None needed |

Test summary:
- Total tests written this batch: 14
- Total tests passing: 350
- Layers used: Unit (14, all Click CliRunner-driven)
- Approval tests (refactoring): 0 (no refactor of pre-existing code)
- Pure functions created: 5 (`_parse_since`, `_drift_exit_code`, `_serialize_drift_report`, `_render_drift_table`, `_write_back_findings`)

## Relevant Files

- `src/flow_engineering/cli.py` — added `decision_drift` import, `datetime`/`UTC`/`Any` imports, `DEFAULT_GRAPH_JSON`, `_parse_since`, `_drift_exit_code`, `_serialize_drift_report`, `_render_drift_table`, `_now_iso`, `_write_back_findings`, and the `drift` Click command.
- `tests/unit/test_cli_drift.py` (NEW) — 14 tests across 8 test classes covering exit-code contract, --json, --since, --include-obsolete, --write-back (incl. per-row isolation + read-only default), table output, and --help exit-code documentation.

## Notes for the Reviewer

- The `_FakeClient` test pattern targets `flow_engineering.cli.EngramClient` (NOT `engram_io.EngramClient`) because `cli.py` imports `EngramClient` by name at module load — patching the upstream module wouldn't intercept the local reference. This is documented in test docstrings.
- The CLI reuses `_default_save_backend()` (the same InMemoryBackend used by `flow save` and `flow inspect`) so `--write-back` works without any additional backend wiring in tests.
- `observability.record_drift_summary(report)` is called BEFORE the exit, so even exit-2 paths emit the drift counter contract — REQ-12 invariant is preserved across all exit codes.

**Session**: flow-engineering-batch-e-2026-06-26
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-e
**Engram**: #129
**Next**: Batch F (T1.10 BDD `req9_drift_detection`)