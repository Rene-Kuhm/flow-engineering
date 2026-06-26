# Design: Flow Engineering

**Change:** `flow-engineering`
**Builds on:** `propose/proposal.md`
**Date:** 2026-06-25
**Status:** DESIGNED → ready for sdd-spec

## Resolved open questions

### Q1: CLI distribution

**Decision**: Single `flow` binary installed via `uv tool install flow-engineering`. Per-project pinning via `.flow-version` file at project root (similar to `.python-version` or `.nvmrc`).

**Rationale**: A single binary is the only way to make `flow-engineering new <project>` work for bootstrapping new repos. Per-project pinning prevents the "works on my machine" problem when the binary evolves.

```
# Install globally
uv tool install flow-engineering

# Per-project pin (auto-detected on `flow` invocation)
$ cat .flow-version
0.1.0

# Per-project use
$ flow new my-change --in .
$ flow apply my-change
```

### Q2: Template engine

**Decision**: Plain Jinja2.

**Rationale**: Jinja2 is already a transitive dep of many Python tools (Ansible, FastAPI, etc.) and is small (~200KB). Avoids new toolchain concepts (no cookiecutter, no copier).

### Q3: File watcher scope

**Decision**: Per-change directory.

**Rationale**: A "change" is the unit of work. Watching `flow-engineering/{change-name}/` keeps the watcher focused and avoids spurious triggers from unrelated file activity in the rest of the repo.

### Q4: Plugin namespace collision

**Decision**: `[flow-engineering]` prefix on all command output; merge contract documented in plugin header.

**Rationale**: The graphify plugin already uses no prefix. Adding `[flow-engineering]` to flow's plugin output makes coexistence unambiguous. The merge contract: each plugin reads its own pre-state from disk before injecting; no plugin assumes sole ownership of `tool.execute.before`.

### Q5: CI integration

**Decision**: Design for it, ship v1 OpenCode-only.

**Rationale**: Including a CI mode in v1 doubles surface area and tests. But the CLI's subcommand structure (`flow apply`, `flow verify`, `flow archive`) is already CI-friendly — just needs a runner later. Document the CI contract in FLOW.md even if v1 doesn't implement it.

### Q6: Cross-project commit detection

**Decision**: Manual flag in change metadata (`cross_projects: [project-a, project-b]` in `flow-engineering/{change-name}/change.yaml`).

**Rationale**: Auto-detect from diff is fragile (a single shared config file would trigger false positives). Manual is explicit and reviewable.

## Component architecture

### `flow.py` — CLI entry

```python
# Subcommands
flow new <change> [--in <path>]   # scaffold a new change
flow apply <change>               # run sdd-apply
flow verify <change>              # run sdd-verify
flow archive <change>             # run sdd-archive + graphify update
flow status                       # list in-progress changes + drift summary
flow doctor                       # check plugin↔CLI version compat
flow watch <change>               # start file watcher for CONTEXT→SPEC transition
```

Invokes the appropriate `sdd-*` sub-agent via `task` tool OR runs the phase inline if sub-agents unavailable (current cache issue).

### `state.py` — change status, drift baselines

```python
# Per-change state file: flow-engineering/<change>/state.json
{
  "change": "add-dark-mode",
  "status": "APPLYING",  # state machine value
  "created_at": "...",
  "updated_at": "...",
  "transitions": [
    {"from": "NEW", "to": "EXPLORED", "at": "...", "artifact": "explore/exploration.md"},
    ...
  ],
  "drift_baseline": {
    "tasks_md_hash": "abc123",
    "apply_progress_topic": "sdd/add-dark-mode/apply-progress",
    "graph_node_count": 5043
  }
}
```

### `drift.py` — 3-signal drift detection

```python
def detect_drift(change: str) -> DriftReport:
    return DriftReport(
        spec_drift=check_spec_drift(change),       # tasks.md vs apply-progress
        test_failures=classify_test_failures(change),  # by exception type
        memory_mismatch=check_memory_mismatch(change),  # triangulate Engram + FS + graph
    )

def check_spec_drift(change: str) -> bool:
    """Diff tasks.md checked-state vs latest apply-progress in Engram."""
    ...

def classify_test_failures(change: str) -> TestFailureClass:
    """Read last test run output, classify by exception type."""
    # ImportError/SyntaxError → STRUCTURAL (escalate, never retry)
    # TimeoutError/ConnectionError → TRANSIENT (retry ≤2)
    # AssertionError → CONTRACT (re-spec)
    ...

def check_memory_mismatch(change: str) -> bool:
    """Triangulate mem_search vs tasks.md vs graphify query."""
    ...
```

### `retries.py` — bounded retry policy

