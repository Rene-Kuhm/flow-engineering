<!-- Spec: cross-project-federation. Source: manual. -->
# Spec: cross-project-federation

**Change:** `cross-project-federation`
**Builds on:** `proposal.md` (Sketch A — additive `mem_search_federated` on the shared SQLite, opt-in via `FLOW_AUTO_PROJECT_TAG=1`, alias map for rename absorption), `design.md` (D1-D11 resolved: NON-BREAKING ABC v1.2, single-pass FTS5 IN clause, `None` fallback for detector, `--dry-run`+`--confirm` backfill gate, histogram counter shape, exact-match `type_filter`, lexicographic `since` ISO comparison, list-of-records alias schema with audit history, additive ABC, tmp_path SQLite fixtures, no auto data migration)
**Date:** 2026-06-26
**Status:** SPECIFIED → ready for sdd-tasks

## Goal

`flow-engineering`'s `EngramBackend.mem_search` is single-project FTS5; an `sdd-explore` agent running inside one sub-project can't cheaply see what peers in `mockup-2-blog` or `tecnodespegue-landing` already decided. This change ships **additive** multi-project retrieval on top of the existing prose contract — never replacing `mem_search` — so sdd sub-agents ask "has any peer decided between Postgres and sqlite-vec?" and get a BM25-ranked answer with `project` attribution per hit. Tagging discipline (most observations currently land in `project=insyd`) is fixed in the same change via opt-in cwd-based auto-detection, because the federated query API alone is useless if observations aren't tagged with the right project to begin with. Rename absorption via `project-aliases.json` lets the federation transparently resolve `flow-image-generator-v2` to `flow-image-generator-main` without forcing a destructive mass-backfill. Activation is **opt-in** via `FLOW_AUTO_PROJECT_TAG=1`; the default install never auto-tags. ABC is annotated v1.2 in docstring (documentation only). Federation operates on the prose index, NOT the vector index — vector-semantic-search (REQ-17..22) stays green.

**Filter truth table** (matches design D1, D6, D7):

| `projects` | `since` | `type_filter` | SQL filter applied |
|---|---|---|---|
| `None` | `None` | `None` | `observations_fts MATCH ?` only |
| `["p1","p2"]` | `None` | `None` | `… AND o.project IN ('p1','p2')` |
| `[]` (empty list) | anything | anything | short-circuit return `[]` (SQL `IN ()` is a syntax error) |
| `["p1"]` | `"2026-06-01"` | `["decision"]` | `… AND o.project IN ('p1') AND o.created_at >= '2026-06-01' AND o.type IN ('decision')` |

**Alias resolver contract** (matches design D8): `project_aliases.resolve(name)` is forward-only (`old → new`), identity for non-aliased names, applied to every `project` read BEFORE SQL.

---

## PR#1 — Federated query + tagging discipline + rename absorption

### REQ-23: `mem_search_federated` on `EngramBackend` ABC v1.2

The system SHALL provide `EngramBackend.mem_search_federated(query, projects=None, *, limit=10, since=None, type_filter=None, scope="project") -> list[dict[str, Any]]` as a NON-BREAKING default method on the v1.2 ABC. The default implementation SHALL raise `NotImplementedError` (mirrors the `update_observation` precedent at `engram_io.py:147` and the v1.1 pattern from REQ-17). `InMemoryBackend.mem_search_federated` SHALL override the default and return filtered rows from the in-memory dict so unit tests do not require SQLite.

When `projects is None`, the system SHALL NOT add a `project` filter to the SQL (search all 9 project tags). When `projects` is a non-empty list, the system SHALL parameterise an `IN (?, ?, …)` clause with one placeholder per project (no SQL string interpolation). When `projects` is an empty list (`[]`), the system SHALL short-circuit and return `[]` BEFORE the SQL runs (SQLite rejects `IN ()` as a syntax error). The `since` parameter, when provided, SHALL be compared against `observations.created_at` with `>=` using lexicographic string comparison because `created_at` is stored as `YYYY-MM-DD HH:MM:SS` TEXT (verified via `sqlite3 .schema`). The `type_filter` parameter, when provided, SHALL match `observations.type` exactly (case-sensitive) and accept either a single string or a list (the list form is the v1.2 contract; the single-string form is the convenience wrapper the CLI uses). Each returned dict SHALL include the `project` field preserved verbatim so the caller can attribute hits to a peer project.

