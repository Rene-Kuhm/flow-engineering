# Apply Progress: drift-hardening — batch D (FINAL BREAKING CHANGE)

**Date:** 2026-06-27
**Change:** `drift-hardening` (change #8)
**Branch:** main
**Base HEAD:** a1b25a8 (post-batch-C closeout; 21 NEW BDD scenarios committed by orchestrator after separate-copper-asp timeout)
**Final HEAD:** d2bee79 (post-T4.5.d spec bootstrap)
**Strict TDD:** ON
**Status:** success (v0.8.0 BREAKING migration landed)

## Goal

Implement T4.1 + T4.2 + T4.3 + T4.4 + T4.5 + T4.6 from
`openspec/changes/drift-hardening/tasks.md` for batch D (the FINAL batch):
the **REQ-56 W8 dataclass shape migration** (BREAKING: `decision_id` `str→int`,
`scanned_at` `float→str` ISO 8601, `classify_binding` `3-arg→2-arg`) +
CHANGELOG v0.8.0 entry + 6 SKILL.md runtime updates + pyproject version
bump + `openspec/specs/decision-drift/spec.md` capability bootstrap +
apply-progress closeout.

This is the FINAL batch of the `drift-hardening` cluster (change #8) and
ships as v0.8.0 — a public-API breaking release per design D9.

## Branch + PR State

| Field | Value |
|-------|-------|
| Branch | main |
| Base HEAD | a1b25a8 (post-batch-C) |
| Final HEAD | d2bee79 (post-spec-bootstrap) |
| Working tree | clean (only untracked files are out-of-band planning docs in `openspec/changes/{drift-hardening,prompt-registry}/`) |
| Tests | 1102 baseline; 1115 final (+13 NEW: v0.8.0 migration tests in `tests/unit/test_decision_drift_v080_migration.py`) |
| Strict TDD | ON |

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | b609311 | test(unit) | RED fixtures for Finding + DriftReport + classify_binding v0.8.0 migration (REQ-56 W8) |
| 2 | 50de3aa | feat(decision-drift) | Finding + DriftReport + classify_binding v0.8.0 BREAKING migration (REQ-56 W8) |
| 3 | d918db8 | refactor(daemon) | document v0.8.0 contract for finding.decision_id int (REQ-56 W8) |
| 4 | dd0beb6 | chore(version) | bump pyproject 0.7.0 -> 0.8.0 + CHANGELOG v0.8.0 entry (REQ-56 BREAKING) |
| 5 | d5f2147 | docs(skills) | refresh Drift detection hook in 6 SKILL.md runtime files (REQ-57) |
| 6 | d2bee79 | docs(specs) | bootstrap openspec/specs/decision-drift/spec.md capability catalog |
| 7 | (this file) | docs(apply-progress) | batch-d.md — T4.1-T4.6 v0.8.0 BREAKING migration (drift-hardening batch D closeout) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN at its landing.
The T4.6 apply-progress file (this file) is docs-only and lands after the
T4.5.d spec bootstrap.

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T4.1 — Finding.decision_id int + from_legacy shim (REQ-56 W8 part 1) | b609311 (4 RED fixtures: decision_id_is_int_type, from_legacy_emits_deprecation_warning, from_legacy_coerces_str_to_int, from_legacy_non_numeric_str_raises — all fail at import because `_epoch_to_iso` / `from_legacy` / 2-arg signature don't exist yet) | 50de3aa (Finding dataclass: `decision_id: int` annotation + `from_legacy()` classmethod with DeprecationWarning + numeric str coercion + non-numeric ValueError; `_epoch_to_iso()` helper; 13/13 new tests pass; 1115/1115 full suite green) | n/a (clean first cut) |
| T4.2 — DriftReport.scanned_at str ISO + from_legacy shim + unable_reason field (REQ-56 W8 part 2) | b609311 (6 RED fixtures: scanned_at_is_str_iso, from_legacy_emits_deprecation_warning, from_legacy_converts_epoch_to_iso, from_legacy_handles_unable_to_verify_alias, unable_reason_default_none, _epoch_to_iso_helper) | 50de3aa (DriftReport dataclass: `scanned_at: str` ISO 8601 + `graph_mtime: str | None` ISO + `unable_reason: str | None` NEW field + `from_legacy()` classmethod with DeprecationWarning + float epoch coercion + `unable_to_verify` alias mapping; 13/13 new tests pass; 1115/1115 full suite green) | n/a (clean first cut) |
| T4.3 — `classify_binding(ref, graph_nodes)` 2-arg signature + `classify_binding_legacy` 3-arg wrapper (REQ-56 W8 part 3 / OQ-10) | b609311 (3 RED fixtures: classify_binding_2arg_signature, classify_binding_legacy_3arg_emits_deprecation_warning, classify_binding_2arg_unable_to_verify_when_nodes_empty) | 50de3aa (2-arg `classify_binding` primary; 3-arg `classify_binding_legacy` wrapper with DeprecationWarning; `current_id_map` derived internally in O(N) via `_classify_with_id_map()` helper; existing 12 tests migrated to `classify_binding_legacy`; 13/13 new tests pass; 1115/1115 full suite green) | n/a (clean first cut) |
| T4.4 — Update callers in daemon.py + cli.py + observability.py (REQ-56 cascade) | n/a (no new test surface; existing 49 daemon/cli/observability tests cover the migration) | d918db8 (daemon.py `_append_drift_events` documents the v0.8.0 contract: `finding.decision_id` is int, `DriftEvent` coerces via str() for JSONL wire-format backward compat; 49/49 daemon/cli/observability tests still pass) | n/a |
| T4.5.a — pyproject.toml 0.7.0 -> 0.8.0 | n/a (1-line version bump; per design D9 SemVer minor for public API break) | dd0beb6 (no test change; pyproject.toml bumped) | n/a |
| T4.5.b — CHANGELOG v0.8.0 entry | n/a (docs-only; CHANGELOG structure tests deferred to v0.9 follow-up) | dd0beb6 (CHANGELOG placeholder replaced with FINAL v0.8.0 entry: 4 breaking changes + 8 added items + 4-step migration guide + 1115/1115 tests + 53 BDD scenarios + 1-release shim window) | n/a |
| T4.5.c — 6 SKILL.md runtime updates (REQ-57 hook refresh) | n/a (runtime config files OUTSIDE repo; --allow-empty commit per existing pattern) | d5f2147 (6 SKILL.md files at C:\Users\insyd\.config\opencode\skills\ updated with v0.8.0 API note appended to each `## Drift detection hook` section: int decision_id, ISO scanned_at, graph_unavailable + unable_reason, 2-arg classify_binding, 1-release shims) | n/a |
| T4.5.d — `openspec/specs/decision-drift/spec.md` capability bootstrap | n/a (docs-only; mirrors change #6 observability + change #7 prompt-registry pattern) | d2bee79 (NEW capability spec at openspec/specs/decision-drift/spec.md: v0.8.0 migration note header + REQ-9..16 + REQ-55..59 + 21 NEW BDD scenarios catalogued + dataclass shape contract + counter catalog + cross-impact table) | n/a |

## File-by-file diff summary

| File | Action | LOC delta | Notes |
|------|--------|-----------|-------|
| `src/flow_engineering/decision_drift.py` | MODIFY | +120/-30 | T4.1+T4.2+T4.3 GREEN: `Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`, `_epoch_to_iso`, `unable_reason` field, `scan_change` emits ISO `scanned_at` |
| `tests/unit/test_decision_drift_v080_migration.py` | NEW | +262 | 13 RED fixtures for T4.1+T4.2+T4.3 |
| `tests/unit/test_decision_drift.py` | MODIFY | +5/-5 | Migrate 12 `classify_binding(binding, nodes, id_map)` 3-arg calls to `classify_binding_legacy`; update `test_scan_change_snapshot` to compare ISO `graph_mtime` |
| `src/flow_engineering/daemon.py` | MODIFY | +6/-0 | T4.4: `_append_drift_events` documents v0.8.0 contract for `finding.decision_id` int |
| `pyproject.toml` | MODIFY | +1/-1 | T4.5.a: `version = "0.8.0"` (was `0.7.0`) |
| `CHANGELOG.md` | MODIFY | +33/-14 | T4.5.b: v0.8.0-dev placeholder replaced with FINAL v0.8.0 entry |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | ~+850 bytes each | T4.5.c: v0.8.0 API note appended to each `## Drift detection hook` section (OUTSIDE repo; --allow-empty commit) |
| `openspec/specs/decision-drift/spec.md` | NEW | +366 | T4.5.d: capability spec bootstrap (mirrors change #6 observability + change #7 prompt-registry pattern) |
| `openspec/changes/drift-hardening/apply-progress/batch-d.md` | NEW | (this file) | T4.6: batch D closeout |

## Test delta

| Source | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Unit tests | 1102 | 1115 | +13 (T4.1 + T4.2 + T4.3) |
| BDD scenarios | 53 | 53 | 0 (no new BDD in batch D; the 21 NEW from REQ-57 already landed in batch C) |
| Test runner | `uv run pytest -x --tb=short -q` | 62.37s | 62.86s |

The +13 new unit tests are all in `tests/unit/test_decision_drift_v080_migration.py`:
- T4.1: 4 tests (Finding decision_id int type, from_legacy DeprecationWarning, from_legacy numeric str coercion, from_legacy non-numeric ValueError)
- T4.2: 6 tests (DriftReport scanned_at str ISO, from_legacy DeprecationWarning, from_legacy float coercion, from_legacy unable_to_verify alias, unable_reason default None, _epoch_to_iso helper)
- T4.3: 3 tests (classify_binding 2-arg signature, classify_binding_legacy 3-arg DeprecationWarning, classify_binding 2-arg UNABLE_TO_VERIFY for empty graph_nodes)

## Deviations

1. **No `decision_id_int` @property added**: the orchestrator brief mentioned
   adding a `@property decision_id_int` for code that needs strict int. Since
   `Finding.decision_id` IS now `int` directly (the v0.8.0 contract), the
   property is redundant. All existing `int(finding.decision_id)` call sites
   simplify to direct `finding.decision_id` access.

2. **No strict `__post_init__` coercion in `Finding`**: the design.md
   suggested `__post_init__` with numeric str coercion + DeprecationWarning.
   The orchestrator brief specified `from_legacy()` classmethod as the
   migration path. Followed the brief — `Finding(decision_id="obs-1", ...)`
   continues to work via Python duck-typed dataclass field assignment (no
   `__init__` enforcement); `Finding.from_legacy(decision_id="obs-1", ...)`
   is the explicit migration path with DeprecationWarning.

3. **`DriftReport.graph_unavailable` kept as canonical field name**: the
   design.md suggested renaming `graph_unavailable` → `unable_to_verify` (with
   `@property graph_unavailable` 1-release alias). The orchestrator brief
   kept `graph_unavailable` as canonical and added `unable_reason` as new
   field; `from_legacy(unable_to_verify=True)` maps to
   `graph_unavailable=True`. Followed the brief.

4. **`classify_binding` accepts BOTH 2-arg and 3-arg signatures**: OQ-10
   specified a clean 2-arg break with TypeError for 3-arg callers. The
   orchestrator brief specified `classify_binding_legacy` 3-arg wrapper as
   the 1-release migration path. Followed the brief — soft migration via
   wrapper + DeprecationWarning (no TypeError for 3-arg callers).

5. **No BDD scenarios added in batch D**: batch C already landed the 21 NEW
   BDD scenarios (REQ-57 W4). Batch D focuses on the v0.8.0 dataclass
   migration + closeout docs.

6. **6 SKILL.md files updated as --allow-empty commit**: the SKILL.md files
   live OUTSIDE the repo at `C:\Users\insyd\.config\opencode\skills\` (runtime
   config dir). Per the existing pattern (change #5 graph-snapshots + change
   #6 observability), batch D uses --allow-empty commits with byte-delta
   verification documented in the commit message.

## Risks

1. **Hidden callers may still pass float `scanned_at` / str `decision_id` /
   3-arg `classify_binding`**: the 1-release `DeprecationWarning` shims absorb
   these callers, but the warnings will surface in `flow drift` / daemon
   stdout. Operators should grep their logs for
   `DeprecationWarning: Finding.decision_id constructed with str` /
   `DeprecationWarning: DriftReport constructed with legacy float scanned_at`
   / `DeprecationWarning: classify_binding 3-arg signature deprecated` and
   update callers before v0.9.0.

2. **Existing tests use str `decision_id` in fixtures**:
   `Finding(decision_id="obs-1", ...)` and `Finding(decision_id="1", ...)`
   in test fixtures continue to work via Python duck-typing. These tests
   emit `DeprecationWarning` once pytest enables `filterwarnings = "error"`
   (currently not configured). Future test cleanup should migrate fixtures
   to int `decision_id` per the v0.8.0 contract.

3. **`DriftEvent` JSONL wire format still uses str `decision_id`**: the
   `_append_drift_events` helper coerces via `str(finding.decision_id)`
   for JSONL wire-format backward compat. Future v1 follow-up may flip
   `DriftEvent.decision_id` to `int` once the wire format itself migrates
   (REQ-55 deferred to v1.0).

## Next steps

- **sdd-verify drift-hardening cluster** (next): run the full suite + BDD
  scenarios + closeout unit tests; produce verify-report for the PR#1
  review.
- **sdd-archive drift-hardening cluster**: sync delta specs to
  `openspec/changes/archive/2026-06-27-drift-hardening/`; preserve REQ-56
  v0.8.0 migration note in the archive.
- **change #7 PR#2 apply**: prompt-registry PR#2 (REQ-49..54) follows
  after drift-hardening archive; preserves REQ-55..59 numbering.

## Coordination notes

- **MANDATORY**: prompt-registry change #7 PR#1 archived BEFORE drift-hardening
  apply started (preserves REQ-55..59 numbering; REQ-45..54 reserved for
  prompt-registry per Engram #183 + #201). ✅ satisfied.

## Engram observation

This apply-progress observation is mirrored to Engram as
`sdd/drift-hardening/apply-progress-batch-d` (architecture type, project
scope). The merged root apply-progress is mirrored as
`sdd/drift-hardening/apply-progress-merged` capturing all 4 batches
(A + B + C + D).
