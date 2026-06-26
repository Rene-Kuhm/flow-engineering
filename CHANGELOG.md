# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/).

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