#### Scenario: Federated search across 3 projects returns results from each with `project` field per row

- GIVEN an Engram backend seeded with one observation per project (`mockup-2-blog`, `flow-engineering`, `tecnodespegue-landing`), each containing the term "drift" in its content
- WHEN `mem_search_federated("drift", projects=["mockup-2-blog", "flow-engineering", "tecnodespegue-landing"], limit=10)` runs
- THEN the returned list has length `3`
- AND each result dict has a non-null `project` field equal to one of the three queried projects
- AND the union of `project` values across the result list equals the input set (no project is silently dropped)

#### Scenario: `projects=["flow-engineering"]` restricts the result set to a single project

- GIVEN a backend seeded with 5 observations in `flow-engineering` containing "drift"
- AND 3 observations in `mockup-2-blog` containing "drift"
- WHEN `mem_search_federated("drift", projects=["flow-engineering"])` runs
- THEN the returned list contains ONLY observations whose `project == "flow-engineering"`
- AND the length is `5` (no leakage from `mockup-2-blog`)

#### Scenario: `since="2026-06-01"` excludes observations created before that date

- GIVEN a backend with one observation created at `"2026-05-31 23:59:59"` and one at `"2026-06-01 00:00:00"`, both in `flow-engineering`
- WHEN `mem_search_federated("drift", projects=["flow-engineering"], since="2026-06-01")` runs
- THEN the `2026-05-31` observation is NOT in the result list
- AND the `2026-06-01` observation IS in the result list
- AND the SQL filter is `created_at >= '2026-06-01'` (lexicographic comparison; the trailing `00:00:00` is implicit for date-only input)

#### Scenario: `type_filter=["decision", "bugfix"]` includes only matching types

- GIVEN a backend with observations of types `decision`, `bugfix`, `pattern`, and `learning` in `flow-engineering`, all containing "drift"
- WHEN `mem_search_federated("drift", projects=["flow-engineering"], type_filter=["decision", "bugfix"])` runs
- THEN the result list contains ONLY observations whose `type` is `"decision"` or `"bugfix"` (exact match, case-sensitive)
- AND `pattern` and `learning` observations are excluded

#### Scenario: ABC default raises `NotImplementedError` when not overridden

- GIVEN a third-party subclass of `EngramBackend` that does NOT override `mem_search_federated`
- WHEN `instance.mem_search_federated("drift")` runs
- THEN `NotImplementedError` is raised at call time (not import time)
- AND the exception message identifies the ABC version (`v1.2`) so users find the right docs
- AND the import of `EngramBackend` itself succeeds (third-party code that never calls the new method is unaffected)

---

### REQ-24: `project_detector` with auto-tagging via `FLOW_AUTO_PROJECT_TAG=1`

The system SHALL provide `src/flow_engineering/project_detector.py` with three public functions: `detect(cwd: Path, *, registry: Registry | None = None) -> str | None`, `apply_tag(observation_id: int, project: str, *, backend: EngramBackend) -> dict`, and a registry loader that reads `~/.config/flow-engineering/registry.json` (a JSON map `{abs_path_prefix: project_key}`) when present and falls back to scanning `FLOW_PROJECTS_ROOT` (default `C:\dev\proyects`) lazily on first call when the registry file is missing.

The `detect` function SHALL return the deepest-matching project key when `cwd` (or any of its ancestors) is registered as a sub-project, and SHALL return `None` when no match is found. The lookup chain SHALL be: (a) explicit `project=` argument to the caller (handled outside the detector), (b) `FLOW_PROJECT_OVERRIDE` env var, (c) `detect(cwd)`. `detect` SHALL refuse to return any key for `cwd` paths that match no entry AND are not under `FLOW_PROJECTS_ROOT` — the caller decides fallback. The `apply_tag` helper SHALL mutate one observation's `project` field via `update_observation` (existing ABC seam from `decision-code-linking`) and SHALL refuse (return error dict) when `project` is empty or whitespace.

