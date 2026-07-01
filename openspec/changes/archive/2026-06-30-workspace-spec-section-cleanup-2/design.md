# Design: workspace-spec-section-cleanup-2

## Scope

Closed-box doc cleanup: three text replacements in `openspec/specs/workspace/spec.md` only.

## Edit recipe

1. §2 boundary stress test: replace TUI framing with shipped Rich dashboard framing.
2. §4.1 graph arrow: replace `Phase 5 (future)` with `Phase 5 (shipped)`.
3. §4.1 dependency note: replace future-tense dependency wording with shipped/current dependency wording.

## Verification gates

- The three stale strings are absent.
- The three expected replacement strings are present.
- Existing Source lines remain present.
- AC9 byte-identical guard passes.
- `openspec/changes/v1.1-followups/` remains untouched/untracked.

## Rollback

`git revert HEAD` restores the doc-only cleanup.
