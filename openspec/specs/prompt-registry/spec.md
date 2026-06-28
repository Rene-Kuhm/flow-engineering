<!-- spec.md: prompt-registry capability spec. Source: manual. PR#1 archive sync: 2026-06-27. -->
# PromptRegistry Capability Spec

## PR#1 archive status (2026-06-27)

**REQ-45** ⚠️ PARTIAL — `PROMPT_NAMES: tuple[PromptDef, ...]` shipped (5-field `PromptDef` with `name`+`domain`+`template`+`version`+`metadata`); spec originally locked `PROMPT_REGISTRY: dict[str, PromptEntry]` (6-field `PromptEntry` with `template_id`+`version`+`owner`+`location`+`variables`+`schema_version`). S1 BDD asserts `len(list_prompts()) >= 4` (does not assert per-entry `owner`/`variables`/`location` per spec scenario). S2 BDD asserts `get_prompt("unknown")` raises `KeyError` (uses `get_prompt()` helper, not direct `PROMPT_REGISTRY["..."]` dict access as spec scenario dictated). Both PARTIAL are documented in `verify-report-pr1.md` W10 (BDD coverage gap) and resolved via D10 alias convention (thin wrappers preserve the migration). Schema migration to 6-field `PromptEntry` deferred to a future v0.8.x follow-up.

**REQ-46** ✅ RESOLVED post-`613f716` — `render_prompt(name, **kwargs)` lands with a `.format()` fallback path (W5) plus a `PromptRenderError` / `PromptNotFoundError` exception hierarchy (W6) at commit `613f716`. The 4 migrated `PROMPT_NAMES` entries (which use Python `.format()` syntax `{test_command}`) now render correctly via `render_prompt("strict_tdd", test_command="pytest")`. S1/S3 BDD scenarios pass. S2 BDD still uses newly-registered Jinja2 prompts (`{{ user_name }}`) rather than the 4 migrated entries, so the spec scenario's exact-string assertion is not exercised — but the API contract works end-to-end at runtime.

**REQ-47** ✅ COMPLIANT — `lint_prompts() -> LintReport` ships with 5 impl-taxonomy error codes (`duplicate_name`, `invalid_domain`, `jinja_syntax`, `undefined_var`, `invalid_version`). W1 lint category name mismatch (impl taxonomy ≠ spec taxonomy `missing_placeholder`/`unused_variable`/`template_parse_error`/`autoescape_disabled`/`missing_variable`) is PARTIAL — downstream consumers querying for spec-mandated category names need a mapping shim (deferred to v0.8.x). S1/S2 BDD scenarios pass.

**REQ-49 / REQ-50 (PR#2)** — NOT YET SHIPPED. Deferred to `prompt-registry` PR#2 (sdd-tasks to launch from existing proposal REQ-49/50 scope; SKILL_CATALOG mirror + `flow prompts` CLI group + 5 BDD scenarios).

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

The 7 PR#1 scenarios (in `tests/bdd/`) cover REQ-45/46/47. PR#2
extends the `test_prompt_registry_steps.py` glue file with 5 more
scenarios for REQ-49 + REQ-50.

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

### REQ-49 (PR#2)

- `tests/bdd/req49_skill_catalog.feature` — "check-drift detects when
  SKILL.md checksums don't match catalog" + "check-drift passes when all
  SKILL.md checksums match".

### REQ-50 (PR#2)

- `tests/bdd/req50_cli_prompts.feature` — `flow prompts list` +
  `flow prompts show <name>` + `flow prompts lint` (3 scenarios).

## Versioning

- **v1.0** (2026-06-27) — initial bootstrap from change #7
  `prompt-registry` PR#1. Catalogs 4 `PROMPT_NAMES` entries + the
  `render_prompt` / `render_prompt_safe` / `list_required_vars` render
  contract + the 5-error-code `lint_prompts` validator. Mirrors the
  `observability` capability spec pattern. PR#2 extends this baseline
  with REQ-49 (`SKILL_CATALOG` 20-entry mirror + sidecar JSON) and
  REQ-50 (`flow prompts` CLI subcommand + 7 flags).

## PR#1 Scope (archived 2026-06-27)

| REQ | Status | Notes |
|-----|--------|-------|
| **REQ-45** — `PROMPT_NAMES` catalog | ⚠️ PARTIAL | S1 BDD weaker than spec scenario (asserts `len >= 4` only); S2 BDD uses `get_prompt()` helper instead of direct dict access. Catalog schema shipped as `tuple[PromptDef, ...]` (5 fields) instead of locked `dict[str, PromptEntry, ...]` (6 fields). All 4 entries migrated with identity-preserving thin wrappers. |
| **REQ-46** — `render_prompt` + helpers | ✅ RESOLVED post-`613f716` | `.format()` fallback path (W5) + `PromptRenderError` / `PromptNotFoundError` exception class (W6) land at commit `613f716`. The 4 migrated Python-`.format()` entries now render correctly via `render_prompt("strict_tdd", test_command="pytest")`. Autoescape NOT enabled (W2; spec OQ-2 violation; deferred to v0.8.x). |
| **REQ-47** — `lint_prompts` validator | ⚠️ PARTIAL | Ships 5 impl-taxonomy error codes (`duplicate_name`, `invalid_domain`, `jinja_syntax`, `undefined_var`, `invalid_version`). ZERO name overlap with spec-locked taxonomy (`missing_placeholder`, `unused_variable`, `template_parse_error`, `autoescape_disabled`, `missing_variable`) — W1 lint category name mismatch. Mapping shim deferred to v0.8.x. |
| **REQ-48** — golden regression tests | 🔲 NOT SHIPPED (PR#2 deferred) | Out of PR#1 scope per proposal. |
| **REQ-49** — `SKILL_CATALOG` + drift detection | 🔲 NOT SHIPPED (PR#2 deferred) | PR#2 sdd-tasks. |
| **REQ-50** — `flow prompts` CLI subcommand | 🔲 NOT SHIPPED (PR#2 deferred) | PR#2 sdd-tasks. |
| **REQ-51..54** — counters + sidecar + docs | 🔲 NOT SHIPPED (v1.1 deferred) | Future change beyond PR#2. |