The CLI subcommand `flow projects backfill [--dry-run] [--confirm] [--project=<key>] [--since=<iso>]` SHALL iterate the alias map (`~/.config/flow-engineering/project-aliases.json`, see REQ-27) and re-tag matching observations. The default mode SHALL be `--dry-run` (preview only, no writes, JSON report to stdout). To write, the caller MUST pass `--confirm` explicitly; no interactive prompt is shown. `--project=<key>` SHALL restrict the operation to a single alias `<old>` key (without it the operation iterates the entire alias map). The output SHALL be a JSON array `[{observation_id, current_tag, proposed_tag, action}, …]` where `action` is one of `"rename"`, `"skip_already_tagged"`, or `"skip_no_match"`.

#### Scenario: `detect` returns project name when cwd is `~/dev/proyects/flow-engineering/`

- GIVEN the registry contains `"C:/dev/proyects/flow-engineering": "flow-engineering"`
- WHEN `detect(Path("C:/dev/proyects/flow-engineering/src"))` runs
- THEN the return value is the string `"flow-engineering"` (deepest-match: subdirectory resolves to the parent project key)

#### Scenario: `detect` returns `None` when cwd is `~/Downloads/` (not under projects dir)

- GIVEN the registry contains only sub-projects under `C:/dev/proyects/`
- WHEN `detect(Path("C:/Users/insyd/Downloads"))` runs
- THEN the return value is `None` (no match; the caller decides what to do, NOT a silent `"insyd"` fallback)

#### Scenario: `flow projects backfill` (no flags) defaults to dry-run

- GIVEN a backend with 1 observation tagged `project=flow-image-generator-v2`
- AND an alias config mapping `flow-image-generator-v2 -> flow-image-generator-main`
- WHEN `flow projects backfill` runs (no flags)
- THEN the process exits `0`
- AND stdout is a JSON array with one entry: `{"observation_id": <id>, "current_tag": "flow-image-generator-v2", "proposed_tag": "flow-image-generator-main", "action": "rename"}`
- AND the observation's `project` field in the database is UNCHANGED (still `flow-image-generator-v2`)

#### Scenario: `flow projects backfill --confirm --project=flow-image-generator-v2` writes

- GIVEN the same backend + alias config as the previous scenario
- WHEN `flow projects backfill --confirm --project=flow-image-generator-v2` runs
- THEN the process exits `0`
- AND the observation's `project` field is now `flow-image-generator-main`
- AND the counter `project_tag_backfilled_total{from="flow-image-generator-v2"}` increments by `1`

#### Scenario: `flow projects backfill --confirm` without `--project` on a multi-alias corpus scopes to all aliases

- GIVEN a backend with 1 observation tagged `flow-image-generator-v2` AND 1 tagged `another-old-key`
- AND alias config has both `flow-image-generator-v2 -> flow-image-generator-main` AND `another-old-key -> another-new-key`
- WHEN `flow projects backfill --confirm` runs (no `--project` flag)
- THEN BOTH observations are re-tagged in one invocation (the alias map is iterated in full)
- AND the JSON report has two entries
- AND each `project_tag_backfilled_total{from=<old>}` counter increments by `1`

#### Scenario: `flow projects backfill` without `--confirm` exits non-zero on a corpus needing changes (refuses silent write)

- GIVEN a backend with 1 observation tagged `flow-image-generator-v2`
- AND an alias config mapping it to `flow-image-generator-main`
- WHEN `flow projects backfill --project=flow-image-generator-v2` runs (note: NO `--confirm`)
- THEN the process exits non-zero
- AND stderr contains `"--confirm required to write changes; use --dry-run to preview"`
- AND the observation's `project` field is UNCHANGED

---

