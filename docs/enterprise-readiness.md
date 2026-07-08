# Enterprise Readiness Checklist

This project is healthy for a small advanced team. Enterprise readiness means making operations, security, governance, memory, and recovery repeatable without turning the repo into bureaucracy.

## Quick path

1. Run the current health check:
   ```powershell
   .\scripts\system_health.ps1
   ```
2. Check the priority table below.
3. Promote only one small work item at a time.
4. Keep each implementation slice reviewable: target <=400 changed lines, hard stop >600 unless explicitly justified.

## Current baseline

| Area | Current state | Enterprise gap |
|------|---------------|----------------|
| CI | GitHub Actions is green on Python 3.12 and 3.13. | Add proactive failure alerts. |
| Runner | Self-hosted Windows runner runs as an Automatic service. | Add scheduled health monitoring and recovery notes. |
| Health | `scripts/system_health.ps1` gives manual system status. | Run it automatically and record history. |
| Memory | Engram/SDD memory policy exists. | Add periodic review cadence and stale-memory triage. |
| Follow-ups | Follow-up audit exists and has no urgent blockers. | Keep a single live follow-up register. |
| Drift detection | Active change exists with review-budget guardrail. | Continue only via small, tested slices. |

## Priority 0 — non-negotiable operating discipline

These are required before calling a change done.

- [ ] `git status` is clean or intentionally dirty with a documented reason.
- [ ] Relevant tests pass locally.
- [ ] CI is green after push.
- [ ] `scripts/system_health.ps1` reports runner service healthy.
- [ ] Important decisions, bug fixes, and gotchas are saved to memory.
- [ ] Follow-ups are either closed, promoted, or explicitly deferred.
- [ ] The diff is reviewable: target <=400 changed lines, hard stop >600 without explicit exception.

## Priority 1 — operations and alerting

Goal: failures should find us before users do.

- [ ] Add a scheduled runner health check.
- [ ] Add CI failure notification path.
- [ ] Add stale-green alert when no successful CI run exists after a threshold.
- [ ] Document incident response: symptom, diagnosis, fix, prevention.
- [ ] Record recent health-check result history.

## Priority 2 — security baseline

Goal: secrets and supply chain mistakes should be hard to miss.

- [ ] Enable or document secret scanning.
- [ ] Define token rotation rules for GitHub, OpenAI, OpenCode, and runner credentials.
- [x] Add dependency update policy. See `docs/dependency-updates.md`.
- [ ] Add lightweight SAST/security scan for changed code.
- [ ] Require extra review for changes touching secrets, runner setup, filesystem access, auth, or external command execution.

## Priority 3 — governance of change

Goal: every change should be understandable, reversible, and auditable.

- [ ] Add a project Definition of Done.
- [ ] Add session start/close checklist.
- [ ] Add release checklist.
- [ ] Add changelog or release notes process.
- [ ] Use ADRs for durable architecture decisions.
- [ ] Keep SDD/OpenSpec active only when it guides real current work.

## Priority 4 — quality and verification

Goal: prevent regressions without testing everything blindly.

- [ ] Add smoke test for CLI installation and basic commands.
- [ ] Add tests for `scripts/system_health.ps1` output expectations where practical.
- [ ] Define minimum regression test set for drift-detection changes.
- [ ] Keep bug fixes paired with regression tests.
- [ ] Document supported platforms and Python versions.

## Priority 5 — observability

Goal: system state should be easy to inspect in one minute.

- [ ] Keep the lightweight health command as the source of truth.
- [ ] Add CI status, runner status, active specs, follow-ups, and memory hygiene to one dashboard view.
- [ ] Avoid a large dashboard until the manual health workflow proves stable.
- [ ] Add structured logs only where they answer real operational questions.

## Priority 6 — AI and memory governance

Goal: AI should remember useful context and forget stale noise.

- [ ] Run memory maintenance on a regular cadence.
- [ ] Separate active decisions from historical notes.
- [ ] Promote only validated follow-ups into current work.
- [ ] Mark stale SDD artifacts as historical instead of letting agents reopen them silently.
- [ ] Save important user constraints and workflow conventions.

## Priority 7 — release and recovery

Goal: the project should be restorable on another machine.

- [ ] Document how to rebuild the runner service.
- [ ] Back up critical Codex/OpenCode/Engram configuration.
- [ ] Document disaster recovery steps.
- [ ] Tag stable releases.
- [ ] Define rollback strategy for shipped changes.

## Definition of Done

A slice is done when:

- [ ] The intended behavior or documentation outcome is complete.
- [ ] Local verification relevant to the slice passed.
- [ ] CI passed after push.
- [ ] Health check confirms runner/CI visibility.
- [ ] Memory was updated for any non-obvious decision, bug fix, or discovery.
- [ ] Follow-ups are explicit and not hidden in chat.
- [ ] The change stayed inside review budget or has a documented exception.

## Next recommended slices

| Slice | Why | Size target |
|-------|-----|-------------|
| Session checklist | Standardizes how agents start and close work. | Docs-only, <150 LOC |
| Runner alerting | Converts manual health into proactive operations. | Small script/workflow, <300 LOC |
| Secret/dependency baseline | Raises enterprise security posture. | Config/docs, <300 LOC |
| Drift-detection micro-slice | Continues product evolution safely. | Code+tests, <=400 LOC |

## Anti-goals

- Do not build a large dashboard before the simple health command is trusted.
- Do not convert every old follow-up into active work.
- Do not expand SDD docs just to look enterprise.
- Do not merge large refactors without slicing and review-budget proof.
