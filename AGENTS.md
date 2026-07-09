# Agent Operating Contract

This repository must be handled as an AI Engineering OS, not as a simple chatbot session. Agents must work from current evidence, keep changes reviewable, and prove outcomes before claiming completion.

## Quick path

1. Read `docs/operating-manual.md` first.
2. Load only the task-relevant context listed in its **Agent context loading** section.
3. Run `./scripts/system_health.ps1` before non-trivial work when the environment matters.
4. Plan the slice before editing.
5. Implement in small phases with tests and verification.
6. Save important decisions, gotchas, and outcomes to memory.

## Non-negotiable rules

| Area | Rule |
|---|---|
| Evidence | Do not agree with claims or mark work complete without checking code, docs, commands, CI, or health output. |
| Scope | Keep slices small and reviewable. Target <=400 changed lines; hard stop >600 unless explicitly justified. |
| Architecture | Make design tradeoffs explicit before implementation. No accidental architecture. |
| Tests | Behavior changes require tests in the same work unit. Bug fixes require regression coverage. |
| Security | Never print, commit, or expose secrets. Rotate any secret that becomes visible. |
| Docs | Document decisions only when they reduce future operator, reviewer, or agent load. |
| Memory | Persist non-obvious decisions, fixes, gotchas, and user constraints. |
| Completion | Do not say done until local verification and, when relevant, CI/health checks pass. |

## Working model

Agents should use:

- context engineering: load the smallest useful context, not the whole repo blindly;
- staged planning: understand, plan, implement, verify, document, summarize;
- specialized tools/skills when available: SDD, tests, security review, GitHub/CI, browser, and docs skills;
- project memory: recover prior decisions and save new ones;
- critical review: challenge assumptions and inspect diffs before shipping.

## Required project context

| Need | Load |
|---|---|
| Project entrypoint | `docs/operating-manual.md` |
| Vocabulary | `docs/glossary.md` |
| Definition of done | `docs/change-governance.md` |
| Quality gates | `docs/engineering-quality-gates.md` |
| Session workflow | `docs/session-checklist.md` |
| Live follow-ups | `docs/follow-up-audit.md` |
| Operations health | `docs/system-health.md`, `docs/runner-watchdog.md` |
| Memory hygiene | `docs/memory-maintenance.md` |

## Operational commands

```powershell
./scripts/system_health.ps1
./scripts/runner_watchdog.ps1 -Json
./scripts/runner_watchdog.ps1 -WebhookTest
```

For local pytest runs on Windows, use isolated temp storage:

```powershell
$base = Join-Path $env:TEMP "flow-engineering-pytest-$PID"
uv run pytest --basetemp="$base"
```

## What not to do

- Do not start from stale memory without checking the current repo.
- Do not treat archived OpenSpec changes as live backlog.
- Do not mix broad refactors with product changes.
- Do not add process/docs just to look enterprise.
- Do not bypass tests or CI to make progress look faster.
- Do not leak Slack webhooks, GitHub tokens, or local credentials.

## Completion checklist

- [ ] Current state was understood before editing.
- [ ] The slice had a clear plan and bounded scope.
- [ ] Tests or relevant verification passed.
- [ ] CI passed when code, scripts, CI, or operational docs changed.
- [ ] Health checks still show a usable system view.
- [ ] Decisions and gotchas were saved to memory.
- [ ] Remaining work is explicit and small.
