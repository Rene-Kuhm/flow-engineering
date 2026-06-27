<!-- Spec: graph-snapshots. Source: manual. -->
# Spec: graph-snapshots

**Change:** `graph-snapshots`
**Builds on:** `proposal.md` (B+F hybrid: immutable gzipped JSON snapshots at `~/.flow-engineering/snapshots/snap_<ISO>-<hex>.json.gz`, sha256-stamped, with auto-safety snapshot before rollback), `design.md` (D1-D13 resolved: NON-BREAKING `snap_id` kwarg on `load_graph`/`scan_change`, hard-fail rollback conflict policy with `--force` override, frozen-state drift-pinned semantics, dry-run prune default, canonical-JSON sha256, two-phase rollback with safety-first snapshot)
**Date:** 2026-06-26
**Status:** SPECIFIED → ready for sdd-tasks

## Goal

`flow-engineering` models three graph-shaped concepts — the **Engram observation graph** (observations + `code_refs` bindings), the **drift history** (via `decision_drift.scan_change`), and the external **graphify `graph.json` correlator** — but every change mutates in place with **zero historical record**. `revision_count` exists but is a dedup counter, not history. This change ships an **additive** immutable JSON snapshot subsystem so users can answer "what did the graph look like last Tuesday?", "undo the last 3 changes", and "did bindings drift gradually or suddenly?" — without touching the live `EngramBackend` write paths except during an explicit `--confirm`'d rollback.

