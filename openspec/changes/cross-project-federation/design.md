# Design: cross-project-federation

> Mirror of Engram `sdd/cross-project-federation/design` (topic_key upsert
> after file creation). Reference format mirrors
> [`openspec/changes/vector-semantic-search/design.md`](../../vector-semantic-search/design.md)
> (D1–D11). The Engram `code_refs` block is appended at file end so
> `flow inspect <change>` can render the binding surface.

## Technical Approach

`cross-project-federation` adds an **additive** multi-project retrieval
layer on top of the existing prose `mem_search` contract. Two surfaces land:

1. **Federated query** — `EngramBackend.mem_search_federated(query, projects,
   limit, since, type_filter, *, scope)` joins `observations` with
   `observations_fts` and applies `project IN (...)` + `created_at >= ?` +
   `type IN (...)` filters in a single BM25-ranked pass. ABC default raises
   `NotImplementedError`; `InMemoryBackend` implements it for tests; the
   production MCP-backed impl runs the same SQL against
   `~/.engram/engram.db`. NO new infra — the shared SQLite + FTS5 already
   exist (verified: `idx_obs_project`, `idx_obs_type`, `idx_obs_created`,
   `observations_fts` virtual table all present).

2. **Tagging discipline + rename absorption** — three small modules:
   - `project_detector.py` (NEW): `detect(cwd) -> str | None`, walks the
     user-editable `~/.config/flow-engineering/registry.json` and returns the
     deepest-matching project key. Opt-in via `FLOW_AUTO_PROJECT_TAG=1`.
     Explicit `project=` always wins.
   - `project_aliases.py` (NEW): `resolve(name) -> str` reads
     `~/.config/flow-engineering/project-aliases.json` (forward-only map),
     applies it to every `project` read so `flow-image-generator-v2`
     transparently resolves to `flow-image-generator-main`.
   - `flow projects alias <old> <new>` + `flow projects backfill [--dry-run
     --confirm]` subcommands for safe rename migration.