### REQ-25: `flow search --federated --projects=<csv> --since=<iso> --type=<csv>` CLI

The system SHALL add four opt-in flags to the existing `flow search` subcommand: `--federated` (boolean, default `False`), `--projects=<csv>` (comma-separated project keys, default = all), `--since=<iso>` (ISO 8601 date OR datetime, optional), `--type=<csv>` (comma-separated observation types, optional). When `--federated` is absent, `flow search` SHALL behave byte-identically to its pre-change behaviour (existing scripts unaffected — D9 non-breaking guarantee). When `--federated` is present, the CLI SHALL invoke `EngramBackend.mem_search_federated(...)` with the parsed parameters and render the returned rows with a `project` column prepended to the existing output. CSV parsing SHALL split on `,` only (no spaces, no quote escaping in v1). The `--since` parser SHALL reuse `_parse_since` from `cli.py:892` for CLI parity with `flow drift --since`.

#### Scenario: `flow search "drift"` (no `--federated` flag) returns identical results to pre-change behaviour

- GIVEN a backend with 3 observations in `flow-engineering` containing "drift"
- AND 2 observations in `mockup-2-blog` containing "drift"
- WHEN `flow search "drift"` runs (no federated flag)
- THEN the process exits `0`
- AND the result list contains ONLY `flow-engineering` observations (default behaviour: single-project, current cwd)
- AND the JSON / table output is byte-identical to the pre-change output (no `project` column added, no behaviour change)

#### Scenario: `flow search --federated "drift"` returns results from all projects

- GIVEN the same backend as the previous scenario
- WHEN `flow search --federated "drift"` runs (no `--projects` flag → all projects)
- THEN the result list contains all 5 observations (3 from `flow-engineering` + 2 from `mockup-2-blog`)
- AND each row in the table output has a populated `project` column

#### Scenario: `flow search --federated --projects=flow-engineering,mockup-2-blog "drift"` restricts to the named projects

- GIVEN a backend with observations in 9 projects, all containing "drift"
- WHEN `flow search --federated --projects=flow-engineering,mockup-2-blog "drift"` runs
- THEN the result list contains ONLY observations whose `project` is `flow-engineering` or `mockup-2-blog`
- AND no observation from `tecnodespegue-landing` (or any other of the 7 projects) appears in the output

#### Scenario: `flow search --federated --since=2026-06-01 "drift"` excludes observations created before that date

- GIVEN a backend with 1 observation created `"2026-05-31 23:59:59"` and 1 created `"2026-06-01 00:00:00"`, both in `flow-engineering` and both containing "drift"
- WHEN `flow search --federated --since=2026-06-01 "drift"` runs
- THEN the `2026-05-31` observation is NOT in the output
- AND the `2026-06-01` observation IS in the output

#### Scenario: `flow search --federated --type=decision "drift"` includes only `decision` type observations

- GIVEN a backend with `decision`, `bugfix`, `pattern`, and `learning` observations in `flow-engineering`, all containing "drift"
- WHEN `flow search --federated --type=decision "drift"` runs
- THEN the result list contains ONLY observations whose `type` is `"decision"` (exact match)
- AND `--type=decision,bugfix` includes BOTH types (CSV parsed correctly)

---

### REQ-26: Three observability counters for federated operations

The system SHALL emit the following JSONL counter events via `observability.increment()` and persist them in `~/.flow-engineering/metrics.jsonl` (overridable via `FLOW_METRICS_PATH`). Counter names SHALL match the REQ-8 / REQ-22 convention established in `decision-code-linking` and `vector-semantic-search`.

| Counter | Type | Trigger |
|---|---|---|
| `federated_search_invoked_total{trigger=cli\|programmatic}` | counter | increments by `1` per `mem_search_federated` invocation |
| `federated_search_projects_queried{count=N}` | histogram | one event per call with `count=<N>` where N = number of projects queried (1..9); `count=None` ⇒ `count=0` (search-all case) |
| `federated_search_results_returned_total` | counter | increments by `len(returned_rows)` per invocation |

