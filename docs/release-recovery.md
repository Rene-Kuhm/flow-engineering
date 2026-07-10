# Release and Recovery

Use this guide when preparing a stable release or recovering from a bad change.
Recovery work takes priority over new features.

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
- [ ] Hosted `tests` CI is green on the supported Python matrix.
- [ ] Enterprise readiness checklist has no surprise blocker for the release.
- [ ] Security-sensitive changes were reviewed with `docs/security-baseline.md`.
- [ ] Follow-ups are explicit and not hidden in chat.

Tag only after the checklist passes:

```powershell
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

## Disaster recovery

When repository state is uncertain:

| Step | Action |
|------|--------|
| 1 | Stop new feature work. |
| 2 | Capture `git status --short`, latest hosted CI run URL, and current branch. |
| 3 | If credentials may be exposed, rotate them before cleanup. |
| 4 | Restore repository state with `git fetch origin` and a deliberate branch/reset plan. |
| 5 | Re-run hosted CI and `.\scripts\system_health.ps1`. |
| 6 | Save the incident cause and mitigation to memory. |

Do not rewrite shared history unless the incident explicitly requires secret
removal and the recovery plan is approved.

## Rollback strategy

| Situation | Preferred rollback |
|-----------|--------------------|
| Bad unpushed local change | `git restore` or `git reset --hard` after confirming the target files. |
| Bad pushed commit on `main` | `git revert <sha>` and push a corrective commit. |
| Bad release tag | Create a new patch tag after reverting; do not move published tags silently. |
| Bad dependency update | Revert the dependency PR or pin the previous compatible version. |

## Backups to preserve

Keep enough local state to rebuild the system on another machine:

- repository remote URL and branch strategy;
- Codex/OpenCode configuration locations used by the operator;
- Engram project memory and session summaries;
- dependency lockfile: `uv.lock`;
- release tags and CI run URLs for stable baselines.
