# Archive Report — prompt-registry PR#1

## Status

**ARCHIVED** (2026-06-27)

SDD cycle complete: explore → propose → design → spec → tasks → apply (single PR via 3 batches A + B + C across 14 work-unit commits + 1 docs commit) → verify (PASS WITH WARNINGS, 0C + 10W + 6S) → 1 W-fix commit (`613f716` resolves REQ-46 W5/W6: `.format()` fallback + `PromptRenderError`) → archive.

**Verdict at archive**: **PARTIAL — archive-ready**. REQ-45 + REQ-46 + REQ-47 ship with 0 CRITICAL findings, 10 WARNING findings documented in `verify-report-pr1.md`, 6 SUGGESTION findings skipped (non-blocking). REQ-46 W5/W6 RESOLVED at commit `613f716` (the `.format()` fallback lets the 4 migrated `PROMPT_NAMES` entries render via the public `render_prompt(name, **kwargs)` API; `PromptRenderError` / `PromptNotFoundError` exception classes added). REQ-45 S1/S2 + REQ-47 W1 remain PARTIAL — schema-shape, BDD-coverage, and lint-taxonomy divergences documented in `verify-report-pr1.md` §"Coherence" + "Carry-forwards" and carry-forwarded to PR#2 / v0.8.x follow-up. REQ-49 / REQ-50 / REQ-48 / REQ-51..54 explicitly NOT shipped in PR#1 (deferred to PR#2 or v1.1).

## PR#1 Scope vs Out-of-Scope (precise)

| REQ | Description | PR#1 Status |
|-----|-------------|-------------|
| **REQ-45** | `PROMPT_NAMES` catalog + 4 migrated entries | ⚠️ PARTIAL — tuple/5-field shipped; dict/6-field deferred |
| **REQ-46** | `render_prompt` + helpers | ✅ RESOLVED post-`613f716` |
| **REQ-47** | `lint_prompts()` validator | ⚠️ PARTIAL — impl taxonomy ≠ spec taxonomy |
| **REQ-48** | golden regression tests | 🔲 NOT SHIPPED — PR#2 deferred |
| **REQ-49** | `SKILL_CATALOG` mirror + drift | 🔲 NOT SHIPPED — PR#2 deferred |
| **REQ-50** | `flow prompts` CLI subcommand | 🔲 NOT SHIPPED — PR#2 deferred |
| **REQ-51..54** | counters + sidecar + docs | 🔲 NOT SHIPPED — v1.1 deferred |

## Files Created / Moved

### Synced to capability spec baseline (source of truth)
- `openspec/specs/prompt-registry/spec.md` — MODIFY (added `## PR#1 archive status` header + `## PR#1 Scope` table)

### Moved to archive (git-detected rename, 100% similarity — `git mv`)
- `openspec/changes/prompt-registry/proposal.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/proposal.md`
- `openspec/changes/prompt-registry/spec.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/spec.md` (added `## PR#1 Scope` heading)
- `openspec/changes/prompt-registry/design.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/design.md`
- `openspec/changes/prompt-registry/tasks.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/tasks.md`
- `openspec/changes/prompt-registry/explore.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/explore.md`
- `openspec/changes/prompt-registry/verify-report-pr1.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/verify-report-pr1.md`
- `openspec/changes/prompt-registry/apply-progress/pr1-batch-a.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/apply-progress/pr1-batch-a.md`
- `openspec/changes/prompt-registry/apply-progress/pr1-batch-b.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/apply-progress/pr1-batch-b.md`
- `openspec/changes/prompt-registry/apply-progress/pr1-batch-c.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/apply-progress/pr1-batch-c.md`
- `openspec/changes/prompt-registry/apply-progress/pr1-merged.md` → `openspec/changes/archive/2026-06-27-prompt-registry-pr1/apply-progress/pr1-merged.md`

