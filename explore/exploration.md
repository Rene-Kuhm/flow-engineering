## Exploration: Flow Engineering

### Current State

**Primitives wired up:**
- **Engram** (persistent memory) — topic_keys exist for the concept (`architecture/flow-engineering-concept`), the graph (`architecture/flow-engineering-graph`), LLM config (`config/minimax-as-graphify-backend`), and projects centralization (`architecture/projects-centralization`). Provides `mem_save`, `mem_search`, `mem_update`, `mem_get_observation`, `mem_session_summary`.
- **Graphify** v0.8.49 — installed, pipeline produces `graph.json` (5043 nodes / 8213 edges / 329 communities), `GRAPH_REPORT.md`, `graph.html`. Schema includes `id`, `label`, `source_file`, `source_location`, `confidence` (EXTRACTED/INFERRED/AMBIGUOUS), `nodes`, `edges`, `hyperedges`. Cache at `graphify-out/cache/{semantic,ast}/`.
- **OpenCode plugin pattern** (`graphify.js`, 22 lines) — proves the lightest viable coupling: `tool.execute.before` hook that injects a reminder into bash commands when `graphify-out/graph.json` exists. One-shot per session via `reminded` flag.
- **SDD skill set** (10 skills, all `disable-model-invocation: true` except `sdd-explore`) — each skill is a SKILL.md prompt consumed by an LLM, with an explicit **ORCHESTRATOR GATE** that forces delegation to sub-agents. Persistence via Engram (`sdd/{change}/proposal|spec|design|tasks|apply-progress`) or filesystem (`openspec/changes/...`).
- **LLM backend** — MiniMax API (`https://api.minimax.io/v1`), model `MiniMax-M3` for structured output.
- **Project root** — `C:\dev\proyects\` with 6 sub-projects.

**What's missing:**
- No deterministic automation of the `INTENT → CONTEXT → SPEC → APPLY → VERIFY → ARCHIVE → memory/graph` loop. Transitions are run by LLM following SKILL.md prompts, not by code.
- No retry/auto-correction policy when VERIFY fails (currently the user decides).
- No drift detection between spec/tasks state (Engram) and on-disk reality (tasks.md, openspec/changes/).
- No bootstrap command (`flow-engineering new <project>`) that wires all four pillars for a fresh project.

### Affected Areas

- `C:\Users\insyd\.opencode\plugins\graphify.js` — current 22-line plugin is the template for the new flow-engineering plugin (or it gets extended).
- `C:\Users\insyd\.config\opencode\skills\_shared\sdd-phase-common.md` — defines retrieval/persistence contracts (`Section B`/`C`/`D`) the orchestrator must respect.
- `C:\Users\insyd\.config\opencode\skills\sdd-apply\SKILL.md` (and `sdd-verify`, `sdd-archive`) — the orchestrator delegates to these sub-agents; the new layer decides WHEN to delegate.
- `C:\dev\proyects\graphify-out\graph.json` — read by the orchestrator at the ARCHIVE→memory/graph transition to rebuild the cross-project graph.
- `C:\dev\proyects\` (project root) — orchestrator operates on changes located under each sub-project's `openspec/changes/` or `sdd/` directory.
- `C:\dev\proyects\flow-engineering\` (NEW) — orchestrator home.
- Engram MCP — orchestrator is a heavy `mem_save` / `mem_search` / `mem_update` consumer; topic_key convention (`sdd/{change}/...`) becomes load-bearing.

### Approaches

1. **Hybrid: thin OpenCode plugin + Python CLI**
   Thin plugin (`flow-engineering.js`, ~30 lines, mirrors `graphify.js` shape) listens to OpenCode events and shells out to `flow-engineering.exe` (Python via uv tool, same dispatch pattern as graphify). CLI owns state, retries, and Engram I/O.
   - Pros: plugin stays trivial (proven pattern), CLI is testable/deterministic, language choice matches existing graphify ecosystem, the orchestrator can run independent of an OpenCode session (CI, scripts).
   - Cons: two moving parts to ship; plugin-to-CLI contract needs versioning.
   - Effort: Medium.

2. **Pure OpenCode plugin (extends `graphify.js`)**
   Single `flow-engineering.js` plugin that subscribes to `tool.execute.before`, `tool.execute.after`, and `session.*` events; mutates prompts and intercepts bash commands to enforce the loop. No separate binary.
   - Pros: zero new binaries, same process as the LLM (no IPC), one artifact to version.
   - Cons: state (Engram topic indexes, drift baselines) must live in Engram or disk because the plugin has no persistent memory; tests must mock OpenCode internals; loop can't run unattended (no OpenCode session = no orchestrator).
   - Effort: Medium-Low.

3. **Standalone Python CLI + shell wrappers**
   `flow-engineering new|apply|verify|archive|flow` subcommands invoked manually by the user; OpenCode plugins stay untouched. Drift detection via cron-like file watcher (`watchdog`).
   - Pros: simplest mental model; works without OpenCode; CI-friendly.
   - Cons: no automatic hooks — the user still triggers every transition. Drift detection can miss things if the watcher is down. Doesn't really close the loop.
   - Effort: Low.

4. **Makefile / Taskfile driving shell scripts**
   Each transition is a `make` target chained by `make flow`. Verification is a script that runs tests and exits non-zero.
   - Pros: declarative, no runtime.
   - Cons: no reactive triggers, no state, no drift detection, no Engram integration. Static, not flow.
   - Effort: Low (but insufficient).

### Recommendation

**Approach 1 (hybrid: thin OpenCode plugin + Python CLI).**

Reasoning grounded in what was read:
- `graphify.js` is the de-facto template: 22 lines, file-presence check, one-shot per session, dispatches no work itself. Reusing this shape for the plugin half keeps the cognitive load at zero for someone reading `~/.opencode/plugins/`. Extending `graphify.js` directly (option 2's variant) was considered and rejected because flow engineering needs **persistent state across sessions** (drift baselines, retry counts, change status) — that belongs in a process with a real filesystem and Python tooling, not in a hook that fires once per session.
- The Python CLI mirrors `graphify`'s own install/dispatch strategy (`uv tool run graphifyy python -c "..."`), so there is no new toolchain concept to learn. Same interpreter-resolution dance, same cache conventions.
- It cleanly preserves the ORCHESTRATOR GATE contract from `sdd-apply`: the CLI **never inlines** SDD phases — it delegates to sub-agents that load the skill. The CLI is the trigger, the LLM is the executor.
- It is the only option that closes the loop without an OpenCode session active (CI, batch archive, post-commit hook → `flow-engineering archive` → triggers graphify rebuild).

Concretely:
```
C:\dev\proyects\flow-engineering\
  flow.py                    # CLI entry, ~40 commands
  state.py                   # change status / drift baselines
  drift.py                   # spec↔code↔memory diff
  retries.py                 # bounded retry policy
  engram_io.py               # mem_save / mem_search wrapper
  plugins\flow-engineering.js   # OpenCode plugin (~30 lines)
  templates\                 # `flow-engineering new` scaffolds
  tests\                     # BDD specs for each transition
