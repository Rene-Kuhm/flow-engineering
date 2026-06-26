<!-- Proposal: cross-project-federation. Source: manual. -->
# Proposal: cross-project-federation

## Intent

`flow-engineering`'s `EngramBackend` exposes `mem_search` with single-project
filters, so an `sdd-explore` agent in one sub-project can't cheaply see what
peers in `mockup-2-blog` or `tecnodespegue-landing` already decided. This
change adds **additive** multi-project (Penpax) retrieval on top of the
existing prose contract — never replacing `mem_search` — so sdd sub-agents
can ask "has any peer decided between Postgres and sqlite-vec?" and get a
ranked answer with `project` attribution per hit. Tagging discipline (most
work currently lands in `project=insyd`) is fixed in the same change via
opt-in auto-detection, because the query API alone is useless if observations
aren't tagged with the right project to begin with.

## Context (from explore)

The user's original framing assumed per-project Engram DBs ("7 silos"). That
premise was **wrong** — there is **one** shared SQLite at `~/.engram/engram.db`
(3.4 MB, WAL, FTS5-indexed by `project`) with 155 observations across 9
`project` values. The silos are **logical** (`project` column), not **physical**
(separate DB files). This collapses the problem from "merge N separate DBs"
to "add a federated query API + fix tagging discipline". See
[`explore.md`](./explore.md) and Engram #156 for the full option matrix.

## Approach — Sketch A, additive `mem_search_federated` on the shared DB

`EngramBackend.mem_search_federated(...)` is added as a NON-BREAKING ABC
default (returns `NotImplementedError`, mirrors REQ-17 / REQ-22 convention).
`InMemoryBackend` implements it for tests; the production MCP-backed impl
runs a single FTS5 query with `project IN (...)` plus optional `created_at`
and `type` filters. No new infra, no sync, no hub.

Five cooperating pieces:

1. **`EngramBackend.mem_search_federated(query, projects=None, limit=10,
   since=None, type_filter=None, scope="project")`** — ABC method.
   `projects=None` means "search ALL project tags" (the federated default).
   `projects=["flow-engineering","mockup-2-blog"]` restricts to a list.
   Returns hits with the `project` field preserved per row.
2. **`project_detector` module (NEW)** — `detect(cwd) -> str | None` walks a
   user-editable `~/.config/flow-engineering/projects.json` registry
   (`{abs_path: project_key}`) and returns the deepest-matching project key
   for the cwd. When `FLOW_AUTO_PROJECT_TAG=1` is set, `mem_save` uses the
   detected key when the caller omits `project=`. Explicit `project=` always
   wins.
3. **`project_aliases` module (NEW) + `~/.config/flow-engineering/project-aliases.json`** —
   forward alias map `{old: new}`. Loaded on startup, applied to every
   `project` read so `flow-image-generator-v2` transparently resolves to
   `flow-image-generator-main`. `flow projects alias <old> <new>` writes it
   idempotently; `flow projects backfill [--dry-run]` retro-tags
   under-tagged observations (CLI subcommand).
4. **CLI surface** — `--federated --projects=<csv> --since=<iso>
   --type=<csv>` flags added to existing `flow search`. Off by default →
   existing scripts unaffected. JSON output includes `project` per row.
5. **Observability** — 3 counters via `record_federated_summary(...)`:
   `federated_search_invoked_total`,
   `federated_search_projects_queried` (histogram of project-count per query),
   `federated_search_results_returned_total`.

### Distribution

No new runtime dependencies — the shared SQLite + FTS5 already exist. JSON
parsing via stdlib (`json`).

## Scope

### In Scope
- `EngramBackend.mem_search_federated(...)` (NEW ABC method, default
  `NotImplementedError`)
- `InMemoryBackend.mem_search_federated(...)` (test seam)
- `src/flow_engineering/project_detector.py` (NEW) — `detect()`, registry
  loader, `apply_tag()` helper
- `src/flow_engineering/project_aliases.py` (NEW) — `resolve()`, file IO
- `~/.config/flow-engineering/projects.json` (NEW runtime config, default
  `{}` — populated lazily on first run by scanning `FLOW_PROJECTS_ROOT`)
- `~/.config/flow-engineering/project-aliases.json` (NEW runtime config,
  default `{}`)
- `flow search --federated --projects=<csv> --since=<iso> --type=<csv>`
  flags (NEW) on existing `flow search`
- `flow projects alias <old> <new>` (NEW subcommand)
- `flow projects backfill [--dry-run]` (NEW subcommand)
- 3 federated observability counters + `record_federated_summary(...)`
  helper in `observability.py`
- Backfill-once migration: re-tag `flow-image-generator-v2` (1 obs) →
  `flow-image-generator-main` via the alias config