CLI gets 3 opt-in flags on the existing `flow search`:
`--federated --projects=<csv> --since=<iso> --type=<csv>`. Default mode is
byte-identical to today. Observability adds three counters
(`federated_search_invoked_total`,
`federated_search_projects_queried`,
`federated_search_results_returned_total`) exposed via
`record_federated_summary(...)`, paralleling `record_vector_summary`.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | `mem_search_federated` signature and SQL strategy | Signature: `mem_search_federated(query, projects=None, *, limit=10, since=None, type_filter=None, scope="project")`. Single SQL pass: `SELECT … FROM observations_fts JOIN observations o ON o.id = observations_fts.rowid WHERE observations_fts MATCH ? [AND o.project IN (?, …)] [AND o.created_at >= ?] [AND o.type IN (?, …)] ORDER BY bm25(observations_fts) LIMIT ?`. **`projects=None` ⇒ no project filter (search all). `projects=[]` ⇒ short-circuit return `[]` (explicit empty is an error in IN-clause SQL — fail fast). Non-empty list ⇒ parameterised IN clause.** | Mirrors the v1.1 pattern from `mem_search_semantic` / `mem_search_hybrid`. BM25 ranking is already what `mem_search` returns; we reuse it. Single-pass avoids N round-trips per project. IN-clause parameterisation is safe (no SQL injection); the empty-list short-circuit prevents the `IN ()` SQLite syntax error. ABC default raises `NotImplementedError` (mirrors `engram_io.py:147` `update_observation` precedent). |
| **D2** | `project_detector` state machine | Lookup chain (first hit wins): (a) explicit `project=` argument, (b) `FLOW_PROJECT_OVERRIDE` env var (escape hatch), (c) registry lookup via `detect(cwd)`. **Return `None` when cwd matches no entry AND is not the registry root** — the caller decides fallback. `flow save` / `EngramClient.save_phase` apply the detected key ONLY when (a) `FLOW_AUTO_PROJECT_TAG=1` AND (b) caller omitted `project=` AND (c) `detect(cwd)` returned a non-None key. | Returning `None` (not `"insyd"`) prevents silent mis-tagging from `/tmp/foo` or `~/Downloads`. Explicit `project=` always wins so users can override without env vars. The opt-in gate keeps existing scripts byte-identical when `FLOW_AUTO_PROJECT_TAG` is unset. |
| **D3** | Backfill CLI safety gate | `flow projects backfill [--dry-run] [--confirm] [--project=<key>]` — **default is `--dry-run`**. To write, caller MUST pass `--confirm` (no interactive prompt; explicit flag wins). Without `--project=<key>`, backfill iterates the alias map (NOT a global scan) and emits a JSON report listing each `observation_id` with its old→new project. The alias map is the ONLY source of truth for what gets renamed — no regex, no fuzzy matching, no full-corpus scan from a global backfill. | `--dry-run` default + `--confirm` gate mirrors the `flow reindex --dry-run` precedent (`cli.py:643`) and the `flow projects` guard semantics in REQ-15. JSON output is machine-readable (BDD scenarios can assert exact lists). Hard-requirement on the alias map keeps mass-renames opt-in and reviewable. |
| **D4** | Three federated counter shapes | `federated_search_invoked_total` (counter, default `count=1` per call), `federated_search_projects_queried` (histogram via `count=<N>` per call where N is the number of projects in the query), `federated_search_results_returned_total` (counter, `count=<N>` where N is the number of rows returned). All three live in `metrics.jsonl` like every other counter. `record_federated_summary(invoked=1, projects_queried=N, results_returned=M)` mirrors `record_vector_summary`. | Names follow the established REQ-8 / REQ-22 convention (`<verb>_<noun>_total` for counters; `count=` for cardinalities; no `_total` suffix on the histogram because the value IS already a count). `federated_search_projects_queried` is intentionally NOT `_total` because the same call may have 1 or 17 projects — `count=` per call gives a per-call histogram of project-bucket size, which is the metric a user actually wants ("how wide were my federated queries?"). |
| **D5** | ABC version bump v1.1 → v1.2 | Bump `EngramBackend` class docstring to **"ABC v1.2"** and add `mem_search_federated` as a NON-BREAKING default method that raises `NotImplementedError`. Same precedent as v1.1 (`mem_search_semantic`, `mem_search_hybrid`) and the older `update_observation` (`engram_io.py:147`). `InMemoryBackend.mem_search_federated` IMPLEMENTS the method (returns filtered rows from the in-memory dict) — the prose path is testable without the production SQLite backend. | Documenting the bump keeps third-party subclasses honest. The non-breaking default means existing imports keep working; only callers that invoke `mem_search_federated` on a non-overriding subclass get a call-time error. |
| **D6** | `type_filter` matching | Exact-match (case-sensitive) on `observations.type`. CLI parses `--type=decision,bugfix,pattern` via `csv_split` (no regex, no aliasing). Empty list ⇒ no type filter (search all). No-match ⇒ return empty list, no error. Documented in `flow search --help`. | Exact match matches what `idx_obs_type` already supports efficiently. Aliasing (`bug=bugfix`) is a future concern; adding it now would require a translation table that drifts out of sync with the Engram schema. Behaviour on no-match returns empty (not error) so an overly-narrow `--type` is a silent miss, not a CLI failure. |
| **D7** | `since` filter semantics | `since` is an ISO 8601 date OR datetime. Comparison: `WHERE created_at >= ?` — **lexicographic** because `created_at` is stored as ISO-style TEXT (`YYYY-MM-DD HH:MM:SS` per SQLite `datetime('now')` default). UTC assumed (no timezone conversion): `--since 2026-01-01` means "everything from 2026-01-01 00:00:00 UTC inclusive". Pre-existing `_parse_since` helper at `cli.py:892` parses to epoch seconds for `flow drift`; federated reuses the same parser for CLI parity but passes the original ISO string through to SQL. | Lexicographic comparison on ISO 8601 strings is correct ONLY when the format is fixed-width. SQLite's `datetime('now')` returns `YYYY-MM-DD HH:MM:SS` (no `T`, no `Z`) — a consistent fixed-width format, so `>=` works. UTC-only matches the precedent set by `flow drift --since` (`cli.py:1045-1046`). Date-only input (`2026-01-01`) is treated as midnight UTC. |
| **D8** | Alias config schema | `~/.config/flow-engineering/project-aliases.json` shape: `{ "version": 1, "aliases": [ {"old": "flow-image-generator-v2", "new": "flow-image-generator-main", "created_at": "2026-06-26T19:46:07Z"}, … ] }`. Loaded on startup, cached in memory, applied to every `project` read. Write API: `flow projects alias <old> <new>` appends to the `aliases` array (idempotent: if `<old> -> <existing_new>` already present, no-op + prints confirmation; if `<old> -> <different_new>` already present, ERRORS to prevent silent history loss). Backfill is a separate `flow projects backfill` invocation — never auto-runs. Atomic write via `tempfile + Path.replace`. Missing or malformed file ⇒ start with empty list + `alias_config_load_failed_total` counter increment. | List-of-records preserves history (audit trail — you can see WHEN each rename happened and WHAT the old key was). The JSON-map format would lose the `created_at` per alias. Version field is the standard pattern from `vector-semantic-search` D6 / `flow-engineering/config.py` precedent — future schema bumps don't break loaders. Explicit idempotency rule prevents the classic "alias drifted to a wrong key" silent failure mode. |
| **D9** | Non-breaking guarantees | (a) `EngramBackend.mem_search_federated` ABC default raises `NotImplementedError` — third-party subclasses import unchanged (same as v1.1 / REQ-17). (b) `flow search` without `--federated` flag is byte-identical to current behaviour (existing scripts unaffected). (c) `FLOW_AUTO_PROJECT_TAG` defaults unset — no auto-tag happens. (d) `~/.config/flow-engineering/registry.json` and `project-aliases.json` are empty by default; missing file ⇒ empty list, no error. (e) `mem_search` (single-project FTS5) unchanged. (f) Existing tests pass — `InMemoryBackend.mem_search_federated` is the ONLY behavioural addition. | Matches the "additive default pattern" rule established by `update_observation` (REQ-3) and `mem_search_semantic` (REQ-17). Verified by counting test classes: existing 25 BDD + 32 unit (`test_engram_io.py`, `test_observability.py`, `test_cli_search_semantic.py`, etc.) must pass without modification. New tests extend the existing files. |
| **D10** | Test strategy for federated queries | **Unit tests** use `tmp_path` SQLite fixtures (not the real `~/.engram/engram.db`) via `pytest`'s `tmp_path` fixture + a tiny in-memory schema that mirrors the live one. **Integration test**: seed 3 projects × 10 observations = 30 rows; assert BM25 rank order across the federated query. **Backfill safety**: dry-run + confirm tests with a simulated 50-obs corpus where 1 obs has `project=flow-image-generator-v2` and the alias config maps it to `flow-image-generator-main` — assert `--dry-run` writes nothing AND `--confirm` updates exactly 1 row. **Alias resolution**: test that `flow-image-generator-v2` queries return the renamed row. **InMemoryBackend test seam**: `mem_search_federated` returns filtered rows from the in-memory dict so unit tests don't need SQLite. **Secrets invariant** (REQ-15 carry-over): BDD scenario GIVEN an observation text mentions `secrets.yaml` WHEN `mem_search_federated` runs THEN no file is opened during the call (asserted via `monkeypatch.delattr(os, "stat")` or similar disk-touch detector). | Mirrors the test layering from `vector-semantic-search` design (test_seam_unit + fixture_integration + bdd_scenarios). The secrets-invariant test is the critical cross-cutting test that protects against accidental file leakage in a future refactor. |
| **D11** | Migration / back-compat | Existing observations in `~/.engram/engram.db` may have wrong or absent `project` tags. The migration is **NOT automatic**: users must run `flow projects backfill` explicitly. **First-run seeding**: when the registry is missing, `flow projects` subcommands auto-scan `FLOW_PROJECTS_ROOT` (default `C:\dev\proyects`) ONCE on first invocation that needs the registry, persist to `registry.json`, then load from disk on subsequent runs. The user can edit `registry.json` manually — manual entries win on key collision. **Pre-existing observations with no project tag**: `iter_observations()` returns them with `project=None`; `mem_search_federated` filters them out when `projects` is non-None (because `project IN (...)` does not match NULL); when `projects=None` they ARE included. The `insyd` default applies only when a NEW observation is saved without a project tag AND `FLOW_AUTO_PROJECT_TAG` is unset — existing data is unchanged. | Single explicit backfill step is auditable. Auto-scan on first run matches the "convenient defaults, explicit overrides" pattern from `vector-semantic-search` (the `_vectors_sqlite_path` default at `cli.py:292`). Pre-existing NULL `project` rows are NOT silently renamed to `insyd` — that would be a destructive mass-rename. |

