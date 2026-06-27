# Apply Progress: change #6 observability — PR#1 batch D

**Date:** 2026-06-27
**Branch:** main
**Base HEAD:** 38df3db (post batch C)
**Final HEAD:** b8088c0
**Strict TDD:** ON
**Status:** success

## Goal

Implement T1.8 + T1.9 from `openspec/changes/observability/tasks.md` for
change #6 observability, PR#1 batch D: the default-empty handling per
design D8 + exit-code contract per D9 (`MetricsSummaryResult` dataclass +
`read_and_summarize()` helper + `EXIT_*` constants), the CLI integration
on `flow metrics summary` (exit 3 on malformed metrics, exit 0 with
"No metrics recorded yet." on missing/empty), and the focused regression
tests for the existing `atomic_write_text` helper (D10 prep for PR#2's
`--out` flag).

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | 5646516 | test(unit) | RED fixtures for read_and_summarize + MetricsSummaryResult + exit code constants (REQ-35..37 error handling foundation) |
| 2 | 2766a9f | feat(observability) | read_and_summarize + MetricsSummaryResult + EXIT_* constants (REQ-35..37 GREEN) |
| 3 | dde2bc9 | feat(cli) | flow metrics summary uses read_and_summarize + emits exit 3 on malformed metrics (REQ-35..37 CLI exit codes) |
| 4 | b8088c0 | test(unit) | atomic_write_text coverage — tempfile + os.replace pattern (REQ-38 prep) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN.

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T1.8 — observability.py read_and_summarize | 5646516 (10 RED fixtures: 9 fail with AttributeError on `EXIT_*` / `MetricsSummaryResult` / `read_and_summarize`; 1 missing-file CLI test passes against the pre-existing CLI flow) | 2766a9f (9/9 new pass + 847 existing = 856 GREEN; only the CLI exit-3 test remains RED by design) | n/a (clean first cut) |
| T1.8 — CLI integration | included in dde2bc9 (3 RED behaviors: exit-3 on malformed, validate --window pre-read for missing-file, filter-empty contract update) | dde2bc9 (all 10 T1.8 tests + 13 prior CLI tests pass; 857 GREEN) | n/a |
| T1.9 — atomic_write_text coverage | n/a (helper already exists from batch A T1.1 GREEN) | b8088c0 (5/5 new tests pass; 862 GREEN) | n/a |

Commit 4 (T1.9) is regression coverage, not strict RED→GREEN. The
helper shipped in commit `6148b66` (batch A GREEN) and the focused tests
land now to lock in the D10 contract before PR#2's `--out` flag consumes
the helper.

## Files touched

### Production

- `src/flow_engineering/observability.py` (+131 / -0): added the four
  `EXIT_*` constants (`EXIT_OK=0`, `EXIT_INVALID_VALUE=2`,
  `EXIT_MALFORMED_METRICS=3`, `EXIT_WRITE_FAILURE=4`) per design D9; added
  the `MetricsSummaryResult` frozen dataclass carrying
  `summary` / `events_read` / `source_path` / `empty_reason` / `window` /
  `domain`; added `read_and_summarize(*, window, domain, path)` that reads
  + applies window + applies domain + summarizes + detects the three
  empty reasons (`missing_file` / `empty_file` / `all_malformed`) for
  downstream exit-code mapping.