### Out of Scope (deferred — see Risks §)
- HTTP-based federation (option B) — not needed, single-host shared DB
- MCP server federation (option F) — not needed
- Cross-DB federation — there IS only one DB
- Central hub publication (option G) — explicitly violates Penpax
- Periodic sync (option D) — violates "no sync"
- Federated semantic search (option C) — depends on vector-semantic-search
  battle-test in production; possible v2
- Per-peer physical DB isolation — not needed today
- Hosting embedding fallback / model hot-swap — out of scope per
  vector-semantic-search v1 boundary

## Capabilities

### New Capabilities
- `cross-project-federation`: search across multiple Engram project tags in
  a single FTS5 query, surface `project` attribution per hit, opt-in
  auto-detection of project tag from cwd, and forward alias absorption for
  renamed project keys. Fully additive — never replaces prose `mem_search`.

### Modified Capabilities
- None. `vector-semantic-search` (REQ-17/18/22), `decision-code-linking`
  (REQ-1..8), and `decision-reality-drift` (REQ-9..16) are unchanged. The
  new ABC method defaults to `NotImplementedError` (same pattern REQ-17
  established). Existing `mem_search` byte-identical when `--federated`
  is absent.

## Public API surface

- `EngramBackend.mem_search_federated(query, projects=None, limit=10,
  since=None, type_filter=None, *, scope="project") -> list[dict]` (NEW)
- `project_detector.detect(cwd: Path) -> str | None` (NEW)
- `project_detector.apply_tag(observation_id: int, project: str) -> dict`
  (NEW)
- `project_aliases.resolve(name: str) -> str` (NEW; identity for non-aliased)
- `flow search --federated --projects=<csv> --since=<iso> --type=<csv>
  <query>` (NEW flags)
- `flow projects alias <old> <new>` (NEW subcommand)
- `flow projects backfill [--dry-run]` (NEW subcommand)
- `observability.record_federated_summary(invoked, projects_queried,
  results_returned)` (NEW helper)

## Non-breaking guarantees

- `EngramBackend` ABC: new method defaults to `NotImplementedError` — same
  additive pattern REQ-17 / REQ-22 used for `mem_search_semantic` and
  `mem_search_hybrid`. Third-party subclasses import unchanged.
- `flow search` without `--federated` flag: byte-identical to current
  behavior; existing scripts unaffected.
- Existing `mem_search` (FTS5 single-project) unchanged.
- All existing 385+ tests still pass — backfill-once script uses
  `update_observation` already present in the ABC.
- Auto-tagging opt-in via `FLOW_AUTO_PROJECT_TAG=1`; default off. Explicit
  `project=` always wins.
