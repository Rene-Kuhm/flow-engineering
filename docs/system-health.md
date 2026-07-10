# System Health

Use this as the lightweight dashboard for the project. It answers four
questions: is hosted CI green, what SDD/follow-up work is active,
and is memory helping instead of adding noise.

## Quick command

```powershell
.\scripts\system_health.ps1
```

For offline structure checks without GitHub CLI calls, use:

```powershell
.\scripts\system_health.ps1 -SkipGitHub
```

The `tests` workflow uses GitHub-hosted Windows runners for both pushes and pull
requests. This keeps untrusted pull-request workflow changes away from the
owner's machine. The repository does not require or target a self-hosted runner.
The manual health command remains the one-minute operator dashboard.

## Last verified command set

Last checked manually: 2026-07-09. Treat this section as the operator
evidence shape, not as the source of truth for the latest run id. The live
source of truth is always `scripts/system_health.ps1` plus the current GitHub
Actions run list.

| Check | Result | Evidence |
|---|---|---|
| CI | Green | Latest `tests` run on `main` succeeds in `scripts/system_health.ps1` |
| Workflow runners | Hosted-only | PR-triggerable jobs use an audited GitHub-hosted label. |

Expected healthy state:

| Check | Healthy value |
|---|---|
| Latest CI | most recent `main` run succeeds |
| Active OpenSpec changes | only intentional in-progress work |
| Follow-up audit | no urgent blocker unless explicitly promoted |

## Hosted CI health

```powershell
gh run list --repo Rene-Kuhm/flow-engineering --limit 5
```

If CI fails, inspect the latest failed run before changing code:

```powershell
gh run view <run-id> --log-failed
```

## Memory health

Use `docs/memory-maintenance.md` before promoting old Engram or SDD context.
The rule is simple: memory guides the search, current code and tests prove the
claim.

## Next-slice guardrail

Future drift-detection work stays small:

- target: <=400 changed lines
- hard stop: >600 changed lines
- one behavior-preserving seam per slice
- tests with the behavior they verify
