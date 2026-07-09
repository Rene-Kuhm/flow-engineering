# System Health

Use this as the lightweight dashboard for the project. It answers four
questions: is the runner alive, is CI green, what SDD/follow-up work is active,
and is memory helping instead of adding noise.

## Quick command

```powershell
.\scripts\system_health.ps1
```

For offline structure checks without GitHub CLI calls, use:

```powershell
.\scripts\system_health.ps1 -SkipGitHub
```

GitHub also runs `health-monitor` every six hours. It fails visibly if the
latest `main` tests run is not green or if the latest green run is older than
the configured stale threshold.

The current repository cannot use GitHub-hosted runners because the account
billing gate prevents those jobs from starting. Runner-down detection can run
outside GitHub Actions through `scripts/runner_watchdog.ps1`; the manual health
command remains the one-minute operator dashboard.

## Last verified status

Last checked: 2026-07-09.

| Check | Result | Evidence |
|---|---|---|
| Runner service | Healthy | `actions.runner.Rene-Kuhm-flow-engineering.TECNODESPEGUE-flow-engineering` is `Running` / `Automatic` |
| Startup fallback | Removed | `flow-engineering-actions-runner.cmd` does not exist in Startup |
| CI | Green | `tests` run `28995468222` passed on `main` for release evidence `e296eba` |
| Scheduled monitor | Green | `health-monitor` run `28996019265` passed on `main` |

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

- self-hosted runner can start the monitor job;
- latest completed `main` push run for the `tests` workflow is successful;
- latest green `main` tests run is not older than `HEALTH_MAX_CI_AGE_HOURS`.

This workflow currently uses the self-hosted runner because GitHub-hosted jobs
are blocked by account billing. That means it verifies CI freshness and runner
reachability by successfully starting on the runner. A fully out-of-band
runner-down alert can be handled outside GitHub Actions with
`scripts/runner_watchdog.ps1`; see `docs/runner-watchdog.md`. The default
`GITHUB_TOKEN` cannot list repository runners through the runner API, so the
monitor does not call that endpoint.

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
