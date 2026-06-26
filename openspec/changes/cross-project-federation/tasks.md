<!-- tasks.md: cross-project-federation. Source: manual. -->
# Tasks: cross-project-federation

**Change:** `cross-project-federation`
**Builds on:** `proposal.md` (#158) — Sketch A additive `mem_search_federated`; `design.md` (#159) — D1-D11 resolved; `spec.md` (#161) — 5 REQs (REQ-23..27), 25 BDD scenarios
**Date:** 2026-06-26
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (single PR, batched)
**Strict TDD:** ON (per `vector-semantic-search` precedent; RED → GREEN → REFACTOR cycle per task)
**Delivery strategy:** single-pr (per prompt; `400-line budget risk: low`)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 13 (T1.1..T1.13) |
| Forecast LOC production | ~370 |
| Forecast LOC test (unit + BDD) | ~835 |
| Forecast LOC grand total | ~1205 |
| Forecast LOC realistic (×6 TDD multiplier per Engram #113) | **~7200** |
| BDD feature files | 5 (all NEW) |
| BDD scenarios | 25 |
| New source files | 2 (`project_detector.py`, `project_aliases.py`) |
| Modified source files | 3 (`engram_io.py`, `cli.py`, `observability.py`) |
| New test files | 6 unit + 1 BDD step glue (`test_cross_project_federation_steps.py`) |
| Chained PRs recommended | No (single PR per proposal #158) |
| Chain strategy | N/A (single PR) |
| 400-line budget risk | **Low** (single PR ~1205 LOC, split into 3 apply batches ≤530 LOC each) |
| Decision needed before apply | No (single-pr with `400-line budget risk: low` per design.md) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A (single PR)
400-line budget risk: Low

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC | design.md D-file breakdown (sum of `engram_io.py` +35 + `cli.py` +120 + `observability.py` +25 + `project_detector.py` ~80 + `project_aliases.py` ~110) | ~370 |
| Realistic ×6 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): decision-code-linking PR#1 forecast ~390 LOC, actual 2179 LOC net | ×6 → ~2220 production realistic + ~5000 test realistic (×30 LOC/BDD scenario × 25 scenarios) |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (#112): ≤6 tasks OR ≤150 LOC prod per delegation, default runtime ~15 min | batch B at ~530 LOC is the **TIMEOUT RISK BATCH** |
| Risk: batch B | ~530 LOC across 5 tasks (project_detector + 2 BDD features + CLI federated flags + backfill CLI) at ~6 LOC/min = ~1.5h | **TIMEOUT RISK** — split into B1 (impl) + B2 (BDD + backfill CLI) if delegation hits 15-min ceiling |

### Suggested Work Units

Single PR (no chained PR split per proposal #158). The work fits in one ~1205-LOC PR (~7200 LOC realistic under Strict TDD). Per-delegation batching (≤6 tasks / ≤150 LOC) is still required at the apply phase because the delegate runtime is ~15 min.

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|-----------------|----------|-----|
| **A** | T1.1 + T1.2 + T1.4 | ~75 | ~320 | ABC v1.2 + InMemoryBackend federated impl + BDD req23 — atomic foundation; T1.4 tests backfill T1.1+T1.2 |
| **B** | T1.3 + T1.5 + T1.6 + T1.7 + T1.12 | ~220 | ~410 | project_detector + 2 BDD features + CLI federated flags + backfill CLI — combined CLI+library work; **TIMEOUT RISK BATCH** |
| **C** | T1.8 + T1.9 + T1.10 + T1.11 + T1.13 | ~170 | ~400 | Observability counters + aliases + 2 BDD features + docs — cohesive close-out |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 8 items are explicitly deferred per spec.md — apply must NOT introduce code for them:

- **HTTP-based federation (option B from explore)** — shared SQLite makes it unneeded
- **MCP server federation (option F)** — `flow search --federated` is the consumer
- **Vector-search-augmented federation** — v2 after `vector-semantic-search` battle-test
- **Cross-DB federation** — physically impossible (one DB only)
- **Auto tag inference from content (NLP)** — v2 follow-up; opt-in cwd-detect is v1
- **Async / streaming federated queries** — v1 sync at 9-project scale is fine
- **Hosted embedding fallback in federated path** — v1 prose-only
- **Per-project physical SQLite isolation** — rejected by explore analysis

---

## Task list (13 tasks, single PR)

### T1.1 — Add `mem_search_federated` to `EngramBackend` ABC (v1.2, NON-BREAKING default)

- **Type:** code
- **TDD phase:** N/A (ABC extension; backward compat covered by T1.2 + T1.4 RED tests)
- **LOC:** ~15 impl + ~10 tests = ~25
- **Files:**
  - `src/flow_engineering/engram_io.py` (modify — add `mem_search_federated` default method to `EngramBackend`; bump docstring "ABC v1.1" → "ABC v1.2")
- **Dependencies:** none
- **Acceptance criteria:**
  - [x] `EngramBackend.mem_search_federated(self, query: str, projects: list[str] | None = None, *, limit: int = 10, since: str | None = None, type_filter: list[str] | None = None, scope: str = "project") -> list[dict[str, Any]]` defined with default body `raise NotImplementedError("federated search requires explicit backend impl — EngramBackend v1.2")`
  - [x] `EngramBackend` class docstring bumped to "ABC v1.2 — added `mem_search_federated` as default `NotImplementedError` (NON-BREAKING; mirrors `mem_search_semantic` v1.1 + `update_observation` precedent at `engram_io.py:147`)"
  - [x] Existing 576+ tests still pass (`uv run pytest`)
  - [x] Third-party subclass fixtures import unchanged
- **Commit:** `feat(backend): add mem_search_federated to EngramBackend ABC v1.2 (NON-BREAKING default)` — DONE (8d158d1)

### T1.2 — Implement `mem_search_federated` in `InMemoryBackend` (REQ-23 library)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~30 impl + ~180 tests = ~210
- **Files:**
  - `src/flow_engineering/engram_io.py` (modify — override `mem_search_federated` in `InMemoryBackend` to filter in-memory dict by `projects` / `since` / `type_filter`)
  - `tests/unit/test_engram_io_federated.py` (NEW — 5 RED fixtures + GREEN coverage for REQ-23 scenarios 1-5)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [x] RED: `test_inmemory_federated_three_projects_returns_each` fails (no impl yet); `test_inmemory_federated_projects_filter_restricts_to_named` fails; `test_inmemory_federated_since_filter_excludes_older` fails; `test_inmemory_federated_type_filter_restricts_to_listed` fails; `test_inmemory_federated_empty_projects_returns_empty` fails
  - [x] GREEN: `InMemoryBackend.mem_search_federated("drift", projects=["mockup-2-blog", "flow-engineering", "tecnodespegue-landing"], limit=10)` returns 1 row per project with `project` field preserved per row
  - [x] GREEN: `mem_search_federated("drift", projects=["flow-engineering"])` returns ONLY rows where `project == "flow-engineering"` (no leakage)
  - [x] GREEN: `mem_search_federated("drift", projects=["flow-engineering"], since="2026-06-01")` excludes obs with `created_at < "2026-06-01"`; lexicographic `>=` on `YYYY-MM-DD HH:MM:SS` TEXT works
  - [x] GREEN: `mem_search_federated("drift", projects=["flow-engineering"], type_filter=["decision", "bugfix"])` returns ONLY matching types (exact match, case-sensitive); `pattern` + `learning` excluded
  - [x] GREEN: `mem_search_federated("drift", projects=[])` raises `ValueError("projects must be None or non-empty list")` (fail-fast per design D1; equivalent to short-circuit for fail-fast contract)
  - [x] GREEN: Each returned dict includes `project` field non-null and equal to one of the queried projects
- **Commit:** `feat(backend): InMemoryBackend.mem_search_federated with projects/since/type_filter filters (REQ-23)` — DONE (5cbcd26 RED + 6b2818d GREEN)

### T1.3 — Scaffold `project_detector.py` with `detect()` + `apply_tag()` + registry loader (REQ-24)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~80 impl + ~140 tests = ~220
- **Files:**
  - `src/flow_engineering/project_detector.py` (NEW — `Registry` dataclass, `load_registry()`, `detect(cwd, *, registry=None) -> str | None`, `apply_tag(observation_id, project, *, backend) -> dict`)
  - `tests/unit/test_project_detector.py` (NEW — RED fixtures: cwd matches sub-project, cwd is registry root, cwd is unknown (`None`), env override, registry missing, registry malformed)
- **Dependencies:** none (independent of T1.1/T1.2; pure file)
- **Acceptance criteria:**
  - [ ] RED: `test_detect_subdirectory_resolves_to_parent_project` fails; `test_detect_unknown_cwd_returns_none` fails; `test_detect_env_override_wins_over_registry` fails; `test_apply_tag_empty_project_refuses` fails; `test_registry_missing_file_returns_empty` fails; `test_registry_malformed_json_raises` fails
  - [ ] GREEN: `detect(Path("C:/dev/proyects/flow-engineering/src"))` returns `"flow-engineering"` when registry contains `"C:/dev/proyects/flow-engineering": "flow-engineering"` (deepest-match)
  - [ ] GREEN: `detect(Path("C:/Users/insyd/Downloads"))` returns `None` when registry contains only sub-projects under `C:/dev/proyects/` (NOT `"insyd"` fallback; caller decides)
  - [ ] GREEN: `FLOW_PROJECT_OVERRIDE=mockup-2-blog` env var wins over registry lookup (escape hatch)
  - [ ] GREEN: `apply_tag(obs_id, "")` returns error dict `{"error": "project cannot be empty"}`; refuses to mutate
  - [ ] GREEN: `apply_tag(obs_id, "mockup-2-blog")` calls `backend.update_observation(obs_id, project="mockup-2-blog")` and returns the updated obs dict
  - [ ] GREEN: Missing `registry.json` → empty registry; malformed JSON → `RegistryParseError` with file path in message
  - [ ] GREEN: Lazy scan of `FLOW_PROJECTS_ROOT` (default `C:/dev/proyects`) on first `load_registry()` call when file missing; persist to `~/.config/flow-engineering/registry.json`; subsequent loads read from disk
- **Commit:** `feat(backend): project_detector with cwd-based detection + registry auto-build + apply_tag`

### T1.4 — BDD feature `req23_federated_search.feature` (5 scenarios)

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~30 feature + ~150 step defs = ~180
- **Files:**
  - `tests/bdd/req23_federated_search.feature` (NEW — 5 scenarios from REQ-23)
  - `tests/bdd/test_cross_project_federation_steps.py` (NEW — pytest-bdd step glue shared across all 5 features)
- **Dependencies:** T1.1, T1.2
- **Acceptance criteria:**
  - [x] Feature file contains 5 scenarios matching spec REQ-23:
    1. Federated search across 3 projects returns results from each with `project` field per row
    2. `projects=["flow-engineering"]` restricts the result set to a single project (no leakage)
    3. `since="2026-06-01"` excludes observations created before that date (lexicographic comparison)
    4. `type_filter=["decision", "bugfix"]` includes only matching types (exact match)
    5. ABC default raises `NotImplementedError` when not overridden (third-party subclass scenario)
  - [x] Step defs use `InMemoryBackend` for filtering scenarios; a custom subclass for the ABC-default-raises scenario
  - [ ] Secrets-invariant scenario: observation text containing `secrets.yaml` returns row WITHOUT any file re-read (asserted via `monkeypatch.setattr(os, "stat", ...)`) — DEFERRED to batch C (T1.13 docs follow-up) or as separate hardening change; not in the original 5 REQ-23 scenarios per spec #161
  - [x] `uv run pytest tests/bdd/req23_federated_search.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req23_federated_search feature with 5 scenarios + step glue` — DONE (6076aba)

### T1.5 — BDD feature `req24_project_detector.feature` (6 scenarios)

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~40 feature + ~150 step defs = ~190
- **Files:**
  - `tests/bdd/req24_project_detector.feature` (NEW — 6 scenarios from REQ-24)
  - `tests/bdd/test_cross_project_federation_steps.py` (extend — step glue for REQ-24)
- **Dependencies:** T1.3
- **Acceptance criteria:**
  - [ ] Feature file contains 6 scenarios matching spec REQ-24:
    1. `detect()` returns project name when cwd is `~/dev/proyects/flow-engineering/`
    2. `detect()` returns `None` when cwd is `~/Downloads/` (no silent `"insyd"` fallback)
    3. `flow projects backfill` (no flags) defaults to dry-run
    4. `flow projects backfill --confirm --project=flow-image-generator-v2` writes
    5. `flow projects backfill --confirm` without `--project` on multi-alias corpus scopes to all aliases
    6. `flow projects backfill` without `--confirm` exits non-zero on corpus needing changes (refuses silent write)
  - [ ] Step defs use `tmp_path` for registry + alias config fixtures; `CliRunner` for CLI invocations
  - [ ] Opt-in gate scenario: `FLOW_AUTO_PROJECT_TAG` unset → no auto-tag happens (REQ-24 implicit in scenario 1; explicit assertion)
  - [ ] `uv run pytest tests/bdd/req24_project_detector.feature -v` passes all 6 scenarios
- **Commit:** `test(bdd): req24_project_detector feature with 6 scenarios + step glue`

### T1.6 — Add `--federated --projects --since --type` flags to `flow search` CLI (REQ-25)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~50 impl + ~120 tests = ~170
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `search` command at `cli.py:496` with 4 new opt-in flags)
  - `tests/unit/test_cli_federated.py` (NEW)
- **Dependencies:** T1.1, T1.2
- **Acceptance criteria:**
  - [ ] RED: `test_cli_search_federated_default_off_byte_identical` fails (no flag yet); `test_cli_search_federated_returns_all_projects` fails; `test_cli_search_federated_projects_csv_restricts` fails; `test_cli_search_federated_since_filter_excludes_older` fails; `test_cli_search_federated_type_csv_restricts_to_listed` fails
  - [ ] GREEN: `flow search "drift"` (no `--federated`) is **byte-identical** to pre-change output (D9 non-breaking guarantee; verified by snapshot test against v0.4.0 golden)
  - [ ] GREEN: `flow search --federated "drift"` invokes `backend.mem_search_federated(...)` with `projects=None` → all projects
  - [ ] GREEN: `flow search --federated --projects=flow-engineering,mockup-2-blog "drift"` parses CSV → `projects=["flow-engineering","mockup-2-blog"]` (split on `,`; no spaces; no quote escaping)
  - [ ] GREEN: `flow search --federated --since=2026-06-01 "drift"` parses via `_parse_since` at `cli.py:892` → passes ISO string through to SQL
  - [ ] GREEN: `flow search --federated --type=decision,bugfix "drift"` parses CSV → `type_filter=["decision","bugfix"]`
  - [ ] GREEN: Output table includes `project` column prepended when `--federated` is present; absent when flag is missing
  - [ ] GREEN: JSON output (`--json`) includes `project` key per row when `--federated` is present
- **Commit:** `feat(cli): --federated --projects --since --type flags on flow search (REQ-25)`

### T1.7 — BDD feature `req25_cli_federated.feature` (5 scenarios)

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~30 feature + ~120 step defs = ~150
- **Files:**
  - `tests/bdd/req25_cli_federated.feature` (NEW — 5 scenarios from REQ-25)
  - `tests/bdd/test_cross_project_federation_steps.py` (extend — step glue for REQ-25)
- **Dependencies:** T1.6
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-25:
    1. `flow search "drift"` (no `--federated`) returns identical results to pre-change behaviour
    2. `flow search --federated "drift"` returns results from all projects (project column populated)
    3. `flow search --federated --projects=flow-engineering,mockup-2-blog "drift"` restricts to named projects
    4. `flow search --federated --since=2026-06-01 "drift"` excludes observations created before that date
    5. `flow search --federated --type=decision "drift"` includes only `decision` type observations (CSV: `--type=decision,bugfix` includes both)
  - [ ] Step defs use `CliRunner` + seeded `InMemoryBackend` (no real SQLite)
  - [ ] `uv run pytest tests/bdd/req25_cli_federated.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req25_cli_federated feature with 5 scenarios + step glue`

### T1.8 — Add 3 federated observability counters + `record_federated_summary` (REQ-26)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~40 impl + ~100 tests = ~140
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add `FEDERATED_COUNTER_NAMES` catalog + `record_federated_summary(*, invoked=1, projects_queried, results_returned)` helper mirroring `record_vector_summary` at `observability.py:295`)
  - `tests/unit/test_observability_federated.py` (NEW)
- **Dependencies:** none (library-only; consumed by T1.2 InMemoryBackend override + T1.6 CLI flags)
- **Acceptance criteria:**
  - [ ] RED: `test_record_federated_summary_emits_3_events` fails (helper missing); `test_federated_counter_names_catalog_has_3` fails; `test_federated_search_invoked_total_increments` fails
  - [ ] GREEN: `FEDERATED_COUNTER_NAMES: list[str] = ["federated_search_invoked_total", "federated_search_projects_queried", "federated_search_results_returned_total"]` (3 names, parallels `VECTOR_COUNTER_NAMES` at `observability.py:63`)
  - [ ] GREEN: `record_federated_summary(*, invoked=1, projects_queried=3, results_returned=7)` emits 3 JSONL events: `{"counter": "federated_search_invoked_total", "count": 1}`, `{"counter": "federated_search_projects_queried", "count": 3}`, `{"counter": "federated_search_results_returned_total", "count": 7}`
  - [ ] GREEN: `projects_queried=None` (search-all case) emits `count=0` for the histogram bucket
  - [ ] GREEN: `federated_search_projects_queried` has NO `_total` suffix because the value IS the count (mirrors D4 decision)
  - [ ] GREEN: `flow metrics` summary output includes all 3 federated counter rows (assertable via test snapshot)
- **Commit:** `feat(observability): 3 federated_* counters + record_federated_summary helper (REQ-26)`

### T1.9 — BDD feature `req26_federated_observability.feature` (4 scenarios)

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~25 feature + ~80 step defs = ~105
- **Files:**
  - `tests/bdd/req26_federated_observability.feature` (NEW — 4 scenarios from REQ-26)
  - `tests/bdd/test_cross_project_federation_steps.py` (extend — step glue for REQ-26)
- **Dependencies:** T1.8
- **Acceptance criteria:**
  - [ ] Feature file contains 4 scenarios matching spec REQ-26:
    1. `federated_search_invoked_total` increments per federated call
    2. `federated_search_projects_queried` shows the count distribution (histogram of project-bucket sizes)
    3. `federated_search_results_returned_total` increments by sum of result counts
    4. All 3 counters appear in `flow metrics` output (`FEDERATED_COUNTER_NAMES` is the canonical catalog)
  - [ ] Step defs read `~/.flow-engineering/metrics.jsonl` via `observability.snapshot()` and assert counter deltas
  - [ ] `uv run pytest tests/bdd/req26_federated_observability.feature -v` passes all 4 scenarios
- **Commit:** `test(bdd): req26_federated_observability feature with 4 scenarios + step glue`

### T1.10 — Implement `project-aliases.json` + `flow projects alias <old> <new>` (REQ-27)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~110 impl + ~150 tests = ~260
- **Files:**
  - `src/flow_engineering/project_aliases.py` (NEW — `AliasRecord` dataclass, `resolve(name, *, aliases=None) -> str`, `load_aliases(path=None) -> list[AliasRecord]`, `save_aliases(aliases, path=None) -> None`, `add_alias(old, new, *, path=None) -> dict` — atomic write via `tempfile + Path.replace`)
  - `src/flow_engineering/cli.py` (modify — add `flow projects` group + `flow projects alias <old> <new>` subcommand)
  - `tests/unit/test_project_aliases.py` (NEW)
  - `tests/unit/test_cli_projects_alias.py` (NEW)
- **Dependencies:** none (pure library + small CLI subcommand)
- **Acceptance criteria:**
  - [ ] RED: `test_resolve_identity_for_non_aliased` fails; `test_resolve_rewrites_aliased_name` fails; `test_load_aliases_missing_file_returns_empty` fails; `test_load_aliases_malformed_json_raises_with_path` fails; `test_save_aliases_atomic_write_via_tempfile` fails; `test_add_alias_idempotent_same_target_noop` fails; `test_add_alias_conflicting_target_errors` fails
  - [ ] GREEN: `resolve("flow-image-generator-v2", aliases=[{"old": "flow-image-generator-v2", "new": "flow-image-generator-main", "created_at": "..."}])` returns `"flow-image-generator-main"` (forward-only)
  - [ ] GREEN: `resolve("flow-engineering", aliases=[...])` returns `"flow-engineering"` (identity for non-aliased)
  - [ ] GREEN: `load_aliases(path=tmp_path/"aliases.json")` returns `[]` when file missing + increments `alias_config_load_failed_total{reason="missing"}` counter
  - [ ] GREEN: `load_aliases(path=tmp_path/"bad.json")` raises `AliasConfigParseError` with message containing `"failed to parse project-aliases.json at <path>: <json-error>"` + increments `alias_config_load_failed_total{reason="malformed"}` counter
  - [ ] GREEN: `save_aliases([...], path=...)` writes via `tempfile.NamedTemporaryFile + Path.replace` (atomic); original file unchanged on mid-write crash (verified via `monkeypatch.setattr(Path, "replace", lambda self: raise OSError)`)
  - [ ] GREEN: `flow projects alias flow-image-generator-v2 flow-image-generator-main` writes file (REQ-27 scenario 2); stdout contains `"alias added: flow-image-generator-v2 -> flow-image-generator-main"`
  - [ ] GREEN: Re-invoking `flow projects alias <old> <same_new>` is no-op (REQ-27 scenario 4); stdout contains `"alias already present: <old> -> <same_new>"`
  - [ ] GREEN: `flow projects alias <old> <different_new>` when alias exists exits non-zero (REQ-27 scenario 3); stderr contains `"alias for <old> already maps to <existing_new>; refusing to overwrite"`; existing record UNCHANGED
- **Commit:** `feat(backend): project-aliases.json + flow projects alias subcommand with idempotency + atomic write (REQ-27)`

### T1.11 — BDD feature `req27_project_aliases.feature` (5 scenarios)

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~30 feature + ~100 step defs = ~130
- **Files:**
  - `tests/bdd/req27_project_aliases.feature` (NEW — 5 scenarios from REQ-27)
  - `tests/bdd/test_cross_project_federation_steps.py` (extend — step glue for REQ-27)
- **Dependencies:** T1.10
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-27:
    1. Query for `flow-image-generator-v2` returns `flow-image-generator-main` rows when alias exists
    2. `flow projects alias flow-image-generator-v2 flow-image-generator-main` writes the file
    3. `flow projects alias <old> <new>` with an existing alias for `<old>` to a `<different_new>` ERRORS (no silent history loss)
    4. Re-invoking with the same `<old> <new>` is a no-op + prints confirmation (idempotent)
    5. Alias file with malformed JSON fails fast on startup with clear error
  - [ ] Step defs use `tmp_path` for alias config; `CliRunner` for CLI invocations
  - [ ] Scenario 1 must trace through `project_aliases.resolve()` → `mem_search_federated` SQL → returned row's `project` field equals `"flow-image-generator-main"` (canonical name, NOT the alias)
  - [ ] `uv run pytest tests/bdd/req27_project_aliases.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req27_project_aliases feature with 5 scenarios + step glue`

### T1.12 — Implement `flow projects backfill [--dry-run] [--confirm] [--project] [--since]` (REQ-24 CLI surface)

- **Type:** test + code
- **TDD phase:** RED → GREEN
- **LOC:** ~50 impl + ~100 tests = ~150
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `flow projects backfill` subcommand extending the `flow projects` group from T1.10)
  - `tests/unit/test_cli_projects_backfill.py` (NEW)
