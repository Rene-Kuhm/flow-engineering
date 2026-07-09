# Operating Manual

Use this manual as the first stop for agents and maintainers. It does not
replace the detailed docs; it tells you what to read, in what order, and what
quality bar to enforce before changing the project.

## Quick path

1. Start with `docs/session-checklist.md`.
2. Run `.\scripts\system_health.ps1`.
3. Check `docs/follow-up-audit.md` before promoting old work.
4. Pick one reviewable slice.
5. Verify locally, wait for CI, update memory, and leave the next step explicit.

## Quality bar

| Rule | Standard |
|---|---|
| Design | Expert-level tradeoffs before implementation. No accidental architecture. |
| Scope | One clear outcome per slice. Target <=400 changed lines; hard stop >600. |
| Tests | Behavior changes need tests in the same work unit. Bug fixes need regression coverage. |
| Docs | Add docs only when they reduce future operator or reviewer load. |
| Evidence | Claims need current code, command output, CI, or health-check evidence. |
| Memory | Save non-obvious decisions, fixes, gotchas, and user constraints. |

## Read this first

| Need | Source |
|---|---|
| Start or close a work session | `docs/session-checklist.md` |
| Current system health | `docs/system-health.md` |
| Enterprise readiness status | `docs/enterprise-readiness.md` |
| Definition of Done | `docs/change-governance.md` |
| Drift-detection slice rules | `docs/engineering-quality-gates.md` |
| Live debt and follow-ups | `docs/follow-up-audit.md` |
| Memory hygiene | `docs/memory-maintenance.md` |
| Project vocabulary | `docs/glossary.md` |

## Agent context loading

Use this when MiniMax, Codex, or another agent needs focused context. Load the
smallest set that answers the task; do not copy these files into parallel docs.

| Agent need | Load |
|---|---|
| Understand the project shape | `docs/operating-manual.md`, `README.md`, `docs/glossary.md` |
| Choose commands for this or another stack | `docs/stack-tooling-policy.md`, then the target repository's manifests and lockfiles |
| Design a change | `docs/change-governance.md`, `docs/engineering-quality-gates.md`, relevant `docs/adr/`, relevant `openspec/specs/` |
| Work on drift detection | `docs/drift-detection-regression-set.md`, `openspec/changes/drift-detection/`, `docs/follow-up-audit.md` |
| Touch CI, runner, or operations | `docs/system-health.md`, `docs/runner-watchdog.md`, `docs/incident-response.md`, `docs/release-recovery.md` |
| Use memory or old SDD context | `docs/memory-maintenance.md`, `docs/follow-up-audit.md`, then verify current code/tests |
| Close a session | `docs/session-checklist.md`, `docs/change-governance.md` |

## Architecture and decisions

| Topic | Source |
|---|---|
| Durable architecture decisions | `docs/adr/` |
| Active SDD change | `openspec/changes/drift-detection/` |
| Shipped capability specs | `openspec/specs/` |
| Historical design context | `openspec/changes/archive/` |
| Project SDD bootstrap | `sdd-init/flow-engineering.md` |
| Skill registry | `.atl/skill-registry.md` |

Archived OpenSpec content is history, not backlog. Promote it only when current
code, tests, and product intent prove it still matters.

## Operating commands

| Task | Command |
|---|---|
| Check project health | `.\scripts\system_health.ps1` |
| Check runner watchdog | `.\scripts\runner_watchdog.ps1 -Json` |
| Run monthly maintenance | `.\scripts\monthly_maintenance.ps1` |
| Install monthly task | `.\scripts\install_monthly_maintenance_task.ps1` |
| Set alert webhook | `.\scripts\set_runner_watchdog_webhook.ps1` |
| Test alert webhook | `.\scripts\runner_watchdog.ps1 -WebhookTest` |

For local pytest runs on Windows, avoid shared temp cleanup issues:

```powershell
$base = Join-Path $env:TEMP "flow-engineering-pytest-$PID"
uv run pytest --basetemp="$base"
```

## Known operational gotchas

| Gotcha | Response |
|---|---|
| GitHub-hosted runners are blocked by billing gate | Use the self-hosted Windows runner and verify it with `system_health.ps1`. |
| Runner-down cannot be detected by a workflow that never starts | Use `runner_watchdog.ps1` through Task Scheduler or an external monitor. |
| Codecov can slow or block the single runner | Keep upload steps time-bounded and non-blocking. |
| PowerShell JSON/JQ behavior differs across versions | Prefer explicit PowerShell JSON parsing in workflows. |
| Old SDD notes can look like live debt | Check `docs/follow-up-audit.md` before acting. |
| Pytest shared temp cleanup can fail on Windows | Use an isolated `--basetemp`. |

## What not to do

- Do not start feature work on a red or unknown baseline.
- Do not treat archived specs as automatic backlog.
- Do not mix broad refactors with product changes.
- Do not bypass tests to make a slice look finished.
- Do not duplicate docs just to look more “enterprise”.
- Do not claim external alerting is active until a real webhook is configured
  and verified with `-WebhookTest`.

## Done means

- The intended outcome is complete.
- Local verification relevant to the slice passed.
- CI passed after push when code, CI, scripts, or docs affecting operations changed.
- `.\scripts\system_health.ps1` still gives a healthy operating view.
- Important discoveries are saved to memory.
- Any remaining work is explicit, small, and not hidden in chat.

## Next product direction

The project is operationally solid. Future work should be product evolution,
especially small drift-detection slices that preserve behavior and improve
observability, maintainability, or correctness one seam at a time.
