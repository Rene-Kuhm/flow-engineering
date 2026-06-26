# Tasks: decision-code-linking

**Change:** `decision-code-linking`
**Approach:** D (trailing `code_refs` block + auto-suggest) — see `proposal.md` / design.md
**Delivery:** `force-chained` · Chain: `stacked-to-main` · Strict TDD: ON

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | PR#1 ~390, PR#2 ~280 (combined ~670) |
| 400-line budget risk | Low (both PRs under budget) |
| Chained PRs recommended | Yes |
| Suggested split | PR#1 (binding + backfill) → PR#2 (auto-suggest + surface) |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low
```

### Work Units

| PR | Goal | Base | Notes |
|----|------|------|-------|
| PR#1 | Binding format + save hook + backfill | `main` | Independently mergeable. BDD scenarios for REQ-1..REQ-5. |
| PR#2 | Auto-suggest + `flow inspect` + metrics + SKILL.md | `main` | Targets main independently of PR#1; review-friendly stacked branch. BDD scenarios for REQ-6..REQ-8. |

---

## Phase 1: PR#1 — Bootstrap

- [ ] **1.1.1** Scaffold PR#1 files with empty stubs that compile.
  - Type: bootstrap · TDD: N/A · LOC: ~20 · Depends: —
  - Files: `src/flow_engineering/binding.py` (CodeRef class), `src/flow_engineering/graphify_query.py` (query_nodes stub), `src/flow_engineering/engram_io.py` (+ ext point), `scripts/backfill_code_refs.py` (CLI skeleton), `tests/unit/test_binding.py`, `tests/unit/test_engram_io_code_refs.py`, `tests/unit/test_backfill.py`
  - Acceptance: All files import; no behavior yet
  - Commit: `chore: scaffold decision-code-linking pr1 stubs`

## Phase 2: PR#1 — `binding.py` (Strict TDD)

- [ ] **1.2.1** RED — golden fixtures for extract/parse/format/round-trip/malformed (~10 cases).
  - Type: test · TDD: RED · LOC: ~25 · Depends: 1.1.1
  - Files: `tests/unit/test_binding.py`
  - Acceptance: REQ-1 scenarios, REQ-2 scenarios
  - Commit: `test(binding): golden fixtures for code_refs parse and format`

- [ ] **1.2.2** GREEN — implement `extract_code_refs`, `parse_code_refs`, `format_code_refs_block`, `split_prose_and_refs`, `CodeRef` dataclass, `ParseError` (with line offset).
  - Type: code · TDD: GREEN · LOC: ~60 · Depends: 1.2.1
  - Files: `src/flow_engineering/binding.py`
  - Acceptance: REQ-1 (all 4 scenarios), REQ-2 (all 4 scenarios)
  - Commit: `feat(binding): implement code_refs parse, format, split`

- [ ] **1.2.3** REFACTOR — consolidate validation, tighten `ParseError` offsets, sort-by-id canonicalization.
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 1.2.2
  - Files: `src/flow_engineering/binding.py`
  - Acceptance: REQ-2 round-trip + malformed-with-offset pass after refactor
  - Commit: `refactor(binding): tighten ParseError offsets and validation`

## Phase 3: PR#1 — `graphify_query.py` (Strict TDD)

- [ ] **1.3.1** RED — mocked subprocess tests for `query_nodes` (cache hit/miss, Jaccard fallback, fail-open on missing binary/JSON/timeout).
  - Type: test · TDD: RED · LOC: ~30 · Depends: 1.1.1
  - Files: `tests/unit/test_graphify_query.py`
  - Acceptance: cache + Jaccard + fail-open scenarios pre-implementation
  - Commit: `test(graphify_query): mock subprocess with cache and fallback`

- [ ] **1.3.2** GREEN — implement `query_nodes` (CLI wrapper + sha1+graph.json mtime cache + Jaccard fallback).
  - Type: code · TDD: GREEN · LOC: ~60 · Depends: 1.3.1
  - Files: `src/flow_engineering/graphify_query.py`
  - Acceptance: cache hit/miss, Jaccard, fail-open all green
  - Commit: `feat(graphify_query): CLI wrapper with cache and Jaccard fallback`

- [ ] **1.3.3** REFACTOR — extract cache key derivation, tighten fail-open error handling, document cache TTL.
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 1.3.2
  - Files: `src/flow_engineering/graphify_query.py`
  - Acceptance: tests pass unchanged; cache key derivation isolated
  - Commit: `refactor(graphify_query): extract cache key + fail-open paths`

## Phase 4: PR#1 — `engram_io.py` save_phase hook (Strict TDD)

- [ ] **1.4.1** RED — InMemoryBackend test for `save_phase` auto-appending empty unbound block when content lacks marker.
  - Type: test · TDD: RED · LOC: ~15 · Depends: 1.2.2
  - Files: `tests/unit/test_engram_io_code_refs.py`
  - Acceptance: REQ-3 scenario "no-marker" + "valid-block" pre-implementation
  - Commit: `test(engram_io): save_phase appends code_refs block`

- [ ] **1.4.2** GREEN — hook `save_phase` to call `binding.extract` + `format` unbound when no block; preserve existing blocks.
  - Type: code · TDD: GREEN · LOC: ~20 · Depends: 1.4.1
  - Files: `src/flow_engineering/engram_io.py`
  - Acceptance: REQ-3 scenarios "no-marker", "valid-block", "empty-block" green
  - Commit: `feat(engram_io): save_phase auto-appends unbound block`

- [ ] **1.4.3** RED — tests for malformed-block rejection (no row written) + `load_code_refs(phase)` accessor.
  - Type: test · TDD: RED · LOC: ~15 · Depends: 1.4.2
  - Files: `tests/unit/test_engram_io_code_refs.py`
  - Acceptance: REQ-3 malformed + unknown-schema pre-implementation
  - Commit: `test(engram_io): validate block + load_code_refs accessor`

- [ ] **1.4.4** GREEN — add block validation in `save_phase` (reject before write) + `load_code_refs` accessor.
  - Type: code · TDD: GREEN · LOC: ~10 · Depends: 1.4.3
  - Files: `src/flow_engineering/engram_io.py`
  - Acceptance: REQ-3 all 5 scenarios green; REQ-5 "older binary reads" scenario
  - Commit: `feat(engram_io): validate block + load_code_refs accessor`

- [ ] **1.4.5** REFACTOR — extract `validate_block` helper into `binding.py`; reduce duplication.
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 1.4.4
  - Files: `src/flow_engineering/engram_io.py`, `src/flow_engineering/binding.py`
  - Acceptance: tests pass unchanged; validation centralized
  - Commit: `refactor(binding): extract validate_block helper`

## Phase 5: PR#1 — backfill script (Strict TDD)

- [ ] **1.5.1** RED — seeded-obs tests: dry-run reports counts (no writes), `--apply` mutates only missing obs, idempotent on re-run, pre-image JSONL written.
  - Type: test · TDD: RED · LOC: ~25 · Depends: 1.4.4
  - Files: `tests/unit/test_backfill.py`
  - Acceptance: REQ-4 all 4 scenarios pre-implementation
  - Commit: `test(backfill): dry-run, apply, idempotency, preimage`

- [ ] **1.5.2** GREEN — implement backfill script (`--dry-run` default, `--apply`, `--project insyd`, preimage → `~/.flow-engineering/backfill-preimage.jsonl`).
  - Type: code · TDD: GREEN · LOC: ~40 · Depends: 1.5.1
  - Files: `scripts/backfill_code_refs.py`
  - Acceptance: REQ-4 all 4 scenarios green; preserves `created_at`; advances `updated_at`
  - Commit: `feat(backfill): idempotent script with preimage safety net`

- [ ] **1.5.3** REFACTOR — extract preimage writer + idempotency check (`source: backfill` ⇒ skip).
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 1.5.2
  - Files: `scripts/backfill_code_refs.py`
  - Acceptance: tests pass unchanged; idempotency + preimage isolated
  - Commit: `refactor(backfill): extract preimage writer and idempotency check`

## Phase 6: PR#1 — BDD feature files (one per requirement)

- [ ] **1.6.1** BDD — write feature files for REQ-1 (3 scenarios) and REQ-2 (3 scenarios).
  - Type: bdd · TDD: N/A · LOC: ~15 · Depends: 1.2.3
  - Files: `tests/bdd/decision_code_linking_p1_block.feature`, `tests/bdd/decision_code_linking_p1_roundtrip.feature`
  - Acceptance: REQ-1 + REQ-2 scenarios expressed in Gherkin
  - Commit: `test(bdd): block format + roundtrip features (REQ-1, REQ-2)`

- [ ] **1.6.2** BDD — feature file for REQ-3 (5 scenarios: no-marker, valid-block, malformed, unknown-schema, empty-block).
  - Type: bdd · TDD: N/A · LOC: ~15 · Depends: 1.4.4
  - Files: `tests/bdd/decision_code_linking_p1_save.feature`
  - Acceptance: REQ-3 scenarios expressed
  - Commit: `test(bdd): save_observation feature (REQ-3)`

- [ ] **1.6.3** BDD — feature file for REQ-4 (4 scenarios: dry-run, apply prose-preserved, created_at/updated_at, idempotent).
  - Type: bdd · TDD: N/A · LOC: ~15 · Depends: 1.5.2
  - Files: `tests/bdd/decision_code_linking_p1_backfill.feature`
  - Acceptance: REQ-4 scenarios expressed
  - Commit: `test(bdd): backfill feature (REQ-4)`

- [ ] **1.6.4** BDD — feature file for REQ-5 (3 scenarios: no-marker-saves, older-binary-reads, FTS5-still-matches).
  - Type: bdd · TDD: N/A · LOC: ~10 · Depends: 1.4.4
  - Files: `tests/bdd/decision_code_linking_p1_nonbreaking.feature`
  - Acceptance: REQ-5 scenarios expressed
  - Commit: `test(bdd): non-breaking feature (REQ-5)`

- [ ] **1.6.5** BDD — pytest-bdd step definitions for all 5 PR#1 feature files.
  - Type: bdd · TDD: N/A · LOC: ~25 · Depends: 1.6.1, 1.6.2, 1.6.3, 1.6.4
  - Files: `tests/bdd/test_decision_code_linking_p1_steps.py`
  - Acceptance: `pytest tests/bdd/ -k p1` runs all 5 features green
  - Commit: `test(bdd): pr1 step definitions`

## Phase 7: PR#1 — Cleanup

- [ ] **1.7.1** Update `CHANGELOG.md` with PR#1 entry (binding format, save hook, backfill shipped).
  - Type: docs · TDD: N/A · LOC: ~5 · Depends: 1.6.5
  - Files: `CHANGELOG.md`
  - Acceptance: PR#1 entry references REQ-1..REQ-5 success criteria
  - Commit: `docs: changelog entry for pr1`

---

## Phase 8: PR#2 — Bootstrap (after PR#1 merged)

- [ ] **2.1.1** Scaffold PR#2 files with empty stubs.
  - Type: bootstrap · TDD: N/A · LOC: ~15 · Depends: PR#1 merged
  - Files: `src/flow_engineering/metrics.py` (record/read_all stubs), `src/flow_engineering/engram_io.py` (+ `auto_suggest_code_refs` no-op), `src/flow_engineering/cli.py` (`flow inspect` stub), 3 test files empty, 6 SKILL.md files get placeholder "Step 5: Resolve code_refs" header
  - Acceptance: All files import; `flow inspect --help` lists the command
  - Commit: `chore: scaffold decision-code-linking pr2 stubs`

## Phase 9: PR#2 — `auto_suggest_code_refs` (Strict TDD)

- [ ] **2.2.1** RED — tests for `auto_suggest_code_refs` (threshold filter, `max_results` cap, prompt shown when ≥1 candidate).
  - Type: test · TDD: RED · LOC: ~20 · Depends: 2.1.1
  - Files: `tests/unit/test_auto_suggest.py`
  - Acceptance: REQ-6 "prompts when ≥1 candidate clears threshold" pre-impl
  - Commit: `test(auto_suggest): threshold filter and confirmation prompt`

- [ ] **2.2.2** GREEN — implement `auto_suggest_code_refs` (delegates to `graphify_query.query_nodes`, filters by threshold, prompts user on candidates).
  - Type: code · TDD: GREEN · LOC: ~40 · Depends: 2.2.1
  - Files: `src/flow_engineering/engram_io.py`
  - Acceptance: REQ-6 "prompts" + "user-confirms-none" + "below-threshold" scenarios green
  - Commit: `feat(engram_io): auto_suggest_code_refs with threshold filter`

- [ ] **2.2.3** REFACTOR — extract confirmation prompt logic; add `--non-interactive` and `--no-suggest` flags handling.
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 2.2.2
  - Files: `src/flow_engineering/engram_io.py`
  - Acceptance: REQ-6 "graphify-unavailable" + "no-suggest-flag" scenarios pass; prompt logic isolated
  - Commit: `refactor(auto_suggest): extract confirmation prompt and flags`

## Phase 10: PR#2 — `metrics.py` (Strict TDD)

- [ ] **2.3.1** RED — tests for `record(event, **fields)` (appends JSONL) and `read_all()` (parses back into dict-of-lists).
  - Type: test · TDD: RED · LOC: ~10 · Depends: 2.1.1
  - Files: `tests/unit/test_metrics.py`
  - Acceptance: REQ-8 "manual_count" + "auto_suggest_hits" pre-impl
  - Commit: `test(metrics): append and read JSONL counters`

- [ ] **2.3.2** GREEN — implement `metrics.record` and `metrics.read_all` against `~/.flow-engineering/metrics.json`.
  - Type: code · TDD: GREEN · LOC: ~25 · Depends: 2.3.1
  - Files: `src/flow_engineering/metrics.py`
  - Acceptance: REQ-8 "manual_count" + "auto_suggest_hits" + "avg_bindings" + "backfill_coverage" green
  - Commit: `feat(metrics): JSONL record/read with derived counters`

- [ ] **2.3.3** REFACTOR — add 1MB rotation stub, tighten JSONL format (single line per event, sorted read).
  - Type: refactor · TDD: REFACTOR · LOC: ~5 · Depends: 2.3.2
  - Files: `src/flow_engineering/metrics.py`
  - Acceptance: tests pass unchanged; rotation hook isolated
  - Commit: `refactor(metrics): rotation at 1MB and JSONL tightening`

## Phase 11: PR#2 — `flow inspect` CLI (Strict TDD)

- [ ] **2.4.1** RED — Click CliRunner test for `flow inspect <change>` table rendering (3 decisions, second has 2 bindings ⇒ 4 rows).
  - Type: test · TDD: RED · LOC: ~15 · Depends: 2.1.1
  - Files: `tests/unit/test_cli_inspect.py`
  - Acceptance: REQ-7 "renders-one-row-per-binding" pre-impl
  - Commit: `test(cli): inspect renders code_refs table`

- [ ] **2.4.2** GREEN — implement `flow inspect <change>` (queries Engram via `EngramClient.search_cross_session`, renders table with `id, label, file:line, confidence, source`).
  - Type: code · TDD: GREEN · LOC: ~45 · Depends: 2.4.1
  - Files: `src/flow_engineering/cli.py`
  - Acceptance: REQ-7 "renders-rows" + "no-bindings-shows-unbound" + "last_verified" green
  - Commit: `feat(cli): flow inspect renders code_refs table`

- [ ] **2.4.3** REFACTOR — extract table renderer; add freshness column (`graph.json` mtime vs obs `updated_at`); per-row parse-error isolation.
  - Type: refactor · TDD: REFACTOR · LOC: ~10 · Depends: 2.4.2
  - Files: `src/flow_engineering/cli.py`
  - Acceptance: REQ-7 "malformed-block-does-not-blank-table" passes; renderer isolated
  - Commit: `refactor(cli): extract table renderer + freshness + error isolation`

## Phase 12: PR#2 — SKILL.md prose updates (no logic, just text)

- [ ] **2.5.1** Add identical "Step 5: Resolve code_refs" sub-step block to 6 SKILL.md files.
  - Type: docs · TDD: N/A · LOC: ~40 · Depends: 2.4.2
  - Files: `.config/opencode/skills/sdd-propose/SKILL.md`, `sdd-design/SKILL.md`, `sdd-tasks/SKILL.md`, `sdd-apply/SKILL.md`, `sdd-verify/SKILL.md`, `sdd-archive/SKILL.md`
  - Acceptance: All 6 files contain identical prose block referencing `binding.extract_code_refs` and `flow inspect`
  - Commit: `docs(skills): step 5 resolve code_refs across 6 sd* files`

## Phase 13: PR#2 — BDD feature files (one per requirement)

- [ ] **2.6.1** BDD — feature file for REQ-6 (5 scenarios: prompts, confirms-none, graphify-unavailable, below-threshold, --no-suggest).
  - Type: bdd · TDD: N/A · LOC: ~20 · Depends: 2.2.2
  - Files: `tests/bdd/decision_code_linking_p2_auto_suggest.feature`
  - Acceptance: REQ-6 scenarios expressed
  - Commit: `test(bdd): auto-suggest feature (REQ-6)`

- [ ] **2.6.2** BDD — feature file for REQ-7 (4 scenarios: renders-rows, no-bindings, last_verified, malformed-isolated).
  - Type: bdd · TDD: N/A · LOC: ~15 · Depends: 2.4.2
  - Files: `tests/bdd/decision_code_linking_p2_inspect.feature`
  - Acceptance: REQ-7 scenarios expressed
  - Commit: `test(bdd): flow inspect feature (REQ-7)`

- [ ] **2.6.3** BDD — feature file for REQ-8 (4 scenarios: manual_count, auto_suggest_hits, avg_bindings, backfill_coverage).
  - Type: bdd · TDD: N/A · LOC: ~15 · Depends: 2.3.2
  - Files: `tests/bdd/decision_code_linking_p2_metrics.feature`
  - Acceptance: REQ-8 scenarios expressed
  - Commit: `test(bdd): metrics counters feature (REQ-8)`

- [ ] **2.6.4** BDD — pytest-bdd step definitions for all 3 PR#2 feature files.
  - Type: bdd · TDD: N/A · LOC: ~20 · Depends: 2.6.1, 2.6.2, 2.6.3
  - Files: `tests/bdd/test_decision_code_linking_p2_steps.py`
  - Acceptance: `pytest tests/bdd/ -k p2` runs all 3 features green
  - Commit: `test(bdd): pr2 step definitions`

## Phase 14: PR#2 — Cleanup

- [ ] **2.7.1** Update `CHANGELOG.md` with PR#2 entry (auto-suggest, flow inspect, metrics shipped).
  - Type: docs · TDD: N/A · LOC: ~5 · Depends: 2.6.4
  - Files: `CHANGELOG.md`
  - Acceptance: PR#2 entry references REQ-6..REQ-8 success criteria
  - Commit: `docs: changelog entry for pr2`

---

## Implementation Order (rationale)

PR#1 builds strictly bottom-up: scaffold → binding (pure functions, no I/O) → graphify_query (wraps external CLI) → engram_io.save_phase hook (integrates both) → backfill script (consumes engram_io) → BDD → CHANGELOG. Each phase depends on the previous; no parallelism inside PR#1.

PR#2 layers onto PR#1's surface: scaffold → auto_suggest (extends save_phase) → metrics (sidecar observer) → cli inspect (consumer of load_code_refs + graph.json mtime) → SKILL.md prose (documents the surface) → BDD → CHANGELOG. PR#2 targets `main` independently per `stacked-to-main` strategy; orchestrator merges PR#1 first to keep the surface stable, but PR#2's branch does not require PR#1's branch as base.

## Dependency Diagram

```
PR#1 chain (target: main)
  1.1.1 → 1.2.1 → 1.2.2 → 1.2.3 → 1.4.1 → 1.4.2 → 1.4.3 → 1.4.4 → 1.4.5
         └→ 1.3.1 → 1.3.2 → 1.3.3 ──────────────────────────────────────┐
         └→ 1.5.1 → 1.5.2 → 1.5.3 ──────────────────────────────────────┤
                              └→ 1.6.1..1.6.5 ─→ 1.7.1                  │
                                                                         ▼
