# Engineering Quality Gates

This project is healthy when `main` stays green, SDD artifacts explain decisions without becoming bureaucracy, and drift-detection changes remain small enough to review honestly.

## Quick path

1. Keep CI green on `main` before starting the next slice.
2. Keep each SDD slice under the review budget.
3. Archive completed changes immediately.
4. Prefer one clear architectural seam over broad “while we are here” refactors.

## Runner operations

The current self-hosted runner lives at:

```text
C:\actions-runner-flow-engineering
```

Current non-admin fallback:

```text
C:\Users\insyd\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\flow-engineering-actions-runner.cmd
```

That startup script restarts the runner after user login. It is not a Windows Service. For a real service, open PowerShell as Administrator and run:

```powershell
$repo = "Rene-Kuhm/flow-engineering"
$runnerRoot = "C:\actions-runner-flow-engineering"
$token = gh api -X POST "repos/$repo/actions/runners/registration-token" --jq .token

cd $runnerRoot
.\config.cmd remove --token (gh api -X POST "repos/$repo/actions/runners/remove-token" --jq .token)
.\config.cmd --unattended --url "https://github.com/$repo" --token $token --name "$env:COMPUTERNAME-flow-engineering" --work _work --labels "self-hosted,Windows,X64,flow-engineering" --replace --runasservice
```

Verify:

```powershell
gh run list --repo Rene-Kuhm/flow-engineering --limit 5
Get-Service | Where-Object { $_.Name -like "actions.runner.*" }
```

## SDD anti-bureaucracy rules

| Rule | Decision |
|---|---|
| Planning docs | Write only what changes reviewer/product understanding. Do not repeat implementation details already obvious from code. |
| Completed changes | Archive immediately after verify passes. No active completed folders. |
| Specs | Sync only stable cross-version behavior into `openspec/specs/`. Keep temporary reasoning in archived change docs. |
| Tasks | Tasks must map to reviewable work units, not file-by-file busywork. |
| Verify reports | Include evidence and risk, not prose theater. |

## Drift-detection slice policy

Every future drift-detection slice must satisfy this before implementation:

- One architectural seam only.
- Target review size: ≤400 changed lines.
- Hard stop: >600 changed lines requires a new chained slice before code continues.
- No mixed feature + refactor slice.
- Regression gates named before touching production code.
- Strict TDD remains RED → GREEN → REFACTOR.

Good slice shape:

```text
Extract one protocol/helper + tests + unchanged behavior proof.
```

Bad slice shape:

```text
Extract protocols, change CLI output, rewrite persistence, and update docs in one PR.
```

## Checklist before opening a PR

- [ ] `main` was green before the branch started.
- [ ] Diff is under the 400-line review budget, or explicitly chained.
- [ ] SDD artifacts are short and decision-focused.
- [ ] Tests are with the behavior they verify.
- [ ] Archive/spec sync is included only when the change is complete.
