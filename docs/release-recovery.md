# Release and Recovery

Use this guide when preparing a stable release, rebuilding the self-hosted
runner, or recovering from a bad change. Recovery work takes priority over new
features.

## Release checklist

Before tagging a release:

```powershell
git status --short
.\scripts\system_health.ps1
uv run ruff check src tests
uv run ruff check --select S102,S105,S106,S107,S108,S301,S302,S303,S304,S305,S306,S307,S308,S310,S312,S313,S314,S315,S316,S317,S318,S319,S321,S323,S501,S502,S503,S504,S505,S506,S507,S508,S509,S601,S602,S604,S605,S606,S608,S609,S610,S611,S612 src scripts
uv run mypy src
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 --basetemp .pytest_tmp
```

Confirm:

- [ ] Working tree is clean.
- [ ] Main CI is green after the last push.
- [ ] Runner service is `Running` and `Automatic`.
- [ ] Enterprise readiness checklist has no surprise blocker for the release.
- [ ] Security-sensitive changes were reviewed with `docs/security-baseline.md`.
- [ ] Follow-ups are explicit and not hidden in chat.

Tag only after the checklist passes:

```powershell
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

## Runner rebuild

Use an elevated PowerShell session.

```powershell
$repo = "Rene-Kuhm/flow-engineering"
$runnerRoot = "C:\actions-runner-flow-engineering"

Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*actions-runner-flow-engineering*" -or $_.CommandLine -like "*Runner.Listener*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

cd $runnerRoot

$removeToken = gh api -X POST "repos/$repo/actions/runners/remove-token" --jq .token
.\config.cmd remove --token $removeToken

$token = gh api -X POST "repos/$repo/actions/runners/registration-token" --jq .token
.\config.cmd --unattended --url "https://github.com/$repo" --token $token --name "$env:COMPUTERNAME-flow-engineering" --work _work --labels "self-hosted,Windows,X64,flow-engineering" --replace --runasservice

Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\flow-engineering-actions-runner.cmd" -Force -ErrorAction SilentlyContinue

Get-Service | Where-Object { $_.Name -like "actions.runner.*" } |
  Select-Object Status,StartType,Name,DisplayName
```

Expected result:

- service status is `Running`;
- start type is `Automatic`;
- startup fallback file does not exist;
- `.\scripts\system_health.ps1` reports the runner and latest CI visibility.

## Disaster recovery

When the repo or runner state is uncertain:

| Step | Action |
|------|--------|
| 1 | Stop new feature work. |
| 2 | Capture `git status --short`, latest CI run URL, runner service status, and current branch. |
| 3 | If credentials may be exposed, rotate them before cleanup. |
| 4 | Restore repository state with `git fetch origin` and a deliberate branch/reset plan. |
| 5 | Rebuild the runner only if service health or registration is suspect. |
| 6 | Re-run CI and `.\scripts\system_health.ps1`. |
| 7 | Save the incident cause and mitigation to memory. |

Do not rewrite shared history unless the incident explicitly requires secret
removal and the recovery plan is approved.

## Rollback strategy

| Situation | Preferred rollback |
|-----------|--------------------|
| Bad unpushed local change | `git restore` or `git reset --hard` after confirming the target files. |
| Bad pushed commit on `main` | `git revert <sha>` and push a corrective commit. |
| Bad release tag | Create a new patch tag after reverting; do not move published tags silently. |
| Bad dependency update | Revert the dependency PR or pin the previous compatible version. |
| Runner registration issue | Remove and re-register the runner service with fresh GitHub tokens. |

## Backups to preserve

Keep enough local state to rebuild the system on another machine:

- repository remote URL and branch strategy;
- GitHub runner install path: `C:\actions-runner-flow-engineering`;
- Codex/OpenCode configuration locations used by the operator;
- Engram project memory and session summaries;
- dependency lockfile: `uv.lock`;
- release tags and CI run URLs for stable baselines.
