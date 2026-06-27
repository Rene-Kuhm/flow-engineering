<!-- tasks.md: graph-snapshots. Source: manual. -->
# Tasks: graph-snapshots

**Change:** `graph-snapshots`
**Builds on:** `proposal.md` (#174) — B+F hybrid (immutable gzipped JSON snapshots + sha256 + auto-safety before rollback); `design.md` (#175) — D1-D13 resolved; `spec.md` (#176) — 7 REQs (REQ-28..34), 14 BDD scenarios
**Date:** 2026-06-26
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (single PR, batched)
**Strict TDD:** ON (per `cross-project-federation` precedent; RED → GREEN → REFACTOR cycle per task)
**Delivery strategy:** single-pr (per task brief; `400-line budget risk: high` mitigated by per-commit work-unit splits per `work-unit-commits` skill)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 8 (T1.1..T1.8) |
| Forecast LOC production | ~625 |
| Forecast LOC test (unit + BDD) | ~975 |
| Forecast LOC grand total | **~1 600** |
| Forecast LOC realistic (×6 TDD multiplier per Engram #113) | **~9 600** |
| BDD feature files | 7 (all NEW) |
| BDD scenarios | 14 (matches spec REQ-28..34) |
| New source files | 1 (`snapshot_manager.py`) |
| Modified source files | 3 (`cli.py`, `decision_drift.py`, `observability.py`) |
| New test files | 3 unit + 1 BDD step glue (`test_snapshot_steps.py`) |
| Chained PRs recommended | No (single PR per task brief; per-commit splits handle review tractability) |
| Chain strategy | N/A (single PR; commits-per-work-unit per `work-unit-commits`) |
| 400-line budget risk | **High** (single PR ~1 600 LOC total, ~9 600 realistic) — mitigated by 8 focused commits each ≤400 LOC |
| Decision needed before apply | No (single-pr is explicit in task brief; per-commit splits mitigate review budget) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A (single PR)
400-line budget risk: High

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC | design.md D-file breakdown (sum of `snapshot_manager.py` ~350 + `cli.py` ~150 + `decision_drift.py` ~25 + `observability.py` ~50 + CHANGELOG/SKILL.md ~15) | ~625 |
| Realistic ×6 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): cross-project-federation PR#1 forecast ~1 205 LOC, actual ~7 200 LOC realistic | ×6 → ~3 750 production realistic + ~5 850 test realistic (~30 LOC/BDD scenario × 14 + ~50 LOC/unit test avg × 30+ unit tests) |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (#112): ≤6 tasks OR ≤150 LOC prod per delegation, default runtime ~15 min | batch B at ~710 LOC is the **TIMEOUT RISK BATCH** |
| Risk: batch B | ~710 LOC across 3 tasks (rollback + drift-pinned seam + CLI surface) at ~6 LOC/min = ~2h | **TIMEOUT RISK** — split into B1 (rollback + drift-pinned) + B2 (CLI surface) if delegation hits 15-min ceiling mid-batch |
| Risk: 400-line review budget | Single PR ~1 600 LOC > 400-line budget | Mitigated by 8 work-unit commits per `work-unit-commits` convention; per-commit diffs ≤400 LOC |

### Suggested Work Units

Single PR (no chained PR split per task brief + proposal #174). The work fits in one ~1 600-LOC PR (~9 600 LOC realistic under Strict TDD). Per-delegation batching (≤6 tasks / ≤150 LOC) is still required at the apply phase because the delegate runtime is ~15 min.

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|-----------------|----------|-----|
| **A** | T1.1 + T1.2 | ~250 | ~350 | SnapshotManager core (`create`/`list`/`show`/`diff`) + first 4 BDD features (REQ-28..31 = 7 scenarios) — atomic foundation; 4 commits RED → GREEN cycle |
| **B** | T1.3 + T1.4 + T1.5 | ~260 | ~450 | `rollback` two-phase safety + `decision_drift.load_graph`/`scan_change` `snap_id` seam + CLI surface (`flow snapshot` group + `--snapshot` flag) + BDD req32/req33 — **TIMEOUT RISK BATCH** |
| **C** | T1.6 + T1.7 + T1.8 | ~115 | ~175 | `prune` retention policy + 4 `snapshot_*` observability counters + BDD req34 + CHANGELOG v0.6.0 + 6 SKILL.md hooks — cohesive close-out |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 11 items are explicitly deferred per spec.md — apply must NOT introduce code for them:

- **Per-project snapshots** — v1 captures the full DB at once; `--project=<key>` is a SHOW-TIME slice only
- **Encrypted snapshots at rest** — OS-level encryption is the user's responsibility
- **Snapshot-based time-travel query API** (`mem_search_as_of(query, timestamp)`) — v2 SDK addition
- **Snapshot streaming or compression beyond gzip** — `--no-compress` for `jq` ergonomics
- **Federated cross-project snapshot diff** — single-project diff only in v1
- **Snapshot immutability enforcement at OS level** (chattr +i, append-only FS) — deployment concern
- **Snapshot tags / labels beyond ISO timestamp + description** — `description` is free-text only
- **Auto-daily / auto-hourly snapshot triggers** — manual-only in v1; cron/Task Scheduler is v2
- **Rollback three-way merge / automatic conflict resolution** — hard-fail + `--force` only
- **Snapshot export / import** (`flow snapshot export <id>` for sharing) — `cp <file>.json.gz` is the v1 escape hatch
- **Vector index snapshots** — v2 follow-up once vector index recovery is needed

---

## Task list (8 tasks, single PR)

### T1.1 — Scaffold `snapshot_manager.py` with `SnapshotManager` class + `create()` + `list()` (REQ-28 + REQ-29)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~150 impl + ~150 tests = ~300
- **Files:**
  - `src/flow_engineering/snapshot_manager.py` (NEW — `SnapshotEnvelopeError`, `SnapshotMeta`/`SnapshotDiff`/`RollbackResult`/`PruneResult` dataclasses, `SnapshotManager` class with constructor + `create()` + `list()`)
  - `tests/unit/test_snapshot_manager.py` (NEW — 8-10 RED fixtures: create round-trip, sha256 stamp, atomic write cleanup, list ordering, empty-dir short-circuit)
- **Dependencies:** none
- **Acceptance criteria:**
  - [x] RED: `test_snapshot_create_writes_gzipped_envelope_with_sha256` fails; `test_snapshot_create_lazy_creates_snapshots_dir` fails; `test_snapshot_create_atomic_write_no_tmp_left` fails; `test_snapshot_create_first_run_labels_initial_state` fails; `test_snapshot_create_explicit_description_wins_over_initial_state` fails; `test_snapshot_list_returns_reverse_chronological` fails; `test_snapshot_list_since_filter_excludes_older` fails; `test_snapshot_list_limit_applies_after_since` fails; `test_snapshot_list_empty_dir_returns_empty_array` fails
  - [x] GREEN: `SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend([...]))` constructor; lazy-creates `snapshots_dir` if missing
  - [x] GREEN: `manager.create(description="pre-deploy-v0.6", trigger="manual")` returns `snap_<ISO>-<6hex>` ID; writes gzipped JSON envelope at `snapshots_dir / f"{id}.json.gz"` via `tempfile.NamedTemporaryFile` + `Path.replace` (no `.tmp` left behind on success)
  - [x] GREEN: Envelope has `schema: 1`, `id`, `created_at` (ISO 8601 UTC with `Z` suffix), `trigger`, `description`, `graph_state: {observations, bindings, project_tags, aliases, drift_history, graph_json}`, `metadata: {obs_count, binding_count, project_count, drift_event_count, graph_node_count, file_size_bytes, sha256, include_graph: True}`
  - [x] GREEN: `metadata.sha256 == hashlib.sha256(canonical_json_dumps(envelope_without_sha256)).hexdigest()` (D9 — canonicalized JSON: sorted keys, no whitespace)
  - [x] GREEN: ID format `snap_<YYYY-MM-DDTHH-MM-SS>-<6hex>` where hex = `secrets.token_hex(3)` (D7 collision-safe on sub-second creates)
  - [x] GREEN: First-run auto-label `initial_state` ONLY when `snapshots_dir` is empty/missing AND no `--description` was passed (Q10 resolution; explicit description always wins)
  - [x] GREEN: `manager.list(since="2026-06-01T00:00:00Z", limit=10)` returns reverse-chronological list of `SnapshotMeta` dataclasses; `--since` filter applied BEFORE `--limit`; empty dir → `[]`
- **Commits:**
  1. `test(unit): RED fixtures for SnapshotManager.create + list (REQ-28 + REQ-29)`
  2. `feat(snapshot): SnapshotManager scaffold with create + list + gzipped JSON + sha256 + atomic write`

### T1.2 — Add `show()` + `diff()` methods + BDD req28 + req29 + req30 + req31 (REQ-28..31 surface)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN
- **LOC:** ~100 impl + ~150 unit tests + ~200 BDD feature+step defs = ~450
- **Files:**
  - `src/flow_engineering/snapshot_manager.py` (extend — `show()` parses + sha256-verifies envelope; `diff(snap_id_a, snap_id_b=None)` returns `SnapshotDiff` with field-level diff for `code_refs` blocks)
  - `tests/unit/test_snapshot_manager.py` (extend — 4-5 RED fixtures: show round-trip, sha256 tamper raises `SnapshotEnvelopeError`, diff invariants, diff 1-arg vs live)
  - `tests/bdd/req28_snapshot_create.feature` (NEW — 2 scenarios)
  - `tests/bdd/req29_snapshot_list.feature` (NEW — 2 scenarios)
  - `tests/bdd/req30_snapshot_show.feature` (NEW — 1 scenario)
  - `tests/bdd/req31_snapshot_diff.feature` (NEW — 2 scenarios)
  - `tests/bdd/test_snapshot_steps.py` (NEW — pytest-bdd step glue shared across all 7 features)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [x] RED: `test_snapshot_show_round_trips_envelope` fails; `test_snapshot_show_tampered_sha256_raises` fails; `test_snapshot_diff_two_arg_returns_added_removed_modified` fails; `test_snapshot_diff_one_arg_vs_live_returns_diff_to_current` fails; `test_snapshot_diff_field_level_code_refs` fails
  - [x] GREEN: `manager.show(snap_id)` parses envelope, verifies `metadata.sha256` matches `canonical_json_dumps(envelope_without_sha256)`, raises `SnapshotEnvelopeError` on mismatch (D11 integrity); returns full envelope dict
  - [x] GREEN: `manager.diff(snap_id_a, snap_id_b=None)`:
    - 2-arg form: compares two stored snapshots
    - 1-arg form: compares stored snapshot against LIVE Engram state via `backend.iter_observations()` (REQ-31 extended form per spec discoveries)
    - Returns `SnapshotDiff(added=[obs_ids], removed=[obs_ids], modified=[{id, field, before, after}], unchanged_count=N, summary="+A -R ~M (unchanged: N)")`
    - For `code_refs` blocks within modified entries, `field` is parsed binding field name (e.g., `code_refs.bound_id.file`, `code_refs.bound_id.label`) — NOT raw content diff (D9 field-level diff)
  - [x] GREEN: BDD feature files contain scenarios matching spec REQ-28..31 (2+2+1+2 = 7 scenarios verbatim):
    - `req28_snapshot_create.feature`: (1) create writes snapshot with all observations + sha256; (2) `--description` stores verbatim + prior snapshot UNCHANGED
    - `req29_snapshot_list.feature`: (1) 3 snapshots returns reverse-chronological; (2) `--since` filter respects lexicographic `created_at >= <iso>` + `--limit` applies AFTER `--since`
    - `req30_snapshot_show.feature`: (1) show renders pretty-printed JSON with all top-level keys
    - `req31_snapshot_diff.feature`: (1) 2-arg form returns added/removed/modified counts; (2) 1-arg form diff against live state
  - [x] GREEN: Step defs use `tmp_path` snapshots_dir + `InMemoryBackend` + `CliRunner`; `InMemoryBackend` seeded with mock observations matching `code_refs` block format
- **Commits:**
  1. `test(unit): RED fixtures for SnapshotManager.show + diff (sha256 tamper, 1-arg vs live, field-level code_refs)`
  2. `feat(snapshot): SnapshotManager.show + diff with structured JSON output + field-level code_refs diff`
  3. `test(bdd): req28+req29+req30+req31 snapshot features with 7 scenarios + step glue`

### T1.3 — Add `rollback()` method with auto-safety snapshot + BDD req32 (REQ-32)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN
- **LOC:** ~80 impl + ~150 unit tests + ~120 BDD feature+step defs = ~350
- **Files:**
  - `src/flow_engineering/snapshot_manager.py` (extend — `rollback(snap_id, *, confirm=False, force=False)` two-phase: Phase 1 auto-safety snapshot via `create(trigger="rollback_safety")`; Phase 2 atomic SQLite `BEGIN IMMEDIATE` apply via `mem_save`/`update_observation`/soft-delete)
  - `tests/unit/test_snapshot_manager.py` (extend — 5 RED fixtures: refuses without `--confirm`, safety snapshot created FIRST, hard-fails on conflicts without `--force`, applies with `--force` + warning, idempotent on retry)
  - `tests/bdd/req32_snapshot_rollback.feature` (NEW — 3 scenarios from spec REQ-32)
  - `tests/bdd/test_snapshot_steps.py` (extend — step glue for REQ-32)
- **Dependencies:** T1.1, T1.2
- **Acceptance criteria:**
  - [x] RED: `test_rollback_without_confirm_raises_refused_error` fails; `test_rollback_with_confirm_creates_safety_snapshot_first` fails; `test_rollback_with_conflicts_without_force_raises_conflict_error` fails; `test_rollback_with_force_overrides_with_warning` fails; `test_rollback_idempotent_on_retry` fails
  - [x] GREEN: `manager.rollback(snap_id, confirm=False)` raises `RollbackRefusedError` with message `{"error": "--confirm required to write; use --dry-run to preview", "snap_id": <id>}` — no writes, no safety snapshot
  - [x] GREEN: `manager.rollback(snap_id, confirm=True)` (no `--force`):
    - Phase 1: calls `manager.create(description=f"pre_rollback_to_{snap_id}", trigger="rollback_safety")` FIRST; Phase 1 MUST succeed before Phase 2 begins (D11 ordering)
    - Computes diff between target snapshot and live state; if conflicts (added/modified/deleted since `created_at`) and not `force`: raises `RollbackConflictError` with JSON `{error: "...", conflicts: [{id, change}]}` — exit code 2 (distinct from confirmation-refusal exit 3)
    - Phase 2 (atomic): `BEGIN IMMEDIATE` transaction → `mem_save` for added, `update_observation` for modified, soft-delete (set `deleted_at`) for removed → `COMMIT`
    - On success: increments `snapshot_rollback_total{success="true"}`; returns `RollbackResult(safety_snapshot_id, target_snapshot_id, applied=summary, forced=False)`
  - [x] GREEN: `manager.rollback(snap_id, confirm=True, force=True)` with conflicts:
    - Emits loud stderr warning `"WARNING: --force override; existing observations will be overwritten"`
    - Increments `snapshot_rollback_total{success="false"}` BEFORE applying (audit trail of forced rollback)
    - Then proceeds with the apply (acknowledging override)
    - Returns `RollbackResult(..., forced=True)`
  - [x] GREEN: Idempotency: re-running `manager.rollback(snap_id, confirm=True)` after a partial Phase 2 failure produces same end state (because Phase 1's new safety snapshot replaces the prior; transaction rolled back atomically)
  - [x] GREEN: BDD `req32_snapshot_rollback.feature` 3 scenarios verbatim from spec:
    1. Without `--confirm`: refuses non-zero exit + JSON error, live state UNCHANGED, no safety snapshot, no counter increment
    2. With `--confirm` (no `--force`): safety snapshot created first, diff applied, live state matches `snap_A`, counter `success=true` increments
    3. With `--confirm` + conflicts (no `--force`): exits code 2 + JSON listing conflict IDs, `snapshot_rollback_total{success="false"}` increments
- **Commits:**
  1. `test(unit): RED fixtures for rollback with --confirm + conflict detection + auto-safety + --force override`
  2. `feat(snapshot): rollback two-phase with auto-safety snapshot + conflict detection + atomic SQLite transaction`
  3. `test(bdd): req32_snapshot_rollback feature with 3 scenarios`

### T1.4 — Extend `decision_drift.load_graph()` + `scan_change()` with `snap_id` kwarg + BDD req33 (REQ-33)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN
- **LOC:** ~30 impl + ~100 unit tests + ~80 BDD feature+step defs = ~210
- **Files:**
  - `src/flow_engineering/decision_drift.py` (modify — `load_graph(graph_json_path=None, *, snap_id=None)` and `scan_change(change_name, *, ..., snap_id=None)` at lines 124 + 188 per design D13 — kwarg-only with `None` default = current behavior)
  - `tests/unit/test_decision_drift_snap_id.py` (NEW — 5 RED fixtures: `load_graph(snap_id=...)` reads frozen content, `scan_change(snap_id=...)` uses frozen observations, mutual-exclusion assertion, default `None` byte-identical, graph.json missing raises `SnapshotGraphMissing`)
  - `tests/bdd/req33_drift_pinned.feature` (NEW — 2 scenarios from spec REQ-33)
  - `tests/bdd/test_snapshot_steps.py` (extend — step glue for REQ-33)
- **Dependencies:** T1.1, T1.2 (needs `SnapshotManager.show()` to load envelope)
- **Acceptance criteria:**
  - [x] RED: `test_load_graph_with_snap_id_reads_frozen_content` fails; `test_load_graph_default_none_byte_identical_to_pre_change` fails; `test_load_graph_snap_id_and_path_mutual_exclusion` fails; `test_scan_change_with_snap_id_uses_frozen_observations` fails; `test_scan_change_snap_id_and_backend_mutual_exclusion` fails
  - [x] GREEN: `decision_drift.load_graph(graph_json_path: Path | None = None, *, snap_id: str | None = None) -> tuple[dict | None, dict | None, float | None]`:
    - When `snap_id=None`: byte-identical to pre-change `load_graph(graph_json_path)` (D13 non-breaking)
    - When `snap_id` set: `graph_json_path` MUST be `None` (asserted; raises `ValueError`); reads envelope from `~/.flow-engineering/snapshots/<snap_id>.json.gz`, extracts `graph_state.graph_json`, returns `(nodes, id_map, snap_mtime)` built from frozen content
    - When envelope's `metadata.include_graph == False`: raises `SnapshotGraphMissing`
  - [x] GREEN: `decision_drift.scan_change(change_name, *, graph_json_path, backend=None, include_obsolete=False, since=None, *, snap_id=None) -> DriftReport`:
    - When `snap_id` set: builds `InMemoryBackend` from snapshot's frozen `graph_state.observations`; passes via `backend=`; calls `load_graph(snap_id=<snap_id>)` internally
    - `snap_id` XOR `backend` (mutual-exclusion assertion raises `ValueError` if both set)
    - Returns `DriftReport` computed against frozen state — different snapshots → different drift reports (D5 headline use case)
  - [x] GREEN: 699+ existing tests pass WITHOUT modification (verified via `uv run pytest` — non-breaking guarantee)
  - [x] GREEN: BDD `req33_drift_pinned.feature` 2 scenarios verbatim from spec:
    1. Snapshot from 2026-06-01 with 0 drift findings; `flow drift vector-semantic-search --snapshot=snap_2026-06-01` returns `DriftReport.class_counts={STILL_VALID: 12}` even though today's live scan returns `{STILL_VALID: 9, STALE_LOCATION: 3}` (D5 worked example)
    2. `flow drift <change>` without `--snapshot` is byte-identical to current behavior (same `class_counts`, same `findings`, same `graph_mtime`)
- **Commits:**
  1. `test(unit): RED fixtures for decision_drift.load_graph(snap_id=...) + scan_change(snap_id=...) kwarg`
  2. `feat(drift): load_graph + scan_change accept snap_id kwarg (NON-BREAKING, mutual-exclusion with backend/graph_json_path)`
  3. `test(bdd): req33_drift_pinned feature with 2 scenarios (frozen-state worked example + non-breaking guarantee)`

### T1.5 — Add `flow snapshot` + `flow drift --snapshot` CLI subcommands (REQ-28..33 CLI surface)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~150 impl + ~200 tests = ~350
- **Files:**
  - `src/flow_engineering/cli.py` (modify — new `flow snapshot` subcommand group with 6 subcommands: `create`, `list`, `show`, `diff`, `rollback`, `prune`; `--snapshot=<snap_id>` flag on existing `flow drift` for REQ-33 surface)
  - `tests/unit/test_cli_snapshot.py` (NEW — 12-15 RED fixtures: 6 subcommands + `--snapshot` flag + non-breaking default + `--no-include-graph` + `--confirm`/`--force` gates + `--since`/`--limit` filter parsing)
- **Dependencies:** T1.1, T1.2, T1.3, T1.4 (all SnapshotManager methods + decision_drift seam must exist for CLI surface to invoke)
- **Acceptance criteria:**
  - [x] RED: `test_cli_snapshot_create_invokes_manager_create` fails; `test_cli_snapshot_list_with_since_flag_parses` fails; `test_cli_snapshot_show_renders_envelope_or_errors` fails; `test_cli_snapshot_diff_two_arg_and_one_arg_forms` fails; `test_cli_snapshot_rollback_requires_confirm` fails; `test_cli_snapshot_prune_dry_run_default` fails; `test_cli_drift_snapshot_flag_invokes_scan_change_with_kwarg` fails; `test_cli_drift_without_snapshot_byte_identical` fails; 8+ more for `--no-include-graph`, `--confirm`, `--force`, `--keep-last=0` safety gate
  - [x] GREEN: `flow snapshot create [--description=<text>] [--no-include-graph] [--project=<key>]` invokes `SnapshotManager.create()` with the right kwargs; exits 0 on success
  - [x] GREEN: `flow snapshot list [--since=<iso>] [--limit=N] [--json]` parses flags via stdlib `csv` for multi-value (not needed here) + `argparse` for `--since`/`--limit`; emits JSON array (or table when stdout is TTY); empty dir → `[]` exit 0
  - [x] GREEN: `flow snapshot show <snap_id>` parses + sha256-verifies envelope; emits pretty-printed JSON to stdout; on `SnapshotEnvelopeError` emits JSON error to stderr + non-zero exit
  - [x] GREEN: `flow snapshot diff <snap_id_a> [<snap_id_b>] [--json]`:
    - 2-arg form: compares two stored snapshots
    - 1-arg form (extended per spec discoveries): compares stored snapshot vs LIVE state via `backend.iter_observations()`
    - Emits structured JSON `{added, removed, modified, unchanged_count, summary}`
  - [x] GREEN: `flow snapshot rollback <snap_id> [--confirm] [--force]`:
    - Without `--confirm`: emits JSON error to stderr, exits 3 (confirmation-refusal), no writes
    - With `--confirm` + no conflicts: Phase 1 safety snapshot first, Phase 2 atomic apply, exits 0, emits JSON `{safety_snapshot_id, target_snapshot_id, applied, forced}` to stdout
    - With `--confirm` + conflicts (no `--force`): exits 2 (conflict), emits JSON error listing conflict IDs
    - With `--confirm --force` + conflicts: emits stderr warning + applies + exits 0 with `forced: true`
  - [x] GREEN: `flow snapshot prune [--keep-last=N] [--keep-days=N] [--max-total-size-mb=N] [--confirm] [--force]`:
    - Default (no flags): dry-run JSON `{would_delete, would_keep, freed_bytes_estimate}` to stdout, exits 0, no deletes
    - With `--confirm` + 1 filter: actually deletes; increments `snapshot_pruned_total{reason}` per deletion
    - `--keep-last=0` requires BOTH `--confirm` AND `--force` (D10 safety gate); refuses non-zero if either missing
    - `--keep-last=0` mutually exclusive with `--keep-days` or `--max-total-size-mb`
  - [x] GREEN: `flow drift <change> --snapshot=<snap_id>`:
    - New `--snapshot=<snap_id>` opt-in flag on existing `flow drift` command
    - When set: invokes `decision_drift.scan_change(change_name, *, ..., snap_id=<snap_id>, backend=None)` (REQ-33)
    - When absent: byte-identical to pre-change behavior (D13 non-breaking)
- **Commits:**
  1. `test(unit): RED fixtures for flow snapshot {create,list,show,diff,rollback,prune} subcommands + flow drift --snapshot flag`
  2. `feat(cli): flow snapshot {create,list,show,diff,rollback,prune} subcommand group with --confirm/--force/--no-include-graph flags`
  3. `feat(cli): flow drift --snapshot=<snap_id> flag (NON-BREAKING — wraps decision_drift.scan_change with snap_id kwarg)`

### T1.6 — Add `prune()` method with retention policy + BDD req34 (REQ-34)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN
- **LOC:** ~50 impl + ~100 unit tests + ~60 BDD feature+step defs = ~210
- **Files:**
  - `src/flow_engineering/snapshot_manager.py` (extend — `prune(*, keep_last=None, keep_days=None, max_total_size_mb=None, confirm=False, force=False) -> PruneResult` with retention policy)
  - `tests/unit/test_snapshot_manager.py` (extend — 4-5 RED fixtures: dry-run default reports `would_delete` + no deletes, `--confirm` deletes, `--keep-last=0` requires `--confirm`+`--force`, filter combinations)
  - `tests/bdd/req34_snapshot_prune.feature` (NEW — 2 scenarios from spec REQ-34 — added to align with spec's 7 BDD feature file plan; task brief did not include this file explicitly)
  - `tests/bdd/test_snapshot_steps.py` (extend — step glue for REQ-34)
- **Dependencies:** T1.1, T1.2 (needs `list()` to enumerate snapshots)
- **Acceptance criteria:**
  - [x] RED: `test_prune_dry_run_reports_would_delete_no_actual_delete` fails; `test_prune_keep_last_confirm_actually_deletes` fails; `test_prune_keep_last_zero_requires_confirm_and_force` fails; `test_prune_keep_days_excludes_older` fails; `test_prune_max_size_keeps_newest_until_fits` fails
  - [x] GREEN: `manager.prune(*, keep_last=None, keep_days=None, max_total_size_mb=None, confirm=False, force=False) -> PruneResult`:
    - At least ONE of `keep_last` / `keep_days` / `max_total_size_mb` required (else raises `PruneNoFilterError`)
    - Default behavior (no `confirm`): dry-run, exits 0, returns `PruneResult(deleted=[], would_delete=[ids], would_keep=[ids], freed_bytes=N)` — no actual deletes
    - With `confirm=True`: actually deletes; `deleted=len(would_delete)`; increments `snapshot_pruned_total{reason=<age|count|size>}` by `len(deleted)` per call
    - `keep_last=0` requires BOTH `confirm=True` AND `force=True` (D10 two-flag safety gate); raises `PruneSafetyGateError` if either missing
    - `keep_last=0` mutually exclusive with `keep_days` or `max_total_size_mb` (raises `PruneFilterConflictError` if combined)
    - Reason value for counter: `keep_days` → `reason="age"`; `keep_last` → `reason="count"`; `max_total_size_mb` → `reason="size"` (frozen set `SNAPSHOT_PRUNE_REASON_VALUES`)
  - [x] GREEN: BDD `req34_snapshot_prune.feature` 2 scenarios verbatim from spec:
    1. With 5 snapshots, `flow snapshot prune --keep-last=3` (no `--confirm`) shows `would_delete` + `would_keep` JSON, deletes no files, exits 0
    2. `flow snapshot prune --keep-last=2 --confirm` deletes 3 oldest, exits 0, counter `snapshot_pruned_total{reason="count"}` reads K+3
- **Commits:**
  1. `test(unit): RED fixtures for prune with retention policy + --keep-last=0 safety gate`
  2. `feat(snapshot): prune with retention policy (keep_last/keep_days/max_total_size_mb) + dry-run default + safety gates`
  3. `test(bdd): req34_snapshot_prune feature with 2 scenarios (added per spec 7-feature-file plan)`

### T1.7 — Add 4 observability counters + `record_snapshot_event` helper (REQ-22/26 pattern)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~50 impl + ~100 unit tests = ~150
- **Files:**
  - `src/flow_engineering/observability.py` (modify — `SNAPSHOT_COUNTER_NAMES` catalog with 4 names; `SNAPSHOT_TRIGGER_VALUES` / `SNAPSHOT_ROLLBACK_VALUES` / `SNAPSHOT_PRUNE_REASON_VALUES` frozensets; `record_snapshot_event(name, **fields)` helper mirroring `record_federated_summary` at `observability.py:377`)
  - `tests/unit/test_observability_snapshot.py` (NEW — 8 RED fixtures: catalog has 4 names; `record_snapshot_event` emits correct shape; trigger/success/reason field validation against frozensets; fail-open on `OSError`; integration with `SnapshotManager.create`/`diff`/`rollback`/`prune` increments counters)
- **Dependencies:** T1.1, T1.2, T1.3, T1.6 (counters are emitted from SnapshotManager methods; integration tested via `record_snapshot_event` invocation paths)
- **Acceptance criteria:**
  - [x] RED: `test_snapshot_counter_names_catalog_has_4` fails; `test_record_snapshot_event_emits_correct_shape` fails; `test_record_snapshot_event_validates_trigger_field` fails; `test_record_snapshot_event_validates_success_field` fails; `test_record_snapshot_event_validates_reason_field` fails; `test_record_snapshot_event_fail_open_on_oserror` fails; `test_snapshot_manager_create_increments_counter` fails; `test_snapshot_manager_rollback_increments_counter` fails
  - [x] GREEN: `SNAPSHOT_COUNTER_NAMES: list[str] = ["snapshot_created_total", "snapshot_diff_invoked_total", "snapshot_rollback_total", "snapshot_pruned_total"]` (4 names, parallels `FEDERATED_COUNTER_NAMES` at `observability.py:89` per spec reference)
  - [x] GREEN: `SNAPSHOT_TRIGGER_VALUES: frozenset[str] = frozenset({"manual", "auto", "rollback_safety"})`
  - [x] GREEN: `SNAPSHOT_ROLLBACK_VALUES: frozenset[str] = frozenset({"success", "failure"})`
  - [x] GREEN: `SNAPSHOT_PRUNE_REASON_VALUES: frozenset[str] = frozenset({"age", "count", "size"})`
  - [x] GREEN: `record_snapshot_event(name, **fields) -> None`:
    - Validates `name` is in `SNAPSHOT_COUNTER_NAMES` (else logs warning + no-op)
    - For `snapshot_created_total`: validates `trigger` field is in `SNAPSHOT_TRIGGER_VALUES`
    - For `snapshot_rollback_total`: validates `success` field is in `SNAPSHOT_ROLLBACK_VALUES`
    - For `snapshot_pruned_total`: validates `reason` field is in `SNAPSHOT_PRUNE_REASON_VALUES`
    - On invalid field: falls back to safe default + logs warning (never raises)
    - Failures absorbed by `increment` — `OSError` swallowed (per REQ-22/26 precedent)
  - [x] GREEN: Integration: `SnapshotManager.create()` calls `record_snapshot_event("snapshot_created_total", trigger="manual")`; `manager.diff()` calls `record_snapshot_event("snapshot_diff_invoked_total")`; `manager.rollback()` calls `record_snapshot_event("snapshot_rollback_total", success=True|False)`; `manager.prune()` calls `record_snapshot_event("snapshot_pruned_total", reason="age"|"count"|"size")` per deletion
  - [x] GREEN: Existing `VECTOR_COUNTER_NAMES` and `FEDERATED_COUNTER_NAMES` catalogs byte-identical (verified via test snapshot)
  - [x] GREEN: `flow metrics` summary output includes all 4 `snapshot_*` counter rows
- **Commits:**
  1. `test(unit): RED fixtures for 4 SNAPSHOT_COUNTER_NAMES + record_snapshot_event helper + frozenset validation`
  2. `feat(observability): 4 snapshot_* counters + record_snapshot_event helper + frozenset validation (mirrors FEDERATED pattern)`

### T1.8 — CHANGELOG.md v0.6.0 entry + 6 SKILL.md "Graph snapshots hook" prose updates

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~15 CHANGELOG + ~25 prose (~4 per file × 6) = ~40
- **Files:**
  - `CHANGELOG.md` (modify, repo — new `## [0.6.0] - <date>` section above `[0.5.0]`)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify, runtime — NOT in repo)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify, runtime)
- **Dependencies:** all T1.1..T1.7
- **Acceptance criteria:**
  - [x] CHANGELOG v0.6.0 entry lists:
    - `flow snapshot {create,list,show,diff,rollback,prune}` subcommand group
    - `flow drift --snapshot=<id>` flag (drift-pinned scan via frozen state)
    - Gzipped JSON snapshot format with sha256 over canonicalized JSON
    - Auto-safety snapshot before rollback destructive change (two-phase commit)
    - Prune retention policy with `--confirm`/`--force` safety gates
    - 4 new `snapshot_*` observability counters + `record_snapshot_event` helper
    - `decision_drift.load_graph(snap_id=)` + `scan_change(snap_id=)` NON-BREAKING kwarg extensions
    - 14 new BDD scenarios across 7 feature files
  - [x] 6 SKILL.md files have `## Graph snapshots hook` section (3-5 lines each) naming all 7 REQs (REQ-28..34) and referencing `SnapshotManager`, `flow snapshot` group, `flow drift --snapshot=<id>`, `~/.flow-engineering/snapshots/`, sha256 tamper detection, 4 `snapshot_*` counters
  - [x] CHANGELOG entry follows `[0.5.0]` format (Added / Tests / Notes sections)
- **Commit:**
  1. `docs(release): CHANGELOG v0.6.0 entry + 6 SKILL.md graph snapshots hooks`

---

## Apply Batches (≤6 tasks OR ≤150 LOC prod per delegation)

Per-delegation batch ceiling from Engram #112 pattern (`apply-batches-split-into-6-tasks-per-delegation`). Default delegate runtime is ~15 min; larger batches TIMEOUT.

### Single-PR batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **A** | T1.1 + T1.2 | ~750 | SnapshotManager core (`create`/`list`/`show`/`diff`) + first 4 BDD features (REQ-28..31 = 7 scenarios) — atomic foundation; 5 commits RED → GREEN cycle |
| **B** | T1.3 + T1.4 + T1.5 | ~910 | `rollback` two-phase safety + `decision_drift.load_graph`/`scan_change` `snap_id` seam + CLI surface (`flow snapshot` group + `--snapshot` flag) + BDD req32/req33 — **TIMEOUT RISK BATCH** |
| **C** | T1.6 + T1.7 + T1.8 | ~400 | `prune` retention policy + 4 `snapshot_*` observability counters + BDD req34 + CHANGELOG v0.6.0 + 6 SKILL.md hooks — cohesive close-out |

**Batch B risk mitigation:** at ~910 LOC, batch B is the highest timeout risk (~2.5h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **B1** = T1.3 + T1.4 (rollback two-phase + decision_drift seam) — ~560 LOC; library cohesion (snapshot_manager.py + decision_drift.py)
- **B2** = T1.5 (CLI surface only) — ~350 LOC; CLI-only work (cli.py + test_cli_snapshot.py)

If sub-agent reports progress as "rollback + decision_drift seam landed, CLI remaining", abort and launch B2 as continuation.

### Branch targeting

- **Single PR → `main`.** No chained PR split per task brief + proposal #174 recommendation. Per-delegation batching is internal to the apply phase only; the final PR merges the cumulative result of all 3 batches.
- **Squash merge** for the final PR (preserves linear history, single commit `feat: graph-snapshots v0.6.0`).
- Each batch's commits land on the PR branch; PR merges after batch C completes + `uv run pytest` is green + 699+ existing tests pass.

---

## Open follow-ups for sdd-archive (after PR merges)

| # | Item | Owner |
|---|------|-------|
| 1 | Spec counter catalog in `openspec/specs/observability/spec.md` for the 4 new `snapshot_*` counters (REQ-22/26 pattern) | sdd-archive |
| 2 | Bump `pyproject.toml` version `0.5.0` → `0.6.0` (matches CHANGELOG entry) | sdd-archive |
| 3 | Verify `MEMORY.md` or AGENTS.md mentions `flow snapshot` workflow + `--snapshot` flag for future contributors | sdd-archive |
| 4 | Cross-impact: confirm `cross-project-federation` (REQ-23..27) tests stay green; snapshots work on top of federated search without coupling | sdd-archive |
| 5 | Update README to mention `~/.flow-engineering/snapshots/` runtime dir + first-snapshot auto-label `initial_state` UX nudge | sdd-archive |
| 6 | Consider follow-up change for v2 deferred items: per-project snapshots, encrypted snapshots at rest, snapshot-based time-travel API (`mem_search_as_of`), auto-daily triggers, vector index snapshots | sdd-archive |

---

## Structured Metadata

- **total_tasks:** 8 (T1.1..T1.8)
- **pr_split:** single PR (no chained split per task brief + proposal #174)
- **forecast_loc_production:** ~625
- **forecast_loc_test:** ~975
- **forecast_loc_grand_total:** ~1 600
- **forecast_loc_realistic:** ~9 600 (×6 TDD multiplier per Engram #113 cross-project-federation precedent + ~30 LOC per BDD scenario × 14 scenarios)
- **batches:** 3 (A=2 tasks, B=3 tasks, C=3 tasks)
- **batch_b_timeout_risk:** HIGH (~910 LOC; mitigation = split into B1 + B2 if delegation hits 15-min ceiling)
- **review_workload_forecast:**
  - `400_line_budget_risk`: high (single PR ~1 600 LOC; ~9 600 realistic; ~700 per apply batch avg)
  - `chained_prs_recommended`: no (per task brief + proposal #174; per-commit work-unit splits per `work-unit-commits` skill mitigate review budget)
  - `decision_needed_before_apply`: no (single-pr is explicit in task brief; per-commit splits mitigate 400-line review budget)
  - `chain_strategy`: N/A (single PR; 8 work-unit commits per `work-unit-commits` convention)
- **strict_tdd:** on (RED → GREEN → REFACTOR per task)
- **bdd_feature_files:** 7 NEW (req28..req34)
- **bdd_scenarios:** 14 (matches spec #176 REQ-28:2 + REQ-29:2 + REQ-30:1 + REQ-31:2 + REQ-32:3 + REQ-33:2 + REQ-34:2 = 14)
- **out_of_scope_count:** 11 (preserved from spec #176)
- **file_created:** `C:\dev\proyects\flow-engineering\openspec\changes\graph-snapshots\tasks.md`
- **next_recommended:** `sdd-apply graph-snapshots batch A` (T1.1 + T1.2, ~750 LOC, ~17-20 min)
