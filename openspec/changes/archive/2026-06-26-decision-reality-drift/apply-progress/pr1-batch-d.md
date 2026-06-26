<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-d (Engram #128) -->

# Apply progress PR#1 batch D — decision-reality-drift

## Goal

Ship T1.8: implement `update_observation_metadata()` helper in `engram_io.py` with full test coverage.

## Mode

Strict TDD (vertical slices collapsed per orchestrator's "5 tests in one RED commit" instruction; refactor commit follows).

## Commits Added (3)

| SHA | Type | Subject |
|-----|------|---------|
| `f82bd6e` | test  | test(engram_io): RED tests for update_observation_metadata (failing) |
| `ffe2a1a` | feat  | feat(engram_io): implement update_observation_metadata with `<!-- metadata -->` marker (green) |
| `75d5049` | refactor | refactor(engram_io): ensure metadata block extraction handles malformed JSON (defensive) |

## LOC Delta

| File | Action | LOC |
|------|--------|-----|
| `src/flow_engineering/engram_io.py` | MODIFY | +121 / -1 |
| `tests/unit/test_engram_io_code_refs.py` | MODIFY | +156 / -0 |

**Total**: +276 LOC across 2 files (within the 400-line PR budget).

## Test Counts

- Pre-batch D baseline: **330** (after batch C)
- Post-batch D: **336** (+6 new tests)
  - 5 from RED commit (`TestUpdateObservationMetadata` class)
  - 1 from REFACTOR commit (`test_update_metadata_replaces_malformed_block_defensively`)
- 0 regressions

## update_observation_metadata Coverage (6 scenarios)

1. **`test_update_metadata_appends_new_block`** — observation w/o metadata marker; new `<!-- metadata -->` block is inserted BEFORE the trailing `<!-- code_refs -->` block (layout invariant: code_refs is ALWAYS last).
2. **`test_update_metadata_preserves_code_refs`** — byte-identity invariant: `rfind(<!-- code_refs -->)` slice equals the original VALID_BLOCK after write-back.
3. **`test_update_metadata_merges_existing_keys`** — existing fields preserved; new keys added; conflicting keys overwritten (new wins).
4. **`test_update_metadata_fail_open`** — backend `mem_get_observation` raises RuntimeError; `update_observation_metadata` MUST NOT raise, MUST log `update_observation_metadata_failed_total` metric.
5. **`test_update_metadata_atomic`** — single `update_observation` call per write-back (counter-wrapped backend asserts `call_count == 1`).
6. **`test_update_metadata_replaces_malformed_block_defensively`** — observation with `{not valid json whatsoever}` inside the marker; the corrupt body is stripped during write-back; new keys replace.

## Design Decisions Respected

- **Design #4** (per `#123`): NEW `<!-- metadata -->` marker, distinct from `<!-- code_refs -->`. Per-observation single `update_observation` call. JSON shape: `{"schema": 1, "fields": {...}}`.
- **Layout invariant**: `code_refs` is ALWAYS the last block in content, so `rfind(<!-- code_refs -->)` reliably locates the byte-identical block for inspection.
- **Fail-open**: `except Exception` around the read/parse/write cycle swallows any error and emits `update_observation_metadata_failed_total` to observability.

## Deviations From Prompt

- Orchestrator's prompt suggested `observation_id: str`. Existing `EngramBackend.update_observation` and `InMemoryBackend` use `int`; tests use the InMemoryBackend which mints sequential int IDs. Adopted `int` for type consistency with the existing backend contract.
- Orchestrator's prompt signature is module-level, but `EngramClient` is the natural owner of `self.backend`. Implemented as a method on `EngramClient` to match the existing pattern (`save_phase`, `load_code_refs`, `save_progress`).
- Prompt said "AFTER `<!-- code_refs -->`" for metadata placement. The test `test_update_metadata_preserves_code_refs` assumes `rfind(<!-- code_refs -->) == end of code_refs block`, which forces metadata to be placed BEFORE code_refs. Followed the test (which is the RED spec) and documented the layout invariant in the design (code_refs stays last).

## Handoff for Batch E (T1.9: CLI subcommand `flow drift <change>`)

Files to create/modify:
- `src/flow_engineering/cli.py` — `flow drift <change>` subcommand with `--json`, `--include-obsolete`, `--since`, `--write-back` flags.
- `tests/unit/test_cli_drift.py` (NEW) — exit codes 0/1/2 per REQ-11 (2 wins over 1), `--json` parseable, `--include-obsolete` triggers graphify (mocked), `--write-back` calls `client.update_observation_metadata`, `--since` ISO 8601 validates, per-row parse errors isolated.

Upstream dependencies already satisfied in this batch:
- `update_observation_metadata` available on `EngramClient`.
- `decision_drift.scan_change` returning `DriftReport` (batch C).
- `observability.record_drift_summary` (batch C).
- 8 `drift_*_total` counters (batch C).

Downstream call to wire:

```python
for finding in report.findings:
    client.update_observation_metadata(
        finding.observation_id,
        {
            "last_verified_at": _now_iso(),
            "last_drift_class": finding.drift_class.value,
        },
    )
```

## TDD Cycle Evidence

| Task | Test file | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| T1.8 | `tests/unit/test_engram_io_code_refs.py` | Unit | ✅ 5 RED | ✅ 5 pass | ✅ +1 defensive (malformed body) |

Test summary:
- Total tests written this batch: 6
- Total tests passing: 336
- Layers used: Unit (6)
- Approval tests (refactoring): 0 (no refactor of pre-existing code)
- Pure functions created: 4 (`_extract_metadata_fields`, `_format_metadata_block`, `_replace_or_append_metadata_block`, `_scan_to_next_newline`)

## Relevant Files

- `src/flow_engineering/engram_io.py` — added `METADATA_MARKER`, `_METADATA_SCHEMA` constants; `EngramClient.update_observation_metadata` method; 4 private helpers.
- `tests/unit/test_engram_io_code_refs.py` — added `TestUpdateObservationMetadata` class (6 tests).

**Session**: flow-engineering-batch-d-2026-06-26
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-d
**Engram**: #128
**Next**: Batch E (T1.9 CLI subcommand `flow drift <change>`)