A `record_federated_summary(*, invoked=1, projects_queried, results_returned)` helper SHALL aggregate federated metrics in one call (parallels `record_vector_summary` from REQ-22). `HybridBackend.mem_search_federated` SHALL call `record_federated_summary` on every invocation. All three counters SHALL be observable in the `flow metrics` summary output. `FEDERATED_COUNTER_NAMES` SHALL be the canonical catalog list (parallels `VECTOR_COUNTER_NAMES`).

#### Scenario: `federated_search_invoked_total` increments per federated call

- GIVEN the metrics file has `federated_search_invoked_total = N` (read via `observability.snapshot()`)
- WHEN `mem_search_federated("drift")` runs once programmatically
- THEN `federated_search_invoked_total` reads `N + 1` from the metrics file
- AND the JSONL event includes `{"trigger": "programmatic"}` label

#### Scenario: `federated_search_projects_queried` shows the count distribution (histogram of project-bucket sizes)

- GIVEN a metrics file with two prior events: `federated_search_projects_queried{count=1}` and `federated_search_projects_queried{count=3}`
- WHEN `mem_search_federated("drift", projects=["p1","p2","p3","p4"])` runs (4-project query)
- THEN a new event `federated_search_projects_queried{count=4}` appears in the metrics file
- AND `flow metrics` renders the histogram with buckets `{count=1: 1, count=3: 1, count=4: 1}` (each `count=` value is a separate bucket; NO `_total` suffix because the value IS the count)

#### Scenario: `federated_search_results_returned_total` increments by sum of result counts

- GIVEN the metrics file has `federated_search_results_returned_total = M`
- WHEN `mem_search_federated("drift", projects=["p1","p2"])` runs and returns 7 rows
- THEN `federated_search_results_returned_total` reads `M + 7` from the metrics file
- AND a second call returning 3 rows increments the counter by another `3` (cumulative)

#### Scenario: All 3 counters appear in `flow metrics` output

- GIVEN a metrics file containing at least one event for each of the 3 federated counters
- WHEN `flow metrics` runs
- THEN the summary output includes `federated_search_invoked_total`, `federated_search_projects_queried`, and `federated_search_results_returned_total` as named rows
- AND `FEDERATED_COUNTER_NAMES` is the canonical list (assertable via `observability.list_counter_names()`)
- AND no counter is silently renamed across the `vector-semantic-search` → `cross-project-federation` boundary (the contract forbids drift without a CHANGELOG entry)

---

### REQ-27: `project-aliases.json` config for rename absorption

The system SHALL read `~/.config/flow-engineering/project-aliases.json` on startup, cache it in memory, and apply it to every `project` read BEFORE the federated SQL runs (forward alias resolution: `flow-image-generator-v2` → `flow-image-generator-main`). The file SHALL conform to the schema:

```json
{
  "version": 1,
  "aliases": [
    {"old": "flow-image-generator-v2", "new": "flow-image-generator-main", "created_at": "2026-06-26T19:46:07Z"}
  ]
}
```

The `version` field is mandatory and SHALL be the integer `1` (future schema bumps increment it). Each alias record SHALL have exactly three keys: `old` (the deprecated project key), `new` (the canonical replacement), `created_at` (ISO 8601 datetime). Missing file SHALL start with an empty list and SHALL increment the `alias_config_load_failed_total{reason="missing"}` counter. Malformed JSON SHALL fail fast on startup with a clear error message naming the file path AND increment `alias_config_load_failed_total{reason="malformed"}`.

The CLI subcommand `flow projects alias <old> <new>` SHALL append a new record to the `aliases` array (idempotent: re-invoking with the same `<old>` → `<existing_new>` is a no-op + prints confirmation; re-invoking with `<old>` → `<different_new>` SHALL ERROR to prevent silent history loss — the existing record is preserved unchanged). Writes SHALL be atomic (`tempfile + Path.replace`) so a crash mid-write cannot corrupt the file. Alias resolution SHALL NOT auto-backfill (the user runs `flow projects backfill` separately per REQ-24); aliasing is read-time only.

