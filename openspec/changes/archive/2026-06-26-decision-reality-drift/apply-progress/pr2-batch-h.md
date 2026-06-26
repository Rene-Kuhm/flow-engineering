<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr2-batch-h (Engram #134) -->

# Apply progress PR#2 batch H — decision-reality-drift

## Goal

SDD apply batch H of decision-reality-drift PR#2: T2.4 (sdd-verify SKILL.md Step 6a) + T2.5 (CHANGELOG v0.3.0) + T2.6 (6 SKILL.md "Drift detection hook" sections).

## Branch / PR State

- Branch: `feature/decision-reality-drift-pr2-batch-h`
- Baseline (main HEAD at start): `a5a9719` (PR#4 squash merge)
- Final HEAD: `65ea92a`
- PR: https://github.com/Rene-Kuhm/flow-engineering/pull/5

## Commits (repo)

- `65ea92a` chore(release): CHANGELOG v0.3.0 entry (files: CHANGELOG.md, +20/-0)

## Runtime Side Effects (NOT in repo, NOT in PR)

- `~/.config/opencode/skills/sdd-verify/SKILL.md`: 5165 → 5917 bytes (+752) — Step 6a sub-step + Drift detection hook section
- `~/.config/opencode/skills/sdd-propose/SKILL.md`: 8141 → 8634 bytes (+493) — Drift detection hook section
- `~/.config/opencode/skills/sdd-design/SKILL.md`: 7649 → 8157 bytes (+508) — Drift detection hook section
- `~/.config/opencode/skills/sdd-tasks/SKILL.md`: 11686 → 12137 bytes (+451) — Drift detection hook section
- `~/.config/opencode/skills/sdd-apply/SKILL.md`: 12086 → 12546 bytes (+460) — Drift detection hook section
- `~/.config/opencode/skills/sdd-archive/SKILL.md`: 7338 → 7763 bytes (+425) — Drift detection hook section

## LOC Delta (repo)

- `CHANGELOG.md`: +20/-0
- **Total**: +20/-0 = +20 net (repo only)

## Runtime Bytes Delta

- 6 SKILL.md files modified, total +3089 bytes
- All under respective file-size budgets (sdd-verify 5917 < 6000 byte ceiling).

## Test Delta

- 385 passing (unchanged — docs-only batch, verified via `uv run pytest -x --tb=short` in 2.28s)

## Risks / Blockers

- **Minor**: sdd-verify Drift detection hook was tightened after first draft pushed file to 6048 bytes (over the ≤6000 budget). Final size 5917 bytes — under budget.
- **Note**: found and cleared stale `git rebase-merge` state from batch G's `feature/decision-reality-drift-pr2` branch (now merged via PR#4 squash). The `git rebase --abort` to clear stale state temporarily switched HEAD to `feature/decision-reality-drift-pr2`; recovered by checking out `feature/decision-reality-drift-pr2-batch-h` and re-applying the CHANGELOG edit. No data loss.

## Drift Detection Hook Content (high-level)

Each of the 6 SKILL.md files (`sdd-propose`, `sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`) gained a new section `## Drift detection hook` containing:

- Reference to the 6 drift classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`) plus the terminal `unable_to_verify` state.
- The `flow drift <change>` invocation point (REQ-10).
- The exit-code contract 0/1/2 (REQ-11) — 2 wins over 1.
- The 8 counter names (REQ-12) — names stable across changes.
- Cross-reference to `sdd-verify` Step 6a for sub-step placement.

`sdd-verify` SKILL.md also gained Step 6a: "Run `flow drift <change>` and surface findings before declaring green" + the 0/1/2 contract from REQ-11.

## CHANGELOG v0.3.0 Entry

(See repo `CHANGELOG.md` lines 7-26; corrected typo + BDD count via PR #6.)

```markdown
## [0.3.0] - 2026-06-26

### Added
- `flow drift <change>` subcommand — scans Engram observations for binding drift and reports one of six classes per REQ-12. Exits 0/1/2 per REQ-11.
- `flow watch --drift` flag — daemon subscribes to apply-progress writes and re-runs scan_change on merged status (REQ-15, REQ-16).
- 8 new drift_*_total observability counters persisted alongside flow metrics JSONL.

### Closed (W2/W3 carry-forwards)
- W2 — REQ-8 counter reconciliation.
- W3 — REQ-3 empty-block BDD.

### Tests
- 385 / 385 tests passing.
- 63 BDD scenarios across 12 feature files (req1..req9 + req15_drift_daemon).
```

## Post-Archive Follow-ups (carried forward in archive-report)

- **W4** BDD shortfall — owner: `drift-hardening`.
- **W5** REQ-15 event-log mechanism drift — owner: `drift-hardening`.
- **W6** REQ-15 still-valid silence drift — owner: `drift-hardening`.
- **W8** Spec/design dataclass drift — owner: spec delta sync or `drift-hardening`.

## TDD Cycle Evidence

| Task | Type | TDD | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| T2.4 (sdd-verify Step 6a) | docs (runtime) | N/A | ➖ Docs | ➖ Docs | ✅ Final size 5917 bytes |
| T2.5 (CHANGELOG) | docs (repo) | N/A | ➖ Docs | ➖ Docs | ✅ Typo fix in PR #6 |
| T2.6 (6 SKILL.md hook) | docs (runtime) | N/A | ➖ Docs | ➖ Docs | ✅ All 6 files under byte budget |

## Files Touched

- `CHANGELOG.md` — v0.3.0 entry (+20 lines).
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — runtime updates (+3089 bytes total).

**Session**: insyd-2026-06-26-batch-h
**Topic**: sdd/decision-reality-drift/apply-progress-pr2-batch-h
**Engram**: #134
**Next**: sdd-verify PR#2 (validate against spec/design/tasks) → sdd-archive decision-reality-drift (close the change) → change #3: vector-semantic-search (/sdd-new)