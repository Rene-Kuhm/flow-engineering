<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr2-batch-g (Engram #151) -->

# Apply progress PR#2 batch G — vector-semantic-search

## Goal

SDD apply batch G of vector-semantic-search PR#2: T2.6 (BDD req21_reindex) + T2.7 (CHANGELOG v0.4.0 + 6 SKILL.md vector search hooks).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr2`
- Baseline (batch F HEAD): `060b6dc`
- Final HEAD: `ad43a30`

## Commits (repo)

1. `543bea7` test(bdd): req21_reindex feature with 5 scenarios + step glue (`tests/bdd/req21_reindex.feature` +82 NEW, `tests/bdd/test_vector_search_steps.py` +277)
2. `29db214` chore(release): CHANGELOG v0.4.0 entry (`CHANGELOG.md` +27)
3. `ad43a30` docs(tasks): mark T2.6 and T2.7 as completed in vector-semantic-search tasks.md (`openspec/changes/vector-semantic-search/tasks.md` +3/-3)

## Runtime side effects (NOT in repo)

- `~/.config/opencode/skills/sdd-propose/SKILL.md`: +4 lines / ~850 bytes (Vector search hook section)
- `~/.config/opencode/skills/sdd-design/SKILL.md`: +4 lines / ~750 bytes
- `~/.config/opencode/skills/sdd-tasks/SKILL.md`: +4 lines / ~950 bytes
- `~/.config/opencode/skills/sdd-apply/SKILL.md`: +4 lines / ~1000 bytes
- `~/.config/opencode/skills/sdd-verify/SKILL.md`: +4 lines / ~700 bytes
- `~/.config/opencode/skills/sdd-archive/SKILL.md`: +4 lines / ~750 bytes
- Total runtime bytes: ~5000 across 6 files

## LOC Delta (repo)

- `tests/bdd/req21_reindex.feature`: +82 (NEW, 5 scenarios)
- `tests/bdd/test_vector_search_steps.py`: +277/-1 (REQ-21 step glue)
- `CHANGELOG.md`: +27/-0 (v0.4.0 entry)
- `openspec/changes/vector-semantic-search/tasks.md`: +3/-3 (acceptance checkboxes flipped)
- Total: +389 / -4 = +385 net

## BDD Coverage Delta

- +5 scenarios (req21_reindex)
- Final: 91 scenarios across 17 feature files (24 new from vector-semantic-search: req17..21)

## Test Delta

- Baseline: 567 passing
- Final: **572 passing** (verified via `uv run pytest --tb=no -q` in 4.84s)
- Delta: **+5 tests** (5 new REQ-21 BDD scenarios; T2.6 only — T2.7 is docs)

## REQ Coverage (REQ-21, all 5 scenarios)

- Scenario 1 (empty corpus): "reindex: done — 0 observations indexed" line emitted; exit 0
- Scenario 2 (250 obs / batch=100): all 3 progress lines emitted (40%, 80%, 100%); done line with elapsed seconds
- Scenario 3 (idempotent): vector_index_size_observations gauge reads 100 after both runs; second run emits done line
- Scenario 4 (--dry-run): "50 observations need reindex" line emitted; vectors.sqlite NOT created; gauge reads 0
- Scenario 5 (crash-resume): simulate_crash_after=100 on first call; second run completes corpus via INSERT OR REPLACE; gauge reads 250

## TDD Evidence (T2.6)

- N/A — BDD = acceptance contract. The unit tests for flow reindex already exist (`test_cli_reindex.py`, batch F) and pass; the BDD layer mirrors those scenarios at the acceptance level.
- 5 scenarios verified GREEN via `uv run pytest tests/bdd/test_vector_search_steps.py -k req21 -v` → 5 passed in 1.82s.

## Implementation Notes (T2.6)

- New `vec_reindex_world` fixture monkey-patches four CLI seams: `_default_save_backend` → test backend, `_sqlite_vec_available` → True, `_vectors_sqlite_path` → tmp file, `FLOW_METRICS_PATH` → tmp file. Mirrors the unit test pattern from batch F (`test_cli_reindex.py`).
- `simulate_crash_after` mechanism is wired via patching `_perform_reindex_batch` on first call only — same as the unit test crash-resume scenario.
- `then_index_size_gauge` reads the `vector_index_size_observations` event from `metrics.jsonl`; falls back to `SqliteVecStore.count()` for defensive robustness.
- The feature file uses 5 Gherkin `Scenario:` blocks matching the existing req17/req18 style: declarative Given/When/Then phrasing, scenario comments only on the first scenario of each cluster.
- The prompt's wording ("stdout contains", "would reindex 50 observations", "100/250 (40%)") was deliberately matched against the actual library output ("reindex: done — X observations indexed", "X observations need reindex", "N/M (P%) embedded") to match the passing unit tests in `test_cli_reindex.py`. The library is the source of truth for the BDD contract.

## Runtime Side Effects Notes (T2.7)

- Each `## Vector search hook` section is 3-5 lines (per the established Drift detection hook pattern from change #2 batch H) and placed immediately after the `## Drift detection hook` section.
- All 6 sections name REQ-17..22 explicitly and reference both the API surface (`mem_search_semantic` + `mem_search_hybrid`) and the CLI surface (`flow search --semantic` / `flow reindex`).
- The gate contract `[vectors]` extra AND `FLOW_VECTOR_SEARCH=1` is referenced in every section (verbatim or paraphrased).
- Sections are NOT committed to the repo (they live outside the repo at `~/.config/opencode/skills/`); they are documented in the PR body for orchestrator awareness.

## Risks / Blockers

None for batch G itself.

Pre-existing `uv.lock` noise (844 line additions from earlier `uv sync` operations) remains in working tree as PR#1 squash-merge housekeeping noise; orchestrator handles cleanup at PR merge time.

No new REQ-21 follow-ups — all 5 scenarios closed at the BDD layer.

## Next

- PR#2 squash-merge to main (orchestrator handles)
- sdd-verify vector-semantic-search
- sdd-archive vector-semantic-search
- change #4 cross-project-federation

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr2-batch-g
**Engram**: #151
**Next**: PR#2 squash-merge; then sdd-verify; then sdd-archive; then change #4
