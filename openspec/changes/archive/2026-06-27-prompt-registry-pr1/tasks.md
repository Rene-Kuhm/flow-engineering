<!-- tasks.md: prompt-registry. Source: manual. -->
# Tasks: prompt-registry

**Change:** `prompt-registry`
**Builds on:** `proposal.md` (#201) — Approach A: `PromptRegistry` class + JSON-backed catalog; `design.md` (#207) — D1-D12 resolved (12 architecture decisions); `spec.md` (#204) — 5 REQs (REQ-45..47, REQ-49..50), 12 BDD scenarios
**Date:** 2026-06-27
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (2 chained PRs, batched)
**Strict TDD:** ON (per `decision-code-linking` precedent; RED → GREEN → REFACTOR cycle per task)
**Delivery strategy:** chained-pr (per proposal #201 + design #207 D11; 2 PRs mandatory given ×6 strict-TDD multiplier pushes realistic LOC past the 400-line review budget)

---

```yaml
status: success
confidence: high
total_tasks: 17  # T1.1..T1.9 + T2.1..T2.8
pr_split: 2 chained PRs (PR#1: foundation + registry + render + lint; PR#2: SKILL.md catalog + flow prompts CLI)
forecast_loc_production: ~3243
forecast_loc_test: ~6486
forecast_loc_grand_total: ~9729
forecast_loc_realistic_x6: ~19458  # design says ×6 mandatory for CLI-heavy change (mirrors decision-code-linking S3 precedent)
batches:
  pr1_batch_a: 3 tasks   # T1.1, T1.2, T1.3
  pr1_batch_b: 3 tasks   # T1.4, T1.5, T1.6
  pr1_batch_c: 3 tasks   # T1.7, T1.8, T1.9
  pr2_batch_d: 3 tasks   # T2.1, T2.2, T2.3
  pr2_batch_e: 3 tasks   # T2.4, T2.5, T2.6
  pr2_batch_f: 2 tasks   # T2.7, T2.8
review_workload_forecast:
  pr1_400_line_budget_risk: high
  pr2_400_line_budget_risk: medium
  chained_prs_recommended: yes
  decision_needed_before_apply: no  # explicit in proposal #201
strict_tdd: on
bdd_feature_files: 5 NEW (req45..req47, req49, req50)
bdd_scenarios: 12 (REQ-45:2 + REQ-46:3 + REQ-47:2 + REQ-49:2 + REQ-50:3)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\tasks.md
next_recommended: sdd-apply prompt-registry PR#1 batch A
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×6) |
|----|------|-------|--------------|--------------------|
| PR#1 | REQ-45, REQ-46, REQ-47 | T1.1..T1.9 (9 tasks) | ~1900 prod / ~3800 test = ~5700 | ~11 400 |
| PR#2 | REQ-49, REQ-50 | T2.1..T2.8 (8 tasks) | ~1343 prod / ~2686 test = ~4029 | ~8 058 |
| **Total** | **5 REQs** | **17 tasks** | **~3243 / ~6486 = ~9729** | **~19 458** |

**Rationale**:
- **PR#1 establishes the foundation + registry + render + lint surface.** It boots the `PROMPT_REGISTRY` catalog (REQ-45), the shared Jinja2 `Environment` (REQ-46), and the 5-category `lint_prompts()` validator (REQ-47). PR#1 also bootstraps `openspec/specs/prompt-registry/spec.md` per D12. Each PR is independently shippable; PR#1 ships visible user value (catalog discoverability + prompt render + lint coverage) without requiring the SKILL.md mirror catalog or the `flow prompts` CLI.
- **PR#2 adds the SKILL.md discovery mirror + the user-facing `flow prompts` CLI.** It builds on PR#1's `PROMPT_REGISTRY` + shared BDD glue file at `tests/bdd/test_prompt_registry_steps.py` (per D11). All additive on top of PR#1's HEAD; merge-base is PR#1's merge commit.
- **Merge ordering is MANDATORY**: PR#1 MUST merge to `main` BEFORE PR#2 apply starts (Engram #114 stacked-to-main pattern). PR#2 cherry-picks additive changes only.

---

## Dependency Graph

```
PR#1 (branched from main):
  Batch A (foundation + .j2 files + migration):
    T1.1 (prompt_registry.py: PROMPT_REGISTRY dict + PromptEntry frozen dataclass + REGISTRY_SCHEMA_VERSION
          + 4 entries)
      ↓
    T1.2 (prompts/ directory at repo root + get_prompts_dir() + 4 .j2 files
          + scaffold._env() hoist to prompt_render.py)
      ↓
    T1.3 (migrate 4 inline constants: STRICT_TDD_PROMPT + EMPTY_PROMPT_TEXT
          + PROMPT_HEADER + PROMPT_FOOTER → thin wrappers around render_prompt()
          per D10 alias convention)

  Batch B (registry extension + lint):
    T1.4 (prompt_registry.py: list_prompts(domain=None) + get_prompt(name)
          + domain-grouped lookup helpers + 5 unit tests)
      ↓
    T1.5 (prompt_registry.py: PromptRegistry.register(name, template, domain, **meta)
          + validate_catalog() per REGISTRY_SCHEMA_VERSION invariant)
      ↓
    T1.6 (prompt_lint.py: lint_prompts() + LintWarning frozen dataclass
          + 5 warning categories per D7 + LINT_CATEGORY_SEVERITY map)

  Batch C (render + BDD + closeout):
    T1.7 (prompt_render.py: render_prompt() + render_prompt_safe()
          + PromptRenderError + shared Jinja2 Environment per D3/D4)
      ↓
    T1.8 (tests/bdd/req45_prompt_registry.feature + req46_prompt_render.feature
          + req47_prompt_lint.feature + tests/bdd/test_prompt_registry_steps.py glue)
      ↓
    T1.9 (CHANGELOG.md v0.8.0 + 6 SKILL.md "Prompt registry hook" runtime updates
          + bootstrap openspec/specs/prompt-registry/spec.md per D12)

[PR#1 MERGE → main]
        ↓
PR#2 (branched from PR#1's merge commit):
  Batch D (SKILL.md catalog + checksum):
    T2.1 (opencode_skill_catalog.py: SkillEntry + SkillDrift frozen dataclasses
          + SIDECAR_PATH constant + SkillVersionError exception)
      ↓
    T2.2 (opencode_skill_catalog.py: SKILL_CATALOG dict with 20 entries
          = 10 SKILL.md + 10 prompts/sdd/*.md per D6 dual-surface coverage)
      ↓
    T2.3 (opencode_skill_catalog.py: _compute_frontmatter_checksum() + _parse_frontmatter()
          + _read_sidecar() + _write_sidecar() I/O helpers per D5)

  Batch E (drift detection + flow prompts CLI):
    T2.4 (opencode_skill_catalog.py: check_drift() + update_checksums() + init_checksums()
          per D8/D9 exit codes)
      ↓
    T2.5 (cli.py: flow prompts list + flow prompts show <id> subcommands
          with --json + --var key=value flags)
      ↓
    T2.6 (cli.py: flow prompts lint + flow prompts check subcommands
          with --strict / --update / --no-fail / --init / --skill flags per D9)

  Batch F (BDD + closeout):
    T2.7 (tests/bdd/req49_skill_catalog.feature + req50_cli_prompts.feature
          + tests/bdd/test_prompt_registry_steps.py glue extensions)
      ↓
    T2.8 (CHANGELOG.md v0.8.1 + 6 SKILL.md "Skill catalog hook"
          + "Flow prompts CLI hook" runtime updates + apply-progress/finalize)
```

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 17 (T1.1..T1.9 PR#1 + T2.1..T2.8 PR#2) |
| Forecast LOC production (PR#1) | ~1900 |
| Forecast LOC test (PR#1, unit + BDD) | ~3800 |
| Forecast LOC grand total (PR#1) | ~5700 |
| Forecast LOC production (PR#2) | ~1343 |
| Forecast LOC test (PR#2, unit + BDD) | ~2686 |
| Forecast LOC grand total (PR#2) | ~4029 |
| Forecast LOC grand total (both PRs) | ~9729 |
| Forecast LOC realistic (×6 per design §"Strict-TDD ratio") | ~19 458 |
| BDD feature files | 5 (all NEW; req45_prompt_registry, req46_prompt_render, req47_prompt_lint, req49_skill_catalog, req50_cli_prompts) |
| BDD scenarios | 12 (matches spec REQ-45..47 + REQ-49..50) |
| New source files | 5 (`prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`, `opencode_skill_catalog.py`, `openspec/specs/prompt-registry/spec.md`) + 4 `.j2` files at repo root |
| Modified source files | 5 (`strict_tdd.py`, `auto_suggest_code_refs.py`, `scaffold.py`, `cli.py`, `pyproject.toml`) + 2 docs (`CHANGELOG.md`, `openspec/changes/prompt-registry/tasks.md`) |
| New test files | 4 unit (`test_prompt_registry.py`, `test_prompt_render.py`, `test_prompt_lint.py`, `test_opencode_skill_catalog.py`, `test_cli_prompts.py`) + 5 BDD feature files + 1 BDD glue (`test_prompt_registry_steps.py` shared across all 5 BDD features per D11) |
| Chained PRs recommended | **Yes** (per proposal #201 + design #207 D11; ×6 TDD multiplier pushes realistic LOC past 400-line review budget) |
| Chain strategy | PR#1 → merge → PR#2 (mandatory; no cherry-pick across PRs) |
| PR#1 400-line budget risk | **High** (~5700 LOC forecast, ~11 400 realistic; mitigated by 6 work-unit commits per `work-unit-commits` skill) |
| PR#2 400-line budget risk | **Medium** (~4029 LOC forecast, ~8058 realistic; smaller surface, 5 work-unit commits per `work-unit-commits` skill) |
| Decision needed before apply | **No** (chained-pr strategy is explicit in proposal #201; per-commit work-unit splits per `work-unit-commits` skill mitigate review budget) |

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC (PR#1) | design.md D-file breakdown (`prompt_registry.py` ~300 + `prompt_render.py` ~150 + `prompt_lint.py` ~150 + 4 `.j2` files ~10 + `strict_tdd.py` +50 + `auto_suggest_code_refs.py` +50 + `scaffold.py` +50 + `openspec/specs/prompt-registry/spec.md` ~150 + CHANGELOG +50 + 6 SKILL.md +60 + `pyproject.toml` +5 + integration tests +875) | ~1900 |
| Production LOC (PR#2) | design.md D-file breakdown (`opencode_skill_catalog.py` ~300 + `cli.py` +150 + CHANGELOG +50 + 6 SKILL.md +60 + integration tests +783) | ~1343 |
| Realistic ×6 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): design §"File Changes" sets strict-TDD ratio at **×6** (full band; CLI-heavy change mirrors decision-code-linking precedent) | ×6 → ~19 458 grand total realistic |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (#112): ≤3 tasks OR ≤150 LOC prod per delegation, default runtime ~15 min | PR#1 batch A at ~700 LOC is the **TIMEOUT RISK BATCH** |
| Risk: PR#1 batch A | ~700 LOC across 3 tasks (foundation + .j2 files + migration) at ~6 LOC/min = ~2h | **TIMEOUT RISK** — split into A1 (T1.1 foundation) + A2 (T1.2 .j2 files + T1.3 migration) if delegation hits 15-min ceiling mid-batch |
| Risk: 400-line review budget | PR#1 cumulative ~5700 LOC > 400-line budget by ~14× | Mitigated by 6 work-unit commits per `work-unit-commits` convention; per-commit diffs ≤400 LOC |

### Suggested Work Units

Two chained PRs (per proposal #201 + design #207 D11). Each PR lands via per-delegation batching (≤3 tasks / ≤150 LOC prod) at the apply phase.

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|-----------------|----------|-----|
| **PR#1 A** | T1.1 + T1.2 + T1.3 | ~700 | ~550 | PROMPT_REGISTRY foundation + `.j2` files + scaffold hoist + 4 inline constants migrated to thin wrappers — atomic foundation; 6 commits RED → GREEN → REFACTOR; **TIMEOUT RISK BATCH** |
| **PR#1 B** | T1.4 + T1.5 + T1.6 | ~450 | ~700 | `list_prompts`/`get_prompt` lookup helpers + `register()` + `validate_catalog()` + `lint_prompts()` 5-category validator — registry extension |
| **PR#1 C** | T1.7 + T1.8 + T1.9 | ~750 | ~2550 | `render_prompt()` + `render_prompt_safe()` with Jinja2 Environment + BDD req45/46/47 (7 scenarios) + glue file + CHANGELOG + 6 SKILL.md hooks + spec bootstrap |
| **PR#2 D** | T2.1 + T2.2 + T2.3 | ~600 | ~600 | `SKILL_CATALOG` + 20 entries + `compute_checksum()` + frontmatter parser + sidecar I/O — **TIMEOUT RISK BATCH** |
| **PR#2 E** | T2.4 + T2.5 + T2.6 | ~550 | ~1350 | `check_drift()` + `update_checksums()` + `init_checksums()` + `flow prompts list/show/lint/check` CLI subcommands with 7 flags |
| **PR#2 F** | T2.7 + T2.8 | ~193 | ~736 | BDD req49/req50 (5 scenarios) + step glue extensions + CHANGELOG v0.8.1 + 6 SKILL.md skill-catalog/CLI hooks + apply-finalize |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 14 items are explicitly deferred per spec.md #204 + design.md #207 — apply must NOT introduce code for them:

- **REQ-48 — Golden regression tests** — `tests/golden/prompts/<prompt_id>.txt` snapshots for every `PROMPT_REGISTRY` entry; `render_prompt(prompt_id, **canonical_variables)` must equal the snapshot. Defer to v1.1; bundle into PR#1 if scope allows.
- **REQ-51 — `prompt_renders.jsonl` append-only sink** — `~/.flow-engineering/prompt_renders.jsonl` parallels `metrics.jsonl`; opt-in via `FLOW_PROMPT_LOG=1`. Defer to v1.1.
- **REQ-52 — Prompt observability counters** — `prompts_render_total{prompt_id, version}`, `prompts_render_ms`, `prompts_render_failed_total{reason}`. Per D10, when these land, add them to the existing `observability.py` catalog (not a new module). Defer to v1.1 (bundles with REQ-51).
- **REQ-53 — `docs/prompts.md` generated from `PROMPT_REGISTRY`** — flat list of every entry with `{prompt_id, purpose, where it appears, example output}`; cross-linked from `flow prompts show <id>`. Defer to v1.1.
- **REQ-54 — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`** — `flow apply` / `verify` / `archive` assert on startup that the on-disk SKILL.md `version` is >= the minimum; raises `SkillVersionError`. Could bundle into PR#2 if scope allows; otherwise defer to v1.1.
- **LLM client integration** — any actual `openai` / `anthropic` / `litellm` / `langchain` dependency. NEVER (out of project scope per explore C.5; the registry is provider-agnostic and the LLM call is someone else's job).
- **i18n / multi-language prompts** — defer to v1.1+ (no current need; 1 active user).
- **Prompt A/B testing infrastructure** — defer to v1.1+ (only 4 prompts today; no statistical power for A/B).
- **External prompt marketplace / community registry** — NEVER (single-user tool; out of project scope).
- **Federated prompt registry** (per-project prompt catalogs) — defer until `cross-project-federation` extension surfaces a concrete need; resolution from explore C.4 / archive-report #61.
- **Histogram metric type in observability** for `prompts_render_ms` — v1 (when REQ-52 lands) emits `summary` type; `histogram` type deferred until someone needs bucket math.
- **Prompt template caching** — Jinja2 templates are already cached by the `Environment`; no additional layer needed for v1.
- **Async `render_prompt_async()`** — v1 is sync; async variant deferred until a real async caller materializes (none in the current codebase).
- **Per-prompt-per-language sidecar files** — defer to i18n work (v1.1+).
- **CLI flags for prompt introspection beyond `list/show/lint/check`** — defer until a real use case surfaces.

---

## Task list (17 tasks, 2 chained PRs)

### PR#1 — Foundation: PROMPT_REGISTRY catalog + render_prompt() helper + lint_prompts() validator

#### T1.1 — Scaffold `src/flow_engineering/prompt_registry.py` with `PROMPT_REGISTRY` + `PromptEntry` frozen dataclass + 4 entries (REQ-45 core)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~300 impl + ~250 tests = ~550
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (NEW — `REGISTRY_SCHEMA_VERSION: str = "1.0"`, `@dataclass(frozen=True) class PromptEntry` with 6 fields per D4, `PROMPT_REGISTRY: dict[str, PromptEntry]` with 4 entries: `strict_tdd`, `auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`)
  - `tests/unit/test_prompt_registry.py` (NEW — `TestPromptRegistrySchema` class with 8-10 RED fixtures: schema validation, 4-entry migration, frozen-dataclass mutation guard, owner convention, location path resolution)
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] RED: `test_registry_has_exactly_4_entries` fails; `test_registry_strict_tdd_entry_schema` fails; `test_registry_auto_suggest_header_empty_variables` fails; `test_registry_auto_suggest_footer_empty_variables` fails; `test_registry_auto_suggest_empty_empty_variables` fails; `test_prompt_entry_is_frozen_dataclass` fails; `test_prompt_entry_mutation_raises_frozen_instance_error` fails; `test_registry_schema_version_matches_constant` fails; `test_registry_location_points_to_existing_file` fails; `test_registry_owner_contains_slash` fails
  - [ ] GREEN: `REGISTRY_SCHEMA_VERSION: str = "1.0"` (module-level constant per D3)
  - [ ] GREEN: `@dataclass(frozen=True) class PromptEntry` with 6 fields: `template_id: str`, `version: str` (semver `^\d+\.\d+\.\d+$`), `owner: str` (contains `/`, e.g., `flow/observability`), `location: str` (absolute path resolved at import time per D2), `variables: tuple[str, ...]` (declared Jinja2 variable names; may be empty), `schema_version: str` (MUST equal `REGISTRY_SCHEMA_VERSION`)
  - [ ] GREEN: `PROMPT_REGISTRY: dict[str, PromptEntry]` with 4 entries:
    - `"strict_tdd"` → `PromptEntry(template_id="strict_tdd", version="1.0.0", owner="flow/observability", location="<repo>/prompts/strict_tdd.j2", variables=("test_command",), schema_version="1.0")`
    - `"auto_suggest_header"` → `PromptEntry(template_id="auto_suggest_header", version="1.0.0", owner="flow/binding", location="<repo>/prompts/auto_suggest_header.j2", variables=(), schema_version="1.0")`
    - `"auto_suggest_footer"` → `PromptEntry(template_id="auto_suggest_footer", version="1.0.0", owner="flow/binding", location="<repo>/prompts/auto_suggest_footer.j2", variables=(), schema_version="1.0")`
    - `"auto_suggest_empty"` → `PromptEntry(template_id="auto_suggest_empty", version="1.0.0", owner="flow/binding", location="<repo>/prompts/auto_suggest_empty.j2", variables=(), schema_version="1.0")`
  - [ ] GREEN: `PROMPT_REGISTRY` importable as a single symbol: `from flow_engineering.prompt_registry import PROMPT_REGISTRY`
  - [ ] GREEN: Mutation attempts on a `PromptEntry` instance raise `dataclasses.FrozenInstanceError` (verified via `test_prompt_entry_mutation_raises_frozen_instance_error`)
  - [ ] GREEN: All 783 existing tests pass WITHOUT modification (verified via `uv run pytest` — non-breaking guarantee per D8 non-breaking guarantees)
- **Commits:**
  1. `test(unit): RED fixtures for PROMPT_REGISTRY schema + frozen-dataclass mutation guard + 4-entry shape`
  2. `feat(prompt-registry): PROMPT_REGISTRY dict + PromptEntry frozen dataclass + 4 entries + REGISTRY_SCHEMA_VERSION (REQ-45)`

#### T1.2 — Add `prompts/` directory at repo root + `get_prompts_dir()` helper + 4 `.j2` files + hoist `_env()` from `scaffold.py:20` (REQ-46 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~200 tests = ~250
- **Files:**
  - `prompts/strict_tdd.j2` (NEW — Jinja2 version of `STRICT_TDD_PROMPT`; ~4 LOC)
  - `prompts/auto_suggest_header.j2` (NEW — Jinja2 version of `PROMPT_HEADER`; ~2 LOC)
  - `prompts/auto_suggest_footer.j2` (NEW — Jinja2 version of `PROMPT_FOOTER`; ~3 LOC)
  - `prompts/auto_suggest_empty.j2` (NEW — Jinja2 version of `EMPTY_PROMPT_TEXT`; ~1 LOC)
  - `src/flow_engineering/prompt_registry.py` (extend — add `get_prompts_dir() -> Path` helper per D1, configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml`, default `<repo>/prompts/`)
  - `src/flow_engineering/prompt_render.py` (NEW — shared Jinja2 `Environment` hoisted from `scaffold.py:20`; `_env(prompts_dir: Path | None = None) -> Environment` per D3; `select_autoescape(enabled_extensions=(), default_for_string=True)` per OQ-2; `keep_trailing_newline=True`; `FileSystemLoader(prompts_dir)`)
  - `src/flow_engineering/scaffold.py` (modify — `_env()` becomes a thin re-export from `prompt_render._env()`; existing `_env()` callers in `scaffold.py` get `templates/` via a separate `scaffold._env()` that points to the package templates; no import cycle per D11)
  - `pyproject.toml` (modify — add `[tool.flow_engineering.prompts] directory = "prompts"` section)
  - `tests/unit/test_prompt_registry.py` (extend — `TestGetPromptsDir` class with 4 RED fixtures: default path resolution, override via env var, override via pyproject.toml, path normalization)
  - `tests/unit/test_prompt_render.py` (NEW — `TestSharedJinjaEnvironment` class with 4 RED fixtures: environment construction, autoescape enabled, keep_trailing_newline, FileSystemLoader configured)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [ ] RED: `test_get_prompts_dir_default_returns_repo_root_prompts` fails; `test_get_prompts_dir_override_via_env_var` fails; `test_get_prompts_dir_override_via_pyproject_toml` fails; `test_get_prompts_dir_path_normalized` fails; `test_shared_jinja_env_has_select_autoescape_default_for_string_true` fails; `test_shared_jinja_env_keep_trailing_newline_true` fails; `test_shared_jinja_env_file_system_loader_configured` fails; `test_scaffold_env_thin_reexport_works` fails
  - [ ] GREEN: `prompts/strict_tdd.j2` content: `STRICT TDD MODE IS ACTIVE. Test runner: {{ test_command }}. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.`
  - [ ] GREEN: `prompts/auto_suggest_header.j2` content: `Auto-suggested code bindings:`
  - [ ] GREEN: `prompts/auto_suggest_footer.j2` content: `\nEnd of suggestions.`
  - [ ] GREEN: `prompts/auto_suggest_empty.j2` content: `(no suggestions available)`
  - [ ] GREEN: `get_prompts_dir() -> Path` reads `[tool.flow_engineering.prompts] directory` from `pyproject.toml` via `tomllib` (stdlib in Python 3.11+); defaults to `<repo>/prompts/` (resolved via `Path(__file__).parent.parent.parent.parent / "prompts"`)
  - [ ] GREEN: `_env(prompts_dir: Path | None = None) -> Environment` in `prompt_render.py`:
    - `Environment(loader=FileSystemLoader(str(prompts_dir or get_prompts_dir())), autoescape=select_autoescape(enabled_extensions=(), default_for_string=True), keep_trailing_newline=True)`
    - Hoisted from `scaffold.py:20-25` per D3 (no new runtime dependency; Jinja2 is already a project dep)
    - Cached via `functools.lru_cache(maxsize=1)` so the `Environment` is constructed once per process (Jinja2 templates are already cached by the `Environment`)
  - [ ] GREEN: `scaffold.py:_env()` becomes `from flow_engineering.prompt_render import _env as _env` thin re-export; existing `_env()` callers in `scaffold.py` get `templates/` via separate `scaffold._env()` that points to `Path(__file__).parent / "templates"`; no import cycle (verified by `test_scaffold_env_thin_reexport_works`)
  - [ ] GREEN: `pyproject.toml` adds `[tool.flow_engineering.prompts]\ndirectory = "prompts"` section; default fallback if missing is `<repo>/prompts/`
  - [ ] GREEN: All 783 existing tests pass WITHOUT modification (scaffold.py tests, scaffold.py call sites in `cli.py` etc.)
- **Commits:**
  1. `feat(prompt-render): hoist _env() from scaffold.py to prompt_render.py + autoescape per OQ-2`
  2. `feat(prompt-registry): get_prompts_dir() helper + prompts/ directory + 4 .j2 files + pyproject.toml config`
  3. `test(unit): RED fixtures for get_prompts_dir + shared Jinja environment + scaffold._env() re-export`

#### T1.3 — Migrate 4 inline prompt constants to thin `render_prompt()` wrappers (REQ-45 migration per D10 alias convention)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~100 tests = ~250
- **Files:**
  - `src/flow_engineering/strict_tdd.py` (modify — replace `STRICT_TDD_PROMPT` constant (3 lines at `:13`) with 1-line wrapper: `def _build_strict_tdd_prompt(test_command: str) -> str: return render_prompt("strict_tdd", test_command=test_command)`; expose `STRICT_TDD_PROMPT = _build_strict_tdd_prompt` as the v0.7.0 alias per D10)
  - `src/flow_engineering/auto_suggest_code_refs.py` (modify — replace 3 inline constants `EMPTY_PROMPT_TEXT` / `PROMPT_HEADER` / `PROMPT_FOOTER` (at `:47-49`) with thin wrappers: `EMPTY_PROMPT_TEXT = lambda: render_prompt("auto_suggest_empty")`, `PROMPT_HEADER = lambda: render_prompt("auto_suggest_header")`, `PROMPT_FOOTER = lambda: render_prompt("auto_suggest_footer")`; `format_suggestion_prompt()` delegates to registry)
  - `tests/unit/test_strict_tdd.py` (extend — `TestStrictTddMigration` class with 3 RED fixtures: `STRICT_TDD_PROMPT("pytest")` returns expected string, thin wrapper preserves output, removal deferred to v0.8.0)
  - `tests/unit/test_auto_suggest_code_refs.py` (extend — `TestAutoSuggestMigration` class with 4 RED fixtures: each of the 3 constants delegates to `render_prompt()`, output matches pre-migration bytes, `format_suggestion_prompt()` still works)
- **Dependencies:** T1.2 (needs `prompt_render.py:_env()` for the wrappers to call)
- **Acceptance criteria:**
  - [ ] RED: `test_strict_tdd_prompt_thin_wrapper_returns_expected_string` fails; `test_strict_tdd_prompt_thin_wrapper_preserves_output_bytes` fails; `test_strict_tdd_prompt_thin_wrapper_deferred_to_v0_8_0` fails; `test_empty_prompt_text_thin_wrapper` fails; `test_prompt_header_thin_wrapper` fails; `test_prompt_footer_thin_wrapper` fails; `test_format_suggestion_prompt_still_works` fails
  - [ ] GREEN: `STRICT_TDD_PROMPT` becomes a thin wrapper that calls `render_prompt("strict_tdd", test_command=cmd)` per D10 alias convention; output bytes byte-equivalent to pre-migration `STRICT_TDD_PROMPT.format(test_command=cmd)` (verified by `test_strict_tdd_prompt_thin_wrapper_preserves_output_bytes`)
  - [ ] GREEN: 3 inline constants in `auto_suggest_code_refs.py` (`EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) become thin wrappers that call `render_prompt("auto_suggest_empty")`, `render_prompt("auto_suggest_header")`, `render_prompt("auto_suggest_footer")` respectively
  - [ ] GREEN: `format_suggestion_prompt()` in `auto_suggest_code_refs.py` continues to use the constants — no behavior change for external callers
  - [ ] GREEN: `prompt_fn=Callable` injection point at `engram_io.py:541` is preserved as-is (the registry is additive; the testable seam still works — verified by existing `test_engram_io.py` tests staying green)
  - [ ] GREEN: All 783 existing tests pass WITHOUT modification (verified via `uv run pytest` — non-breaking guarantee)
- **Commits:**
  1. `test(unit): RED fixtures for thin-wrapper migration of 4 inline prompt constants`
  2. `feat(prompt-registry): migrate STRICT_TDD_PROMPT + EMPTY_PROMPT_TEXT + PROMPT_HEADER + PROMPT_FOOTER to render_prompt() wrappers per D10 alias`
  3. `test(unit): verify prompt_fn=Callable seam at engram_io.py:541 still works after migration`

#### T1.4 — Add `list_prompts(domain=None)` + `get_prompt(name)` + domain-grouped lookup helpers (REQ-45 extension)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 impl + ~150 tests = ~230
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (extend — add `list_prompts(domain: str | None = None) -> list[PromptEntry]` returning a list of `PromptEntry` instances filtered by domain; `get_prompt(name: str) -> PromptEntry` raising `KeyError` for unknown names; `prompts_by_domain() -> dict[str, list[str]]` returning `{domain: [prompt_id, ...]}` grouped shape)
  - `tests/unit/test_prompt_registry.py` (extend — `TestListPrompts` class with 5 RED fixtures: list all 4, list by domain `flow/binding` returns 3, list by domain `flow/observability` returns 1, list by unknown domain returns empty, `get_prompt("strict_tdd")` returns correct entry, `get_prompt("nonexistent")` raises `KeyError`)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [ ] RED: `test_list_prompts_returns_all_4_entries` fails; `test_list_prompts_filters_by_domain_flow_binding` fails; `test_list_prompts_filters_by_domain_flow_observability` fails; `test_list_prompts_unknown_domain_returns_empty` fails; `test_get_prompt_returns_correct_entry` fails; `test_get_prompt_unknown_name_raises_key_error` fails; `test_prompts_by_domain_groups_correctly` fails
  - [ ] GREEN: `list_prompts(domain=None) -> list[PromptEntry]`:
    - `domain=None` → returns `list(PROMPT_REGISTRY.values())` (all entries)
    - `domain="flow/observability"` → returns 1 entry (`strict_tdd`)
    - `domain="flow/binding"` → returns 3 entries (`auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`)
    - Unknown `domain` → returns `[]` (defensive; caller decides)
    - Result is sorted by `entry.template_id` for stable output
  - [ ] GREEN: `get_prompt(name: str) -> PromptEntry` returns `PROMPT_REGISTRY[name]`; unknown `name` raises `KeyError` with the name in the message (Python's default `KeyError` formatting)
  - [ ] GREEN: `prompts_by_domain() -> dict[str, list[str]]` returns `{"flow/observability": ["strict_tdd"], "flow/binding": ["auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"]}` (used by `flow prompts list` in PR#2 to group rows by `owner`)
- **Commits:**
  1. `test(unit): RED fixtures for list_prompts + get_prompt + prompts_by_domain`
  2. `feat(prompt-registry): list_prompts/get_prompt/prompts_by_domain lookup helpers`

#### T1.5 — Add `PromptRegistry.register(name, template, domain, **meta)` + `validate_catalog()` per REGISTRY_SCHEMA_VERSION (REQ-45 register surface)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~150 tests = ~250
- **Files:**
  - `src/flow_engineering/prompt_registry.py` (extend — add `class PromptRegistry` with `register(name: str, template: str, domain: str, version: str = "1.0.0", variables: tuple[str, ...] = (), **meta: Any) -> PromptEntry` and `validate_catalog(registry: dict[str, PromptEntry] | None = None) -> list[str]` returning list of schema errors; module-level `default_registry: PromptRegistry = PromptRegistry(PROMPT_REGISTRY)` for singleton access)
  - `tests/unit/test_prompt_registry.py` (extend — `TestPromptRegistryRegister` class with 5 RED fixtures: register new entry, register with version bump, register validates `variables` uniqueness, `validate_catalog` returns empty for well-formed catalog, `validate_catalog` fails on `schema_version` mismatch)
- **Dependencies:** T1.1, T1.4
- **Acceptance criteria:**
  - [ ] RED: `test_registry_register_creates_new_entry` fails; `test_registry_register_with_version_bump` fails; `test_registry_register_validates_variables_unique` fails; `test_registry_register_validates_owner_contains_slash` fails; `test_validate_catalog_empty_for_well_formed` fails; `test_validate_catalog_fails_on_schema_version_mismatch` fails
  - [ ] GREEN: `class PromptRegistry`:
    - Constructor: `PromptRegistry(initial: dict[str, PromptEntry] | None = None)` seeds from `PROMPT_REGISTRY` by default
    - `register(name, template, domain, version="1.0.0", variables=(), **meta)` builds a `PromptEntry` with `template_id=name`, `location=str(get_prompts_dir() / f"{name}.j2")`, `owner=domain`, `variables=variables`, `version=version`, `schema_version=REGISTRY_SCHEMA_VERSION`; adds to internal `_registry: dict[str, PromptEntry]`; returns the entry
    - Validates `domain` contains `/` (raises `ValueError` if not)
    - Validates `variables` is a tuple of unique strings (raises `ValueError` on duplicates)
    - Validates `version` matches semver `^\d+\.\d+\.\d+$` (raises `ValueError` if not)
  - [ ] GREEN: `validate_catalog(registry=None) -> list[str]`:
    - Iterates every entry; collects errors for: missing `template_id`, invalid `version` (non-semver), `owner` without `/`, duplicate `variables`, `schema_version` mismatch
    - Returns empty list `[]` for well-formed catalog
    - Defensive: does NOT raise on broken catalog; returns the error list for the caller
- **Commits:**
  1. `test(unit): RED fixtures for PromptRegistry.register + validate_catalog`
  2. `feat(prompt-registry): PromptRegistry class with register() + validate_catalog() per REGISTRY_SCHEMA_VERSION invariant`

#### T1.6 — Implement `lint_prompts()` with 5 warning categories + `LintWarning` frozen dataclass (REQ-47)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~250 tests = ~400
- **Files:**
  - `src/flow_engineering/prompt_lint.py` (NEW — `class PromptLintError(Exception)`, `@dataclass(frozen=True) class LintWarning(prompt_id: str, category: str, message: str, line: int | None = None)`, `LINT_CATEGORY_SEVERITY: dict[str, str]` map with 5 entries per D7, `lint_prompts(registry: dict[str, PromptEntry] | None = None) -> list[LintWarning]`, `_validate_entry(entry: PromptEntry, env: Environment) -> list[LintWarning]` helper)
  - `tests/unit/test_prompt_lint.py` (NEW — `TestLintPrompts` class with 8-10 RED fixtures: clean registry returns empty list, `missing_placeholder` fires when template has `{{ var }}` not in `variables`, `unused_variable` fires when declared `variables` not in template, `template_parse_error` fires on Jinja2 syntax error, `autoescape_disabled` fires when env has no autoescape, `missing_variable` fires on runtime UndefinedError catch, severity map covers all 5 categories)
- **Dependencies:** T1.2 (needs `prompt_render.py:_env()` for parse + AST inspection)
- **Acceptance criteria:**
  - [ ] RED: `test_lint_clean_registry_returns_empty_list` fails; `test_lint_missing_placeholder_fires` fails; `test_lint_unused_variable_fires` fails; `test_lint_template_parse_error_fires` fails; `test_lint_autoescape_disabled_fires` fails; `test_lint_missing_variable_fires` fails; `test_lint_category_severity_map_covers_5_categories` fails; `test_lint_warning_dataclass_is_frozen` fails; `test_lint_does_not_raise_on_broken_catalog` fails
  - [ ] GREEN: `@dataclass(frozen=True) class LintWarning` with 4 fields: `prompt_id: str`, `category: str` (one of 5: `missing_placeholder`, `unused_variable`, `template_parse_error`, `autoescape_disabled`, `missing_variable`), `message: str`, `line: int | None = None` (template line number; None for global checks)
  - [ ] GREEN: `LINT_CATEGORY_SEVERITY: dict[str, str] = {"missing_placeholder": "error", "unused_variable": "warning", "template_parse_error": "error", "autoescape_disabled": "error", "missing_variable": "error"}` per D7
  - [ ] GREEN: `lint_prompts(registry=None) -> list[LintWarning]`:
    - `registry=None` defaults to `PROMPT_REGISTRY`
    - For each `prompt_id, entry in registry.items()`:
      1. Try `parsed = shared_env.parse(entry.location)` → on `jinja2.TemplateSyntaxError`, append `LintWarning(prompt_id, "template_parse_error", f"syntax error: {exc.message}", line=exc.lineno)` and `continue`
      2. `referenced = jinja2.meta.find_undeclared_variables(parsed)`
      3. For each `ref in referenced - set(entry.variables)`: append `LintWarning(prompt_id, "missing_placeholder", f"undefined variable '{ref}'", line=...)`
      4. For each `var in set(entry.variables) - referenced`: append `LintWarning(prompt_id, "unused_variable", f"declared variable '{var}' not used", line=None)`
      5. If `not shared_env.autoescape`: append `LintWarning(prompt_id, "autoescape_disabled", "autoescape is off", line=None)`
    - Returns the collected `list[LintWarning]` (empty when clean; caller decides; CLI maps to exit codes per D9)
  - [ ] GREEN: Does NOT raise on broken registries; returns the warnings list (caller decides; pytest fixture asserts clean; CLI surfaces to user)
- **Commits:**
  1. `test(unit): RED fixtures for lint_prompts 5 warning categories + LintWarning frozen dataclass`
  2. `feat(prompt-lint): lint_prompts() with 5 warning categories per D7 + LINT_CATEGORY_SEVERITY map`

#### T1.7 — Implement `render_prompt()` + `render_prompt_safe()` + `PromptRenderError` (REQ-46)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~120 impl + ~200 tests = ~320
- **Files:**
  - `src/flow_engineering/prompt_render.py` (extend — add `class PromptRenderError(Exception)`, `class PromptNotFoundError(PromptRenderError)`, `render_prompt(prompt_id: str, **variables: Any) -> str`, `render_prompt_safe(prompt_id: str, **variables: Any) -> str`)
  - `tests/unit/test_prompt_render.py` (extend — `TestRenderPrompt` class with 6 RED fixtures: render with kwargs substitutes placeholders, render with no kwargs returns template as-is, render with missing kwargs raises `PromptRenderError`, render unknown prompt_id raises `PromptNotFoundError`, `render_prompt_safe` substitutes `<{var_name}>` sentinel for missing vars, autoescape blocks HTML injection in `test_command`)
- **Dependencies:** T1.2 (needs `prompt_render.py:_env()` from T1.2)
- **Acceptance criteria:**
  - [ ] RED: `test_render_prompt_substitutes_kwargs` fails; `test_render_prompt_no_kwargs_returns_template_as_is` fails; `test_render_prompt_missing_kwargs_raises_error` fails; `test_render_prompt_unknown_id_raises_not_found` fails; `test_render_prompt_safe_sentinel_substitution` fails; `test_render_prompt_autoescape_blocks_html_injection` fails; `test_render_prompt_safe_includes_all_provided_vars` fails
  - [ ] GREEN: `class PromptRenderError(Exception)` is the base for all render failures; `class PromptNotFoundError(PromptRenderError)` raised when `prompt_id` not in `PROMPT_REGISTRY`
  - [ ] GREEN: `render_prompt(prompt_id: str, **variables: Any) -> str`:
    - `entry = PROMPT_REGISTRY[prompt_id]` (raises `PromptNotFoundError` wrapping `KeyError` for unknown IDs — CLI exits 5)
    - `template = _env().get_template(entry.template_id + ".j2")`
    - `return template.render(**variables)`; on `jinja2.UndefinedError`, raises `PromptRenderError(f"undefined variable in {prompt_id}: {exc.message}")` from `exc`
  - [ ] GREEN: `render_prompt_safe(prompt_id: str, **variables: Any) -> str`:
    - Computes `missing = set(entry.variables) - set(variables.keys())`
    - For each missing var, substitutes `safe_kwargs[var_name] = f"<{var_name}>"`
    - Calls `_env().get_template(...).render(**safe_kwargs)`
    - Returns the rendered string with sentinels in place of missing vars
    - NEVER raises on missing vars (CLI inspection mode is informative; sentinels prevent silent empty-string injection into agent context per OQ-4)
  - [ ] GREEN: Autoescape blocks HTML injection — `render_prompt("strict_tdd", test_command="<script>alert(1)</script>")` returns the string with `<` escaped to `&lt;` (verified via `test_render_prompt_autoescape_blocks_html_injection` per OQ-2)
- **Commits:**
  1. `test(unit): RED fixtures for render_prompt + render_prompt_safe + PromptRenderError + autoescape`
  2. `feat(prompt-render): render_prompt() + render_prompt_safe() + PromptRenderError per OQ-4 split`

#### T1.8 — BDD `req45_prompt_registry.feature` (2 scenarios) + `req46_prompt_render.feature` (3 scenarios) + `req47_prompt_lint.feature` (2 scenarios) + step glue (REQ-45/46/47 BDD coverage)

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 prod (BDD feature file headers + glue structure) + ~300 test (5 BDD feature files + glue) = ~350
- **Files:**
  - `tests/bdd/req45_prompt_registry.feature` (NEW — 2 BDD scenarios from spec REQ-45: "Registry lists all known prompts by domain" + "Registry raises KeyError on unknown prompt name")
  - `tests/bdd/req46_prompt_render.feature` (NEW — 3 BDD scenarios from spec REQ-46: "render with no kwargs returns the template as-is" + "render with kwargs substitutes Jinja2 placeholders" + "render with missing kwargs raises UndefinedError")
  - `tests/bdd/req47_prompt_lint.feature` (NEW — 2 BDD scenarios from spec REQ-47: "lint passes for well-formed prompt catalog" + "lint fails for prompt with undefined placeholder variable")
  - `tests/bdd/test_prompt_registry_steps.py` (NEW — pytest-bdd glue shared across all 5 BDD features per D11; ~150 LOC for PR#1; ~250 more LOC land in PR#2 T2.7)
  - `tests/unit/test_prompt_registry.py` (extend — +`TestBddRegistrySteps` smoke test that BDD steps glue correctly)
- **Dependencies:** T1.1, T1.4, T1.6, T1.7
- **Acceptance criteria:**
  - [ ] RED: `pytest tests/bdd/req45_prompt_registry.feature` fails (no steps); `pytest tests/bdd/req46_prompt_render.feature` fails (no steps); `pytest tests/bdd/req47_prompt_lint.feature` fails (no steps)
  - [ ] GREEN: `tests/bdd/req45_prompt_registry.feature` has 2 scenarios verbatim from spec REQ-45 §"Scenario: Registry lists all known prompts by domain" + §"Scenario: Registry raises KeyError on unknown prompt name"
  - [ ] GREEN: `tests/bdd/req46_prompt_render.feature` has 3 scenarios verbatim from spec REQ-46 §"Scenario: render with no kwargs returns the template as-is" + §"Scenario: render with kwargs substitutes Jinja2 placeholders" + §"Scenario: render with missing kwargs raises UndefinedError"
  - [ ] GREEN: `tests/bdd/req47_prompt_lint.feature` has 2 scenarios verbatim from spec REQ-47 §"Scenario: lint passes for well-formed prompt catalog" + §"Scenario: lint fails for prompt with undefined placeholder variable"
  - [ ] GREEN: `tests/bdd/test_prompt_registry_steps.py` provides step definitions for all 7 PR#1 BDD scenarios; uses `from flow_engineering.prompt_registry import PROMPT_REGISTRY` + `from flow_engineering.prompt_render import render_prompt, render_prompt_safe, PromptRenderError` + `from flow_engineering.prompt_lint import lint_prompts, LintWarning` imports
  - [ ] GREEN: All 7 PR#1 BDD scenarios pass via `pytest tests/bdd/`; full unit test suite (783 existing + ~700 new unit tests from T1.1..T1.7) passes
- **Commits:**
  1. `test(bdd): req45_prompt_registry feature with 2 scenarios + shared step glue foundation`
  2. `test(bdd): req46_prompt_render feature with 3 scenarios + step glue extensions`
  3. `test(bdd): req47_prompt_lint feature with 2 scenarios + step glue extensions`

#### T1.9 — CHANGELOG.md v0.8.0 entry + 6 SKILL.md "Prompt registry hook" runtime updates + bootstrap `openspec/specs/prompt-registry/spec.md` (REQ-45/46/47 closeout + D12)

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~250 docs (CHANGELOG +50 + 6 SKILL.md ~30 prose each + spec.md ~150 = ~380)
- **Files:**
  - `CHANGELOG.md` (modify — new `## [0.8.0] - 2026-06-27` section above `[0.7.0]` after PR#1 merge; entry covers `PROMPT_REGISTRY` + `render_prompt()` + `lint_prompts()` + 4 migrated inline constants)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify, runtime — NOT in repo; add `## Prompt registry hook` section referencing REQ-45 `PROMPT_REGISTRY`)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify, runtime)
  - `openspec/specs/prompt-registry/spec.md` (NEW — capability catalog per D12; mirrors `openspec/changes/prompt-registry/spec.md` shape with v1.0 baseline; catalogs all 4 `PROMPT_REGISTRY` entries + the 4 new `.j2` files + the `render_prompt()` API + the `lint_prompts()` 5-category validator)
  - `tests/integration/test_prompt_registry_pr1_integration.py` (NEW — 4-5 integration tests covering the full PR#1 surface: 50 events across 4 prompts → `PROMPT_REGISTRY` lookup → `render_prompt()` round-trip → `lint_prompts()` clean → thin-wrapper migration preserved)
- **Dependencies:** T1.1..T1.8
- **Acceptance criteria:**
  - [ ] GREEN: CHANGELOG v0.8.0 entry lists:
    - `PROMPT_REGISTRY: dict[str, PromptEntry]` with 4 migrated entries (REQ-45)
    - `render_prompt(prompt_id, **variables)` shared Jinja2 helper (REQ-46)
    - `render_prompt_safe(prompt_id, **variables)` with sentinel substitution (REQ-46)
    - `lint_prompts()` validator with 5 warning categories (REQ-47)
    - 4 inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) migrated to thin `render_prompt()` wrappers for v0.7.0 (per D10 alias)
    - 7 BDD scenarios across 3 feature files (req45/46/47)
    - `openspec/specs/prompt-registry/spec.md` bootstrap (per D12)
    - `prompts/` directory at repo root + `_env()` hoist from `scaffold.py:20` to `prompt_render.py`
    - All 783 existing tests pass; `ruff check` clean on changed files
  - [ ] GREEN: 6 SKILL.md files have `## Prompt registry hook` section (3-5 lines each) naming REQ-45/46/47 and referencing `PROMPT_REGISTRY`, `render_prompt()`, `lint_prompts()`, and the `prompts/` directory
  - [ ] GREEN: `openspec/specs/prompt-registry/spec.md` exists (verified via `Test-Path -LiteralPath "openspec/specs/prompt-registry/spec.md"` returning `True` after PR#1 merge); catalogs 4 `PROMPT_REGISTRY` entries with full metadata + the render/lint contracts; marks as `v1.0` baseline; kebab-case folder per capability per D12
  - [ ] GREEN: Integration tests pass — `PROMPT_REGISTRY["strict_tdd"]` round-trip via `render_prompt("strict_tdd", test_command="pytest")` returns expected string; `lint_prompts(PROMPT_REGISTRY)` returns empty list; 4 migrated thin wrappers preserve output bytes
- **Commits:**
  1. `docs(spec): bootstrap openspec/specs/prompt-registry/spec.md capability catalog per D12`
  2. `docs(release): CHANGELOG v0.8.0 entry + 6 SKILL.md prompt registry hooks`
  3. `test(integration): end-to-end integration tests for PR#1 surface (PROMPT_REGISTRY + render + lint)`

---

### PR#2 — Discovery: SKILL_CATALOG mirror + `flow prompts` CLI + sidecar JSON + closeout

#### T2.1 — Scaffold `src/flow_engineering/opencode_skill_catalog.py` with `SkillEntry` + `SkillDrift` frozen dataclasses + `SkillVersionError` (REQ-49 core)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~100 tests = ~150
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (NEW — `SIDECAR_PATH: Path = Path.home() / ".flow-engineering" / "prompt_checksums.json"`, `@dataclass(frozen=True) class SkillEntry` with 6 fields: `skill_name: str`, `surface: str` ∈ `{"skill", "prompt"}`, `expected_version: str` (semver MAJOR.MINOR), `expected_path: str` (absolute path), `last_verified_checksum: str` (64-char lowercase hex SHA-256), `owner: str` (typically `gentleman-programming`), `@dataclass(frozen=True) class SkillDrift` with 6 fields: `skill_name: str`, `surface: str`, `expected_version: str`, `on_disk_version: str`, `expected_checksum: str`, `on_disk_checksum: str`, `drift_kind: str` ∈ `{"checksum_mismatch", "version_mismatch", "missing_file", "frontmatter_parse_error"}`, `class SkillVersionError(Exception)`)
  - `tests/unit/test_opencode_skill_catalog.py` (NEW — `TestSkillEntrySchema` class with 4 RED fixtures: SkillEntry frozen-dataclass mutation guard, surface ∈ {skill, prompt}, expected_version semver MAJOR.MINOR format, last_verified_checksum 64-char hex)
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] RED: `test_skill_entry_frozen_mutation_raises` fails; `test_skill_entry_surface_must_be_skill_or_prompt` fails; `test_skill_entry_expected_version_semver_format` fails; `test_skill_entry_last_verified_checksum_64_char_hex` fails
  - [ ] GREEN: `SIDECAR_PATH: Path = Path.home() / ".flow-engineering" / "prompt_checksums.json"` per D5 (parallels `~/.flow-engineering/metrics.jsonl` REQ-8 close contract)
  - [ ] GREEN: `@dataclass(frozen=True) class SkillEntry` with 6 fields per D5; mutation attempts raise `dataclasses.FrozenInstanceError`
  - [ ] GREEN: `@dataclass(frozen=True) class SkillDrift` with 7 fields per D9; `drift_kind` constrained to the 4 categories
  - [ ] GREEN: `class SkillVersionError(Exception)` raised by `flow apply` / `flow verify` / `flow archive` (REQ-54 stub, deferred to v1.1) when on-disk SKILL.md `version` is less than `expected_version`; v0.7.0 surface only WARNs via the `flow prompts check` exit code
- **Commits:**
  1. `test(unit): RED fixtures for SkillEntry + SkillDrift + SkillVersionError schema`
  2. `feat(skill-catalog): SkillEntry + SkillDrift frozen dataclasses + SIDECAR_PATH constant + SkillVersionError (REQ-49)`

#### T2.2 — Add 20 entries to `SKILL_CATALOG` (10 SKILL.md + 10 prompts/sdd/*.md per D6 dual-surface coverage)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~120 prod (data) + ~100 tests = ~220
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (extend — `SKILL_CATALOG: dict[str, SkillEntry]` with 20 entries: 10 `skill` surface (sdd-init, sdd-explore, sdd-propose, sdd-design, sdd-spec, sdd-tasks, sdd-apply, sdd-verify, sdd-archive, sdd-onboard at `~/.config/opencode/skills/<name>/SKILL.md`) + 10 `prompt` surface (same 10 names at `~/.config/opencode/prompts/sdd/<name>.md`); keys are `<skill_name>/<surface>`; `expected_version="3.0"` for each; `owner="gentleman-programming"` for each)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — `TestSkillCatalogCoverage` class with 4 RED fixtures: catalog has exactly 20 entries, all 10 sdd-* agents present, both surfaces covered for each agent, expected_version is 3.0 across the catalog)
- **Dependencies:** T2.1
- **Acceptance criteria:**
  - [ ] RED: `test_skill_catalog_has_exactly_20_entries` fails; `test_skill_catalog_covers_all_10_sdd_agents` fails; `test_skill_catalog_both_surfaces_per_agent` fails; `test_skill_catalog_expected_version_3_0` fails
  - [ ] GREEN: `SKILL_CATALOG: dict[str, SkillEntry]` has 20 entries keyed by `<skill_name>/<surface>`:
    - 10 `skill` surface entries: paths to `~/.config/opencode/skills/sdd-<name>/SKILL.md` (10 agents: sdd-init, sdd-explore, sdd-propose, sdd-design, sdd-spec, sdd-tasks, sdd-apply, sdd-verify, sdd-archive, sdd-onboard)
    - 10 `prompt` surface entries: paths to `~/.config/opencode/prompts/sdd/<name>.md` (same 10 agents)
    - All entries have `expected_version="3.0"`, `owner="gentleman-programming"`, `last_verified_checksum=""` (empty before first `--init`)
  - [ ] GREEN: Per-agent coverage test verifies both surfaces exist for each of the 10 sdd-* agents (per D6 dual-surface coverage)
- **Commits:**
  1. `test(unit): RED fixtures for SKILL_CATALOG 20-entry coverage + dual-surface invariant`
  2. `feat(skill-catalog): SKILL_CATALOG dict with 20 entries (10 SKILL.md + 10 prompts/sdd/*.md per D6)`

#### T2.3 — Implement `compute_checksum()` + frontmatter parser + sidecar I/O helpers (REQ-49 helpers)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~200 tests = ~300
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (extend — `FRONTMATTER_PATTERN: re.Pattern` matching `\A---\s*\n(.*?\n)---\s*\n`, `_compute_frontmatter_checksum(path: Path) -> str` per OQ-5 (SHA-256 of canonicalized YAML frontmatter dict), `_parse_frontmatter(path: Path) -> dict[str, Any]` parsing YAML between `---` markers, `_read_sidecar() -> dict[str, dict[str, str]]` returning `{}` when sidecar missing, `_write_sidecar(sidecar: dict[str, dict[str, str]]) -> None` writing JSON atomically via `tempfile + os.replace`)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — `TestChecksum` class with 6 RED fixtures: SHA-256 matches reference value, frontmatter-only checksum ignores body whitespace, Unicode preserved via `ensure_ascii=False`, missing file raises `FileNotFoundError`, no frontmatter raises `SkillVersionError`, frontmatter not a dict raises `SkillVersionError`)
- **Dependencies:** T2.1
- **Acceptance criteria:**
  - [ ] RED: `test_compute_checksum_matches_reference_sha256` fails; `test_compute_checksum_ignores_body_whitespace` fails; `test_compute_checksum_preserves_unicode` fails; `test_compute_checksum_missing_file_raises_file_not_found` fails; `test_compute_checksum_no_frontmatter_raises_skill_version_error` fails; `test_compute_checksum_frontmatter_not_dict_raises_skill_version_error` fails; `test_sidecar_read_returns_empty_when_missing` fails; `test_sidecar_write_read_round_trip` fails
  - [ ] GREEN: `_compute_frontmatter_checksum(path: Path) -> str` per OQ-5:
    - `text = path.read_text(encoding="utf-8")`
    - `match = FRONTMATTER_PATTERN.match(text)`; if no match, raise `SkillVersionError(f"{path}: no YAML frontmatter found")`
    - `parsed = yaml.safe_load(match.group(1))`; if not isinstance(parsed, dict), raise `SkillVersionError(f"{path}: frontmatter is not a YAML dict")`
    - `canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
    - `return hashlib.sha256(canonical.encode("utf-8")).hexdigest()` (64-char lowercase hex)
  - [ ] GREEN: `_parse_frontmatter(path: Path) -> dict[str, Any]` returns the YAML dict (same regex + parse as checksum)
  - [ ] GREEN: `_read_sidecar() -> dict[str, dict[str, str]]`:
    - `if not SIDECAR_PATH.exists(): return {}` (lazy bootstrap on first `--init`)
    - `return json.loads(SIDECAR_PATH.read_text(encoding="utf-8"))` (returns the per-skill dict)
  - [ ] GREEN: `_write_sidecar(sidecar)` writes JSON atomically (mirrors `_atomic_write_text` from observability T1.9; `tempfile.NamedTemporaryFile` + `os.replace` per D11 cross-PR consistency)
- **Commits:**
  1. `test(unit): RED fixtures for compute_checksum + frontmatter parser + sidecar I/O`
  2. `feat(skill-catalog): _compute_frontmatter_checksum + _parse_frontmatter + sidecar I/O helpers per OQ-5`

#### T2.4 — Implement `check_drift()` + `update_checksums()` + `init_checksums()` per D8/D9 exit codes (REQ-49 core operations)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~150 tests = ~250
- **Files:**
  - `src/flow_engineering/opencode_skill_catalog.py` (extend — `check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]` per D8; `update_checksums(catalog=None) -> int` returning count of entries updated; `init_checksums(catalog=None) -> int` returning count of entries bootstrapped)
  - `tests/unit/test_opencode_skill_catalog.py` (extend — `TestCheckDrift` class with 5 RED fixtures: empty catalog returns empty list, fresh init returns no drift, modified SKILL.md triggers `checksum_mismatch`, missing SKILL.md triggers `missing_file`, version-only change triggers `version_mismatch`)
- **Dependencies:** T2.2, T2.3
- **Acceptance criteria:**
  - [ ] RED: `test_check_drift_empty_catalog_returns_empty` fails; `test_check_drift_fresh_init_no_drift` fails; `test_check_drift_modified_skill_md_triggers_checksum_mismatch` fails; `test_check_drift_missing_file_triggers_missing_file` fails; `test_check_drift_version_only_change_triggers_version_mismatch` fails; `test_update_checksums_writes_new_sidecar` fails; `test_init_checksums_bootstrap_when_missing` fails
  - [ ] GREEN: `check_drift(catalog=None) -> list[SkillDrift]` per design §"Algorithm Details":
    - `catalog = catalog or SKILL_CATALOG`; `sidecar = _read_sidecar()` (returns `{}` when missing)
    - For each `key, entry in catalog.items()`:
      1. `sidecar_entry = sidecar.get(key, {})`; `expected_checksum = sidecar_entry.get("checksum", "")`; `expected_version = sidecar_entry.get("version", entry.expected_version)` (catalog fallback for first-ever check before `--init`)
      2. If `not Path(entry.expected_path).exists()`: append `SkillDrift(..., drift_kind="missing_file")` and `continue`
      3. Try: `on_disk_checksum = _compute_frontmatter_checksum(Path(entry.expected_path))`; `on_disk_version = str(_parse_frontmatter(...).get("version", "0.0"))`
      4. On `(SkillVersionError, yaml.YAMLError)`: append `SkillDrift(..., drift_kind="frontmatter_parse_error")` and `continue`
      5. If `on_disk_checksum != expected_checksum`: append `SkillDrift(..., drift_kind="checksum_mismatch")`
      6. Elif `on_disk_version != expected_version`: append `SkillDrift(..., drift_kind="version_mismatch")`
    - Returns the `list[SkillDrift]` (empty when clean)
  - [ ] GREEN: `update_checksums(catalog=None) -> int`:
    - Computes fresh checksum for each entry via `_compute_frontmatter_checksum`
    - Writes to sidecar via `_write_sidecar` (atomic via `tempfile + os.replace` per D11)
    - Returns count of entries updated
  - [ ] GREEN: `init_checksums(catalog=None) -> int`:
    - If `SIDECAR_PATH.exists()`: returns `0` (idempotent; no overwrite)
    - Else: calls `update_checksums(catalog)` and returns count bootstrapped
- **Commits:**
  1. `test(unit): RED fixtures for check_drift + update_checksums + init_checksums`
  2. `feat(skill-catalog): check_drift + update_checksums + init_checksums per D8/D9 contracts`

#### T2.5 — Add `flow prompts list` + `flow prompts show <id>` subcommands with `--json` + `--var key=value` flags (REQ-50 partial)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~250 tests = ~400
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `flow` CLI with `prompts` Click group; add `list` subcommand with `--json` flag per REQ-50; add `show <prompt_id>` subcommand with repeatable `--var key=value` flag per REQ-50 + OQ-4; uses `render_prompt_safe()` for missing-var sentinel substitution)
  - `tests/unit/test_cli_prompts.py` (NEW — `TestFlowPromptsList` class with 5 RED fixtures + `TestFlowPromptsShow` class with 6 RED fixtures)
- **Dependencies:** T2.4 (CLI uses `PROMPT_REGISTRY` + `render_prompt_safe`)
- **Acceptance criteria:**
  - [ ] RED: `test_flow_prompts_list_default_renders_table` fails; `test_flow_prompts_list_json_emits_flat_dict` fails; `test_flow_prompts_list_groups_by_owner` fails; `test_flow_prompts_list_empty_registry_emits_no_entries` fails; `test_flow_prompts_list_includes_footer` fails; `test_flow_prompts_show_renders_with_kwargs` fails; `test_flow_prompts_show_metadata_header` fails; `test_flow_prompts_show_repeatable_var_flag` fails; `test_flow_prompts_show_sentinel_for_missing_vars` fails; `test_flow_prompts_show_unknown_id_exits_5` fails; `test_flow_prompts_show_autoescape_footer` fails
  - [ ] GREEN: `flow prompts list` (no flags):
    - Prints table with columns `{prompt_id, version, owner, location}` per spec REQ-50 §"flow prompts list"
    - Header line: `prompt_id                  version  owner                location`
    - Rows grouped by `owner` (`flow/observability` for `strict_tdd`, `flow/binding` for the 3 auto-suggest entries)
    - Footer: `4 prompt entries · 0 lint warnings · registry schema_version=1.0`
    - Exits `0`
  - [ ] GREEN: `flow prompts list --json`:
    - Emits flat dict `{prompt_id: {version, owner, location, variables}, ...}` (mirrors `flow metrics --json` precedent)
    - Exits `0`
  - [ ] GREEN: `flow prompts show <prompt_id>`:
    - Prints metadata header (`prompt_id`, `version`, `owner`, `variables`) followed by rendered template + footer (`rendered via Jinja2 · autoescape=on · source: prompts/<id>.j2`) per spec REQ-50 §"flow prompts show"
    - Exits `0` on success
    - Exits `5` on unknown prompt_id (per D9 exit codes: `5` = unknown prompt id); emits JSON error `{"error": "unknown prompt id", "prompt_id": "<id>", "hint": "run 'flow prompts list' to see available"}` to stderr
  - [ ] GREEN: `--var key=value` flag is repeatable (`--var test_command=pytest --var foo=bar`); uses `render_prompt_safe()` so missing declared vars get `<{var_name}>` sentinel per OQ-4
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts list + show + --json + --var flags + exit code 5`
  2. `feat(cli): flow prompts list + show subcommands with --json and --var flags per REQ-50`

#### T2.6 — Add `flow prompts lint` + `flow prompts check` subcommands with `--strict` / `--update` / `--no-fail` / `--init` / `--skill` flags (REQ-47/49/50 closeout CLI)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~200 tests = ~300
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `lint` subcommand with `--strict` flag per REQ-50; add `check` subcommand with `--update` / `--no-fail` / `--init` / `--skill <name>` flags per REQ-50 + OQ-9)
  - `tests/unit/test_cli_prompts.py` (extend — `TestFlowPromptsLint` class with 4 RED fixtures + `TestFlowPromptsCheck` class with 6 RED fixtures)
- **Dependencies:** T2.4 (uses `check_drift` + `update_checksums` + `init_checksums`)
- **Acceptance criteria:**
  - [ ] RED: `test_flow_prompts_lint_clean_exits_0` fails; `test_flow_prompts_lint_with_errors_exits_2` fails; `test_flow_prompts_lint_with_warnings_exits_1` fails; `test_flow_prompts_lint_strict_promotes_warnings_to_errors` fails; `test_flow_prompts_check_clean_exits_0` fails; `test_flow_prompts_check_drift_exits_1` fails; `test_flow_prompts_check_no_fail_exits_0_on_drift` fails; `test_flow_prompts_check_update_refreshes_sidecar` fails; `test_flow_prompts_check_init_bootstraps_sidecar` fails; `test_flow_prompts_check_skill_flag_limits_to_one_entry` fails
  - [ ] GREEN: `flow prompts lint [--strict]`:
    - Prints `<prompt_id>: OK` per entry + footer `4 prompts linted · 0 warnings · 0 errors` when clean; exits `0`
    - Prints `<prompt_id>: <category>: <message>` lines + footer `4 prompts linted · N warnings · M errors` when warnings/errors present
    - Exits `1` on `warning` category, `2` on `error` category, `2` when `--strict` is given AND any warning is present (mirrors `flow drift --strict` precedent per REQ-50)
  - [ ] GREEN: `flow prompts check [--update] [--no-fail] [--init] [--skill <name>]`:
    - Prints `<skill_name>: <version>: <status>` lines where status is `OK` / `DRIFT` / `MISSING` / `PARSE_ERROR` per spec REQ-50 §"flow prompts check"
    - Exits `0` when no drift detected; exits `1` on drift (unless `--no-fail`)
    - `--update` flag calls `update_checksums()` to refresh the sidecar (opt-in per OQ-9); exits `0` after writing
    - `--no-fail` flag suppresses non-zero exit on drift (CI compat per OQ-9 / D9 exit codes)
    - `--init` flag calls `init_checksums()` to bootstrap the sidecar when missing; exits `0`
    - `--skill <name>` flag limits the check to one entry (debugging; filters catalog by `skill_name == <name>` before `check_drift`)
- **Commits:**
  1. `test(unit): RED fixtures for flow prompts lint + check + 5 flags (--strict, --update, --no-fail, --init, --skill)`
  2. `feat(cli): flow prompts lint + check subcommands per REQ-50 + OQ-9 exit codes`

#### T2.7 — BDD `req49_skill_catalog.feature` (2 scenarios) + `req50_cli_prompts.feature` (3 scenarios) + step glue extensions (REQ-49/50 BDD coverage)

- **Type:** bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 prod (BDD feature file headers) + ~250 test (2 new BDD feature files + glue extensions) = ~300
- **Files:**
  - `tests/bdd/req49_skill_catalog.feature` (NEW — 2 BDD scenarios from spec REQ-49: "check-drift detects when SKILL.md checksums don't match catalog" + "check-drift passes when all SKILL.md checksums match")
  - `tests/bdd/req50_cli_prompts.feature` (NEW — 3 BDD scenarios from spec REQ-50: "`flow prompts list` shows all registered prompts grouped by domain" + "`flow prompts show <name>` renders the prompt with kwargs" + "`flow prompts lint` exits non-zero when catalog has validation errors")
  - `tests/bdd/test_prompt_registry_steps.py` (extend — +step glue for REQ-49 + REQ-50; uses `from flow_engineering.opencode_skill_catalog import SKILL_CATALOG, check_drift, update_checksums, init_checksums` + Click's `CliRunner` for CLI testing)
- **Dependencies:** T2.1..T2.6
- **Acceptance criteria:**
  - [ ] RED: `pytest tests/bdd/req49_skill_catalog.feature` fails (no steps); `pytest tests/bdd/req50_cli_prompts.feature` fails (no steps)
  - [ ] GREEN: `tests/bdd/req49_skill_catalog.feature` has 2 scenarios verbatim from spec REQ-49 §"Scenario: check-drift detects when SKILL.md checksums don't match catalog" + §"Scenario: check-drift passes when all SKILL.md checksums match"
  - [ ] GREEN: `tests/bdd/req50_cli_prompts.feature` has 3 scenarios verbatim from spec REQ-50 §"Scenario: `flow prompts list` shows all registered prompts grouped by domain" + §"Scenario: `flow prompts show <name>` renders the prompt with kwargs" + §"Scenario: `flow prompts lint` exits non-zero when catalog has validation errors"
  - [ ] GREEN: `tests/bdd/test_prompt_registry_steps.py` extended with step definitions for all 5 PR#2 BDD scenarios; uses `Click.CliRunner` for `flow prompts list/show/lint/check` CLI invocations
  - [ ] GREEN: All 5 PR#2 BDD scenarios pass via `pytest tests/bdd/`; full unit test suite (783 existing + ~700 new unit tests from PR#1 + ~600 new from PR#2) passes
- **Commits:**
  1. `test(bdd): req49_skill_catalog feature with 2 scenarios + shared step glue extensions`
  2. `test(bdd): req50_cli_prompts feature with 3 scenarios + step glue extensions`

#### T2.8 — CHANGELOG.md v0.8.1 entry + 6 SKILL.md "Skill catalog hook" + "Flow prompts CLI hook" runtime updates + apply-progress/finalize (REQ-49/50 closeout)

- **Type:** docs + apply-closeout
- **TDD phase:** N/A (docs)
- **LOC:** ~200 docs (CHANGELOG +50 + 12 SKILL.md prose ~60 + apply-progress/finalize +40 = ~150)
- **Files:**
  - `CHANGELOG.md` (modify — add `## [0.8.1] - 2026-06-27` section above `[0.8.0]`; incremental from PR#1's v0.8.0 entry)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify, runtime — extend with `## Skill catalog hook` + `## Flow prompts CLI hook` subsections referencing REQ-49 + REQ-50)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify, runtime)
- **Dependencies:** T2.1..T2.7
- **Acceptance criteria:**
  - [ ] GREEN: CHANGELOG v0.8.1 entry lists:
    - `SKILL_CATALOG` with 20 entries (10 SKILL.md + 10 prompts/sdd/*.md per D6 dual-surface coverage) (REQ-49)
    - `check_drift(SKILL_CATALOG)` returns `list[SkillDrift]` with 4 drift kinds (`checksum_mismatch`, `version_mismatch`, `missing_file`, `frontmatter_parse_error`) per D8/D9
    - `~/.flow-engineering/prompt_checksums.json` sidecar JSON format (per D5 frontmatter-only SHA-256)
    - `flow prompts {list, show, lint, check}` CLI surface with 7 flags (`--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`) (REQ-50)
    - Exit codes 0/1/2/3/5 per D9 contract; `flow prompts show <unknown>` exits 5; `flow prompts check` with drift exits 1 (unless `--no-fail`); `flow prompts lint` with errors exits 2
    - 5 BDD scenarios across 2 feature files (req49/req50)
    - `openspec/specs/prompt-registry/spec.md` extension with 20 SKILL_CATALOG entries + SKILL.md mirror contract
  - [ ] GREEN: 6 SKILL.md files extend `## Prompt registry hook` with `## Skill catalog hook` (REQ-49; `SKILL_CATALOG` + `check_drift` + sidecar format) and `## Flow prompts CLI hook` (REQ-50; `flow prompts {list, show, lint, check}` + exit codes + 7 flags) subsections (3-5 lines each)
  - [ ] GREEN: CHANGELOG entry follows the `[0.8.0]` format (Added / Tests / Notes sections)
  - [ ] GREEN: Apply-progress/finalize: confirm 783+ existing tests pass + new PR#1+PR#2 tests pass + `ruff check` clean + `flow` without any new subcommand is byte-identical to v0.6.0 behavior (REQ-50 non-breaking guarantees)
- **Commits:**
  1. `docs(release): CHANGELOG v0.8.1 entry + 6 SKILL.md skill catalog + CLI hooks + apply-finalize`

---

## Apply Batches (≤3 tasks OR ≤150 LOC prod per delegation)

Per-delegation batch ceiling from Engram #112 pattern (`apply-batches-split-into-6-tasks-per-delegation`). Default delegate runtime is ~15 min; larger batches TIMEOUT.

### PR#1 batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **A** | T1.1 + T1.2 + T1.3 | ~1450 | `PROMPT_REGISTRY` foundation + `.j2` files + `get_prompts_dir()` + `_env()` hoist + 4 inline constants migrated to thin wrappers — atomic foundation; 6 commits RED → GREEN → REFACTOR cycle; **TIMEOUT RISK BATCH** |
| **B** | T1.4 + T1.5 + T1.6 | ~1380 | `list_prompts`/`get_prompt` helpers + `register()` + `validate_catalog()` + `lint_prompts()` 5-category validator — registry extension |
| **C** | T1.7 + T1.8 + T1.9 | ~3380 | `render_prompt()` + `render_prompt_safe()` + BDD req45/46/47 (7 scenarios) + glue file + CHANGELOG + 6 SKILL.md hooks + spec bootstrap |

**Batch A risk mitigation:** at ~1450 LOC, batch A is the highest timeout risk (~4h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **A1** = T1.1 (PROMPT_REGISTRY scaffold) + T1.2 (prompts/ directory + .j2 files + _env() hoist) — ~800 LOC; library cohesion
- **A2** = T1.3 (4 inline constants migrated to thin wrappers) — ~250 LOC; migration-only work

If sub-agent reports progress as "PROMPT_REGISTRY scaffold + .j2 files landed, migration remaining", abort and launch A2 as continuation.

### PR#2 batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **D** | T2.1 + T2.2 + T2.3 | ~920 | `SkillCatalog` + 20 entries + `compute_checksum()` + frontmatter parser + sidecar I/O — **TIMEOUT RISK BATCH** |
| **E** | T2.4 + T2.5 + T2.6 | ~950 | `check_drift` + `update_checksums` + `init_checksums` + `flow prompts list/show/lint/check` CLI subcommands with 7 flags |
| **F** | T2.7 + T2.8 | ~500 | BDD req49/req50 (5 scenarios) + step glue extensions + CHANGELOG v0.8.1 + 6 SKILL.md skill-catalog/CLI hooks + apply-finalize |

**Batch D risk mitigation:** at ~920 LOC, batch D is the second-highest timeout risk (~2.5h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **D1** = T2.1 (`SkillCatalog` schema) + T2.2 (20 entries) — ~370 LOC; catalog-only work
- **D2** = T2.3 (compute_checksum + frontmatter parser + sidecar I/O) — ~300 LOC; checksum + I/O cohesion

If sub-agent reports progress as "SKILL_CATALOG schema + 20 entries landed, checksum helpers remaining", abort and launch D2 as continuation.

### Branch targeting

- **PR#1 → `main`.** Branch from `main`; merge to `main` after batch C completes + `uv run pytest` is green + 783+ existing tests pass.
- **PR#2 → `main`.** Branch from PR#1's merge commit (NOT from `main` pre-merge; per Engram #114 stacked-to-main pattern). Cherry-pick additive changes only. Merge to `main` after batch F completes + full PR#1 + PR#2 test suites pass + `ruff check` clean.
- **Squash merge** for both PRs (preserves linear history, single commit `feat: prompt-registry v0.8.0` + `feat: prompt-registry v0.8.1`).
- Each batch's commits land on the PR branch; PR merges after the final batch completes.
- **MANDATORY**: PR#1 merge to `main` MUST complete BEFORE PR#2 apply starts (stacked-to-main pattern #114).

---

## Patterns Honored

- **`apply-batches-split-into-6-tasks-per-delegation`** (Engram #112): each batch ≤3 tasks (PR#1 A=3, B=3, C=3; PR#2 D=3, E=3, F=2)
- **`apply-under-strict-tdd-grows-5-6x-beyond-forecast`** (#113): design ×6 multiplier is the project-specific band for prompt-registry (CLI-heavy change mirrors decision-code-linking precedent; full band per D-file breakdown)
- **`work-unit-commits`** skill: per-commit work-unit splits to mitigate 400-line review budget (6 work-unit commits per PR, each ≤400 LOC)
- **`stacked-to-main-requires-merging-prior-pr-before-next-apply`** (#114): MERGE PR#1 to `main` BEFORE launching PR#2 apply
- **`openspec/specs/` bootstrap pattern** (D12 from design): bootstrap `openspec/specs/prompt-registry/spec.md` as T1.9 in PR#1 batch C (mirrors change #6 observability T1.3)
- **Shared BDD glue file** (D11 from design): `tests/bdd/test_prompt_registry_steps.py` is shared across all 5 BDD features (req45..47 + req49/req50); PR#1 lands the foundation (~150 LOC), PR#2 extends (~250 more LOC)

---

## Open follow-ups for sdd-archive (after both PRs merge)

| # | Item | Owner |
|---|------|-------|
| 1 | Confirm `openspec/specs/prompt-registry/spec.md` is the project baseline pattern; retro-fill prior capability specs (`openspec/specs/observability/spec.md`, etc.) on a future change | sdd-archive |
| 2 | Bump `pyproject.toml` version `0.7.0` → `0.8.1` (matches the dual CHANGELOG entries; verify the `uv version` workflow) | sdd-archive |
| 3 | Verify `MEMORY.md` or AGENTS.md mentions `PROMPT_REGISTRY` + `flow prompts list/show/lint/check` workflow for future contributors | sdd-archive |
| 4 | Cross-impact: confirm all 6 prior changes (REQ-1..44) tests stay green; prompt-registry is purely additive (REQ-50 non-breaking guarantees; `prompt_fn=Callable` seam preserved) | sdd-archive |
| 5 | Update README to mention the new `~/.flow-engineering/prompt_checksums.json` sidecar + the 7 new `flow prompts` flags + the SKILL.md drift detection surface | sdd-archive |
| 6 | Consider follow-up changes for v1.1 deferred items: REQ-48 (golden regression tests), REQ-51 (prompt_renders.jsonl sink), REQ-52 (prompt observability counters), REQ-53 (docs/prompts.md), REQ-54 (min_sdd_skill_versions enforcement) | sdd-archive |
| 7 | Verify `_atomic_write_text` reuse: confirm `flow prompts check --update` sidecar write uses the same `tempfile + os.replace` pattern as observability T1.9; if not, factor into a shared `cli_io.py` helper on a future change | sdd-archive |
| 8 | Verify the 6 SKILL.md runtime updates landed correctly (manually inspect `~/.config/opencode/skills/sdd-*/SKILL.md` for "Prompt registry hook" + "Skill catalog hook" + "Flow prompts CLI hook" sections) | sdd-archive |

---

## Structured Metadata

- **status:** success
- **confidence:** high
- **total_tasks:** 17 (T1.1..T1.9 PR#1 + T2.1..T2.8 PR#2)
- **pr_split:** 2 chained PRs (PR#1 foundation + PR#2 discovery+CLI)
- **forecast_loc_production:** ~3243 (~1900 PR#1 + ~1343 PR#2)
- **forecast_loc_test:** ~6486 (~3800 PR#1 + ~2686 PR#2)
- **forecast_loc_grand_total:** ~9729
- **forecast_loc_realistic_x6:** ~19 458 (×6 multiplier applies to production only per design §"Strict-TDD ratio")
- **batches:** 6 (PR#1: A=3 + B=3 + C=3 = 9 tasks; PR#2: D=3 + E=3 + F=2 = 8 tasks)
- **pr1_batch_a_timeout_risk:** HIGH (~1450 LOC; mitigation = split into A1 + A2 if delegation hits 15-min ceiling)
- **pr2_batch_d_timeout_risk:** HIGH (~920 LOC; mitigation = split into D1 + D2 if delegation hits 15-min ceiling)
- **review_workload_forecast:**
  - `pr1_400_line_budget_risk`: high (~5700 LOC forecast, ~11 400 realistic; 6 work-unit commits per `work-unit-commits` convention)
  - `pr2_400_line_budget_risk`: medium (~4029 LOC forecast, ~8058 realistic; 5 work-unit commits per `work-unit-commits` convention)
  - `chained_prs_recommended`: yes (per proposal #201 + design #207 D11; ×6 TDD multiplier)
  - `decision_needed_before_apply`: no (chained-pr strategy is explicit in proposal #201)
- **strict_tdd:** on (RED → GREEN → REFACTOR per task; per `decision-code-linking` precedent)
- **bdd_feature_files:** 5 NEW (req45_prompt_registry, req46_prompt_render, req47_prompt_lint, req49_skill_catalog, req50_cli_prompts)
- **bdd_scenarios:** 12 (REQ-45:2 + REQ-46:3 + REQ-47:2 + REQ-49:2 + REQ-50:3)
- **out_of_scope_count:** 14 (REQ-48, REQ-51..54 v1.1 defers + 10 v2 defers)
- **file_created:** `C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\tasks.md`
- **next_recommended:** `sdd-apply prompt-registry PR#1 batch A` (T1.1 + T1.2 + T1.3, ~1450 LOC, ~25-30 min)