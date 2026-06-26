# flow-engineering Constitution

**Version**: 1.0.0
**Effective**: 2026-06-26
**Aligned with**: [GitHub SpecKit](https://github.com/github/spec-kit) — adapted to our Agentic & Context-Driven methodology
**Owner**: Rene-Kuhm

---

## Preamble

This constitution establishes the governing principles for `flow-engineering`, an orchestrator that closes the loop between saved decisions (Engram), code structure (Graphify), and shipped behavior. It adapts GitHub's SpecKit constitution to our context where the AI-assisted development loop already follows most principles implicitly.

The constitution is enforced at every SDD phase boundary via `sdd-{explore,propose,design,spec,tasks,apply,verify,archive}` and read by every sub-agent before phase work begins.

---

## Article I: Library-First Principle

**Every feature ships as a standalone library before integration.**

### Mandate

- Each capability in `src/flow_engineering/` is a standalone Python module with explicit public surface (`__all__` or documented exports).
- Modules MUST be importable without the CLI binary. The CLI is a thin wrapper.
- Cross-module dependencies are explicit (no implicit singletons via global state).
- Library tests run without the CLI; CLI tests run separately.

### Enforcement

- `tests/unit/` covers library surface.
- `tests/bdd/` covers CLI surface.
- Library API breaking changes require a MAJOR version bump.

### Examples in this codebase

- `binding.py` — pure parse/format library, no CLI dependency.
- `decision_drift.py` — pure drift detection library, CLI is a thin wrapper in `cli.py`.
- `engram_io.py` — I/O library with `InMemoryBackend` for tests, real `EngramBackend` for production.

---

## Article II: CLI Interface Mandate

**All libraries expose a text-based CLI interface for orchestration.**

### Mandate

- Every library module MUST have a corresponding CLI subcommand in `cli.py` (or be explicitly exempted with rationale).
- CLI uses `click` (already a dep). No new CLI frameworks.
- All CLI subcommands support `--json` for programmatic consumption.
- Exit codes follow the REQ-11 / REQ-N contract for each subcommand and are documented in `--help`.
- Subcommands are independently testable via `click.testing.CliRunner`.

### Enforcement

- New library module without CLI subcommand → `sdd-verify` flags as gap.
- CLI subcommand without `--json` → review feedback in PR.
- Exit codes not documented in `--help` → review feedback.

### Examples in this codebase

- `flow drift <change>` — drift detection with `--json`, `--include-obsolete`, `--write-back`, `--since`, `--graph-json`.
- `flow inspect <change>` — decision↔code binding table.
- `flow metrics` — observability counters summary.

---

## Article III: Test-First Imperative (Strict TDD)

**Tests precede implementation. No code lands without a failing test first.**

### Mandate

- Strict TDD is **ON** by default (per `sdd-init/insyd`).
- Every code task follows RED → GREEN → REFACTOR cycle.
- Tests must demonstrate the failure BEFORE the implementation lands.
- BDD scenarios in `tests/bdd/` are written AFTER unit tests pass but BEFORE integration tests.
- Backfill scripts are dry-run by default; mutation requires explicit `--apply` flag.

### Enforcement

- `sdd-apply` sub-agent runs `uv run pytest --tb=short -q` after each commit; red builds are not committed.
- `sdd-verify` runs the full BDD suite + adversarial probes.
- PRs that contain untested code changes trigger automatic review feedback.

### Examples in this codebase

- `tests/unit/test_decision_drift.py` — 14 RED tests precede `classify_binding()` GREEN implementation.
- `tests/bdd/req9_drift_detection.feature` — 14 BDD scenarios after unit tests.
- `scripts/backfill_code_refs.py` — dry-run by default, `--apply` required for mutation.

---

## Article IV: Simplicity and Anti-Abstraction

**Prefer the simplest solution that solves the problem. No premature abstraction.**

### Mandate

- Don't add layers of indirection until they're needed.
- Don't introduce base classes, abstract factories, or DI containers unless 2+ concrete cases demand them.
- Configuration via env vars or simple dataclasses, not framework-heavy config systems.
- Reject abstractions that don't earn their keep in the first 3 use cases.

### Enforcement

- PR review: if abstraction has <3 concrete uses, push back.
- `sdd-design` must justify any new abstract base class or factory.

### Examples in this codebase

- `DriftClass(str, Enum)` — flat enum, no inheritance hierarchies.
- `Finding` / `DriftReport` — frozen dataclasses, no behavioral methods.
- `load_graph()` returns `(nodes, id_map, mtime)` tuple — no GraphLoader class.

---

## Article V: Integration-First Testing

**Test against realistic backends. Mock only at the external boundary.**

### Mandate

- Unit tests run against `InMemoryBackend` (real implementation, not mocks of internal methods).
- BDD tests run against real `EngramClient` with in-memory storage.
- External services (graphify CLI, Engram MCP) ARE mocked — but the mock represents the real interface, not internal behavior.
- Failures in integration tests are higher signal than unit test failures.

### Enforcement

- `sdd-verify` runs BDD suite before unit suite (BDD failures block merge).
- New code without integration test coverage → review feedback.

### Examples in this codebase

- `InMemoryBackend` for tests; `EngramBackend` for production.
- `graphify_query.py` subprocess mocked at the CLI boundary, not at the Python function boundary.
- `tests/bdd/test_decision_reality_drift_steps.py` — full Click CliRunner + InMemoryBackend stack.

---

## Article VI: Spec-as-Truth

**The spec is the contract. Code is the implementation. Drift is a bug.**

### Mandate

- Every REQ in `spec.md` MUST have at least one BDD scenario.
- Specs are written BEFORE implementation (per SpecKit Phase 2).
- Spec drift (impl contradicts spec) is detected by `sdd-verify` and flagged CRITICAL.
- OpenSpec files in `openspec/changes/<name>/` are the source of truth for active changes.
- Archived changes move to `openspec/changes/archive/<date>-<name>/`.

### Enforcement

- `sdd-verify` cross-checks REQ coverage against BDD scenarios.
- `sdd-archive` reconciles spec↔impl drift before closure.
- Spec drift carried forward to next change is tracked in verify-report WARNING section.

### Examples in this codebase

- `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` — REQ-1..8 with 33 BDD scenarios.
- `openspec/changes/decision-reality-drift/spec.md` — REQ-9..16 with 39 BDD scenarios.
- Verify reports flag spec↔impl drift (e.g., REQ-8 counter name drift closed by W2 in `decision-reality-drift` change).

---

## Article VII: Chained PR Discipline

**Chained PRs with stacked-to-main merge strategy.**

### Mandate

- Changes >400 LOC (real, after TDD multiplier) MUST be split into chained PRs.
- PRs merge to `main` in order; each PR is independently reviewable.
- PR#2 depends on PR#1's code; the implementer merges PR#1 BEFORE launching PR#2 apply.
- Chained PR boundary = reviewable unit, not arbitrary LOC threshold.

### Enforcement

- `sdd-tasks` Review Workload Forecast flags High risk when either PR exceeds 400-line budget at ×6 TDD multiplier.
- `sdd-apply` for PR#2 reads PR#1's `apply-progress` artifact for continuity.
- PRs merged out of order break the chain; orchestrator enforces via stacked-to-main.

### Examples in this codebase

- `decision-code-linking` change shipped as 2 PRs (#1, #2) with ~2179 + ~2026 LOC.
- `decision-reality-drift` change in flight: PR#1 merged, PR#2 pending.

---

## Article VIII: Persistent Context Across Sessions

**Engram is the persistent memory. Decisions survive compaction.**

### Mandate

- Every architectural decision, bug fix, or non-obvious discovery is saved to Engram via `mem_save`.
- Topic keys for evolving topics use the same `topic_key` (upsert behavior).
- Session summaries saved at every natural close-of-chunk boundary.
- Cross-session recovery: `mem_search` → `mem_get_observation` reconstructs context.

### Enforcement

- `sdd-verify` failure modes are saved as Engram observations for future reference.
- `apply-progress-<pr>-<batch>` saved after each apply batch.
- Session summary mandatory before ending or after compaction.

---

## Amendment Process

This constitution follows SpecKit's MAJOR.MINOR.PATCH versioning:

- **MAJOR** (X.0.0): Backward-incompatible governance changes (e.g., removing an article).
- **MINOR** (1.X.0): New principles or material expansions (e.g., adding Article IX).
- **PATCH** (1.0.X): Clarifications or refinements (e.g., tightening enforcement language).

Amendment process:
1. Open a PR against `main` modifying this file.
2. PR description must include rationale and impact analysis.
3. All chained PRs in flight must be re-evaluated for compliance.
4. Reviewer approval required from at least one human maintainer.

---

## Cross-references

- `AGENTS.md` — Top-level methodology mandate (SDD + BDD + TDD).
- `openspec/changes/<name>/{spec,design,tasks}.md` — Per-change artifacts.
- `openspec/changes/archive/<date>-<name>/` — Archived changes.
- Engram topic keys: `sdd-init/{project}`, `sdd/{change-name}/{phase}`, `sdd-session/{session-id}`.
- SpecKit reference: https://github.com/github/spec-kit