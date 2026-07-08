# Memory Maintenance Policy

This project uses memory to reduce repeated context, not to preserve every old
thought forever. Keep memory useful by promoting only live decisions,
re-verifying stale claims, and treating archived SDD commentary as historical
unless it is explicitly re-promoted.

## Quick path

1. Start from the latest session summary and `docs/follow-up-audit.md`.
2. Promote only items that still affect CI, correctness, reviewer load, or the
   next planned slice.
3. Re-check code/tests before trusting old memory.
4. Keep the next drift-detection slice below the review budget.

## Maintenance rules

| Area | Rule |
|---|---|
| Engram memories | Use as orientation. Verify against current files before acting. |
| Archived SDD changes | Historical by default. Re-promote only through `docs/follow-up-audit.md` or a new proposal. |
| Session summaries | Keep them concise: goal, discoveries, accomplished work, next step, relevant files. |
| Old warnings | Drop unless they still block CI, spec parity, or the next concrete slice. |
| Token use | Search memory/code first; avoid loading broad docs or many files without a specific question. |

## Monthly audit checklist

- [ ] Latest `main` CI is green.
- [ ] Runner service is `Running` and `Automatic`.
- [ ] `docs/follow-up-audit.md` still reflects the current next slice.
- [ ] No completed OpenSpec change is left active outside `openspec/changes/archive/`.
- [ ] New memories are actionable and not duplicates of stale notes.
- [ ] Any `needs_review` memory is verified before being used.

## Promotion test

Promote a memory or archived follow-up only if this sentence is true:

> If we ignore this, the next small slice becomes riskier, harder to review, or
> less correct.

If the sentence is false, leave it archived.
