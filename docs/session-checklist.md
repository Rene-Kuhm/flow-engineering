# Session Checklist

Use this checklist at the start and end of every meaningful work session. It keeps
agent work repeatable without adding heavy process.

## Start of session

Run this before changing files:

```powershell
git status --short
.\scripts\system_health.ps1
gh pr list --repo Rene-Kuhm/flow-engineering --state open --limit 10
```

Confirm:

- [ ] The working tree is clean, or the dirty files are understood.
- [ ] The runner service is `Running` and `Automatic`.
- [ ] The latest relevant CI run is green, or the failure is the current task.
- [ ] Open PRs are known before starting new work.
- [ ] Active follow-ups come from `docs/follow-up-audit.md`, not from old archived noise.
- [ ] Any SDD work stays inside the review budget: target <=400 changed lines, hard stop >600 without exception.

## During session

Keep each slice narrow:

- [ ] Work on one reviewable outcome at a time.
- [ ] Pair bug fixes with regression tests when behavior changes.
- [ ] Update docs only when they help future operation or review.
- [ ] Save non-obvious decisions, bug fixes, and gotchas to memory.
- [ ] Do not promote archived SDD follow-ups unless current evidence confirms they still matter.

## End of session

Run this before calling the work complete:

```powershell
git status --short
.\scripts\system_health.ps1
```

Confirm:

- [ ] Relevant local verification passed.
- [ ] CI is green after any push.
- [ ] The final health check shows runner and CI visibility.
- [ ] Memory has the important outcome and gotchas.
- [ ] Follow-ups are explicit: closed, promoted, or deferred.
- [ ] The next step is small enough for one reviewable slice.

## If something is red

Do not keep building on top of a bad baseline.

| Symptom | First action |
|---------|--------------|
| Runner is stopped | Check the `actions.runner.*` Windows service before touching CI code. |
| CI is failing | Inspect the failing run logs before changing implementation. |
| Working tree is dirty unexpectedly | Stop and identify every file before editing more. |
| Old follow-up looks important | Verify it against current code/docs before promoting it. |
| Slice is growing past budget | Split the work before adding more changes. |

## Source of truth

- `docs/enterprise-readiness.md` — enterprise maturity roadmap.
- `docs/system-health.md` — runner and CI health routine.
- `docs/follow-up-audit.md` — current follow-up policy.
- `docs/memory-maintenance.md` — memory hygiene policy.