- Alias resolver is forward-only (old → new); non-aliased names are
  identity-mapped.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/engram_io.py` | MODIFY | Add `mem_search_federated` ABC default + `InMemoryBackend` impl |
| `src/flow_engineering/project_detector.py` | NEW | detect + apply_tag + registry loader |
| `src/flow_engineering/project_aliases.py` | NEW | resolve + JSON IO + atomic write |
| `src/flow_engineering/cli.py` | MODIFY | 3 new flags on `flow search`; 2 new subcommands under `flow projects` |
| `src/flow_engineering/observability.py` | MODIFY | 3 new counters + `record_federated_summary` |
| `src/flow_engineering/orchestrator.py` | MODIFY (optional) | thread detected project key into `EngramClient.save_phase` when `FLOW_AUTO_PROJECT_TAG=1` |
| `~/.config/flow-engineering/projects.json` | NEW (runtime) | `{abs_path: project_key}` registry; lazy-built on first run |
| `~/.config/flow-engineering/project-aliases.json` | NEW (runtime) | forward alias map; default `{}` |
| `tests/unit/test_project_detector.py` | NEW | RED fixtures: matches sub-project, parent (`insyd`), unknown cwd, env override |
| `tests/unit/test_project_aliases.py` | NEW | resolve identity, missing file, malformed JSON, atomic write |
| `tests/unit/test_federation.py` | NEW | multi-project scan, `since` filter, `type_filter`, ABC default raises |
| `tests/bdd/req23_federation.feature` | NEW | ~8-10 BDD scenarios (see Success Criteria) |
| `tests/bdd/test_federation_steps.py` | NEW | pytest-bdd glue |
| `openspec/changes/cross-project-federation/{design,spec,tasks}.md` | NEW | follow-on phases |
| `CHANGELOG.md` | MODIFY | v0.5.0 entry post-merge |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Federation surfaces a `project=tecnosquire-infra` observation whose text quotes a SOPS path | Med | "No file re-read" invariant test — `mem_search_federated` MUST never touch disk beyond the Engram DB; observations stored are user-authored summaries only. Add BDD scenario GIVEN a fake SOPS observation WHEN federated search runs THEN result text contains no path matching `secrets.yaml` |
| Stale observations from 2024 surface as "fresh" hits, masking newer decisions | Med | `--since` filter exposed in CLI; existing `review_after` column honored via existing `compute_freshness`; downstream callers can compose |
| 3 of 7 sub-projects lack `.git` — auto-detect from cwd is the only viable tag source | Low | The detector walks the user-editable registry + filesystem only; git status is not consulted |
| User tagged an observation as `project=insyd` intentionally for cross-cutting notes | Med | Auto-detection is **opt-in** (`FLOW_AUTO_PROJECT_TAG=1`); explicit `project=` always wins; never overwrite without opt-in |
| Adding a new ABC method bumps `EngramBackend` to v1.2 — third-party subclasses that don't override get a call-time `NotImplementedError` | Low | Default impl raises `NotImplementedError` (same pattern REQ-17). Document in CHANGELOG and `EngramBackend` docstring. ABC version bump from "v1.1" → "v1.2" |
| Auto-detection gets the cwd wrong when running tests from a tmpdir not in the registry | Low | Detector returns `None` (not `insyd`) when no match — caller decides fallback; tests use `monkeypatch.setattr` to inject a fixed registry |
| Backfill script accidentally re-tags the WRONG observations (e.g., mass-renames `flow-image-generator-v2` → `flow-image-generator-main` AND every other `-v2` key) | Med | Backfill is **opt-in** via explicit `flow projects backfill` subcommand; `--dry-run` first; alias config is per-key (not regex); add `--confirm` gate for non-dry-run; log every change to observability with `project_tag_corrected_total` counter |
| `project-aliases.json` file gets corrupted by half-written write | Low | Atomic write via `tempfile` + `Path.replace`; missing or malformed file → start with empty `{}` + observability increment |
| Performance: federated query on a corpus with 9 project buckets and 155 obs is fine; on 10k+ obs it may be slow | Low | `idx_obs_project` already covers the filter; `LIMIT` honored; benchmarks in `tests/perf/` (stretch goal, NOT v1) |
| Embedding-rerank temptation creeps into PR (REQ-17 / REQ-22 boundary) | Med | Out of scope per this proposal; PR review must reject any embedding-rerank commit; deferred to a named follow-up change |

## Rollback Plan

All artifacts are additive — single revert of the merge commit restores
pre-change state. The new files (`project_detector.py`, `project_aliases.py`)
are self-contained. The runtime config files (`projects.json`,
`project-aliases.json`) are empty `{}` by default; deleting them is harmless.
ABC bump from v1.1 → v1.2 is additive (callers that don't call the new
method see no change). The `--federated` flag is opt-in; without it,
`flow search` runs the existing prose path.

## Dependencies

- **None new**. Uses existing `sqlite3` + FTS5 + stdlib `json`.
- `decision-code-linking` (shipped v0.2.0) — independent; `update_observation`
  seam reused by the backfill path.
- `vector-semantic-search` (shipped v0.4.0) — independent; federation operates
  on the prose index, NOT the vector index. REQ-17 / REQ-22 contracts unchanged.
- `decision-reality-drift` (shipped v0.3.0) — independent; drift uses
  `decision_id`, not project.

## Open Questions (for sdd-design)

1. **Registry discovery**: should `projects.json` be auto-built by scanning
   `FLOW_PROJECTS_ROOT` (default `C:\dev\proyects`) on first run, or must
   the user edit it manually? **Recommend** auto-build on first run (one-time,
   idempotent) + manual override file wins.
2. **Auto-detection fallback**: when cwd matches no entry AND cwd is not the
   `FLOW_PROJECTS_ROOT` parent, return `None` (caller decides) OR default to
   `insyd` (current behavior)? **Recommend** return `None`; caller decides.
   Avoids the trap where a script in `/tmp/foo` silently tags as `insyd`.
3. **Backfill gate**: should `flow projects backfill` require `--confirm` or
   prompt? **Recommend** `--dry-run` first; require `--confirm` for the
   actual write; print summary of what WOULD change.
4. **Counter `federated_search_projects_queried`**: histogram (one event per
   query with `count=<N>`) or gauge (latest value)? **Recommend** histogram
   (mirrors REQ-22 `vector_search_latency_ms` precedent).
5. **ABC version bump**: v1.1 → v1.2 in docstring, or just document as
   additive? **Recommend** v1.2 in docstring — keeps the contract honest.
6. **Type filter vs scope**: should `type_filter` accept a CSV like
   `--type=decision,bugfix`? **Recommend** yes; mirrors `--projects=<csv>`.
7. **`since` semantics**: filter on `created_at` or `updated_at`? Recommend
   `created_at` (matches `flow drift --since` precedent at `cli.py:1046`).
8. **Alias file format**: JSON map (`{old: new}`) or JSON list
   (`[{old,new}]`)? **Recommend** JSON map — single-key reads, idempotent
   writes via simple `dict[key] = value`.

## Success Criteria

- [ ] `InMemoryBackend.mem_search_federated("drift", projects=["p1","p2"])` returns
      only observations whose `project` is `p1` or `p2`, in BM25 rank order
- [ ] Federated search returns rows with `project` field preserved per hit
- [ ] `flow search --federated --projects=flow-engineering,mockup-2-blog
      "Astro"` exits 0 and renders a table with `project` column populated
- [ ] `flow search --federated --since=2026-01-01 --type=decision <q>` filters
      correctly (BDD scenario)
- [ ] `flow projects alias flow-image-generator-v2 flow-image-generator-main`
      is idempotent: second invocation is a no-op + prints confirmation
- [ ] `flow projects backfill --dry-run` lists the changes it WOULD make
      without writing; `--confirm` performs the write
- [ ] When `FLOW_AUTO_PROJECT_TAG=1`, `EngramClient.save_phase(...)` called
      from `C:\dev\proyects\mockup-2-blog` tags the observation with
      `project=mockup-2-blog`
- [ ] When `FLOW_AUTO_PROJECT_TAG=1` is unset, no auto-tag happens
      (byte-identical to current)
- [ ] Alias resolver: `flow-image-generator-v2` resolves to
      `flow-image-generator-main`; `flow-engineering` resolves to itself
- [ ] All 3 federated counters increment on a synthetic run; `flow metrics`
      surfaces them
- [ ] ABC default: a third-party subclass that doesn't override the new
      method gets `NotImplementedError` at call time, not import time
- [ ] Secrets invariant: a fixture observation referencing `secrets.yaml`
      is NOT augmented with file contents by `mem_search_federated`
- [ ] REQ-17 / REQ-18 / REQ-22 (vector search) tests stay green
- [ ] REQ-5 prose tokenization unchanged
- [ ] REQ-9..16 drift detector unchanged
- [ ] Ruff lint clean on changed files
- [ ] Strict TDD evidence: every public method has RED→GREEN→REFACTOR
      history in commit log

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Reuses `update_observation` for backfill | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses `decision_id`, not `project` | No conflict |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is per-project by file path; federation routes PROSE, not vectors | Compatible (boundary respected); future v2 may federate vectors |
| `graph-snapshots` (#5) | Graph nodes are change-scoped, not project-scoped | No conflict |
| `prompt-registry` (#7) | Unrelated layer | No conflict |

**Unblocks**: meaningful cross-language + cross-project search; finding peer
observations by meaning not keyword (future v2 once vector-semantic-search is
battle-tested); an `sdd-explore` agent that knows about prior decisions in
sibling sub-projects instead of re-discovering them.

**Constrains**: any future change that adds a method to `EngramBackend` must
either bump the ABC version or follow the v1.2 additive-default pattern
established here. Backfill is opt-in; future changes that depend on a
backfilled `project` tag must document the dependency and refuse to run
without it.

## Estimated Effort

- **Apply LOC (forecast)**: ~400-600 production + ~1500-2400 tests (×3-4 TDD
  multiplier). Mirrors `vector-semantic-search` PR#1 scale.
- **Chained PR strategy**: **NO — single PR**. The work fits in one ~600-LOC
  PR + ~1.5k test LOC; PR#2 would be cosmetic CLI polish only. Review budget:
  ~400-500 lines per the chained-pr convention, comfortably under.
- **Phase estimate**:
  - ~15min explore (DONE)
  - ~10min propose (this phase)
  - ~20min design
  - ~15min spec
  - ~10min tasks
  - ~60-90min apply (single PR)
  - ~10min verify
  - ~10min archive
  - **Total ~2-2.5h end-to-end**

## Next Step

Ready for `sdd-design cross-project-federation`. The 8 open questions above
MUST be resolved in the design phase (especially backfill confirmation gate
and registry auto-build behavior) before `sdd-spec` locks the requirement
contract. Single PR — no chained PR split needed.

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_engrambackend",
      "label": "EngramBackend (v1.2 — adds mem_search_federated)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 53,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_inmemorybackend",
      "label": "InMemoryBackend (test seam for federated)",
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
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_project_aliases",
      "label": "project_aliases (NEW — resolve + JSON IO)",
      "file": "src/flow_engineering/project_aliases.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_search",
      "label": "flow search (--federated flags added)",
      "file": "src/flow_engineering/cli.py",
      "line": 496,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_drift_summary",
      "label": "observability.record_drift_summary (precedent)",
      "file": "src/flow_engineering/observability.py",
      "line": 249,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}