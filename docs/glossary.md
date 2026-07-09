# Glossary

Use this glossary to keep agents and maintainers aligned on this project's
language. Terms here describe `flow-engineering` specifically, not generic
industry definitions.

## Core loop

| Term | Meaning in this project |
|---|---|
| Agentic closed loop | The INTENT → CONTEXT → SPEC → APPLY → VERIFY → ARCHIVE workflow that turns a requested change into verified shipped behavior. |
| SDD | Spec-Driven Development. The project workflow where proposals, designs, specs, tasks, implementation, verification, and archive evidence stay linked. |
| OpenSpec | The file-backed SDD artifact store under `openspec/`, including active changes, archived changes, and shipped capability specs. |
| Engram | The persistent memory layer used for cross-session decisions, discoveries, preferences, and SDD artifacts when applicable. |
| Graphify | The code-structure/indexing layer used to connect code symbols and project graph context. |
| Strict TDD | The rule that behavior changes are protected by tests and implementation follows RED → GREEN → REFACTOR where practical. |

## Change artifacts

| Term | Meaning in this project |
|---|---|
| Change | A named SDD work unit, usually stored under `openspec/changes/<name>/` while active. |
| Proposal | The product/intent framing for a change: problem, scope, non-goals, and expected outcome. |
| Design | The technical decision record for a change: architecture, tradeoffs, seams, and constraints. |
| Spec | Behavior requirements and scenarios that define the truth the implementation must satisfy. |
| Tasks | Ordered reviewable work units. They should map to behavior, not file-by-file busywork. |
| Verify report | Evidence that implementation matches spec/design/tasks, with risks called out explicitly. |
| Archive report | Close-out evidence for a completed change and any spec sync or follow-up decisions. |
| Follow-up audit | The live triage register in `docs/follow-up-audit.md`; old archived notes are not backlog unless promoted there. |

## Product/domain terms

| Term | Meaning in this project |
|---|---|
| Decision drift | A mismatch between saved decisions/specs/tasks and current code or implementation reality. |
| Drift detection | The capability that scans a change and reports stale, contradicted, or unverifiable decision/code bindings. |
| Finding | One drift-detection result for a decision binding, including the drift class and detail. |
| Drift class | The classification for a binding, such as still valid, stale ID, stale location, label drift, contradicted, obsolete, or unable to verify. |
| CodeRef | A structured reference to a code symbol or location: project, id, label, file, line, confidence, and source. |
| Graph snapshot | A frozen graph state used to compare drift against a deterministic past or pinned state. |
| `unable_reason` | Machine-readable reason explaining why drift verification could not load graph/snapshot state. |
| Drift event log | Append-only JSONL event stream for drift-related observability. |

## Operational terms

| Term | Meaning in this project |
|---|---|
| Self-hosted runner | The Windows GitHub Actions runner installed as a service at `C:\actions-runner-flow-engineering`. |
| Runner watchdog | `scripts/runner_watchdog.ps1`, the out-of-band health signal for runner service and latest CI health. |
| System health | `scripts/system_health.ps1`, the one-minute local dashboard for runner, CI, active specs, follow-ups, and memory pointers. |
| Monthly maintenance | `scripts/monthly_maintenance.ps1`, the periodic routine for health, follow-up, and memory hygiene checks. |
| Health monitor | The scheduled GitHub Actions workflow that checks latest main CI health when the self-hosted runner can start jobs. |
| Alert webhook | `FLOW_RUNNER_ALERT_WEBHOOK`, the external notification URL for watchdog warnings/critical states. It is not active until a real URL is configured and tested. |

## Repository surfaces

| Term | Meaning in this project |
|---|---|
| CLI | The Python Click command surface under `src/flow_engineering/cli/`, exposed as `flow`. |
| Prompt registry | The Jinja2 prompt-template system with validation and render logs. |
| Workspace hygiene | Commands and checks that keep local project/workspace state understandable and recoverable. |
| Observability | Lightweight counters, JSONL logs, and summaries that answer real operational questions without overbuilding dashboards. |
| ADR | Architecture Decision Record stored under `docs/adr/` for durable decisions maintainers should not rediscover. |

## Do not confuse

| Similar terms | Difference |
|---|---|
| OpenSpec vs Engram | OpenSpec is file-backed and committable; Engram is persistent memory across sessions. |
| Archived change vs active follow-up | Archived changes are historical; active follow-ups must appear in `docs/follow-up-audit.md` or a new proposal. |
| Health monitor vs runner watchdog | Health monitor runs inside GitHub Actions; watchdog can run outside GitHub Actions and can detect runner-down states. |
| Operating manual vs detailed docs | The operating manual is a routing map; detailed docs remain the source of truth for each topic. |