```

Location: `C:\dev\proyects\flow-engineering\` — consistent with the existing `architecture/projects-centralization` decision in memory and physically co-located with the 6 projects it orchestrates.

### Hook Model

| Transition | Trigger | Mechanism |
|---|---|---|
| INTENT → CONTEXT | User invokes `/sdd-explore` or runs `flow-engineering new <change>` | CLI subcommand; plugin detects `sdd/{change}/explore/` written and emits `context_ready` event |
| CONTEXT → SPEC | `exploration.md` persisted | File watcher on `explore/exploration.md`; CLI runs `sdd-propose` → `sdd-spec` → `sdd-design` → `sdd-tasks` as a chain |
| SPEC → APPLY | `tasks.md` complete with `[ ]` marks | CLI subcommand `flow-engineering apply <change>`; delegates to `sdd-apply` sub-agent in batches; reads prior `apply-progress` from Engram (merge protocol from `sdd-apply` Step 2b) |
| APPLY → VERIFY | All tasks marked `[x]` in apply-progress | Auto-triggered after final apply batch; runs `sdd-verify`; if Strict TDD mode, demands TDD Cycle Evidence table |
| VERIFY → ARCHIVE | `sdd-verify` returns PASS | Auto-triggered; runs `sdd-archive` |
| ARCHIVE → memory/graph | Archive complete | Writes `mem_save` summary; fires `graphify update` against affected sub-project; cross-project rebuild if archive touches >1 sub-project |

Plugin events: `tool.execute.before` (intercept bash to enforce SDD order), `session.idle` (heartbeat for orchestrator state sync), custom `flow-engineering:transition` event the CLI emits over a unix socket / named pipe.

### Drift Detection

Three signals, each with a different retry policy:

1. **Spec drift** — diff `tasks.md` `[x]` marks vs. latest `sdd/{change}/apply-progress` in Engram. If mismatch: halt apply batch, force reconciliation step.
2. **Test failure classification** — capture runner output, classify with regex (`ImportError`, `SyntaxError` → structural failure → escalate; `TimeoutError`, `ConnectionError` → transient → retry ≤2; `AssertionError` with new trace → contract failure → re-spec). Heuristic table in `drift.py`.
3. **Memory mismatch** — `mem_search("sdd/{change}/tasks")` vs. filesystem `tasks.md` vs. graph query `graphify query "what implements {task-id}"`. Triangulate; if graph says no code implements a task marked `[x]`, flag as ghost-completion.

**Retry policy**: ≤2 transient retries, then escalate to user with a structured report (which transition failed, which signal tripped, suggested next action).

### Reusability (Bootstrap)

`flow-engineering new my-app` ships a minimal scaffold:
- `openspec/changes/` (or `sdd/`) with placeholder structure
- `CLAUDE.md` referencing the 4 pillars
- `~/.opencode/plugins/flow-engineering.js` symlink (or copy)
- `config.yaml` with `artifact_store: engram`, `llm_backend: minimax`, `strict_tdd: true`
- A `Makefile` exposing `flow-engineering` targets so non-Python projects can call it
- A 1-page `FLOW.md` describing the loop for humans

Minimum reusable subset = the CLI + plugin + `templates/scaffold/` (no Engram dependency hardcoded; Engram is one of four store modes).

### Risks

1. **Runaway cost** — closed loop + retries could trigger unbounded LLM calls (apply → verify → fail → re-spec → re-apply → re-verify). Mitigation: per-change token budget cap enforced at CLI level; abort and escalate when exceeded.
2. **State divergence** — Engram topic state, `tasks.md` filesystem state, and graph-implied state can disagree (e.g. user edits `tasks.md` outside the loop, network blip mid-`mem_save`). Mitigation: single source of truth per concern (Engram owns phase progress, filesystem owns phase artifacts, graph owns code-implements-claim), with explicit reconciliation step on every transition entry.
3. **Plugin/CLI version skew** — OpenCode updates or a Python release could silently break the IPC contract. Mitigation: `flow-engineering doctor` subcommand that runs on every session start; pinned versions in plugin metadata; CI test that loads the plugin in a headless OpenCode harness.
4. **Auto-correction masks real bugs** — a 2-retry cap helps, but if the failure mode is deterministic (wrong spec, wrong design), retries waste tokens without progress. Mitigation: classify failures; structural failures escalate immediately, never retry.
5. **Hook ordering with graphify plugin** — when both `graphify.js` and `flow-engineering.js` subscribe to `tool.execute.before`, order is undefined. Mitigation: namespace the prepended commands (`[graphify]` vs `[flow-engineering]`); document the merge contract.

### Ready for Proposal

**No — clarification needed before `sdd-propose`:**

1. **Artifact store default**: should `flow-engineering new` default to `engram` (project-native) or `hybrid` (engram + filesystem `openspec/`) for new projects? The 6 existing projects in `C:\dev\proyects\` use different conventions (some have `openspec/`, some don't) — need a decision on the migration cost vs. green-field default.
2. **Strict TDD default**: `sdd-apply` requires Strict TDD mode to be opt-in (`strict_tdd: true` in `config.yaml`). Should flow-engineering's bootstrap turn it ON by default, or stay neutral?
3. **Cross-project changes**: when one change touches ≥2 of the 6 sub-projects, does the orchestrator run as one apply (single apply-progress topic) or per-project? This changes the drift-detection unit.
4. **Trigger for ARCHIVE → graph rebuild**: incremental (`graphify update <sub-project>`) or full rebuild (`graphify .`)? Incremental is faster but can re-introduce the #479 shrink-guard problem if the change deletes nodes.

Once these four are resolved, ready for `sdd-propose`.
