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
| CI | GitHub Actions is green on Python 3.12 and 3.13. | Keep failure signals visible and investigated. |
| Runner | Self-hosted Windows runner runs as an Automatic service. | Add out-of-band runner-down alert after GitHub-hosted billing or an external monitor is available. |
| Health | `scripts/system_health.ps1` gives manual system status; `health-monitor` runs scheduled checks. | Keep recording recent health history. |
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

- [x] Add a scheduled runner health check. See `.github/workflows/health-monitor.yml`.
- [x] Add CI failure notification path. `health-monitor` fails visibly through GitHub Actions notifications when the self-hosted runner is available.
- [x] Add stale-green alert when no successful CI run exists after a threshold. `health-monitor` uses `HEALTH_MAX_CI_AGE_HOURS`.
- [ ] Add out-of-band runner-down alert after GitHub-hosted billing or an external monitor is available.
- [x] Document incident response: symptom, diagnosis, fix, prevention. See `docs/incident-response.md`.
- [x] Record recent health-check result history. See `docs/system-health.md`.

## Priority 2 — security baseline

Goal: secrets and supply chain mistakes should be hard to miss.

- [x] Document secret handling and security reporting. See `SECURITY.md` and `docs/security-baseline.md`.
- [x] Define token rotation rules for GitHub, OpenAI, OpenCode, and runner credentials. See `docs/security-baseline.md`.
- [x] Add dependency update policy. See `docs/dependency-updates.md`.
- [x] Add lightweight SAST/security scan for changed code. CI runs a focused Ruff security rule set over `src` and `scripts`.
- [x] Require extra review for changes touching secrets, runner setup, filesystem access, auth, or external command execution. See `docs/security-baseline.md`.

## Priority 3 — governance of change

Goal: every change should be understandable, reversible, and auditable.

- [x] Add a project Definition of Done. See `docs/change-governance.md`.
- [x] Add session start/close checklist. See `docs/session-checklist.md`.
- [x] Add release checklist. See `docs/release-recovery.md`.
- [x] Add changelog or release notes process. See `CHANGELOG.md` and `docs/change-governance.md`.
- [x] Use ADRs for durable architecture decisions. See `docs/adr/0001-lightweight-enterprise-governance.md`.
- [x] Keep SDD/OpenSpec active only when it guides real current work. See `docs/change-governance.md`.

## Priority 4 — quality and verification

Goal: prevent regressions without testing everything blindly.

- [x] Add smoke test for CLI installation and basic commands. See `tests/integration/test_cli_smoke.py`.
- [x] Add tests for `scripts/system_health.ps1` output expectations where practical. See `tests/integration/test_system_health_script.py`.
- [x] Define minimum regression test set for drift-detection changes. See `docs/drift-detection-regression-set.md`.
- [x] Keep bug fixes paired with regression tests. See `docs/change-governance.md`.
- [x] Document supported platforms and Python versions. See `docs/support-matrix.md`.

## Priority 5 — observability

Goal: system state should be easy to inspect in one minute.

- [x] Keep the lightweight health command as the source of truth. See `docs/system-health.md`.
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

- [x] Document how to rebuild the runner service. See `docs/release-recovery.md`.
- [x] Document what critical Codex/OpenCode/Engram configuration must be preserved. See `docs/release-recovery.md`.
- [x] Document disaster recovery steps. See `docs/release-recovery.md`.
- [x] Tag stable releases. `v1.3.0` is published at https://github.com/Rene-Kuhm/flow-engineering/releases/tag/v1.3.0.
- [x] Define rollback strategy for shipped changes. See `docs/release-recovery.md`.

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