### Created (this archive)
- `openspec/changes/archive/2026-06-27-prompt-registry-pr1/archive-report.md` (this file)
- `openspec/changes/prompt-registry/README.md` — PR#2 active scope skeleton (per "next PR continues" precedent at `openspec/changes/archive/2026-06-27-observability-pr2/`)

### Cleanup
- Empty `openspec/changes/prompt-registry/apply-progress/` directory removed
- `openspec/changes/prompt-registry/` retained with only `README.md` (PR#2 skeleton)

## PRs merged

- **PR#1**: feat(prompt-registry): `PromptRegistry` catalog + `render_prompt` + `lint_prompts` foundation (REQ-45 + REQ-46 + REQ-47) — 14 commits total on `main` since change #6 PR#2 archive commit `7dee089`:
  - 6 batch A work-unit commits (`39cbb1d`, `01f5576`, `bc8359f`, `ccd05bb`, `fbe9a83`, `6763a02`)
  - 4 batch B work-unit commits (`d9173c8`, `0936875`, `8bd8358`, `e054b09`)
  - 4 batch C work-unit commits (`cc75dd5`, `dcdb088`, `01556bf`, `51ac227`)
  - 1 W-fix commit (`613f716` — REQ-46 W5/W6 GREEN: `.format()` fallback + `PromptRenderError`)
- Final HEAD pre-archive: `4bbcc21`
- Strict TDD enabled throughout (×6 LOC multiplier realized per `decision-code-linking` archive-report #119 S3; cumulative ~1 400 LOC production + ~1 200 LOC tests, well within the per-batch ≤400 LOC commit budget)

## Test summary

- 953 (post #6 PR#2) → **1 120 passing + 5 failing = 1 125** (post #7 PR#1 + W-fix) — delta +172 tests
- **5 failing** tests are NOT in prompt-registry scope — they live in `tests/unit/test_observability_aggregate.py::TestWindowIntegrationOnExport` and belong to the parallel **drift-hardening** cluster (REQ-56 BREAKING migration, REQ-59 snapshot field reconciliation) which is being archived separately. The drift-hardening failures are out of scope for this archive per the brief ("Do NOT touch drift-hardening directory").
- 7 BDD scenarios across 3 feature files (start) → 7 scenarios across 3 feature files (post PR#1; PR#2 will add 5 more for REQ-49 + REQ-50)
- 9 tasks closed (T1.1..T1.9; full PR#1 task list per `tasks.md`)
- Prompt-registry tests: 99 unit + 7 BDD = 106 new tests, 0 regressions from prompt-registry work
- Final pytest run (excluding drift-hardening WIP failures): **prompt-registry tests all green**

## Capability Mapping Decision

**Precedent-following change**: PR#1 extends the existing `openspec/specs/prompt-registry/spec.md` (bootstrapped at commit `51ac227` per D12 in design.md). The PR#1 archive sync adds:
1. **PR#1 archive status header** at the top of the capability spec, explicitly marking REQ-45/46/47 with their PARTIAL/COMPLIANT status and pointing to `verify-report-pr1.md` for evidence.
2. **PR#1 Scope table** at the bottom of the capability spec, enumerating every REQ (REQ-45..54) with its PR#1 status (PARTIAL/RESOLVED/NOT SHIPPED) so downstream consumers can read the baseline + the deferred-to-PR#2/v1.1 scope at a glance.

The sync pattern matches `observability` PR#1 (per archive-report #61 resolution) and `observability` PR#2 (per `2026-06-27-observability-pr2/archive-report-pr2.md` §"Capability Mapping Decision" — W-fix reconciliation commits are the canonical mechanism for spec/implementation drift at archive time). For prompt-registry PR#1 the resolution is split across two commits:
- **`613f716`** — RESOLVES REQ-46 W5/W6 (the `.format()` fallback + `PromptRenderError` exception class)
- **Archive capability-spec sync** (this commit) — DOCUMENTS the residual PARTIAL state for REQ-45 S1/S2 (schema-shape + BDD-coverage gap) and REQ-47 W1 (lint-taxonomy rename) without modifying production code; carries forward to PR#2 + v0.8.x follow-up.

**Pattern reinforced**: Future capability delta specs continue to ADD requirements to the baseline via standard ADDED/MODIFIED/REMOVED rules; PR#1 archive sync is the canonical mechanism for marking baseline compliance at archive time.

## Carry-forwards from PR#1 verify (resolution)

| ID | Severity | Status | Resolution |
|----|----------|--------|------------|
| **W1** | WARNING | ⚠️ PARTIAL (carry-forward) | `lint_prompts` impl taxonomy (`duplicate_name`, `invalid_domain`, `jinja_syntax`, `undefined_var`, `invalid_version`) ≠ spec taxonomy (`missing_placeholder`, `unused_variable`, `template_parse_error`, `autoescape_disabled`, `missing_variable`). Functionally useful; zero name overlap with spec contract. **Carry-forward to PR#2** — add a `LINT_CATEGORY_SPEC_ALIASES` mapping shim or rename impl categories to spec taxonomy. |
| **W2** | WARNING | ⚠️ PARTIAL (carry-forward) | `_safe_jinja_env()` ships with `autoescape=False`; spec OQ-2 recommends `select_autoescape(default_for_string=True)`. Risk: control-character injection via `{{ var }}` substitution. Bounded for PR#1 (4 migrated entries use Python `.format()` syntax); resurfaces when PR#2 / REQ-51 / REQ-53 generate Jinja2-rendered prompts. **Carry-forward to PR#2** — 3-line fix at `_safe_jinja_env()`. |
| **W3** | WARNING | ⚠️ PARTIAL (carry-forward) | No `prompts/` directory + no `.j2` files at repo root. Templates stored inline as Python strings in `prompt_registry.py:88-134`. **Carry-forward to PR#2** — restore D1 + D2 design choices. |
| **W4** | WARNING | ⚠️ PARTIAL (carry-forward) | `scaffold._env()` hoist NOT done (D3 violation). `scaffold.py:20-25` retains self-contained `_env()` factory. No import cycle, no shared state. **Carry-forward to PR#2** — hoist into shared `prompt_render._env()`. |
| **W5** | WARNING | ✅ **RESOLVED** | commit `613f716` — `render_prompt(name, **kwargs)` now detects templates without Jinja2 placeholders and falls back to `prompt.template.format(**kwargs)`. The 4 migrated `PROMPT_NAMES` entries (Python `.format()` syntax `{test_command}`) now render correctly via `render_prompt("strict_tdd", test_command="pytest")`. Verified at runtime. |
| **W6** | WARNING | ✅ **RESOLVED** | commit `613f716` — `PromptRenderError(Exception)` + `PromptNotFoundError(PromptRenderError)` exception hierarchy lands with structured payload. PR#2 `flow prompts show <unknown>` can wire exit-code-5 mapping. |
| **W7** | WARNING | ⚠️ PARTIAL (carry-forward) | No `[tool.flow_engineering.prompts]` section in `pyproject.toml`. Defaults assumed. **Carry-forward to PR#2** — add section. |
| **W8** | WARNING | ⚠️ PARTIAL (carry-forward) | `pyproject.toml` version `0.7.0`; CHANGELOG.md claims `0.8.0`. `flow --version` prints the old version. **Carry-forward to PR#2** — bump `pyproject.toml:3` to `"0.8.0"`. |
| **W9** | WARNING | ⚠️ PARTIAL (carry-forward) | 5 ruff warnings on changed files (UP042 StrEnum migration, I001 import sort, SIM105 contextlib.suppress, W292 ×2 trailing newlines). 3 of 5 auto-fixable. **Carry-forward to PR#2** — `uv run ruff check --fix` on changed PR#1 files (3 auto-fixed) + manual fixes for the 2 non-auto-fixable. |
| **W10** | WARNING | ⚠️ PARTIAL (carry-forward) | BDD scenarios weaker than spec Gherkin scenarios. REQ-45 S1 only asserts `len >= 4`; REQ-46 S2 uses newly-registered Jinja2 prompts (`{{ user_name }}`) instead of the 4 migrated entries. **Carry-forward to PR#2** — strengthen BDD assertions to match spec Gherkin shape (per-entry fields for REQ-45 S1; exact-string render for REQ-46 S2 with the actual `strict_tdd` entry). |
| **S1..S6** | SUGGESTION | SKIPPED | All 6 suggestions non-blocking (lint alias map, `--autoescape` flag, version bump, ruff auto-fix, BDD shape, federated prompts). Carried to PR#2 sdd-verify for prioritization. |
| **C1 (PR#1 verify brief)** | CRITICAL | ✅ **RESOLVED** | D10 thin-wrapper migration identity check: `STRICT_TDD_PROMPT is get_prompt_template("strict_tdd") == True`; same for `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`. Both `strict_tdd.py:17` and `auto_suggest_code_refs.py:38` import from `prompt_registry.py` per `tests/unit/test_inline_prompt_migration.py`. |

**Resolution count**: 1/1 critical resolved (C1); 2/10 warnings resolved pre-archive (W5, W6 at `613f716`); 8/10 warnings carry-forward to PR#2 (W1, W2, W3, W4, W7, W8, W9, W10); 6/6 suggestions skipped (non-blocking).

## Out-of-scope reminders (carried to PR#2)

1. **REQ-49 SKILL_CATALOG mirror** + checksum drift detection (`opencode_skill_catalog.py`, 20-entry catalog, `~/.flow-engineering/prompt_checksums.json` sidecar). PR#2 sdd-tasks T2.1..T2.3.
2. **REQ-50 `flow prompts` CLI subcommand group** (`list`, `show <id>`, `lint`, `check` — 7 flags total, ~150 prod LOC delta in `cli.py`). PR#2 sdd-tasks T2.4..T2.7.
3. **8/10 W-fix carry-forwards from PR#1** (W1 lint taxonomy alias, W2 autoescape, W3 `prompts/` directory, W4 `scaffold._env()` hoist, W7 `[tool.flow_engineering.prompts]` section, W8 `pyproject.toml` version bump, W9 ruff auto-fix, W10 BDD coverage gap). PR#2 sdd-tasks — bundle into PR#2 closeout batch.
4. **W6 / W5 already resolved** at `613f716` — PR#2 verify confirms carry-forward closure.

## Out-of-scope reminders (deferred beyond PR#2)

1. **REQ-48** — golden regression tests via `pytest` snapshots at `tests/golden/prompts/<prompt_id>.txt` (defer to v1.1)
2. **REQ-51** — `prompt_renders.jsonl` append-only sink at `~/.flow-engineering/prompt_renders.jsonl` (defer to v1.1)
3. **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters wired into `render_prompt()` (defer to v1.1, bundles with REQ-51; lands in `observability.py` per D10)
4. **REQ-53** — `docs/prompts.md` generated from `PROMPT_REGISTRY` at build time (defer to v1.1)
5. **REQ-54** — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`; `flow apply` / `verify` / `archive` assert version >= minimum at startup (defer to v1.1 or bundle into PR#2)
6. **LLM client integration** — NEVER (out of project scope per explore C.5)
7. **i18n / multi-language prompts** — defer to v1.1+
8. **Prompt A/B testing infrastructure** — defer to v1.1+
9. **External prompt marketplace / community registry** — NEVER (single-user tool)
10. **Federated prompt registry** (per-project prompt catalogs) — defer until cross-project-federation extension surfaces a concrete need
11. **Schema migration** `PromptDef` → `PromptEntry` (5 fields → 6 fields: add `template_id` + `location` + `schema_version` as separate fields) — defer to v0.8.x follow-up (not PR#2)
12. **Catalog shape migration** `PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict` — defer to v0.8.x follow-up (not PR#2)

## Cross-impact on prior changes

- **decision-code-linking (change #1, REQ-1..8)**: no impact — `STRICT_TDD_PROMPT` migration to thin `get_prompt_template()` wrapper preserves byte-equality; `prompt_fn=Callable` seam at `engram_io.py:541` unchanged.
- **decision-reality-drift (change #2, REQ-9..16)**: no impact — drift path unchanged; REQ-56 BREAKING migration (parallel drift-hardening work) does not intersect prompt-registry.
- **vector-semantic-search (change #3, REQ-17..22)**: no impact — `VECTOR_COUNTER_NAMES` catalog pattern used as structural template for `PROMPT_NAMES`; no shared mutable state.
- **cross-project-federation (change #4, REQ-23..27)**: no impact — federated prompt registry deferred to v1.1+ (per explore C.5 + proposal §"Out of scope").
- **graph-snapshots (change #5, REQ-28..34)**: no impact — the 6-SKILL.md hand-edit pattern from `CHANGELOG.md:13` is formalized by REQ-49 (PR#2).
- **observability (change #6, REQ-35..39)**: no impact — `PROMPT_NAMES` mirrors the observability catalog pattern; REQ-52 prompt counters (deferred to v1.1) will land in `observability.py` per D10; no shared mutable state, no shared event sink, no shared lookup table.
- **drift-hardening (parallel change #8, REQ-55..59)**: no impact on prompt-registry surface. The 5 failing tests observed in `tests/unit/test_observability_aggregate.py::TestWindowIntegrationOnExport` belong to drift-hardening (REQ-56 BREAKING migration, REQ-59 snapshot field reconciliation) and are out of scope for this archive. Drift-hardening is being archived separately.
- **prompt-registry itself (REQ-45..47)**: shipped + verified + archived with 0 CRITICAL + 2 RESOLVED W (W5, W6 at `613f716`) + 8 PARTIAL W carry-forward to PR#2 + 6 SKIPPED S. PR#2 will close REQ-49 + REQ-50 + the 8 W carry-forwards.

## Cleanup Verification

- `git status --short` after archive operations (pre-commit): working tree shows 10 renames (`R`) + 1 modified (`M` for capability spec) — no untracked files in prompt-registry scope
- `git log --oneline -5`: PR#1 14 apply commits + 1 W-fix commit + archive commit all intact on `main` (HEAD `4bbcc21` pre-archive; archive commit pending orchestrator)
- `uv run pytest --tb=no -q`: **1 120 passed + 5 failed** in 62.39s — prompt-registry tests all green; 5 failures are drift-hardening territory (out of scope per brief)
- 10 git mv operations (6 root + 4 apply-progress)
- 1 mv operation on capability spec (modification, not mv)
- 1 directory removal (empty `apply-progress/` in source)
- 2 created files in archive (this archive-report + capability spec update) + 1 created README.md skeleton in source folder

## Relevant Files

- `src/flow_engineering/prompt_registry.py` — `PromptDomain` enum + `PromptDef` frozen dataclass + `PROMPT_NAMES: tuple[PromptDef, ...]` (4 entries) + `get_prompt_template` / `get_prompt_metadata` / `register_prompt` / `unregister_prompt` / `register` / `validate_catalog` helpers + `lint_prompts()` + `LintReport` + `render_prompt` + `render_prompt_safe` + `list_required_vars` + `PromptRenderError` + `PromptNotFoundError` (~770 LOC final)
- `src/flow_engineering/strict_tdd.py` — MODIFIED (T1.3 thin-wrapper migration: `STRICT_TDD_PROMPT = get_prompt_template("strict_tdd")`)
- `src/flow_engineering/auto_suggest_code_refs.py` — MODIFIED (T1.3 thin-wrapper migration: `EMPTY_PROMPT_TEXT` / `PROMPT_HEADER` / `PROMPT_FOOTER` = `get_prompt_template(...)`)
- `openspec/specs/prompt-registry/spec.md` — UPDATED with PR#1 archive status header + PR#1 Scope table; baseline capability spec catalogs 4 `PROMPT_NAMES` entries + `render_prompt` / `render_prompt_safe` / `list_required_vars` + 5-error-code `lint_prompts`
- `CHANGELOG.md` — v0.8.0 entry (REQ-45..47 + capability bootstrap); `pyproject.toml` version NOT bumped (W8 carry-forward)
- 6 SKILL.md runtime files (outside repo) — `## Prompt registry hook` section in sdd-propose/sdd-design/sdd-tasks/sdd-apply/sdd-verify/sdd-archive
- `tests/unit/test_prompt_registry.py` — NEW (REQ-45 catalog schema + 4-entry migration)
- `tests/unit/test_prompt_registry_helpers.py` — NEW (REQ-45 helpers)
- `tests/unit/test_inline_prompt_migration.py` — NEW (REQ-45 D10 thin-wrapper identity checks)
- `tests/unit/test_prompt_registry_validation.py` — NEW (REQ-47 register + validate_catalog RED→GREEN)
- `tests/unit/test_prompt_lint.py` — NEW (REQ-47 lint_prompts + LintReport)
- `tests/unit/test_prompt_render.py` — NEW (REQ-46 render_prompt + render_prompt_safe + list_required_vars + W5/W6 .format() fallback + PromptRenderError)
- `tests/bdd/req45_prompt_registry.feature` — NEW (REQ-45, 2 BDD scenarios)
- `tests/bdd/req46_prompt_render.feature` — NEW (REQ-46, 3 BDD scenarios)
- `tests/bdd/req47_prompt_lint.feature` — NEW (REQ-47, 2 BDD scenarios)
- `tests/bdd/test_prompt_registry_steps.py` — NEW (shared step glue for 7 PR#1 scenarios; D11 cross-PR extensibility)
- `openspec/changes/archive/2026-06-27-prompt-registry-pr1/` — full archive of proposal/spec/design/tasks/explore/verify-report-pr1 + 4 apply-progress files (pr1-batch-{a,b,c}.md + pr1-merged.md) + this archive-report
- `openspec/changes/prompt-registry/README.md` — PR#2 active scope skeleton (per "next PR continues" precedent at `openspec/changes/archive/2026-06-27-observability-pr2/`)

## Next change

- **Change #7 PR#2**: REQ-49 `SKILL_CATALOG` mirror + REQ-50 `flow prompts` CLI subcommand group. Apply batches ready (T2.1..T2.7 per `tasks.md`). Plus 8 W-fix carry-forwards from PR#1 (W1 lint taxonomy alias, W2 autoescape, W3 `prompts/` directory, W4 `scaffold._env()` hoist, W7 `[tool.flow_engineering.prompts]` section, W8 `pyproject.toml` version bump, W9 ruff auto-fix, W10 BDD coverage gap). **Launch `sdd-tasks prompt-registry PR#2` first** to break the work into implementation tasks; then `sdd-apply prompt-registry PR#2`.
- **After #7 PR#2 archives**: drift-hardening cluster (change #8, REQ-55..59 — already being archived in parallel; W5 from PR#2 will join the carry-forward pool).

---

**Session**: flow-engineering-prompt-registry-pr1-archive-2026-06-27
**SDD Cycle**: COMPLETE (PR#1 closeout)
**Verdict**: PARTIAL — archive-ready (0/0 C + 2/10 W resolved, 8/10 W carry-forward to PR#2, 6/6 S skipped; 5 failing tests are drift-hardening WIP, NOT prompt-registry scope)
**Capability spec sync**: `openspec/specs/prompt-registry/spec.md` updated with PR#1 archive status header + PR#1 Scope table
**Next**: `prompt-registry` PR#2 (sdd-tasks from existing proposal REQ-49/50)
**Topic**: sdd/prompt-registry/archive-report-pr1