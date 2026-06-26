# Spec: Flow Engineering

**Change:** `flow-engineering`
**Builds on:** `design/design.md`
**Date:** 2026-06-25
**Status:** SPECIFIED → ready for sdd-tasks

## Requirements

### REQ-1: CLI binary

The system SHALL provide a `flow` CLI installed via `uv tool install flow-engineering`.

#### Scenario REQ-1.1: Install

```gherkin
GIVEN a Python 3.12+ environment with uv installed
WHEN the user runs `uv tool install flow-engineering`
THEN the `flow` binary is available on PATH
  AND `flow --version` prints the installed version
```

#### Scenario REQ-1.2: Per-project pin

```gherkin
GIVEN a project with `.flow-version` containing `0.1.0`
WHEN the user runs `flow new my-change` inside the project
THEN `flow` reads the version, warns if binary version differs from `.flow-version`
  AND uses the pinned version semantics for the new change
```

### REQ-2: New change scaffolding

The system SHALL scaffold a new change directory using Jinja2 templates.

#### Scenario REQ-2.1: Scaffold a change

```gherkin
GIVEN a project at `c:/dev/proyects/my-app`
  AND `flow` binary is installed
WHEN the user runs `flow new my-change --in c:/dev/proyects/my-app`
THEN `c:/dev/proyects/my-app/flow-engineering/my-change/` is created
  AND contains explore/, propose/, design/, spec/, tasks/, change.yaml
  AND state.json is created with status=NEW
  AND an Engram observation is saved with topic_key `sdd/my-change/created`
```

#### Scenario REQ-2.3: Cross-project change

```gherkin
GIVEN a change that must touch 2 sub-projects
WHEN the user creates `change.yaml` with `cross_projects: [mockup, tecnodespegue-landing]`
THEN `flow apply my-change` creates per-project apply-progress for each
  AND does not archive until all per-project apply-progress reach VERIFIED
```

### REQ-3: State machine

The system SHALL enforce the transition: NEW → EXPLORED → PROPOSED → DESIGNED → SPECIFIED → TASKED → APPLYING → VERIFYING → ARCHIVING → DONE.

#### Scenario REQ-3.1: Forward transition

```gherkin
GIVEN a change in status=EXPLORED with explore/exploration.md present
WHEN `flow propose my-change` completes successfully
THEN status transitions to PROPOSED
  AND propose/proposal.md exists
  AND Engram observation `sdd/my-change/proposal` is saved
```

#### Scenario REQ-3.2: Skip transition rejected

```gherkin
GIVEN a change in status=NEW (no exploration.md yet)
WHEN the user runs `flow propose my-change`
THEN the CLI rejects with error: "Cannot skip EXPLORED. Run `flow explore my-change` first."
  AND status remains NEW
```

### REQ-4: Drift detection

The system SHALL detect 3 classes of drift and route them differently.

#### Scenario REQ-4.1: Spec drift detected

```gherkin
GIVEN a change in status=APPLYING
  AND tasks.md shows task #3 marked [x]
  AND the latest apply-progress in Engram shows task #3 as in_progress
WHEN the orchestrator checks drift before next transition
THEN drift.py reports spec_drift=true
  AND apply halts
  AND the user is shown: "tasks.md and apply-progress disagree on task #3. Reconcile manually."
```

#### Scenario REQ-4.2: Structural test failure escalates

```gherkin
GIVEN a change in status=VERIFYING
  AND the test runner output contains `ImportError: cannot import name 'foo'`
WHEN drift.py classifies the failure
THEN classification=STRUCTURAL
  AND the system escalates immediately (no retry)
  AND the user is shown: "Structural failure. Fix the spec or design before retrying."
```

#### Scenario REQ-4.3: Transient test failure retries

```gherkin
GIVEN a change in status=VERIFYING
  AND the test runner output contains `TimeoutError: test exceeded 30s`
WHEN drift.py classifies the failure
THEN classification=TRANSIENT
  AND the system retries up to 2 times with exponential backoff
  AND if still failing after 2 retries, escalates with structured report
```

#### Scenario REQ-4.4: Contract failure re-specs

```gherkin
GIVEN a change in status=VERIFYING
  AND the test runner output contains `AssertionError: expected 200, got 404`
WHEN drift.py classifies the failure
THEN classification=CONTRACT
  AND the system prompts the user: "Test asserts contract X. Re-spec or update implementation?"
  AND does NOT auto-retry
```

### REQ-5: ARCHIVE → graph rebuild

The system SHALL trigger a graph rebuild after archive, choosing incremental or full based on change shape.

#### Scenario REQ-5.1: Incremental rebuild on non-structural change

```gherkin
GIVEN a change that only added a new component (no deleted files, no renamed modules)
WHEN archive completes
THEN graphify_hook runs `graphify update c:/dev/proyects/{sub_project}`
  AND exits 0
  AND the new component appears in graph.json
  AND the cost is ≤ $0.05 (incremental)
```

