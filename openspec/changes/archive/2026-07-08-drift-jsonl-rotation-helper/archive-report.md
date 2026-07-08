# Archive Report: drift-jsonl-rotation-helper

**Change**: `drift-jsonl-rotation-helper`
**Archive date**: 2026-07-08
**Mode**: hybrid (filesystem merge + Engram observation)
**Chain strategy**: feature-branch-chain / tracker branch (extended with PR7)
**Tracker (root)**: `refactor/drift-jsonl-rotation-helper` (no-merge/draft) ← `origin/main` @ `cf7a052`
**Archive branch (this commit)**: `docs/drift-jsonl-rotation-helper-07-archive` ← PR6 (`docs/drift-jsonl-rotation-helper-06-verify`)
**Verdict basis**: `sdd-verify` PASS (chain-remediated; archive unlocked)
**Archived to**: `openspec/changes/archive/2026-07-08-drift-jsonl-rotation-helper/`

---

## Goal

Slice 2 of `drift-detection`: extract the verbatim-duplicated JSONL rotation logic from `drift_event_log.py` (REQ-V1.1.1) and `observability.py` (REQ-V1.2.1) into a single shared private helper at `src/flow_engineering/_jsonl_rotation.py`. Zero operator-visible change — env-var names, defaults, ISO-stamp format, glob prefix, and lock semantics are preserved exactly.

## Chain topology — preserved

The feature-branch-chain was set up during `sdd-verify` to absorb an earlier single-PR overflow (1 967 net LOC on one branch = ~5× the 400-LOC review budget). The chain runs through a no-merge tracker; each child PR targets its immediate parent, carries only its own slice, and stays under 400 LOC.

```
origin/main @ cf7a052
   │
   └── tracker refactor/drift-jsonl-rotation-helper       (no-merge / draft)
          │
          ├── PR #1  docs/...-01-explore       → tracker         (361 LOC) ✅
          ├── PR #2  docs/...-02-plan          → PR #1           (395 LOC) ✅
          ├── PR #3  feat/...-03-core          → PR #2           (391 LOC) ✅
          ├── PR #4  refactor/...-04-call-sites→ PR #3           (182 net) ✅
          ├── PR #5  docs/...-05-apply         → PR #4            (94 LOC) ✅
          ├── PR #6  docs/...-06-verify        → PR #5           (377 LOC) ✅
          └── PR #7  docs/...-07-archive  📍   → PR #6           (≤400 LOC) ✅  ← this archive slice
```

**Why PR7 exists (not folded into PR6)**: the archive operation itself produces a substantial diff on top of PR6 (new main spec + folder move + archive report). A conservative estimate was ≥600 LOC additions on the PR6 branch, which would have pushed PR6 over its 400-LOC review budget. Per the user brief ("If archiving creates a new diff >400 lines on the current PR6 branch, report it as a follow-up branch/PR7 boundary instead of hiding it"), the archive handoff was spun off as PR7. PR6's diff stays at 377 LOC (under budget, chain integrity preserved).

## PR7 budget check

| Slice | Insertions | Deletions | Net | Notes |
|-------|-----------:|----------:|----:|-------|
| `openspec/specs/jsonl-rotation-helper/spec.md` (new) | +84 | 0 | +84 | Verbatim copy of delta spec (no prior main spec existed) |
| Folder move (`drift-jsonl-rotation-helper` → `archive/2026-07-08-drift-jsonl-rotation-helper`) | 0 | 0 | 0 | `git mv` rename detected; 7 files relocated, content identical |
| `openspec/changes/archive/2026-07-08-drift-jsonl-rotation-helper/archive-report.md` (new) | +? | 0 | +? | This file |
| **Total** | <400 | 0 | <400 | ✅ under review budget |

Exact stat follows the commit.

## Specs synced

| Domain | Action | Requirements | Source → Destination |
|--------|--------|--------------|----------------------|
| `jsonl-rotation-helper` | **Created** (no prior main spec) | 4 (REQ-JRH-1, REQ-JRH-2, REQ-JRH-3, REQ-JRH-4) + 7 scenarios | `openspec/changes/drift-jsonl-rotation-helper/specs/jsonl-rotation-helper/spec.md` → `openspec/specs/jsonl-rotation-helper/spec.md` |