## Data Flow

### Federated query (CLI)

```
$ flow search --federated --projects=p1,p2 --since=2026-01-01 --type=decision "drift"
   │
   ▼
@click search(...)                                # cli.py search() — adds 4 flags
   │
   ▼
backend.mem_search_federated(                    # EngramBackend.mem_search_federated
    query="drift",
    projects=["p1","p2"],                         # CSV split in CLI
    since="2026-01-01",                           # parsed to ISO string for SQL
    type_filter=["decision"],                     # CSV split in CLI
    limit=10,
)
   │
   ▼
project_aliases.resolve(...)                     # applied to projects list BEFORE SQL
   │
   ▼
SQL: SELECT … FROM observations_fts JOIN observations o …
     WHERE observations_fts MATCH 'drift'
       AND o.project IN ('p1','p2')
       AND o.created_at >= '2026-01-01'
       AND o.type IN ('decision')
     ORDER BY bm25(observations_fts) LIMIT 10;
   │
   ▼
observability.record_federated_summary(...)      # 3 counters
   │
   ▼
_render_search_table(rows) | json.dumps({...})
```

### Project detector + auto-tag

```
$ FLOW_AUTO_PROJECT_TAG=1 flow save my-change explore <content>
   │
   ▼
EngramClient.save_phase(phase, content)
   │
   ▼
   detect_key = project_detector.detect(Path.cwd())   # walks registry.json
   │              │
   │              ├─ match → "mockup-2-blog"
   │              └─ no match → None
   │
   ▼
if FLOW_AUTO_PROJECT_TAG == "1" and detect_key is not None:
    project_tag = detect_key                          # otherwise pass None → backend default
else:
    project_tag = None                                # backend decides (InMemoryBackend → "insyd")
   │
   ▼
backend.mem_save(..., project=project_tag)            # explicit project param NEW in v1.2
```

