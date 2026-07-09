# System Health

Use this as the lightweight dashboard for the project. It answers four
questions: is the runner alive, is CI green, what SDD/follow-up work is active,
and is memory helping instead of adding noise.

## Quick command

```powershell
.\scripts\system_health.ps1
```

GitHub also runs `health-monitor` every six hours on GitHub-hosted runners. It
fails visibly if the self-hosted runner is offline, if the latest `main` tests
run is not green, or if the latest green run is older than the configured stale
threshold.

Expected healthy state:

| Check | Healthy value |
|---|---|
| Runner service | `Running`, `Automatic` |
| Startup fallback | `False` |
| Latest CI | most recent `main` run succeeds |
| Active OpenSpec changes | only intentional in-progress work |
| Follow-up audit | no urgent blocker unless explicitly promoted |

## Scheduled health monitor

Workflow: `.github/workflows/health-monitor.yml`

The monitor checks:

- at least one online runner whose name contains `flow-engineering`;
- latest `main` push run for the `tests` workflow is `completed/success`;
- latest green `main` tests run is not older than `HEALTH_MAX_CI_AGE_HOURS`.

This workflow intentionally uses `ubuntu-latest`, not the self-hosted runner, so
runner outages are still detectable.

## Manual runner health

```powershell
Get-Service | Where-Object { $_.Name -like "actions.runner.*" } |
  Select-Object Status,StartType,Name,DisplayName
```

Expected service:

```text
actions.runner.Rene-Kuhm-flow-engineering.TECNODESPEGUE-flow-engineering
```

## Manual CI health

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
