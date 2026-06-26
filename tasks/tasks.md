# Tasks: Flow Engineering

**Change:** `flow-engineering`
**Builds on:** `spec/spec.md`
**Date:** 2026-06-25
**Status:** TASKED → ready for sdd-apply

**Strict TDD**: ON. Each task that produces code MUST have failing tests first.

---

## Phase 1: Project bootstrap (T-DD)

- [ ] **T1.1** Initialize uv tool project structure at `c:/dev/proyects/flow-engineering/`
  - pyproject.toml with `[project]` metadata, `[project.scripts]` entry `flow = "flow_engineering.cli:main"`
  - src layout: `src/flow_engineering/`
  - Dependencies: click, jinja2, watchdog, pydantic, pyyaml
  - Dev deps: pytest, pytest-bdd, pytest-cov, ruff, mypy

- [ ] **T1.2** Set up CI linting
  - ruff config in pyproject.toml
  - mypy strict config
  - Makefile targets: `make lint`, `make test`, `make typecheck`

- [ ] **T1.3** BDD test scaffolding
  - `tests/bdd/` with feature files per REQ (req1_cli.feature, req2_scaffold.feature, ...)
  - `tests/unit/` with `conftest.py`
  - pytest-bdd configured

---

## Phase 2: State machine (REQ-3)

- [ ] **T2.1** `[RED]` Write `tests/unit/test_state_machine.py` — forward transition, skip rejection, retry loop
- [ ] **T2.2** `[GREEN]` Implement `state.py` — `ChangeStatus` enum, `transition()` function, validation
- [ ] **T2.3** `[REFACTOR]` Extract `transitions[]` writer helper

---

## Phase 3: Engram I/O (REQ-8)

- [ ] **T3.1** `[RED]` Write `tests/unit/test_engram_io.py` — save_phase, load_phase, cross-session search
- [ ] **T3.2** `[GREEN]` Implement `engram_io.py` — mem_save / mem_search / mem_get_observation wrappers with topic_key `sdd/{change}/{phase}`
- [ ] **T3.3** `[BDD]` Write `tests/bdd/req8_recovery.feature` — scenario REQ-8.1

---

## Phase 4: Drift detection (REQ-4)

- [ ] **T4.1** `[RED]` Write `tests/unit/test_drift_spec.py` — tasks.md vs apply-progress mismatch
- [ ] **T4.2** `[GREEN]` Implement `drift.check_spec_drift()`
- [ ] **T4.3** `[RED]` Write `tests/unit/test_drift_test_failures.py` — structural/transient/contract classification
- [ ] **T4.4** `[GREEN]` Implement `drift.classify_test_failures()` with regex on test runner output
- [ ] **T4.5** `[RED]` Write `tests/unit/test_drift_memory.py` — mem_search vs tasks.md vs graphify query triangulation
- [ ] **T4.6** `[GREEN]` Implement `drift.check_memory_mismatch()`
- [ ] **T4.7** `[BDD]` Write `tests/bdd/req4_drift.feature` — scenarios REQ-4.1, REQ-4.2, REQ-4.3, REQ-4.4

---

## Phase 5: Retry policy (REQ-4 + REQ-9)

- [ ] **T5.1** `[RED]` Write `tests/unit/test_retries.py` — max transient retries, exponential backoff, structural no-retry
- [ ] **T5.2** `[GREEN]` Implement `retries.py` — `RetryPolicy` dataclass, `should_retry(signal_class, attempt_n)` function
- [ ] **T5.3** `[RED]` Write `tests/unit/test_budget.py` — token budget tracking, threshold escalation
- [ ] **T5.4** `[GREEN]` Implement budget tracker in `state.py` (counter + threshold check)

---

## Phase 6: Scaffolding (REQ-2)

- [ ] **T6.1** Create Jinja2 templates in `src/flow_engineering/templates/`
  - `new-project/` (full project bootstrap)
  - `new-change/` (per-change directory)
- [ ] **T6.2** `[RED]` Write `tests/unit/test_scaffold.py` — renders templates, writes files, creates state.json, saves Engram observation
- [ ] **T6.3** `[GREEN]` Implement `scaffold.py` — `render_new_change(change_name, target_path, cross_projects=[])`
- [ ] **T6.4** `[BDD]` Write `tests/bdd/req2_scaffold.feature` — scenarios REQ-2.1, REQ-2.3

---

## Phase 7: CLI subcommands (REQ-1)

- [ ] **T7.1** `[RED]` Write `tests/unit/test_cli_new.py` — args parsing, target path validation, version pin check
- [ ] **T7.2** `[GREEN]` Implement `flow new <change> [--in <path>]` via click
- [ ] **T7.3** `[RED]` Write `tests/unit/test_cli_apply.py` — delegates to sdd-apply (or inline), reads prior apply-progress
- [ ] **T7.4** `[GREEN]` Implement `flow apply <change> [--no-strict-tdd REASON]`
- [ ] **T7.5** `[RED]` Write `tests/unit/test_cli_verify.py`, `test_cli_archive.py`, `test_cli_status.py`, `test_cli_doctor.py`
- [ ] **T7.6** `[GREEN]` Implement remaining subcommands
- [ ] **T7.7** `[BDD]` Write `tests/bdd/req1_cli.feature` — scenarios REQ-1.1, REQ-1.2