### Backfill (alias → re-tag)

```
$ flow projects backfill --dry-run
   │
   ▼
read ~/.config/flow-engineering/project-aliases.json
   │
   ▼
for alias in aliases:
    rows = backend.iter_observations(project=alias.old)   # pre-rename scan
    for row in rows:
        print {"observation_id": row.id, "old": alias.old, "new": alias.new}
   │
   ▼
exit 0 (no writes, JSON report to stdout)

$ flow projects backfill --confirm --project=flow-image-generator-v2
   │
   ▼
(same scan, but writes)
   │
   ▼
for row in rows:
    backend.update_observation(row.id, project=alias.new)
    observability.increment("project_tag_backfilled_total", project=alias.new)
```

## File Changes

### New files (~370 LOC production)

| File | LOC | Purpose |
|---|---|---|
| `src/flow_engineering/project_detector.py` | ~80 | `detect(cwd)` + registry loader + `apply_tag(obs_id, project)`; opt-in via `FLOW_AUTO_PROJECT_TAG=1` |
| `src/flow_engineering/project_aliases.py` | ~110 | `resolve(name)` + JSON IO + atomic write + version field migration; list-of-records schema |
| `tests/unit/test_project_detector.py` | ~140 | RED fixtures: cwd matches sub-project, cwd is registry root, cwd is unknown (`None`), env override, registry missing, registry malformed |
| `tests/unit/test_project_aliases.py` | ~120 | resolve identity, missing file, malformed JSON, atomic write, idempotent add, conflicting add errors |
| `tests/unit/test_engram_io_federated.py` | ~180 | ABC default raises; InMemoryBackend filtering by projects/since/type; BM25 rank order; empty-projects short-circuit |
| `tests/unit/test_cli_federated.py` | ~100 | 4-flag matrix on `flow search --federated` |
| `tests/unit/test_cli_projects_alias.py` | ~80 | `flow projects alias`, `flow projects backfill --dry-run`, `--confirm`, `--project=` |
| `tests/unit/test_observability_federated.py` | ~70 | 3 counters increment on synthetic run; `record_federated_summary` helper |
| `tests/bdd/req23_federated_search.feature` | ~70 | 5 BDD scenarios (multi-project rank, since filter, type filter, secrets invariant, default off) |
| `tests/bdd/req24_project_detector.feature` | ~50 | 3 BDD scenarios (auto-tag, opt-in gate, explicit override wins) |
| `tests/bdd/req25_cli_federated.feature` | ~60 | 3 BDD scenarios (CLI flag matrix, JSON output includes project, dry-run safety) |

