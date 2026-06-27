<!-- Archived 2026-06-26 from openspec/changes/decision-reality-drift/spec.md -->
# Spec: decision-reality-drift

**Change:** `decision-reality-drift`
**Builds on:** `proposal.md` (Approach C — on-demand `flow drift <change>` + daemon-ready library, 2 chained PRs)
**Date:** 2026-06-25
**Status:** SPECIFIED → ready for sdd-design / sdd-tasks

## Goal

Close the decision↔code verification loop. `decision-code-linking` shipped the **pointer** (`code_refs` block + `CodeRef` dataclass + `flow inspect`); this change ships the **verifier**. `flow drift <change>` resolves every binding against current `graph.json`, classifies drift into one of six mutually-exclusive classes plus a terminal `unable_to_verify`, persists observability counters, and is daemon-ready by design. PR#1 lands the pure library + CLI + counter contract. PR#2 wires the verification surface into `flow watch --drift` and extends SKILL.md prose.

**W3 absorption**: append ONE BDD scenario "Save with valid empty block writes as `source: unbound`" to `tests/bdd/req3_engram_io.feature` (mirrors REQ-3 line 116 in archived spec; unit test passes, BDD scenario was missing per verify-report #118).

---

## PR#1 — Core verifier

### REQ-9: Drift classification

The system SHALL provide a pure-library resolver `decision_drift.resolve_binding(ref, graph_nodes)` that, given a `CodeRef` and the current `graph.json` parsed as `dict[id, node]`, classifies the binding into exactly one of six mutually-exclusive classes. When the graph cannot be read, the report carries a terminal `unable_to_verify` state (NOT a per-binding class).

| Class | Detection rule |
|---|---|
| `still_valid` | `id` resolves at the same `file:line` with matching `label` |
| `label_drift` | `id` resolves at the same `file:line` but `label` differs |
| `stale_location` | `id` resolves at a different `file:line` |
| `stale_id` | `id` is absent from current `graph.json` |
| `obsolete` | All bindings are `source: unbound` AND `graphify query` returns 0 candidates ≥ threshold |
| `contradicted` | Two decisions in the same change reference the same `id` with conflicting `source`/`confidence` |

Classification MUST be deterministic for a given `(ref, graph)` pair and MUST emit exactly one class per binding. The `unable_to_verify` state is terminal for the WHOLE report, not per-binding.

#### Scenario: still_valid — happy path
- GIVEN a binding `{id: "src_auth_jwt_jwttokenmanager", file: "src/auth/jwt.py", line: 42, label: "JWTTokenManager", source: manual, confidence: 0.9}`
- AND graph.json contains a node with the same `id` at the same `file:line` and matching `label`
- WHEN `resolve_binding` runs
- THEN the verdict is `still_valid`

#### Scenario: still_valid — `source` and `confidence` do not change the class
- GIVEN the same binding as the happy path with `source: backfill` (confidence 0.3)
- WHEN `resolve_binding` runs
- THEN the verdict is `still_valid`
- AND `confidence` is returned alongside the class for downstream weighting

#### Scenario: label_drift — symbol renamed at same location
- GIVEN a binding with `label: "JWTTokenManager"` and `id` resolving at the same `file:line`
- AND graph.json reports `label: "JWTManager"` for the same `id`
- WHEN `resolve_binding` runs
- THEN the verdict is `label_drift`
- AND the verdict carries `detail: {"expected_label": "JWTTokenManager", "actual_label": "JWTManager"}`

#### Scenario: label_drift — case-only change still flags
- GIVEN a binding with `label: "jwtTokenManager"` and graph reports `label: "JwtTokenManager"`
- WHEN `resolve_binding` runs
- THEN the verdict is `label_drift` (comparison is case-sensitive)

#### Scenario: stale_location — file moved within graph
- GIVEN a binding `{id: "x", file: "src/old.py", line: 10}`
- AND graph.json has the node at `src/new.py:42`
- WHEN `resolve_binding` runs
- THEN the verdict is `stale_location`
- AND the verdict carries `detail: {"expected": "src/old.py:10", "actual": "src/new.py:42"}`

#### Scenario: stale_location — same file, line shifted
- GIVEN a binding `{file: "src/foo.py", line: 10}` where graph reports the node at `src/foo.py:15`
- WHEN `resolve_binding` runs
- THEN the verdict is `stale_location`

#### Scenario: stale_id — file deleted from graph
- GIVEN a binding whose `id` is not present in graph.json
- WHEN `resolve_binding` runs
- THEN the verdict is `stale_id`
- AND `detail` is empty (no fallback location surfaced)

#### Scenario: stale_id — id renamed with no alias
- GIVEN a binding `{id: "old_class_hash"}` and graph.json contains only `new_class_hash` with no alias
- WHEN `resolve_binding` runs
- THEN the verdict is `stale_id`

#### Scenario: obsolete — unbound bindings plus zero graphify candidates
- GIVEN an observation with `source: unbound` and empty `nodes`
- AND `graphify query <observation content>` returns 0 candidates ≥ threshold 0.3
- WHEN `drift_report_for_change` runs with `--include-obsolete`
- THEN the verdict is `obsolete`
- AND `record_drift_summary` increments `drift_obsolete_total`

#### Scenario: obsolete — non-empty bindings short-circuit classification
- GIVEN an observation with at least one non-`unbound` binding
- WHEN `drift_report_for_change` runs
- THEN `obsolete` classification is NOT applied to that observation (other classes take precedence)

#### Scenario: contradicted — two decisions disagree on the same id
- GIVEN decision A binds `id: "x"` with `source: manual, confidence: 0.9`
- AND decision B binds `id: "x"` with `source: auto_suggest, confidence: 0.4`
- AND both live in the same change
- WHEN `drift_report_for_change` runs
- THEN both bindings surface `contradicted` with `detail: {"conflicting_decisions": [A.id, B.id]}`
- AND severity is WARNING (not ERROR)

#### Scenario: contradicted — identical source + confidence does not flag
- GIVEN two decisions in the same change both binding `id: "x"` with `source: manual, confidence: 0.9`
- WHEN `drift_report_for_change` runs
- THEN neither binding is classified `contradicted`

#### Scenario: unable_to_verify — graph.json missing (terminal)
- GIVEN the path passed as `graph_path` does not exist
- WHEN `drift_report_for_change` runs
- THEN the report contains a single `unable_to_verify` entry
- AND no per-binding classifications are emitted
- AND `record_drift_summary` increments `drift_unable_to_verify_total`

#### Scenario: unable_to_verify — graph.json schema mismatch (terminal)
- GIVEN `graph.json` exists but its top-level keys do not match the expected schema
- WHEN `drift_report_for_change` runs
- THEN the report contains `unable_to_verify`
- AND the detail names the schema mismatch

---

### REQ-10: `flow drift <change>` CLI subcommand

The system SHALL provide a `flow drift <change>` subcommand that renders a drift report table with columns `decision`, `binding` (id), `class`, `detail`. The command MUST accept `--json` (machine-readable output), `--include-obsolete` (opt-in trigger for the expensive `obsolete` classification), and `--since <ISO8601>` (skip decisions whose `created_at` precedes the cutoff).

#### Scenario: Default table render groups by decision
- GIVEN a change with three decisions and five total bindings
- WHEN `flow drift <change>` runs with no flags
- THEN the output is a table grouped by decision
- AND each binding appears as a sub-row with `class` and `detail`

#### Scenario: `--json` emits parseable JSON on stdout
- GIVEN a change with one decision and one binding
- WHEN `flow drift <change> --json` runs
- THEN stdout contains a JSON object parseable by `json.loads`
- AND the object has keys `change`, `graph_mtime`, `entries: [{decision_id, binding_id, class, detail}]`

#### Scenario: `--include-obsolete` triggers `graphify query` per unbound decision
- GIVEN a change with two unbound decisions
- WHEN `flow drift <change> --include-obsolete` runs
- THEN `graphify query` is invoked exactly twice
- AND each unbound decision receives a class (`obsolete` if zero candidates ≥ threshold)

#### Scenario: `--include-obsolete` absent → obsolete classification skipped
- GIVEN a change with two unbound decisions
- WHEN `flow drift <change>` runs (no flag)
- THEN `graphify query` is NOT invoked
- AND unbound decisions are silently omitted from the report

#### Scenario: `--since <ISO8601>` filters decisions by `created_at`
- GIVEN a change with one decision created at `2026-06-01` and another at `2026-06-20`
- WHEN `flow drift <change> --since 2026-06-15` runs
- THEN only the `2026-06-20` decision appears in the report

#### Scenario: `--since` with invalid date fails loudly
- GIVEN the user passes `--since yesterday`
- WHEN the command runs
- THEN it exits non-zero with a usage error naming the expected ISO 8601 format

---

### REQ-11: Exit codes

The system SHALL exit `0` when every binding classifies as `still_valid`; `1` when at least one binding classifies as anything other than `still_valid`; and `2` when the terminal state is `unable_to_verify`. Exit `2` MUST take precedence over exit `1`.

#### Scenario: Exit 0 — every binding still_valid
- GIVEN a change whose every binding resolves to `still_valid`
- WHEN `flow drift <change>` runs
- THEN the process exits `0`

#### Scenario: Exit 1 — at least one non-still_valid class present
- GIVEN a change with one `stale_id` binding and one `still_valid` binding
- WHEN `flow drift <change>` runs
- THEN the process exits `1`

#### Scenario: Exit 2 — graph.json missing takes precedence
- GIVEN `graph.json` is absent from the configured path AND the change has one stale binding
- WHEN `flow drift <change>` runs
- THEN the process exits `2`
- AND stderr contains a one-line explanation referencing the missing path

---

### REQ-12: Observability counters

The system SHALL increment, per `flow drift <change>` invocation, the following counters in `~/.flow-engineering/metrics.jsonl`: `drift_invoked_total`, `drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total`. A `record_drift_summary(report)` helper MUST aggregate per-class counts and emit exactly one JSONL line per invocation.

#### Scenario: All per-class counters increment on a multi-class run
- GIVEN a fixture change producing one binding in each of the six classes
- WHEN `flow drift <change>` runs
- THEN each of `drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total` increments by exactly `1`
- AND `drift_invoked_total` increments by `1`

#### Scenario: Unable-to-verify run increments only the dedicated counter
- GIVEN `graph.json` is missing
- WHEN `flow drift <change>` runs
- THEN `drift_unable_to_verify_total` increments by `1`
- AND `drift_invoked_total` still increments by `1`
- AND no per-class counter increments

#### Scenario: Counter names are stable across changes
- GIVEN the documented list above
- WHEN any future change reads these counters (e.g., `flow metrics`)
- THEN the names MUST NOT change without a deprecation period documented in CHANGELOG.md

---

### REQ-13: `update_observation_metadata()` helper

The system SHALL provide `engram_io.update_observation_metadata(observation_id, *, last_verified_at=None, last_drift_class=None)` that appends or replaces ONLY a trailing metadata block distinct from the `code_refs` block. The helper MUST NOT touch the existing `code_refs` block. The helper MUST be idempotent — calling it twice with the same arguments yields one metadata record, not duplicates.

#### Scenario: Write-back appends trailing metadata after code_refs
- GIVEN an observation whose `code_refs` block ends with `{"schema": 1, "nodes": [...]}` and `source: manual`
- WHEN `update_observation_metadata(obs.id, last_verified_at="2026-06-25T20:00:00Z", last_drift_class="still_valid")` runs
- THEN the saved content's `code_refs` block is byte-for-byte unchanged
- AND a new trailing block `<!-- drift_meta -->\n{"last_verified_at": "...", "last_drift_class": "still_valid"}` is appended

#### Scenario: Idempotent re-write — duplicate keys collapse
- GIVEN an observation already carries a `drift_meta` block from a prior run
- WHEN `update_observation_metadata` runs with the same arguments
- THEN exactly one `drift_meta` block exists
- AND the keys are not duplicated

#### Scenario: Missing observation raises structured error
- GIVEN an `observation_id` that does not exist in the backend
- WHEN `update_observation_metadata` runs
- THEN it raises a structured `ObservationNotFound` error (NOT a bare `KeyError`)

---

### REQ-14: Non-breaking — drift never blocks saves or raises

The system MUST guarantee that `flow drift <change>` failures (missing graph, malformed bindings, parser errors per row) NEVER propagate as uncaught exceptions. A missing `graph.json` MUST be reported as a terminal `unable_to_verify` entry (per REQ-11), not as an exception. Per-row parse errors MUST be isolated and surfaced as their own class row in the report. The default MUST be read-only (no observation mutation) unless `--write-back` is explicitly passed.

#### Scenario: Missing graph.json exits 2, not 1, with no traceback
- GIVEN `graph.json` does not exist
- WHEN `flow drift <change>` runs
- THEN the process exits `2`
- AND no Python traceback is printed to stderr
- AND the report contains a single `unable_to_verify` entry

#### Scenario: One malformed binding does not blank the table
- GIVEN a change where one observation has a malformed `code_refs` block (invalid JSON after marker)
- WHEN `flow drift <change>` runs
- THEN the malformed row appears with `class: parse_error` and `detail: <offset>`
- AND all other rows render normally

#### Scenario: `flow drift` does not mutate observations by default
- GIVEN any change with N observations
- WHEN `flow drift <change>` runs without `--write-back`
- THEN no observation content is mutated
- AND `mtime` of the affected observations is unchanged

#### Scenario: `flow drift` is safe to invoke from CI
- GIVEN a CI script invokes `flow drift <change>` with all flags unset
- WHEN the command runs against an arbitrary fixture
- THEN it never raises into the parent process
- AND exit code is one of `{0, 1, 2}`

---

## PR#2 — Verification wiring

### REQ-15: `flow watch --drift` daemon integration

The system SHALL extend the existing `flow watch` daemon to support a `--drift` flag. When set, the daemon watches the per-change directory for file-system changes; on a change to a binding's `file:line` or to an observation, the daemon runs `drift_report_for_change` for the affected change and surfaces findings via (a) the existing observability counters from REQ-12 and (b) a new JSONL event log at `~/.flow-engineering/drift_events.jsonl`. The daemon MUST stay alive across transient `unable_to_verify` states.

#### Scenario: Daemon emits event-log line on detected drift
- GIVEN a `flow watch --drift` daemon is running on change `my-change`
- AND a file change occurs to a binding's `file:line`
- WHEN the daemon observes the change
- THEN exactly one line is appended to `~/.flow-engineering/drift_events.jsonl`
- AND the line contains keys `change`, `decision_id`, `binding_id`, `class`, `detected_at`

#### Scenario: Daemon still-valid change does not emit event-log line
- GIVEN a `flow watch --drift` daemon is running
- AND a file change does NOT alter any binding's resolution
- WHEN the daemon observes the change
- THEN `drift_still_valid_total` increments by `1`
- AND no stdout summary line is emitted (REQ-56 silence) — still-valid findings go to counters only

#### Scenario: Daemon missing graph.json does not crash the watcher
- GIVEN the daemon is running and `graph.json` is absent
- WHEN the watcher ticks
- THEN it logs `unable_to_verify` once to the event log
- AND the watcher process remains alive

> **Drift note (post-drift-hardening, 2026-06-27)**: scenario 2 was reconciled
> per W6 carry-forward resolution. The original spec said "no event-log
> line" but the JSONL append-only writer at `~/.flow-engineering/drift_events.jsonl`
> is shipped separately in change #8 `drift-hardening` (REQ-55). The
> `flow watch --drift` daemon emits a single stdout summary line via the
> `on_summary` callback in `daemon.py::handle_apply_progress_event`; that
> line is now suppressed when `report.total == 0 and not report.graph_unavailable`
> per design D4 (REQ-56 W6 silence rule). The `unable_to_verify` edge
> case preserves the summary line so the user still sees a graph-unavailable
> signal.

---

### REQ-16: SKILL.md prose updates

The system SHALL update the following six SKILL.md files to include a `## Drift detection hook` section describing the six drift classes and when to invoke `flow drift <change>`: `sdd-propose`, `sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`. Each section MUST reference the exit-code contract from REQ-11 and the counter contract from REQ-12.

#### Scenario: All six SKILL.md files contain the section
- GIVEN the six skill files exist under `~/.config/opencode/skills/`
- WHEN the change lands
- THEN each file contains a `## Drift detection hook` heading
- AND each section names all six classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`)
- AND each section references `flow drift <change>` as the invocation point

#### Scenario: `sdd-verify` gains a Step 6 sub-step
- GIVEN `sdd-verify/SKILL.md` previously had Steps 1–5
- WHEN the change lands
- THEN a new sub-step under Step 6 reads "Run `flow drift <change>` and surface findings before declaring green"
- AND the sub-step names the exit codes 0/1/2 from REQ-11

---

## W3 Absorption: REQ-3 BDD Scenario Addition

The following BDD scenario MUST be appended to `tests/bdd/req3_engram_io.feature` to close the W3 gap from verify-report #118 (unit test passes; BDD scenario was missing):

```gherkin
Scenario: Save with valid empty block writes as source: unbound
  Given observation prose ending with code_refs block with empty nodes and source "unbound"
  When save_phase is called for "propose"
  Then the persisted block source is "unbound"
  And binding.extract on persisted content returns an empty list
```

A matching step definition MUST be added to `tests/bdd/test_decision_code_linking_p1_steps.py` (≤6 LOC, reuses the existing `binding.extract` step helper). The scenario text mirrors REQ-3 line 116 in the archived `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md`.

**W2 (REQ-8 counter-name drift in archived spec) is NOT absorbed by this spec.** Spec phase only writes scenarios. The W2 markdown reconciliation in `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` is owned by PR#1 implementation commits (per `work-unit-commits`) and lands as the FIRST commit of PR#1, before any drift-detection code lands, so the counter contract is stable before production reads begin.

---

## Out of Scope (deferred)

- Daemon-only mode (standalone `flow drift --daemon` without the existing `flow watch` flag) — PR#2 adds the `--drift` flag to `flow watch` instead.
- Re-suggestion on `stale_id` — surface-only; the user re-saves via `mem_save`.
- Cross-project drift — `cross-project-federation` owns proper handling (v1 skips + warns on cross-project refs).
- Snapshot-pinned drift — `graph-snapshots` owns; detector takes `graph_path` as a parameter and v1 passes always-current.
- Auto-fixing drift — detector reports; humans fix (matches `flow inspect` read-only precedent).
- `--write-back` default is OFF; only opt-in flips it on.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req9_drift_detection.feature` | NEW | REQ-9 (all 6 classes + unable_to_verify) | 14 |
| `tests/bdd/req10_drift_cli.feature` | NEW | REQ-10, REQ-11 | 9 |
| `tests/bdd/req12_drift_counters.feature` | NEW | REQ-12 | 3 |
| `tests/bdd/req13_drift_metadata.feature` | NEW | REQ-13 | 3 |
| `tests/bdd/req14_drift_resilience.feature` | NEW | REQ-14 | 4 |
| `tests/bdd/req15_drift_daemon.feature` | NEW | REQ-15 | 3 |
| `tests/bdd/req16_skill_prose.feature` | NEW | REQ-16 | 2 |
| `tests/bdd/req3_engram_io.feature` | MODIFY | W3 (REQ-3 absorption) | +1 |
| **Total BDD scenarios** | | | **39** |

Step definitions live in `tests/bdd/test_decision_reality_drift_steps.py` (NEW; one per feature file via pytest-bdd).

---

## Cross-impact

| Queued change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Direct predecessor. Detector walks `code_refs`. W2 reconciliation owned by PR#1 commits. | Required |
| `vector-semantic-search` (#2) | Drift uses `id` lookup, not similarity. Embedding-agnostic. | No conflict |
| `cross-project-federation` (#4) | `CodeRef.project` namespaced. v1 skips + warns cross-project refs. | Compatible |
| `graph-snapshots` (#5) | Detector takes `graph_path` parameter. v1 uses always-current. | Constrains parameter signature |
| `prompt-registry` (#7) | Unrelated layer. | No conflict |
| `observability` (general) | New `drift_*_total` counters plug into existing `observability.increment()`. | Beneficial |

---

## References

- Explore: Engram `sdd/decision-reality-drift/explore` (#120) — Approach C, 6-class taxonomy
- Proposal: Engram `sdd/decision-reality-drift/proposal` (#121) — PR#1/PR#2 breakdown, W2/W3 absorption
- Predecessor spec: `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` (REQ-3, REQ-7, REQ-8)
- Predecessor design: `openspec/changes/archive/2026-06-25-decision-code-linking/design.md`
- Flow Engineering base spec: `c:/dev/proyects/flow-engineering/spec/spec.md`
