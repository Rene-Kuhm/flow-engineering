# Design: graph-snapshots

> Mirror of Engram `sdd/graph-snapshots/design` (topic_key upsert after file
> creation). Reference format mirrors
> [`openspec/changes/cross-project-federation/design.md`](../../archive/2026-06-26-cross-project-federation/design.md)
> (D1–D11) extended to D1–D13 for snapshot-specific concerns. All 10 open
> questions from propose #174 are resolved below. The Engram `code_refs` block
> is appended at file end so `flow inspect <change>` can render the binding
> surface.

## Technical Approach

`graph-snapshots` adds an **additive** immutable snapshot subsystem to the
existing flow-engineering surface. Snapshot state is JSON-serialized (optionally
gzipped) at `~/.flow-engineering/snapshots/snap_<ISO>-<hex>.json.gz` with a
sha256 stamp for tamper detection. Snapshots are **content-frozen views** of:

- The **observation graph** (every Engram observation in full + parsed
  `code_refs` / `metadata` blocks).
- The **drift history** (last N `metrics.jsonl` events at snapshot time).
- The **project alias map** (forward-only rename history).
- The **graphify `graph.json` content** (REJECTED in propose Q2; **REINSTATED
  here** because D5 drift-pinned semantics cannot work without the frozen
  graph).

Five cooperating pieces:

1. **`SnapshotManager` (NEW)** — `src/flow_engineering/snapshot_manager.py`.
   Pure-file facade over `~/.flow-engineering/snapshots/`. Six methods:
   `create`, `list`, `show`, `diff`, `rollback`, `prune`.
2. **CLI subcommand group** — `flow snapshot {create,list,show,diff,rollback,prune}`
   on the existing `cli.py` argparse tree. New `--snapshot=<snap_id>` flag on
   the existing `flow drift` for snapshot-pinned scans.
3. **`decision_drift` seam extension** — `load_graph(graph_json_path=None, *,
   snap_id=None)` gains a kwarg that loads the snapshot's frozen graph content
   when `snap_id` is provided. `scan_change(change_name, *, graph_json_path,
   backend=None, include_obsolete=False, since=None, *, snap_id=None)` gains
   a `snap_id` kwarg that pins the observation set to the snapshot. Both are
   kwarg-only with `None` default — existing callers byte-identical.
4. **Observability** — 4 new counters in `observability.py`:
   `snapshot_created_total{trigger=manual|auto|rollback_safety}`,
   `snapshot_diff_invoked_total`, `snapshot_rollback_total{success|failure}`,
   `snapshot_pruned_total{reason=age|count|size}`. Exposed via
   `SNAPSHOT_COUNTER_NAMES` catalog and `record_snapshot_event(name, **fields)`
   helper (mirrors `record_federated_summary`).
