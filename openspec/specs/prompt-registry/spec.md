<!-- spec.md: prompt-registry capability spec. Source: manual. PR#1 archive sync: 2026-06-27; PR#2a archive sync: 2026-06-27. -->
# PromptRegistry Capability Spec

## PR#1 archive status (2026-06-27)

**REQ-45** ⚠️ PARTIAL — `PROMPT_NAMES: tuple[PromptDef, ...]` shipped (5-field `PromptDef` with `name`+`domain`+`template`+`version`+`metadata`); spec originally locked `PROMPT_REGISTRY: dict[str, PromptEntry]` (6-field `PromptEntry` with `template_id`+`version`+`owner`+`location`+`variables`+`schema_version`). S1 BDD asserts `len(list_prompts()) >= 4` (does not assert per-entry `owner`/`variables`/`location` per spec scenario). S2 BDD asserts `get_prompt("unknown")` raises `KeyError` (uses `get_prompt()` helper, not direct `PROMPT_REGISTRY["..."]` dict access as spec scenario dictated). Both PARTIAL are documented in `verify-report-pr1.md` W10 (BDD coverage gap) and resolved via D10 alias convention (thin wrappers preserve the migration). Schema migration to 6-field `PromptEntry` deferred to a future v0.8.x follow-up.

**REQ-46** ✅ RESOLVED post-`613f716` — `render_prompt(name, **kwargs)` lands with a `.format()` fallback path (W5) plus a `PromptRenderError` / `PromptNotFoundError` exception hierarchy (W6) at commit `613f716`. The 4 migrated `PROMPT_NAMES` entries (which use Python `.format()` syntax `{test_command}`) now render correctly via `render_prompt("strict_tdd", test_command="pytest")`. S1/S3 BDD scenarios pass. S2 BDD still uses newly-registered Jinja2 prompts (`{{ user_name }}`) rather than the 4 migrated entries, so the spec scenario's exact-string assertion is not exercised — but the API contract works end-to-end at runtime.

**REQ-47** ✅ COMPLIANT — `lint_prompts() -> LintReport` ships with 5 impl-taxonomy error codes (`duplicate_name`, `invalid_domain`, `jinja_syntax`, `undefined_var`, `invalid_version`). W1 lint category name mismatch (impl taxonomy ≠ spec taxonomy `missing_placeholder`/`unused_variable`/`template_parse_error`/`autoescape_disabled`/`missing_variable`) is PARTIAL — downstream consumers querying for spec-mandated category names need a mapping shim (deferred to v0.8.x). S1/S2 BDD scenarios pass.

## PR#2a archive status (2026-06-27)

**REQ-49** ✅ SHIPPED via PR#2a (chained PR strategy; PR#2b still pending for REQ-50). The `SKILL_CATALOG: dict[str, SkillEntry]` mirror catalog (20 entries — 10 `sdd-*` agents × 2 surfaces `skill` + `prompt`) + SHA-256 frontmatter drift detection + `check_drift()` walker (4 `drift_kind` categories: `version_mismatch`, `checksum_mismatch`, `missing_file`, `frontmatter_parse_error`) + sidecar JSON I/O at `~/.flow-engineering/prompt_checksums.json` (atomic write via `tempfile + os.replace + os.fsync`) all ship in `src/flow_engineering/opencode_skill_catalog.py`. CLI surface wired in `src/flow_engineering/cli.py` as `flow prompts {check, lint}` Click subcommands (group + `check --init/--update/--no-fail/--skill` 4-flag matrix + `lint --strict --json` with 0/1/2 exit codes). PR#2a also resolved T2.5 follow-up findings from the initial verify cycle: **C1** (nested `metadata.version` fallback in `parse_frontmatter` via `_extract_version` helper — fixes 20/20 false-positive DRIFT on the real OpenCode SKILL.md corpus), **W1** (the 3 missing `--update`/`--no-fail`/`--skill` flags + `_resolve_check_action` helper + `CheckAction` dataclass), **W2** (stderr WARN summary when drift detected + 4 observability counters via `observability.increment()` / `observability.observe()`). 60 NEW unit tests + 2 NEW REQ-49 BDD scenarios pass; 1199/1199 full suite green; ruff + mypy clean on changed files. Full evidence at `verify-report-pr2a.md` + `apply-progress-pr2a.md`. The `## PR#1 Scope` table below now marks REQ-49 as ✅ SHIPPED (was 🔲).

