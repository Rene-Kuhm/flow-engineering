# System Health

Use this as the lightweight dashboard for the project. It answers four
questions: is the runner alive, is CI green, what SDD/follow-up work is active,
and is memory helping instead of adding noise.

## Quick command

```powershell
.\scripts\system_health.ps1
```

GitHub also runs `health-monitor` every six hours. It fails visibly if the
latest `main` tests run is not green or if the latest green run is older than
the configured stale threshold.

The current repository cannot use GitHub-hosted runners because the account
billing gate prevents those jobs from starting. Until billing or an external
monitor is available, runner-down detection remains manual through this health
command.

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

This workflow currently uses the self-hosted runner because GitHub-hosted jobs
are blocked by account billing. That means it verifies CI freshness and runner
reachability when the runner is alive, but a fully out-of-band runner-down alert
requires GitHub-hosted billing to be fixed or an external monitor.

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