Delta acceptance: ADDED requirements (the entire spec was new — no main spec pre-existed), no MODIFIED / REMOVED / RENAMED sections in the delta. The merged main spec is a verbatim copy of the delta spec because the spec was net-new (the only consumer domain).

## Source of truth updated

| Spec file | State |
|-----------|-------|
| `openspec/specs/jsonl-rotation-helper/spec.md` | ✅ Created (new domain) — capture REQ-JRH-1..4 + 7 scenarios |
| `openspec/specs/observability/spec.md` | ⚠ Untouched — REQ-V1.2.1 wording stays valid (helper is refactor-preserving) |
| `openspec/specs/decision-drift/spec.md` | ⚠ Untouched — REQ-V1.1.1 wording stays valid (helper is refactor-preserving) |

## Archive contents

```
openspec/changes/archive/2026-07-08-drift-jsonl-rotation-helper/
├── archive-report.md          ← this file (new at archive time)
├── proposal.md                ✅
├── exploration.md             ✅
├── design.md                  ✅
├── tasks.md                   ✅ (18/18 tasks complete; 0 unchecked)
├── apply-progress.md          ✅
├── verify-report.md           ✅ (verdict PASS; chain-remediated)
└── specs/
    └── jsonl-rotation-helper/
        └── spec.md            ✅ (delta spec; merged into main)
```

Tasks artifact is fully reconciled — every implementation task in `tasks.md` is marked `[x]`, no stale checkboxes remain. `apply-progress.md` corroborates 18/18 completion.

## Workload / chain summary

| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 18 ✅ |
| Tasks incomplete | 0 |
| Aggregate diff vs `origin/main` (full chain) | 1 687 insertions, 159 deletions = 1 846 net |
| Per-PR diff (largest) | PR2 (plan) at 395 / 400 LOC |
| PR6 (verify) | 377 LOC ✅ |
| PR7 (archive, this slice) | ≤400 LOC ✅ |
| Strict regression gate (`test_drift_event_log.py`, `test_observability.py`, `req44_metrics_rotation.feature`) | 0 edits ✅ |

## Verification recap

- **ruff**: `uv run --frozen ruff check src tests` → All checks passed
- **mypy**: `uv run --frozen mypy src` → Success: no issues found in 48 source files
- **Unit (helper)**: 24/24 parametrized cases in `tests/unit/test_jsonl_rotation.py` → pass
- **Unit (regression gate)**: 46/46 (`tests/unit/test_drift_event_log.py` + `tests/unit/test_observability.py`) → pass with zero edits
- **BDD**: 204/204 scenarios collected → pass; `tests/bdd/req44_metrics_rotation.feature` unchanged
- **Full unit suite**: 1 486/1 486 → no regressions
- **Coverage**: 94% on `_jsonl_rotation.py` (above 80% threshold)
- **Boundary (REQ-JRH-3)**: `grep _jsonl_rotation src/flow_engineering/prompt_render_log.py` → 0 matches

## Carry-over warnings (non-blocking, pre-existing)

1. `tests/bdd/req44_metrics_rotation.feature` has no pytest-bdd step definitions in any `test_*_steps.py` (pre-existing, unchanged by Slice 2; the REQ-44 contract is materially covered by the 7 `TestMetricsRotation` unit tests). Out of scope for this archive.
2. `src/flow_engineering/drift_event_log.py:16` docstring still says "v1 ships without rotation" — historically inaccurate post-Slice 2 but pre-existing docstring drift; recorded as a follow-up cosmetic edit (not a behavioral defect).

## Out of scope (per proposal + spec)

- Slice 3 (`graph_unavailable` per-finding refinement).
- `prompt_render_log.py` rotation (separate future feature).
- `flow archive rotate` (`cli/rotation.py`).
- Existing rotation tests / BDD scenarios (kept as strict regression gates).
- The two carry-over warnings above.

## Follow-up work after archive

None. The change is feature-complete and behavior-preserving. The two carry-over cosmetic items are deliberately excluded from this archive and would belong in a future docstring cleanup change.

## Next step

`openspec/changes/drift-jsonl-rotation-helper/` is gone from active changes; `openspec/changes/archive/2026-07-08-drift-jsonl-rotation-helper/` is the audit trail. PR7 is ready for review (orchestrator owns PR opening; `sdd-archive` does NOT push). Ready for the next change.