- **Dependencies:** T1.10 (alias resolver + file IO must exist for backfill to read aliases)
- **Acceptance criteria:**
  - [ ] RED: `test_backfill_no_flags_defaults_to_dry_run` fails; `test_backfill_dry_run_writes_nothing` fails; `test_backfill_confirm_writes_to_alias_new` fails; `test_backfill_project_flag_scopes_to_single_alias` fails; `test_backfill_missing_confirm_refuses_on_pending_changes` fails
  - [ ] GREEN: `flow projects backfill` (no flags) exits `0` + emits JSON array `[{observation_id, current_tag, proposed_tag, action}]` to stdout (REQ-24 scenario 3); NO writes to backend
  - [ ] GREEN: `flow projects backfill --confirm --project=flow-image-generator-v2` iterates alias map scoped to that `<old>` + writes via `backend.update_observation(obs_id, project=alias.new)` (REQ-24 scenario 4); counter `project_tag_backfilled_total{from="flow-image-generator-v2"}` increments by `1`
  - [ ] GREEN: `flow projects backfill --confirm` (no `--project`) iterates the entire alias map + writes all matches (REQ-24 scenario 5); each `project_tag_backfilled_total{from=<old>}` increments by `1`
  - [ ] GREEN: `flow projects backfill --project=flow-image-generator-v2` (no `--confirm`) on a corpus needing changes exits non-zero (REQ-24 scenario 6); stderr contains `"--confirm required to write changes; use --dry-run to preview"`; NO writes
  - [ ] GREEN: `flow projects backfill --dry-run --confirm` is equivalent to `flow projects backfill --dry-run` (explicit dry-run wins over confirm)
  - [ ] GREEN: `--since=<iso>` filters which observations are eligible for re-tag (lexicographic `created_at >=` comparison like REQ-25)
  - [ ] GREEN: JSON output shape matches design D3: `[{"observation_id": int, "current_tag": str, "proposed_tag": str, "action": "rename"|"skip_already_tagged"|"skip_no_match"}]`
