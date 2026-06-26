# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-06-26

### Added
- `flow drift <change>` subcommand — scans Engram observations for binding drift and reports one of six classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`) per REQ-12. Exits `0` (all `still_valid`), `1` (any drift), `2` (`unable_to_verify`) per REQ-11.
- `flow watch --drift` flag — daemon subscribes to `apply-progress` writes and re-runs `scan_change` on `merged` status, emitting a summary line per detected change (REQ-15, REQ-16).
- 8 new `drift_*_total` observability counters (`drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total`, `drift_scan_total`) persisted alongside the existing `flow metrics` JSONL.

### Closed (W2/W3 carry-forwards)
- **W2** — REQ-8 counter reconciliation: spec counter names now match the 8 implementation counters shipped in v0.2.0.
- **W3** — REQ-3 empty-block BDD: empty `code_refs` blocks are treated as `unbound` and counted via `unbound_observations_total`.

### Tests
- 385 / 385 tests passing (`uv run pytest -x --tb=short`).
- 39 BDD scenarios across 9 feature files (`req1..req9` + `req15_drift_daemon`).
- See `openspec/changes/archive/2026-06-26-decision-reality-drift/` for full spec, design, and task breakdown (post-archive).

### Notes
- `decision-reality-drift` shipped via two chained PRs (#1 core detector + counters + W2/W3, #2 verification wiring + `flow watch --drift` + REQ-15/REQ-16).
- `sdd-verify` Step 6 gained a sub-step that surfaces `flow drift <change>` findings before declaring green.

## [0.2.0] - 2026-06-25

### Added
- `code_refs` binding block in Engram observations (`<!-- code_refs -->` marker + JSON).
- `src/flow_engineering/binding.py` — extract / parse / format / split round-trip helpers and `CodeRef` dataclass (REQ-1, REQ-2).
- `src/flow_engineering/graphify_query.py` — CLI wrapper for `graphify query` with sha1+mtime cache (24h TTL) and Jaccard fallback (REQ-6 query layer).
- `scripts/backfill_code_refs.py` — append-only migration script with dry-run / apply / idempotency / pre-image JSONL (REQ-4).
- `src/flow_engineering/auto_suggest_code_refs.py` — save-time auto-suggest with threshold filter and confirmation prompt (REQ-6).
- `flow inspect <change>` — CLI command that renders decision ↔ code bindings as a table with freshness column and per-row parse-error isolation (REQ-7).
- `flow metrics` — observability counters persisted as JSONL in `~/.flow-engineering/metrics.json` (REQ-8).
- `EngramClient.save_phase()` auto-appends an `unbound` `code_refs` block when content lacks a marker (REQ-3).
- 6 `SKILL.md` files (sdd-propose / design / tasks / apply / verify / archive) carry the binding-hook prose so future SDD runs resolve `code_refs` automatically.

### Modified
- `src/flow_engineering/engram_io.py` — `save_phase` validation, `auto_suggest_code_refs` wiring, `load_code_refs` accessor (REQ-3, REQ-5, REQ-6).
- `src/flow_engineering/cli.py` — `--with-suggest` / `--no-suggest` flags on save; new `flow inspect` and `flow metrics` subcommands.
- `src/flow_engineering/orchestrator.py` — minor wiring for the save hook.

### Tests
- 302 / 302 tests passing (`uv run pytest`).
- 45 BDD scenarios across 8 feature files (`req1..req8`).
- See `openspec/changes/archive/2026-06-25-decision-code-linking/` for full spec, design, and task breakdown.

### Notes
- `decision-code-linking` shipped via two chained PRs (#1 core binding + backfill, #2 auto-suggest + surface + observability).
- Verify report: PASS WITH WARNINGS, 0 critical. Three documentation-class warnings carried forward (see sdd/decision-code-linking/verify-report for detail).

## [0.1.0] - prior

Initial baseline. See `FLOW.md` and `README.md` for project context.

[0.2.0]: #020--2026-06-25