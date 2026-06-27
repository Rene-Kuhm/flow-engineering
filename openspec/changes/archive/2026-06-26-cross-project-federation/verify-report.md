<!-- Archived 2026-06-26 from sdd/cross-project-federation/verify-report (Engram #170) -->

# Verify Report — cross-project-federation

## Status

**FAIL** (initial; resolved post-W-fix)

## Date

2026-06-26

## Mode

Strict TDD (`uv run pytest`); main HEAD `bfa2db5` (PR #10 squash merge)

## Test Execution

| Suite | Count | Time | Exit |
|---|---|---|---|
| Full pytest (`-x --tb=short`) | **699 passed** | 5.78s | 0 |
| BDD subset (`tests/bdd/ -v`) | **116 passed** | 2.72s | 0 |
| Delta from vector-semantic-search baseline (572) | **+127** | | |
| Delta from v0.4.0 (576) | **+123** | | |

| Subset | Count | Files | Notes |
|---|---|---|---|
| Unit tests | ~583 | many | includes 23 new federated + 20 project_detector + 20 project_aliases + 16 cli_federated + 27 cli_projects_backfill + 8 cli_projects_alias + 19 observability_federated + 9 engram_io_federated |
| BDD tests | 116 | 23 | +25 cross-project-federation scenarios across 5 new feature files (req23..req27) |

## REQ Coverage (5 REQs, 25 scenarios)

| REQ | Scenarios | Tests covering | Status |
|---|---|---|---|
| REQ-23 (mem_search_federated ABC v1.2) | 5 | TestFederatedSearch (9 unit) + 5 BDD req23 | COMPLIANT — NON-BREAKING default raises NotImplementedError; InMemoryBackend override with projects/since/type_filter SQL-equivalent filters |
| REQ-24 (project_detector + backfill) | 6 | 20 unit project_detector + 14 unit cli_projects_backfill + 6 BDD req24 | COMPLIANT — `detect(cwd)` cwd-based; `flow projects backfill --dry-run` default + `--confirm` gate; `flow projects backfill --confirm` without `--project` iterates alias map (B2 deviation closed in batch C) |
| REQ-25 (CLI --federated flags) | 5 | 16 unit cli_federated + 5 BDD req25 | COMPLIANT — `--federated` default off (byte-identical to pre-change verified by spy); CSV parsing; `_parse_since` reused |
| REQ-26 (3 federated counters + record_federated_summary) | 4 | 19 unit observability_federated + 4 BDD req26 | COMPLIANT — `federated_search_invoked_total{trigger=cli|programmatic}`, `federated_search_projects_queried{count=N}` (no `_total`), `federated_search_results_returned_total`; helper mirrors `record_vector_summary` |
| REQ-27 (project-aliases.json + flow projects alias) | 5 | 20 unit project_aliases + 8 unit cli_projects_alias + 5 BDD req27 | PARTIAL at verify-time — Scenarios 2-5 PASS (CLI write, conflict, idempotent, malformed JSON). Scenario 1 PASSES VACUOUSLY at verify-time (see C1 below); RESOLVED in `4c6b39b` |

**Compliance summary (verify-time)**: 4/5 REQs compliant; REQ-27 scenario 1 contract NOT delivered (C1).

**Compliance summary (post W-fix)**: 5/5 REQs compliant; REQ-27 scenario 1 contract delivered with forward+reverse alias resolution + result-level project field rewrite.

## Task Closure (13 tasks)

| Task | Status | Notes |
|---|---|---|
| T1.1 — mem_search_federated ABC v1.2 | DONE | commit `8d158d1`; NON-BREAKING default raises NotImplementedError |
| T1.2 — InMemoryBackend.mem_search_federated | DONE | commit `6b2818d`; projects/since/type_filter all implemented |
| T1.3 — project_detector + apply_tag | DONE | commit `8f258df`; cwd-based detect + apply_tag (W19 contract drift fixed in `4c6b39b`) |
| T1.4 — BDD req23_federated_search.feature | DONE | commit `6076aba`; 5 scenarios |
| T1.5 — BDD req24_project_detector.feature | DONE | commit `5795625`; 6 scenarios |
| T1.6 — flow search --federated flags | DONE | commit `dfd0e68`; 4 flags added |
| T1.7 — BDD req25_cli_federated.feature | DONE | commit `5795625`; 5 scenarios |
| T1.8 — 3 federated_* counters | DONE | commit `b31c48f`; FEDERATED_COUNTER_NAMES + record_federated_summary |
| T1.9 — BDD req26_federated_observability.feature | DONE | commit `e8ecd2a`; 4 scenarios |
| T1.10 — project-aliases.json + flow projects alias | DONE | commit `97f5a94`; AliasRecord, resolve, load/save atomic, add_alias idempotent+conflict-safe (C1 fix in `4c6b39b`) |
| T1.11 — BDD req27_project_aliases.feature | DONE | commit `70921dc`; 5 scenarios |
| T1.12 — flow projects backfill | DONE | commit `31b89ff`; --dry-run default + --confirm gate; B2 deviation (REFUSE without --project) closed in batch C via alias-map iteration |
| T1.13 — CHANGELOG v0.5.0 + 6 SKILL.md | DONE | CHANGELOG entry exists (PR#10 squash); 6 SKILL.md hooks present; W17 doc-accuracy fix in `4c6b39b`; W18 tasks.md checkbox flip landed as part of archive commit |

**Task closure summary**: 13/13 work units shipped (commits + tests + docs). All 13 now marked `[x]` in tasks.md (W18 fix landed in archive commit).

## CHANGELOG Accuracy

| Claim | Actual | Status |
|---|---|---|
| `699 / 699 tests passing` | 699 / 699 passing in 5.78s | verified |
| `25 new BDD scenarios across 5 feature files` | 25 / 5 confirmed | verified |
| `Total BDD: 116 scenarios across 23 feature files` | 116 / 23 confirmed | verified |
| Feature files: req23 (5), req24 (6), req25 (5), req26 (4), req27 (5) | matches | verified |
| Counter names match `FEDERATED_COUNTER_NAMES` in observability.py:90-93 | matches | verified |
| REQ-23..27 listed | all 5 present | verified |
| `record_federated_summary(invoked, projects_queried, results_returned, *, trigger="programmatic")` signature | all four params are keyword-only (`*` BEFORE `invoked`) | S3 minor doc nit (cosmetic) |
| `Alias resolution is applied in mem_search_federated and flow projects backfill (both forward and reverse...)` | matches after W17 fix in `4c6b39b` | resolved |

## Documentation Check

| Check | Result |
|---|---|
| CHANGELOG v0.5.0 entry exists | verified — `CHANGELOG.md:7-31` |
| 6 SKILL.md files have `## Cross-project federation hook` | verified — via grep on `~/.config/opencode/skills/sdd-*/SKILL.md`: 6/6 matches (sdd-propose, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive) |
| Hook content references the 5 REQs + flag + subcommand + counter names | verified — sampled SKILL.md content at sdd-apply:247-250 and sdd-verify:94-98 includes all required references |

## Cross-Impact Non-Regression

| Prior change | REQs | BDD tests | Result |
|---|---|---|---|
| decision-code-linking | REQ-1..8 | 20 P1 + 19 P2 = 39 | all pass |
| decision-reality-drift | REQ-9..16 | 17 | all pass |
| vector-semantic-search | REQ-17..22 | 28 | all pass |
| `mem_search` (FTS5 single-project) | — | implicit | unchanged (alias resolver added only to `mem_search_federated`; legacy `mem_search` byte-identical) |
| `EngramBackend` ABC v1.2 backward compat | — | TestFederatedSearch::test_abc_default_import_unchanged | third-party subclass without override still instantiates; default raises only at call-time |
| `flow search` without `--federated` | — | TestSearchNoFederatedUnchanged (2 unit) + BDD req25 scenario 1 | byte-identical; spy asserts `mem_search_federated` NOT called |

## CRITICAL FINDINGS (verify-time)

### C1 — REQ-27 scenario 1 contract NOT delivered; BDD test passes vacuously

**Spec contract** (`openspec/changes/cross-project-federation/spec.md:235-242`):
> Query for `flow-image-generator-v2` returns `flow-image-generator-main` rows when alias exists
> - GIVEN a backend with 1 observation tagged `project=flow-image-generator-v2` containing "drift"
> - AND `project-aliases.json` maps `flow-image-generator-v2 → flow-image-generator-main`
> - WHEN `mem_search_federated("drift", projects=["flow-image-generator-v2"])` runs
> - THEN the alias resolver rewrites `projects` to `["flow-image-generator-main"]` BEFORE SQL
> - AND **the observation IS returned** (alias resolution is transparent; the user-facing contract treats the alias as a synonym)
> - AND the `project` field in the result row is `"flow-image-generator-main"` (the canonical name, NOT the alias)

**Implementation at verify-time** (`src/flow_engineering/engram_io.py:334-348`):
The alias resolver only rewrote the QUERY (`projects`), NOT the result rows. When the obs was tagged `flow-image-generator-v2` and the query was rewritten to `flow-image-generator-main`, the obs was filtered OUT.

**Smoke test reproduction** (manual, run against live impl at verify-time):
```
Seeded obs: id=1 project=flow-image-generator-v2
Query returned 0 rows
FAIL: spec scenario 1 says 'the observation IS returned' but impl returned 0 rows.
```

**BDD test passed vacuously** (`tests/bdd/test_cross_project_federation_steps.py:429-440`):
With 0 results, the for loop never executes, no assertion fires, test PASSES.

**Classification**: Per Strict TDD Module Step 5f, this was **CRITICAL — assertion without production code call**.

**Resolution** (`4c6b39b`): Added forward + reverse alias resolution on results — when an obs is tagged with an `old` key, rewrite its `project` field to the canonical `new` in the returned dict. Also tightened the BDD step to assert `len(payload["results"]) == 1` BEFORE the per-row loop.

## WARNING FINDINGS (verify-time)

### W17 — CHANGELOG line 30 overstates alias resolution surface

`CHANGELOG.md:30` (verify-time): "Alias resolution is applied in `mem_search_federated`, `mem_search`, and `flow projects backfill`"

**Resolution** (`4c6b39b`): Changed "mem_search_federated, mem_search, and flow projects backfill" to "mem_search_federated and flow projects backfill (both forward and reverse...)". Now matches actual impl.

### W18 — tasks.md checkboxes stale for batch C (T1.8..T1.13)

At verify-time, tasks.md had unchecked `[ ]` acceptance bullets for T1.8, T1.9, T1.10, T1.11, T1.13.

**Resolution** (archive commit): flipped all 5 sections' acceptance bullets to `[x]`; added `DONE (<hash>)` annotations. (Note: `4c6b39b` commit message claimed W18 was resolved but the diff didn't actually include tasks.md; the bookkeeping fix landed in the archive commit.)

### W19 — apply_tag spec deviation: raises ValueError instead of returning error dict

Spec (REQ-24 spec.md:79): "`apply_tag` helper SHALL mutate one observation's `project` field via `update_observation` ... and SHALL refuse (**return error dict**) when `project` is empty or whitespace."

**Resolution** (`4c6b39b`): Changed `apply_tag` to return structured error dict; updated 3 unit tests to assert the new contract. The `update_observation` ABC seam extension was left as-is (the deviated path mutates the live dict; this is acceptable for `InMemoryBackend` since the ABC seam extension would require bumping to v1.3).

## SUGGESTION FINDINGS

### S2 — pyproject.toml version not bumped to 0.5.0

`tasks.md:368` listed as open follow-up: "Bump `pyproject.toml` version `0.4.0` → `0.5.0` (matches CHANGELOG entry)". Defer to sdd-archive (carried forward as out-of-scope item).

### S3 — CHANGELOG record_federated_summary signature nit

`CHANGELOG.md:17-18`: `record_federated_summary(invoked, projects_queried, results_returned, *, trigger="programmatic")` — the notation `(invoked, ...)` suggests `invoked` is positional, but actual signature has all four params keyword-only. Cosmetic.

## Verdict (verify-time, before W-fix)

**FAIL** — 1 CRITICAL (C1: REQ-27 scenario 1 contract not delivered; BDD test passes vacuously on ghost loop). 3 WARNINGs (W17 CHANGELOG accuracy, W18 tasks.md bookkeeping, W19 apply_tag spec deviation). 2 SUGGESTIONs.

## Verdict (post W-fix, pre-archive)

**PASS WITH WARNINGS** — All CRITICAL resolved. 0 carry-forward warnings blocking archive. S2/S3 carry forward as non-blocking suggestions.

## Relevant Files

- `openspec/changes/cross-project-federation/spec.md` — REQ-23..27 + 25 scenarios
- `openspec/changes/cross-project-federation/design.md` — D1-D11 (locked)
- `openspec/changes/cross-project-federation/tasks.md` — 13 tasks (post-W18: all `[x]`)
- `src/flow_engineering/engram_io.py:124-160` — ABC v1.2 mem_search_federated default
- `src/flow_engineering/engram_io.py:295-373` — InMemoryBackend.mem_search_federated impl (forward+reverse alias resolution post-C1 fix)
- `src/flow_engineering/observability.py:89-100` — FEDERATED_COUNTER_NAMES catalog
- `src/flow_engineering/observability.py:374-413` — record_federated_summary helper
- `src/flow_engineering/project_detector.py:139-166` — apply_tag (returns error dict post-W19 fix)
- `src/flow_engineering/project_aliases.py:198-242` — add_alias (idempotent + conflict-safe)
- `src/flow_engineering/cli.py:572-680` — flow search --federated flags + trigger="cli"
- `src/flow_engineering/cli.py:1201-1382` — flow projects backfill (alias iteration in lines 1303-1342)
- `src/flow_engineering/cli.py:1386-1430` — flow projects alias subcommand
- `tests/bdd/test_cross_project_federation_steps.py:429-440` — REQ-27 scenario 1 step (asserts non-empty before per-row loop post-C1 fix)
- `tests/bdd/test_cross_project_federation_steps.py:618-632` — REQ-27 alias CLI exit-code steps
- `tests/bdd/test_cross_project_federation_steps.py:1094-1193` — alias_world fixture + alias CLI step bindings
- `CHANGELOG.md:7-31` — v0.5.0 entry (W17 doc-accuracy fix in `4c6b39b`)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — 6 hook sections
- Engram `sdd/cross-project-federation/verify-report` — observation #170 (this file's source)

**Session**: sdd-cross-project-federation-verify-2026-06-26
**Topic**: sdd/cross-project-federation/verify-report
**Engram**: #170