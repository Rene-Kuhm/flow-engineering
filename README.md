# flow-engineering

[![CI](https://img.shields.io/github/actions/workflow/status/Rene-Kuhm/flow-engineering/test.yml?branch=main&event=push&style=flat-square)](https://github.com/Rene-Kuhm/flow-engineering/actions)
[![codecov](https://img.shields.io/codecov/c/github/Rene-Kuhm/flow-engineering/main?style=flat-square&token=PLACEHOLDER)](https://codecov.io/gh/Rene-Kuhm/flow-engineering)
[![pypi](https://img.shields.io/pypi/v/flow-engineering?style=flat-square)](https://pypi.org/project/flow-engineering/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)

> Orchestrator of the Agentic & Context-Driven closed loop: **INTENT → CONTEXT → SPEC → APPLY → VERIFY → ARCHIVE**.

## What is flow-engineering

`flow-engineering` is an opinionated Python orchestrator that closes the loop between saved decisions (Engram), code structure (Graphify), and shipped behavior. It implements **SDD (Spec-Driven Development)** end-to-end with strict TDD, drift detection, and cross-session recovery.

It is governed by the **SpecKit-aligned constitution** at `.specify/memory/constitution.md` (8 articles). Every sub-agent that touches this repo is required to read that file before proposing, designing, or applying any change.

## Install

Per-project pinning via `.flow-version`:

```bash
echo "0.1.0" > .flow-version
uv tool install flow-engineering
```

For end-users invoking `flow` directly, pin a project to a minimum `flow-engineering` version in `pyproject.toml` under `[tool.flow_engineering]` (see `min_sdd_skill_versions` in this repo's `pyproject.toml`).

## Quickstart — the SDD phase loop

```text
        ┌─────────────────────────────────────────────────────────┐
        │                                                         │
        ▼                                                         │
    ┌───────┐    ┌─────────┐    ┌───────┐    ┌───────┐    ┌───────┐
    │ INTENT│───▶│ CONTEXT │───▶│ SPEC  │───▶│ APPLY │───▶│VERIFY │
    └───────┘    └─────────┘    └───────┘    └───────┘    └───┬───┘
                                            ▲                │
                                            │                ▼
                                        ┌───────┐       ┌─────────┐
                                        │ TASKS │       │ ARCHIVE │
                                        └───────┘       └─────────┘
```

```bash
# Inside a project at the SDD phase loop:
flow new         my-change   # scaffold INTENT
flow propose     my-change   # draft CONTEXT
flow design      my-change   # lock architecture
flow spec        my-change   # BDD + unit tests
flow tasks       my-change   # ordered work list
flow apply       my-change   # ship implementation
flow verify      my-change   # prove spec ↔ impl parity
flow archive     my-change   # reconcile + close
```

For full phase semantics, see `openspec/changes/v1.1-followups/spec.md` and the `.specify/memory/constitution.md` governance.

## Architecture

`flow-engineering` is organized as a Python package under `src/flow_engineering/`. Entry points:

| Surface | Path | Purpose |
|---|---|---|
| Python CLI | `src/flow_engineering/cli/` | Click-based CLI; entry point `flow` registered in `pyproject.toml [project.scripts]` |
| OpenCode plugin | `plugins/flow-engineering.js` | Inject a one-shot `flow status` reminder before the first bash tool call when a `flow-engineering/` subdir exists |
| State machine | `src/flow_engineering/state.py` | NEW → EXPLORED → PROPOSED → DESIGNED → SPECIFIED → TASKED → APPLYING → VERIFYING → ARCHIVING → DONE |
| Drift detector | `src/flow_engineering/decision_drift.py` | Compares spec ↔ tasks ↔ apply-progress ↔ code; flags spec drift as CRITICAL per Article VI |
| Snapshot manager | `src/flow_engineering/snapshot_manager.py` | Byte-deterministic graph snapshots (sha256-locked) |
| Engram bridge | `src/flow_engineering/engram_io.py` | Real `EngramBackend` + `InMemoryBackend` for tests |
| Prompt registry | `src/flow_engineering/prompt_registry.py` | Jinja2 prompt templates with render logs |

The orchestrator enforces **strict TDD per Constitution Article III**: `sdd-apply` runs `uv run pytest --tb=short -q` after every commit; red builds are not committed. **Chained PRs per Article VII**: changes >400 LOC at TDD multiplier MUST split into chained PRs. **Spec-as-Truth per Article VI**: any spec↔impl drift is detected by `sdd-verify` and flagged CRITICAL.

## Capabilities

| Command | Description | Status |
|---|---|---|
| `flow new` | Scaffold a new change (INTENT) | stable |
| `flow propose` | Generate proposal.md from explore | stable |
| `flow design` | Lock architectural decisions | stable |
| `flow spec` | Write BDD + unit tests before code | stable |
| `flow tasks` | Generate ordered work list | stable |
| `flow apply` | Implement tasks in strict TDD order | stable |
| `flow verify` | Prove spec ↔ impl parity | stable |
| `flow archive` | Reconcile + close the change | stable |
| `flow drift <change>` | Detect spec ↔ tasks ↔ code drift | stable |
| `flow drift events {list,tail,stats}` | Read drift event log | stable |
| `flow drift-events` | DEPRECATED alias for `flow drift events` (REMOVED in v1.3 — REQ-V1.2.4) | deprecated |
| `flow metrics {summary,export,aggregate}` | Observability counters | stable |
| `flow prompts {check,lint,list,show}` | Prompt registry validation | stable |
| `flow projects {ls,backfill,alias}` | Cross-project registry | stable |
| `flow snapshot {create,list,show,diff,rollback,prune}` | Graph snapshots | stable |
| `flow workspace {status,dashboard,fix,archive,archived,restore}` | Workspace hygiene | stable |
| `flow archive rotate` | Read-only archive preview (v1.3 sub-change d; REQ-V1.3.4) | stable |

## Compatibility

| Component | Supported |
|---|---|
| Python | 3.12, 3.13 |
| OS | Windows CI-gated; Linux/macOS supported but not CI-gated |
| OpenCode runtime | >= `gentle-ai` 4.x with skill bundles ≥3.0 |
| engram-mcp | optional; needed for `flow search --semantic` |
| torch + sentence-transformers | optional via `[vectors]` extra + `FLOW_VECTOR_SEARCH=1` |

## OpenCode plugin

`plugins/flow-engineering.js` is registered automatically when OpenCode loads this repo's plugins directory. It registers a single `tool.execute.before` hook that prepends a one-shot `echo '[flow-engineering 0.1.0] Active changes detected. Run: flow status'` to the first bash tool call when a `flow-engineering/` change directory is detected in the working tree. Subsequent calls are no-ops. No outbound IPC, no subprocess — pure local reminder, mirroring the `graphify.js` pattern.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev workflow, conventional commit discipline, and the chained-PR policy. Constitution at `.specify/memory/constitution.md` is binding — PRs that violate any article will be flagged by `sdd-verify`.

See [Engineering Quality Gates](docs/engineering-quality-gates.md) for self-hosted runner operations, lean SDD documentation rules, and drift-detection slice limits.
See [Follow-up Audit](docs/follow-up-audit.md) for the current debt triage policy and next-slice guidance.
See [Drift Detection Regression Set](docs/drift-detection-regression-set.md) for the minimum tests required by future drift slices.
See [System Health](docs/system-health.md) for the lightweight runner/CI/follow-up dashboard.
See [Runner Watchdog](docs/runner-watchdog.md) for out-of-band runner-down checks.
See [Memory Maintenance](docs/memory-maintenance.md) for keeping Engram/SDD context useful instead of noisy.
See [Enterprise Readiness](docs/enterprise-readiness.md) for the operational, security, governance, and recovery checklist.
See [Dependency Updates](docs/dependency-updates.md) for Dependabot scope and review rules.
See [Security Baseline](docs/security-baseline.md) and [Security Policy](SECURITY.md) for secret handling, token rotation, and sensitive-change gates.
See [Operating Manual](docs/operating-manual.md) for the first-read map for agents and maintainers.
See [Session Checklist](docs/session-checklist.md) for the start/close routine agents should follow.
See [Release and Recovery](docs/release-recovery.md) for release tagging, runner rebuild, rollback, and disaster recovery.
See [Incident Response](docs/incident-response.md) for the symptom/diagnosis/fix/prevention workflow.
See [Change Governance](docs/change-governance.md), [Architecture Decisions](docs/adr/README.md), and [Changelog](CHANGELOG.md) for Definition of Done, release notes, and durable decisions.
See [Support Matrix](docs/support-matrix.md) for Python and platform support levels.

## License

[MIT](LICENSE) — © 2026 Rene-Kuhm.

## Acknowledgements

- Built on top of [GitHub SpecKit](https://github.com/github/spec-kit)'s constitutional governance, adapted to our Agentic & Context-Driven methodology.
- Memory layer via [Engram](https://engram-mcp.com) (or compatible MCP memory provider).
- Code indexing via [Graphify](https://github.com/codebase-memory/graphify).
- Inspired by classical compiler pipelines: lex → parse → type-check → codegen → verify → archive.

