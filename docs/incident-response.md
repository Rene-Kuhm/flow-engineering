# Incident Response

Use this guide when CI, the self-hosted runner, release flow, or drift-detection behavior fails. The goal is to restore service, capture the cause, and prevent repeat failures without adding bureaucracy.

## Quick path

1. Identify the failing surface: CI, runner, release, CLI behavior, memory/SDD, or documentation drift.
2. Capture evidence before changing anything: run ID, command output, log excerpt, commit SHA, and timestamp.
3. Apply the smallest safe fix.
4. Verify with the narrowest relevant command first, then CI or health monitor when applicable.
5. Record prevention: test, doc update, monitor, or explicit deferred follow-up.

## Incident record template

| Field | Notes |
|---|---|
| Date/time | Use ISO date when possible. |
| Symptom | What failed from the operator/user perspective. |
| Impact | Who or what was blocked. |
| Evidence | Run IDs, logs, commands, screenshots, or error snippets. |
| Root cause | The smallest proven explanation. Avoid guesses. |
| Fix | Commit SHA, command, or config change. |
| Verification | Local command, CI run, health-monitor run, or manual check. |
| Prevention | Regression test, docs update, monitor, or accepted risk. |

## Severity guide

| Severity | Meaning | Response |
|---|---|---|
| SEV1 | Main workflow is blocked or data/security risk exists. | Stop feature work, fix or rollback first. |
| SEV2 | CI, runner, or release path is degraded but workaround exists. | Fix in the next operational slice. |
| SEV3 | Documentation, follow-up, or memory drift with no immediate blocker. | Record and batch with maintenance work. |

## Default response by surface

| Surface | First check | Verification |
|---|---|---|
| Runner | `Get-Service -Name "actions.runner.*"` | `.\scripts\system_health.ps1` and `health-monitor` |
| CI | `gh run view <run-id> --log-failed` | rerun or push fix, then wait for green `tests` |
| Security | Confirm secret exposure or risky surface before editing | rotate/revoke if needed, then document in `SECURITY.md` if policy changed |
| SDD/memory | Check current code/tests before trusting old notes | update follow-up audit or Engram with only validated facts |
| Release | Follow `docs/release-recovery.md` | tag/release only after CI and health evidence |

## Recent incident examples

| Date | Symptom | Root cause | Fix | Verification |
|---|---|---|---|---|
| 2026-07-09 | `health-monitor` failed with `function not defined: completed/0`. | Windows PowerShell/native argument quoting broke the `gh --jq` filter. | Removed `--jq`; parsed JSON in PowerShell. | `tests` run `28991760348` and `health-monitor` run `28992222994` passed. |
| 2026-07-09 | `health-monitor` failed parsing `createdAt`. | Windows PowerShell 5.1 returns `ConvertFrom-Json` dates as strings, unlike PowerShell 7. | Parsed dates explicitly with `InvariantCulture`. | `health-monitor` run `28992222994` passed. |

## Prevention rules

- Do not patch CI from memory; inspect logs first.
- Keep Windows runner scripts PowerShell-native unless bash is explicitly installed.
- Avoid `gh --jq` in Windows runner workflows when PowerShell can parse JSON directly.
- Every operational fix needs evidence: commit SHA plus CI or health-monitor run ID.
- If the fix discovers a repeatable gotcha, update this file or the relevant runbook.



