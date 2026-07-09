# Runner Watchdog

Use this when you need a runner-down signal that does not depend on GitHub Actions starting successfully. It is designed for Windows Task Scheduler, Uptime Kuma push monitors, or any external scheduler that can run PowerShell.

## Quick path

Run a local check without GitHub API calls:

```powershell
./scripts/runner_watchdog.ps1 -SkipGitHub
```

Run the full check with GitHub CLI available:

```powershell
./scripts/runner_watchdog.ps1 -Repo Rene-Kuhm/flow-engineering -MaxCiAgeHours 24
```

Send alerts to a webhook when the watchdog finds a warning or critical state:

```powershell
$env:FLOW_RUNNER_ALERT_WEBHOOK = "https://example.invalid/webhook"
./scripts/runner_watchdog.ps1
```

## Exit codes

| Exit code | Meaning |
|---|---|
| `0` | All checks are OK or explicitly skipped. |
| `1` | Warning: the runner may be OK, but CI freshness or GitHub visibility needs attention. |
| `2` | Critical: the runner service is missing/unhealthy or latest tests are not green. |

## What it checks

| Check | Source | Why |
|---|---|---|
| Runner service | Windows service manager | Detects service missing, stopped, or not configured for Automatic start. |
| Latest `main` tests run | `gh run list` | Detects red or stale CI when GitHub CLI is available. |
| Webhook delivery | Optional `FLOW_RUNNER_ALERT_WEBHOOK` | Lets an external monitor receive the alert payload. |

## Install as a scheduled task

Preview the Task Scheduler command without registering anything:

```powershell
./scripts/install_runner_watchdog_task.ps1 -DryRun
```

Register the watchdog to run every 15 minutes:

```powershell
./scripts/install_runner_watchdog_task.ps1
```

For webhook alerts, set `FLOW_RUNNER_ALERT_WEBHOOK` as a user or machine environment variable before the task runs. Do not pass webhook secrets on the command line because Task Scheduler stores task arguments.

Use the helper interactively so the secret is not stored in shell history or task arguments:

```powershell
./scripts/set_runner_watchdog_webhook.ps1
```

Preview the change without writing the environment variable:

```powershell
./scripts/set_runner_watchdog_webhook.ps1 -WebhookUrl "https://your-alert-webhook.example/path" -DryRun
```

After setting the real webhook, send a controlled test payload:

```powershell
./scripts/runner_watchdog.ps1 -WebhookTest
```

Preview the payload without posting:

```powershell
./scripts/runner_watchdog.ps1 -WebhookTest -WebhookDryRun -Json
```

## Recommended schedule

Use Task Scheduler or an external monitor every 15 minutes. The task should run outside GitHub Actions; otherwise it cannot detect the case where the runner is down and no job starts.

Keep the task simple:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File C:/dev/proyects/flow-engineering/scripts/runner_watchdog.ps1
```

## Limitations

- This does not create a SaaS monitor by itself; it provides the health signal and optional webhook payload.
- Webhook secrets belong in machine environment variables or the scheduler secret store, not in the repository.
- If GitHub CLI is unavailable, the watchdog still checks the runner service and reports CI visibility as a warning unless `-SkipGitHub` is used.