---

## Phase 8: Graphify hook (REQ-5)

- [ ] **T8.1** `[RED]` Write `tests/unit/test_graphify_hook.py` — structural detection, incremental vs full dispatch, force-flag escalation
- [ ] **T8.2** `[GREEN]` Implement `graphify_hook.py` — `archive_hook(change)` reads change diff stats, decides incremental vs full
- [ ] **T8.3** `[BDD]` Write `tests/bdd/req5_archive.feature` — scenarios REQ-5.1, REQ-5.2, REQ-5.3

---

## Phase 9: OpenCode plugin (REQ-6)

- [ ] **T9.1** Write `plugins/flow-engineering.js` (≤30 lines, mirrors graphify.js)
- [ ] **T9.2** `[RED]` Write plugin integration test — fake OpenCode event loop, verify one-shot reminder, command namespacing
- [ ] **T9.3** `[GREEN]` Validate plugin loads without errors
- [ ] **T9.4** `[BDD]` Write `tests/bdd/req6_plugin.feature` — scenarios REQ-6.1, REQ-6.2, REQ-6.3

---

## Phase 10: File watcher (REQ-3 hook model)

- [ ] **T10.1** `[RED]` Write `tests/unit/test_watcher.py` — detects explore/exploration.md write, transitions NEW → EXPLORED
- [ ] **T10.2** `[GREEN]` Implement `watcher.py` using watchdog, integrates with state.py
- [ ] **T10.3** `[GREEN]` Implement `flow watch <change>` subcommand

---

## Phase 11: Strict TDD enforcement (REQ-7)

- [ ] **T11.1** `[RED]` Write `tests/unit/test_strict_tdd.py` — checks `sdd-init/{project}` for strict_tdd flag, builds prompt injection
- [ ] **T11.2** `[GREEN]` Implement strict TDD injection in `flow apply` before delegating to sdd-apply
- [ ] **T11.3** `[BDD]` Write `tests/bdd/req7_strict_tdd.feature` — scenarios REQ-7.1, REQ-7.2

---

## Phase 12: Cost guard (REQ-9)

- [ ] **T12.1** `[RED]` Write `tests/unit/test_cost_guard.py` — threshold detection, escalation message
- [ ] **T12.2** `[GREEN]` Implement `cost_guard.py` — wraps retry loop with budget check
- [ ] **T12.3** `[BDD]` Write `tests/bdd/req9_cost.feature` — scenario REQ-9.1

---

## Phase 13: End-to-end smoke test

- [ ] **T13.1** Create a dummy change `e2e-smoke` in a test repo
- [ ] **T13.2** Run full pipeline: `flow new` → write explore → `flow propose` → ... → `flow archive`
- [ ] **T13.3** Verify all BDD scenarios pass
- [ ] **T13.4** Verify Engram has all phase observations
- [ ] **T13.5** Verify graph.json updated (incremental or full as appropriate)

---

## Phase 14: Documentation

- [ ] **T14.1** Write `FLOW.md` — 1-page loop description for new users
- [ ] **T14.2** Write `README.md` — install, quickstart, configuration
- [ ] **T14.3** Write `CONTRIBUTING.md` — how to add new transitions, drift signals, retries

---

## Review Workload Forecast

- **Total tasks**: 47 (some grouped: ~14 `[RED]` + ~14 `[GREEN]` + ~7 BDD + ~12 misc)
- **Estimated lines**: ~1500 LOC (well above 400 budget)
- **Risk**: High — will exceed review budget per `delivery_strategy: ask-on-risk`
- **Recommendation**: **Chained PRs**

### Proposed PR chain (chained)

| PR | Scope | Tasks | Est. LOC |
|---|---|---|---|
| PR #1 | Bootstrap + state machine | T1.1-T1.3, T2.1-T2.3 | ~200 |
| PR #2 | Engram I/O + Drift detection | T3.*, T4.* | ~400 |
| PR #3 | Retry policy + Budget | T5.* | ~150 |
| PR #4 | Scaffolding + CLI | T6.*, T7.* | ~350 |
| PR #5 | Graphify hook + Plugin | T8.*, T9.* | ~200 |
| PR #6 | Watcher + Strict TDD + Cost guard | T10.*, T11.*, T12.* | ~250 |
| PR #7 | E2E smoke + Docs | T13.*, T14.* | ~150 |

**Chain strategy**: `feature-branch-chain` (each PR targets the previous PR's branch; tracker branch accumulates final integration; only tracker merges to main). This preserves rollback control.

---

## Ready for apply

**Conditional on user approval** — chained PR plan exceeds 400-line budget by default. Need confirmation before PR #1 starts.