PR#2 chain (target: main; stacked branch, independent base)
  2.1.1 → 2.2.1 → 2.2.2 → 2.2.3 ──────────────────────────────────────┐
         └→ 2.3.1 → 2.3.2 → 2.3.3 ─────────────────────────────────────┤
         └→ 2.4.1 → 2.4.2 → 2.4.3 → 2.5.1 ────────────────────────────┤
                              └→ 2.6.1..2.6.4 ─→ 2.7.1                 │
                                                                         ▼
```

## Review Workload Forecast (verdict)

- **Estimated total changed lines per PR**: PR#1 ~390 LOC, PR#2 ~280 LOC. Combined ~670 LOC across 2 PRs.
- **Either PR exceeds the 400-line budget**: **No.** PR#1 sits ~10 LOC under; PR#2 ~120 LOC under. Real-world drift may push PR#1 over by 30-50 LOC if tests expand; if so, split a BDD feature into PR#2's bootstrap.
- **Chained PRs recommended**: **Yes** — both per user `delivery_strategy: force-chained` and the change spans 2 self-contained work units (binding vs. surface).
- **400-line budget risk**: **Low.**
- **Decision needed before apply**: **No** — `force-chained` is auto-chain; orchestrator proceeds with PR#1 first per `stacked-to-main`.