```python
@dataclass
class RetryPolicy:
    max_transient_retries: int = 2
    transient_signals: set = {"TimeoutError", "ConnectionError"}
    structural_signals: set = {"ImportError", "SyntaxError", "NameError"}
    contract_signals: set = {"AssertionError", "ValueError"}
```

### `engram_io.py` — memory wrapper

```python
def save_phase(change: str, phase: str, content: str) -> None:
    """mem_save with topic_key = sdd/{change}/{phase}"""
    ...

def load_phase(change: str, phase: str) -> str:
    """mem_search + mem_get_observation"""
    ...

def search_cross_session(query: str) -> list:
    """mem_search across all flow-engineering changes"""
    ...
```

### `graphify_hook.py` — incremental graph rebuild

```python
def archive_hook(change: str) -> None:
    """Triggered after sdd-archive completes."""
    if is_structural_change(change):
        # Full rebuild for affected sub-project
        subprocess.run(["graphify", f"c:/dev/proyects/{sub_project}"], check=True)
    else:
        # Incremental update
        subprocess.run(["graphify", "update", f"c:/dev/proyects/{sub_project}"], check=True)
```

### `plugins/flow-engineering.js` — OpenCode plugin (~30 lines)

```javascript
// Mirrors graphify.js shape
import { readFileSync, existsSync } from 'fs';

const PLUGIN_VERSION = '0.1.0';

export const FlowEngineeringPlugin = async ({
    project, client, $, directory, worktree,
}) => ({
    'tool.execute.before': async (input, output) => {
        // Only fire when a change is in progress
        if (!existsSync(`${directory}/flow-engineering`)) return;
        if (output.args?.command?.startsWith('flow ')) {
            output.args.command = `[flow-engineering ${PLUGIN_VERSION}] ${output.args.command}`;
        }
        // One-shot per session reminder
        if (!globalThis.__flow_reminded) {
            globalThis.__flow_reminded = true;
            console.log('[flow-engineering] Active changes detected. Use `flow status` to see them.');
        }
    },
});
```

### `templates/` — scaffolds

```
templates/
├── new-project/
│   ├── flow-engineering/        # empty change folder
│   ├── openspec/changes/        # openspec structure
│   ├── CLAUDE.md                # references 4 pillars
│   ├── .flow-version            # pin current version
│   ├── Makefile                 # CI-friendly flow targets
│   └── FLOW.md                  # 1-page loop description
└── new-change/
    ├── explore/.gitkeep
    ├── propose/.gitkeep
    ├── design/.gitkeep
    ├── spec/.gitkeep
    ├── tasks/.gitkeep
    └── change.yaml              # change metadata (cross_projects, etc.)
```

## Data flow

```
user invokes `flow new my-change --in c:/dev/proyects/my-app`
    │
    ├── Jinja2 renders templates/new-change/ into target
    ├── state.py writes state.json (status=NEW)
    ├── engram_io.save_phase(change="my-change", phase="created", ...)
    └── plugin detects new state file → next session reminder fires

developer writes explore/exploration.md
    │
    ├── watchdog (in flow watch) detects file change
    ├── state.py transitions: NEW → EXPLORED
    ├── engram_io.save_phase(change="my-change", phase="explore", content=md_content)
    └── plugin suggests next: `flow propose my-change`

user invokes `flow propose my-change`
    │
    ├── delegates to sdd-propose sub-agent (or runs inline)
    ├── writes propose/proposal.md
    ├── state.py transitions: EXPLORED → PROPOSED
    └── engram_io.save_phase(...)

... (SPEC, TASKS, APPLY, VERIFY, ARCHIVE follow same pattern)

ARCHIVE completes:
    │
    ├── state.py transitions: ARCHIVING → DONE
    ├── graphify_hook.archive_hook(change) → graphify update or full
    ├── engram_io.save_phase(change, "archive", summary)
    └── plugin removes reminder for this change
```

## Dependencies

- **Python 3.12+** (uv-managed)
- **click** (CLI subcommand framework) — small, well-known
- **jinja2** — templates
- **watchdog** — file watcher for CONTEXT→SPEC
- **pydantic** — state.json validation
- **pyyaml** — change.yaml parsing

All standard, no exotic deps.

## Plugin ↔ CLI IPC

The plugin and CLI communicate via:
1. **Filesystem state** — `flow-engineering/<change>/state.json` is the IPC channel.
2. **File presence detection** — plugin checks if `flow-engineering/` exists in cwd.
3. **No socket, no HTTP** — pure filesystem keeps it testable and CI-friendly.

## Versioning

- CLI binary: semver. Pin via `.flow-version`.
- Plugin: same version as CLI (tightly coupled).
- Engram topic_keys: include version in key if schema changes (`sdd/{change}/v2/...`).

## Ready for spec

**Yes** — architecture is concrete, components are sized, IPC is defined. Spec phase will define the BDD scenarios per transition.