### Modified files (~80 LOC delta)

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/engram_io.py` | +35 | Add `mem_search_federated` ABC default raising `NotImplementedError`; `InMemoryBackend` overrides it (returns filtered rows); docstring bumped to "ABC v1.2" |
| `src/flow_engineering/cli.py` | +30 | 4 new flags on `flow search` (`--federated --projects=<csv> --since=<iso> --type=<csv>`); new `flow projects` group with `alias` + `backfill` subcommands |
| `src/flow_engineering/observability.py` | +25 | 3 new counters + `record_federated_summary(...)` helper mirroring `record_vector_summary`; add to a future `FEDERATED_COUNTER_NAMES` list (matches `VECTOR_COUNTER_NAMES` precedent) |

**Production total**: ~370 LOC across 3 new + 3 modified files (6 total).
**Test total**: ~870 LOC across 7 new unit + 3 new BDD feature files.
**Strict-TDD ratio**: ~2.4× (under the 3-4× target — federation is mostly composition + small modules, not heavy logic).

## Interfaces / Contracts

```python
# EngramBackend ABC v1.2 — new method, NON-BREAKING default
def mem_search_federated(
    self,
    query: str,
    projects: list[str] | None = None,
    *,
    limit: int = 10,
    since: str | None = None,
    type_filter: list[str] | None = None,
    scope: str = "project",
) -> list[dict[str, Any]]:
    """Search across N project tags in a single FTS5 pass (v1.2).

    Returns rows with ``project`` field preserved for attribution.
    Default impl raises NotImplementedError — concrete backends MUST override.
    """

# project_detector.py — NEW
def detect(cwd: Path, *, registry: Registry | None = None) -> str | None:
    """Return the deepest-matching project key for cwd, or None."""

def apply_tag(observation_id: int, project: str, *, backend: EngramBackend) -> dict:
    """Re-tag a single observation. Refuses when project is empty."""

# project_aliases.py — NEW
def resolve(name: str, *, aliases: list[AliasRecord] | None = None) -> str:
    """Forward alias resolution. Identity for non-aliased names."""

def load_aliases(path: Path | None = None) -> list[AliasRecord]:
    """Load from disk; missing/malformed → empty list + counter."""

def save_aliases(aliases: list[AliasRecord], path: Path | None = None) -> None:
    """Atomic write (tempfile + Path.replace)."""

# observability.py — NEW helper
def record_federated_summary(
    *, invoked: int = 1, projects_queried: int, results_returned: int
) -> None:
    """Emit the 3 federated counters in one call (mirrors record_vector_summary)."""
