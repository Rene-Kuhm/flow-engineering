# flow-engineering

Orchestrator of the Agentic & Context-Driven closed loop: INTENT → CONTEXT → SPEC → APPLY → VERIFY → ARCHIVE.

## What it does

Automates the transitions between SDD phases with drift detection, retry policy, and cross-session recovery. Mirrors the proven `graphify.js` plugin pattern as a thin OpenCode plugin, with a Python CLI doing the heavy lifting.

## Install

```bash
uv tool install flow-engineering
```

Per-project pinning via `.flow-version`:

```bash
echo "0.1.0" > .flow-version
```

## Quickstart

```bash
# Inside a project
flow new my-change
# Edit flow-engineering/my-change/explore/exploration.md
flow propose my-change
flow design my-change
flow spec my-change
flow tasks my-change
flow apply my-change
flow verify my-change
flow archive my-change
```

## Status

PR #1 (bootstrap + state machine) — see `tasks/tasks.md` for full plan.

## See also

- `FLOW.md` — 1-page loop description
- `propose/proposal.md` — why this exists
- `design/design.md` — architecture
- `spec/spec.md` — BDD scenarios
- `tasks/tasks.md` — implementation breakdown
