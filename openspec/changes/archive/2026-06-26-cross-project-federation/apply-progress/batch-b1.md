<!-- Archived 2026-06-26 from sdd/cross-project-federation/apply-progress-batch-b1 (Engram #166) -->

# Apply progress batch B1 — cross-project-federation

## Goal

SDD apply batch B1 of cross-project-federation (split from B due to timeout risk): T1.3 (project_detector) + T1.6 (CLI --federated flags).

## Branch / PR State

- Branch: `feature/cross-project-federation`
- Baseline (batch A HEAD): `d44c599`
- Final HEAD: `5d85b5e`

## Commits

- `83a2a03` test(unit): RED fixtures for project_detector with cwd-based detection — tests/unit/test_project_detector.py +218
- `8f258df` feat(backend): project_detector with cwd-based detection + apply_tag — src/flow_engineering/project_detector.py +171 (NEW)
- `9a06499` test(unit): RED fixtures for flow search --federated --projects --since --type flags — tests/unit/test_cli_federated.py +320
- `dfd0e68` feat(cli): --federated --projects --since --type flags on flow search (NON-BREAKING) — src/flow_engineering/cli.py +121/-25
- `6005232` test(refine): portable home anchor in project_detector tests + fix noise fixture — tests/unit/* +15/-15
- `5d85b5e` docs(sdd): mark T1.3 + T1.6 complete in cross-project-federation tasks.md — tasks.md +19/-19

## LOC Delta

- `src/flow_engineering/project_detector.py`: +171 (NEW)
- `src/flow_engineering/cli.py`: +121/-25 (+96 net)
- `tests/unit/test_project_detector.py`: +218 (NEW)
- `tests/unit/test_cli_federated.py`: +320 (NEW)
- `openspec/changes/cross-project-federation/tasks.md`: +19/-19
- Total: +849/-44 (+805 net)

## Test Delta

- Baseline: 590
- Final: 620
- Delta: +30 (20 project_detector unit + 10 cli_federated unit)

## Risks / Blockers

- none

## Deviations from Spec

1. `apply_tag` mutates the live obs dict returned by `mem_get_observation` rather than going through `backend.update_observation(..., project=project)` because the existing ABC seam doesn't accept `project`. InMemoryBackend returns the live dict (engram_io.py:232) so mutation works for the test fixture. T1.5 BDD will exercise the production backend; if it needs the ABC extension it lands in batch B2.
2. `wrong-shape` registry test dropped — user prompt only requires empty-dict for missing file and parse error for malformed JSON. Wrong-shape (no `cwd_to_project` key) is treated as empty for forgiveness.
3. T1.3 acceptance bullet "Lazy scan of FLOW_PROJECTS_ROOT on first load_registry() when file missing" DEFERRED to T1.10 — T1.3's detect() already reads registry.json when present (manual seeding required for now).

## Learnings

- pathlib `Path("/c/dev/proyects/...")` on Windows: parts are `('\\', 'c', 'dev', 'proyects', ...)` so the `/c` becomes drive-rooted. Parts-based detection (find `proyects` with prev=`dev`) handles this; literal `Path.home() / "dev" / "proyects"` would NOT match (different drive).
- For Layout 2 (`<home>/proyects/<name>`), use `Path.home() / "proyects" / <name>` directly in tests rather than `/c/Users/insyd/...` — portable across platforms and matches `is_relative_to` semantics.
- CSV parsing via stdlib `csv.reader([s])` handles quoted commas (`"a, b",c`); preferred over `str.split(',')` per user prompt.
- `--since` validation: `_parse_since(s)` returns epoch float; we validate via `_parse_since(s)` then pass the raw ISO string to `mem_search_federated` (design D7 lexicographic compare). Discarding the float is intentional.
- `--federated` is mutually exclusive with `--semantic/--hybrid` — gate check at CLI level is the cleanest place to express this.
- Table renderer with project column: gating `show_project = any("project" in r for r in rows)` keeps legacy 4-col format unchanged when `--federated` is absent (verified by spy on `mem_search_federated`).

## Next

- batch B2: T1.5 (BDD req24_project_detector.feature with 6 scenarios) + T1.7 (BDD req25_cli_federated.feature with 5 scenarios) + T1.12 (CLI flow projects backfill with --dry-run default + --confirm gate) — ~250 LOC BDD+backfill
- open follow-up: if T1.5 BDD needs the ABC update_observation to accept `project` kwarg, extend `EngramBackend.update_observation` + `InMemoryBackend.update_observation` non-breakingly.

**Session**: sdd-cross-project-federation-design-2026-06-26
**Topic**: sdd/cross-project-federation/apply-progress-batch-b1
**Engram**: #166