5. **Auto-safety snapshot before every rollback** — mirrors the
   `flow projects backfill --confirm` precedent from
   cross-project-federation (#136). Rollback is two-phase: (a) take a
   `trigger=rollback_safety` snapshot of CURRENT live state; (b) apply target
   snapshot via atomic SQLite transaction; (c) `--confirm` flag required
   throughout.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | `SnapshotManager` class API | `SnapshotManager(snapshots_dir: Path, backend: EngramBackend) -> SnapshotManager`; methods: `create(description, trigger) -> str` (returns snap_id); `list(since=None, limit=None) -> list[SnapshotMeta]`; `show(snap_id) -> dict`; `diff(snap_id_a, snap_id_b) -> SnapshotDiff`; `rollback(snap_id, *, confirm=False) -> RollbackResult`; `prune(*, keep_last=None, keep_days=None, max_total_size_mb=None, confirm=False) -> PruneResult`. Constructor takes the snapshots dir + the `EngramBackend` so all reads/writes route through the same backend other tools use (test seam via `InMemoryBackend`). Methods return dataclass results, not bare dicts, for type-checkable BDD assertions. | Constructor injection matches the `EngramBackend` ABC pattern already in use; dataclass returns give BDD steps something concrete to assert against (`diff.added` vs `diff["added"]`). `confirm=False` defaults on mutating methods (D10) mirrors the `--dry-run` default from `flow projects backfill` (`cli.py:643`). |
| **D2** | Snapshot file format version 1 | Envelope schema: `{schema: 1, id, created_at, trigger, description, graph_state: {observations: [...], bindings: [...], project_tags: {...}, aliases: [...], drift_history: [...], graph_json: {...}}, metadata: {obs_count, binding_count, project_count, drift_event_count, graph_node_count, file_size_bytes, sha256, include_graph: bool}}`. The `graph_json` field stores the full `graph.json` content (default ON); `--no-include-graph` CLI flag excludes it (saves ~5 MB/snapshot but disables D5 drift-pinned scans against that snapshot — graceful degradation, `flow drift --snapshot=<id>` returns `SnapshotGraphMissing` error instead). SHA256 computed over **canonicalized JSON** (sorted keys, no whitespace) — tamper detection is "envelope is what I wrote", matches the on-disk integrity model from `code_refs` schema_version 1. | Include graph.json content by default so D5 works without flags. The storage delta is acceptable: 1 MB/snapshot → ~6 MB/snapshot uncompressed (still ~1 MB gzipped), still ~400 MB/year gzipped at 1/day — trivial. The `include_graph: bool` flag in metadata lets `flow drift --snapshot=<id>` detect and refuse cleanly. SHA256 over canonicalized JSON is deterministic across filesystem encodings (the gzipped bytes may differ across implementations). |
| **D3** | Auto-trigger policy | **NEVER auto** in v1. Only `flow snapshot create` (manual invocation). Auto-safety snapshots happen ONLY on rollback (D11, mirrors `flow projects backfill --confirm` precedent). No `flow watch` hook, no cron integration, no systemd timer — these are deferred to v2 when a real "daily backup" workflow emerges. | Auto-daily at midnight sounds nice but adds storage the user didn't ask for; "take a snapshot before every risky change" is the higher-value use case and that's already covered by the manual command. If a user wants auto-daily, they wrap `flow snapshot create` in cron / Task Scheduler — no need to bake it in. |
| **D4** | Rollback conflict policy | **Hard-fail by default**. `rollback()` computes the diff between the target snapshot and the current Engram DB; if any observation has been added/modified/deleted since the snapshot's `created_at`, refuse with non-zero exit + JSON error listing the conflicting `observation_id`s and their change direction. `--force` flag overrides (DANGEROUS: prints loud warning to stderr + increments `snapshot_rollback_total{success=false}` BEFORE applying). `--confirm` flag still required in addition to `--force`. | Hard-fail is the only safe default; merging concurrent writes would silently destroy new work. The two-flag requirement (`--confirm` + `--force`) keeps the dangerous path explicit. JSON error makes it scriptable (CI / BDD can assert on the exact list). |
| **D5** | Drift-pinned semantics (CRITICAL) | `flow drift <change> --snapshot=<snap_id>`: (1) loads the snapshot's frozen `graph_state.observations` (NOT live observations); (2) calls `decision_drift.scan_change(change_name, *, snap_id=<snap_id>, backend=...)`; (3) `scan_change` with `snap_id` set wraps an `InMemoryBackend` containing ONLY the snapshot's frozen observations and uses `load_graph(snap_id=<snap_id>)` to get the frozen `graph.json` content + mtime; (4) returns a `DriftReport` computed entirely against the snapshot's frozen state. **Worked example**: snapshot from 2026-06-01 captures 5 observations with 12 bindings, all `STILL_VALID` against the 2026-06-01 `graph.json`. Today (2026-06-26) the same 12 bindings have 3 `STALE_LOCATION`. Running `flow drift --snapshot=2026-06-01` returns a `DriftReport` with `class_counts={STILL_VALID: 12}` — i.e., the drift state AS OF the snapshot. Running `flow drift <change>` (no `--snapshot`) returns today's report with the 3 `STALE_LOCATION` findings. **Different snapshots → different drift reports → historical drift trend analysis works.** | The proposal's Q7 recommendation was to scan LIVE observations with the snapshot's `graph_mtime` correlator only — that makes `--snapshot` a no-op (same scan as without the flag) and **disables the headline use case** (drift pattern detection over time, use case #4 from explore #173). The TASK-correct interpretation (frozen-state scan) is the value proposition; without it, `flow drift --snapshot=<id>` is a redundant flag. Reinterpreting Q7 in favor of the task brief. |
| **D6** | Snapshot retention default | `flow snapshot prune` with NO flags → dry-run, NO deletes. `flow snapshot prune --keep-last=N` keeps the N most recent (default N = 0 means "delete everything" — see D10). `--keep-days=N` keeps snapshots newer than N days. `--max-total-size-mb=N` keeps files greedily newest-first until the total fits. Default = **do nothing on no flags**; the user MUST specify at least one criterion. | Surprising deletes are the worst kind of delete. The default behavior matches `flow projects backfill --dry-run` — dry-run is the safe default; the user opts in to mutating. |
| **D7** | Snapshot file naming | `snap_<ISO>-<6-char-hex>.json.gz` where ISO is `YYYY-MM-DDTHH-MM-SS` and hex is `secrets.token_hex(3)` (e.g., `snap_2026-06-26T12-34-56-a3b9f1.json.gz`). The hex suffix guarantees collision-safety even with clock skew, simultaneous creation, or DST transitions. 6 hex chars = 16.7M possibilities → birthday-paradox collision probability is ~1 in 4 000 only after ~2 500 same-second creates (negligible in practice; if it ever happens the collision is detected via `os.path.exists` check + retry). | ISO alone collides on sub-second creates; ISO + random suffix is collision-safe without coordination. The `snap_` prefix makes the directory self-describing (`ls` shows only snapshots). `.json.gz` extension signals the format for `jq`-on-the-fly (`zcat file \| jq`). |
| **D8** | Concurrent snapshot policy | Snapshot reads run inside a **read-only SQLite transaction** (`BEGIN IMMEDIATE` for atomicity; the snapshot dir write happens AFTER the transaction commits). Writers to the Engram DB are blocked for ~milliseconds while the transaction holds; readers are NEVER blocked. Snapshot NEVER holds the lock longer than the read pass. `sqlite3.connect(uri, uri=True)` opens read-only when needed. | `BEGIN IMMEDIATE` gives a consistent point-in-time view of the DB (writes that begin after the snapshot starts are queued). Millisecond lock is acceptable — every other tool already serializes through the same file. SQLite docs recommend `BEGIN IMMEDIATE` for any read-then-write pattern (which snapshot is, even though we only read the DB). |
| **D9** | Snapshot diff format | PRIMARY format is structured JSON: `{"added": [obs_ids], "removed": [obs_ids], "modified": [{"id": N, "field": "...", "before": ..., "after": ...}], "unchanged_count": N, "summary": "..."}`. Human-readable rendering: if `rich` is available, render as colored terminal table; else plain-text `+` / `-` / `~` markers. CLI flag `--json` forces JSON-only output to stdout for piping. | JSON-primary matches the cross-project-federation D10 BDD pattern (machine-readable by default, human-readable when stdout is a TTY). Field-level diff for `code_refs` blocks (parse + compare node-by-node) — surfaces "binding file changed from X to Y" rather than "content differs". |
| **D10** | Prune safety gate | `flow snapshot prune` without `--confirm` → dry-run, prints JSON report `{would_delete: [snap_ids], would_keep: [snap_ids], freed_bytes: N}` to stdout, exits 0, **deletes nothing**. With `--confirm` → actually deletes. `--keep-last=0` requires BOTH `--confirm` AND `--force` (cannot be combined with `--keep-days` or `--max-total-size-mb`; refuses if both present). The combination `--keep-last=0 --force --confirm` is the only way to delete every snapshot. | Dry-run default mirrors D6 + `flow projects backfill`. Two-flag requirement for "delete everything" prevents the classic "I meant 1, not 0" foot-gun. JSON report makes the dry-run BDD-testable. |
| **D11** | Rollback idempotency | Two-phase commit pattern. **Phase 1 (always succeeds)**: create auto-safety snapshot of CURRENT live state (`trigger=rollback_safety`). **Phase 2 (single SQLite transaction)**: apply target snapshot's state via `BEGIN IMMEDIATE` — `mem_save` for added observations, `update_observation` for modified, soft-delete (set `deleted_at`) for removed. If phase 2 is interrupted (power loss, ctrl-c), the SQLite transaction rolls back atomically: live state is unchanged, the safety snapshot exists, and the user can retry by running `flow snapshot rollback <safety_id>` (which becomes the inverse). Idempotency: re-running the same `flow snapshot rollback <target>` after a phase-2 failure produces the same end state (because phase 1's safety snapshot is also captured first, replacing the safety). | SQLite's `BEGIN IMMEDIATE` + `ROLLBACK` is the atomic primitive. Safety snapshot FIRST means even a partial rollback leaves the user with two valid states (current + safety). Mirrors the `flow projects backfill --confirm` pattern from cross-project-federation #136 — same safety contract across mutating CLI paths. |
| **D12** | Test strategy for snapshot determinism | Two patterns: **(a) Fixture-based**: `tests/fixtures/snapshots/snap_<fixed-timestamp>-<fixed-hex>.json.gz` committed as binary fixtures. Tests load the fixture via `SnapshotManager(snapshots_dir=fixture_dir)` and assert the parsed envelope. **(b) Dynamic via monkeypatch**: for tests that need a specific `created_at`, `monkeypatch.setattr("flow_engineering.snapshot_manager._now_iso", lambda: "2026-06-26T12:34:56Z")`. The `secrets.token_hex` collision suffix is also monkeypatched in tests to a fixed value. **BDD step defs**: use `tmp_path` for new snapshot creation; use fixtures for reading. | Mirrors the test layering from cross-project-federation D10. Determinism comes from TWO sources: (1) committed fixtures for read paths; (2) monkeypatched clock + RNG for write paths. The two sources cross-check each other (e.g., a BDD scenario can load a freshly-created snapshot AND a pre-committed fixture and assert they round-trip identically). |
| **D13** | Cross-impact non-regression | (a) `decision_drift.load_graph(graph_json_path: Path \| None = None, *, snap_id: str \| None = None)` — kwarg-only `snap_id`, default `None` = current behavior (loads live graph.json from `graph_json_path`). When `snap_id` is set, `graph_json_path` MUST be `None` (asserted); reads the snapshot envelope from `~/.flow-engineering/snapshots/<snap_id>.json.gz`, extracts `graph_state.graph_json`, returns `(nodes, id_map, snap_mtime)` built from the frozen content. (b) `decision_drift.scan_change(change_name, *, graph_json_path, backend=None, include_obsolete=False, since=None, *, snap_id: str \| None = None)` — kwarg-only `snap_id`. When set, builds an `InMemoryBackend` from the snapshot's frozen `graph_state.observations` and passes it via `backend=`. Mutually exclusive with `backend=` (asserted). (c) `flow drift <change>` CLI gains `--snapshot=<snap_id>` flag; absent = current behavior. (d) All 699+ existing tests pass without modification. (e) New counters in `SNAPSHOT_COUNTER_NAMES` additive; existing `VECTOR_COUNTER_NAMES` and `FEDERATED_COUNTER_NAMES` byte-identical. | Kwarg-only with `None` default is the additive-default pattern from REQ-17 / REQ-26. The mutual-exclusion assertion (`snap_id` XOR `backend`) prevents the silent-bug case where both are set. Existing CLI behavior is byte-identical when `--snapshot` is absent. Verified by counting test classes: 699+ existing unit + BDD tests must pass unchanged. |

## Data Flow

### Snapshot create

```
$ flow snapshot create --description=pre_drift_fix [--no-include-graph] [--project=<key>]
   │
   ▼
@click snapshot_create(...)                              # cli.py:new
   │
   ▼
SnapshotManager.create(description, trigger="manual")   # snapshot_manager.py
   │
   ├─► begin IMMEDIATE txn on ~/.engram/engram.db       # D8: atomic read
   │     │
   │     ▼
   │   observations = backend.iter_observations()      # frozen view
   │     │
   │     ▼
   │   for obs: bindings = extract_code_refs(obs.content)  # parsed blocks
   │            project_tags = {obs.id: obs.project for obs in obs_list}
   │            drift_history = read_last_n_metrics_jsonl(n=500)
   │            graph_json = (live graph.json)          # D2: full content
   │            aliases = load_aliases(registry_path)
   │     │
   │     ▼
   │   COMMIT txn                                        # release lock
   │
   ├─► envelope = {
   │     schema: 1, id: "snap_<ISO>-<hex>",              # D7
   │     created_at: <ISO>,
   │     trigger: "manual",
   │     description: "pre_drift_fix",
   │     graph_state: {observations, bindings, project_tags, aliases,
   │                   drift_history, graph_json},
   │     metadata: {obs_count, ..., sha256: <canonical-hash>,
   │                 include_graph: True}
   │   }
   │
   ├─► sha256 = hashlib.sha256(canonical_json_dumps(envelope)).hexdigest()  # D2
   │     envelope.metadata.sha256 = sha256
   │
   ├─► tmp = snapshots_dir / f"{id}.tmp.json.gz"        # D11: atomic write
   │     gzip(tmp, json_dumps(envelope, sort_keys=True, separators=(",",":")))
   │     os.replace(tmp, snapshots_dir / f"{id}.json.gz")
   │
   └─► observability.record_snapshot_event("snapshot_created_total",
                                           trigger="manual")
   return id                                              # e.g. "snap_2026-06-26T12-34-56-a3b9f1"
```

### Snapshot rollback (two-phase, D11)

```
$ flow snapshot rollback <snap_id> --confirm [--force]
   │
   ▼
@click snapshot_rollback(...)                            # cli.py:new
   │
   ▼
if not confirm: error("refusing without --confirm")      # D4
   │
   ▼
diff = snapshot_manager.diff(snap_id, "live")           # snapshot vs live
   │
   ▼
if diff.has_conflicts() and not force:                   # D4: hard-fail
   error({conflicts: [...]}, exit 2)
   │
   ▼
safety_id = snapshot_manager.create(                    # D11 phase 1: safety FIRST
    description=f"pre_rollback_to_{snap_id}",
    trigger="rollback_safety"
)
   │
   ▼
BEGIN IMMEDIATE txn                                      # D11 phase 2: atomic apply
   │
   ├─► for added in diff.added: backend.mem_save(obs)    # re-create
   │
   ├─► for mod in diff.modified:
   │       backend.update_observation(mod.id, content=mod.after)
   │
   └─► for rem in diff.removed:
           backend.update_observation(rem.id, deleted_at=<now>)
   │
   ▼
COMMIT                                                    # atomic — either all-or-nothing
   │
   ▼
observability.record_snapshot_event(
    "snapshot_rollback_total", success=True,
    safety_snapshot_id=safety_id, target_snapshot_id=snap_id
)
return RollbackResult(safety_id=safety_id, applied=diff.summary)
```

### Drift-pinned scan (D5)

```
$ flow drift <change> --snapshot=<snap_id>
   │
   ▼
@click drift(...) with snapshot_flag set                 # cli.py:1146 (mod)
   │
   ▼
if snapshot_flag:
    snap = SnapshotManager.show(snapshot_flag)          # load envelope
    frozen_backend = InMemoryBackend(                    # D13: wraps frozen obs
        {obs.id: obs for obs in snap.graph_state.observations}
    )
    graph_json_path_or_none = None                        # load_graph gets snap_id
else:
    frozen_backend = None
    graph_json_path_or_none = Path("~/.flow-engineering/graph.json")
   │
   ▼
report = decision_drift.scan_change(
    change_name=<change>,
    graph_json_path=graph_json_path_or_none,
    backend=frozen_backend or backend,
    snap_id=snapshot_flag,                              # D13: NEW kwarg
)
   │
   ▼
observability.record_drift_summary(report)              # REQ-12 (unchanged)
```

### Snapshot diff

```
$ flow snapshot diff <snap_a> <snap_b> [--json]
   │
   ▼
SnapshotManager.diff(snap_a, snap_b)
   │
   ├─► load both envelopes (parse + sha256 verify)
   │
   ├─► index_obs = {obs.id: obs for obs in envelope.graph_state.observations}
   │
   ├─► added = [id for id in b if id not in a]
   │   removed = [id for id in a if id not in b]
   │   common = [id for id in a & b]
   │
   ├─► for id in common:
   │       before, after = a.obs[id], b.obs[id]
   │       if before.content != after.content:
   │           field = "content" + parsed_block_diff(before, after)
   │           modified.append({id, field, before, after})
   │
   ├─► unchanged_count = len(common) - len(modified)
   │
   └─► summary = f"+{len(added)} -{len(removed)} ~{len(modified)} (unchanged: {unchanged_count})"
   return SnapshotDiff(added, removed, modified, unchanged_count, summary)
```

## File Changes

### New files (~560 LOC production + ~1 400 LOC test)

| File | LOC prod | LOC test | Purpose |
|---|---|---|---|
| `src/flow_engineering/snapshot_manager.py` | ~350 | — | `SnapshotManager` class (6 methods + envelope dataclasses + `SnapshotEnvelopeError`) |
| `tests/unit/test_snapshot_manager.py` | — | ~400 | 30 tests: create round-trip, sha256 tamper detection, list ordering, diff invariants (added/removed/modified/unchanged), rollback safety (2-phase, hard-fail on conflicts, force override), prune dry-run vs confirm, `--keep-last=0` requires both flags, atomic write temp-file cleanup, monkeypatched clock+RNG |
| `tests/unit/test_decision_drift_snap_id.py` | — | ~100 | 5 tests: `load_graph(snap_id=...)` returns frozen content, `scan_change(snap_id=...)` uses frozen observations, mutual-exclusion assertion (`snap_id` XOR `backend` / `graph_json_path`), default `None` byte-identical to current |
| `tests/unit/test_observability_snapshot.py` | — | ~120 | 8 tests: `SNAPSHOT_COUNTER_NAMES` catalog has 4 names; `record_snapshot_event` emits one line per counter; trigger/success/reason field validation; fail-open on `OSError` |
| `tests/bdd/req28_snapshot_create.feature` | — | ~50 | 2 scenarios: round-trip create→load, sha256 mismatch raises `SnapshotEnvelopeError` |
| `tests/bdd/req29_snapshot_list.feature` | — | ~40 | 2 scenarios: list sorted by `created_at` desc, `--since` filter respected |
| `tests/bdd/req30_snapshot_show.feature` | — | ~30 | 1 scenario: show renders compact table; schema mismatch raises |
| `tests/bdd/req31_snapshot_diff.feature` | — | ~80 | 2 scenarios: diff returns expected `added`/`removed`/`modified`/unchanged, field-level diff for `code_refs` |
| `tests/bdd/req32_snapshot_rollback.feature` | — | ~120 | 3 scenarios: rollback requires `--confirm`; hard-fails on conflicts; auto-safety snapshot created FIRST; `--force` overrides with warning |
| `tests/bdd/req33_drift_pinned.feature` | — | ~80 | 2 scenarios: `flow drift --snapshot=<id>` returns frozen-state drift (worked example from D5); without `--snapshot` returns live drift |
| `tests/bdd/req34_snapshot_prune.feature` | — | ~60 | 2 scenarios: dry-run reports `would_delete` JSON, no deletes; `--confirm` + `--keep-last=N` deletes expired |

### Modified files (~80 LOC delta)

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/decision_drift.py` | +25 | `load_graph(graph_json_path=None, *, snap_id=None)`: kwarg-only `snap_id`; when set, reads envelope from `~/.flow-engineering/snapshots/<snap_id>.json.gz`, returns `(nodes, id_map, snap_mtime)` from frozen content. `scan_change(...)`: adds `*, snap_id=None` kwarg; when set, wraps `InMemoryBackend` over frozen observations. Mutual-exclusion assertions. (`decision_drift.py:124` for `load_graph`, `:188` for `scan_change`) |
| `src/flow_engineering/cli.py` | +150 | New `flow snapshot` subcommand group with 6 subcommands (`create`, `list`, `show`, `diff`, `rollback`, `prune`); `--snapshot=<snap_id>` flag on existing `flow drift`; `--no-include-graph` on `flow snapshot create`; `--confirm` / `--force` flags on rollback + prune; `--json` flag on diff + list |
| `src/flow_engineering/observability.py` | +50 | `SNAPSHOT_COUNTER_NAMES` catalog (4 names); `SNAPSHOT_TRIGGER_VALUES` + `SNAPSHOT_ROLLBACK_VALUES` + `SNAPSHOT_PRUNE_REASON_VALUES` frozensets; `record_snapshot_event(name, **fields)` helper mirroring `record_federated_summary` |

**Production total**: ~560 LOC across 1 new + 3 modified (4 total files).
**Test total**: ~1 400 LOC across 4 new unit + 7 new BDD feature files (11 total files).
**Strict-TDD ratio**: ~2.5× (within the 2-4× target — snapshot logic is mostly
file I/O with focused edge cases).

## Interfaces / Contracts

```python
# snapshot_manager.py — NEW
@dataclass(frozen=True)
class SnapshotMeta:
    id: str                       # e.g. "snap_2026-06-26T12-34-56-a3b9f1"
    created_at: str               # ISO 8601 UTC with Z
    trigger: str                  # "manual" | "auto" | "rollback_safety"
    description: str
    obs_count: int
    binding_count: int
    project_count: int
    size_bytes: int               # on-disk byte size of the gzipped envelope
    pinned: bool                  # retention-pin flag — exempt from auto-prune
    include_graph: bool
    path: Path

@dataclass(frozen=True)
class SnapshotDiff:
    added: list[int]                                    # observation ids
    removed: list[int]
    modified: list[dict]                                # {id, field, before, after}
    unchanged_count: int
    summary: str

@dataclass(frozen=True)
class RollbackResult:
    safety_snapshot_id: str
    target_snapshot_id: str
    applied: str                                        # summary string
    forced: bool                                        # True if --force used

@dataclass(frozen=True)
class PruneResult:
    deleted: list[str]                                  # snap_ids actually deleted
    would_delete: list[str]                             # dry-run path
    freed_bytes: int

class SnapshotEnvelopeError(Exception): ...

class SnapshotManager:
    def __init__(self, snapshots_dir: Path, backend: EngramBackend) -> None: ...
    def create(self, description: str = "", *,
               trigger: str = "manual",
               include_graph: bool = True,
               project: str | None = None) -> str: ...
    def list(self, *, since: str | None = None,
             limit: int | None = None) -> list[SnapshotMeta]: ...
    def show(self, snap_id: str) -> dict: ...           # parsed envelope
    def diff(self, snap_id_a: str, snap_id_b: str) -> SnapshotDiff: ...
    def rollback(self, snap_id: str, *,
                 confirm: bool = False,
                 force: bool = False) -> RollbackResult: ...
    def prune(self, *,
              keep_last: int | None = None,
              keep_days: int | None = None,
              max_total_size_mb: float | None = None,
              confirm: bool = False) -> PruneResult: ...

# decision_drift.py — MODIFIED, NON-BREAKING
def load_graph(graph_json_path: Path | None = None,
               *, snap_id: str | None = None
              ) -> tuple[dict | None, dict | None, float | None]:
    """When snap_id is set, loads graph.json content FROM the snapshot envelope
    instead of from disk. graph_json_path MUST be None in that case."""

def scan_change(change_name: str, *,
                graph_json_path: Path | None,
                backend: "EngramBackend | None" = None,
                include_obsolete: bool = False,
                since: float | None = None,
                snap_id: str | None = None) -> DriftReport:
    """When snap_id is set, backend MUST be None and graph_json_path SHOULD be
    None — the snapshot provides both. Uses an InMemoryBackend built from
    snapshot.graph_state.observations."""

# observability.py — MODIFIED, NON-BREAKING
SNAPSHOT_COUNTER_NAMES: list[str] = [
    "snapshot_created_total",
    "snapshot_diff_invoked_total",
    "snapshot_rollback_total",
    "snapshot_pruned_total",
]

SNAPSHOT_TRIGGER_VALUES: frozenset[str] = frozenset({
    "manual", "auto", "rollback_safety"
})
SNAPSHOT_ROLLBACK_VALUES: frozenset[str] = frozenset({"success", "failure"})
SNAPSHOT_PRUNE_REASON_VALUES: frozenset[str] = frozenset({"age", "count", "size"})

def record_snapshot_event(name: str, **fields: Any) -> None:
    """Emit one SNAPSHOT_COUNTER_NAMES event. Validates trigger/success/reason
    fields against the frozensets above; invalid values fall back to safe
    defaults. Failures absorbed by `increment` — never raises."""
```

## Worked Example for D5 (drift-pinned scan)

**T=2026-06-01 12:00 UTC** — `flow snapshot create --description=pre_db_migration`:

```json
{
  "schema": 1, "id": "snap_2026-06-01T12-00-00-a3b9f1",
  "created_at": "2026-06-01T12:00:00Z", "trigger": "manual",
  "graph_state": {
    "observations": [
      {"id": 42, "title": "Use sqlite-vec", "content":
        "Decision: use sqlite-vec.\n\n<!-- code_refs -->\n{\"nodes\": [...]}"},
      ...
    ],
    "bindings": [{"obs_id": 42, "nodes": [...]}],
    "project_tags": {"42": "flow-engineering"},
    "aliases": [],
    "drift_history": [...],
    "graph_json": {"nodes": [{"id": "vec_store", "file": "vectors/sqlite_vec_store.py",
                              "line": 42, "label": "SQLiteVecStore"}]}
  },
  "metadata": {"sha256": "abc123...", "include_graph": true, ...}
}
```

**Today (2026-06-26)** — `vectors/sqlite_vec_store.py` was refactored;
`vec_store` node now lives at `line 87` (stale location).

```bash
$ flow drift vector-semantic-search --snapshot=snap_2026-06-01T12-00-00-a3b9f1
```

Pipeline:
1. CLI loads `snap_2026-06-01T12-00-00-a3b9f1` envelope.
2. `scan_change(change_name="vector-semantic-search",
   snap_id="snap_2026-06-01T12-00-00-a3b9f1", backend=None, ...)`:
   - Loads snapshot's frozen `graph_state.observations` (5 obs, 12 bindings).
   - Calls `load_graph(snap_id="snap_2026-06-01T12-00-00-a3b9f1")` which
     extracts `graph_state.graph_json` (NOT live disk) → returns
     `(nodes={vec_store: {file: ..., line: 42}}, id_map={vec_store:
     (vectors/sqlite_vec_store.py, 42, "SQLiteVecStore")}, snap_mtime=...)`.
   - Iterates frozen observations; for each binding, classifies against the
     snapshot's frozen `current_id_map`.
3. Result: `DriftReport(class_counts={STILL_VALID: 12}, graph_unavailable=False)`.

Compare to today's scan (no `--snapshot`):

```bash
$ flow drift vector-semantic-search
```

Pipeline reads LIVE graph.json (vec_store at line 87 now) + LIVE observations →
`DriftReport(class_counts={STILL_VALID: 9, STALE_LOCATION: 3})`.

Different snapshots → different drift reports → historical drift trend analysis
works. The user's question "did bindings drift gradually or suddenly?" becomes
answerable: plot `STALE_LOCATION` count across N daily snapshots.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | SnapshotManager.create | `tmp_path` snapshots_dir; monkeypatched clock + RNG; assert envelope shape, sha256, atomic write (no `.tmp` left behind) |
| Unit | sha256 tamper detection | Create snapshot, flip 1 byte in the .gz file, assert `SnapshotEnvelopeError` on `show()` |
| Unit | SnapshotManager.list | Create 5 snapshots with monkeypatched ascending `created_at`; assert desc order; `--since` filter |
| Unit | SnapshotManager.diff | Fixtures of 2 snapshots with known add/remove/modify; assert exact lists and summary |
| Unit | Rollback hard-fail | Mock backend with conflicting observation; assert `RollbackConflictError` without `--force`, applies with `--force` |
| Unit | Prune safety | Dry-run asserts no deletes; `--confirm` deletes; `--keep-last=0` requires `--force`+`--confirm` |
| Unit | `load_graph(snap_id=...)` | Committed snapshot fixture; assert frozen nodes match envelope (not live disk) |
| Unit | `scan_change(snap_id=...)` | Same fixture; assert `DriftReport.class_counts` from frozen state, NOT live |
| Unit | Mutual-exclusion assertion | `scan_change(snap_id=X, backend=Y)` raises `ValueError` |
| Unit | Counter catalog | `SNAPSHOT_COUNTER_NAMES` has exactly 4 names; `record_snapshot_event` emits correct shape |
| Integration | Round-trip via real SQLite | Seed 5 observations in `InMemoryBackend`; create snapshot; rollback to it; assert state restored |
| BDD (REQ-28) | create round-trip | GIVEN empty snapshots dir WHEN `flow snapshot create --description=X` THEN file exists + envelope valid |
| BDD (REQ-29) | list ordering | GIVEN 3 snapshots created in order WHEN `flow snapshot list` THEN sorted desc |
| BDD (REQ-30) | show renders | GIVEN snapshot X WHEN `flow snapshot show X` THEN stdout is compact table with id/created_at/obs_count |
| BDD (REQ-31) | diff invariants | GIVEN snap_a with 5 obs, snap_b with 4 obs (1 removed, 1 modified) WHEN `flow snapshot diff` THEN JSON output has added/removed/modified counts |
| BDD (REQ-32) | rollback safety | GIVEN live DB diverged from snapshot WHEN `flow snapshot rollback --confirm` THEN auto-safety snapshot created FIRST; live state restored |
| BDD (REQ-32) | hard-fail on conflict | GIVEN live has 1 obs added since snapshot WHEN `flow snapshot rollback --confirm` THEN exits 2 with conflict list |
| BDD (REQ-33) | drift-pinned | GIVEN snapshot T1 with bindings at (file, line) WHEN `flow drift --snapshot=T1` THEN report matches T1 state (NOT today's state) |
| BDD (REQ-33) | non-breaking | GIVEN no `--snapshot` flag WHEN `flow drift <change>` THEN behavior byte-identical to current |
| BDD (REQ-34) | prune dry-run | GIVEN 5 snapshots WHEN `flow snapshot prune --keep-last=2` (no --confirm) THEN stdout lists would_delete=3, files unchanged |
| BDD (REQ-34) | prune apply | Same as above WITH `--confirm`; assert 3 files deleted, 2 remain |
| Secrets invariant | code_refs exposes only metadata | GIVEN observation text mentions `secrets.yaml` WHEN `flow snapshot create` THEN envelope `bindings` contain file=`secrets.yaml`, line=N, label=`...` — NO file contents |

## Migration / Rollout

**No data migration** is automatic. The user's existing 172 observations stay
untouched. Two opt-in paths:

1. **First snapshot**: `flow snapshot create --description=initial_state`
   captures current state. Until that runs, `~/.flow-engineering/snapshots/`
   is empty / non-existent (lazy-created).

2. **Drift trend adoption**: existing `flow drift <change>` works without
   `--snapshot` (byte-identical to current). New `--snapshot` flag is opt-in.

**Rollback**: single revert of the merge commit restores pre-change state.
- New file `snapshot_manager.py` is self-contained, easy to delete.
- Modified files (`cli.py`, `decision_drift.py`, `observability.py`) only ADD
  new symbols / subcommands; no existing behavior removed.
- `snap_id` kwarg on `load_graph` / `scan_change` is keyword-only with default
  `None`; callers that don't pass it see no behavior change.
- New runtime dir `~/.flow-engineering/snapshots/` is empty until first
  `flow snapshot create`; deleting it is harmless.
- The user's own snapshots are NOT touched by a code revert. To restore live
  state to a prior point in time, the user runs `flow snapshot rollback <id>`
  BEFORE reverting the code PR.

## Open Questions — RESOLVED (all 10 from propose #174)

| # | Question | Resolution |
|---|---|---|
| **1** | Auto-trigger policy | **NEVER auto in v1.** Manual only via `flow snapshot create`. Auto-safety snapshots happen ONLY on rollback (D3 + D11, mirrors `flow projects backfill` precedent). No `flow watch` hook, no cron, no systemd timer — deferred to v2 when a real daily-backup workflow emerges. (Resolves Q1 from proposal: opt-in flag deferred to v2 entirely.) |
| **2** | `--include-graph` flag | **Default ON for v1.** The flag is `--no-include-graph` (excludes `graph_state.graph_json` from the envelope, saving ~5 MB/snapshot). Without graph content, drift-pinned scans (D5) return `SnapshotGraphMissing` error rather than silently scanning against live graph.json. (Resolves Q2 from proposal: deferred flag promoted to default-on for D5 to work; users who want mtime-only can opt out.) |
| **3** | Compression default | **gzip ON by default.** `--no-compress` flag writes `.json` instead of `.json.gz` for `jq` ergonomics. (Resolves Q3 from proposal as proposed.) |
| **4** | Rollback conflict policy | **Hard-fail by default.** Detect new observations added/modified/deleted since snapshot's `created_at`; refuse with non-zero exit + JSON error listing the conflicting `observation_id`s. `--force` flag overrides (DANGEROUS, prints warning to stderr, increments `snapshot_rollback_total{success=false}` BEFORE applying). `--confirm` still required alongside `--force`. (Resolves Q4 from proposal as proposed.) |
| **5** | Cross-project default | **Full DB (all projects) by default.** `--project=<key>` is a read-time slice for `flow snapshot show <id> --project=<key>`. Parity with `mem_search_federated(projects=None)` from cross-project-federation D1. (Resolves Q5 from proposal as proposed.) |
| **6** | Snapshot ID determinism | **Monotonic ISO + 6-char hex suffix.** `snap_<YYYY-MM-DDTHH-MM-SS>-<hex>.json.gz` — collision-safe even with clock skew, simultaneous creation, or DST transitions. (Resolves Q6 from proposal: hex suffix added to the proposed monotonic ISO for collision safety.) |
| **7** | Drift-pinned semantics (CRITICAL) | **Scan SNAPSHOT state, NOT live state.** `flow drift --snapshot=<id> <change>` reads frozen observations + frozen graph.json from the envelope, runs `scan_change` against both. Different snapshots → different drift reports → historical drift trend analysis works. (REJECTS proposal Q7's "scan live" recommendation — that interpretation makes `--snapshot` a no-op and disables the headline use case from explore #173.) |
| **8** | Prune default behavior | **Dry-run when no flags.** Exit 0, JSON `{would_delete, would_keep, freed_bytes}` to stdout, deletes nothing. User MUST pass at least one of `--keep-last`, `--keep-days`, `--max-total-size-mb` AND `--confirm` to actually delete. (Resolves Q8 from proposal as proposed.) |
| **9** | SHA256 over what | **Canonicalized JSON** (sorted keys, no whitespace), NOT raw gzip bytes. Deterministic across filesystem encodings (the gzipped bytes may differ across implementations). Tamper detection becomes "envelope is what I wrote" regardless of gzip implementation. (REJECTS proposal Q9's "raw gzip bytes" recommendation — byte-level integrity is less portable; canonical-JSON integrity is what `code_refs` schema_version 1 already uses.) |
| **10** | First-snapshot auto-label | **YES, auto-label `initial_state`.** When the snapshot dir is empty (or non-existent), the FIRST `flow snapshot create` automatically uses `description="initial_state"`. User can override by passing `--description=<other>` explicitly — explicit wins. The auto-label is a UX nudge, not a hard-coded default. (Resolves Q10 from proposal as proposed.) |

**Resolved: 10/10. Remaining: 0.**

## Unblocks / Constraints

**Unblocks**: temporal diff between any two snapshots, full-state rollback with
safety net, byte-exact audit via sha256, drift pattern detection over time
(correlate `metrics.jsonl` events with snapshot mtime), federated timeline
queries (REQ-23..27 + snapshots = "what was each project's state at milestone X?"),
historical drift trend analysis (D5 worked example).

**Constrains**: any future change that extends `decision_drift.load_graph()` or
`scan_change()` must keep the `snap_id` kwarg-only contract (no positional
args). Snapshots must remain JSON-encoded + sha256-stamped; binary formats
would break `flow snapshot show <id> | jq` ergonomics. The `graph_json`
default-on default means v1 snapshots are ~6 MB uncompressed; users who
want a leaner store use `--no-include-graph` but lose drift-pinned scans.

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Reuses `binding.extract_code_refs()` for snapshot block parsing | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `load_graph()` + `scan_change()` seams extended with kwarg-only `snap_id` | Compatible (existing callers unaffected; new flag is opt-in) |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is in `~/.flow-engineering/vectors.sqlite`; snapshots capture PROSE state + graph.json + drift history; vectors NOT included in v1 | Compatible (boundary respected); v2 may snapshot vector index separately |
| `cross-project-federation` (shipped v0.5.0) | `flow projects backfill --confirm` confirmation gate is the precedent for `flow snapshot rollback --confirm` + `flow snapshot prune --confirm` | Compatible (same safety pattern); no federation coupling |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |

## Chained PR Strategy

**SINGLE PR** (per propose #174 recommendation; no chaining needed).

| PR | Scope | Forecast LOC | Forecast ×2.5 TDD | Acceptance |
|---|---|---|---|---|
| **PR#1** | All 7 REQs (REQ-28..34): SnapshotManager class + 6 methods + envelope schema v1 + sha256 + atomic write + 4 counters + `--snapshot` flag on `flow drift` + 7 BDD features + 4 unit test files + observability catalog + CHANGELOG v0.6.0 + 6 SKILL.md | ~560 production | ~1 400 test | All 699+ existing tests still pass; new tests pass with `--run-slow`; ruff + mypy clean; secrets-invariant BDD green; sha256 tamper test red→green |

**Chain strategy**: stacked-to-main (consistent with prior 4 changes).
**400-line review budget risk**: medium — PR#1 is ~1 960 total LOC, **above
the 400-line budget for review**. **Mitigation**: single PR with detailed
commit splits per work-unit-commits skill convention:

- **Commit 1**: `feat(snapshot_manager): envelope schema + sha256 + atomic write` (~200 prod LOC, 0 tests yet — RED phase)
- **Commit 2**: `test(snapshot_manager): create + list + show round-trip` (~400 test LOC — RED→GREEN evidence)
- **Commit 3**: `feat(snapshot_manager): diff with field-level code_refs delta` (~120 prod + 200 test — REFACTOR)
- **Commit 4**: `feat(snapshot_manager): rollback two-phase + safety snapshot + hard-fail` (~100 prod + 200 test — most complex)
- **Commit 5**: `feat(decision_drift): snap_id kwarg + frozen-state scan` (~25 prod + 100 test — REQ-33)
- **Commit 6**: `feat(snapshot_manager): prune retention with safety gate` (~80 prod + 150 test — REQ-34)
- **Commit 7**: `feat(observability): 4 SNAPSHOT_COUNTER_NAMES + record_snapshot_event` (~50 prod + 120 test)
- **Commit 8**: `docs(changelog): v0.6.0 entry + 6 SKILL.md updates + 7 BDD feature files` (~80 prod + 350 test/docs)

The per-commit diffs stay focused (≤400 LOC each) so review remains tractable
even though the cumulative PR is large. This is the chained-PR-as-commits
pattern from the `work-unit-commits` skill.

## Decision ↔ Code Binding

10 `code_refs` nodes (manual source) bind the design decisions to existing
anchor points:

- `SnapshotManager (NEW — create/list/show/diff/rollback/prune)` → `src/flow_engineering/snapshot_manager.py:1`
- `SnapshotEnvelopeError (NEW exception — raised on sha256/schema mismatch)` → `src/flow_engineering/snapshot_manager.py:30`
- `SnapshotMeta/SnapshotDiff/RollbackResult/PruneResult (NEW dataclasses)` → `src/flow_engineering/snapshot_manager.py:50`
- `flow snapshot subcommand group (NEW — 6 subcommands)` → `src/flow_engineering/cli.py:1`
- `flow drift --snapshot=<id> (NEW flag — REQ-33)` → `src/flow_engineering/cli.py:1146`
- `decision_drift.load_graph (MODIFIED — snap_id kwarg, non-breaking)` → `src/flow_engineering/decision_drift.py:124`
- `decision_drift.scan_change (MODIFIED — snap_id kwarg, non-breaking)` → `src/flow_engineering/decision_drift.py:188`
- `observability.record_snapshot_event (NEW helper — mirrors record_federated_summary)` → `src/flow_engineering/observability.py:430`
- `SNAPSHOT_COUNTER_NAMES (NEW catalog — 4 counters)` → `src/flow_engineering/observability.py:90`
- `binding.extract_code_refs (REUSED — snapshot block parsing)` → `src/flow_engineering/binding.py:1`

---

## Structured Metadata

- **decisions_count**: 13 (D1..D13)
- **open_questions_resolved**: 10/10 (all from propose #174)
- **open_questions_remaining**: 0
- **file_count**: 4 new + 3 modified + 11 new test = 18 total (4 prod new + 4 unit test new + 7 BDD feature new + 3 prod modified)
- **loc_forecast**: ~560 production + ~1 400 test = ~1 960 total
- **pr_count**: 1 (single PR; commits split per work-unit-commits convention for review tractability)
- **next_recommended**: `sdd-spec graph-snapshots`

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_class",
      "label": "SnapshotManager (NEW — create/list/show/diff/rollback/prune)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_envelope_error",
      "label": "SnapshotEnvelopeError (NEW — sha256/schema mismatch)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 30,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_dataclasses",
      "label": "SnapshotMeta/SnapshotDiff/RollbackResult/PruneResult (NEW dataclasses)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 50,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_snapshot_group",
      "label": "flow snapshot subcommand group (NEW — 6 subcommands)",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_drift_snapshot_flag",
      "label": "flow drift --snapshot=<id> (NEW flag — REQ-33)",
      "file": "src/flow_engineering/cli.py",
      "line": 1146,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_load_graph_snap_id",
      "label": "load_graph(graph_json_path=None, *, snap_id=None) (kwarg-only extension)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 124,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_scan_change_snap_id",
      "label": "scan_change(change_name, *, ..., snap_id=None) (kwarg-only extension)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 188,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_snapshot_event",
      "label": "record_snapshot_event (NEW helper — mirrors record_federated_summary)",
      "file": "src/flow_engineering/observability.py",
      "line": 430,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_snapshot_counter_names",
      "label": "SNAPSHOT_COUNTER_NAMES catalog (NEW — 4 counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 90,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_binding_extract_code_refs",
      "label": "extract_code_refs (reused — snapshot block parsing)",
      "file": "src/flow_engineering/binding.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}