- **Commit:** `feat(cli): flow projects backfill with --dry-run default + --confirm gate + --project scope (REQ-24)`

### T1.13 — CHANGELOG.md v0.5.0 entry + 6 SKILL.md "Cross-project federation hook" prose updates

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~15 CHANGELOG + ~25 prose (~4 per file × 6) = ~40
- **Files:**
  - `CHANGELOG.md` (modify — new `## [0.5.0] - <date>` section above `[0.4.0]`)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (runtime, not repo)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (runtime)
- **Dependencies:** all T1.1..T1.12
- **Acceptance criteria:**
  - [ ] `CHANGELOG.md` v0.5.0 entry lists: `--federated --projects --since --type` flags on `flow search`; `flow projects alias` + `flow projects backfill` subcommands; `mem_search_federated` ABC v1.2 + `InMemoryBackend` impl; 3 new `federated_*` counters + `record_federated_summary` helper; `project_detector` + `project_aliases` modules; `~/.config/flow-engineering/registry.json` + `project-aliases.json` runtime configs; ABC v1.1 → v1.2 bump
  - [ ] 6 SKILL.md prose updates name all 5 REQs (REQ-23..27) and reference `mem_search_federated`, `--federated` flag, `flow projects alias`, `flow projects backfill --dry-run`, `project-aliases.json`, and the 3 federated counters in their respective "Cross-project federation hook" sections
  - [ ] CHANGELOG entry follows the `[0.4.0]` format (Added / Tests / Notes sections)
