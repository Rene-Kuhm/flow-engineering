<!-- Proposal: graph-snapshots. Source: manual. -->
# Proposal: graph-snapshots

## Intent

`flow-engineering` already models three graph-shaped concepts — the **Engram
observation graph** (observations + `code_refs` bindings), **drift history**
(via `decision_drift.scan_change`), and the **graphify `graph.json` correlator**
— but every change mutates them in place with **zero historical record**.
`revision_count` exists but is a dedup counter, not history. This blocks five
real workflows: temporal diff, rollback, audit, drift pattern detection over
time, and federated timeline (REQ-23..27 interaction). This change adds an
**additive** immutable JSON snapshot subsystem so users can answer "what did
the graph look like last Tuesday?" and "undo the last 3 changes" without
touching the live `EngramBackend` write paths.

## Context (from explore)

Explored in [`explore.md`](./explore.md) and Engram #173. Six strategies
evaluated against five use cases; **B+F hybrid recommended**: immutable JSON
snapshots (optionally gzipped) at `~/.flow-engineering/snapshots/snap_<ISO>.json.gz`.
Storage sizing: ~1 MB/snapshot uncompressed, ~200 KB gzipped, ~73 MB/year at
1/day — trivially cheap on local-first. The seam for snapshot-pinned drift is
**already in place** (carry-forward from `decision-reality-drift` archive #136):
`decision_drift.load_graph(graph_json_path)` accepts a `Path`, so REQ-33 needs
no new drift code — only a thin wrapper. Event-sourced log (option A) and
incremental deltas (option C) deferred to v2 because replay correctness adds
schema + maintenance cost that is unjustified at the 172-observation scale.
Git-based snapshots (option D) rejected: 3 of 7 sub-projects lack git; graph
state lives in Engram SQLite, not in any repo. SQLite "system-versioned"
temporal tables (option E) **do not exist** in SQLite — the honest equivalent
is "custom triggers + history table", which is option A in disguise.

## Approach (proposed)

### Architecture

Five cooperating pieces, all additive:

1. **`SnapshotManager` (NEW)** — `src/flow_engineering/snapshot_manager.py`.
   Pure-file facade over `~/.flow-engineering/snapshots/`. Methods:
   `create(label=None, project=None, include_graph=False)`,
   `list(label=None, since=None, project=None)`,
   `show(snap_id)`,
   `diff(snap_id_a, snap_id_b)` → `{added, removed, modified: [{id, field, before, after}]}`,
   `rollback(snap_id, *, confirm=False)` — auto-creates safety snapshot first,
   `prune(*, keep_last=None, keep_days=None, max_total_size_mb=None)`.
2. **CLI subcommand group** — `flow snapshot {create,list,show,diff,rollback,prune}`
   on the existing `cli.py` argparse tree. New `--snapshot=<snap_id>` flag on
   `flow drift` for snapshot-pinned drift scans (REQ-33).
3. **Observability** — 4 new counters in `observability.py` (REQ-22 / REQ-26
   pattern): `snapshot_created_total{trigger=manual|auto|rollback_safety}`,
   `snapshot_diff_invoked_total`, `snapshot_rollback_total{success|failure}`,
   `snapshot_pruned_total{reason=age|count|size}`. Exposed via
   `SNAPSHOT_COUNTER_NAMES` catalog for `flow metrics` consumers.
4. **`decision_drift` seam extension** — add optional `snap_id` kwarg to
   `load_graph(graph_json_path, *, snap_id=None)` (default `None` = current
   state; existing callers unaffected). `flow drift --snapshot=<id>` resolves
   `snap_id` → snapshot file → reads `graph_mtime` correlator (graph.json
   content itself NOT copied; mtime-only for v1).
5. **Auto-safety snapshot** before every rollback — mirrors the `flow projects
   backfill` confirmation gate from cross-project-federation (#136). Rollback
   requires `--confirm`; safety snapshot is tagged `trigger=rollback_safety`.

### Snapshot file format

```json
{
  "schema": 1,
  "id": "snap_2026-06-26T123456Z",
  "created_at": "2026-06-26T12:34:56Z",
  "trigger": "manual | auto | rollback_safety",
  "label": "pre_drift_fix",
  "graph_state": {
    "observations": [...],   // full list, all projects
    "bindings": [...],       // code_refs per obs
    "project_tags": {...},   // obs_id -> project
    "aliases": [...],        // current alias config snapshot
    "drift_history": [...]   // last N metrics.jsonl events
  },
  "metadata": {
    "obs_count": 169,
    "binding_count": ...,
    "project_count": 9,
    "file_size_bytes": ...,
    "sha256": "..."         // integrity hash for tamper detection
  }
}
```

Gzipped to `.json.gz` by default (flag `--no-compress` for jq-ability).
SHA256 computed on the canonicalized JSON for tamper detection.

### Dependencies

- **NO new runtime dependencies** — stdlib `gzip` + `json` + `pathlib` +
  `hashlib` + `tempfile` + `sqlite3` (for read transaction).
- Reuses `decision_drift.load_graph(graph_json_path)` seam (REQ-33).
- Reuses `EngramBackend.iter_observations()` (no new ABC method; we read,
  never write from the snapshot path).
- Reuses `binding.extract_code_refs()` for block parsing.

### What changes (scope)

**In scope**:
- `src/flow_engineering/snapshot_manager.py` (NEW): create/list/show/diff/rollback/prune.
- `src/flow_engineering/cli.py` (MODIFY): new `flow snapshot` subcommand group
  (6 subcommands) + `--snapshot=<snap_id>` flag on existing `flow drift`.
- `src/flow_engineering/decision_drift.py` (MODIFY): optional `snap_id` kwarg
  on `load_graph()` (default `None`, non-breaking).
- `src/flow_engineering/observability.py` (MODIFY): 4 new counters +
  `SNAPSHOT_COUNTER_NAMES` catalog + `record_snapshot_event(name, **fields)`
  helper (mirrors `record_vector_summary`).
- `~/.flow-engineering/snapshots/` (NEW runtime dir, created lazily on first
  `flow snapshot create`).

**Out of scope (deferred to v2)**:
- Per-project snapshots (v1 is global; mirrors `mem_search_federated`
  behavior).
- Encrypted snapshots at rest (local-first; OS-level encryption is user's
  responsibility — documented in README).
- Event-sourced log (option A in explore) — fine-grained audit; would require
  patching every `mem_save` / `update_observation` write site.
- Snapshot diff over federated queries (cross-project temporal diff).
- Time-travel query API (`mem_search_as_of(query, timestamp)`).
- Snapshot streaming / compression beyond gzip.
- Snapshot redaction (`--redact` flag) — revisit when sharing is a real
  workflow.

### Public API surface

- `SnapshotManager` class (NEW) with 6 methods as listed above.
- `flow snapshot create|list|show|diff|rollback|prune` (NEW CLI group).
- `flow drift --snapshot=<snap_id>` (NEW flag on existing `flow drift`).
- `decision_drift.load_graph(graph_json_path, *, snap_id=None)` — kwarg-only
  addition, default behavior unchanged.
- `observability.record_snapshot_event(name, **fields)` (NEW helper).

### Non-breaking guarantees

- `decision_drift.load_graph(graph_json_path, *, snap_id=None)`: kwarg-only
  addition, default `None` = current state. Existing callers unchanged.
- `flow drift <change>` without `--snapshot` flag: byte-identical to current.
- All existing 699 tests pass — verified locally before PR open.
- Snapshots are **read-only** views of state; the live Engram DB is never
  mutated by `snapshot create` / `snapshot list` / `snapshot show` /
  `snapshot diff` / `snapshot prune`. Only `rollback` writes — and it takes
  an auto-safety snapshot first.
- New runtime dir `~/.flow-engineering/snapshots/` is opt-in: only created on
  the first `flow snapshot create` invocation.
- `SNAPSHOT_COUNTER_NAMES` catalog additive; existing
  `VECTOR_COUNTER_NAMES` and `FEDERATED_COUNTER_NAMES` byte-identical.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/snapshot_manager.py` | NEW | `SnapshotManager` class (6 methods) + snapshot envelope dataclasses |
| `src/flow_engineering/cli.py` | MODIFY | `flow snapshot` subcommand group (6 cmds) + `--snapshot` flag on `flow drift` |
| `src/flow_engineering/decision_drift.py` | MODIFY | Optional `snap_id` kwarg on `load_graph()` (line ~124) |
| `src/flow_engineering/observability.py` | MODIFY | `SNAPSHOT_COUNTER_NAMES` catalog + `record_snapshot_event` helper |
| `~/.flow-engineering/snapshots/` | NEW (runtime) | Snapshot dir, created lazily; default empty |
| `tests/unit/test_snapshot_manager.py` | NEW | RED fixtures: create round-trip, list ordering, diff invariants, rollback safety, prune retention |
| `tests/unit/test_decision_drift_snap_id.py` | NEW | RED fixtures: `snap_id=None` default unchanged; `snap_id=...` resolves to graph_mtime correlator |
| `tests/bdd/req28_snapshot.feature` (REQ-28..34) | NEW | ~10-12 BDD scenarios (see Success Criteria) |
| `tests/bdd/test_snapshot_steps.py` | NEW | pytest-bdd glue |
| `openspec/changes/graph-snapshots/{design,spec,tasks}.md` | NEW | follow-on phases |
| `CHANGELOG.md` | MODIFY | v0.7.0 entry post-merge |

## Capabilities

### New Capabilities
- `graph-snapshots`: immutable JSON snapshot subsystem covering create / list /
  show / diff / rollback / prune + drift-pinned scan via the existing
  `decision_drift.load_graph()` seam. Snapshots are gzipped JSON files at
  `~/.flow-engineering/snapshots/`, sha256-stamped for tamper detection, with
  an auto-safety snapshot before every rollback. Fully additive — read-only
  by default; rollback is the only mutating path and it has a `--confirm`
  safety gate.

### Modified Capabilities
- `decision-reality-drift` (REQ-9..16): `decision_drift.load_graph()` gains an
  optional `snap_id` kwarg for snapshot-pinned drift scans. Behavior is
  unchanged when `snap_id=None` (the default). One small delta spec.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Snapshot during a concurrent `mem_save` captures a half-written observation | Med | Snapshot reads inside `BEGIN IMMEDIATE` + ordered `SELECT ... FROM observations ORDER BY id` (mirrors `flow projects backfill` pattern); sha256 of canonical JSON provides tamper detection post-hoc |
| Rollback overwrites concurrent writes from other Engram tools | Med | Rollback runs inside one SQLite transaction with `BEGIN IMMEDIATE`; safety snapshot first (auto); requires `--confirm`; documented that rollback briefly blocks other Engram writers |
| Storage grows unbounded; hundreds of daily snapshots accumulate | Low | `flow snapshot prune [--keep-last=N] [--keep-days=N] [--max-total-size-mb=N]` retention policy; `snapshot_pruned_total{reason}` counter tracks what was pruned and why |
| Snapshot file corruption (half-written gzip) leaves silent data loss | Low | Atomic write via `tempfile` + `Path.replace`; sha256 hash verified on every `snapshot show` / `snapshot rollback`; `SnapshotEnvelopeError` raised with helpful message on mismatch |
| Cross-project snapshot semantics drift from `mem_search_federated` defaults | Low | v1 snapshots are global (all projects at once); documented as "parity with federated default" (mirrors cross-project-federation decision for `projects=None`) |
| Privacy leak via shared snapshot (code_refs expose file paths + confidences) | Med | Document explicitly in README + `flow snapshot create --help` text: "sharing a snapshot shares the underlying decision corpus"; `--redact` flag deferred to v2 once a real sharing workflow emerges |
| Schema evolution: v2 snapshots add fields; v1 readers choke | Low | `schema: 1` field in envelope; readers ignore unknown fields (strict-TDD contract test); new readers must support older `schema` versions for ≥2 minor versions |
| Snapshot ID collision when two `create` calls land in the same second | Low | ID format `snap_<ISO>` (1-sec resolution); collision window requires intentional double-fire — log warning + append `-<microseconds>` suffix on detect |
| Snapshot directory fills `/` on a constrained system (~73 MB/yr is cheap, but unbounded prune deferral) | Low | Default `~/.flow-engineering/` lives on user home (rarely constrained); README documents the size math; `flow snapshot prune` is the user's hammer |

## Rollback Plan

All artifacts are additive. Single revert of the merge commit restores
pre-change state:
- New file `snapshot_manager.py` is self-contained, easy to delete.
- Modified files (`cli.py`, `decision_drift.py`, `observability.py`) only
  ADD new symbols / subcommands; no existing behavior removed.
- New counters in `SNAPSHOT_COUNTER_NAMES` are additive; `flow metrics`
  consumers ignore unknown names.
- New runtime dir `~/.flow-engineering/snapshots/` is empty until first
  `flow snapshot create`; deleting it is harmless.
- The `snap_id` kwarg on `load_graph()` is keyword-only with default `None`;
  callers that don't pass it see no behavior change.

The user's own snapshots are NOT touched by a code revert. To restore live
state to a prior point in time, the user runs `flow snapshot rollback <id>`
BEFORE reverting the code PR. (If they forget, no harm — the live state
survives; they just lose the rollback convenience.)

## Dependencies

- **None new.** stdlib `gzip` + `json` + `pathlib` + `hashlib` + `tempfile` +
  `sqlite3`.
- `decision-reality-drift` (shipped v0.3.0) — `load_graph(graph_json_path)`
  seam is extended (kwarg-only).
- `decision-code-linking` (shipped v0.2.0) — `binding.extract_code_refs()`
  reused for snapshot block parsing.
- `cross-project-federation` (shipped v0.5.0) — independent surface; the
  `flow projects backfill` confirmation gate is the precedent for the
  rollback safety pattern.
- `vector-semantic-search` (shipped v0.4.0) — unrelated; snapshots capture
  the prose index state, not the vector index (vector index is in
  `~/.flow-engineering/vectors.sqlite`, separately recoverable).

## Open Questions (for sdd-design)

1. **Auto-daily snapshot trigger**: hook into `flow watch` daemon at midnight,
   OR opt-in via cron / systemd timer? **Recommend** opt-in flag
   `flow snapshot auto [--daily|--hourly|--on-watch]` (no auto behavior in v1).
2. **`--include-graph` flag**: should v1 allow opting in to full-content
   `graph.json` snapshots (5+ MB), or stay mtime-only? **Recommend** mtime-only
   for v1; flag deferred to v2.
3. **Compression default**: gzip ON by default, OR plain JSON for
   `jq`-ability? **Recommend** gzip ON, `--no-compress` for jq.
4. **Rollback conflict policy**: if live DB changed since snapshot, hard-fail
   OR three-way merge? **Recommend** hard-fail by default; explicit `--force`
   override required (mirrors `flow projects backfill --confirm` pattern).
5. **Cross-project default**: full DB (all projects) OR current
   `FLOW_PROJECT_TAG` only? **Recommend** full DB for parity with
   `mem_search_federated(projects=None)`; per-project filter is a read-time
   slice (`flow snapshot show <id> --project=<key>`).
6. **Snapshot ID determinism**: monotonic ISO (1-sec resolution, collisions
   possible) OR sha256-of-content (content-addressed, can't have two
   identical-state snapshots)? **Recommend** monotonic + accept the
   sub-second collision window (extremely unlikely in practice).
7. **Drift-pinned scan semantics**: does `flow drift --snapshot=<id>` scan
   the LIVE observations or the snapshot's frozen state? **Recommend** scan
   LIVE observations (otherwise drift detection becomes a tautology); use the
   snapshot's `graph_mtime` correlator ONLY for `graph.json` audit context.
8. **`snapshot prune` default behavior**: if no flags are passed, prune
   nothing (dry-run) OR apply a sane default (keep last 30 + 1 year weekly)?
   **Recommend** dry-run when no flags — safer; user must opt in.
9. **SHA256 field**: computed over canonicalized JSON (sorted keys, no
   whitespace) OR over the raw gzip bytes? **Recommend** raw gzip bytes
   (matches the on-disk artifact exactly; integrity = "file is what I wrote").
10. **Migration from prior in-place state**: should first `flow snapshot create`
    be labeled `initial_state` automatically? **Recommend** yes — first call
    (when snapshot dir is empty) auto-labels as `initial_state`.

## Success Criteria

- [ ] `SnapshotManager.create()` writes a gzipped JSON envelope at
      `~/.flow-engineering/snapshots/snap_<ISO>.json.gz` with sha256 stamped
      (BDD scenario REQ-28)
- [ ] `flow snapshot list` returns snapshots sorted by `created_at` desc,
      with `--since=<iso>` filter respected (REQ-29)
- [ ] `flow snapshot show <snap_id>` parses + renders the envelope; raises
      `SnapshotEnvelopeError` on sha256 mismatch or schema mismatch (REQ-30)
- [ ] `flow snapshot diff <snap_a> <snap_b>` returns
      `{added: [obs_ids], removed: [obs_ids], modified: [{id, field, before, after}]}`
      with field-level diff for `code_refs` blocks (REQ-31)
- [ ] `flow snapshot rollback <snap_id> --confirm` takes an auto-safety
      snapshot first, then applies the diff via `mem_save` (added) +
      `update_observation` (modified) + soft-delete (removed); refuses
      without `--confirm`; counter `snapshot_rollback_total{success}`
      increments on completion (REQ-32)
- [ ] `flow drift <change> --snapshot=<snap_id>` reuses
      `decision_drift.scan_change` with the snapshot's `graph_mtime`
      correlator; behavior unchanged when `--snapshot` is absent (REQ-33)
- [ ] `flow snapshot prune --keep-last=N` keeps the N most recent and
      deletes the rest; `--keep-days=N` keeps those newer than N days;
      `--max-total-size-mb=N` keeps files until total size fits;
      counter `snapshot_pruned_total{reason=age|count|size}` increments per
      deletion (REQ-34)
- [ ] All 4 `snapshot_*` counters increment correctly; `flow metrics` lists
      them in the catalog
- [ ] Existing 699 tests pass; `ruff check` clean on changed files
- [ ] Strict TDD evidence: every public method has RED→GREEN→REFACTOR
      history in commit log
- [ ] Secrets invariant: a snapshot containing a `code_refs` block with
      `file=secrets.yaml` does NOT include the file contents in the
      snapshot envelope (only the reference metadata)

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Reuses `binding.extract_code_refs()` for snapshot parsing | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `load_graph(graph_json_path)` seam extended with kwarg-only `snap_id` | Compatible (existing callers unaffected; new flag is opt-in) |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is in `~/.flow-engineering/vectors.sqlite`; snapshots capture PROSE state only | Compatible (boundary respected); v2 may snapshot vector index separately |
| `cross-project-federation` (shipped v0.5.0) | `flow projects backfill` confirmation gate is the precedent for `flow snapshot rollback --confirm` | Compatible (same safety pattern); no federation coupling |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |

**Unblocks**: temporal diff between any two snapshots, full-state rollback
with safety net, byte-exact audit via sha256, drift pattern detection over
time (correlate `metrics.jsonl` events with snapshot mtime), federated
timeline queries (REQ-23..27 + snapshots = "what was each project's state
at milestone X?").

**Constrains**: any future change that extends `decision_drift.load_graph()`
must keep the `snap_id` kwarg-only contract (no positional args). Snapshots
must remain JSON-encoded + sha256-stamped; binary formats would break
`flow snapshot show <id> | jq` ergonomics.

## Estimated Effort

- **Apply LOC (forecast)**: ~500-700 production + ~1500-2400 tests (×3-4
  TDD multiplier). Mirrors `cross-project-federation` PR#1 scale.
- **Chained PR strategy**: **NO — single PR**. The work fits in one
  ~500-700 LOC PR + ~1.5-2k test LOC; PR#2 would be cosmetic CLI polish
  only. Review budget: ~400-500 lines per the chained-pr convention,
  comfortably under.
- **Phase estimate**:
  - ~10min explore (DONE)
  - ~10min propose (this phase)
  - ~15min design
  - ~10min spec
  - ~10min tasks
  - ~60-90min apply (single PR)
  - ~10min verify
  - ~10min archive
  - **Total ~2-2.5h end-to-end**

## References

- Explore: [`explore.md`](./explore.md) (Engram #173, full option matrix)
- Prior pattern: `openspec/changes/archive/2026-06-26-cross-project-federation/`
- Carry-forward seam: `decision_drift.load_graph(graph_json_path)` from
  `decision-reality-drift` archive #136
- `flow projects backfill --confirm` precedent for the rollback safety gate
- Counter pattern: REQ-22 (`VECTOR_COUNTER_NAMES`) + REQ-26
  (`FEDERATED_COUNTER_NAMES`) catalogs in `observability.py:70,89`

## Next Step

Ready for `sdd-design graph-snapshots`. The 10 open questions above MUST be
resolved in the design phase (especially auto-snapshot trigger, rollback
conflict policy, and `snap_id` drift-pinned semantics) before `sdd-spec`
locks the requirement contract. Single PR — no chained PR split needed.

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager",
      "label": "SnapshotManager (NEW — create/list/show/diff/rollback/prune)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_snapshot",
      "label": "flow snapshot subcommand group (NEW — 6 subcommands)",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_drift_snapshot_flag",
      "label": "flow drift --snapshot=<id> (NEW flag — REQ-33)",
      "file": "src/flow_engineering/cli.py",
      "line": 1146,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_load_graph",
      "label": "load_graph(graph_json_path, *, snap_id=None) (kwarg-only extension)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 124,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_snapshot_event",
      "label": "record_snapshot_event (NEW helper — mirrors record_vector_summary)",
      "file": "src/flow_engineering/observability.py",
      "line": 413,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_snapshot_counter_names",
      "label": "SNAPSHOT_COUNTER_NAMES catalog (NEW — 4 counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 70,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_binding_extract_code_refs",
      "label": "extract_code_refs (reused for snapshot block parsing)",
      "file": "src/flow_engineering/binding.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_iter_observations",
      "label": "EngramBackend.iter_observations() (reused — no ABC changes)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}
