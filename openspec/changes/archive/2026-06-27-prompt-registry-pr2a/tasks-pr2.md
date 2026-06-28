<!-- tasks-pr2.md: prompt-registry PR#2 task breakdown. Source: sdd-tasks sub-agent. -->
# Tasks: prompt-registry PR#2

**Change:** `prompt-registry` (change #7, PR#2)
**Builds on:** PR#1 archive (REQ-45/46/47 — catalog+render+lint) at `openspec/changes/archive/2026-06-27-prompt-registry-pr1/`; original `proposal.md` §"In scope (PR#2)" (REQ-49/50); `design.md` D1..D12 + 10 open questions resolved; `spec.md` REQ-49 ×2 BDD + REQ-50 ×3 BDD; `verify-report-pr1.md` W1..W10 carry-forwards
**Date:** 2026-06-27
**Status:** SPECIFIED + DESIGNED + PR#1 ARCHIVED → ready for sdd-apply (chained PRs recommended)
**Strict TDD:** ON (per `decision-code-linking` archive-report #119 S3 precedent; RED → GREEN → REFACTOR cycle per task)

> **W-fix note**: PR#1 verify-report raised 10 carry-forwards (W1..W10). PR#2 scope bundles **W1, W2, W3, W4, W7, W8, W9, W10** as implementation tasks. **W5 + W6** are ALREADY RESOLVED at commit `613f716` (per pre-flight — verify only, no work). W2 is `select_autoescape(default_for_string=True)` for `_safe_jinja_env()` (verified absent in PR#1's `_safe_jinja_env()`).

```yaml
status: success
confidence: high
total_tasks: 21  # T1.1..T1.5 + T2.1..T2.4 + T3.1..T3.12
pr_split: 2 chained PRs recommended (PR#2a REQ-49; PR#2b REQ-50 + W-fixes)
forecast_loc_production: ~310   # opencode_skill_catalog.py ~120 + cli.py ~150 + W-fix ~40
forecast_loc_test: ~1250         # test_opencode_skill_catalog.py ~300 + test_cli_prompts.py ~400 + 5 BDD feature ~300 + step glue ~150 + W-fix BDD ~100
forecast_loc_grand_total: ~1560
forecast_loc_realistic_x5_7: ~8900  # per drift-hardening precedent multiplier
batches:
  batch_a: 5 tasks   # T1.1..T1.5   — REQ-49 opencode_skill_catalog module + SKILL_CATALOG + 2 BDD scenarios
  batch_b: 4 tasks   # T2.1..T2.4   — flow prompts check + lint CLI + 4 flags + S2 stderr WARN
  batch_c: 12 tasks  # T3.1..T3.12  — flow prompts list/show + W1..W10 fixes + capability spec sync + closeout
review_workload_forecast:
  chained_pr_recommendation: yes
  single_pr_400_line_budget_risk: high
  chained_pr_split: "PR#2a = REQ-49 batches A+B; PR#2b = REQ-50 batch C + W-fixes"
  decision_needed_before_apply: yes
strict_tdd: on
bdd_feature_files: 2 NEW (req49_skill_catalog.feature + req50_cli_prompts.feature)
bdd_scenarios: 5 NEW (REQ-49:2 + REQ-50:3) + 4 EXTENDED (REQ-45 S1/S2 strengthen per W10 + REQ-49 extend step glue)
pr1_carryforwards_resolved:
  W1: lint spec-taxonomy alias map (Batch C T3.3)
  W2: select_autoescape(default_for_string=True) (Batch C T3.4)
  W3: restore prompts/ directory + 4 .j2 files (Batch C T3.5)
  W4: hoist scaffold._env() to prompt_render._env() (Batch C T3.6)
  W5: ALREADY RESOLVED at 613f716 (verify only)
  W6: ALREADY RESOLVED at 613f716 (verify only)
  W7: [tool.flow_engineering.prompts] section (Batch C T3.7)
  W8: pyproject.toml version 0.7.0→0.8.0 (Batch C T3.8)
  W9: uv run ruff check --fix (Batch C T3.9)
  W10: strengthen REQ-45 S1/S2 BDD scenarios (Batch C T3.10)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\tasks-pr2.md
next_recommended: sdd-apply prompt-registry PR#2a batch A (T1.1..T1.5)
```

---

## PR Split (CHAINED PRs RECOMMENDED)

| PR | REQs | Tasks | LOC forecast | LOC realistic (×5.7) |
|----|------|-------|--------------|----------------------|
| **PR#2a** (REQ-49 discovery) | REQ-49 only | T1.1..T1.5 + T2.1..T2.4 (9 tasks across 2 batches) | ~190 prod / ~650 test = ~840 | ~4 800 |
| **PR#2b** (REQ-50 CLI + W-fixes) | REQ-50 + W1..W10 | T3.1..T3.12 (12 tasks in 1 batch) | ~120 prod / ~600 test = ~720 | ~4 100 |
| **Total** | **2 REQs + 8 W-fixes** | **21 tasks** | **~310 prod / ~1 250 test = ~1 560** | **~8 900** |

**Rationale**: Single PR ~1 560 LOC > 400-line budget; realistic ~8 900 LOC. The chained split protects review focus (REQ-49 is the new module + BDD surface; PR#2b is CLI extension + accumulated W-fix cleanup). Each PR has clear start, clear finish, autonomous verification. Per-commit work-unit splits per `work-unit-commits` skill (12-14 commits each ≤400 LOC).

Decision needed before apply: **Yes** (user must choose chain strategy: `stacked-to-main` or `feature-branch-chain`).
Chained PRs recommended: **Yes**
Chain strategy: `stacked-to-main` (per proposal #201 §"PR split" precedent; PR#1 already archived to main)
400-line budget risk: **High** (single PR ~1 560 forecast / ~8 900 realistic)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 21 (T1.1..T1.5, T2.1..T2.4, T3.1..T3.12) |
| Forecast LOC production | ~310 |
| Forecast LOC test (unit + BDD) | ~1 250 |
| Forecast LOC grand total | **~1 560** |
| Forecast LOC realistic (×5.7 TDD multiplier per design §"Structured Metadata") | **~8 900** |
| BDD feature files | 2 NEW (`req49_skill_catalog.feature` + `req50_cli_prompts.feature`) |
| BDD scenarios | 5 NEW (REQ-49:2 + REQ-50:3) + 4 EXTENDED (REQ-45 S1/S2 per W10 + REQ-49 step glue) |
| New source files | 1 (`src/flow_engineering/opencode_skill_catalog.py`) |
| Modified source files | 4 (`src/flow_engineering/cli.py`, `src/flow_engineering/prompt_lint.py`, `src/flow_engineering/prompt_render.py`, `src/flow_engineering/scaffold.py`, `pyproject.toml`, `CHANGELOG.md`, `openspec/specs/prompt-registry/spec.md`) + 1 NEW (`prompts/` directory + 4 `.j2` files) |
| New test files | 1 unit (`test_opencode_skill_catalog.py`) + 1 unit (`test_cli_prompts.py`) + 2 BDD feature + 1 BDD step glue |
| Chained PRs recommended | **Yes** (single PR > 800 LOC threshold per orchestrator brief) |
| Chain strategy | `stacked-to-main` (mirrors `cross-project-federation` chained-PR pattern) |
| 400-line budget risk | **High** (single PR ~1 560 forecast; mitigated by 2-PR split) |
| Decision needed before apply | **Yes** (chain strategy confirmation) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC | opencode_skill_catalog.py ~120 (per design §"Module/File Layout" + spec §"PR#2 production forecast") + cli.py +150 (4 subcommands + 7 flags) + W-fix +40 (W3 restore prompts/ + W7 pyproject section + W8 version bump) | ~310 |
| Test LOC | test_opencode_skill_catalog.py ~300 (catalog schema + 20 entries + check_drift + sidecar I/O + SkillVersionError) + test_cli_prompts.py ~400 (full CLI surface + all 7 flags + exit code matrix) + 5 NEW BDD scenarios ~300 + step glue ~150 + W10 REQ-45 scenario strengthening ~100 | ~1 250 |
| Realistic ×5.7 TDD multiplier | `drift-hardening` precedent (design §"Structured Metadata") — strict-TDD band ×5.7 absorbs BDD step def growth per `decision-code-linking` archive-report #119 S3 | ×5.7 → ~8 900 grand total realistic |
| Per-delegation batch ceiling | `apply-batches-split-into-6-tasks-per-delegation` pattern: ≤3 tasks OR ≤150 LOC prod per delegation | Batch C at 12 tasks is the DELEGATION-EXCEPTION (must split into 2-3 sub-delegations at apply phase) |
| Risk: Batch C W-fix bundling | 12 tasks in 1 batch combines CLI work + 8 W-fixes + spec sync + closeout | **SCOPE RISK** — split into PR#2b sub-delegations (T3.1..T3.6, T3.7..T3.9, T3.10..T3.12) |
| Risk: 400-line review budget | Single PR ~1 560 LOC > 400-line budget | Mitigated by 2-PR chained split (PR#2a ~840 + PR#2b ~720) |
| Risk: W2 + W3 dependency | T3.4 (autoescape) and T3.5 (prompts/ dir restore) both touch `_safe_jinja_env()`/`prompts/` | T3.5 MUST land before T3.4 so the autoescape test has a real `.j2` file to render against |

### Suggested Work Units (per PR)

**PR#2a — REQ-49 discovery** (chained, stacked-to-main; base = `main` after PR#1 archive):

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|----------------|----------|-----|
| **A1** | T1.1 + T1.2 + T1.3 | ~85 | ~250 | NEW `opencode_skill_catalog.py` (SkillEntry + SKILL_CATALOG + check_drift) — atomic foundation |
| **A2** | T1.4 + T1.5 + T2.1 + T2.2 | ~95 | ~300 | init/update sidecar JSON + 2 BDD scenarios + `flow prompts check` CLI + 4 flags |
| **A3** | T2.3 + T2.4 | ~30 | ~100 | `flow prompts lint` subcommand + S2 stderr WARN (mirrors drift-hardening T2.5) |
| **PR#2a total** | 9 tasks | ~210 | ~650 | REQ-49 complete + `flow prompts {lint,check}` partial |

**PR#2b — REQ-50 CLI + W-fixes** (chained, stacked-to-main; base = PR#2a merge commit):

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|----------------|----------|-----|
| **B1** | T3.1 + T3.2 | ~50 | ~150 | `flow prompts list` + `flow prompts show` subcommands (REQ-50 surface complete) |
| **B2** | T3.3 + T3.4 + T3.5 + T3.6 | ~50 | ~200 | W1 lint alias map + W2 autoescape + W3 prompts/ restore + W4 scaffold._env() hoist |
| **B3** | T3.7 + T3.8 + T3.9 | ~10 | ~50 | W7 pyproject section + W8 version bump + W9 ruff --fix |
| **B4** | T3.10 + T3.11 + T3.12 | ~20 | ~250 | W10 BDD strengthen + capability spec sync + CHANGELOG v0.8.0 + closeout |
| **PR#2b total** | 12 tasks | ~130 | ~650 | REQ-50 complete + 8 W-fixes + spec sync |

---

## Dependency Graph

```
Batch A — REQ-49 opencode_skill_catalog.py foundation (5 tasks)
  T1.1 (opencode_skill_catalog.py: SkillEntry + SKILL_CATALOG 20 entries)
    ↓
  T1.2 (_compute_frontmatter_checksum SHA-256 + _parse_frontmatter YAML reader)
    ↓
  T1.3 (check_drift() walks catalog → list[SkillDrift]; 4 drift_kind categories)
    ↓
  T1.4 (init_checksums + update_checksums sidecar JSON I/O + SkillVersionError)
    ↓
  T1.5 (test_opencode_skill_catalog.py RED fixtures + req49_skill_catalog.feature 2 BDD scenarios)

Batch B — REQ-49 `flow prompts check` CLI + observability (4 tasks)
  T2.1 (cli.py: flow prompts Click group + check subcommand wired to check_drift)
    ↓
  T2.2 (4 flags: --update/--no-fail/--init/--skill with exit code matrix per D9)
    ↓
  T2.3 (cli.py: flow prompts lint subcommand + --strict flag + exit codes 0/1/2)
    ↓
  T2.4 (S2 stderr WARN for parse errors + observability counters for check_drift)

Batch C — REQ-50 CLI surface + W-fix carry-forwards (12 tasks)
  T3.1 (cli.py: flow prompts list + --json flag)
    ↓
  T3.2 (cli.py: flow prompts show <id> + --var key=value repeatable)
    ↓
  T3.3 (prompt_lint.py: LINT_CATEGORY_SPEC_ALIASES mapping shim — W1)
    ↓
  T3.4 (prompt_render.py: select_autoescape(default_for_string=True) — W2)
    ↓
  T3.5 (prompts/ directory + 4 .j2 files restored — W3)
    ↓
  T3.6 (prompt_render.py: _env() hoisted from scaffold.py:20 — W4)
    ↓
  T3.7 (pyproject.toml: [tool.flow_engineering.prompts] section — W7)
    ↓
  T3.8 (pyproject.toml: version 0.7.0 → 0.8.0 — W8)
    ↓
  T3.9 (uv run ruff check --fix on changed files — W9)
    ↓
  T3.10 (tests/bdd/req45_prompt_registry.feature: S1/S2 strengthened — W10)
    ↓
  T3.11 (openspec/specs/prompt-registry/spec.md: REQ-49 + REQ-50 sections added)
    ↓
  T3.12 (CHANGELOG v0.8.0 entry + 3 BDD scenarios for REQ-50 + closeout tests)

[Apply batch merge after each sub-batch → final PR merge for each chained PR]
```

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 6 items are explicitly deferred per spec §"Out of Scope" + design §"Out-of-Scope (consolidated)" — apply must NOT introduce code for them:

- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt` snapshots (defer to v1.1)
- **REQ-51** — `prompt_renders.jsonl` append-only sink (defer to v1.1; `FLOW_PROMPT_LOG=1` gate)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (defer to v1.1; lands in `observability.py` per D10)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_REGISTRY` (defer to v1.1)
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` gate in `pyproject.toml` (defer to v1.1)
- **`PromptDef` → `PromptEntry` schema migration** (5 → 6 fields: add `template_id` + `location` + `schema_version`) — deferred to v0.8.x follow-up; PR#2 ships the `SKILL_CATALOG` mirror as the v0.8.x hook
- **`PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict`** shape migration — deferred to v0.8.x follow-up

---

## Patterns Honored

- `apply-batches-split-into-6-tasks-per-delegation` (Engram #112): each apply batch ≤3 tasks / ≤150 LOC prod (Batch C is the DELEGATION-EXCEPTION; split into 4 sub-batches B1..B4 at apply phase)
- `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): design ×5.7 multiplier is the project-specific band
- `work-unit-commits` skill: 12-14 work-unit commits per PR, each ≤400 LOC
- `stacked-to-main-requires-merging-prior-pr-before-next-apply` (#114): PR#2b applies AFTER PR#2a merges to main
- `chained-pr-strategy-stacked-to-main` (per orchestrator brief): PR#2a base = `main` (post-PR#1 archive); PR#2b base = PR#2a merge commit
- `w-fix-carry-forward-bundling` (PR#1 verify-report precedent): W1..W10 carry-forwards integrated as discrete implementation tasks (NOT as orphan follow-up)
- `openspec/specs/` bootstrap pattern (design D12): `openspec/specs/prompt-registry/spec.md` REQ-49/50 sections added in T3.11

---

## Task list (21 tasks, 2 chained PRs, 3 sequential batches)

### Batch A — REQ-49 opencode_skill_catalog.py foundation (5 tasks)

#### T1.1 — Create `src/flow_engineering/opencode_skill_catalog.py` with `SkillEntry` dataclass + `SKILL_CATALOG` 20-entry dict + `SkillDrift` + `SkillVersionError` (REQ-49, D1 + D6)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~120 impl + ~50 tests = ~170
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (NEW — `SkillEntry` frozen dataclass (6 fields: `skill_name`, `surface`, `expected_version`, `expected_path`, `last_verified_checksum`, `owner`) + `SKILL_CATALOG: dict[str, SkillEntry]` with 20 entries (10 `sdd-*` agents × 2 surfaces: `~/.config/opencode/skills/sdd-*/SKILL.md` + `~/.config/opencode/prompts/sdd/*.md`) + `SkillDrift` frozen dataclass + `SkillVersionError(Exception)` + `SIDECAR_PATH` constant; ~120 LOC)
  - `tests/unit/test_opencode_skill_catalog.py` (NEW — +2 RED fixtures: `SkillEntry(skill_name="sdd-apply", surface="skill", expected_version="3.0", expected_path="~/.config/opencode/skills/sdd-apply/SKILL.md", last_verified_checksum="a" * 64, owner="gentleman-programming")` constructs without error; `SKILL_CATALOG` has exactly 20 entries keyed by `<skill_name>/<surface>`)
- **Dependencies:** none (foundation task)
- **Acceptance criteria:**
  - [ ] RED: `test_skill_entry_frozen_dataclass_with_six_fields` fails; `test_skill_catalog_has_exactly_20_entries` fails
  - [ ] GREEN: `SkillEntry` is `frozen=True` dataclass with 6 fields per spec REQ-49; mutation raises `dataclasses.FrozenInstanceError`
  - [ ] GREEN: `SKILL_CATALOG` has exactly 20 entries (10 sdd-* agents × 2 surfaces) keyed by `<skill_name>/<surface>` (e.g., `"sdd-init/skill"`, `"sdd-init/prompt"`); all entries satisfy validation rules per design §"Validation rules" (skill_name lowercase kebab, surface ∈ `{"skill", "prompt"}`, expected_version `MAJOR.MINOR`, last_verified_checksum 64-char hex)
  - [ ] GREEN: `SkillDrift` is `frozen=True` with 7 fields (skill_name, surface, expected_version, on_disk_version, expected_checksum, on_disk_checksum, drift_kind); `drift_kind ∈ {"version_mismatch", "checksum_mismatch", "missing_file", "frontmatter_parse_error"}`
  - [ ] GREEN: `SkillVersionError(Exception)` raised on missing frontmatter or non-dict frontmatter per design §"Algorithm Details / Edge cases"
  - [ ] GREEN: `SIDECAR_PATH = Path.home() / ".flow-engineering" / "prompt_checksums.json"` constant exported
  - [ ] GREEN: All 1125 existing tests pass without modification (foundation is additive)
- **Commits:**
  1. `test(unit): RED fixtures for SkillEntry + SKILL_CATALOG 20-entry shape`
  2. `feat(skill_catalog): NEW module — SkillEntry + SkillDrift + SKILL_CATALOG 20 entries + SkillVersionError (REQ-49)`

#### T1.2 — Implement `_compute_frontmatter_checksum()` SHA-256 helper + `_parse_frontmatter()` YAML reader (REQ-49, D5 + OQ-5)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 impl + ~80 tests = ~110
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (modify — add `_compute_frontmatter_checksum(path: Path) -> str` private helper per design §"Frontmatter checksum / Pseudocode": extract YAML between `---` markers via `FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)`; parse via `yaml.safe_load`; canonicalize via `json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; SHA-256 hexdigest; ~+25 LOC delta)
  - `src/flow_engineering/opencode_skill_catalog.py` (modify — add `_parse_frontmatter(path: Path) -> dict[str, Any]` private helper that returns the parsed YAML dict; raises `SkillVersionError` on missing frontmatter or non-dict; ~+5 LOC delta)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — +3 RED fixtures: `_compute_frontmatter_checksum` on a SKILL.md with frontmatter returns deterministic 64-char hex; same frontmatter content + different body whitespace returns SAME checksum (frontmatter-only per OQ-5); `_parse_frontmatter` on a file with no frontmatter raises `SkillVersionError`)
- **Dependencies:** T1.1 (`SkillVersionError` and `FRONTMATTER_PATTERN` constant must exist)
- **Acceptance criteria:**
  - [ ] RED: `test_compute_frontmatter_checksum_deterministic_hex` fails; `test_compute_frontmatter_checksum_ignores_body_whitespace` fails; `test_parse_frontmatter_raises_on_no_frontmatter` fails
  - [ ] GREEN: `_compute_frontmatter_checksum` returns 64-char lowercase hex SHA-256 digest of canonicalized frontmatter YAML dict
  - [ ] GREEN: Two SKILL.md files with IDENTICAL frontmatter but DIFFERENT body whitespace return the SAME checksum (frontmatter-only per OQ-5)
  - [ ] GREEN: UTF-8 unicode in frontmatter is preserved via `ensure_ascii=False`
  - [ ] GREEN: `_parse_frontmatter` raises `SkillVersionError` with message `"{path}: no YAML frontmatter found"` when `FRONTMATTER_PATTERN` fails to match
  - [ ] GREEN: `_parse_frontmatter` raises `SkillVersionError` with message `"{path}: frontmatter is not a YAML dict"` when YAML parses to non-dict (e.g., scalar)
- **Commits:**
  1. `test(unit): RED fixtures for frontmatter SHA-256 + whitespace-insensitivity + missing-frontmatter`
  2. `feat(skill_catalog): _compute_frontmatter_checksum + _parse_frontmatter helpers (REQ-49, D5)`

#### T1.3 — Implement `check_drift()` walking catalog → `list[SkillDrift]` with 4 drift_kind categories (REQ-49 S1 + S2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~150 tests = ~200
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (modify — add `check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]` per design §"Drift check / Pseudocode": walk catalog, read sidecar (default `{}`), for each entry check `expected_path.exists()` → compute checksum + parse frontmatter → compare against sidecar; return `SkillDrift` for each mismatch; ~+50 LOC delta)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — +5 RED fixtures: empty catalog returns empty list; all checksums match returns empty list (clean state S2); stale sidecar entry with on-disk edit returns 1 `SkillDrift` with `drift_kind="checksum_mismatch"` (S1); missing file returns `SkillDrift` with `drift_kind="missing_file"`; frontmatter parse error returns `SkillDrift` with `drift_kind="frontmatter_parse_error"`)
- **Dependencies:** T1.1, T1.2 (dataclass + helpers must exist)
- **Acceptance criteria:**
  - [ ] RED: All 5 RED fixtures fail
  - [ ] GREEN: `check_drift(None)` walks `SKILL_CATALOG` (20 entries); each entry's on-disk checksum compared against sidecar `{"checksum": "<hex>"}` field
  - [ ] GREEN: `SkillDrift.expected_checksum` reads from sidecar; `expected_version` reads from sidecar `{"version": "..."}` (falls back to `entry.expected_version` when sidecar missing — covers first-ever check before `--init`)
  - [ ] GREEN: Missing file → `SkillDrift(drift_kind="missing_file", on_disk_version="", on_disk_checksum="")`
  - [ ] GREEN: Frontmatter parse error → `SkillDrift(drift_kind="frontmatter_parse_error", on_disk_version="", on_disk_checksum="")`
  - [ ] GREEN: Checksum mismatch → `SkillDrift(drift_kind="checksum_mismatch", on_disk_checksum=<computed>, on_disk_version=<from frontmatter>)`
  - [ ] GREEN: Version mismatch (checksum matches but frontmatter `version:` differs from expected) → `SkillDrift(drift_kind="version_mismatch")`
  - [ ] GREEN: All checksums + versions match → empty `list[SkillDrift]` (clean state)
  - [ ] GREEN: Function completes in <1 second for 20-entry catalog (sanity per spec REQ-49 S2)
- **Commits:**
  1. `test(unit): RED fixtures for check_drift empty/clean/stale/missing/parse-error paths`
  2. `feat(skill_catalog): check_drift walks catalog → SkillDrift list with 4 drift_kind categories (REQ-49 S1+S2)`

#### T1.4 — Implement `init_checksums()` + `update_checksums()` sidecar JSON I/O + private `_read_sidecar`/`_write_sidecar` helpers (REQ-49 D5 + D8 + D9)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~40 impl + ~80 tests = ~120
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (modify — add `_sidecar_path() -> Path` (lazy mkdir parents) + `_read_sidecar() -> dict[str, dict[str, str]]` (returns `{}` when missing) + `_write_sidecar(sidecar: dict) -> None` (atomic write via `tempfile.NamedTemporaryFile` + `os.replace`) + `init_checksums(catalog=None) -> int` (writes fresh checksums to sidecar; returns count) + `update_checksums(catalog=None) -> int` (refreshes sidecar; returns count); ~+40 LOC delta)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — +3 RED fixtures: `init_checksums` creates sidecar with 20 entries + `last_verified_at` ISO 8601 UTC Z-suffixed + `version` field from frontmatter; `update_checksums` overwrites stale entries; `_write_sidecar` atomic write survives mid-write interruption via `tmp` file + `os.replace`)
- **Dependencies:** T1.2 (`_compute_frontmatter_checksum` + `_parse_frontmatter` must exist)
- **Acceptance criteria:**
  - [ ] RED: All 3 RED fixtures fail
  - [ ] GREEN: `_sidecar_path()` returns `Path.home() / ".flow-engineering" / "prompt_checksums.json"`; lazy-creates parents via `mkdir(parents=True, exist_ok=True)`
  - [ ] GREEN: `_read_sidecar()` returns `{}` when file missing (no raise; first-run safety)
  - [ ] GREEN: `_write_sidecar()` writes atomically (write to `tmp` + `os.replace`) — survives mid-write interruption (no half-written JSON)
  - [ ] GREEN: `init_checksums(SKILL_CATALOG)` walks 20 entries; for each: compute frontmatter checksum + read `version` from frontmatter; writes sidecar shape `{key: {"version": str, "checksum": str, "last_verified_at": "<ISO 8601 UTC Z>"}}`; returns count of entries written
  - [ ] GREEN: `update_checksums(SKILL_CATALOG)` refreshes existing sidecar (overwrites stale entries with fresh checksums); returns count of entries refreshed
  - [ ] GREEN: Sidecar JSON is human-readable (`indent=2`) for grep-ability
- **Commits:**
  1. `test(unit): RED fixtures for sidecar JSON init/update/atomic-write`
  2. `feat(skill_catalog): init_checksums + update_checksums + atomic sidecar JSON I/O (REQ-49 D5+D8+D9)`

#### T1.5 — RED fixtures + 2 BDD scenarios for REQ-49 (clean state S2 + drift detected S1) + extend step glue

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 BDD scenarios + ~60 step glue = ~140
- **Files:**
  - `tests/bdd/req49_skill_catalog.feature` (NEW — 2 BDD scenarios verbatim from spec §"REQ-49 BDD Scenarios": `Scenario: check-drift detects when SKILL.md checksums don't match catalog` (S1) + `Scenario: check-drift passes when all SKILL.md checksums match` (S2); ~80 LOC)
  - `tests/bdd/test_prompt_registry_steps.py` (modify — extend step glue with `@given("a SKILL_CATALOG with {n:d} entries")`, `@given("a sidecar prompt_checksums.json recording stale checksums")`, `@when("the user calls check_drift(SKILL_CATALOG)")`, `@then("the result is a list with at least {n:d} SkillDrift entry")`, `@then("the drift entry has skill_name={name} and drift_kind={kind}")`, `@then("the result is an empty list")`; ~+60 LOC delta)
- **Dependencies:** T1.1, T1.3 (catalog + check_drift must exist)
- **Acceptance criteria:**
  - [ ] RED: All 2 BDD scenarios fail (no step glue yet)
  - [ ] GREEN: Scenario S1 verbatim from spec: stale sidecar + on-disk edit → `check_drift()` returns list with ≥1 entry; drift entry has `skill_name="sdd-apply"` and `drift_kind="checksum_mismatch"`; expected_checksum == stale value; on_disk_checksum == current value
  - [ ] GREEN: Scenario S2 verbatim from spec: fresh sidecar with all matches → `check_drift()` returns empty list; function does NOT raise; completes in <1 second
  - [ ] GREEN: Step glue uses business-domain Given/When/Then phrasing (D5 quality gate; mirrors drift-hardening T3.1 quality gate)
  - [ ] GREEN: Step glue shared with future REQ-50 CLI scenarios (`@then("the command exits {n:d}")`, `@then("stdout contains {line}")`) — enables test_cli_prompts.py reuse
- **Commits:**
  1. `test(bdd): req49_skill_catalog.feature 2 scenarios + step glue extension`

---

### Batch B — REQ-49 `flow prompts {check, lint}` CLI + observability (4 tasks)

#### T2.1 — Add `flow prompts` Click group + `check` subcommand wired to `check_drift()` (REQ-49 + REQ-50)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~80 tests = ~130
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `@click.group(name="prompts")` decorator + `flow_prompts` group function; add `flow_prompts_check` subcommand with `check_drift()` integration; print `<skill_name>: <version>: <status>` lines per design §"Data Flow / flow prompts check"; ~+50 LOC delta)
  - `tests/unit/test_cli_prompts.py` (NEW — +3 RED fixtures: `flow prompts` group appears in `flow --help`; `flow prompts check` exits 0 on clean state; `flow prompts check` exits 1 on drift detected)
- **Dependencies:** T1.3 (`check_drift()` must exist)
- **Acceptance criteria:**
  - [ ] RED: All 3 RED fixtures fail
  - [ ] GREEN: `flow --help` lists `prompts` group with description "Inspect and validate prompt registry + SKILL catalog"
  - [ ] GREEN: `flow prompts check` invokes `check_drift(SKILL_CATALOG)`; prints `<skill_name>/<surface>: <expected_version>: <status>` lines (status ∈ `OK` / `DRIFT` / `MISSING` / `PARSE_ERROR`)
  - [ ] GREEN: Clean state (no drifts) → prints footer `N skills verified · 0 drift detected` + exit 0
  - [ ] GREEN: Drift detected → prints drift lines + footer `N skills verified · M drift detected` + exit 1
  - [ ] GREEN: JSON to stderr on errors (no traceback to user per D9)
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts group + check subcommand + exit codes`
  2. `feat(cli): flow prompts Click group + check subcommand wired to check_drift (REQ-49+REQ-50)`

#### T2.2 — Add 4 `--update` / `--no-fail` / `--init` / `--skill <name>` flags with exit code matrix per D9 (REQ-49 D9 + D8)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~25 impl + ~100 tests = ~125
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add 4 Click flags to `flow_prompts_check`: `--update` (calls `update_checksums()` + exits 0 per D9), `--no-fail` (suppresses exit 1 on drift per D5), `--init` (calls `init_checksums()` + exits 0), `--skill <name>` (limits catalog to one entry via catalog subset dict); ~+25 LOC delta)
  - `tests/unit/test_cli_prompts.py` (extend — +4 RED fixtures: `--update` refreshes sidecar + exits 0; `--no-fail` exits 0 even on drift; `--init` bootstraps missing sidecar + exits 0; `--skill sdd-apply` checks only one entry)
- **Dependencies:** T2.1 (CLI group + check subcommand must exist)
- **Acceptance criteria:**
  - [ ] RED: All 4 RED fixtures fail
  - [ ] GREEN: `--update` calls `update_checksums()`; prints `Updated N checksums · sidecar: <path>`; exits 0 unconditionally
  - [ ] GREEN: `--no-fail` suppresses exit 1 on drift (prints drift lines but exits 0) — CI compat per design D5 / D8
  - [ ] GREEN: `--init` calls `init_checksums()`; prints `Initialized N checksums · sidecar: <path>`; exits 0; idempotent (re-init overwrites)
  - [ ] GREEN: `--skill sdd-apply` filters catalog to `{"sdd-apply/skill": entry, "sdd-apply/prompt": entry}` (2 entries, both surfaces)
  - [ ] GREEN: All 4 flags composable: `--update --no-fail` works; `--init --update` is a no-op (init first); `--skill unknown` prints `Unknown skill: unknown` to stderr + exits 3 (usage error per D9)
- **Commits:**
  1. `test(unit): RED fixtures for --update/--no-fail/--init/--skill flags + composition + usage errors`
  2. `feat(cli): flow prompts check 4 flags with D9 exit code matrix (REQ-49 D9)`

#### T2.3 — Add `flow prompts lint` subcommand + `--strict` flag + exit codes 0/1/2 (REQ-47 + REQ-50)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~20 impl + ~50 tests = ~70
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `flow_prompts_lint` subcommand that invokes `lint_prompts(PROMPT_NAMES)` (or `PROMPT_REGISTRY` if migrated in W1 alias) + `--strict` flag; prints `<prompt_id>: <category>: <message>` lines per design §"Error Handling / Lint clean/warnings/errors" + footer `N prompts linted · M warnings · K errors`; ~+20 LOC delta)
  - `tests/unit/test_cli_prompts.py` (extend — +3 RED fixtures: clean registry exits 0; warnings-only exits 1; errors OR `--strict` with warnings exits 2)
- **Dependencies:** T2.1 (CLI group must exist); PR#1 `lint_prompts()` already shipped
- **Acceptance criteria:**
  - [ ] RED: All 3 RED fixtures fail
  - [ ] GREEN: `flow prompts lint` walks `PROMPT_NAMES` (or `PROMPT_REGISTRY` per W1); clean registry → footer `4 prompts linted · 0 warnings · 0 errors` + exit 0
  - [ ] GREEN: Warnings-only (no errors) → exit 1 + footer `4 prompts linted · N warnings · 0 errors`
  - [ ] GREEN: Errors OR `--strict` with warnings → exit 2 + footer `4 prompts linted · N warnings · M errors`
  - [ ] GREEN: Mirrors `flow drift --strict` precedent (drift-hardening D8); `flow prompts lint --strict` on warnings exits 2
  - [ ] GREEN: Uses `LINT_CATEGORY_SPEC_ALIASES` mapping from T3.3 if W1 ships before T2.3; otherwise uses PR#1's impl taxonomy (order-dependent)
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts lint 3 exit codes + --strict`
  2. `feat(cli): flow prompts lint subcommand + --strict flag + exit codes 0/1/2 (REQ-47+REQ-50)`

#### T2.4 — S2 stderr WARN for SKILL.md parse errors + observability counters for `check_drift` invocations (REQ-59 S2 mirror + REQ-22 precedent)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~15 impl + ~30 tests = ~45
- **Files:**
  - `src/flow_engineering/cli.py` (modify — at end of `flow_prompts_check`, compute `parse_error_count = sum(1 for d in drifts if d.drift_kind == "frontmatter_parse_error")`; when `parse_error_count >= _SKILL_PARSE_WARN_THRESHOLD` (default 3, parse from `FLOW_SKILL_PARSE_WARN_THRESHOLD` env var; 0 = always; -1 = never), print `WARN: skill catalog parse errors: {parse_error_count} entries` to `sys.stderr` ONCE per invocation; add `_get_skill_parse_warn_threshold()` helper; ~+15 LOC delta)
  - `src/flow_engineering/observability.py` (modify — add 3 counters to `SNAPSHOT_COUNTER_NAMES` analog: `prompts_check_total`, `prompts_check_drift_total{skill_name,surface}`, `prompts_check_parse_error_total{skill_name,surface}` — total 3 new counter names; ~+3 LOC delta)
  - `tests/unit/test_cli_prompts.py` (extend — +2 RED fixtures: stderr WARN captured via `capsys` when `parse_error_count >= threshold`; `FLOW_SKILL_PARSE_WARN_THRESHOLD=0` emits WARN on every invocation with parse errors)
- **Dependencies:** T2.1, T2.2 (`flow_prompts_check` must exist)
- **Acceptance criteria:**
  - [ ] RED: Both RED fixtures fail
  - [ ] GREEN: S2 stderr WARN emitted ONCE per invocation when `parse_error_count >= threshold` (NOT per drifted entry)
  - [ ] GREEN: `FLOW_SKILL_PARSE_WARN_THRESHOLD=0` → WARN every invocation with `parse_error_count > 0`
  - [ ] GREEN: `FLOW_SKILL_PARSE_WARN_THRESHOLD=-1` → WARN never
  - [ ] GREEN: `FLOW_SKILL_PARSE_WARN_THRESHOLD=garbage` → falls back to default 3 (parse error tolerance; mirrors drift-hardening T2.5)
  - [ ] GREEN: 3 new counter names added to observability catalog: `prompts_check_total`, `prompts_check_drift_total{skill_name,surface}`, `prompts_check_parse_error_total{skill_name,surface}` (REQ-22 prefix convention; mirror `drift_*_total` from drift-hardening)
  - [ ] GREEN: Counters are EMITTED on each `flow_prompts_check` invocation via `record_counter()` helper (not yet incrementing — that wiring lands in v1.1 with REQ-51+REQ-52)
- **Commits:**
  1. `test(unit): RED fixtures for S2 stderr WARN + env var threshold + 3 counter names`
  2. `feat(cli): flow prompts check S2 stderr WARN + observability counter catalog entries (REQ-59 S2 mirror)`

---

### Batch C — REQ-50 CLI surface + W-fix carry-forwards (12 tasks)

#### T3.1 — Add `flow prompts list` subcommand with `--json` flag (REQ-50 S1)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 impl + ~60 tests = ~90
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `flow_prompts_list` subcommand; prints table `{prompt_id, version, owner, location}` grouped by owner per spec §"REQ-50 Scenario S1"; add `--json` flag that emits flat dict mirroring `flow metrics --json` precedent per REQ-8; ~+30 LOC delta)
  - `tests/unit/test_cli_prompts.py` (extend — +3 RED fixtures: `flow prompts list` exits 0 + stdout contains all 4 prompt_ids + footer `4 prompt entries`; `--json` exits 0 + `json.loads(stdout)` returns dict with 4 keys; default text output is grouped by owner)
- **Dependencies:** T2.1 (CLI group must exist)
- **Acceptance criteria:**
  - [ ] RED: All 3 RED fixtures fail
  - [ ] GREEN: `flow prompts list` prints human-readable table with header `prompt_id / version / owner / location`; rows for all 4 `PROMPT_NAMES` entries (`strict_tdd`, `auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`); footer `4 prompt entries · 0 lint warnings · registry schema_version=1.0`; exit 0
  - [ ] GREEN: `flow prompts list --json` emits `json.dumps({"prompts": [{"name": ..., "version": ..., "owner": ..., "location": ...}, ...], "count": 4, "registry_schema_version": "1.0"}, indent=2)` to stdout; exit 0
  - [ ] GREEN: Default text output groups rows by `owner` column (flow/observability before flow/binding) per spec S1 Gherkin
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts list + --json + owner grouping`
  2. `feat(cli): flow prompts list + --json flag with owner grouping (REQ-50 S1)`

#### T3.2 — Add `flow prompts show <id>` subcommand with `--var key=value` repeatable + sentinel substitution (REQ-50 S2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~40 impl + ~80 tests = ~120
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `flow_prompts_show` subcommand with `<prompt_id>` argument + `--var` repeatable Click flag; invokes `render_prompt_safe()` with sentinel substitution per OQ-4; prints metadata header + rendered template + footer; exits 5 on unknown prompt_id per D9; ~+40 LOC delta)
  - `tests/unit/test_cli_prompts.py` (extend — +4 RED fixtures: `flow prompts show strict_tdd --var test_command=pytest` exits 0 + stdout contains `pytest` substituted + footer `autoescape=on`; `flow prompts show strict_tdd` (no --var) prints `<test_command>` sentinel for missing variable; `flow prompts show unknown_prompt` exits 5 + stderr `{"error": "unknown prompt id", "prompt_id": "unknown_prompt"}`; `--var` repeatable accepts multiple `key=value` pairs)
- **Dependencies:** T2.1, T3.1 (CLI group + list subcommand must exist); PR#1 `render_prompt_safe()` already shipped at `613f716`
- **Acceptance criteria:**
  - [ ] RED: All 4 RED fixtures fail
  - [ ] GREEN: `flow prompts show strict_tdd --var test_command=pytest` prints header `prompt_id: strict_tdd / version: 1.0.0 / owner: flow/observability / variables: {test_command: pytest}` + rendered template `STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.` + footer `(rendered via Jinja2 · autoescape=on · source: prompts/strict_tdd.j2)`; exit 0
  - [ ] GREEN: Missing `--var` for a prompt with declared variables prints `<test_command>` sentinel in the rendered output (per OQ-4 + D4)
  - [ ] GREEN: Unknown prompt_id → `{"error": "unknown prompt id", "prompt_id": "<id>", "hint": "run 'flow prompts list' to see available"}` to stderr + exit 5 (per D9)
  - [ ] GREEN: `--var` is REPEATABLE: `--var test_command=pytest --var extra=foo` parses both pairs; repeated key overrides previous (last-write-wins)
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts show + --var repeatable + sentinel + unknown-id exit 5`
  2. `feat(cli): flow prompts show <id> + --var repeatable + sentinel + exit 5 on unknown (REQ-50 S2)`

#### T3.3 — W1 lint spec-taxonomy alias map `LINT_CATEGORY_SPEC_ALIASES` in `prompt_registry.py` (W1 verify-report PR#1)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~10 impl + ~40 tests = ~50
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (modify — add `LINT_CATEGORY_SPEC_ALIASES: dict[str, str]` constant mapping impl category names → spec taxonomy names: `{"missing_placeholder": "undefined_var", "unused_variable": "<no-op: implement later>", "template_parse_error": "jinja_syntax", "autoescape_disabled": "<no-op: never emitted by impl>", "missing_variable": "<no-op: subset of missing_placeholder>"}`; add `get_spec_category(impl_category: str) -> str | None` helper; ~+10 LOC delta)
  - `tests/unit/test_prompt_registry.py` (extend — +2 RED fixtures: `LINT_CATEGORY_SPEC_ALIASES` maps `missing_placeholder` → `undefined_var`; `get_spec_category("undefined_var")` returns `"missing_placeholder"`; round-trip works)
- **Dependencies:** PR#1 `lint_prompts()` + impl taxonomy already shipped
- **Acceptance criteria:**
  - [ ] RED: Both RED fixtures fail
  - [ ] GREEN: `LINT_CATEGORY_SPEC_ALIASES` is a module-level constant with 5 keys (the spec taxonomy names) → 5 values (impl names where applicable, or `None` for unimplemented mappings)
  - [ ] GREEN: `get_spec_category(impl_name)` returns the spec-taxonomy name if a mapping exists; returns `None` otherwise
  - [ ] GREEN: W1 verify-report carry-forward resolved — downstream consumers querying for spec-mandated `missing_placeholder` / `template_parse_error` / etc. now resolve to impl equivalents (or get `None` for unimplemented)
- **Commits:**
  1. `test(unit): RED fixtures for LINT_CATEGORY_SPEC_ALIASES mapping + get_spec_category helper`
  2. `feat(prompt_registry): LINT_CATEGORY_SPEC_ALIASES mapping shim for spec taxonomy (W1 resolve)`

#### T3.4 — W2 `select_autoescape(default_for_string=True)` in `_safe_jinja_env()` (W2 verify-report PR#1 + OQ-2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~5 impl + ~30 tests = ~35
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (modify — change `_safe_jinja_env()`: `autoescape=False` → `autoescape=select_autoescape(enabled_extensions=(), default_for_string=True)` per design OQ-2; ~+3/-2 LOC delta)
  - `tests/unit/test_prompt_registry.py` (extend — +2 RED fixtures: `_safe_jinja_env().autoescape` is truthy (NOT `False`); `render_prompt` on a test prompt with `{{ var }}` containing `<script>` returns `&lt;script&gt;` (autoescape blocks HTML injection))
- **Dependencies:** T3.5 (`prompts/` directory + `.j2` files must exist so autoescape test has real templates to render against)
- **Acceptance criteria:**
  - [ ] RED: Both RED fixtures fail
  - [ ] GREEN: `_safe_jinja_env().autoescape` is `select_autoescape(enabled_extensions=(), default_for_string=True)` per OQ-2 (truthy)
  - [ ] GREEN: `render_prompt("strict_tdd", test_command="<script>")` returns `STRICT TDD MODE IS ACTIVE. Test runner: &lt;script&gt;. ...` (HTML-escaped)
  - [ ] GREEN: All existing 1125 tests still pass (no regression on existing 4 entries which use Python `.format()` syntax — autoescape only affects Jinja2 `{{ var }}` substitution)
- **Commits:**
  1. `test(unit): RED fixtures for select_autoescape(default_for_string=True) + HTML injection block`
  2. `feat(prompt_registry): select_autoescape(default_for_string=True) on _safe_jinja_env (W2 + OQ-2)`

#### T3.5 — W3 restore `prompts/` directory + 4 `.j2` files at repo root (W3 verify-report PR#1 + D1 + D2)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~15 impl (4 `.j2` files + 1 test fixture) + ~30 tests = ~45
- **Files:**
  - `prompts/strict_tdd.j2` (NEW — `STRICT TDD MODE IS ACTIVE. Test runner: {{ test_command }}. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.\n`; ~4 LOC)
  - `prompts/auto_suggest_header.j2` (NEW — `Auto-suggested code bindings:\n`; ~2 LOC)
  - `prompts/auto_suggest_footer.j2` (NEW — `Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)\n`; ~3 LOC)
  - `prompts/auto_suggest_empty.j2` (NEW — `No auto-suggested bindings available.\n`; ~1 LOC)
  - `tests/unit/test_prompt_registry.py` (extend — +2 RED fixtures: `prompts/` directory exists at repo root + contains all 4 `.j2` files; `get_prompts_dir()` returns the `prompts/` path)
  - `src/flow_engineering/prompt_registry.py` (modify — add `get_prompts_dir() -> Path` helper per design §"prompt_registry.py / Public API"; default `<repo>/prompts/`; configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (landed in T3.7); ~+10 LOC delta)
- **Dependencies:** none (foundation task; T3.4 depends on this)
- **Acceptance criteria:**
  - [ ] RED: Both RED fixtures fail
  - [ ] GREEN: `<repo>/prompts/` directory exists with 4 `.j2` files (one per PROMPT_NAMES entry)
  - [ ] GREEN: `get_prompts_dir()` returns the `prompts/` path resolved relative to the repo root (via `Path(__file__).parent.parent.parent` chain or pyproject lookup)
  - [ ] GREEN: `get_prompts_dir()` reads `[tool.flow_engineering.prompts] directory` from pyproject when T3.7 lands; falls back to `<repo>/prompts/` default
  - [ ] GREEN: W3 verify-report carry-forward resolved — `prompts/` directory exists + `.j2` files restored per D1 + D2
- **Commits:**
  1. `test(unit): RED fixtures for prompts/ directory + 4 .j2 files + get_prompts_dir()`
  2. `feat(prompts): NEW directory at repo root with 4 .j2 files (W3 + D1+D2)`
  3. `feat(prompt_registry): get_prompts_dir() helper with pyproject override (W3 dependency)`

#### T3.6 — W4 hoist `scaffold._env()` to shared `prompt_render._env()` (W4 verify-report PR#1 + D3)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~25 impl + ~40 tests = ~65
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (modify — add `_env() -> Environment` factory per design §"prompt_render.py / Public API": `select_autoescape(enabled_extensions=(), default_for_string=True)`, `keep_trailing_newline=True`, `FileSystemLoader(get_prompts_dir())`; `@functools.lru_cache(maxsize=1)`; ~+15 LOC delta)
  - `src/flow_engineering/scaffold.py` (modify — replace local `_env()` at lines 20-25 with `from flow_engineering.prompt_registry import _env as _scaffold_env` thin re-export; preserve existing callers (`_env()` at lines 42, 77) via the re-export; ~+5/-10 LOC delta)
  - `tests/unit/test_scaffold.py` (extend — +2 RED fixtures: `scaffold._env() is prompt_registry._env()` (identity check — same cached factory); `scaffold._env().autoescape` is truthy (autoescape ON; per W2+T3.4))
  - `tests/unit/test_prompt_registry.py` (extend — +1 RED fixture: `prompt_registry._env()` is `@lru_cache`d — repeated calls return identity)
- **Dependencies:** T3.4 (autoescape must be set), T3.5 (`prompts/` directory must exist so `FileSystemLoader` resolves)
- **Acceptance criteria:**
  - [ ] RED: All 3 RED fixtures fail
  - [ ] GREEN: `prompt_registry._env()` returns a single `jinja2.Environment` with `select_autoescape(default_for_string=True)` + `keep_trailing_newline=True` + `FileSystemLoader(get_prompts_dir())`; `@lru_cache`d so repeated calls return identity
  - [ ] GREEN: `scaffold._env() is prompt_registry._env()` (identity check — proves the hoist)
  - [ ] GREEN: No import cycle: `scaffold.py` imports from `prompt_registry.py` (NOT the reverse)
  - [ ] GREEN: Existing 16 `tests/unit/test_scaffold.py` tests pass without modification
  - [ ] GREEN: W4 verify-report carry-forward resolved — shared `Environment` invariant enforced
- **Commits:**
  1. `test(unit): RED fixtures for _env() hoist + identity check + lru_cache`
  2. `feat(prompt_registry): _env() factory hoisted with lru_cache + select_autoescape (D3)`
  3. `refactor(scaffold): replace local _env() with re-export from prompt_registry (W4)`

#### T3.7 — W7 `[tool.flow_engineering.prompts] directory = "prompts"` in `pyproject.toml` (W7 verify-report PR#1 + D1)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~5 impl + ~15 tests = ~20
- **Files:**
  - `pyproject.toml` (modify — add `[tool.flow_engineering.prompts]` section with `directory = "prompts"` per design D1 + spec §"PR#2 files to touch"; ~+5 LOC delta)
  - `tests/unit/test_pyproject_prompts.py` (NEW — +1 RED fixture: `pyproject.toml` has `[tool.flow_engineering.prompts]` section with `directory = "prompts"`; ~+15 LOC)
- **Dependencies:** T3.5 (`get_prompts_dir()` must read pyproject override)
- **Acceptance criteria:**
  - [ ] RED: RED fixture fails
  - [ ] GREEN: `pyproject.toml` has `[tool.flow_engineering.prompts]` section with `directory = "prompts"` (relative to repo root)
  - [ ] GREEN: `get_prompts_dir()` reads the pyproject override via `tomllib.load(pyproject_path)` (Python 3.11+ stdlib)
  - [ ] GREEN: W7 verify-report carry-forward resolved
- **Commits:**
  1. `test(unit): RED fixture for pyproject [tool.flow_engineering.prompts] section presence`
  2. `feat(pyproject): [tool.flow_engineering.prompts] directory = "prompts" section (W7 + D1)`

#### T3.8 — W8 bump `pyproject.toml` version to `0.8.0` (W8 verify-report PR#1)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~1 impl + ~15 tests = ~16
- **Files:**
  - `pyproject.toml` (modify — `version = "0.7.0"` → `version = "0.8.0"` per verify-report W8 + CHANGELOG `## [0.8.0] - 2026-06-27` alignment; ~+1/-1 LOC delta)
  - `tests/unit/test_pyproject_version.py` (NEW — +1 RED fixture: `pyproject.toml` `version` field equals `"0.8.0"`; `flow --version` prints `0.8.0`; ~+15 LOC)
- **Dependencies:** none (independent of T3.7)
- **Acceptance criteria:**
  - [ ] RED: RED fixture fails
  - [ ] GREEN: `pyproject.toml` `version = "0.8.0"` matches CHANGELOG `## [0.8.0] - 2026-06-27` entry
  - [ ] GREEN: `flow --version` prints `flow 0.8.0`
  - [ ] GREEN: W8 verify-report carry-forward resolved
- **Commits:**
  1. `test(unit): RED fixture for pyproject version == 0.8.0`
  2. `chore(pyproject): version 0.7.0 → 0.8.0 to match CHANGELOG (W8)`

#### T3.9 — W9 `uv run ruff check --fix` on changed files (W9 verify-report PR#1)

- **Type:** cleanup
- **TDD phase:** REFACTOR (no new tests; verifies existing 1125 tests still pass after auto-fix)
- **LOC:** ~0 impl (auto-fix) + ~20 verification tests = ~20
- **Files:**
  - `src/flow_engineering/prompt_registry.py`, `src/flow_engineering/cli.py`, `src/flow_engineering/opencode_skill_catalog.py`, `tests/unit/test_opencode_skill_catalog.py`, `tests/unit/test_cli_prompts.py`, `tests/bdd/test_prompt_registry_steps.py` (modified — `uv run ruff check --fix` auto-applies 3 of 5 fixes from verify-report W9: `I001` import sort, `SIM105` contextlib.suppress, `W292` trailing newline; the 2 manual fixes `UP042` StrEnum migration + 1 trailing newline are 1-line edits)
  - `tests/unit/test_ruff_clean.py` (NEW — +1 verification fixture: `uv run ruff check src/flow_engineering/opencode_skill_catalog.py src/flow_engineering/cli.py tests/unit/test_opencode_skill_catalog.py tests/unit/test_cli_prompts.py` exits 0; ~+20 LOC)
- **Dependencies:** all W-fix tasks T3.1..T3.8 must be GREEN (so auto-fix has stable input)
- **Acceptance criteria:**
  - [ ] GREEN: `uv run ruff check --fix` on changed files applies 3 auto-fixable lint fixes (I001, SIM105, W292) — 0 remaining errors on changed files
  - [ ] GREEN: 2 manual fixes (UP042 StrEnum migration + 1 trailing newline) applied as 1-line edits
  - [ ] GREEN: All 1125 existing tests + new PR#2 tests pass after auto-fix (no regression from ruff changes)
  - [ ] GREEN: W9 verify-report carry-forward resolved
- **Commits:**
  1. `chore(lint): uv run ruff check --fix on changed files (W9)`

#### T3.10 — W10 strengthen BDD scenarios for REQ-45 S1/S2 to match spec Gherkin shape (W10 verify-report PR#1)

- **Type:** bdd (strengthening existing PR#1 scenarios)
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~30 BDD scenarios (modify) + ~30 step glue (modify) = ~60
- **Files:**
  - `tests/bdd/req45_prompt_registry.feature` (modify — strengthen S1 from `len(list_prompts()) >= 4` to spec verbatim: `And "strict_tdd" maps to a PromptEntry with owner="flow/observability" and variables=("test_command",)` + per-entry owner/variables assertions per spec §"REQ-45 Scenario S1"; strengthen S2 from `get_prompt("unknown") raises KeyError` to `PROMPT_REGISTRY["nonexistent_prompt"]` direct dict access per spec §"REQ-45 Scenario S2"; ~+30 LOC delta)
  - `tests/bdd/test_prompt_registry_steps.py` (modify — extend step glue with `@then('"{name}" maps to a PromptEntry with owner="{owner}" and variables=({vars})')` + step that reads `PROMPT_REGISTRY[name]` directly; ~+30 LOC delta)
- **Dependencies:** PR#1 `PROMPT_NAMES` + `get_prompt_template` already shipped at `613f716`
- **Acceptance criteria:**
  - [ ] RED: Strengthened S1 fails (current weaker assertion passes; new assertion fails until per-entry shape asserted)
  - [ ] GREEN: S1 verbatim from spec §"REQ-45 Scenario S1" — 5 `And` lines asserting per-entry owner + variables
  - [ ] GREEN: S2 verbatim from spec §"REQ-45 Scenario S2" — direct `PROMPT_REGISTRY["nonexistent_prompt"]` access raises `KeyError` with name in message
  - [ ] GREEN: Step glue uses business-domain Given/When/Then phrasing (D5 quality gate)
  - [ ] GREEN: W10 verify-report carry-forward resolved — BDD scenarios match spec Gherkin shape
- **Commits:**
  1. `test(bdd): strengthen req45 S1/S2 to match spec Gherkin shape (W10)`

#### T3.11 — Capability spec sync: `openspec/specs/prompt-registry/spec.md` REQ-49 + REQ-50 sections (D12 + W1+W4+W7+W8 resolution notes)

- **Type:** docs
- **TDD phase:** N/A (docs-only)
- **LOC:** ~150 spec
- **Files:**
  - `openspec/specs/prompt-registry/spec.md` (modify — extend with REQ-49 section (catalog schema + check_drift contract + 2 BDD scenarios) + REQ-50 section (4 subcommands + 7 flags + 3 BDD scenarios) + 8 W-fix resolution notes (W1 LINT_CATEGORY_SPEC_ALIASES, W2 autoescape, W3 prompts/ restored, W4 scaffold._env() hoisted, W5/W6 already resolved at 613f716, W7 pyproject section, W8 version 0.8.0, W9 ruff clean, W10 BDD strengthened); ~+150 LOC delta)
- **Dependencies:** T3.1..T3.10 (all W-fixes + REQ-49/50 ship before spec reflects them)
- **Acceptance criteria:**
  - [ ] GREEN: `openspec/specs/prompt-registry/spec.md` has REQ-49 section + REQ-50 section + 8 W-fix resolution notes
  - [ ] GREEN: REQ-49 section documents `SkillEntry` 6-field schema + 20 catalog entries + `check_drift` 4 drift_kind categories + sidecar JSON shape
  - [ ] GREEN: REQ-50 section documents `flow prompts {list,show,lint,check}` 4 subcommands + 7 flags + 3 BDD scenarios + exit code matrix per D9
  - [ ] GREEN: Spec is INFORMATIONAL (does not import `opencode_skill_catalog.py` or `cli.py`); reflects runtime contract only
- **Commits:**
  1. `docs(spec): extend prompt-registry spec with REQ-49 + REQ-50 + 8 W-fix resolution notes (D12)`

#### T3.12 — Closeout: 3 BDD scenarios for REQ-50 (S1 list + S2 show + S3 lint) + CHANGELOG v0.8.0 entry + closeout unit tests (W8 + W10 closeout + REQ-50 BDD)

- **Type:** bdd + docs + integration
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 BDD scenarios + ~30 step glue + ~50 CHANGELOG + ~30 closeout tests = ~190
- **Files:**
  - `tests/bdd/req50_cli_prompts.feature` (NEW — 3 BDD scenarios verbatim from spec §"REQ-50 BDD Scenarios": S1 `flow prompts list` shows all registered prompts grouped by domain; S2 `flow prompts show <name>` renders the prompt with kwargs; S3 `flow prompts lint` exits non-zero when catalog has validation errors; ~80 LOC)
  - `tests/bdd/test_prompt_registry_steps.py` (modify — extend step glue for REQ-50 S1/S2/S3: `@when('the user runs "{command}"')`, `@then("stdout contains a row for {name} with version={version} and owner={owner}")`, `@then("stdout contains the rendered string {string}")`, `@then("the command exits {n:d}")`; ~+30 LOC delta)
  - `CHANGELOG.md` (modify — add `## [0.8.0] - 2026-06-27` entry (already exists; verify + extend with REQ-49/50 sections) listing all 5 NEW capabilities (REQ-49 SKILL_CATALOG, REQ-50 CLI surface, 8 W-fix resolutions) with one-line summaries; ~+50 LOC delta)
  - `tests/unit/test_changelog_v080.py` (NEW — +2 verification fixtures: CHANGELOG v0.8.0 entry lists REQ-49 + REQ-50 + W1..W10 resolutions; pyproject version == "0.8.0"; ~+30 LOC)
- **Dependencies:** T3.1, T3.2, T3.3 (all CLI subcommands + W-fixes must be GREEN); T3.10 (W10 BDD strengthening)
- **Acceptance criteria:**
  - [ ] RED: All 3 BDD scenarios fail (no step glue yet for REQ-50)
  - [ ] GREEN: Scenario S1 verbatim from spec §"REQ-50 Scenario S1" — `flow prompts list` prints all 4 prompt_ids grouped by owner + footer `4 prompt entries`; exit 0
  - [ ] GREEN: Scenario S2 verbatim from spec §"REQ-50 Scenario S2" — `flow prompts show strict_tdd --var test_command=pytest` prints metadata header + rendered string + autoescape footer; exit 0
  - [ ] GREEN: Scenario S3 verbatim from spec §"REQ-50 Scenario S3" — broken registry with `missing_placeholder` → stdout `broken: missing_placeholder: undefined variable 'test_comand'`; exit code 2 (error category)
  - [ ] GREEN: CHANGELOG v0.8.0 entry lists REQ-49 (SKILL_CATALOG + check_drift + sidecar JSON) + REQ-50 (flow prompts CLI + 7 flags) + 8 W-fix resolutions (W1..W10)
  - [ ] GREEN: All 1125 existing tests + 5 NEW BDD scenarios + 4 EXTENDED BDD scenarios + ~30 NEW unit tests pass
  - [ ] GREEN: `ruff check` clean on all changed files (post-T3.9)
  - [ ] GREEN: Strict TDD evidence: every public helper (`SKILL_CATALOG`, `check_drift`, `update_checksums`, `init_checksums`, `flow prompts {list, show, lint, check}`) has RED → GREEN → REFACTOR history in commit log
- **Commits:**
  1. `test(bdd): req50_cli_prompts.feature 3 scenarios + step glue extension`
  2. `docs(changelog): v0.8.0 entry with REQ-49 + REQ-50 + 8 W-fix resolutions`
  3. `test(unit): CHANGELOG v0.8.0 structure + REQ-49/50 resolution verification tests`

---

## Open follow-ups for sdd-archive (after PR#2b merge)

- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt` snapshots (v1.1)
- **REQ-51** — `prompt_renders.jsonl` append-only sink at `~/.flow-engineering/prompt_renders.jsonl` with `FLOW_PROMPT_LOG=1` gate (v1.1)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters wired into `render_prompt()` via `observability.increment()` (v1.1; bundles with REQ-51)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_NAMES` at build time (v1.1)
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`; `flow apply` / `verify` / `archive` assert on startup that on-disk SKILL.md `version` is >= minimum; raises `SkillVersionError` (v1.1)
- **`PromptDef` → `PromptEntry` schema migration** — 5 → 6 fields (add `template_id` + `location` + `schema_version`); v0.8.x follow-up
- **`PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict`** shape migration — v0.8.x follow-up; this PR ships the `SKILL_CATALOG` mirror as the v0.8.x hook

---

## Coordination notes

- **W5/W6 RESOLVED at `613f716`** — pre-flight `pytest --collect-only` shows 1125 tests collecting clean; PR#1 closeout at `51ac227` includes `PromptRenderError`/`PromptNotFoundError` exception classes (W6) and `.format()` fallback path that renders the 4 migrated entries (W5). No work needed in PR#2; verify in sdd-verify Step 6 only.
- **Chain strategy**: `stacked-to-main` per orchestrator brief + proposal #201 §"PR split" precedent. PR#2a base = `main` (post-PR#1 archive at `51ac227`); PR#2b base = PR#2a merge commit.
- **Decision needed before apply**: orchestrator must confirm chain strategy + user approval for W1 lint alias map (deferred vs PR#2 resolution trade-off).
- **Batch C delegation**: 12 tasks in Batch C is the DELEGATION-EXCEPTION; split into 4 sub-batches B1..B4 at apply phase per `apply-batches-split-into-6-tasks-per-delegation` pattern.
- **W2 + W3 dependency**: T3.4 (autoescape) and T3.5 (`prompts/` restore) both touch `_safe_jinja_env()`/`prompts/`. T3.5 MUST land before T3.4 so the autoescape test has a real `.j2` file to render against.
- **PR#2b work-unit commit splits**: per `work-unit-commits` skill, 12-14 work-unit commits each ≤400 LOC across B1..B4 sub-batches.
- **Cross-impact**: REQ-1..8 (decision-code-linking), REQ-9..16 (decision-reality-drift), REQ-17..22 (vector-semantic-search), REQ-23..27 (cross-project-federation), REQ-28..34 (graph-snapshots), REQ-35..39 (observability), REQ-55..59 (drift-hardening) all ship unchanged. PR#2 ships REQ-49 + REQ-50 + 8 W-fixes; all additive.