```

## Worked Example for D1 + D7 (federated query)

Database state (simplified):

```
id=42, project=mockup-2-blog, type=decision, created_at="2025-11-15 12:00:00", title="Use Astro for static blog"
id=43, project=flow-engineering, type=decision, created_at="2026-02-01 09:30:00", title="Use sqlite-vec for embeddings"
id=44, project=tecnodespegue-landing, type=decision, created_at="2026-05-20 14:00:00", title="Use Postgres for landing CMS"
```

CLI invocation:
```
flow search --federated --projects=mockup-2-blog,flow-engineering --since=2026-01-01 --type=decision "embeddings"
```

After `project_aliases.resolve(...)` (idempotent here, no aliases match):

```sql
SELECT o.id, o.title, o.content, o.type, o.project, o.created_at, o.topic_key,
       bm25(observations_fts) AS score
FROM observations_fts
JOIN observations o ON o.id = observations_fts.rowid
WHERE observations_fts MATCH 'embeddings'
  AND o.project IN ('mockup-2-blog','flow-engineering')
  AND o.created_at >= '2026-01-01'
  AND o.type IN ('decision')
ORDER BY score
LIMIT 10;
```

Result:
```json
[
  {"id": 43, "title": "Use sqlite-vec for embeddings", "project": "flow-engineering",
   "created_at": "2026-02-01 09:30:00", "score": -1.45}
]
```

Observability: `federated_search_invoked_total` += 1,
`federated_search_projects_queried` count=2, `federated_search_results_returned_total` count=1.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | ABC default raises; InMemoryBackend filtering | `tmp_path` fixture, in-memory dict, assert row shapes; no SQLite |
| Unit | project_detector | `monkeypatch.setattr` on registry; fixtures for cwd under sub-project, cwd is parent, cwd is unknown, env var override |
| Unit | project_aliases | load/save round-trip; missing file → empty; malformed JSON → empty + counter; atomic write temp-file cleanup |
| Unit | CLI flags | Click `CliRunner`; assert exit codes, JSON output shape, dry-run vs confirm |
| Unit | Observability | synthetic run; assert 3 counters present in `metrics.jsonl` |
| Integration | 3-project × 10-obs fixture | assert BM25 rank order across the federated query; alias resolution changes which rows surface |
| BDD | Secrets invariant | GIVEN an observation text references `secrets.yaml` WHEN `mem_search_federated` runs THEN no file is opened (monkeypatch on `pathlib.Path.open` / `os.stat`) |
| BDD | Opt-in gate | GIVEN `FLOW_AUTO_PROJECT_TAG` unset WHEN `flow save` runs THEN observation is tagged `insyd` (default), not the cwd's project |
| BDD | Explicit wins | GIVEN `FLOW_AUTO_PROJECT_TAG=1` AND caller passes `project=` explicitly WHEN `flow save` runs THEN explicit project wins |
| BDD | Backfill safety | GIVEN alias config maps `flow-image-generator-v2` → `flow-image-generator-main` AND 1 obs tagged `flow-image-generator-v2` WHEN `flow projects backfill --dry-run` runs THEN no rows change AND stdout lists the obs id; WHEN `--confirm` runs THEN exactly 1 row updates |

## Migration / Rollout

**No data migration** is automatic. The user's existing 158 observations stay
untouched. Two opt-in migration paths:

1. **Tagging discipline** — set `FLOW_AUTO_PROJECT_TAG=1` in the env. Future
   `flow save` runs from `C:\dev\proyects\mockup-2-blog` will tag new
   observations as `mockup-2-blog`. Historical observations are NOT retro-tagged
   (would require guessing intent).

2. **Rename migration** — for the known rename `flow-image-generator-v2` →
   `flow-image-generator-main`:
   ```
   flow projects alias flow-image-generator-v2 flow-image-generator-main
   flow projects backfill --dry-run        # review
   flow projects backfill --confirm --project=flow-image-generator-v2
   ```
   The alias config means new federated queries transparently resolve
   `flow-image-generator-v2` to `flow-image-generator-main` even WITHOUT the
   backfill run.

**Rollback**: single revert of the merge commit restores pre-change state.
New files (`project_detector.py`, `project_aliases.py`) are self-contained.
Runtime configs (`registry.json`, `project-aliases.json`) default to empty —
deleting them is harmless. ABC bump from v1.1 → v1.2 is additive (callers
that don't call the new method see no change).

## Open Questions — RESOLVED (all 8 from propose #158)

| # | Question | Resolution |
|---|---|---|
| 1 | Registry auto-build: first run vs manual edit? | **AUTO-BUILD ON FIRST USE**: scan `FLOW_PROJECTS_ROOT` (default `C:\dev\proyects`) once, persist to `~/.config/flow-engineering/registry.json`, cache in memory. Manual edits to `registry.json` win on key collision (user override beats auto-scan). Lazy — does NOT run on plain `flow search`; only when `flow projects …`, `flow save` with `FLOW_AUTO_PROJECT_TAG=1`, or `project_detector.detect()` is called. |
| 2 | Auto-detect fallback: None vs `"insyd"`? | **RETURN `None`**. Caller decides. Prevents the trap where a script in `/tmp/foo` silently tags as `insyd`. `InMemoryBackend.mem_save` keeps its current `project="insyd"` default for backward compat (used by every existing test) — only the new `apply_tag` path overrides. |
| 3 | Backfill confirmation gate? | **`--dry-run` default + `--confirm` required to write**. No interactive prompt — explicit flag wins. JSON output always. Alias map is the ONLY source of truth (no regex, no fuzzy match). `--project=<key>` scopes the operation to a single alias; without it the operation iterates the entire alias map. |
| 4 | `federated_search_projects_queried` histogram vs gauge? | **HISTOGRAM** via `count=<N>` per call where N = number of projects in the query. NO `_total` suffix because the value IS the count. Mirrors REQ-22 `vector_search_latency_ms` precedent (per-event `elapsed_ms` is a histogram too). |
| 5 | ABC version bump policy? | **BUMP TO v1.2** in docstring. Same non-breaking-default pattern as REQ-17 (v1.1). `update_observation` at `engram_io.py:147` is the canonical precedent. CHANGELOG entry. |
| 6 | `--type` CSV format? | **EXACT MATCH, case-sensitive, CSV split on comma**. No aliasing (`bug=bugfix`) in v1. Documented in `flow search --help`. Empty list → no type filter. |
| 7 | `--since` semantics? | **ISO 8601 date or datetime, UTC assumed**. Lexicographic `WHERE created_at >= ?` because `created_at` is stored as `YYYY-MM-DD HH:MM:SS` TEXT (verified via `.schema`). Date-only input → midnight UTC inclusive. Reuse `_parse_since` from `cli.py:892` for CLI parity. |
| 8 | Alias file format? | **LIST-OF-RECORDS with version field**. `{ "version": 1, "aliases": [ {"old": …, "new": …, "created_at": "2026-06-26T…Z"}, … ] }`. Preserves audit history. JSON-map (`{old: new}`) loses `created_at` per alias — rejected for audit reasons. |

## Unblocks / Constraints

**Unblocks**: meaningful cross-project search; an `sdd-explore` sub-agent
in `flow-engineering` that can ask "has any peer decided between Postgres
and sqlite-vec?" and get a ranked answer with `project` attribution per hit;
a v2 of `vector-semantic-search` that generalises to federation once the
prose federated path is battle-tested.

**Constrains**: any future change that adds a method to `EngramBackend` must
either follow the v1.2 additive-default pattern or bump the version. The
`FLOW_AUTO_PROJECT_TAG` opt-in means existing tagging discipline (mostly
`insyd`) is unchanged for users who don't set the env var.

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `update_observation` reused by backfill path | Compatible (consumes seam) |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses `decision_id`, not `project` | No conflict |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is per-project by file path; federation routes PROSE, not vectors | Compatible (boundary respected); future v2 may federate vectors |
| `graph-snapshots` (#5) | Graph nodes are change-scoped, not project-scoped | No conflict |
| `prompt-registry` (#7) | Unrelated layer | No conflict |

## Chained PR Strategy

**SINGLE PR** (per propose #158 recommendation; no chaining needed).

| PR | Scope | Forecast LOC | Forecast ×2.4 TDD | Acceptance |
|---|---|---|---|---|
| **PR#1** | All 5 REQs (REQ-23..27): ABC v1.2 + InMemoryBackend federated impl + project_detector + project_aliases + CLI flags + CLI subcommands + 3 counters + 3 BDD features | ~370 production | ~870 test | All 576+ existing tests still pass; new tests pass with `--run-slow`; ruff + mypy clean; secrets-invariant BDD green |

**Chain strategy**: stacked-to-main (consistent with prior 4 changes).
**400-line review budget risk**: low — PR#1 is comfortably under budget
(~370 production + ~870 test, well under the ~1500 total LOC threshold).

## Decision ↔ Code Binding

8 `code_refs` nodes (manual source) bind the design decisions to existing anchor points:

- `EngramBackend ABC v1.2 (mem_search_federated)` → `src/flow_engineering/engram_io.py:53`
- `update_observation default (NotImplementedError precedent)` → `src/flow_engineering/engram_io.py:147`
- `InMemoryBackend (test seam, will override mem_search_federated)` → `src/flow_engineering/engram_io.py:150`
- `flow search (--federated flags added)` → `src/flow_engineering/cli.py:531`
- `_parse_since (CLI ISO date parser, reused for --since)` → `src/flow_engineering/cli.py:892`
- `flow drift --since (precedent for --since flag)` → `src/flow_engineering/cli.py:1045`
- `observability.record_vector_summary (counter-batch helper precedent)` → `src/flow_engineering/observability.py:295`
- `VECTOR_COUNTER_NAMES (catalog precedent for FEDERATED_COUNTER_NAMES)` → `src/flow_engineering/observability.py:63`

---

## Structured Metadata

- **decisions_count**: 11 (D1..D11)
- **open_questions_resolved**: 8/8 (all from propose #158)
- **open_questions_remaining**: 0
- **file_count**: 11 new + 3 modified = 14 total (3 prod new + 8 test new + 3 prod modified)
- **loc_forecast**: ~370 production + ~870 test = ~1.24k total
- **pr_count**: 1 (single PR, no chained split)
- **next_recommended**: `sdd-spec cross-project-federation`

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_engrambackend_v1_2",
      "label": "EngramBackend ABC v1.2 (adds mem_search_federated)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 53,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_update_observation_default",
      "label": "update_observation default (NotImplementedError precedent)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 147,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_inmemorybackend",
      "label": "InMemoryBackend (test seam — overrides mem_search_federated)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 150,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_project_detector",
      "label": "project_detector (NEW — detect/apply_tag)",
      "file": "src/flow_engineering/project_detector.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_project_aliases",
      "label": "project_aliases (NEW — resolve + JSON IO)",
      "file": "src/flow_engineering/project_aliases.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_search_v1_2",
      "label": "flow search (--federated/--projects/--since/--type flags added)",
      "file": "src/flow_engineering/cli.py",
      "line": 531,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_parse_since",
      "label": "_parse_since (ISO date parser — reused by --since federated)",
      "file": "src/flow_engineering/cli.py",
      "line": 892,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_since_precedent",
      "label": "flow drift --since (precedent for federated --since)",
      "file": "src/flow_engineering/cli.py",
      "line": 1045,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_vector_summary",
      "label": "observability.record_vector_summary (counter-batch helper precedent)",
      "file": "src/flow_engineering/observability.py",
      "line": 295,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_vector_counter_names",
      "label": "VECTOR_COUNTER_NAMES (catalog precedent for FEDERATED_COUNTER_NAMES)",
      "file": "src/flow_engineering/observability.py",
      "line": 63,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}
