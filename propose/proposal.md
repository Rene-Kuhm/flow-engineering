# Proposal: Flow Engineering

**Change:** `flow-engineering`
**Author:** orchestrator (sdd-propose inline due to sdd-* sub-agent model cache issue)
**Date:** 2026-06-25
**Status:** PROPOSED → ready for sdd-design

## Why (the problem)

Today, AI-assisted development at this user's setup runs as a **manual closed loop**: ask → write → review → forget → repeat. Context (memory, graph, specs, tests) is fragmented across tools that don't talk to each other. Each session starts cold. Cost is unpredictable; drift between spec and implementation goes undetected.

The user explicitly framed the target methodology as **"Agentic & Context-Driven Software Engineering with Closed-Loop Development"** (4 pillars: context architecture, spec+TDD-AI, hybrid model routing, flow engineering). Three pillars are partially in place (Engram for memory, Graphify for graph, SDD skills for spec+test). The fourth — **flow engineering** — has no implementation: it's the orchestrator that closes the loop.

## What (the deliverable)

A **thin OpenCode plugin + Python CLI** living at `C:\dev\proyects\flow-engineering\`. The plugin (≤30 lines, mirrors `graphify.js`) hooks into OpenCode events. The CLI (uv-installable, like graphify) owns state, retries, drift detection, and Engram I/O.

The CLI **never** inlines SDD phase logic — it always delegates to the appropriate `sdd-*` sub-agent (or runs the phase inline if the cache issue persists). This preserves the ORCHESTRATOR GATE principle: the LLM is the executor, the orchestrator decides WHEN.

```
INTENT → CONTEXT → SPEC → APPLY → VERIFY → ARCHIVE → (back to memory+graph)
```

Each transition is a deterministic hook, not a prompt.

## How (architecture sketch)

```
flow-engineering/
├── flow.py                 # CLI entry, subcommands
├── state.py                # change status, drift baselines (FS SoT)
├── drift.py                # spec ↔ code ↔ memory diff
├── retries.py              # bounded retry policy
├── engram_io.py            # mem_save / mem_search wrapper
├── graphify_hook.py        # incremental graph rebuild trigger
├── plugins/
│   └── flow-engineering.js # OpenCode plugin (~30 lines)
├── templates/
│   ├── new-project/        # scaffold for `flow new <name>`
│   └── new-change/         # scaffold for `flow change <name>`
└── tests/
    ├── bdd/                # Gherkin-style scenarios per transition
    └── unit/               # state, drift, retries unit tests
```

### Hook model

| Transition | Trigger | Mechanism |
|---|---|---|
| INTENT → CONTEXT | `flow-engineering new <change>` | CLI subcommand |
| CONTEXT → SPEC | `explore/exploration.md` written | file watcher (watchdog) |
| SPEC → APPLY | `tasks.md` with unchecked items | `flow-engineering apply <change>` delegates to `sdd-apply` |
| APPLY → VERIFY | all tasks `[x]` in apply-progress | auto after final apply batch |
| VERIFY → ARCHIVE | `sdd-verify` returns PASS | auto |
| ARCHIVE → graph | archive complete | `mem_save` summary + `graphify update <sub-project>` |

Plugin hooks:
- `tool.execute.before` — namespace commands (`[flow-engineering]` prefix to coexist with `[graphify]`)
- `session.idle` — heartbeat sync of in-progress changes
- Custom event via named pipe for `flow-engineering:transition`

### Drift detection (3 signals)

1. **Spec drift** — diff `tasks.md` `[x]` vs latest `sdd/{change}/apply-progress` in Engram. Mismatch → halt apply, force reconciliation.
2. **Test failure classification** — `ImportError`/`SyntaxError` → structural (escalate, never retry); `TimeoutError`/`ConnectionError` → transient (retry ≤2); `AssertionError` → contract failure (re-spec).
3. **Memory mismatch** — triangulate `mem_search("sdd/{change}/tasks")` vs `tasks.md` vs `graphify query "what implements {task-id}"`. Flag ghost-completions.

Retry policy: ≤2 transient retries, then escalate with structured report (failed transition, tripped signal, suggested next action).

### Per-change state machine

```
NEW → EXPLORED → PROPOSED → DESIGNED → SPECIFIED → TASKED →
  APPLYING → VERIFYING → ARCHIVING → DONE
            ↑                ↓
            └── retry ───────┘ (≤2 transient)
```

State persisted in `state.py` JSON file per change, with topic_key in Engram for cross-session recovery.

## Expert decisions (already made)

| # | Decision | Choice |
|---|---|---|
| 1 | Artifact store default | hybrid (filesystem SoT + engram cache/index) |
| 2 | Strict TDD default | ON (require `--no-strict-tdd` flag with reason to disable) |
| 3 | Cross-project changes | per-project apply-progress + cross-project commit wrapper |
| 4 | ARCHIVE → graph rebuild | incremental default; full only on structural changes (deleted files, renamed modules, package.json rewrite) |

## Non-goals (what Flow Engineering does NOT do)

- Does NOT replace human judgment — automates *transport* of judgment between stages.
- Does NOT replace SDD skills — the CLI delegates to them.
- Does NOT replace Graphify — graph remains the codebase knowledge layer.
- Does NOT replace Engram — memory remains the cross-session recovery layer.
- Does NOT auto-write code without human approval — `sdd-apply` requires explicit invocation.
- Does NOT silence failures — every drift signal has a clear escalation path.

## Open questions for design phase

1. **CLI distribution**: single `flow` binary via `uv tool install flow-engineering`, or per-project `flow.py` invoked via `uv run`? The first is more reusable but harder to version per-project. Recommend: single binary + per-project `.flow-version` pin.
2. **Template engine**: cookiecutter, copier, or plain Jinja2? Plain Jinja2 is simplest and avoids new deps.
3. **File watcher scope**: per-change directory (`flow-engineering/`) or whole repo? Per-change is more focused but misses cross-cutting changes.
4. **Plugin namespace collision with graphify.js**: confirm `[flow-engineering]` vs `[graphify]` prefix is enough, or do we need to merge hooks into a single plugin?
5. **CI integration**: can the orchestrator run in CI (GitHub Actions, etc.)? Currently only OpenCode-local. Worth designing for, even if v1 is OpenCode-only.
6. **Cross-project commit wrapper**: how to detect "this change touches ≥2 projects"? Manual flag in the change metadata, or auto-detect from diff? Manual is safer; auto-detect could miss intentional cross-cutting changes.

## Risks (from explore)

1. **Runaway cost** — closed loop + retries can trigger unbounded LLM calls. Mitigation: per-change token budget cap at CLI level.
2. **State divergence** — Engram topic state, `tasks.md` FS state, and graph-implied state can disagree. Mitigation: filesystem as SoT, engram derived from it.
3. **Plugin/CLI version skew** — OpenCode or Python update could silently break the IPC contract. Mitigation: `flow-engineering doctor` on session start; pinned versions in plugin metadata.
4. **Auto-correction masks real bugs** — deterministic failures (wrong spec, wrong design) waste tokens on retry. Mitigation: structural failures escalate immediately, never retry.
5. **Hook ordering with graphify plugin** — `tool.execute.before` fires for both. Mitigation: namespace prepended commands.

## Ready for design

**Yes** — open questions above are candidates for `sdd-design` to resolve. Architecture is concrete enough to proceed.