#### Scenario: Query for `flow-image-generator-v2` returns `flow-image-generator-main` rows when alias exists

- GIVEN a backend with 1 observation tagged `project=flow-image-generator-v2` containing "drift"
- AND `project-aliases.json` maps `flow-image-generator-v2 → flow-image-generator-main`
- WHEN `mem_search_federated("drift", projects=["flow-image-generator-v2"])` runs
- THEN the alias resolver rewrites `projects` to `["flow-image-generator-main"]` BEFORE SQL
- AND the observation IS returned (alias resolution is transparent; the user-facing contract treats the alias as a synonym)
- AND the `project` field in the result row is `"flow-image-generator-main"` (the canonical name, NOT the alias)

#### Scenario: `flow projects alias flow-image-generator-v2 flow-image-generator-main` writes the file

- GIVEN `project-aliases.json` does NOT exist (or exists with empty `aliases` array)
- WHEN `flow projects alias flow-image-generator-v2 flow-image-generator-main` runs
- THEN the process exits `0`
- AND `project-aliases.json` now contains `{"version": 1, "aliases": [{"old": "flow-image-generator-v2", "new": "flow-image-generator-main", "created_at": "<iso-now>"}]}`
- AND stdout contains `"alias added: flow-image-generator-v2 -> flow-image-generator-main"`

#### Scenario: `flow projects alias <old> <new>` with an existing alias for `<old>` to a `<different_new>` ERRORS (no silent history loss)