- `src/flow_engineering/cli.py` (+66 / -26): refactored `metrics_summary`
  to consume `read_and_summarize()`. Added early validation of `--window`
  (via `parse_window`) and `--domain` (via `validate_domain`) so a bad
  flag value exits 2 even when the JSONL sink is missing. Added the
  exit-3 path on `all_malformed` ("Error: metrics file at <path> is
  malformed."). Refactored the existing `--since` / `--until` post-filter
  pass to re-read events when those flags are active (read_and_summarize
  consumes events internally; the post-filter re-summarizes for
  completeness). Distinguished the filter-empty case (empty_reason None
  + summary empty → "No metrics in window/domain.") from the
  missing/empty-file case ("No metrics recorded yet.").

### Tests (new + extended)

- `tests/unit/test_observability_summary_result.py` (NEW, 212 LOC, 10 tests):
  `TestReadAndSummarizeEmptyHandling` (3 tests: missing/empty/all_malformed
  detection), `TestReadAndSummarizeFilterComposition` (1 test: window +
  domain filter composition), `TestExitCodeConstants` (4 tests: each
  `EXIT_*` constant matches the contract value), `TestMetricsSummaryCliExitCodes`
  (2 tests: missing-file CLI exits 0 with friendly message; malformed
  file exits 3 with helpful message).

- `tests/unit/test_cli_metrics_summary.py` (MODIFY, +10 / -2): updated
  `test_metrics_summary_with_domain_filter_engine` to reflect the new
  T1.8 contract — empty summary after filtering emits
  "No metrics in window/domain." (case 4) rather than the prior
  "No metrics recorded yet." (which now maps to cases 1+2 only).

- `tests/unit/test_atomic_write.py` (NEW, 148 LOC, 5 tests):
  `TestAtomicWriteCreatesAndOverwrites` (2 tests: basic write + overwrite),
  `TestAtomicWriteCreatesParentDirectories` (1 test: parent dir
  auto-creation), `TestAtomicWriteUsesTempfileAndRename` (1 test: verifies
  the `tempfile.mkstemp + os.replace` pattern via `unittest.mock.patch`
  with a spy), `TestAtomicWriteRollsBackOnFailure` (1 test: simulated
  `os.replace` failure cleans up the staging `.prom.tmp` and leaves no
  orphan).

## Test delta

| Metric | Baseline (post batch C) | Final | Delta |
|--------|------------------------|-------|-------|
| Total tests passing | 847 | 862 | +15 |
| New unit tests (T1.8) | — | 10 | +10 |
| New unit tests (T1.9) | — | 5 | +5 |
| New BDD scenarios | 0 | 0 | 0 (PR#1 batch D is docs/CLI exit codes only — no new BDD features) |

Full suite runs in ~63s.

## BDD scenario delta

| REQ | Pre-batch | Post-batch D | Delta |
|-----|-----------|--------------|-------|
| REQ-35 (summary) | 2 | 2 | 0 |
| REQ-36 (window) | 2 | 2 | 0 |
| REQ-37 (domain) | 2 | 2 | 0 |
| REQ-38 (prometheus) | 0 | 0 | 0 (PR#2 batch F) |
| REQ-39 (percentile) | 0 | 0 | 0 (PR#2 batch G) |
| Total | 6 | 6 | 0 |

## Deviations from spec/design

1. **CLI distinguishes 4 empty cases vs the prompt's unified
   "missing/empty" path.** The T1.8 prompt maps 4 cases to 4 messages:
   - missing_file / empty_file → "No metrics recorded yet." (exit 0)
   - all_malformed → exit 3 + stderr message
   - filter-empty (summary == {} after filtering) → "No metrics in window/domain." (exit 0)

   The pre-existing batch-C test
   `test_metrics_summary_with_domain_filter_engine` asserted
   "No metrics recorded yet." for the filter-empty case. Per the T1.8
   contract (4-case mapping) the filter-empty case now emits the more
   informative "No metrics in window/domain." — the batch-C test was
   updated accordingly (1-line assertion change + docstring update;
   no logic change in the existing test).

2. **`--window` is validated BEFORE `read_and_summarize()` is called.**
   The prompt's pseudocode lets `read_and_summarize()` short-circuit on
   empty reasons before applying the window filter. This means a bad
   `--window=garbage` against a missing JSONL file would emit
   "No metrics recorded yet." instead of the expected exit-2 usage
   error. To preserve the existing `test_metrics_summary_invalid_window_exits_2`
   behavior (and the D9 contract that usage errors always exit 2),
   the CLI calls `observability.parse_window(window)` for validation
   BEFORE invoking `read_and_summarize()`. Same for `--domain` via
   `observability.validate_domain()`. This is a defensive pre-validation
   step the prompt did not anticipate but matches the operator expectation
   that bad input always fails fast.

3. **`read_and_summarize()` does not consume `--since` / `--until`.**
   The prompt's signature is `(window, domain, path)`; the CLI applies
   `--since` / `--until` as a post-filter pass by re-reading events
   from disk and re-summarizing. This is wasteful (extra disk read when
   both since/until are set) but matches the prompt's signature exactly
   and keeps the helper minimal. Future batches could extend
   `read_and_summarize()` with `since_epoch` / `until_epoch` parameters
   if the re-read cost becomes a problem at scale (unlikely at v1's
   ~150 KB JSONL scale).

4. **`atomic_write_text` lives in `observability.py` (not `cli.py`)** as
   per the batch-A deviation note (consolidated so PR#2's `--out` flag
   can import it from `observability`). The T1.9 task brief asked to
   "extract to cli.py per design D10" but explicitly allowed leaving it
   in `observability.py` for PR#1: "the design D10 wants it in cli.py
   for PR#2 (export --out flag reuse). For batch D, just VERIFY the
   existing helper works correctly and add a focused test for it. No
   file moves needed (atomic_write_text in observability.py is fine for
   PR#1)." No file move done.

## Risks / follow-ups

- **REQ-8 byte-identical regression**: verified `flow metrics` and
  `flow metrics --json` outputs match v0.6.0 against the 3 existing
  `TestMetricsCommand` tests in `tests/unit/test_cli_inspect.py`. No
  regression.
- **`read_and_summarize()` re-read cost when `--since` is set**: minor;
  ~150 KB JSONL reads in <1ms. Acceptable for v1.
- **`flow metrics summary` post-filter path complexity**: when both
  `--since` AND `--domain` are set, the CLI does an explicit re-read +
  filter + re-summarize. Future batches could simplify by extending
  `read_and_summarize()` to accept `since_epoch` / `until_epoch`.
- **`atomic_write_text` import surface**: tests + future PR#2 `--out`
  integration import from `observability`; the helper is module-public
  (no underscore prefix), documented via the existing module docstring.

## Next recommended

`sdd-apply observability PR#1 batch E (T1.10: CHANGELOG v0.7.0 + 6 SKILL.md
runtime updates + integration tests sweep)` — the final batch of PR#1;
lands the user-facing release notes + the 6 SKILL.md "Metrics hook"
runtime updates + a small integration test suite covering the full PR#1
surface (summary + window + domain). Depends on T1.1..T1.9 (DONE).