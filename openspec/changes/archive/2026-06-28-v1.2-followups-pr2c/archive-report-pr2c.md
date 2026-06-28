# Archive Report — PR#2c (v1.2.0c) of v1.2-followups

**Change:** `v1.2-followups` PR#2c (v1.2.0c)
**Branch:** main
**Closed:** 2026-06-28
**Status:** ARCHIVED — PR#2c of v1.2-followups chain CLOSED

## Goal

REQ-V1.2.3 — Min SDD skill versions enforcement. Add `enforce_min_skill_versions()` helper using existing `SkillVersionError` at `opencode_skill_catalog.py:117` + `[tool.flow_engineering] min_sdd_skill_versions` section in `pyproject.toml` (8 sdd-* agents) + 3-line CLI hooks at `flow apply`/`verify`/`archive` startup (exit code 4 on violation + JSON remediation payload).

## Sub-batch summary

PR#2c shipped across 5 work-unit commits on `main` (post-PR#2b merge):

| Commit | Task | Description |
|--------|------|-------------|
| `960367c` | T3.2 RED | `TestEnforceMinSkillVersions` (5 tests) + `TestPyprojectMinSkillVersionsSection` (2 tests) |
| `3621521` | T3.3 GREEN | `enforce_min_skill_versions()` helper reusing existing `SkillVersionError` |
| `57845c0` | T3.4 GREEN | `[tool.flow_engineering] min_sdd_skill_versions` pyproject section (8 sdd-* agents) |
| `7b1dc25` | T3.5 | 3-line CLI hooks at `flow apply`/`verify`/`archive` startup (exit code 4 + JSON remediation payload) |
| `5081a67` | T3.6 REFACTOR | Integration test for full skill version gate flow + BDD feature + CHANGELOG v1.2.0c |

## Test count

- Pre-PR#2c: 1360 passing
- Post-PR#2c: **1376 passing** (+16)
- 0 regressions vs v1.2.0b baseline

## Files touched (cumulative within PR#2c scope)

- `src/flow_engineering/opencode_skill_catalog.py` (SkillVersionError + enforce_min_skill_versions helper)
- `src/flow_engineering/cli.py` (3-line CLI hooks at apply/verify/archive startup)
- `pyproject.toml` ([tool.flow_engineering] min_sdd_skill_versions section with 8 sdd-* agents)
- `tests/unit/test_opencode_skill_catalog.py` (TestEnforceMinSkillVersions + TestPyprojectMinSkillVersionsSection)
- `tests/integration/test_skill_version_gate.py` (NEW integration test)
- `tests/bdd/req54_min_sdd_skill_versions.feature` (NEW BDD feature)
- `CHANGELOG.md` (## [1.2.0c] entry)

## Verify verdict

**PASS WITH WARNINGS** (per drift-hardening + v0.9.0 + v1.0 + v1.1 + v1.2-PR#2a + v1.2-PR#2b precedent posture). See `verify-report-pr2c.md` for full findings.

## Carry-forwards NOT in PR#2c (deferred to PR#2d)

- Path A subcommand group rename (`flow drift-events` → `flow drift events`)
- 1-release deprecated=True Click group alias shim
- CHANGELOG v1.2 BREAKING entry
- pyproject version bump 1.1.0 → 1.2.0
- Capability spec sync for v1.2.0 archive status

## Next

After PR#2c archive + push: PR#2d (Path A rename + version bump) closes the entire v1.2 chain. Then change #12 (v1.2-followups) FULLY CLOSED — backlog al día.

## Engram artifacts

- `sdd-init/flow-engineering` — sync_id `obs-a8a3544c95c44a48`
- `sdd/v1.2-followups/{explore,proposal,design,tasks,verify-report-pr2c,archive-report-pr2c}`
- `sdd/v1.2-followups/apply-progress-pr2c`
- `sdd/session-mode/2026-06-28-final-remaining`
- `sdd/prompt-registry/apply-progress-pr2b` (referenced for chained PR pattern)

## Acceptance criteria

- [x] All 5 tasks (T3.2..T3.6) closed
- [x] `enforce_min_skill_versions()` helper exists with full test coverage
- [x] `[tool.flow_engineering] min_sdd_skill_versions` section in pyproject.toml (8 sdd-* agents)
- [x] 3-line CLI hooks at flow apply/verify/archive startup (exit code 4)
- [x] 1376/1376 tests passing
- [x] Ruff clean
- [x] Apply-progress closeout documented (commit `5081a67`)
- [x] Archive closed (this report)