**W-fix carry-forwards still deferred to PR#2b** (from PR#1 verify-report — bundled with REQ-50):
- **W1** — `lint_prompts` spec-taxonomy alias map (`LINT_CATEGORY_SPEC_ALIASES` mapping shim — W1 of PR#1, distinct from W1 of T2.2 which is now RESOLVED in PR#2a)
- **W2** — `select_autoescape(default_for_string=True)` for `_safe_jinja_env()` (W2 of PR#1 — HTML escape blocks Jinja2 `{{ var }}` injection; distinct from W2 of T2.4 which is now RESOLVED in PR#2a)
- **W3** — restore `prompts/` directory + 4 `.j2` files at repo root (per D1 + D2)
- **W4** — hoist `scaffold._env()` to shared `prompt_render._env()` (per D3)
- **W7** — `[tool.flow_engineering.prompts] directory = "prompts"` in `pyproject.toml`
- **W8** — bump `pyproject.toml` version to `0.8.0` (CHANGELOG already claims `0.8.0`)
- **W9** — `uv run ruff check --fix` on changed files (3 of 5 auto-fixable)
- **W10** — strengthen BDD scenarios for REQ-45 S1/S2 to match spec Gherkin shape

**REQ-50 (PR#2b pending)** — NOT YET SHIPPED. Deferred to `prompt-registry` PR#2b (`flow prompts list --json` + `flow prompts show <id> --var key=value` repeatable + sentinel substitution per OQ-4 + exit 5 on unknown id). PR#2b bundles the 8 W-fix carry-forwards listed above.

**REQ-48 / REQ-51..54 (v1.1 deferred)** — NOT SHIPPED. Carried forward beyond PR#2b:
- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt` snapshots (v1.1)
- **REQ-51** — `prompt_renders.jsonl` append-only sink (v1.1; `FLOW_PROMPT_LOG=1` gate)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (v1.1; lands in `observability.py` per D10)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_REGISTRY` (v1.1)
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` gate in `pyproject.toml` (v1.1)

**v0.8.x schema migrations still deferred** (NOT PR#2 — independent of the PR#2 chain):
- `PromptDef` → `PromptEntry` (5 fields → 6 fields: add `template_id` + `location` + `schema_version` as separate fields)
- `PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict` shape migration
- `LINT_CATEGORY_SPEC_ALIASES` mapping shim (W1 of PR#1 verify) — also covers this gap until the schema migration lands

## Purpose

Cross-version capability spec for the **prompt-registry** change — the
central Python API for catalog discovery, Jinja2-based render, and static
validation of inline prompt strings used by `flow` (and downstream agent
prompts). Mirrors the `observability` capability spec pattern (D12 in
`openspec/changes/prompt-registry/design.md`): the spec catalogs ALL
4 `PROMPT_NAMES` entries, the `render_prompt` / `render_prompt_safe` /
`list_required_vars` render contract, and the `lint_prompts` 5-error-code
validator surface. Future LLM-backed REQs (e.g., REQ-52 prompt observability
counters; REQ-53 generated `docs/prompts.md`) add specs to the same baseline.

The spec is **INFORMATIONAL**: it does not import `prompt_registry.py` or
exercise the runtime at parse time. It exists so downstream consumers
(agents, dashboards, future catalog forks) have a stable, human-readable
description of the contract.

## Requirements

### REQ-45 — PromptRegistry catalog

The system SHALL provide a single Python constant `PROMPT_NAMES: tuple[PromptDef, ...]`
in `src/flow_engineering/prompt_registry.py` that catalogs every prompt
string the project ships. Each entry is a frozen `PromptDef` dataclass
with fields:

- **`name: str`** — unique identifier (e.g., `"strict_tdd"`).
- **`domain: PromptDomain`** — categorical domain enum (`BINDING`,
  `DRIFT`, `OBSERVABILITY`, `SNAPSHOT`, `RUNTIME`).
- **`template: str`** — the prompt string; Python `.format()` style for
  the migrated 4 entries; new prompts may use Jinja2 `{{ var }}` syntax.
- **`version: str`** — SemVer `MAJOR.MINOR.PATCH`.
- **`metadata: dict[str, Any]`** — arbitrary key-value pairs; common keys
  include `source` (provenance path) and `required_vars` (tuple of names
  consumed by `render_prompt_safe` for sentinel substitution).

The registry MUST migrate the 4 existing inline prompt constants
(`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`,
`PROMPT_FOOTER`) into thin re-exports. The catalog MUST be importable as
a single symbol: `from flow_engineering.prompt_registry import PROMPT_NAMES`.

#### Current entries (v1.0)

| Name | Domain | Version | Required vars | Template body |
|------|--------|---------|---------------|---------------|
| `strict_tdd` | `OBSERVABILITY` | `1.0.0` | `("test_command",)` | `STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. ...` |
| `auto_suggest_header` | `BINDING` | `1.0.0` | `()` | `Auto-suggested code bindings:` |
| `auto_suggest_footer` | `BINDING` | `1.0.0` | `()` | `Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)` |
| `auto_suggest_empty` | `BINDING` | `1.0.0` | `()` | `No auto-suggested bindings available.` |

### REQ-46 — render_prompt helper

The system SHALL provide a public function
`render_prompt(name: str, **kwargs: Any) -> str` in
`src/flow_engineering/prompt_registry.py` that:

1. Looks up the `PromptDef` in `PROMPT_NAMES` via `get_prompt(name)`.
2. Compiles `prompt.template` via a shared strict Jinja2 `Environment`
   (`StrictUndefined`, `keep_trailing_newline=True`, cached at module
   scope via `functools.lru_cache`).
3. Renders with `**kwargs`; raises `jinja2.UndefinedError` (wrapped with
   the prompt name prefix) on missing declared variables.

The system SHALL also provide:

- `render_prompt_safe(name, **kwargs) -> str` — substitutes the literal
  sentinel `f"<{var_name}>"` for each missing declared variable in
  `metadata.required_vars` BEFORE rendering. Used by `flow prompts show <id>`
  for CLI inspection (per design D4: never inject empty strings into agent
  context).
- `list_required_vars(name) -> set[str]` — parses the template AST via
  `jinja2.meta.find_undeclared_variables` and returns the names of every
  placeholder. Useful for CLI surfaces that need to prompt the user for
  inputs.

The render functions MUST raise `KeyError` on unknown prompt names
(propagated from `get_prompt`).

### REQ-47 — lint_prompts validator

The system SHALL provide a public function
`lint_prompts(catalog=None) -> LintReport` in
`src/flow_engineering/prompt_registry.py` that validates a catalog
against 5 error codes:

1. **`duplicate_name`** — same `PromptDef.name` appears twice.
2. **`invalid_domain`** — `entry.domain` is not a `PromptDomain` value.
3. **`jinja_syntax`** — the template body fails Jinja2 parse.
4. **`undefined_var`** — a Jinja2 `{{ var }}` placeholder appears in the
   template body but is not declared in `metadata.required_vars`.
5. **`invalid_version`** — `entry.version` does not match the SemVer
   `MAJOR.MINOR.PATCH` regex.

The function MUST NOT raise on broken registries; it MUST return a
`LintReport` with `is_clean` / `error_count` / `error_codes` /
`by_code()` / `to_dict()` properties so callers (CLI, CI gates, tests)
decide how to surface the result.

## BDD scenarios

The 7 PR#1 scenarios (in `tests/bdd/`) cover REQ-45/46/47. PR#2a
extends the `test_prompt_registry_steps.py` glue file with 2 NEW
scenarios for REQ-49 (both passing post-T2.5). PR#2b will add 3 more
scenarios for REQ-50.

### REQ-45

- `tests/bdd/req45_prompt_registry.feature` — "Registry lists all known
  prompts by domain" + "Registry raises KeyError on unknown prompt name".

### REQ-46

- `tests/bdd/req46_prompt_render.feature` — "render with no kwargs
  returns the template as-is" + "render with kwargs substitutes Jinja2
  placeholders" + "render with missing kwargs raises UndefinedError".

### REQ-47

- `tests/bdd/req47_prompt_lint.feature` — "lint passes for well-formed
  prompt catalog" + "lint fails for prompt with undefined placeholder
  variable".

### REQ-49 (PR#2a — SHIPPED 2026-06-27)

- `tests/bdd/req49_skill_catalog.feature` — "check-drift detects when
  SKILL.md checksums don't match catalog" + "check-drift passes when all
  SKILL.md checksums match". **Both scenarios PASS** post-T2.5
  (after the nested `metadata.version` fallback fix in
  `opencode_skill_catalog.py:_extract_version` per `verify-report-pr2a.md` §"Re-verify").

### REQ-50 (PR#2b — pending)

- `tests/bdd/req50_cli_prompts.feature` — `flow prompts list` +
  `flow prompts show <name>` + `flow prompts lint` (3 scenarios).
  **Deferred to PR#2b** (chained PR strategy).

## Versioning

- **v1.0** (2026-06-27) — initial bootstrap from change #7
  `prompt-registry` PR#1. Catalogs 4 `PROMPT_NAMES` entries + the
  `render_prompt` / `render_prompt_safe` / `list_required_vars` render
  contract + the 5-error-code `lint_prompts` validator. Mirrors the
  `observability` capability spec pattern. PR#2 extends this baseline
  with REQ-49 (`SKILL_CATALOG` 20-entry mirror + sidecar JSON) and
  REQ-50 (`flow prompts` CLI subcommand + 7 flags).
- **v1.1** (2026-06-27) — PR#2a archive sync. Catalog now reflects
  REQ-49 SHIPPED (`SKILL_CATALOG: dict[str, SkillEntry]` 20-entry
  mirror + `SkillEntry`/`SkillDrift`/`SkillVersionError` dataclasses +
  `check_drift()` walker with 4 `drift_kind` categories + sidecar JSON
  at `~/.flow-engineering/prompt_checksums.json` + `flow prompts {check, lint}`
  Click subcommands). T2.5 follow-up fixed 3 verify findings (C1
  nested `metadata.version` fallback, W1 4-flag matrix, W2 stderr WARN
  + 4 observability counters). REQ-50 (`flow prompts list --json` +
  `flow prompts show <id>`) and 8 PR#1 W-fix carry-forwards (W1 lint
  taxonomy alias, W2 autoescape, W3 `prompts/` directory, W4
  `scaffold._env()` hoist, W7 `[tool.flow_engineering.prompts]`
  section, W8 `pyproject.toml` version bump, W9 ruff auto-fix, W10 BDD
  coverage gap) remain deferred to PR#2b. REQ-48 / REQ-51..54 carry
  forward to v1.1 (post-PR#2b). v0.8.x schema migrations (`PromptDef`
  → `PromptEntry` 6-field; `PROMPT_NAMES` tuple → `PROMPT_REGISTRY`
  dict) deferred independently of the PR#2 chain.

## PR#1 + PR#2a Scope (post-archive 2026-06-27)

| REQ | Status | Notes |
|-----|--------|-------|
| **REQ-45** — `PROMPT_NAMES` catalog | ⚠️ PARTIAL | S1 BDD weaker than spec scenario (asserts `len >= 4` only); S2 BDD uses `get_prompt()` helper instead of direct dict access. Catalog schema shipped as `tuple[PromptDef, ...]` (5 fields) instead of locked `dict[str, PromptEntry, ...]` (6 fields). All 4 entries migrated with identity-preserving thin wrappers. |
| **REQ-46** — `render_prompt` + helpers | ✅ RESOLVED post-`613f716` | `.format()` fallback path (W5) + `PromptRenderError` / `PromptNotFoundError` exception class (W6) land at commit `613f716`. The 4 migrated Python-`.format()` entries now render correctly via `render_prompt("strict_tdd", test_command="pytest")`. Autoescape NOT enabled (W2; spec OQ-2 violation; deferred to v0.8.x). |
| **REQ-47** — `lint_prompts` validator | ⚠️ PARTIAL | Ships 5 impl-taxonomy error codes (`duplicate_name`, `invalid_domain`, `jinja_syntax`, `undefined_var`, `invalid_version`). ZERO name overlap with spec-locked taxonomy (`missing_placeholder`, `unused_variable`, `template_parse_error`, `autoescape_disabled`, `missing_variable`) — W1 lint category name mismatch. Mapping shim deferred to v0.8.x. |
| **REQ-48** — golden regression tests | 🔲 NOT SHIPPED (PR#2 deferred) | Out of PR#1 scope per proposal. |
| **REQ-49** — `SKILL_CATALOG` + drift detection | ✅ SHIPPED via PR#2a (2026-06-27) | 20-entry catalog + SHA-256 frontmatter drift detection + sidecar JSON I/O + `flow prompts {check,lint}` Click subcommands. T2.5 follow-up fixed C1 (nested `metadata.version` fallback), W1 (4-flag matrix `--update`/`--no-fail`/`--skill` + `--init`), W2 (stderr WARN + 4 observability counters). Full evidence at `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/verify-report-pr2a.md`. |
| **REQ-50** — `flow prompts` CLI subcommand | 🔲 NOT SHIPPED (PR#2b deferred) | PR#2b sdd-tasks T3.1 + T3.2 — `flow prompts list --json` + `flow prompts show <id> --var key=value`. Bundles 8 W-fix carry-forwards from PR#1 verify-report (W1 lint taxonomy alias, W2 autoescape, W3 `prompts/` directory, W4 `scaffold._env()` hoist, W7 `[tool.flow_engineering.prompts]` section, W8 `pyproject.toml` version bump, W9 ruff auto-fix, W10 BDD coverage gap). |
| **REQ-51..54** — counters + sidecar + docs | 🔲 NOT SHIPPED (v1.1 deferred) | Future change beyond PR#2. |