#### Scenario REQ-5.2: Full rebuild on structural change

```gherkin
GIVEN a change that includes deleted files or renamed modules (detected by diff stats)
WHEN archive completes
THEN graphify_hook runs `graphify .` against the sub_project
  AND exits 0
  AND node count in graph.json matches expected delta within 5%
  AND the cost is ~$0.40 (full rebuild)
```

#### Scenario REQ-5.3: Force-flag escalation

```gherkin
GIVEN an incremental update that needed --force to complete (shrunk graph)
WHEN graphify_hook reports this back
THEN the system escalates to user with: "graphify update needed --force. Possible drift. Run `graph doctor` before proceeding."
```

### REQ-6: Plugin behavior

The OpenCode plugin SHALL inject reminders and namespace commands.

#### Scenario REQ-6.1: First-run reminder

```gherkin
GIVEN OpenCode session starts
  AND cwd contains a `flow-engineering/` directory with at least one change
WHEN any tool.execute.before fires for the first time in the session
THEN the plugin prints: "[flow-engineering] Active changes detected. Use `flow status` to see them."
  AND this reminder does NOT fire again in the same session (one-shot)
```

#### Scenario REQ-6.2: Command namespacing

```gherkin
GIVEN the plugin is active
WHEN the LLM invokes bash with a command starting with `flow `
THEN the plugin prepends `[flow-engineering {version}] ` to the command output for user visibility
  AND does NOT modify the actual command (just annotates)
```

#### Scenario REQ-6.3: Coexistence with graphify plugin

```gherkin
GIVEN both flow-engineering and graphify plugins are active in the same session
WHEN any bash command fires
THEN graphify's reminder fires once (if graph.json exists)
  AND flow-engineering's reminder fires once (if flow-engineering/ exists)
  AND they do not interfere (no race, no double-fire)
```

### REQ-7: Strict TDD enforcement

The system SHALL default to strict TDD mode for projects that support it.

#### Scenario REQ-7.1: Default ON for compatible projects

```gherkin
GIVEN a change in a sub-project with strict_tdd_compatible=true (e.g., tecnodespegue-landing)
WHEN `flow apply my-change` runs sdd-apply
THEN the sub-agent receives: "STRICT TDD MODE IS ACTIVE. Test runner: playwright test. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
```

#### Scenario REQ-7.2: Explicit opt-out required

```gherkin
GIVEN a change in a strict-TDD-compatible project
WHEN the user runs `flow apply my-change --no-strict-tdd "reason here"`
THEN the opt-out is logged in state.json transitions[]
  AND the sub-agent does NOT receive the strict TDD instruction
  AND a warning is shown: "Strict TDD disabled. Reason: {user reason}"
```

### REQ-8: Cross-session recovery

The system SHALL recover change state across sessions via Engram.

#### Scenario REQ-8.1: Recover in-progress change

```gherkin
GIVEN session 1 ended with change X in status=APPLYING
  AND Engram observation `sdd/X/apply-progress` exists with progress
WHEN session 2 starts
THEN `flow status` lists change X with status=APPLYING
  AND `flow apply X` reads the prior apply-progress and continues
  AND does NOT re-do completed tasks
```

### REQ-9: Runaway cost guard

The system SHALL enforce a per-change token budget.

#### Scenario REQ-9.1: Budget exceeded halts loop

```gherkin
GIVEN a change has consumed 80% of its token budget (default 100k tokens)
WHEN the orchestrator detects the threshold
THEN it logs a warning to state.json
  AND the next loop iteration pauses for user approval before continuing
```

## Out of scope (v1)

- GUI for `flow status` (CLI only)
- Web dashboard for drift history (CLI only, logs to Engram)
- Automatic cross-project commit (manual flag for v1)
- Full CI runner (designed for, not implemented)
- BDD test runner auto-detection (manual via `.flow-version` for v1)

## Acceptance criteria

- [ ] All REQ-1 scenarios pass
- [ ] All REQ-2 scenarios pass
- [ ] All REQ-3 scenarios pass
- [ ] All REQ-4 scenarios pass
- [ ] All REQ-5 scenarios pass
- [ ] All REQ-6 scenarios pass
- [ ] All REQ-7 scenarios pass
- [ ] All REQ-8 scenarios pass
- [ ] All REQ-9 scenarios pass
- [ ] All scenarios have BDD test files in `tests/bdd/`
- [ ] All scenarios have at least one unit test in `tests/unit/`
- [ ] Plugin passes coexistence test with graphify plugin
- [ ] At least one full flow run (NEW → DONE) succeeds end-to-end on a sample change

## Ready for tasks

**Yes** — 9 requirements, ~25 BDD scenarios, all testable. Tasks phase will break down by component.
