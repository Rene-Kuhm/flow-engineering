<!-- Archived 2026-06-26 from sdd/cross-project-federation/apply-progress-batch-b2 (Engram #167) -->

# Apply progress batch B2 — cross-project-federation

## Goal

SDD apply batch B2 of cross-project-federation (split from B): T1.5 (BDD req24) + T1.7 (BDD req25) + T1.12 (CLI flow projects backfill with safety gate).

## Branch / PR State

- Branch: `feature/cross-project-federation`
- Baseline (batch B1 HEAD): `5d85b5e`
- Final HEAD: `7e2dee8`

## Commits

- `5795625` test(bdd): req24 + req25 feature files with 11 scenarios + step glue
- `2598f04` test(unit): RED fixtures for flow projects backfill with dry-run default + confirm gate
- `31b89ff` feat(cli): flow projects backfill with dry-run default + --confirm safety gate + JSON report
- `7e2dee8` docs(sdd): mark T1.5 + T1.7 + T1.12 complete in cross-project-federation tasks.md

## LOC Delta

- `src/flow_engineering/cli.py`: +185 (added `flow projects` group + `flow projects backfill` subcommand with 4 flags)
- `src/flow_engineering/project_detector.py`: +0 (B1 impl reused via `apply_tag` + `detect` imports)
- `tests/bdd/req24_project_detector.feature`: +56 (NEW, 6 scenarios)
- `tests/bdd/req25_cli_federated.feature`: +53 (NEW, 5 scenarios)
- `tests/bdd/test_cross_project_federation_steps.py`: +513/-31 (extended with cli_world fixture + REQ-24/REQ-25 step glue)
- `tests/unit/test_cli_projects_backfill.py`: +304 (NEW, 14 unit tests across 6 test classes)
- `openspec/changes/cross-project-federation/tasks.md`: +27/-27 (marked T1.5 + T1.7 + T1.12 done)
- Total: +1138/-58 (+1080 net)

## BDD Coverage Delta

- +11 scenarios (6 req24 + 5 req25)
- Final: 32 across 21 feature files (was 21 across 19)

## Test Delta

- Baseline: 620
- Final: 645
- Delta: +25 (11 new BDD scenarios + 14 new backfill unit tests)

## Risks / Blockers

- none

## Deviations from Spec

1. **REQ-24 scenario 5 reinterpretation** — The spec says `flow projects backfill --confirm` (no `--project`) iterates the entire alias map and writes all matches. The batch-B2 implementation REFUSES this invocation because the alias resolver (T1.10) is deferred to batch C. The implementation prioritises the explicit safety gate over alias iteration; when T1.10 lands in batch C, the alias-iteration path can be layered on top of the existing `--confirm` gate. Documented in tasks.md T1.12.
2. **REQ-24 scenario 1 BDD wording relaxed** — Spec says `detect()` returns the project name "when env var FLOW_AUTO_PROJECT_TAG=1". The BDD scenario tests `detect()` directly with a known cwd; the env-var opt-in gate is the caller's responsibility per design D2 (`flow save` is what gates on `FLOW_AUTO_PROJECT_TAG`, not `detect()` itself).
3. **JSON output shape** — The spec's design D3 calls for a JSON ARRAY; the implementation emits a JSON OBJECT envelope `{"would_change": N, "would_skip": N, "changes": [...]}`. The user's batch-B2 prompt explicitly listed the object shape with counters; the array form is preserved per-row inside `changes`. Both BDD scenarios and unit tests accept either form.

## Learnings

- pytest-bdd's `parsers.parse` does NOT match empty-string captures: `parsers.parse('... "{args}"')` against `... ""` returns `None`. Workaround: split into two `@when` steps — one literal step for the no-arg case, one parameterized step for the with-args case.
- pytest-bdd step functions are matched to scenarios by **fixture parameter type**: a step function `def then_x(req24_world)` cannot be invoked by a scenario that uses the `req25_world` fixture even if the logic is identical. Solution: consolidate per-test-family fixtures (REQ-24 CLI scenarios + REQ-25 scenarios share a single `cli_world` fixture; REQ-24 detect scenarios keep their own `req24_world`; REQ-23 keeps `federated_world`).
- Click's CliRunner.exit_code is `None` (not 0) when the runner fails to even invoke the command (e.g., "No such command 'projects'"). Tests that assert non-zero exits get a free pass for "command not found" — guard the assertion against this by checking exit_code is not None first OR by using a more specific exit code assertion (e.g., `== 2` for "invalid args").
- InMemoryBackend.mem_save auto-assigns `project="insyd"` — to seed an "untagged" observation for the backfill tests, set `obs["project"] = None` AFTER `mem_save()` returns. The `apply_tag()` helper then mutates the live dict (not via `backend.update_observation`) because `update_observation` in InMemoryBackend doesn't accept `project=`. This is the same seam documented in B1's apply-progress deviation #1.
- `parsers.parse` `{name:w}` matches `\w+` only — dashes in `2026-06-15` are NOT matched. Use bare `{name}` (greedy up to whitespace) for date/title strings.

## Next

- batch C: T1.8 (3 federated_* counters) + T1.9 (BDD req26) + T1.10 (project-aliases.json + flow projects alias — UNBLOCKED by B2's `flow projects` group scaffold) + T1.11 (BDD req27) + T1.13 (CHANGELOG v0.5.0 + 6 SKILL.md) — ~450 LOC

**Session**: sdd-cross-project-federation-design-2026-06-26
**Topic**: sdd/cross-project-federation/apply-progress-batch-b2
**Engram**: #167