- GIVEN `project-aliases.json` already maps `flow-image-generator-v2 → flow-image-generator-main` (created yesterday)
- WHEN `flow projects alias flow-image-generator-v2 some-other-name` runs
- THEN the process exits non-zero
- AND stderr contains `"alias for flow-image-generator-v2 already maps to flow-image-generator-main; refusing to overwrite"`
- AND the existing record (with yesterday's `created_at`) is UNCHANGED (no silent history loss; if the user wants to re-alias, they edit the JSON manually or remove the old record first)

#### Scenario: Re-invoking with the same `<old> <new>` is a no-op + prints confirmation (idempotent)

- GIVEN `project-aliases.json` already maps `flow-image-generator-v2 → flow-image-generator-main`
- WHEN `flow projects alias flow-image-generator-v2 flow-image-generator-main` runs (identical args)
- THEN the process exits `0`
- AND the `aliases` array is UNCHANGED (still has exactly 1 record for that pair; no duplicate row added)
- AND stdout contains `"alias already present: flow-image-generator-v2 -> flow-image-generator-main"` (informational; not an error)

#### Scenario: Alias file with malformed JSON fails fast on startup with clear error

- GIVEN `project-aliases.json` exists but contains invalid JSON (e.g., trailing comma, unclosed brace)
- WHEN the flow CLI starts up (any subcommand that triggers alias load)
- THEN the process exits non-zero
- AND stderr contains `"failed to parse project-aliases.json at <path>: <json-error>"` (path + parser error both visible)
- AND `alias_config_load_failed_total{reason="malformed"}` increments by `1`
- AND the rest of the system continues with an empty alias map (no partial state, no propagation of the malformed file to downstream callers)

---

## Out of Scope (deferred)

The following are explicitly out of scope for this change and belong to named follow-ups:

- **HTTP-based federation (option B from explore)** — not needed, the shared SQLite at `~/.engram/engram.db` is single-host. A future change that needs HTTP federation would publish a read-only Engram API.
- **MCP server federation (option F)** — not needed; `flow search --federated` is the consumer surface. An MCP server can call it programmatically.
- **Vector-search-augmented federation** — semantic search across projects is a v2 follow-up that depends on `vector-semantic-search` (REQ-17..22) being battle-tested in production. For now, federation is prose-only.
- **Cross-DB federation** — physically impossible: there IS only one SQLite (`~/.engram/engram.db`), 3.4 MB, WAL, FTS5-indexed by `project`. Per-project DBs are not on the roadmap.
- **Automatic tag inference from observation content (NLP-based project guess)** — v2 follow-up. The opt-in `FLOW_AUTO_PROJECT_TAG=1` mechanism is the v1 surface; content-based inference would require semantic models and is deferred.
- **Async / streaming federated queries** — v1 is sync; pagination via `limit` is the only knob. A 9-project × 10k-obs BM25 query completes in <100ms; streaming is not needed at this scale.
- **Hosted embedding fallback in the federated path** — federation is prose-only in v1; embedding-rerank during a federated query is the vector-semantic-search v2 boundary.
- **Federation across physical SQLite files (per-project DBs)** — explicitly rejected by explore option analysis; shared DB is the chosen topology.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req23_federated_search.feature` | NEW | REQ-23 | 5 |
| `tests/bdd/req24_project_detector.feature` | NEW | REQ-24 | 6 |
| `tests/bdd/req25_cli_federated.feature` | NEW | REQ-25 | 5 |
| `tests/bdd/req26_federated_observability.feature` | NEW | REQ-26 | 4 |
| `tests/bdd/req27_project_aliases.feature` | NEW | REQ-27 | 5 |
| **Total BDD scenarios** | | | **25** |

Step definitions land in `tests/bdd/test_cross_project_federation_steps.py` (NEW; pytest-bdd glue per file). The REQ-24 plan grew from 5 to 6 scenarios during spec writing: the "backfill without `--confirm` refuses" edge case is non-trivial and warrants its own scenario to make the safety gate explicit (mirrors how `vector-semantic-search` REQ-21 grew to 5 scenarios for the crash-resume + dry-run + idempotent cases). All 25 scenarios are independently testable; no padding.

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `update_observation` seam is reused by `apply_tag` and the backfill path | Compatible (consumes the seam); no change to `decision-code-linking` files |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses `decision_id`, not `project`; federated query is orthogonal to drift detection | No conflict |
| `vector-semantic-search` (shipped v0.4.0) | Vector index is per-project `vectors.sqlite`; federation routes PROSE, not vectors. REQ-17/18/22 contract unchanged | Compatible (boundary respected); future v2 may federate vectors |
| `graph-snapshots` (#5) | Graph nodes are change-scoped, not project-scoped | No conflict |
| `prompt-registry` (#7) | Unrelated layer | No conflict |
| Third-party `EngramBackend` subclasses | v1.2 ABC adds `mem_search_federated` as `NotImplementedError` default (mirrors `update_observation` precedent at `engram_io.py:147`) | NON-BREAKING; old subclasses import unchanged; only callers that invoke the new method get a call-time error |

---

## References

- Explore: Engram `sdd/cross-project-federation/explore` (#156) — option matrix A-G, premise correction (shared DB not per-project silos)
- Proposal: Engram `sdd/cross-project-federation/proposal` (#158) — Sketch A additive federated query, 8 open questions for design
- Design: Engram `sdd/cross-project-federation/design` (#159) — D1-D11 resolved (signature, fallback, gate, counter shape, ABC version, type filter, since semantics, alias schema, non-breaking, test strategy, migration)
- Predecessor spec: `openspec/changes/archive/2026-06-26-vector-semantic-search/spec.md` (REQ-17 additive ABC pattern, REQ-22 counter contract, BDD Feature File Plan table format)
- Predecessor design: `openspec/changes/archive/2026-06-26-vector-semantic-search/design.md` (D1-D11 reference format for design/spec alignment)
- SQLite schema verified via `sqlite3 ~/.engram/engram.db ".schema observations"` — `created_at TEXT` (`YYYY-MM-DD HH:MM:SS`), `idx_obs_project`, `idx_obs_type`, `idx_obs_created`, `observations_fts` virtual table all present
- Engram DB state (2026-06-26): 9 projects, 158 observations — `insyd:100, es:27, mockup-2-blog:16, gentle-ai:7, reels:4, flow-engineering:3, ecommerce-picomar:1, flow-image-generator-v2:1, revisa-porque-obsidian-no-me-marca:1`
