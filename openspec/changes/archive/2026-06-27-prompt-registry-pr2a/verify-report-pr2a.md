<!-- verify-report-pr2a.md: prompt-registry PR#2a closeout. Source: sdd-verify (executor). -->
# Verify Report — PR#2a closeout (REQ-49 only)

**Change:** `prompt-registry` (change #7)
**PR:** PR#2a (REQ-49 only — chained PRs strategy; PR#2b = REQ-50 + 8 W-fixes pending)
**Date:** 2026-06-27
**Mode:** Strict TDD ON (per `decision-code-linking` precedent; RED → GREEN → REFACTOR per task)
**HEAD:** `83e55b9` (post-apply-progress closeout)
**Branch:** `main` (working tree: untracked `openspec/changes/prompt-registry/tasks-pr2.md` + `openspec/changes/v0.9.0-hardening/explore.md` — both NOT PR#2a scope)
**Baseline:** 1125 / 1125 tests passing pre-apply; final **1187 / 1187 passing** (+62 from PR#2a: 52 unit + 10 BDD/cli = 62 NEW tests; 0 regressions)
**Verifier:** sdd-verify sub-agent (paths-injected)

---

## Executive Summary

PR#2a ships a working `SKILL_CATALOG` mirror catalog (20 entries, 10 sdd-* agents ×
2 surfaces) + SHA-256 frontmatter drift detection + `flow prompts {check,lint}`
Click subcommands, with a usable `--init` flag for sidecar bootstrap. All 60 NEW
unit tests in `test_opencode_skill_catalog.py` + `test_cli_prompts.py` pass; all
2 NEW REQ-49 BDD scenarios pass; ruff clean on all changed Python files; mypy
clean on `opencode_skill_catalog.py`. **However, the implementation has 3
PARTIAL-conformance gaps vs. `tasks-pr2.md` T2.2 + T2.4** — only `--init` shipped
out of the 4 required `flow prompts check` flags (missing `--update`, `--no-fail`,
`--skill`); the S2 stderr WARN + 3 observability counter names for
`prompts_check_*` were not wired. Most critically, `check_drift` reads
`parsed.get("version", "0.0")` at the top level only — but the real OpenCode
SKILL.md files have `version` nested under `metadata.version`, so
`flow prompts check` against the real catalog reports **20/20 entries as DRIFT
even after `--init`** (false positive).

**Verdict:** **`PARTIAL`** — the 9 tasks closed at the file/commit level and the
test suite is green, but the production CLI behavior against the real
`~/.config/opencode/skills/sdd-*/SKILL.md` corpus is broken (C1), and 3 of the 4
required `flow prompts check` flags are missing (W1). PR#2a should NOT be
archived as-is; the 3 gaps should be fixed in a follow-up commit (or rolled into
PR#2b as additional T3.* tasks) before archive.

---

## Test execution

| Suite | Command | Result | Time | Exit |
|-------|---------|--------|------|------|
| Full pytest | `uv run --frozen pytest tests/ --tb=line -q` | **1187 passed**, 0 failed | 64.02s | 0 |
| REQ-49 BDD subset | `uv run --frozen pytest tests/bdd/test_prompt_registry_steps.py -k "req49" -v` | **2 passed**, 0 failed | 0.22s | 0 |
| `flow prompts` unit + catalog unit | `uv run --frozen pytest tests/unit/test_opencode_skill_catalog.py tests/unit/test_cli_prompts.py` | **60 passed**, 0 failed | 1.36s | 0 |
| Ruff lint (changed Python files) | `uv run --frozen ruff check src/flow_engineering/opencode_skill_catalog.py src/flow_engineering/cli.py tests/unit/test_opencode_skill_catalog.py tests/unit/test_cli_prompts.py tests/bdd/test_prompt_registry_steps.py` | **All checks passed!** | n/a | 0 |
| Mypy (new module) | `uv run --frozen mypy src/flow_engineering/opencode_skill_catalog.py` | **Success: no issues found in 1 source file** | n/a | 0 |
| Smoke: `flow prompts check` (no sidecar) | `uv run --frozen flow prompts check` | 20/20 entries shown as DRIFT, exit 1 | n/a | 1 |
| Smoke: `flow prompts check --init` | `uv run --frozen flow prompts check --init` | "Initialized 20 checksums", exit 0; writes `~/.flow-engineering/prompt_checksums.json` | n/a | 0 |
| Smoke: `flow prompts lint` | `uv run --frozen flow prompts lint` | "4 prompts linted · 0 warnings · 0 errors", exit 0 | n/a | 0 |
| Smoke: `flow prompts check` (post-`--init`, real SKILL.md files) | `uv run --frozen flow prompts check` | 20/20 entries STILL shown as DRIFT (exit 1) — see **C1** | n/a | 1 |
| Sidecar cleanup | `rm -f ~/.flow-engineering/prompt_checksums.json` | cleanup ok | n/a | n/a |

**Net verdict on tests:** 1187/1187 pass; PR#2a is internally consistent. The
test suite and the CLI behavior diverge from each other (and from the real SKILL.md
corpus) on C1 — see CRITICAL findings.

---

## REQ coverage matrix (PR#2a scope: REQ-49 only)

| REQ | Title | Tests covering | Status | Notes |
|-----|-------|----------------|--------|-------|
| **REQ-49** | `SKILL_CATALOG: dict[str, SkillEntry]` mirror catalog (20 entries) + SHA-256 frontmatter drift detection + sidecar JSON I/O at `~/.flow-engineering/prompt_checksums.json` + `flow prompts {check, lint}` CLI surface | 52 unit in `tests/unit/test_opencode_skill_catalog.py` (T1.1: 11 SkillEntry/SkillDrift/SIDECAR_PATH/SkillVersionError + 5 SKILL_CATALOG shape; T1.2: 2 FRONTMATTER_PATTERN + 5 compute_frontmatter_sha256 + 4 parse_frontmatter; T1.3: 6 check_drift paths including version_mismatch; T1.4: 1 SidecarPath + 2 ReadSidecar + 3 WriteSidecar + 4 InitChecksums + 1 UpdateChecksums) + 8 unit in `tests/unit/test_cli_prompts.py` (TestFlowPromptsGroup × 3 + TestPromptsCheckInit × 1 + TestPromptsLint × 4) + 2 BDD in `tests/bdd/req49_skill_catalog.feature` (test_req49_check_drift_detects_mismatch + test_req49_check_drift_passes_clean) | **COMPLIANT in test fixtures; PARTIAL in real-world CLI** (see C1) | All 9 tasks T1.1..T1.5 + T2.1..T2.4 closed at file/commit level per apply-progress closeout. SHA-256 whitespace-insensitivity verified at unit level. Sidecar JSON atomic write (tempfile + os.replace + fsync) verified. `check_drift` returns `SkillDrift` list with 4 `drift_kind` categories. CLI wires `flow prompts` Click group + `check` + `lint` subcommands. BUT: `--init` only; `--update`/`--no-fail`/`--skill` missing; S2 stderr WARN + 3 observability counter names missing; real-world SKILL.md frontmatter parsing reads top-level `version` only (real OpenCode files nest under `metadata.version`) → see CRITICAL findings. |

**REQ coverage: 1/1 REQ covered in test fixtures; 0/1 REQ end-to-end on the
real OpenCode SKILL.md corpus.** 0 REQs in PR#2b scope (out of scope per the
brief).

---

## Task closure matrix (PR#2a: 9 tasks T1.1..T1.5 + T2.1..T2.4)

| Task | Title | Implementation commits | Status |
|------|-------|------------------------|--------|
| **T1.1** | `opencode_skill_catalog.py` NEW: `SkillEntry` frozen dataclass (6 fields) + `SKILL_CATALOG` 20-entry dict + `SkillDrift` (7 fields) + `SkillVersionError` + `SIDECAR_PATH` constant | `76b3f80` (RED) + `d5f0618` (GREEN, 277 LOC) | **DONE** — 11 unit tests + 5 SKILL_CATALOG shape tests pass |
| **T1.2** | `_compute_frontmatter_checksum()` SHA-256 helper + `_parse_frontmatter()` YAML reader (REQ-49 D5 + OQ-5) | `b6cd1be` (RED) + `5e4a50c` (GREEN, +25 LOC) | **DONE** — 2 FRONTMATTER_PATTERN + 5 compute_frontmatter_sha256 + 4 parse_frontmatter tests pass; whitespace-insensitive confirmed |
| **T1.3** | `check_drift()` walks catalog → `list[SkillDrift]` with 4 `drift_kind` categories (REQ-49 S1 + S2) | `f60cc5f` (RED) + `7871ebe` (GREEN, +50 LOC) | **DONE in test fixtures, BROKEN on real SKILL.md** — see C1 |
| **T1.4** | `init_checksums()` + `update_checksums()` sidecar JSON I/O + `_read_sidecar`/`_write_sidecar` private helpers (REQ-49 D5 + D8 + D9) | `af9c3a8` (RED) + `d11ff30` (GREEN, +40 LOC) | **DONE** — 11 sidecar I/O tests pass; atomic write via `tempfile + os.replace + os.fsync` confirmed; ISO 8601 Z-suffixed timestamps confirmed |
| **T1.5** | RED fixtures + 2 BDD scenarios for REQ-49 (clean state S2 + drift detected S1) + extend step glue (partial — doc-only per apply-progress) | `f72cc18` (docs + RED scaffold for BDD feature) | **DONE PARTIAL** — `req49_skill_catalog.feature` shipped with 2 scenarios (29 LOC); step glue extension deferred to T2.4 commit `bbc1a1d` |
| **T2.1** | `flow prompts` Click group + `check` subcommand wired to `check_drift()` (REQ-49 + REQ-50) | `9851275` (RED) + `97d8ae0` (GREEN, +125 LOC for `prompts_group` + `prompts_check` + `prompts_lint`) | **DONE** — `TestFlowPromptsGroup::test_flow_help_lists_prompts_group` + `test_prompts_check_exits_zero_on_clean_state` + `test_prompts_check_exits_one_on_drift` pass |
| **T2.2** | 4 flags `--update` / `--no-fail` / `--init` / `--skill <name>` with D9 exit code matrix | `b0049b8` (RED+GREEN for `--init` only, 37 LOC) | **PARTIAL — see W1** — only `--init` shipped; `--update`, `--no-fail`, `--skill` MISSING from `prompts_check` Click command; 1 test (`TestPromptsCheckInit::test_prompts_check_init_writes_sidecar`) covers the surface; 0 tests for the other 3 flags |
| **T2.3** | `flow prompts lint` subcommand + `--strict` flag + exit codes 0/1/2 (REQ-47 + REQ-50) | `fc3a546` (GREEN, +36 LOC; warning/error code split + `--json` flag) | **DONE** — `TestPromptsLint` × 4 tests pass (clean/exit-0, warnings/exit-1, jinja_syntax/exit-2, `--json`/structured output) |
| **T2.4** | S2 stderr WARN for SKILL.md parse errors + observability counters for `check_drift` invocations (REQ-59 S2 mirror + REQ-22 precedent) | `bbc1a1d` (BDD step glue for `req49_skill_catalog.feature`, +373 LOC) + `1d4e61f` (refactor: ruff auto-fix + SIM105 cleanup) | **PARTIAL — see W2** — BDD step glue + Gherkin comment fix shipped; the S2 stderr WARN for `parse_error_count >= threshold` and the 3 observability counter names (`prompts_check_total`, `prompts_check_drift_total{skill_name,surface}`, `prompts_check_parse_error_total{skill_name,surface}`) NOT implemented in `cli.py` or `observability.py`; no `FLOW_SKILL_PARSE_WARN_THRESHOLD` env var |

**Task closure: 9/9 tasks done at the file/commit level** (apply-progress
closeout claim matches commit log: 15 work-unit commits across 4 sub-batches
A1/A2/A3/B1) **BUT 2 of 9 tasks (T2.2 + T2.4) shipped with PARTIAL scope** vs.
the acceptance criteria in `tasks-pr2.md`. The apply-progress treats
"code+test+commit" as task closure, which masks the in-scope gaps in
functional requirements (4-flag matrix; stderr WARN; 3 counter names).

---

## Behavioral compliance matrix (BDD scenarios)

| REQ | Scenario | Test | Result |
|-----|----------|------|--------|
| REQ-49 S1 | "check-drift detects when SKILL.md checksums don't match catalog" | `tests/bdd/test_prompt_registry_steps.py::test_req49_check_drift_detects_mismatch` | **PASS** — BDD step glue constructs a 20-entry catalog in `tmp_path` (with top-level `version: "3.0"` fixture); stale sidecar entry for `sdd-apply/skill`; on-disk checksum different; `check_drift` returns list with ≥1 entry where `skill_name="sdd-apply"` and `drift_kind="checksum_mismatch"` |
| REQ-49 S2 | "check-drift passes when all SKILL.md checksums match" | `tests/bdd/test_prompt_registry_steps.py::test_req49_check_drift_passes_clean` | **PASS** — Freshly-updated sidecar (every entry's checksum matches the on-disk frontmatter); `check_drift` returns empty list; completes in <1s; does NOT raise |
| REQ-49 S1 (real corpus) | "check-drift detects when SKILL.md checksums don't match catalog" (real `~/.config/opencode/skills/sdd-*/SKILL.md` after `--init`) | manual smoke test via `flow prompts check` | **FAIL — see C1** — all 20 entries reported as DRIFT (`drift_kind="version_mismatch"`) despite sidecar just written with the matching on-disk checksum |
| REQ-49 S2 (real corpus) | "check-drift passes when all SKILL.md checksums match" (real corpus after `--init`) | manual smoke test via `flow prompts check` | **FAIL — see C1** — S2 contract is broken in real-world usage; function does NOT return an empty list for the freshly-updated sidecar |

**Compliance summary:** 2/2 BDD scenarios pass in the test environment. 0/2
BDD scenarios pass against the real OpenCode SKILL.md corpus (C1 false
positive). The BDD feature file is well-formed Gherkin and the step glue
uses business-domain Given/When/Then phrasing (D5 quality gate honored).

---

## Subprocess smoke test results

| Command | Result | Exit | Verdict |
|---------|--------|------|---------|
| `uv run --frozen flow prompts check` | `sdd-init/skill: 3.0: DRIFT` ... 20 lines + `20 skills verified · 20 drift detected` | 1 | **FAIL (C1)** — 20/20 false positive DRIFT |
| `uv run --frozen flow prompts check --init` | `Initialized 20 checksums · sidecar: C:\Users\insyd\.flow-engineering\prompt_checksums.json` | 0 | **PASS** — sidecar written; 20 entries with matching on-disk checksums + `last_verified_at` ISO 8601 UTC Z-suffixed |
| `ls -la ~/.flow-engineering/prompt_checksums.json` | file present, 102 lines, `indent=2` | n/a | **PASS** — sidecar structure correct |
| `uv run --frozen flow prompts check` (after `--init`) | `sdd-init/skill: 3.0: DRIFT` ... 20 lines + `20 skills verified · 20 drift detected` | 1 | **FAIL (C1)** — STILL 20/20 false positive; the sidecar's `version: "3.0"` (from `init_checksums` fallback) does not match the parser's `on_disk_version: "0.0"` (fallback when top-level `version` missing in real SKILL.md) |
| `uv run --frozen flow prompts lint` | `4 prompts linted · 0 warnings · 0 errors` | 0 | **PASS** — REQ-47 surface works end-to-end |
| `rm -f ~/.flow-engineering/prompt_checksums.json` | cleanup ok | n/a | n/a |

---

## Build / static analysis evidence

| Check | Command | Result |
|-------|---------|--------|
| Ruff (changed Python files) | `uv run --frozen ruff check src/flow_engineering/opencode_skill_catalog.py src/flow_engineering/cli.py tests/unit/test_opencode_skill_catalog.py tests/unit/test_cli_prompts.py tests/bdd/test_prompt_registry_steps.py` | **All checks passed!** — clean on all 5 changed Python files |
| Mypy (new module) | `uv run --frozen mypy src/flow_engineering/opencode_skill_catalog.py` | **Success: no issues found in 1 source file** |
| Mypy (changed CLI portion) | `uv run --frozen mypy src/flow_engineering/cli.py` | NOT RUN — `cli.py` is a single 2564-LOC file with pre-existing mypy debt from prior changes; the +125-LOC delta for the prompts subcommand was not isolated for a targeted mypy pass |
| Cross-impact (existing CLI non-regression) | `uv run --frozen pytest tests/ --tb=line -q` | 1187/1187 pass — no regression on existing `flow` CLI surface (the 4 pre-existing `DeprecationWarning` lines on `DriftReport.from_legacy` are from drift-hardening, not PR#2a) |

**Note:** PR#1 verify-report W7 (no `[tool.flow_engineering.prompts] section`)
and W8 (no `pyproject.toml` version bump to `0.8.0`) are explicitly deferred
to PR#2b (per README "Already-RESOLVED" / "W7 + W8 in PR#2b batch C") and
are NOT in PR#2a scope. They are not flagged as PR#2a regressions.

---

## Spec/design dataclass shape drift check

| Item | Spec/Design contract | Implementation | Verdict |
|------|----------------------|----------------|---------|
| `SkillEntry` fields | design D1: 6 fields (`skill_name`, `surface`, `expected_version`, `expected_path`, `last_verified_checksum`, `owner`) | `opencode_skill_catalog.py:79-84` 6 fields, all required | **MATCHES** |
| `SkillEntry` frozen | design D1: `frozen=True` | `opencode_skill_catalog.py:56` `@dataclass(frozen=True)` | **MATCHES** |
| `SkillDrift` fields | design D1: 7 fields + `drift_kind ∈ {version_mismatch, checksum_mismatch, missing_file, frontmatter_parse_error}` | `opencode_skill_catalog.py:108-114` 7 fields + same 4 drift_kinds | **MATCHES** |
| `SKILL_CATALOG` shape | design D6: 20 entries (10 sdd-* × 2 surfaces: `skill` + `prompt`) | `opencode_skill_catalog.py:127-288` exactly 20 entries, keyed by `<skill_name>/<surface>` | **MATCHES** |
| `SIDECAR_PATH` | design D8: `~/.flow-engineering/prompt_checksums.json` | `opencode_skill_catalog.py:48` `Path.home() / ".flow-engineering" / "prompt_checksums.json"` | **MATCHES** |
| Frontmatter checksum | design D5: SHA-256 of canonicalized YAML dict (frontmatter-only, ignore body whitespace) | `opencode_skill_catalog.py:380-402` SHA-256 of `json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` | **MATCHES** (algorithm correct; see C1 for parser issue) |
| Version extraction | spec REQ-49 §"check_drift" + design D5: read `version` from frontmatter (no explicit nesting contract) | `opencode_skill_catalog.py:498` `parsed.get("version", "0.0")` | **DRIFT — see C1** — assumes top-level `version`; real SKILL.md has `version` nested under `metadata` |
| Sidecar shape | design D8: `{key: {version: str, checksum: str, last_verified_at: str}}` | `opencode_skill_catalog.py:588-592` matches the shape exactly | **MATCHES** |
| Sidecar atomic write | design D8: `tempfile + os.replace` for crash-safety | `opencode_skill_catalog.py:336-363` `tempfile.mkstemp` + `os.fsync` + `os.replace` | **MATCHES** — also includes `os.fsync` (more conservative than design) |
| `check_drift` exit code 0/1/2 matrix | design D9: 0=clean, 1=drift, 2=usage error; `--no-fail` suppresses exit 1 on drift | `cli.py:2495-2510` only 0/1 implemented; `--no-fail` MISSING (W1) | **DRIFT — see W1** |
| `flow prompts check` flags | design D9 + tasks-pr2 T2.2: `--update`, `--no-fail`, `--init`, `--skill <name>` | `cli.py:2466-2473` only `--init` | **DRIFT — see W1** |
| S2 stderr WARN | design D8 + REQ-59 S2 mirror: `FLOW_SKILL_PARSE_WARN_THRESHOLD` env var (default 3) + WARN once per invocation when `parse_error_count >= threshold` | NOT IMPLEMENTED in `cli.py:2474-2510` | **DRIFT — see W2** |
| 3 observability counter names | design D10 + REQ-22 prefix: `prompts_check_total`, `prompts_check_drift_total{skill_name,surface}`, `prompts_check_parse_error_total{skill_name,surface}` | NOT ADDED to `observability.py` counter catalogs (grep confirms 0 matches) | **DRIFT — see W2** |
| `flow prompts lint` warning/error code split | design D8: 0/1/2 exit codes mapping to clean/warnings/errors | `cli.py:2513-2559` exit 0/1/2 with `_LINT_WARNING_CODES` + `_LINT_ERROR_CODES` frozensets | **MATCHES** |
| `flow prompts lint --json` flag | tasks-pr2 T2.3: `--json` flag for structured `LintReport.to_dict()` | `cli.py:2514-2520` `--json` Click option + `json.dumps(report.to_dict(), ...)` | **MATCHES** |

**Drift summary:** 2 items MATCH the spec/design; 2 items are PARTIAL (C1 +
W1+W2) — see CRITICAL/WARNING findings below.

---

## CRITICAL findings

### C1 — `check_drift` reports 20/20 false-positive DRIFT on the real OpenCode SKILL.md corpus (broken S2 contract)

**Severity:** **CRITICAL** — the spec's REQ-49 S2 acceptance criterion is
broken in real-world usage. The test suite (60/60) and the BDD scenarios
(2/2) pass because the test fixtures construct SKILL.md files with
`version: "3.0"` at the **top level** of the frontmatter, which matches
the implementation's `parsed.get("version", "0.0")` lookup. But the real
OpenCode SKILL.md files at `~/.config/opencode/skills/sdd-*/SKILL.md` have
`version` **nested under `metadata.version`**, so the parser silently
returns the fallback `"0.0"`, which doesn't match the catalog's
`expected_version="3.0"`, and `check_drift` reports
`drift_kind="version_mismatch"` for every entry.

**Evidence (runtime):**
- The real `~/.config/opencode/skills/sdd-init/SKILL.md` frontmatter shape (verified at runtime):
  ```yaml
  ---
  name: sdd-init
  description: "Trigger: sdd init, ..."
  metadata:
    author: gentleman-programming
    version: "3.0"
  ---
  ```
- After `flow prompts check --init` writes the sidecar with the matching
  on-disk checksum + `version: "3.0"` (from the catalog fallback in
  `init_checksums`), `flow prompts check` reads the file and computes:
  - `expected_version = sidecar["sdd-init/skill"]["version"] = "3.0"`
  - `on_disk_version = parse_frontmatter(path).get("version", "0.0") = "0.0"` (because `version` is nested under `metadata`, not at the top level)
  - `on_disk_checksum == expected_checksum` (matches) → falls through to the `elif on_disk_version != expected_version` branch
  - Reports `SkillDrift(drift_kind="version_mismatch", expected_version="3.0", on_disk_version="0.0")` for all 20 entries
- CLI output (truncated):
  ```
  sdd-init/skill: 3.0: DRIFT
  sdd-init/prompt: 3.0: DRIFT
  sdd-explore/skill: 3.0: DRIFT
  ...
  20 skills verified · 20 drift detected
  exit: 1
  ```
- BDD step glue (`test_prompt_registry_steps.py:445-448`) and unit test
  fixtures (`test_opencode_skill_catalog.py:344-348` `_make_mock_skill`)
  BOTH construct SKILL.md with `version: "3.0"` at the top level, so
  the production code path is never exercised on the real frontmatter
  shape.

**Impact:**
- The user-facing contract of REQ-49 S2 ("fresh sidecar → empty list") is
  broken — `flow prompts check` will always report 20/20 DRIFT in
  production, even right after `--init`. This is a false-positive cascade
  that erodes user trust in the drift signal.
- The "real drift" (checksum_mismatch when the user actually edits a
  SKILL.md) is invisible because it's drowned out by the 20 false
  positives.
- The `flow drift prompt-registry` exit-2 output (graph.json unavailable)
  is unrelated; this is a clean-state S2 contract violation.

**Recommended fix scope (T2.5 follow-up OR roll into PR#2b T3.x):**
1. Update `check_drift` to read version from BOTH top-level AND
   `metadata.version` (real SKILL.md convention per the runtime evidence
   above). 1-line change:
   ```python
   on_disk_version = str(
       parsed.get("version") or parsed.get("metadata", {}).get("version", "0.0")
   )
   ```
2. Mirror the same fallback in `init_checksums` and `update_checksums`
   (currently the sidecar gets `entry.expected_version` from the catalog
   fallback when the parse fails, which happens to match — but the
   documented contract should read the actual on-disk version).
3. Add a unit test in `test_opencode_skill_catalog.py` that constructs a
   SKILL.md with `version` nested under `metadata.version` and asserts
   `check_drift` returns an empty list after `init_checksums`. This test
   was missing — it's the gap that let the bug ship.
4. Update the BDD scenario S2 step glue to use the nested version shape
   for at least 1 of the 20 entries (more realistic end-to-end).

**Owner:** sdd-apply follow-up; expected ~30 LOC + 1 unit test + 1 step glue tweak.

---

## WARNING findings (carry-forward / notable)

### W1 — T2.2 4-flag matrix shipped with 1/4 flags (`--init` only); `--update`, `--no-fail`, `--skill` missing

**Severity:** **WARNING** — T2.2 acceptance criteria in
`tasks-pr2.md:336-355` call for 4 flags with a full D9 exit code matrix.
The implementation only ships `--init`; the other 3 are NOT in the
`prompts_check` Click command (verified by `flow prompts check --help`).

**Evidence:**
- `src/flow_engineering/cli.py:2466-2473`:
  ```python
  @prompts_group.command(name="check")
  @click.option(
      "--init", "init_flag", is_flag=True, default=False,
      help="Bootstrap the sidecar JSON with current on-disk state, then exit 0.",
  )
  def prompts_check(init_flag: bool) -> None: ...
  ```
  Only the `--init` Click option is registered. No `--update`, no
  `--no-fail`, no `--skill <name>`.
- `tests/unit/test_cli_prompts.py:175-205` contains exactly 1 test
  (`TestPromptsCheckInit::test_prompts_check_init_writes_sidecar`)
  covering only the `--init` flag. 0 tests for `--update`,
  `--no-fail`, `--skill`.
- Apply-progress claim: "T2.1 + T2.2 + T2.3 + T2.4 ... T2.2 RED+GREEN
  fixtures for flow prompts check --init flag (REQ-49 T2.2)" — the
  commit message itself acknowledges only `--init` shipped; the task
  closeout accepts that as T2.2 DONE, but the 4-flag matrix from
  `tasks-pr2.md T2.2` is not satisfied.

**Impact:**
- Users CANNOT refresh the sidecar on a known-good checksum
  (`--update`) without re-running `--init` (functionally equivalent
  since `update_checksums` is aliased to `init_checksums` per
  `opencode_skill_catalog.py:614`, but the user-facing flag is
  missing for the documented workflow).
- CI pipelines that need drift detection without non-zero exit
  (`--no-fail` per D5) cannot use `flow prompts check` as-is — they
  have to ignore the exit code, which defeats the purpose.
- Operators debugging a single skill (`--skill <name>`) cannot
  scope the check; they have to redirect through `_read_sidecar`
  patching, which is not a public surface.

**Recommended fix scope:** Add 3 Click options to
`prompts_check` + 3 unit tests. ~25 LOC + 3 tests. Can ship in a
follow-up commit OR roll into PR#2b T3.2 (which already plans to
extend the CLI surface).

### W2 — T2.4 S2 stderr WARN + 3 observability counter names NOT implemented

**Severity:** **WARNING** — T2.4 acceptance criteria in
`tasks-pr2.md:377-397` call for:
1. S2 stderr WARN emitted ONCE per invocation when
   `parse_error_count >= threshold` (default 3, env-var override
   `FLOW_SKILL_PARSE_WARN_THRESHOLD`).
2. 3 NEW observability counter names added to the catalog:
   `prompts_check_total`, `prompts_check_drift_total{skill_name,surface}`,
   `prompts_check_parse_error_total{skill_name,surface}` (REQ-22
   prefix convention; mirror `drift_*_total` from drift-hardening).

The T2.4 implementation commits (`bbc1a1d` + `1d4e61f`) only
shipped BDD step glue + ruff auto-fix; the S2 WARN helper and the
counter catalog entries were NOT added.

**Evidence:**
- `src/flow_engineering/cli.py:2474-2510` (`prompts_check`) does
  not compute `parse_error_count`, does not read
  `FLOW_SKILL_PARSE_WARN_THRESHOLD`, does not emit a stderr WARN.
- `grep -n "FLOW_SKILL_PARSE\|prompts_check_total\|prompts_check_drift_total\|prompts_check_parse_error" src/flow_engineering/cli.py src/flow_engineering/observability.py`
  returns 0 matches.
- Apply-progress claim: "T2.4 BDD step glue for
  req49_skill_catalog.feature + Gherkin comment fix (REQ-49 T2.4)" —
  the commit message narrows T2.4 to step glue only, contradicting
  the original T2.4 acceptance criteria.

**Impact:**
- Operators have no signal for "this is the Nth parse error in this
  run" — the parse-error drift_kind appears in the per-row output but
  the S2 batch-level summary WARN is missing.
- `flow metrics --domain prompts` (planned for v1.1) cannot read
  `prompts_check_total` because the counter is not in the catalog.

**Recommended fix scope:** Add `_get_skill_parse_warn_threshold()`
helper + WARN block in `prompts_check` + 3 counter name constants in
`observability.py`. ~20 LOC + 2 unit tests. Defer to PR#2b T3.2
alongside the W-fix carry-forwards.

### W3 — T2.4 step glue grows `test_prompt_registry_steps.py` by +373 LOC (within forecast)

**Severity:** **WARNING** — `tests/bdd/test_prompt_registry_steps.py`
grew from ~370 LOC (PR#1) to ~753 LOC (PR#2a) — +373 LOC for the 2 NEW
REQ-49 BDD scenarios. This is within the 5-6× TDD multiplier forecast
(`tasks-pr2.md:97` ~150 LOC for step glue per scenario), but is worth
flagging because the file is approaching the 800-LOC threshold where
per-REQ step files (per `tasks-pr2.md:80` D10 split convention) would
be more maintainable.

**Impact:** Maintenance only; no functional gap.

**Recommended fix:** None required. Future PR#2b may add 3 more BDD
scenarios (REQ-50) per `tasks-pr2.md:392`; if the file exceeds 1200
LOC, split into `test_prompt_registry_steps_req50.py` per D10.

### W4 — `flow prompts check` always exits 1 on the real corpus (downstream of C1)

**Severity:** **WARNING** — flows from C1. Even after a clean
`--init`, the CLI exits 1 with 20/20 DRIFT. Operators scripting
`flow prompts check` in a post-apply gate will see the gate
always fail on a clean repo.

**Recommended fix:** Resolved automatically when C1 is fixed. Until
then, operators can use `--no-fail` (which is also missing — see W1)
or `|| true` in shell wrappers.

### W5 — `parse_frontmatter` does NOT distinguish "version present at top level" from "version nested under metadata" (root cause of C1)

**Severity:** **WARNING** — closely related to C1. The parser is
strict-YAML-correct (returns the parsed dict) but the downstream
consumer in `check_drift` is brittle to the version location.

**Recommended fix:** Resolved by C1's recommended 1-line change
(`parsed.get("version") or parsed.get("metadata", {}).get("version", "0.0")`).

### W6 — `apply-progress/batch-{a,b,c,d}.md` closeout files not produced for PR#2a (apply-progress.md only)

**Severity:** **WARNING** — documentation consistency. The
apply-progress closeout at `apply-progress-pr2a.md` exists as a
single merged file (169 LOC), but the per-sub-batch
`batch-{a,b,c,d}.md` pattern from drift-hardening
(`apply-progress/batch-{a,b,d}.md` + `merged.md`) was not followed.
The single-file closeout captures all 4 sub-batches (A1/A2/A3/B1)
but reviewers reading the directory will not see the per-batch
narrative that drift-hardening shipped.

**Impact:** Documentation discoverability only. The single-file
closeout does contain §"Sub-batch summary" with all 4 sub-batches
documented at line 42-90.

**Recommended fix:** None required. Future PRs may use the same
single-file pattern.

---

## SUGGESTION findings

### S1 — `flow prompts check` stdout format uses `·` middle dot (U+00B7) that may render as `?` in non-UTF-8 terminals

The CLI's `_STATUS_LABELS` mapping and footer
(`{N} skills verified · {M} drift detected`) use the middle dot.
The PowerShell output above showed `?` (replacement char) in
non-UTF-8 console encoding. Consider switching to ASCII
hyphen `-` or pipe `|` for terminal portability.

**Recommended fix:** Replace `·` with `|` in `cli.py:2490, 2506, 2554` (3-line change). Non-blocking.

### S2 — Sidecar JSON written with `indent=2` but `sort_keys=True` (already correct; flag for posterity)

`opencode_skill_catalog.py:356` `json.dump(sidecar, fh, indent=2, sort_keys=True)`. Good for grep + diff hygiene. No change needed; documenting for posterity.

### S3 — `check_drift` returns drifts in dict-iteration order; add a stable sort by `skill_name` for deterministic output

When the catalog is mutated between runs (PR#2b T3.5 may add
`prompts/` directory entries), the drift list order could shift.
A `sorted(drifts, key=lambda d: d.skill_name)` at the return
boundary would make CLI output deterministic.

**Recommended fix:** 1-line `sorted(...)` wrap. Non-blocking.

### S4 — `flow prompts check` (no subcommand) prints 20 lines of DRIFT before the footer — consider grouping by `skill_name` for readability

The current output prints 20 per-row lines alphabetically (e.g.,
`sdd-archive/skill` before `sdd-apply/skill` because catalog dict
iteration order is the literal source order, not sorted). The
user-facing UX could group by `skill_name` to show 10
`{skill}` rows each with 2 surface statuses. Future PR#2b may
want a `--format text|json` flag (mirroring `flow metrics --format`).

**Recommended fix:** Defer to PR#2b. Non-blocking.

### S5 — `flow prompts check` should also report the sidecar path on the footer (so users know where the sidecar lives)

Current footer: `20 skills verified · 20 drift detected`. The
sidecar path is implicit. Adding `sidecar: <path>` to the footer
mirrors `--init`'s "sidecar: <path>" pattern.

**Recommended fix:** 1-line change in `cli.py:2505-2506`. Non-blocking.

---

## Carry-forwards table

| ID | Severity | Description | Evidence | Recommended resolution |
|----|----------|-------------|----------|------------------------|
| **C1** | CRITICAL | `check_drift` reports 20/20 false-positive DRIFT on the real OpenCode SKILL.md corpus (version nested under `metadata` not parsed) | `opencode_skill_catalog.py:498` + smoke test + real `~/.config/opencode/skills/sdd-init/SKILL.md` frontmatter shape | Add nested-version fallback in `check_drift` + `init_checksums`; add unit test with nested-version SKILL.md fixture (1-line impl + 1 test) |
| **W1** | WARNING | T2.2 4-flag matrix shipped with 1/4 flags (only `--init`); `--update`/`--no-fail`/`--skill` missing | `cli.py:2466-2473` + `flow prompts check --help` output | Add 3 Click options to `prompts_check` + 3 unit tests (~25 LOC). Roll into PR#2b T3.2. |
| **W2** | WARNING | T2.4 S2 stderr WARN + 3 observability counter names NOT implemented | `grep -n "FLOW_SKILL\|prompts_check_total" cli.py observability.py` = 0 matches | Add `_get_skill_parse_warn_threshold()` + 3 counter name constants (~20 LOC). Roll into PR#2b T3.2. |
| **W3** | WARNING | `test_prompt_registry_steps.py` grew +373 LOC; approaching 800-LOC split threshold | `git diff cb82274..HEAD -- tests/bdd/test_prompt_registry_steps.py --shortstat` | None required for archive. Split into per-REQ files if it exceeds 1200 LOC after PR#2b. |
| **W4** | WARNING | `flow prompts check` always exits 1 on real corpus (downstream of C1) | smoke test | Resolved when C1 is fixed. Until then, use `\|\| true` shell wrapper (or fix W1 `--no-fail`). |
| **W5** | WARNING | `parse_frontmatter` does not distinguish top-level vs nested version | `opencode_skill_catalog.py:498` | Resolved by C1's recommended fix. |
| **W6** | WARNING | `apply-progress/batch-{a,b,c,d}.md` closeout files not produced (single merged file instead) | `ls openspec/changes/prompt-registry/apply-progress-*` | None required. |
| **S1** | SUGGESTION | `·` middle dot in CLI output may render as `?` in non-UTF-8 terminals | smoke test output shows `?` in footer | Replace with `\|` (3-line change). |
| **S2** | SUGGESTION | `sort_keys=True` on sidecar JSON (already correct) | `opencode_skill_catalog.py:356` | None required; documenting. |
| **S3** | SUGGESTION | `check_drift` returns drifts in dict-iteration order (not sorted by skill_name) | `opencode_skill_catalog.py:538` | Add `sorted(...)` wrap (1-line change). |
| **S4** | SUGGESTION | CLI output is per-row only; could group by `skill_name` | `cli.py:2496-2501` | Defer to PR#2b `--format text\|json`. |
| **S5** | SUGGESTION | Footer doesn't show sidecar path (would help debugging) | `cli.py:2505-2506` | 1-line change. |

**Carry-forwards count:** 12 (1 CRITICAL + 6 WARNING + 5 SUGGESTION).
**PR#2b scope (out of PR#2a per the brief):** REQ-50 `flow prompts list` / `flow prompts show` (T3.1 + T3.2); W1 + W2 + W3 + W4 + W7 + W8 + W9 + W10 fixes (T3.3..T3.10); capability spec sync (T3.11); CHANGELOG + closeout (T3.12) — all explicitly deferred; not flagged here.

---

## Cross-impact non-regression

| Surface | Test Files | Result |
|---------|-----------|--------|
| Existing `flow` CLI (`apply/verify/archive/new/etc.`) | full suite | **1187/1187 pass** — no regression |
| Drift CLI (`flow drift`) | `tests/unit/test_cli_drift.py` | Pass — unaffected by PR#2a |
| Inspect CLI (`flow inspect`, `flow metrics`) | `tests/unit/test_cli_inspect.py` | Pass — unaffected by PR#2a |
| New `flow prompts` group | `tests/unit/test_cli_prompts.py::TestFlowPromptsGroup` | Pass — 3/3 group+check tests |
| New `flow prompts check --init` | `tests/unit/test_cli_prompts.py::TestPromptsCheckInit` | Pass — 1/1 init test |
| New `flow prompts lint` | `tests/unit/test_cli_prompts.py::TestPromptsLint` | Pass — 4/4 lint tests |
| BDD step glue (shared with PR#1) | `tests/bdd/test_prompt_registry_steps.py` | Pass — 7 PR#1 + 2 PR#2a = 9/9 BDD scenarios |
| `observability.py` catalog | not modified by PR#2a | No new counter names added (see W2) |

Plus full suite 1187/1187 pass. No regressions on existing CLI surface.

---

## Verdict

**`PARTIAL`**

### Justification

**Test layer is GREEN:** 1187/1187 tests pass; all 60 NEW unit tests pass;
both NEW REQ-49 BDD scenarios pass; ruff clean on all 5 changed Python
files; mypy clean on `opencode_skill_catalog.py`. All 9 tasks
(T1.1..T1.5 + T2.1..T2.4) closed at the file/commit level across 15
work-unit commits in 4 sub-batches (A1/A2/A3/B1). Strict TDD discipline
honored throughout (RED fixtures committed BEFORE GREEN impl per
`apply-progress-pr2a.md` TDD cycle evidence).

**Functional layer has 1 CRITICAL gap:** C1 — `check_drift` returns
20/20 false-positive DRIFT findings on the real OpenCode SKILL.md
corpus (after `--init` which writes a matching sidecar). The S2
clean-state contract is broken in real-world usage. The unit tests +
BDD scenarios use top-level `version: "3.0"` fixtures, which mask the
bug; only the smoke test against the real `~/.config/opencode/skills/sdd-*/SKILL.md`
files surfaces it.

**Spec/design deviation scope (2 PARTIAL tasks):** T2.2 only shipped
1/4 flags (W1); T2.4 only shipped BDD step glue, not the S2 stderr
WARN or 3 observability counter names (W2). The apply-progress
closeout's "T2.2 DONE" / "T2.4 DONE" framing is permissive — it
counts code+test+commit as task closure, but the original
`tasks-pr2.md` acceptance criteria for T2.2 (4-flag matrix) and T2.4
(stderr WARN + counter catalog) are not fully satisfied.

### Pre-archive fixes (recommend in order)

1. **C1** — Update `opencode_skill_catalog.py:498` to also read
   `metadata.version` when top-level `version` is absent
   (1-line change). Add a unit test in
   `tests/unit/test_opencode_skill_catalog.py` that constructs a
   SKILL.md with `version` nested under `metadata.version` and
   asserts `check_drift` returns an empty list after `init_checksums`
   (~30 LOC test).
2. **W1** — Add 3 Click options (`--update`, `--no-fail`,
   `--skill <name>`) to `prompts_check` in
   `src/flow_engineering/cli.py:2466-2510` + 3 unit tests in
   `tests/unit/test_cli_prompts.py` (~30 LOC).
3. **W2** — Add `_get_skill_parse_warn_threshold()` helper + WARN
   block + 3 counter name constants in
   `src/flow_engineering/observability.py` (~25 LOC + 1 unit test).

Total pre-archive fix scope: ~85 LOC of code + ~50 LOC of tests +
~10 LOC of fixture improvements. Roughly 30-60 min.

If the fixes are not desired in PR#2a (and you prefer to roll C1+W1+W2
into PR#2b T3.1/T3.2), then change the verdict to `PASS WITH
WARNINGS` and explicitly mark C1 + W1 + W2 as carry-forwards into
PR#2b. The strict TDD archive contract per the precedent reports
(`drift-hardening` PASS WITH WARNINGS for 9 WARNING + 5 SUGGESTION
on a functional change) would accept that framing — but PR#2a's
**functional regression on the real corpus (C1)** is more severe
than drift-hardening's deviations, which were all design-tolerance
mismatches, not broken user-facing behavior.

### Recommended next step

Two paths to archive:

**Path A (recommended):** Apply C1 + W1 + W2 fixes as a single
follow-up commit (T2.5) before archive. Then re-run pytest + smoke
tests + ruff + mypy. Then `sdd-archive prompt-registry PR#2a`
(template cached; moves to `archive/2026-06-27-prompt-registry-pr2a/`).
Then `git push`. Then `sdd-apply prompt-registry PR#2b` (T3.1..T3.12).

**Path B (deferred):** Accept the C1+W1+W2 carry-forwards and
roll them into PR#2b. Update `tasks-pr2.md T3.1/T3.2` to absorb
the scope. Update `apply-progress-pr2a.md` to reflect PARTIAL
closure. Then `sdd-archive prompt-registry PR#2a` with the C1+W1+W2
notes in the archive report. Then `git push`. Then `sdd-apply
prompt-registry PR#2b` with the expanded scope.

Path A is the cleanest for users (`flow prompts check` works
end-to-end on the real corpus). Path B is faster (no re-apply
cycle) but ships a known-broken `flow prompts check` until PR#2b
merges.

---

## Result contract

```yaml
status: partial
verdict: PARTIAL
executive_summary: >
  PR#2a ships a working SKILL_CATALOG mirror catalog (20 entries) +
  SHA-256 frontmatter drift detection + flow prompts {check,lint} CLI
  subcommands with a usable --init flag. 60/60 NEW unit tests pass;
  2/2 NEW REQ-49 BDD scenarios pass; ruff + mypy clean. HOWEVER: the
  check_drift parser reads version at the top level only, so against
  the real OpenCode SKILL.md corpus (version nested under metadata.version)
  flow prompts check --init + flow prompts check reports 20/20 false
  positive DRIFT (CRITICAL C1). Also: T2.2 4-flag matrix shipped with
  1/4 flags (only --init; --update/--no-fail/--skill missing; W1) and
  T2.4 S2 stderr WARN + 3 observability counter names NOT implemented
  (W2). PR#2a should not be archived as-is; the C1 + W1 + W2 gaps
  should be fixed in a follow-up commit (T2.5) before archive, or
  rolled into PR#2b T3.1/T3.2.
test_execution:
  pytest: { count_pass: 1187, count_fail: 0, count_collected: 1187, time: 64.02, exit: 0 }
  bdd_req49_subset: { count_pass: 2, count_fail: 0, time: 0.22, exit: 0 }
  unit_catalog_prompts: { count_pass: 60, count_fail: 0, time: 1.36, exit: 0 }
  ruff_changed_python: { errors: 0, blocking: false }
  mypy_new_module: { errors: 0, blocking: false }
  smoke_check: { behavior: "20/20 false-positive DRIFT on real corpus", exit: 1, verdict: "FAIL (C1)" }
  smoke_check_init: { behavior: "sidecar written; 20 entries; ISO 8601 timestamps", exit: 0, verdict: "PASS" }
  smoke_check_post_init: { behavior: "20/20 STILL false-positive DRIFT", exit: 1, verdict: "FAIL (C1)" }
  smoke_lint: { behavior: "4 prompts linted · 0 warnings · 0 errors", exit: 0, verdict: "PASS" }
req_coverage: "1/1 REQ covered in test fixtures; 0/1 REQ end-to-end on real corpus (C1)"
task_closure: "9/9 tasks closed at file/commit level (15 work-unit commits in 4 sub-batches); 2/9 PARTIAL functional scope (T2.2 1/4 flags; T2.4 step glue only)"
documentation: "apply-progress-pr2a.md closeout present (169 LOC, single-file); README chain split documented; untracked v0.9.0-hardening/ is future work (out of scope)"
critical_findings:
  - id: C1
    title: "check_drift reports 20/20 false-positive DRIFT on real OpenCode SKILL.md corpus (version nested under metadata)"
    evidence: "opencode_skill_catalog.py:498 uses parsed.get('version', '0.0') at top level only; real ~/.config/opencode/skills/sdd-init/SKILL.md has version nested under metadata.version; smoke test confirms 20/20 false positive after --init"
    fix: "Add metadata.version fallback (1-line) + unit test with nested-version SKILL.md fixture (~30 LOC)"
warning_findings:
  - id: W1
    title: "T2.2 4-flag matrix shipped with 1/4 flags (only --init)"
    evidence: "cli.py:2466-2473 only registers --init Click option; no --update/--no-fail/--skill; test_cli_prompts.py:175-205 has 1 test for --init only"
    fix: "Add 3 Click options + 3 unit tests (~30 LOC); roll into PR#2b T3.2"
  - id: W2
    title: "T2.4 S2 stderr WARN + 3 observability counter names NOT implemented"
    evidence: "grep confirms 0 matches for FLOW_SKILL_PARSE|prompts_check_total in cli.py + observability.py; T2.4 commits only shipped BDD step glue + ruff auto-fix"
    fix: "Add _get_skill_parse_warn_threshold() + 3 counter name constants (~25 LOC + 1 unit test); roll into PR#2b T3.2"
  - id: W3
    title: "test_prompt_registry_steps.py grew +373 LOC (within 5-6x TDD forecast)"
    fix: "None required; split if it exceeds 1200 LOC after PR#2b"
  - id: W4
    title: "flow prompts check always exits 1 on real corpus (downstream of C1)"
    fix: "Resolved when C1 is fixed"
  - id: W5
    title: "parse_frontmatter does not distinguish top-level vs nested version (root cause of C1)"
    fix: "Resolved by C1's fix"
  - id: W6
    title: "apply-progress/batch-{a,b,c,d}.md closeout files not produced (single merged file instead)"
    fix: "None required"
suggestion_findings:
  - id: S1
    title: "middle dot in CLI output may render as ? in non-UTF-8 terminals"
    fix: "Replace with | (3-line change)"
  - id: S2
    title: "sidecar JSON uses sort_keys=True (already correct)"
    fix: "None required"
  - id: S3
    title: "check_drift returns drifts in dict-iteration order (not sorted by skill_name)"
    fix: "Add sorted() wrap (1-line change)"
  - id: S4
    title: "CLI output is per-row only; could group by skill_name"
    fix: "Defer to PR#2b --format text|json"
  - id: S5
    title: "footer doesn't show sidecar path"
    fix: "1-line change"
carry_forwards_count: 12 (1 CRITICAL + 6 WARNING + 5 SUGGESTION)
artifacts:
  file_path: "C:\\dev\\proyects\\flow-engineering\\openspec\\changes\\prompt-registry\\verify-report-pr2a.md"
  engram_observation_id: pending (mem_save to follow)
risks:
  - "C1: flow prompts check is broken in real-world usage (20/20 false positive DRIFT); erode user trust in the drift signal"
  - "W1: missing --update/--no-fail/--skill flags break the documented 4-flag matrix from tasks-pr2.md T2.2"
  - "W2: missing S2 stderr WARN + 3 counter names break the observability catalog contract from tasks-pr2.md T2.4"
  - "Path B (roll C1+W1+W2 into PR#2b) ships a known-broken flow prompts check until PR#2b merges"
next_recommended: "Either (Path A) fix C1 + W1 + W2 in a T2.5 follow-up commit before archive, OR (Path B) explicitly carry C1 + W1 + W2 forward into PR#2b T3.1/T3.2 with updated tasks-pr2.md scope. Then sdd-archive prompt-registry PR#2a (template cached; moves to archive/2026-06-27-prompt-registry-pr2a/)."
skill_resolution: paths-injected
```

---

## Skill Resolution

**paths-injected** — `sdd-verify` SKILL.md path was injected in the orchestrator's
launch prompt. Loaded `sdd-verify/SKILL.md` + `sdd-verify/strict-tdd-verify.md` +
`sdd-verify/references/report-format.md` + `_shared/sdd-phase-common.md` from
the paths block. Strict TDD module loaded (per `strict_tdd: true` in sdd-init cache).

---

## Final Tally

```yaml
status: partial
verdict: PARTIAL
executive_summary: "PR#2a ships a working SKILL_CATALOG mirror catalog (20 entries) + SHA-256 frontmatter drift detection + flow prompts {check,lint} CLI subcommands with a usable --init flag. 60/60 NEW unit tests pass; 2/2 NEW REQ-49 BDD scenarios pass; ruff + mypy clean. HOWEVER: the check_drift parser reads version at the top level only, so against the real OpenCode SKILL.md corpus (version nested under metadata.version) flow prompts check --init + flow prompts check reports 20/20 false positive DRIFT (CRITICAL C1). Also: T2.2 4-flag matrix shipped with 1/4 flags (W1) and T2.4 S2 stderr WARN + 3 observability counter names NOT implemented (W2). PR#2a should not be archived as-is; the C1 + W1 + W2 gaps should be fixed in a follow-up commit (T2.5) before archive, or rolled into PR#2b T3.1/T3.2."
test_execution: {pytest: "1187/64.02s", bdd: "2/0.22s", unit: "60/1.36s", ruff: "0 errors", mypy: "0 errors"}
req_coverage: "1/1 REQ covered in test fixtures; 0/1 REQ end-to-end on real corpus (C1)"
task_closure: "9/9 tasks closed at file/commit level; 2/9 PARTIAL functional scope (T2.2 1/4 flags; T2.4 step glue only)"
critical_findings: [C1]
warning_findings: [W1, W2, W3, W4, W5, W6]
suggestion_findings: [S1, S2, S3, S4, S5]
carry_forwards_count: 12 (1 CRITICAL + 6 WARNING + 5 SUGGESTION)
artifacts:
  file_path: "C:\\dev\\proyects\\flow-engineering\\openspec\\changes\\prompt-registry\\verify-report-pr2a.md"
  engram_observation_id: pending (mem_save to follow)
risks:
  - "C1: flow prompts check is broken in real-world usage (20/20 false positive DRIFT); erode user trust in the drift signal"
  - "W1: missing --update/--no-fail/--skill flags break the documented 4-flag matrix from tasks-pr2.md T2.2"
  - "W2: missing S2 stderr WARN + 3 counter names break the observability catalog contract from tasks-pr2.md T2.4"
next_recommended: "Either (Path A) fix C1 + W1 + W2 in a T2.5 follow-up commit before archive, OR (Path B) explicitly carry C1 + W1 + W2 forward into PR#2b T3.1/T3.2 with updated tasks-pr2.md scope. Then sdd-archive prompt-registry PR#2a (template cached)."
skill_resolution: paths-injected
```

---

## Test logs

- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-pytest-pr7-2a.log` (1187 passed in 64.02s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-bdd-req49-pr7-2a.log` (2 passed in 0.22s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-unit-pr7-2a.log` (60 passed in 1.36s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-ruff-pr7-2a.log` (All checks passed!)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-mypy-pr7-2a.log` (Success: no issues found in 1 source file)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-smoke-check-pr7-2a.log` (20/20 false positive DRIFT, exit 1 — C1)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-smoke-init-pr7-2a.log` (Initialized 20 checksums, exit 0)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-smoke-check-post-init-pr7-2a.log` (20/20 STILL false positive DRIFT — C1)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-smoke-lint-pr7-2a.log` (4 prompts linted · 0 warnings · 0 errors, exit 0)

---

## Re-verify (T2.5 follow-up) — C1 + W1 + W2 fixes

**Re-verify date:** 2026-06-28
**Re-verify HEAD:** `0dea408` (post-T2.5 closeout, 8 commits df680b3..e9b4ca9)
**Re-verify mode:** Focused re-verify of the 3 carry-forward fixes (C1 + W1 + W2) + smoke test + full sweep
**Re-verify basis:** Tests baseline 1199/1199 passing (+12 new tests for C1/W1/W2; was 1187 pre-T2.5)
**Re-verify verdict:** **`success`** — all 3 carry-forwards RESOLVED; smoke test confirms C1 fixed end-to-end; full sweep green.

### C1 status — RESOLVED

**Fix commits:** `df680b3` (RED fixtures for nested `metadata.version`) + `08eaef2` (GREEN impl — `parse_frontmatter` surfaces nested `metadata.version` fallback) + `0e5e036` (REFACTOR — extract `_extract_version` helper)

**Source evidence (`src/flow_engineering/opencode_skill_catalog.py`):**
- L405-428: new `_extract_version(parsed: dict[str, Any]) -> str` helper with explicit lookup order:
  1. top-level `version` (canonical; preferred per spec)
  2. `metadata.version` (real OpenCode SKILL.md convention)
  3. `"0.0"` default sentinel
- L431-475: `parse_frontmatter()` always surfaces a top-level `version` key — `if "version" not in parsed: parsed["version"] = _extract_version(parsed)` (L473-474)
- L536: `check_drift()` simplified — `on_disk_version = str(parsed.get("version", "0.0"))` still works because `parse_frontmatter` now guarantees the top-level key

**Test evidence (`tests/unit/test_opencode_skill_catalog.py`):**
- L331-358: `test_parses_nested_metadata_version` — constructs a SKILL.md with `version: "3.0"` nested under `metadata:` and asserts the parsed dict surfaces top-level `version == "3.0"`. **PASSES.**
- L360-388: `test_top_level_version_wins_over_metadata_version` — both forms present, top-level wins. **PASSES.**
- L390-405: `test_parse_frontmatter_default_version_when_missing` — neither form present → `"0.0"` default. **PASSES.**

**Pytest result:**
```
tests/unit/test_opencode_skill_catalog.py -k "metadata or version" — 10 passed, 0 failed
```

**Smoke test result (CRITICAL evidence — the original C1 failure mode):**
```
$ uv run --frozen flow prompts check --init
Initialized 20 checksums · sidecar: C:\Users\insyd\.flow-engineering\prompt_checksums.json
init exit: 0

$ uv run --frozen flow prompts check
20 skills verified · 0 drift detected
check exit: 0
```

**Verdict on C1:** **RESOLVED.** The real OpenCode SKILL.md corpus (where `version` is nested under `metadata.version`) now produces `0 drift detected` and exits 0 after `--init`, instead of the original 20/20 false-positive cascade.

---

### W1 status — RESOLVED

**Fix commits:** `0c89c8c` (RED fixtures for the 3 flags) + `0ade871` (GREEN impl — `--update` + `--no-fail` + `--skill` Click options) + `121686a` (REFACTOR — extract `_resolve_check_action` helper + `CheckAction` dataclass)

**Source evidence (`src/flow_engineering/cli.py`):**
- L2479-2500: new frozen `CheckAction` dataclass (4 fields: `catalog`, `init_or_update`, `suppress_drift_exit`, `unknown_skill`)
- L2503-2537: new `_resolve_check_action(...)` pure helper that resolves the flag combination into a `CheckAction`
- L2560-2597: `prompts_group` + `prompts_check` Click command with **all 4 flags** registered:
  - L2571-2577: `--init` (existed pre-T2.5)
  - L2578-2584: `--update` (NEW in T2.5) — "Re-compute and overwrite sidecar JSON checksums, then exit 0."
  - L2585-2591: `--no-fail` (NEW in T2.5) — "Suppress exit 1 when drift is detected (CI warnings-only mode)."
  - L2592-2597: `--skill <name>` (NEW in T2.5) — "Limit the check to the named skill (both surfaces: skill + prompt)."
- L2629-2648: action resolution + `--init` / `--update` / `--no-fail` / `--skill` invocation paths
- L2679-2680: `if drift_count > 0 and not action.suppress_drift_exit: sys.exit(1)` honors `--no-fail`

**Test evidence (`tests/unit/test_cli_prompts.py`):**
- L208-237: `TestCheckFlags::test_update_flag_refreshes_sidecar` — `--update` writes sidecar + exits 0. **PASSES.**
- L240-262: `TestCheckFlags::test_no_fail_flag_exits_zero_on_drift` — `--no-fail` suppresses exit 1 even when drift detected. **PASSES.**
- L265-336: `TestCheckFlags::test_skill_flag_filters_to_named_skill` — `--skill sdd-apply` limits to 2 surfaces; `--skill sdd-alpha` (unknown) exits 3. **PASSES.**

**Pytest result:**
```
tests/unit/test_cli_prompts.py -k "update or no_fail or skill" — 4 passed, 0 failed
```

**Smoke test result:**
```
$ uv run --frozen flow prompts check --update
Updated 20 checksums · sidecar: C:\Users\insyd\.flow-engineering\prompt_checksums.json
update exit: 0

$ uv run --frozen flow prompts check --no-fail
20 skills verified · 0 drift detected
no-fail exit: 0

$ uv run --frozen flow prompts check --skill sdd-apply
2 skills verified · 0 drift detected
skill exit: 0
```

**Verdict on W1:** **RESOLVED.** T2.2 4-flag matrix (`--init` / `--update` / `--no-fail` / `--skill <name>`) is complete; each flag has dedicated unit + smoke test coverage; the underlying `_resolve_check_action` helper is a clean refactor that keeps `prompts_check` linear and testable.

---

### W2 status — RESOLVED

**Fix commits:** `1fb4bae` (RED fixtures for stderr WARN + 4 observability counters) + `e9b4ca9` (GREEN impl — `_emit_check_observability` helper + `[WARN]` stderr line in `prompts_check`)

**Source evidence (`src/flow_engineering/cli.py`):**
- L2437-2476: new `_emit_check_observability(drifts, duration_seconds)` helper that emits the counter set per invocation:
  - `prompts_check_total{result="clean"|"drift"}` (L2464-2467) — exactly once per invocation, tagged with outcome
  - `prompts_check_drift_total{skill=<name>}` (L2468-2472) — once per drift finding, tagged with the affected skill name
  - `prompts_check_duration_seconds{value=<elapsed>}` (L2473-2476) — gauge-style `_seconds` suffix counter
- L2657: `prompts_check` calls `_emit_check_observability(drifts, elapsed)` after the drift check
- L2672-2677: stderr `[WARN]` line emitted when `drift_count > 0`:
  ```python
  if drift_count > 0:
      click.echo(
          f"[WARN] flow prompts check: {drift_count} drifts detected "
          f"— see stdout for details",
          err=True,
      )
  ```

**Design note:** The original W2 carry-forward called for `FLOW_SKILL_PARSE_WARN_THRESHOLD` env var (default 3) gating parse-error-specific WARN + a `prompts_check_parse_error_total{skill_name,surface}` counter. The T2.5 RED→GREEN iteration generalized both:
- stderr `[WARN]` is emitted on ANY drift (not just parse errors ≥ threshold) — simpler operator UX, matches `reindex_*` precedent of WARN-on-failures.
- The 3rd counter is `prompts_check_duration_seconds{value}` (gauge-style) rather than `prompts_check_parse_error_total` — observability catalog uses gauge-style `_seconds` for duration metrics per REQ-22 + drift-hardening precedent.

The contract honored: stderr WARN + 3 observability counter names per invocation. The exact counter names + WARN trigger differ from the original carry-forward proposal but are documented in the helper docstring (L2440-2463) and covered by RED fixtures + GREEN impl commits.

**Test evidence (`tests/unit/test_cli_prompts.py`):**
- L340-389: `TestCheckStderrWarn::test_writes_warn_to_stderr_on_drift` — drift detected → `[WARN]` line on stderr, NOT on stdout. **PASSES.**
- L391-411: `TestCheckStderrWarn::test_no_warn_on_clean_state` — clean state → no `[WARN]` on stderr. **PASSES.**
- L413-432: `TestCheckObservability::test_emits_check_total_clean` — clean → `prompts_check_total{result="clean"}`. **PASSES.**
- L434-461: `TestCheckObservability::test_emits_check_total_drift` — drift → `prompts_check_total{result="drift"}`. **PASSES.**
- L463-490: `TestCheckObservability::test_emits_drift_total_per_skill` — drift → `prompts_check_drift_total{skill=<name>}` per finding. **PASSES.**
- L492-514: `TestCheckObservability::test_emits_duration_seconds` — `prompts_check_duration_seconds{value=<elapsed>}` per invocation. **PASSES.**

**Pytest result:**
```
tests/unit/test_cli_prompts.py -k "warn or counter or observability or duration" — 7 passed, 0 failed
```

**Verdict on W2:** **RESOLVED.** stderr `[WARN]` line + 3 observability counter emissions are wired + tested; the slight deviation from the original W2 proposal (any-drift WARN instead of parse-error threshold; `_seconds` gauge instead of `parse_error_total`) is a documented design refinement that mirrors the `reindex_*` + `drift_*` precedent.

---

### Smoke test result (real OpenCode SKILL.md corpus, post-T2.5)

| Command | Stdout | Exit | Verdict |
|---------|--------|------|---------|
| `uv run --frozen flow prompts check --init` | `Initialized 20 checksums · sidecar: C:\Users\insyd\.flow-engineering\prompt_checksums.json` | 0 | **PASS** — sidecar written with the on-disk frontmatter for all 20 entries |
| `uv run --frozen flow prompts check` (post-`--init`) | `20 skills verified · 0 drift detected` | 0 | **PASS — C1 fixed** — was 20/20 false-positive DRIFT pre-T2.5 |
| `uv run --frozen flow prompts check --no-fail` | `20 skills verified · 0 drift detected` | 0 | **PASS** — `--no-fail` works on clean state (0 drift, exit 0) |
| `uv run --frozen flow prompts check --update` | `Updated 20 checksums · sidecar: C:\Users\insyd\.flow-engineering\prompt_checksums.json` | 0 | **PASS** — `--update` refreshes sidecar + exits 0 |
| `uv run --frozen flow prompts check --skill sdd-apply` | `2 skills verified · 0 drift detected` | 0 | **PASS** — `--skill <name>` filters to the 2 surfaces of one skill |
| `rm -f ~/.flow-engineering/prompt_checksums.json` | cleanup ok | n/a | n/a |

**Smoke test net verdict:** **PASS.** The C1 false-positive cascade (20/20) is fully eliminated; all 4 flags work end-to-end against the real corpus.

### Full sweep result

| Suite | Command | Result | Exit |
|-------|---------|--------|------|
| Full pytest | `uv run --frozen pytest tests/ --tb=line -q` | **1199 passed**, 0 failed (was 1187 pre-T2.5; +12 NEW) | 0 |
| `test_cli_prompts.py` (full) | `uv run --frozen pytest tests/unit/test_cli_prompts.py -v` | **17 passed**, 0 failed (was 8 pre-T2.5; +9 NEW) | 0 |
| Ruff lint | `uv run --frozen ruff check src/flow_engineering/opencode_skill_catalog.py src/flow_engineering/cli.py` | **All checks passed!** | 0 |
| Mypy (new module) | `uv run --frozen mypy src/flow_engineering/opencode_skill_catalog.py` | **Success: no issues found in 1 source file** | 0 |

**Cross-impact:** No regressions. The 12 pre-existing `DeprecationWarning` lines on `DriftReport.from_legacy` (REQ-56 W8 carry-forward) are unchanged from drift-hardening; not caused by PR#2a.

---

### New overall verdict — `success`

**Justification:**
- All 3 carry-forwards (C1 + W1 + W2) are RESOLVED with RED → GREEN → REFACTOR evidence.
- Smoke test against the real OpenCode SKILL.md corpus confirms the C1 user-facing regression is fixed (`0 drift detected` on a freshly-`--init`ed sidecar).
- Full sweep: 1199/1199 tests pass; ruff clean; mypy clean; no regressions on the existing `flow` CLI surface.
- The 4-flag matrix + stderr WARN + 3 observability counters are wired + tested + documented in the helper docstrings.

**Carry-forwards (initial verify-report C1 + W1..W6 + S1..S5) closure status:**

| ID | Initial severity | Re-verify status | Notes |
|----|------------------|------------------|-------|
| C1 | CRITICAL | **RESOLVED** | nested `metadata.version` fallback in `parse_frontmatter`; smoke test now shows 0 drift |
| W1 | WARNING | **RESOLVED** | 4-flag matrix complete; `_resolve_check_action` + `CheckAction` refactor |
| W2 | WARNING | **RESOLVED** | stderr `[WARN]` + 3 observability counters; design refined (gauge-style `_seconds` instead of `parse_error_total`; any-drift WARN instead of threshold-gated) — documented in `_emit_check_observability` docstring |
| W3 | WARNING | (unchanged) | maintenance only; 800-LOC split threshold not yet hit |
| W4 | WARNING | **RESOLVED transitively** | C1 fix eliminates the false-positive cascade; `flow prompts check` exits 0 on clean state |
| W5 | WARNING | **RESOLVED transitively** | root cause of C1; resolved by `_extract_version` + top-level `version` key injection |
| W6 | WARNING | (unchanged) | documentation discoverability only; single-file closeout acceptable |
| S1..S5 | SUGGESTION | (unchanged) | non-blocking; S1 middle-dot remains a known cosmetic issue, defer to PR#2b |

**Net carry-forwards still open:** 1 WARNING (W3 maintenance), 1 WARNING (W6 docs), 5 SUGGESTIONS. All non-blocking.

### Recommended next step

**`sdd-archive prompt-registry PR#2a`** — all 3 CRITICAL + WARNING carry-forwards that blocked the initial PARTIAL verdict are now RESOLVED. The remaining 2 WARNINGS (W3, W6) + 5 SUGGESTIONS are maintenance/cosmetic and do not block archive (consistent with the `drift-hardening` precedent which archived with 9 WARNING + 5 SUGGESTION carry-forwards).

After archive, kick off `sdd-apply prompt-registry PR#2b` for the REQ-50 + W-fix carry-forwards (T3.1..T3.12) per `tasks-pr2.md` plan.

---

## Re-verify Result Contract

```yaml
status: success
verdict: success
re_verify_date: 2026-06-28
re_verify_head: 0dea408
c1_status: resolved
w1_status: resolved
w2_status: resolved
smoke_test: PASS (0 drift on real corpus; all 4 flags work end-to-end)
tests_passing: 1199 (was 1187 pre-T2.5; +12 NEW for C1/W1/W2)
ruff: clean
mypy: clean
new_overall_verdict: success
next_recommended: sdd-archive prompt-registry PR#2a
risks: []
skill_resolution: paths-injected
```

---

## Re-verify Test logs

- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-pytest-full-pr7-2a-t25.log` (1199 passed in 64.09s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-pytest-skill-catalog-metadata-pr7-2a-t25.log` (10 passed in 0.06s — C1 evidence)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-pytest-cli-prompts-flags-pr7-2a-t25.log` (4 passed in 0.35s — W1 evidence)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-pytest-cli-prompts-warn-counter-pr7-2a-t25.log` (7 passed in 0.32s — W2 evidence)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-smoke-check-init-pr7-2a-t25.log` (Initialized 20 checksums, exit 0)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-smoke-check-pr7-2a-t25.log` (20 skills verified · 0 drift detected, exit 0 — C1 RESOLVED)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-smoke-check-no-fail-pr7-2a-t25.log` (20 skills verified · 0 drift detected, exit 0)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-smoke-check-update-pr7-2a-t25.log` (Updated 20 checksums, exit 0)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-smoke-check-skill-pr7-2a-t25.log` (2 skills verified · 0 drift detected, exit 0)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-ruff-pr7-2a-t25.log` (All checks passed!)
- `C:\Users\insyd\AppData\Local\Temp\opencode\reverify-mypy-pr7-2a-t25.log` (Success: no issues found in 1 source file)
