<!-- explore.md: v0.9.0-hardening. Source: sdd-explore (executor). -->
# v0.9.0 hardening — exploration

**Change:** `v0.9.0-hardening` (compat-shim removal follow-up to drift-hardening)
**Date:** 2026-06-27
**Mode:** Strict TDD ON (per `openspec/changes/archive/2026-06-27-drift-hardening/apply-progress/merged.md` line 8)
**Source change:** `drift-hardening` (change #8, v0.8.0 BREAKING, archived 2026-06-27)
**Source verify-report:** `openspec/changes/archive/2026-06-27-drift-hardening/verify-report.md` — 9 WARNING findings; **W1/W2/W3 are the 3 intentional compat shims**
**Current version:** v0.8.0 (`pyproject.toml:3`, `CHANGELOG.md:39`)
**HEAD at exploration:** `cb82274` (`chore(archive): close out drift-hardening v0.8.0 + prompt-registry PR#1`, per Engram #259)
**Branch:** `main` (clean working tree per Engram #259)

---

## Status: explored → ready for sdd-propose

The 3 compat shims from drift-hardening W1/W2/W3 are well-bounded: production callers are all internal (`src/flow_engineering/`), the soft-migration paths use `DeprecationWarning` (per D9 1-release deprecation window in design.md D9), and the v0.8.0 CHANGELOG entry explicitly commits to shim removal in v0.9.0 (lines 43, 44, 46, 74). Removal is mechanical (delete `from_legacy` classmethods + `classify_binding_legacy` wrapper; update test fixtures that pass legacy values directly). The only real scope fork is **W2 field-name direction** — see the W2 fork below.

---

## W1: `Finding.from_legacy()` + `DriftReport.from_legacy()` classmethods

### Definition (production)
- `src/flow_engineering/decision_drift.py:77-117` — `Finding.from_legacy` classmethod (~41 LOC)
- `src/flow_engineering/decision_drift.py:143-197` — `DriftReport.from_legacy` classmethod (~55 LOC)
- `src/flow_engineering/decision_drift.py:200-209` — `_epoch_to_iso()` helper (KEEP — used by `scan_change` at lines 647, 817)

### Production callers in `src/`: **0**
Both classmethods are defined but never called from production code. They exist purely as migration paths for v0.7.x callers. Search across `src/`: only the definitions + 4 docstring references (lines 68, 127, 144, 203) match.

### Test callers: **8 call sites + 2 docstring refs**
**Direct `from_legacy` calls (testing the shim itself — DELETE in v0.9.0):**
- `tests/unit/test_decision_drift_v080_migration.py:110` — `Finding.from_legacy(decision_id="42", ...)` (test_finding_from_legacy_emits_deprecation_warning)
- `tests/unit/test_decision_drift_v080_migration.py:124` — `Finding.from_legacy(decision_id="42", ...)` (test_finding_from_legacy_coerces_str_to_int)
- `tests/unit/test_decision_drift_v080_migration.py:141` — `Finding.from_legacy(decision_id="not-a-number", ...)` (test_finding_from_legacy_non_numeric_str_raises)
- `tests/unit/test_decision_drift_v080_migration.py:171` — `DriftReport.from_legacy(scanned_at=0.0, ...)` (test_drift_report_from_legacy_emits_deprecation_warning)
- `tests/unit/test_decision_drift_v080_migration.py:183` — `DriftReport.from_legacy(scanned_at=epoch, ...)` (test_drift_report_from_legacy_converts_epoch_to_iso)
- `tests/unit/test_decision_drift_v080_migration.py:201` — `DriftReport.from_legacy(unable_to_verify=True, ...)` (test_drift_report_from_legacy_handles_unable_to_verify_alias)

**Direct `Finding(decision_id="<str>", ...)` calls (passing legacy values without going through `from_legacy` — MIGRATE to int):**
- `tests/unit/test_decision_drift.py:196` — `Finding(decision_id="obs-1", ...)` (test_finding_is_frozen smoke)
- `tests/unit/test_cli_watch_drift.py:99` — `Finding(decision_id="1", ...)` (test fixture helper)

**Direct `DriftReport(scanned_at=0.0, ...)` calls (passing legacy float without going through `from_legacy` — MIGRATE to ISO str):**
- `tests/unit/test_decision_drift.py:208` (test_drift_report_defaults)
- `tests/unit/test_decision_drift.py:535` (scan_change fixture)
- `tests/unit/test_cli_watch_drift.py:200` (test fixture)
- `tests/unit/test_cli_watch_drift.py:253` (test fixture)
- `tests/unit/test_daemon_drift_events.py:151` (test fixture)
- `tests/unit/test_daemon_drift_events.py:175` (test fixture)
- `tests/unit/test_daemon_drift_events.py:204` (test fixture)
- `tests/unit/test_daemon_drift_events.py:289` (test fixture)

(Note: `tests/unit/test_drift_event_log.py` also has `_make_event(decision_id="1")` calls at lines 118-141 — but those construct `DriftEvent` from `drift_event_log.py`, NOT `Finding` from `decision_drift.py`. `DriftEvent.decision_id: str` is the intentional JSONL wire-format contract per verify-report S1 — separate concern, deferred to v1.0.)

### Removal complexity: **LOW**

The classmethods are self-contained (no inheritance, no protocol implementation). Migration is mechanical: delete the two classmethods + update ~10 test sites that pass legacy values directly.

### Migration needed: **YES**

1. **Delete** `Finding.from_legacy` (`decision_drift.py:77-117`)
2. **Delete** `DriftReport.from_legacy` (`decision_drift.py:143-197`) — this also removes the W2 `unable_to_verify` kwarg mapping
3. **Delete** 5 test fixtures in `test_decision_drift_v080_migration.py`:
   - test_finding_from_legacy_emits_deprecation_warning (lines 104-119)
   - test_finding_from_legacy_coerces_str_to_int (lines 122-131)
   - test_finding_from_legacy_non_numeric_str_raises (lines 134-146)
   - test_drift_report_from_legacy_emits_deprecation_warning (lines 165-177)
   - test_drift_report_from_legacy_converts_epoch_to_iso (lines 180-192)
   - test_drift_report_from_legacy_handles_unable_to_verify_alias (lines 195-206)
4. **KEEP** 3 smoke tests in `test_decision_drift_v080_migration.py`:
   - test_finding_decision_id_is_int_type (lines 76-101) — canonical Finding type contract
   - test_drift_report_scanned_at_is_str_iso (lines 152-162) — canonical DriftReport scanned_at contract
   - test_drift_report_unable_reason_default_none (lines 209-218) — canonical unable_reason default
5. **MIGRATE** 2 direct `Finding(decision_id="<str>", ...)` sites → use int (test_decision_drift.py:196, test_cli_watch_drift.py:99)
6. **MIGRATE** 8 direct `DriftReport(scanned_at=0.0, ...)` sites → use ISO str literal (`"2026-06-27T12:00:00Z"` or `_epoch_to_iso(0.0)`)
7. **Optional**: add `Finding.__post_init__` coercion per verify-report W1 recommendation (line 139) so direct `Finding(decision_id="obs-1")` raises TypeError on str inputs — this is the design D2 intent (`design.md:934`). Strict TDD: write RED test first.
8. **Cleanup**: remove the 3 `# type: ignore` comments at `decision_drift.py:759/772/792` (the `_append_drift_events` str-coercion sites become unnecessary once `Finding` rejects str; verify-report W9)

Net test file delta: `test_decision_drift_v080_migration.py` shrinks from 13 tests → 3 tests.

---

## W2: `DriftReport.graph_unavailable` + `unable_reason: str | None` + the `unable_to_verify` kwarg shim

### The fork

This is the **only real scope ambiguity** in v0.9.0 hardening.

**State at v0.8.0 (per drift-hardening batch-d.md Deviation #3 + verify-report W2):**
- **Canonical field**: `graph_unavailable: bool` (`decision_drift.py:140`)
- **NEW field**: `unable_reason: str | None` (`decision_drift.py:141`) — first shipped in v0.8.0, no compat shim
- **Compat shim**: `unable_to_verify: bool | None = None` kwarg inside `DriftReport.from_legacy` (`decision_drift.py:155, 183-185, 194` mapping)

**Design D2 intent (per `openspec/changes/archive/2026-06-27-drift-hardening/design.md:178, 208, 1469, 1487`):**
- Canonical field SHOULD be `unable_to_verify: bool` (was the rename target)
- `graph_unavailable` should be a 1-release `@property` alias emitting `DeprecationWarning`
- The impl chose the OPPOSITE direction (kept `graph_unavailable` canonical, added `unable_reason`)

**CHANGELOG v0.8.0 migration guide (line 64) documents the actual direction:**
> "Replace `report.unable_to_verify` (bool) with `report.graph_unavailable` (bool) + `report.unable_reason` (str | None). For legacy kwarg callers, use `DriftReport.from_legacy(unable_to_verify=True, ...)` which maps to `graph_unavailable`."

### Production references: **~20 (all stay canonical)**
**`graph_unavailable` field references — STAY (canonical):**
- `src/flow_engineering/decision_drift.py:140` (definition)
- `src/flow_engineering/decision_drift.py:154` (kwarg in `from_legacy` — auto-removed with W1)
- `src/flow_engineering/decision_drift.py:183-185, 194` (mapping inside `from_legacy` — auto-removed with W1)
- `src/flow_engineering/decision_drift.py:409, 608, 670, 692, 704, 825, 840` (in `scan_change` returns + docstrings)
- `src/flow_engineering/daemon.py:115` (reads `report.graph_unavailable`)
- `src/flow_engineering/cli.py:1562, 1566, 1607, 1625` (reads + emits in JSON output)
- `src/flow_engineering/observability.py:329, 348` (`drift_unable_to_verify_total` counter: `1 if report.graph_unavailable else 0`)

**`unable_reason` field references — STAY (NEW canonical, no compat shim):**
- `src/flow_engineering/decision_drift.py:141` (definition)
- `src/flow_engineering/decision_drift.py:156, 195` (kwarg + passthrough in `from_legacy` — auto-removed with W1)

**`unable_to_verify` kwarg shim — REMOVED with W1 (no separate work needed):**
- `src/flow_engineering/decision_drift.py:155, 183-185, 194` (all inside `DriftReport.from_legacy`)

### Test references: **~25 (all stay canonical)**
**`graph_unavailable` test sites — STAY:**
- `tests/unit/test_cli_snapshot.py:805, 837` (constructor arg in fixtures)
- `tests/unit/test_decision_drift.py:215, 343, 360, 416, 443, 516` (assertions)
- `tests/unit/test_daemon_drift_events.py:177, 236, 280, 295` (constructor + assertions)
- `tests/unit/test_decision_drift_v080_migration.py:197, 206` (within `from_legacy` test — auto-removed with W1)
- `tests/unit/test_cli_drift.py:220, 232, 239, 242, 252` (constructor + assertions)
- `tests/bdd/test_decision_reality_drift_steps.py:306, 316, 371, 651, 2170` (step glue)
- `tests/bdd/req11_drift_exit_codes.feature:23`
- `tests/bdd/req12_drift_counters.feature:15`

**`unable_reason` test sites — STAY (canonical field):**
- `tests/unit/test_decision_drift_v080_migration.py:209-218` (1 test: `test_drift_report_unable_reason_default_none`)

**`unable_to_verify` test sites — mostly STAY (it's a class enum value + counter name + bdd scenario text, not a field):**
- `DriftClass.UNABLE_TO_VERIFY` enum value at `decision_drift.py:59` (STAY — terminal state class)
- Counter name `drift_unable_to_verify_total` in `observability.py:329, 331, 347` + `tests/bdd/req12_drift_counters.feature:15, 27, 30` + `tests/bdd/test_decision_reality_drift_steps.py:1431, 1433, 2210-2221` (STAY — counter name is part of the public observability catalog)
- CLI exit-code 2 wording + BDD scenarios (STAY — REQ-11 / REQ-15 contracts are about the terminal `unable_to_verify` STATE, not a field name)
- The only kwarg use is `tests/unit/test_decision_drift_v080_migration.py:204` (`unable_to_verify=True` inside `from_legacy` test) — auto-removed with W1

### Removal complexity: **LOW (Option B) / HIGH (Option A)**

**Option B (recommended per verify-report W2 line 171): ACCEPT DEVIATION**
- Just delete `DriftReport.from_legacy` (covered by W1)
- Add a `Drift note` to `openspec/changes/archive/2026-06-27-drift-hardening/design.md` post-archive (already recommended in verify-report W2 line 171; can be done in v0.9.0 docs-only batch)
- Zero production code changes beyond W1's `from_legacy` removal
- `graph_unavailable` stays canonical; `unable_reason` stays canonical; `unable_to_verify` enum value + counter name + CLI exit-code 2 wording all stay (they describe the STATE, not the field)

**Option A: CATCH UP WITH DESIGN — rename `graph_unavailable` → `unable_to_verify`**
- Add `unable_to_verify: bool = False` as canonical field
- Keep `graph_unavailable` as a 1-release `@property` alias with `DeprecationWarning` (the design's intent)
- Migrate 4 production files (decision_drift.py:140/154/183-185/194/409/608/670/692/704/825/840, daemon.py:115, cli.py:1562/1566/1607/1625, observability.py:329/348) + 8 test files + 2 BDD features
- ~30 LOC rename + ~5 LOC alias property
- This is a SECOND v0.9.0 BREAKING migration on top of the shim removal — much larger scope
- May be better as its own dedicated change (v0.9.0-rename) rather than bundled

**Recommendation: Option B.** The CHANGELOG v0.8.0 entry (line 45) already says "`graph_unavailable: bool` retained as the canonical field name" — operators have been told to migrate TO `graph_unavailable`. Re-renaming in v0.9.0 would be a third direction-change on the same field in one release cycle, which is operator-hostile.

### Migration needed: **YES (Option B)**
- W1 removes `DriftReport.from_legacy` → auto-removes the `unable_to_verify` kwarg shim (no separate work)
- Docs: add Drift note to `openspec/changes/archive/2026-06-27-drift-hardening/design.md` (per verify-report W2 recommended fix line 171)

---

## W3: `classify_binding_legacy` 3-arg wrapper

### Definition (production)
- `src/flow_engineering/decision_drift.py:267-285` — `classify_binding_legacy(binding, current_nodes, current_id_map)` function (~19 LOC)
- Internal helper `_classify_with_id_map` at `decision_drift.py:248-264` — **KEEP** (used by 2-arg primary at line 245)
- 2-arg primary `classify_binding(ref, graph_nodes)` at `decision_drift.py:212-245` — **STAYS canonical**

### Production callers in `src/`: **0**
Only the definition + 1 docstring reference (line 221) match. The 2-arg primary is used by `scan_change` at `decision_drift.py:769`.

### Test callers: **11 sites**
**Existing tests migrated to `classify_binding_legacy` during drift-hardening T4.3 (verify-report T4.3 line 77 — "existing 12 tests migrated to classify_binding_legacy"). Actual grep = 10 call sites + 1 in the migration test file:**
- `tests/unit/test_decision_drift.py:74, 83, 95, 104, 116, 125, 135, 142, 173, 188` — 10 sites using `classify_binding_legacy(binding, nodes, id_map)`
- `tests/unit/test_decision_drift_v080_migration.py:252` — 1 site inside `test_classify_binding_legacy_3arg_emits_deprecation_warning`

Note: per verify-report S3 line 298-304, these 10 sites emit `DeprecationWarning` on every pytest run (visible noise in test output) — removal eliminates this noise.

### Removal complexity: **LOW**

The 3-arg wrapper is purely additive — the 2-arg primary does the same work and internally derives `current_id_map` (line 245 → 248-264). Migration is mechanical: delete the function + change `classify_binding_legacy(binding, nodes, id_map)` → `classify_binding(binding, nodes)` at 10 test sites (drop the `_id_map(...)` helper construction lines, which become unused).

### Migration needed: **YES**

1. **Delete** `classify_binding_legacy` (`decision_drift.py:267-285`)
2. **Migrate** 10 test sites in `tests/unit/test_decision_drift.py`:
   - Line 74 (test_classify_still_valid_basic): drop `id_map = _id_map(...)` + change call
   - Line 83 (test_classify_still_valid_source_and_confidence_dont_affect_class): same
   - Line 95 (test_classify_label_drift_when_label_differs): same
   - Line 104 (test_classify_label_drift_case_only_still_flags): same
   - Line 116 (test_classify_stale_location_when_file_moved): same
   - Line 125 (test_classify_stale_location_when_line_shifted_same_file): same
   - Line 135 (test_classify_stale_id_when_id_absent_from_id_map): same
   - Line 142 (test_classify_stale_id_when_id_renamed_with_no_alias): same
   - Line 173 (test_classify_binding_never_returns_obsolete_for_resolvable_id): same
   - Line 188 (test_classify_binding_never_returns_contradicted): same
3. **Delete** 1 test fixture in `tests/unit/test_decision_drift_v080_migration.py`:
   - `test_classify_binding_legacy_3arg_emits_deprecation_warning` (lines 243-255)
4. **Check** the `_id_map` test helper at `tests/unit/test_decision_drift.py:61-62` — only used by the 10 migrated tests; can be deleted if no other callers
5. **No production code changes** beyond the function deletion

---

## Aggregate v0.9.0 estimate

### Tests to update: **~30 test sites across 5 files**

| File | Sites | Action |
|------|-------|--------|
| `tests/unit/test_decision_drift_v080_migration.py` | 7 tests deleted + 2 tests kept + 1 test kept + 1 test kept = 13 → 3 | Delete from_legacy/legacy fixtures; keep canonical type-contract smokes |
| `tests/unit/test_decision_drift.py` | 10 call sites migrated (3-arg → 2-arg) + 1 str input migrated to int + 2 float inputs migrated to ISO str = 13 edits | Migrate legacy fixtures |
| `tests/unit/test_cli_watch_drift.py` | 1 str input migrated to int + 2 float inputs migrated to ISO str = 3 edits | Migrate legacy fixtures |
| `tests/unit/test_daemon_drift_events.py` | 4 float inputs migrated to ISO str = 4 edits | Migrate legacy fixtures |
| `tests/unit/test_drift_event_log.py` | 0 (DriftEvent is a different class — deferred to v1.0) | n/a |

### Total LOC delta: **~140 prod deletions + ~25 prod additions + ~150 test deletions**

**Production code (`src/flow_engineering/decision_drift.py`):**
- DELETE: lines 77-117 (`Finding.from_legacy`, ~41 LOC)
- DELETE: lines 143-197 (`DriftReport.from_legacy`, ~55 LOC)
- DELETE: lines 267-285 (`classify_binding_legacy`, ~19 LOC)
- ADD: lines ~75-85 (optional `Finding.__post_init__` coercion per verify-report W1 recommended fix, ~15 LOC)
- DELETE: 3 `# type: ignore` comments at lines 759/772/792 (per verify-report W9)
- KEEP: `_epoch_to_iso` helper (lines 200-209, used by `scan_change` at lines 647, 817)
- KEEP: `_classify_with_id_map` helper (lines 248-264, used by 2-arg primary at line 245)
- KEEP: `graph_unavailable` field (canonical) + `unable_reason` field (canonical) per Option B

**Net prod**: ~115 LOC removed (or ~100 if `__post_init__` is added)

**Test code:**
- DELETE: ~150 LOC of from_legacy/legacy test fixtures
- MODIFY: ~10 LOC of test_decision_drift.py call site edits

**Net test**: ~140 LOC removed

**Documentation:**
- `CHANGELOG.md` v0.9.0 entry (mirror v0.8.0 format at lines 39-74): ~35 LOC added
- `openspec/specs/decision-drift/spec.md` lines 202-208: update migration note (the v0.8.0 shim window is now closed)
- 6 SKILL.md runtime files (`sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` lines 196/191/261/243/91/172): update the v0.8.0 API note to remove the "1-release shim" qualifier
- `openspec/changes/archive/2026-06-27-drift-hardening/design.md` Drift note (Option B, per verify-report W2 line 171): ~10 LOC added
- `pyproject.toml`: bump 0.8.0 → 0.9.0 (1-line edit at line 3)

### Wall time estimate: **~3-4 hours**

Single PR, single apply batch (small enough for chained-PR threshold at 400 LOC — actually under 200 LOC delta):
1. RED fixtures: 30 min (write failing tests that assert the shims are gone)
2. GREEN implementation: 60 min (delete shims, update callers, fix type ignores)
3. REFACTOR + lint/type-cleanup: 30 min
4. Documentation: 30 min (CHANGELOG + 6 SKILL.md + design.md Drift note + spec.md migration note)
5. Verify + archive: 30 min (full pytest, ruff, mypy; update verify-report)

**Dependency note**: the user noted `after PR#2a+PR#2b ship` — referring to prompt-registry PR#2 (active change per Engram #259). v0.9.0 hardening can launch as soon as prompt-registry PR#2 archives (it shares `openspec/specs/` infrastructure but touches a different capability).

---

## Risks

1. **W2 fork (medium)**: Option A (rename `graph_unavailable` → `unable_to_verify`) is a v0.9.0 BREAKING-on-top-of-v0.8.0-BREAKING scenario that compounds operator confusion. CHANGELOG v0.8.0 line 45 explicitly says "`graph_unavailable: bool` retained as the canonical field name" — re-renaming undoes this promise. **Recommend Option B** (accept deviation + Drift note). Surface this fork to user at sdd-propose time for explicit confirmation.

2. **5 pre-existing test failures (carry-forward from verify-report W6)**: `test_cli_metrics_aggregate.py::test_metrics_aggregate_with_window_filter` + `test_cli_metrics_export.py::test_metrics_export_with_window_filter` + `test_observability_aggregate.py::TestWindowIntegrationOnExport` (2 tests) + `tests/bdd/test_prompt_registry_steps.py::test_req46_render_missing_kwargs`. These are unrelated to v0.9.0 hardening but will show in the verify-report. Carry-forward doc is sufficient.

3. **JSONL wire format decoupling (verify-report S1, deferred to v1.0)**: `DriftEvent.decision_id: str` (JSONL) vs `Finding.decision_id: int` (Python). Not in v0.9.0 scope. Document the deferral in CHANGELOG v0.9.0 Notes.

4. **6 SKILL.md runtime files must be updated atomically** (per drift-hardening T4.5.c precedent in `verify-report.md` line 81). The `--allow-empty` commit pattern from drift-hardening T4.5.c commit `d5f2147` is the established workflow.

5. **`openspec/specs/decision-drift/spec.md:202-208` migration note** explicitly references `from_legacy()` as the migration path — must be updated to say "removed in v0.9.0; no migration path; direct int/ISO str required". Forward-reference this in sdd-design.

6. **`tests/unit/test_decision_drift_v080_migration.py` file purpose shifts**: file currently describes v0.8.0 migration tests. After v0.9.0, only 3 canonical-type smoke tests remain. Consider whether to (a) rename to `test_decision_drift_dataclass_contract.py` (clearer purpose) or (b) inline the 3 tests into `test_decision_drift.py`. sdd-design decision.

7. **`_id_map` test helper at `tests/unit/test_decision_drift.py:61-62`**: only used by the 10 tests being migrated to 2-arg `classify_binding`. Likely dead after W3 migration — should be deleted in the same commit.

8. **`Finding.__post_init__` enforcement is optional** per verify-report W1 (line 139 says "Future v0.9.0 follow-up could add `__post_init__` enforcement"). Including it in v0.9.0 hardening adds ~15 LOC + 1-2 RED tests but prevents silent str→int coercion bugs. Recommend including it as part of the same change (small surface, strong safety improvement).

9. **`tests/unit/test_drift_event_log.py` lines 118-141 use `_make_event(decision_id="1")`**: NOT in scope for v0.9.0 hardening (it's `DriftEvent`, not `Finding`), but worth noting in the v0.9.0 verify-report that `DriftEvent.decision_id: str` is intentionally separate from `Finding.decision_id: int` (verify-report S1, deferred to v1.0).

---

## Proposed scope for v0.9.0

**Single PR**: remove v0.8.0 1-release compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`) per CHANGELOG v0.8.0 commit lines 43/44/46/74 ("removed in v0.9.0"). Accept the drift-hardening W2 deviation (`graph_unavailable` canonical + `unable_reason` NEW field) per verify-report W2 Option B; document via Drift note in archived design.md. Add `Finding.__post_init__` str→int enforcement per verify-report W1 recommended fix. Bump `pyproject.toml` 0.8.0 → 0.9.0; update CHANGELOG v0.9.0 entry + 6 SKILL.md runtime files + `openspec/specs/decision-drift/spec.md` migration note. ~115 prod LOC removed + ~15 prod LOC added + ~140 test LOC removed. ~3-4 hours wall time. Single apply batch (well under 400 LOC chained-PR threshold).

**Explicit NON-goals** (deferred to v1.0+):
- `DriftEvent.decision_id: str` → int JSONL wire format change (verify-report S1)
- `DriftEventLog` JSONL rotation (verify-report W7, deferred to v1.1)
- `flow drift events` CLI read-side command (verify-report S2)
- JSONL `os.fsync` atomic-write hardening (verify-report S4)
- `Finding.__post_init__` removal itself (v1.0)

---

## Artifacts

- `openspec/changes/v0.9.0-hardening/explore.md` (this file)
- Engram mirror: topic_key `sdd/v0.9.0-hardening/explore`, type `architecture`

## Next step

`sdd-propose v0.9.0-hardening` — after prompt-registry PR#2 ships (active change per Engram #259). The propose phase will need user confirmation on the W2 fork (Option A vs Option B) before drafting `proposal.md`.