The drift seam is already in place (`decision_drift.load_graph(graph_json_path)` accepts a Path per `decision-reality-drift` archive #136). Snapshots extend that seam with a kwarg-only `snap_id` parameter — **NON-BREAKING**, default `None` = current behavior. Snapshots are gzipped JSON files with sha256 of canonicalized JSON stamped for tamper detection; `flow snapshot show <id> | jq` is the headline ergonomics win.

---

## Snapshot file naming and envelope

| Aspect | Value | Rationale |
|---|---|---|
| File name | `snap_<YYYY-MM-DDTHH-MM-SS>-<6-hex>.json.gz` | ISO + random hex suffix = collision-safe on sub-second creates (D7) |
| Default compression | gzip ON; `--no-compress` flag writes `.json` | Storage cheap; `zcat file \| jq` is the headline ergonomics |
| Envelope schema | `{schema: 1, id, created_at, trigger, description, graph_state: {observations, bindings, project_tags, aliases, drift_history, graph_json}, metadata: {obs_count, binding_count, project_count, drift_event_count, graph_node_count, file_size_bytes, sha256, include_graph}}` | `schema_version 1` matches `code_refs` precedent |
| SHA256 input | **Canonicalized JSON** (sorted keys, no whitespace) | Deterministic across gzip implementations (D9) |
| `graph_json` field | Default ON (full content) | Required for REQ-33 drift-pinned semantics; `--no-include-graph` flag opts out |
| Default trigger | `"manual"`; only other trigger in v1 is `"rollback_safety"` (D3) | Auto-daily deferred to v2 |
| Atomic write | `tempfile + Path.replace`; no `.tmp` left behind | Crash-safe (D11) |

**Trigger values**: `manual | auto | rollback_safety` (frozen set; `SNAPSHOT_TRIGGER_VALUES` in `observability.py`).
**First-run label**: when `~/.flow-engineering/snapshots/` is empty/missing, the first `flow snapshot create` auto-uses `description="initial_state"` UNLESS `--description=<other>` is explicit (Q10 resolution).

---

## PR#1 — Snapshot subsystem + drift-pinned seam

### REQ-28: `flow snapshot create [--description] [--no-include-graph] [--project=<key>]` — manual snapshot creation

The system SHALL provide a new CLI subcommand `flow snapshot create` that writes one gzipped JSON snapshot file to `~/.flow-engineering/snapshots/snap_<ISO>-<6hex>.json.gz`. The snapshot file name MUST be of the form `snap_<YYYY-MM-DDTHH-MM-SS>-<secrets.token_hex(3)>.json.gz` where the ISO segment is the snapshot's `created_at` in UTC and the hex segment is 6 lowercase hex characters; the combination SHALL be collision-safe even on simultaneous creation, clock skew, or DST transitions (verified by `os.path.exists` + retry). Each snapshot envelope MUST include `schema: 1`, `id`, `created_at` (ISO 8601 UTC with `Z` suffix), `trigger` (default `"manual"`), `description`, `graph_state` (frozen: observations, parsed `code_refs` bindings, project_tags, aliases, last N drift metrics, optional `graph_json`), and `metadata` including `sha256` computed over the **canonicalized JSON** (sorted keys, no whitespace). The snapshot file MUST be written atomically (`tempfile.NamedTemporaryFile` + `Path.replace`) so a crash mid-write cannot corrupt the directory.

The `--description <text>` flag SHALL store user-supplied text in `envelope.description`; absent the flag, the description defaults to the empty string UNLESS the snapshot directory is empty/missing (in which case it defaults to `"initial_state"` — explicit `--description` always wins). The `--no-include-graph` flag SHALL exclude `graph_state.graph_json` from the envelope (saves ~5 MB/snapshot but disables REQ-33 drift-pinned scans against that snapshot — they MUST raise `SnapshotGraphMissing` error). The `--project=<key>` flag SHALL slice the snapshot to a single project at read time only (the on-disk envelope always holds the full DB per the `mem_search_federated(projects=None)` parity rule from REQ-23/REQ-24 D1); this flag is a SHOW-TIME filter, not a CREATE-TIME filter.

#### Scenario: `flow snapshot create` writes a snapshot with all current observations and a sha256

- GIVEN an Engram backend seeded with 5 observations (3 in `flow-engineering`, 2 in `mockup-2-blog`) containing the term "drift"
- AND the snapshot directory `~/.flow-engineering/snapshots/` does NOT exist (lazy creation)
- WHEN `flow snapshot create` runs (no flags)
- THEN the process exits `0`
- AND a file matching `snap_<ISO>-<6hex>.json.gz` exists in `~/.flow-engineering/snapshots/`
- AND the parsed envelope `schema == 1` and `metadata.sha256` matches `hashlib.sha256(canonical_json_dumps(envelope)).hexdigest()` computed over the envelope WITHOUT the `sha256` field itself
- AND `graph_state.observations` contains all 5 observations (full DB, not filtered)
- AND the counter `snapshot_create_total{trigger="manual"}` increments by `1`

#### Scenario: `flow snapshot create --description "pre-deploy-v0.6"` stores the description in metadata

- GIVEN the same backend as the previous scenario
- AND the snapshot directory exists with 1 prior snapshot (so the auto-label `initial_state` is NOT applied)
- WHEN `flow snapshot create --description "pre-deploy-v0.6"` runs
- THEN the new snapshot file exists
- AND `envelope.description == "pre-deploy-v0.6"` (verbatim, no trimming)
- AND the prior snapshot file is UNCHANGED (atomic write does not touch siblings)
- AND `snapshot_create_total{trigger="manual"}` increments by `1` again

---

### REQ-29: `flow snapshot list [--since=<iso>] [--limit=N] [--json]` — list snapshots

The system SHALL provide a new CLI subcommand `flow snapshot list` that reads `~/.flow-engineering/snapshots/` and returns a list of snapshot metadata records in **reverse chronological order** (newest `created_at` first). Each entry MUST be a JSON object with the keys: `snap_id`, `created_at`, `trigger`, `description`, `obs_count`, `size_bytes`. The `--since=<iso>` flag SHALL filter results to snapshots whose `created_at >= <iso>` (lexicographic string comparison because the timestamp is ISO 8601 with `Z` suffix — verified sort-safe). The `--limit=N` flag SHALL truncate the list to the N most recent AFTER applying `--since` filtering; default `limit=50`. When the snapshot directory is empty or missing, the command SHALL output `[]` (empty JSON array) and exit `0` (NOT an error).

#### Scenario: After creating 3 snapshots, `flow snapshot list` returns 3 entries in reverse chronological order

- GIVEN 3 snapshots created in chronological order: `snap_A` (T1), `snap_B` (T2), `snap_C` (T3) where T1 < T2 < T3
- WHEN `flow snapshot list` runs (no flags)
- THEN stdout is a JSON array of length `3`
- AND the first entry is `snap_C` (newest first)
- AND the second entry is `snap_B`
- AND the third entry is `snap_A` (oldest last)
- AND each entry has all 6 required keys (`snap_id`, `created_at`, `trigger`, `description`, `obs_count`, `size_bytes`)
- AND the process exits `0`

#### Scenario: `flow snapshot list --since=<recent_iso>` returns only snapshots at or after that timestamp

- GIVEN 5 snapshots created at T1 < T2 < T3 < T4 < T5
- WHEN `flow snapshot list --since=<T3_iso>` runs
- THEN the result array contains EXACTLY the snapshots at T3, T4, T5 (length 3)
- AND snapshots at T1 and T2 are excluded (T1.created_at < T3_iso, T2.created_at < T3_iso)
- AND the ordering within the filtered set is still reverse chronological (T5 first, T3 last)
- AND combining `--since=<T3_iso> --limit=2` returns the 2 most recent (T5, T4) — limit applies AFTER since-filter

> **Drift note (post-drift-hardening, 2026-06-27)**: `SnapshotMeta.size_bytes` is the
> canonical field name returned by `flow snapshot list` and `flow snapshot show`.
> The on-disk envelope still uses `metadata.file_size_bytes` (per the envelope
> schema at line 23); the dataclass field uses the shorter name `size_bytes`.
> Per W25 carry-forward resolution; impl at `snapshot_manager.py:101-121` is
> unchanged. The `SnapshotMeta.pinned: bool` retention-pin field is also
> documented in the dataclass (per S18); it is NOT returned by `flow snapshot list`
> (kept as envelope-only metadata) but IS honored by `flow snapshot prune` to
> skip pinned snapshots.

---

### REQ-30: `flow snapshot show <snap_id>` — print full snapshot content

The system SHALL provide a new CLI subcommand `flow snapshot show <snap_id>` that parses the snapshot envelope and prints the full snapshot content as pretty-printed JSON to stdout. When the `<snap_id>` file is not found in `~/.flow-engineering/snapshots/`, the command SHALL exit with a non-zero status and emit a JSON error object `{"error": "snapshot not found", "snap_id": "<provided>"}` to stderr. When the file is found but the sha256 in `envelope.metadata.sha256` does NOT match `hashlib.sha256(canonical_json_dumps(envelope_without_sha256)).hexdigest()` (i.e., the envelope has been tampered with or the gzip is corrupt), the command SHALL raise `SnapshotEnvelopeError` and exit non-zero — it MUST NOT silently render a tampered envelope.

#### Scenario: After creating a snapshot, `flow snapshot show <snap_id>` prints the JSON with all fields

- GIVEN a snapshot file `snap_<ISO>-<6hex>.json.gz` containing a valid envelope with `metadata.sha256` matching its content
- WHEN `flow snapshot show snap_<ISO>-<6hex>` runs
- THEN the process exits `0`
- AND stdout is the parsed envelope as pretty-printed JSON (`json.dumps(envelope, indent=2)`)
- AND the printed JSON includes all top-level keys: `schema`, `id`, `created_at`, `trigger`, `description`, `graph_state`, `metadata`
- AND stdout is `jq`-parseable (valid JSON; no gzip wrapper when stdout is a pipe)
- AND if the file is missing OR the sha256 does NOT match the canonical-JSON hash, the command exits non-zero with a `SnapshotEnvelopeError`-shaped JSON error to stderr (unit-tested separately; BDD covers the happy path only)

---

### REQ-31: `flow snapshot diff <snap_id_a> [<snap_id_b>]` — diff snapshots (and snapshot-to-current)

The system SHALL provide a new CLI subcommand `flow snapshot diff` with TWO calling forms:
- **2-arg form**: `flow snapshot diff <snap_id_a> <snap_id_b>` compares two stored snapshots and shows changes from `a` to `b`.
- **1-arg form (extended)**: `flow snapshot diff <snap_id>` compares one stored snapshot against the CURRENT live Engram state and shows changes from `<snap_id>` to live.

The output MUST be a structured JSON object with keys: `added` (list of observation IDs present in `b` but not in `a`), `removed` (list of observation IDs present in `a` but not in `b`), `modified` (list of `{id, field, before, after}` objects — one per observation whose `content` differs between `a` and `b`), `unchanged_count` (integer — observations whose `content` is byte-identical between `a` and `b`), and `summary` (human-readable string of the form `"+<added> -<removed> ~<modified> (unchanged: <unchanged_count>)"`). For `code_refs` blocks within `modified` entries, the `field` SHALL be the parsed binding field name (e.g., `code_refs.bound_id.file`, `code_refs.bound_id.label`) — block-level diff, NOT raw content diff. Either or both `<snap_id_a>` / `<snap_id_b>` being unknown SHALL exit non-zero with the same `SnapshotEnvelopeError` shape as REQ-30.

#### Scenario: After creating snapshot A with 3 obs and B with 5 obs (2 added between), `flow snapshot diff A B` shows 2 added observations

- GIVEN snapshot `snap_A` was created when the Engram backend contained 3 observations with IDs `[1, 2, 3]`
- AND after `snap_A` was created, 2 new observations (IDs `[4, 5]`) were saved via `mem_save`
- AND snapshot `snap_B` was then created capturing all 5 observations
- WHEN `flow snapshot diff snap_A snap_B` runs
- THEN stdout is a JSON object with `added == [4, 5]` (order-independent), `removed == []`, `modified == []`, `unchanged_count == 3`, `summary == "+2 -0 ~0 (unchanged: 3)"`
- AND the process exits `0`

#### Scenario: With no second argument, `flow snapshot diff <snap_id>` shows changes from snap_id to current state

- GIVEN snapshot `snap_A` was created with observations `[1, 2, 3]`
- AND the LIVE Engram backend now contains `[1, 2, 3, 4, 5]` (2 added since snapshot) AND observation `2` was updated (`update_observation`)
- WHEN `flow snapshot diff snap_A` runs (one argument)
- THEN the diff is computed against LIVE state (not another snapshot)
- AND `added == [4, 5]`, `removed == []`
- AND `modified` contains exactly one entry: `{id: 2, field: "content", before: <original>, after: <updated>}`
- AND `unchanged_count == 2` (observations 1 and 3)
- AND `summary == "+2 -0 ~1 (unchanged: 2)"`
- AND the process exits `0`

---

### REQ-32: `flow snapshot rollback <snap_id> [--confirm] [--force]` — restore graph state with safety net

The system SHALL provide a new CLI subcommand `flow snapshot rollback <snap_id>` that restores the live Engram state to match a stored snapshot. The command SHALL refuse to run without the `--confirm` flag (non-zero exit + JSON error `{"error": "--confirm required to write; use --dry-run to preview", "snap_id": "<provided>"}` to stderr). When `--confirm` is present, the command SHALL execute a TWO-PHASE operation:

- **Phase 1 (always runs first)**: create an auto-safety snapshot of the CURRENT live state with `trigger="rollback_safety"` and `description=f"pre_rollback_to_<snap_id>"`. Phase 1 MUST succeed before Phase 2 begins. If Phase 1 fails, the rollback aborts with non-zero exit and no live mutation occurs.

- **Phase 2 (atomic)**: compute the diff between the target snapshot and the live state. If any observation has been added, modified, or deleted since the target snapshot's `created_at`, the command SHALL refuse (non-zero exit + JSON error listing the conflicting `observation_id`s and their change direction) UNLESS `--force` is also passed. With `--force`, the command SHALL emit a loud warning to stderr (`"WARNING: --force override; existing observations will be overwritten"`) AND increment `snapshot_rollback_total{success="false"}` BEFORE applying (audit trail of forced rollbacks). Apply the target snapshot's state inside a single SQLite transaction (`BEGIN IMMEDIATE` + `COMMIT` or `ROLLBACK`): `mem_save` for added observations, `update_observation` for modified observations, soft-delete (set `deleted_at`) for removed observations. If Phase 2 is interrupted (power loss, Ctrl-C), the SQLite transaction rolls back atomically; live state is unchanged, the auto-safety snapshot from Phase 1 exists, and the user can retry by running `flow snapshot rollback <safety_snap_id>` (which inverts to the inverse restore).

On success, `snapshot_rollback_total{success="true"}` increments by `1`; the `RollbackResult` returned to the caller includes `safety_snapshot_id`, `target_snapshot_id`, `applied` (diff summary string), and `forced` (bool).

#### Scenario: `flow snapshot rollback <snap_id>` without `--confirm` refuses with non-zero exit

- GIVEN a snapshot `snap_A` exists
- AND the live state matches `snap_A` exactly (no drift)
- WHEN `flow snapshot rollback snap_A` runs (no `--confirm`)
- THEN the process exits non-zero
- AND stderr contains the JSON object `{"error": "--confirm required to write; use --dry-run to preview", "snap_id": "snap_A"}`
- AND the live Engram state is UNCHANGED (no writes)
- AND NO auto-safety snapshot was created (Phase 1 does not start without `--confirm`)
- AND no counter is incremented

#### Scenario: `flow snapshot rollback <snap_id> --confirm` creates a safety snapshot first, restores state, exits 0

- GIVEN snapshot `snap_A` with observations `[1, 2, 3]`
- AND the live state currently has `[1, 2]` (observation 3 was deleted by accident)
- WHEN `flow snapshot rollback snap_A --confirm` runs (no `--force`)
- THEN Phase 1 creates a new snapshot file with `trigger="rollback_safety"` and `description="pre_rollback_to_snap_A"` capturing the CURRENT `[1, 2]` state
- AND Phase 2 applies the diff: observation 3 is restored via `mem_save` (or `update_observation` with `deleted_at=None`)
- AND the live state after the command is `[1, 2, 3]` (matches `snap_A`)
- AND `snapshot_rollback_total{success="true"}` increments by `1`
- AND the JSON result to stdout contains `{"safety_snapshot_id": "<new_id>", "target_snapshot_id": "snap_A", "applied": "+1 -0 ~0", "forced": false}`
- AND the process exits `0`

#### Scenario: `flow snapshot rollback <old_snap_id> --confirm` with new observations added since refuses with JSON error listing new IDs

- GIVEN snapshot `snap_old` was created at T1 with observations `[1, 2]`
- AND between T1 and now, observations `[3, 4, 5]` were added to the live state
- WHEN `flow snapshot rollback snap_old --confirm` runs (no `--force`)
- THEN the process exits non-zero (exit code 2 — conflict, distinct from confirmation-refusal exit 3)
- AND stderr contains a JSON object `{"error": "live state has diverged; refusing rollback without --force", "conflicts": [{"id": 3, "change": "added"}, {"id": 4, "change": "added"}, {"id": 5, "change": "added"}]}`
- AND `snapshot_rollback_total{success="false"}` increments by `1` (audit of attempted rollback)
- AND the live state is UNCHANGED (no writes; Phase 1 safety snapshot MAY be created depending on D11 ordering — verify per implementation)
- AND re-running with `--force` also emits the warning to stderr AND THEN proceeds with the apply (acknowledging the override)

---

### REQ-33: `flow drift <change> --snapshot=<snap_id>` — drift-pinned scan via the existing `load_graph`/`scan_change` seam

The system SHALL add a new `--snapshot=<snap_id>` flag to the existing `flow drift <change>` CLI subcommand. When the flag is absent, `flow drift <change>` SHALL behave byte-identically to its pre-change behaviour (existing scripts and daemon integrations unaffected — non-breaking contract per D13). When the flag is present, the command SHALL compute the drift report against the **SNAPSHOT's frozen state** (not the live Engram DB) by:

1. Loading the snapshot envelope from `~/.flow-engineering/snapshots/<snap_id>.json.gz`.
2. Calling `decision_drift.scan_change(change_name, *, graph_json_path=None, backend=<InMemoryBackend built from snapshot.graph_state.observations>, include_obsolete=False, since=None, *, snap_id=<snap_id>)` — the new kwarg-only `snap_id` parameter.
3. Inside `scan_change`, `snap_id` set SHALL cause `load_graph(snap_id=<snap_id>)` to read the frozen `graph_state.graph_json` from the envelope (NOT from disk) and return `(nodes, id_map, snap_mtime)` built from the frozen content. When the envelope's `metadata.include_graph == False` (the snapshot was created with `--no-include-graph`), `scan_change` SHALL raise `SnapshotGraphMissing` AND emit the counter `snapshot_load_failed_total{reason="graph_missing"}` before raising — the counter is the audit trail of drift-pinned scan attempts that could not be resolved because the snapshot opted out of `graph_json` inclusion.

The two seam extensions SHALL be kwarg-only with `None` default:
- `decision_drift.load_graph(graph_json_path: Path | None = None, *, snap_id: str | None = None) -> tuple[dict | None, dict | None, float | None]` — when `snap_id` is set, `graph_json_path` MUST be `None` (mutual-exclusion assertion raises `ValueError` otherwise); when `snap_id=None`, behavior is byte-identical to the pre-change `load_graph(graph_json_path)`.
- `decision_drift.scan_change(change_name: str, *, graph_json_path: Path | None, backend: "EngramBackend | None" = None, include_obsolete: bool = False, since: float | None = None, *, snap_id: str | None = None) -> DriftReport` — when `snap_id` is set, `backend` MUST be `None` (the snapshot's frozen observations become the implicit backend; mutual-exclusion assertion raises `ValueError` otherwise).

Different snapshots SHALL produce different drift reports against the same change (the headline use case: "what was the drift state at time T?" enabling historical drift trend analysis).

#### Scenario: Snapshot from 2026-06-01 with 0 drift findings; running `flow drift --snapshot=<that_id> <change>` returns 0 findings even if live state has drift

- GIVEN snapshot `snap_2026-06-01` was created when every binding in `change="vector-semantic-search"` had `STILL_VALID` classification against `graph.json` at that time
- AND today (2026-06-26) the same bindings have 3 `STALE_LOCATION` findings against the current `graph.json`
- WHEN `flow drift vector-semantic-search --snapshot=snap_2026-06-01` runs
- THEN `scan_change` is invoked with `snap_id="snap_2026-06-01"` and `backend=None`
- AND the resulting `DriftReport.class_counts` reflects the FROZEN state (e.g., `{STILL_VALID: 12}` — NOT today's `{STILL_VALID: 9, STALE_LOCATION: 3}`)
- AND `DriftReport.graph_mtime` is the snapshot's stored mtime, NOT the live disk mtime
- AND the existing `record_drift_summary` observability counters (REQ-12) increment as normal

#### Scenario: `flow drift <change>` without `--snapshot` is byte-identical to current behavior

- GIVEN any backend + `graph.json` on disk (current production state)
- WHEN `flow drift vector-semantic-search` runs (no `--snapshot` flag)
- THEN `scan_change` is invoked with `snap_id=None`, `graph_json_path=<live path>`, `backend=<live backend>` (or empty `InMemoryBackend` if none provided)
- AND the resulting `DriftReport` is byte-identical (same `class_counts`, same `findings`, same `graph_mtime`) to a pre-change run
- AND no snapshot file is loaded
- AND no new counter increments beyond what the pre-change `flow drift` already increments

---

### REQ-34: `flow snapshot prune [--keep-last=N] [--keep-days=N] [--max-total-size-mb=N] [--confirm] [--force]` — retention policy

The system SHALL provide a new CLI subcommand `flow snapshot prune` for retention-driven deletion of snapshot files. At least ONE filter flag MUST be supplied: `--keep-last=N` (keep the N most recent by `created_at`, delete the rest), `--keep-days=N` (keep snapshots with `created_at >= now - N days`, delete the rest), or `--max-total-size-mb=N` (delete oldest-first until the total snapshot directory size fits within N megabytes). Default behavior (no flags) SHALL be **dry-run**: exit `0`, print JSON `{"would_delete": [snap_ids], "would_keep": [snap_ids], "freed_bytes": N}` to stdout, delete NOTHING.

The `--confirm` flag is REQUIRED to actually delete; without `--confirm`, the command is always dry-run. The combination `--keep-last=0` SHALL additionally require the `--force` flag (D10 two-flag safety gate to prevent the "I meant 1, not 0" foot-gun) — `--keep-last=0` without `--force` SHALL exit non-zero with an error explaining the gate. The `--keep-last=0` flag MUST NOT be combined with `--keep-days` or `--max-total-size-mb` (mutually exclusive; refuses if both present). After a `--confirm`'d deletion, `snapshot_prune_total{reason=<age|count|size>}` increments by `len(deleted_ids)` per call.

#### Scenario: With 5 snapshots, `flow snapshot prune --keep-last=3` (no `--confirm`) shows `would_delete` + `would_keep` JSON and deletes no files

- GIVEN 5 snapshot files exist in `~/.flow-engineering/snapshots/`, created in order: `snap_1`, `snap_2`, `snap_3`, `snap_4`, `snap_5`
- WHEN `flow snapshot prune --keep-last=3` runs (no `--confirm`)
- THEN the process exits `0`
- AND stdout is a JSON object `{"would_delete": ["snap_1", "snap_2"], "would_keep": ["snap_3", "snap_4", "snap_5"], "freed_bytes": <sum of snap_1 + snap_2 sizes>}` (order in arrays is insertion order, oldest first)
- AND all 5 snapshot files still exist on disk (dry-run; no deletion)
- AND `snapshot_prune_total` is NOT incremented (dry-run does not emit the counter)

#### Scenario: `flow snapshot prune --keep-last=2 --confirm` actually deletes 3 oldest snapshots

- GIVEN the same 5-snapshot setup as the previous scenario
- AND `snapshot_prune_total{reason="count"}` reads `K` from the metrics file (baseline)
- WHEN `flow snapshot prune --keep-last=2 --confirm` runs
- THEN the process exits `0`
- AND the 3 oldest files (`snap_1`, `snap_2`, `snap_3`) are removed from disk
- AND the 2 newest files (`snap_4`, `snap_5`) remain on disk
- AND `snapshot_prune_total{reason="count"}` reads `K + 3` from the metrics file (incremented by `len(deleted) = 3`)
- AND `--keep-last=0` requires BOTH `--confirm` AND `--force` (unit-tested separately at `tests/unit/test_snapshot_manager.py` — refuses non-zero when either is missing)

> **Drift note (post-drift-hardening, 2026-06-27)**: `PruneResult.freed_bytes` is
> the canonical field name (per W26 carry-forward resolution). The original
> spec used `freed_bytes_estimate`; the impl at `snapshot_manager.py:235`
> uses `freed_bytes`. The BDD scenarios for REQ-34 don't assert the exact
> field name (only the cumulative byte total), so this is pure spec
> reconciliation with no functional change. `pinned: bool` snapshots are
> also excluded from the dry-run `would_delete` list (per S18).

---

## Reconciliation note (W20 — pre-archive)

The counter names emitted by the implementation (`SNAPSHOT_COUNTER_NAMES` in
`src/flow_engineering/observability.py:124`) DIVERGED from the original
delta-spec catalog during the apply phase. This note records the reconciliation
in line with the W2 reconciliation pattern from the
`decision-code-linking` archive:

| Original spec name | Implementation name (canonical) | REQ | Status |
|---|---|---|---|
| `snapshot_created_total` | `snapshot_create_total` | REQ-28 | reconciled — trailing 'd' dropped |
| `snapshot_diff_invoked_total` | (not emitted) | REQ-31 | removed — `SnapshotManager.diff()` does not increment a per-invocation counter |
| `snapshot_rollback_total` | `snapshot_rollback_total` | REQ-32 | already aligned (no change) |
| `snapshot_pruned_total` | `snapshot_prune_total` | REQ-34 | reconciled — trailing 'd' dropped |
| (none) | `snapshot_load_failed_total{reason="graph_missing"}` | REQ-33 | added — emitted at the `SnapshotGraphMissing` raise site in `decision_drift.scan_change()` (drift-pinned scan audit trail) |

The implementation's names are now the source of truth. The 4-name catalog
(`snapshot_create_total`, `snapshot_rollback_total`, `snapshot_prune_total`,
`snapshot_load_failed_total`) matches `SNAPSHOT_COUNTER_NAMES` and the
CHANGELOG v0.6.0 entry.

---

## Out of Scope (deferred)

The following are explicitly out of scope for this change and belong to named follow-ups:

- **Per-project snapshots** — v1 captures the full DB at once; a `--project=<key>` flag is a SHOW-TIME slice only (mirrors `mem_search_federated(projects=None)` from cross-project-federation D1). Single-project snapshots would require splitting the file format or maintaining parallel indexes — premature at the 172-obs scale.
- **Encrypted snapshots at rest** — local-first; OS-level encryption is the user's responsibility. Documented in the README under "sharing snapshots". A `--redact` flag for sharing is also deferred until a real sharing workflow emerges.
- **Snapshot-based time-travel query API** (e.g., `mem_search_as_of(query, timestamp)`) — `flow snapshot show <id> --project=<key>` is the v1 read surface. A native `mem_search_as_of` is a v2 SDK addition.
- **Snapshot streaming or compression beyond gzip** — gzip ON by default; `--no-compress` for `jq` ergonomics. zstd / brotli / chunked streaming are not on the v1 roadmap.
- **Federated cross-project snapshot diff** — `flow snapshot diff` is single-project diff only in v1 (the underlying observations are tagged with `project`, but the diff format reports added/removed/modified across all projects as a single set). A federated diff surface (`mem_diff_federated(projects=...)`) is a v2 follow-up.
- **Snapshot immutability enforcement at OS level** (e.g., append-only filesystem, chattr +i) — snapshots rely on the sha256 stamp for tamper detection at read time. OS-level immutability is a deployment-time concern, not a runtime one.
- **Snapshot tags / labels beyond ISO timestamp + description** — the `description` field is a free-text user note. A structured tag taxonomy (`tags: ["release:v0.6", "milestone:beta"]`) is v2.
- **Auto-daily / auto-hourly snapshot triggers** (Q1 resolution) — v1 is manual-only; `flow snapshot create` is the only path. Auto-trigger via `flow watch` hook / cron / systemd timer is v2 once a real daily-backup workflow emerges.
- **Rollback three-way merge / automatic conflict resolution** (Q4 resolution) — v1 is hard-fail + `--force` override. A merge-based resolution would need an LLM-judge-style synthesizer and is unjustified at this scale.
- **Snapshot export / import** (`flow snapshot export <id>` for sharing) — sharing is a deferred workflow. `cp ~/.flow-engineering/snapshots/<id>.json.gz` is the v1 escape hatch.
- **Vector index snapshots** — v1 snapshots capture the prose observation graph + drift history + `graph.json` correlator. The vector index lives in `~/.flow-engineering/vectors.sqlite` and is recoverable independently. A `flow snapshot --include-vectors` flag is v2.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req28_snapshot_create.feature` | NEW | REQ-28 | 2 |
| `tests/bdd/req29_snapshot_list.feature` | NEW | REQ-29 | 2 |
| `tests/bdd/req30_snapshot_show.feature` | NEW | REQ-30 | 1 |
| `tests/bdd/req31_snapshot_diff.feature` | NEW | REQ-31 | 2 |
| `tests/bdd/req32_snapshot_rollback.feature` | NEW | REQ-32 | 3 |
| `tests/bdd/req33_drift_pinned.feature` | NEW | REQ-33 | 2 |
| `tests/bdd/req34_snapshot_prune.feature` | NEW | REQ-34 | 2 |
| **Total BDD scenarios** | | | **14** |

Step definitions land in `tests/bdd/test_snapshot_steps.py` (NEW; pytest-bdd glue per file). The per-REQ scenario counts above match the task brief verbatim (REQ-28: 2, REQ-29: 2, REQ-30: 1, REQ-31: 2, REQ-32: 3, REQ-33: 2, REQ-34: 2 — totaling 14). Edge cases that don't fit the BDD scope are covered by unit tests at `tests/unit/test_snapshot_manager.py` (e.g., REQ-30's sha256-tamper detection, REQ-32's `--force` override behavior, REQ-34's `--keep-last=0` two-flag safety gate) — mirrors the cross-project-federation split where the ABC-default test stayed a unit assertion only.

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `binding.extract_code_refs()` reused for snapshot block parsing | Compatible (consumes the seam); no change to `decision-code-linking` files |
| `decision-reality-drift` (shipped v0.3.0) | `load_graph()` (line 124) and `scan_change()` (line 188) extended with kwarg-only `snap_id`; default `None` = current behavior | NON-BREAKING; existing callers byte-identical; 699+ existing tests pass unchanged |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is in `~/.flow-engineering/vectors.sqlite`; snapshots capture PROSE state + `graph.json` + drift history; vectors NOT included in v1 | Compatible (boundary respected); v2 may snapshot vector index separately |
| `cross-project-federation` (shipped v0.5.0) | `flow projects backfill --confirm` confirmation gate is the precedent for `flow snapshot rollback --confirm` + `flow snapshot prune --confirm`; `--dry-run` default mirrors this pattern | Compatible (same safety contract); no federation coupling |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |
| Third-party `EngramBackend` subclasses | No new ABC methods required; `SnapshotManager` reads via the existing `iter_observations()` seam (REQ-7 from `decision-code-linking`) | NON-BREAKING; old subclasses import unchanged |

---

## References

- Explore: Engram `sdd/graph-snapshots/explore` (#173) — option matrix A-G, B+F hybrid recommended, storage sizing math
- Proposal: Engram `sdd/graph-snapshots/proposal` (#174) — Sketch A additive snapshot subsystem, 10 open questions for design
- Design: Engram `sdd/graph-snapshots/design` (#175) — D1-D13 resolved (SnapshotManager API, envelope schema, non-breaking seam, hard-fail rollback, drift-pinned frozen-state scan, dry-run prune, snapshot naming, atomic write, sha256 over canonical JSON, prune safety gate, rollback idempotency, test determinism, cross-impact table)
- Predecessor spec: `openspec/changes/archive/2026-06-26-cross-project-federation/spec.md` (5 REQs, 25 scenarios — format reference; BDD Feature File Plan table format; Out-of-Scope style; Cross-impact table format)
- Predecessor design: `openspec/changes/archive/2026-06-26-cross-project-federation/design.md` (D1-D11 reference format for design/spec alignment; extended to D1-D13 here for snapshot-specific concerns)
- Carry-forward seam: `decision_drift.load_graph(graph_json_path)` at `src/flow_engineering/decision_drift.py:124` + `decision_drift.scan_change(...)` at `:188` (both extended with kwarg-only `snap_id`)
- Counter catalog precedent: `VECTOR_COUNTER_NAMES` (REQ-22) + `FEDERATED_COUNTER_NAMES` (REQ-26) at `observability.py:70,89` — mirrored by `SNAPSHOT_COUNTER_NAMES` (4 names) at `observability.py:90`
- Confirmation-gate precedent: `flow projects backfill --confirm` (REQ-24) — mirrored by `flow snapshot rollback --confirm` (REQ-32) and `flow snapshot prune --confirm` (REQ-34)
- Engram DB state (2026-06-26): 172 observations across 10 projects — snapshot sizing math: ~1 MB uncompressed per snapshot, ~73 MB/year gzipped at 1/day
