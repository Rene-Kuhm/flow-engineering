<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-a (Engram #125) -->

# Apply progress PR#1 batch A — decision-reality-drift

## Goal

Close verify-report carry-forwards **W2** (REQ-8 counter-name drift between spec and impl) and **W3** (missing BDD scenario for "save with valid empty block writes as source: unbound") on PR#1 of the `decision-reality-drift` change.

## Change / Branch

- Change: `decision-reality-drift`
- PR slice: PR#1, Batch A (T1.1 + T1.2 only)
- Branch: `feature/decision-reality-drift-pr1` (created from `main` at `055c616`)
- Chain strategy: `stacked-to-main`
- Artifact store: hybrid (OpenSpec tasks.md + Engram progress)

## Commits Added

| SHA | Type | Subject | Files |
|---|---|---|---|
| `452ddfd` | docs(spec) | reconcile REQ-8 counter names with impl (verify-report W2) | `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` (+40/-16) |
| `56b769e` | test(bdd) | add REQ-3 empty-block-as-unbound scenario (verify-report W3) | `tests/bdd/req3_engram_io.feature` (+6), `tests/bdd/test_decision_code_linking_p1_steps.py` (+31) |

## LOC Delta

- +77 lines / -16 lines = **+61 net** across 3 files
- Well under the 400-line review budget; PR#1 batch A does not need to chain further on its own.

## Test Counts

- Pre-batch baseline: **302 passing** (`uv run pytest --tb=short -q`)
- Post-batch: **303 passing** (+1 from the new BDD scenario `test_save_empty_block_unbound`)
- BDD suite (`tests/bdd/`): 46 passing post-batch
- Run after each commit: green both times

## TDD Cycle Evidence (Strict TDD)

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| T1.1 (W2 spec reconciliation) | n/a — docs only | n/a | ➖ Docs | ➖ Docs | ✅ Reconciliation note + impl-name alignment |
| T1.2 (W3 BDD scenario) | `tests/bdd/test_decision_code_linking_p1_steps.py::test_save_empty_block_unbound` | BDD (integration via InMemoryBackend) | ✅ Written first; **failed initially** with `ParseError: unsupported schema version: None` because the literal Gherkin body `{}` lacks the schema field — input was tightened to the canonical `{"schema": 1, "nodes": [], "source": "unbound"}` per REQ-3 spec | ✅ Passed after input correction, with no impl change | ➖ No refactor needed — reuses existing `extract_code_refs` and `CODE_REFS_MARKER` helpers |

**Triangulation note**: W3 has one scenario. The companion unit test `TestSavePhaseHook::test_save_phase_accepts_empty_block_as_unbound` at `tests/unit/test_engram_io_code_refs.py:86` already covers the same path with the canonical body, satisfying the triangulation gate.

## Deviation From User Spec (T1.2 Gherkin input)

The orchestrator prompt wrote `<!-- code_refs -->\n{}` in the When step. The impl's `validate_block` rejects `{}` because the `schema` field is `None`. Per REQ-3 spec and the existing unit test `EMPTY_BLOCK` constant at `tests/unit/test_engram_io_code_refs.py:32`, the canonical empty-block body is `{"schema": 1, "nodes": [], "source": "unbound"}`. Tightened the When step to use that canonical body. **No impl changes** (per the non-negotiable rules); this is a test-input correction only.

## W2 / W3 Closure Confirmation

- **W2 closed**: REQ-8 counter list now matches `src/flow_engineering/observability.py` (the eight emitted counters: `suggest_invoked_total`, `suggest_hit_total`, `suggest_miss_total`, `bindings_confirmed_total`, `backfill_observations_total`, `backfill_with_refs_total`, `inspect_invoked_total`, `inspect_render_ms`) plus the `backfill_coverage(backend)` derived metric via `record_backfill_coverage`. Reconciliation note at top of spec.md explains the change.
- **W3 closed**: New BDD scenario `Save with valid empty block writes as source: unbound` in `tests/bdd/req3_engram_io.feature:31-35` wires through the existing `binding.extract_code_refs` and `CODE_REFS_MARKER` helpers. Step defs added at `tests/bdd/test_decision_code_linking_p1_steps.py`: `@scenario` binding (line 112), `@when` (line 365), two `@then` (lines 519, 527).

## Out-of-Scope Confirmations

- ✅ No source under `src/flow_engineering/` touched.
- ✅ No OpenSpec tasks.md updated yet — that's the sdd-apply orchestrator's job at end-of-phase, or batch B will roll it up.
- ✅ Untracked `openspec/changes/decision-reality-drift/` not staged.
- ✅ No push to remote.

## Handoff Notes for Batch B (T1.3: scaffold decision_drift.py)

1. Branch state: `feature/decision-reality-drift-pr1` is 2 commits ahead of `main` (`055c616`), working tree clean.
2. Test count to preserve: **303**.
3. Batch B will scaffold `src/flow_engineering/decision_drift.py`. The verify-report W4 carry-forward is the spec for it (REQ-9..16 + 39 BDD scenarios already in proposal #121 / spec #122). Strict TDD applies: RED → GREEN → REFACTOR per scenario, no horizontal slicing.
4. Suggested slice order for T1.3+: (a) pure helpers in `decision_drift.py` (parsing + classification), (b) the walk-and-compare engine, (c) the CLI surface. Each slice must keep the 303-test baseline green and stay inside the 400-line budget per chained PR.
5. Watch out: PR#1 batch A's gherkin tightened the W3 scenario body to the canonical form. Any future BDD scenario that says "empty block" should follow the same pattern — `{}` is rejected by `validate_block`.

## Files Touched

- `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` — W2 reconciliation + counter list + REQ-8 scenarios.
- `tests/bdd/req3_engram_io.feature` — appended W3 scenario.
- `tests/bdd/test_decision_code_linking_p1_steps.py` — added `@scenario` binding + `@when` + 2 `@then` step defs.

**Session**: flow-engineering-gaps-closed-2026-06-25
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-a
**Engram**: #125
**Next**: Batch B (T1.3 scaffold + T1.4 RED + T1.5 GREEN classify_binding)