- **Commit:** `docs(release): CHANGELOG v0.5.0 entry + 6 SKILL.md cross-project federation hooks`

---

## Apply Batches (≤6 tasks OR ≤150 LOC prod per delegation)

Per-delegation batch ceiling from Engram #112 pattern (`apply-batches-split-into-6-tasks-per-delegation`). Default delegate runtime is ~15 min; larger batches TIMEOUT.

### Single-PR batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **A** | T1.1 + T1.2 + T1.4 | ~415 | ABC v1.2 + InMemoryBackend federated impl + BDD req23 — atomic foundation; T1.4 tests backfill T1.1+T1.2 |
| **B** | T1.3 + T1.5 + T1.6 + T1.7 + T1.12 | ~730 | project_detector + 2 BDD features + CLI federated flags + backfill CLI — combined CLI+library work; **TIMEOUT RISK** |
| **C** | T1.8 + T1.9 + T1.10 + T1.11 + T1.13 | ~635 | Observability counters + aliases + 2 BDD features + docs — cohesive close-out |

**Batch B risk mitigation:** at ~730 LOC, batch B is the highest timeout risk (~2h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **B1** = T1.3 + T1.6 (project_detector + CLI federated flags) — ~390 LOC impl + CLI cohesion
- **B2** = T1.5 + T1.7 + T1.12 (2 BDD features + backfill CLI) — ~340 LOC acceptance + backfill

If sub-agent reports progress as "project_detector + CLI federated flags landed, BDD remaining", abort and launch B2 as continuation.

### Branch targeting

- **Single PR → `main`.** No chained PR split per proposal #158 recommendation. Per-delegation batching is internal to the apply phase only; the final PR merges the cumulative result of all 3 batches.
- **Squash merge** for the final PR (preserves linear history, single commit `feat: cross-project-federation v0.5.0`).
- Each batch's commits land on the PR branch; PR merges after batch C completes + `uv run pytest` is green.

---

## Open follow-ups for sdd-archive (after PR merges)

| # | Item | Owner |
|---|------|-------|
| 1 | Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters (REQ-26 scenario 4) | sdd-archive |
| 2 | Bump `pyproject.toml` version `0.4.0` → `0.5.0` (matches CHANGELOG entry) | sdd-archive |
| 3 | Verify `MEMORY.md` or AGENTS.md mentions `FLOW_AUTO_PROJECT_TAG=1` opt-in + `flow projects alias/backfill` workflow for future contributors | sdd-archive |
| 4 | Cross-impact: confirm `vector-semantic-search` (REQ-17/22) tests stay green; vector index path is orthogonal to federation | sdd-archive |
| 5 | Document `registry.json` auto-build behavior (D11) in `~/.config/flow-engineering/README` or AGENTS.md for first-run users | sdd-archive |

---

## Structured Metadata

- **total_tasks:** 13 (T1.1..T1.13)
- **pr_split:** single PR (no chained split)
- **forecast_loc_production:** ~370
- **forecast_loc_realistic:** ~7200 (×6 TDD multiplier per Engram #113 decision-reality-drift precedent + ~30 LOC per BDD scenario × 25 scenarios)
- **batches:** 3 (A=3, B=5, C=5)
- **batch_b_timeout_risk:** HIGH (~730 LOC; mitigation = split into B1+B2 if delegation hits 15-min ceiling)
- **review_workload_forecast:**
  - `400_line_budget_risk`: low (single PR ~1205 LOC; ~7200 realistic; ~1500 per apply batch)
  - `chained_prs_recommended`: no (per proposal #158; design D9 non-breaking + ABC v1.2 additive)
  - `decision_needed_before_apply`: no (delivery strategy `single-pr` with `400-line budget risk: low`)
  - `chain_strategy`: N/A (single PR)
- **strict_tdd:** on (RED → GREEN → REFACTOR per task)
- **bdd_feature_files:** 5 NEW (req23..req27)
- **bdd_scenarios:** 25
- **out_of_scope_count:** 8 (preserved from spec #161)
- **next_recommended:** `sdd-apply cross-project-federation batch A` (T1.1 + T1.2 + T1.4, ~415 LOC, ~17 min)