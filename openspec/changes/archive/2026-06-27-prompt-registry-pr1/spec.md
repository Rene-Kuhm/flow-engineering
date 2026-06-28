<!-- Spec: prompt-registry. Source: manual. Archived 2026-06-27 as PR#1 closeout. -->
# Spec: prompt-registry (PR#1 archived snapshot)

**Change:** `prompt-registry`
**Builds on:** `proposal.md` (Approach A — `PromptRegistry` class + JSON-backed catalog; 4 cooperating modules: `prompt_registry.py` / `prompt_render.py` / `prompt_lint.py` / `opencode_skill_catalog.py`; bootstraps `openspec/specs/prompt-registry/spec.md` capability catalog; 2 chained PRs)
**Date:** 2026-06-27
**Status:** SPECIFIED → ready for sdd-design

```yaml
status: success
confidence: high
change: prompt-registry
pr_split: 2 chained PRs (PR#1: REQ-45/46/47; PR#2: REQ-49/50)
total_reqs: 5
total_bdd_scenarios: 12
file_created: C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\spec.md
next_recommended: sdd-design prompt-registry
archived: 2026-06-27 (PR#1 closeout)
```

## PR#1 Scope (archived 2026-06-27)

**Shipped in PR#1** (foundation: catalog + render + lint):

- **REQ-45** — `PROMPT_NAMES` catalog with 4 migrated entries (PARTIAL: S1/S2 BDD weaker than spec scenarios; tuple/5-field schema instead of locked dict/6-field)
- **REQ-46** — `render_prompt` + `render_prompt_safe` + `list_required_vars` (RESOLVED post-`613f716`: `.format()` fallback + `PromptRenderError`/`PromptNotFoundError`)
- **REQ-47** — `lint_prompts()` + `LintReport` with 5 impl-taxonomy error codes (PARTIAL: impl category names ≠ spec taxonomy; mapping shim deferred)

**Deferred to PR#2** (discovery: SKILL.md mirror + CLI surface):

- **REQ-49** — `SKILL_CATALOG` mirror catalog + checksum drift detection (`opencode_skill_catalog.py`)
- **REQ-50** — `flow prompts {list,show,lint,check}` CLI subcommand group

**Deferred to v1.1** (future change beyond PR#2):

- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt`
- **REQ-51** — `prompt_renders.jsonl` append-only sink
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (REQ-52 lands in `observability.py` per D10)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_REGISTRY`
- **REQ-54** — `min_sdd_skill_versions` gate in `pyproject.toml`

See `archive-report.md` for full closeout details.

## Goal

`flow-engineering` has been quietly accumulating **prompt-shaped artifacts across three disconnected surfaces** without a unifying catalog. Today the codebase ships **4 inline prompt constants** (`STRICT_TDD_PROMPT` at `src/flow_engineering/strict_tdd.py:13` plus `EMPTY_PROMPT_TEXT` / `PROMPT_HEADER` / `PROMPT_FOOTER` at `src/flow_engineering/auto_suggest_code_refs.py:47-49`), **4 Jinja2 scaffolding templates** at `src/flow_engineering/templates/` (loaded via a private `_env()` in `scaffold.py:20` that is NOT exposed to any other module), and **10 OpenCode runtime SKILL.md agent prompts** at `~/.config/opencode/skills/sdd-*/SKILL.md` that drive the entire SDD cycle (used by `flow apply` / `flow verify` / `flow archive` via delegation) yet live **outside the repo** with no version pin, no checksum, and no drift detection. Four of nine user-facing CLI subcommands (`apply`, `verify`, `archive`, and the SKILL.md-running variant of `new`) delegate to sdd-* sub-agents whose prompts the repo cannot see. This change ships the **catalog + render + lint + CLI** surface that turns those three prompt worlds into a single, discoverable, versioned, golden-testable registry — analogous to the `VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` catalog pattern that change #6 ships for observability counters. As a one-time side benefit, change #7 formalizes the **mirror catalog** for the OpenCode SKILL.md runtime surface so that drift between `flow` and the agent prompts that drive the SDD cycle becomes detectable in CI rather than discoverable in a confused `flow apply` run three weeks later.

The registry surface lives in **4 new modules** (`prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`, `opencode_skill_catalog.py`) plus a **`flow prompts` CLI group** in `src/flow_engineering/cli.py` with 4 subcommands (`list`, `show <id>`, `lint`, `check`). The 4 existing inline prompt constants become **thin wrappers around `render_prompt()`** for v0.7.0 (per D.8 alias convention) and are removed in v0.8.0. The `prompt_fn=Callable` injection point at `engram_io.py:541` is preserved as-is. All existing 783 tests MUST pass; `flow` without any new subcommand is byte-identical to v0.6.0 behavior.

---

## Contract table (per-PR breakdown)

| PR | REQs | LOC forecast (production / test) | BDD scenarios |
|----|------|----------------------------------|--------------|
| **PR#1** — foundation: catalog + render + lint | REQ-45, REQ-46, REQ-47 | ~833 / ~2 260 forecast (realistic ~18 710 with ×6 TDD multiplier) | 7 |
| **PR#2** — discovery: SKILL.md mirror + CLI surface + spec bootstrap | REQ-49, REQ-50 | ~1 900 / ~3 800 forecast (realistic ~21 420 with ×6 TDD multiplier) | 5 |
| **Total** | **5 REQs** | **~3 243 / ~6 486 forecast** (realistic ~40 130 with ×6 TDD multiplier) | **12** |

**Realistic LOC multiplier rationale** — per `decision-code-linking` archive-report #119 S3, the strict-TDD ×6 multiplier maps a ~3 243 LOC forecast to ~18 710 realistic. The aggregate realistic estimate of ~40 130 reflects the combined BDD step-def growth (5 BDD feature files sharing `test_prompt_registry_steps.py` ~400 LOC step glue that absorbs the 5-6× multiplier across the surface). Per-PR work-unit commit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC).

---

## PR#1 — Foundation: `PromptRegistry` catalog + `render_prompt()` helper + `lint_prompts()` validator

### REQ-45: `PROMPT_REGISTRY: dict[str, PromptEntry]` — central catalog of all flow-engineering prompt artifacts

The system SHALL provide a single Python constant `PROMPT_REGISTRY: dict[str, PromptEntry]` in a new module `src/flow_engineering/prompt_registry.py` that maps `prompt_id` (a stable, kebab-or-snake-case identifier) to a frozen `PromptEntry` dataclass with the following fields:

- **`template_id: str`** — relative path to the `.j2` template file under the `prompts/` directory (without the `.j2` extension); for inline strings migrated from `STRICT_TDD_PROMPT` etc., this is the canonical `prompt_id` itself.
- **`version: str`** — semver of the entry (e.g., `"1.0.0"`); per-prompt versioning per D.3.
- **`owner: str`** — owner tag (e.g., `"flow/observability"`, `"flow/binding"`, `"flow/scaffold"`); mirrors the `owner` field convention from `VECTOR_COUNTER_NAMES` / `FEDERATED_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` catalogs in `observability.py`.
- **`location: str`** — absolute path to the template file resolved at import time; configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (default `<repo>/prompts/`).
- **`variables: tuple[str, ...]`** — declared Jinja2 variable names that this prompt accepts; the tuple MAY be empty for prompts with no variables (e.g., `auto_suggest_header`).
- **`schema_version: str`** — `PromptEntry` schema version (e.g., `"1.0"`); the registry has a single registry-wide `schema_version` constant for the `PromptEntry` shape itself; `lint_registry()` fails on schema-version mismatch.

The registry MUST migrate the 4 existing inline prompt constants:
1. `STRICT_TDD_PROMPT` (strict_tdd.py:13) → `PROMPT_REGISTRY["strict_tdd"]`
2. `EMPTY_PROMPT_TEXT` (auto_suggest_code_refs.py:47) → `PROMPT_REGISTRY["auto_suggest_empty"]`
3. `PROMPT_HEADER` (auto_suggest_code_refs.py:48) → `PROMPT_REGISTRY["auto_suggest_header"]`
4. `PROMPT_FOOTER` (auto_suggest_code_refs.py:49) → `PROMPT_REGISTRY["auto_suggest_footer"]`

The original inline constants in `strict_tdd.py` and `auto_suggest_code_refs.py` SHALL be preserved as **thin re-exports** that call `render_prompt("strict_tdd", test_command=...)` etc. for v0.7.0 (per D.8 alias convention), removed in v0.8.0. The `prompt_fn=Callable` injection point at `engram_io.py:541` MUST be preserved as-is (testable seam still works).

The registry MUST be `frozen=True` (i.e., entries cannot be mutated at runtime); mutation attempts raise `dataclasses.FrozenInstanceError`. The registry MUST be importable as a single symbol: `from flow_engineering.prompt_registry import PROMPT_REGISTRY`.

#### Scenario: Registry lists all known prompts by domain

```gherkin
Scenario: Registry lists all known prompts by domain
  Given the 4 existing inline prompt constants are migrated into PROMPT_REGISTRY
  When the user imports "from flow_engineering.prompt_registry import PROMPT_REGISTRY"
  Then PROMPT_REGISTRY is a dict with exactly 4 entries
  And "strict_tdd" maps to a PromptEntry with owner="flow/observability" and variables=("test_command",)
  And "auto_suggest_header" maps to a PromptEntry with owner="flow/binding" and variables=()
  And "auto_suggest_footer" maps to a PromptEntry with owner="flow/binding" and variables=()
  And "auto_suggest_empty" maps to a PromptEntry with owner="flow/binding" and variables=()
  And every entry's schema_version equals the registry-wide schema_version "1.0"
  And every entry's location points to an existing file under the configured prompts directory
```

#### Scenario: Registry raises KeyError on unknown prompt name

```gherkin
Scenario: Registry raises KeyError on unknown prompt name
  Given PROMPT_REGISTRY contains 4 migrated entries
  When the user accesses PROMPT_REGISTRY["nonexistent_prompt"]
  Then a KeyError is raised with the message "nonexistent_prompt" (or Python's default KeyError formatting)
  And no silent fallback to an empty string is returned
  And no AttributeError or ImportError is raised (the registry import itself succeeded)
```

---

### REQ-46: `render_prompt(prompt_id, **variables) -> str` — shared Jinja2 prompt-rendering helper

The system SHALL provide a public function `render_prompt(prompt_id: str, **variables: Any) -> str` in a new module `src/flow_engineering/prompt_render.py` that:

1. Looks up the `PromptEntry` in `PROMPT_REGISTRY`; raises `KeyError` (or a subclass `PromptRenderError`) on unknown `prompt_id`.
2. Loads the template from `entry.location` (a `.j2` file under the configured `prompts/` directory).
3. Renders the template via a shared Jinja2 `Environment` (hoisted out of `scaffold.py:_env()` per the proposal; `_env()` is preserved as a thin re-export for backwards compatibility).
4. Passes `**variables` to the template render; raises `jinja2.UndefinedError` (wrapped in `PromptRenderError` for clarity) when a declared `variables` member is missing.
5. Returns the rendered string with no trailing-newline mutation (mirrors `keep_trailing_newline=True` from the existing `_env()`).

The Jinja2 `Environment` SHALL be configured with `select_autoescape(enabled_extensions=(), default_for_string=True)` per D.2 — autoescape ALL string variables by default (defensive against untrusted variable substitution); BDD scenario REQ-46 S2 explicitly tests the autoescape case for `<` and `&` characters in `test_command`.

The system SHALL also provide `render_prompt_safe(prompt_id: str, **variables: Any) -> str` that:
- Replaces missing declared `variables` with a sentinel string `<{var_name}>` (per D.4: CLI inspection mode is informative; sentinel prevents silent empty-string injection into agent context).
- Used by `flow prompts show <id>` only; runtime callers MUST use `render_prompt()` for hard-fail behavior.

The system SHALL define `PromptRenderError(Exception)` as the base class for all render-related failures (unknown id, missing variable, template parse error, template render error). The `_env()` factory in `scaffold.py` MUST be preserved as a thin re-export from `prompt_render._env()`; no import cycle is introduced (refactor target: `prompt_render.py` owns the factory, `scaffold.py` imports it).

#### Scenario: render with no kwargs returns the template as-is

```gherkin
Scenario: render with no kwargs returns the template as-is
  Given PROMPT_REGISTRY has an entry "auto_suggest_header" with variables=()
  And the template at prompts/auto_suggest_header.j2 is "Auto-suggested code bindings:"
  When the user calls render_prompt("auto_suggest_header")
  Then the result equals "Auto-suggested code bindings:"
  And no Jinja2 UndefinedError is raised (no declared variables to satisfy)
  And the result string has no leading or trailing whitespace added by the renderer
```

#### Scenario: render with kwargs substitutes Jinja2 placeholders

```gherkin
Scenario: render with kwargs substitutes Jinja2 placeholders
  Given PROMPT_REGISTRY has an entry "strict_tdd" with variables=("test_command",)
  And the template at prompts/strict_tdd.j2 is "STRICT TDD MODE IS ACTIVE. Test runner: {{ test_command }}. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
  When the user calls render_prompt("strict_tdd", test_command="pytest")
  Then the result equals "STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
  And the {{ test_command }} placeholder is fully substituted
  And no Jinja2 markup characters remain in the output
```

#### Scenario: render with missing kwargs raises UndefinedError

```gherkin
Scenario: render with missing kwargs raises UndefinedError
  Given PROMPT_REGISTRY has an entry "strict_tdd" with variables=("test_command",)
  When the user calls render_prompt("strict_tdd") with no kwargs (test_command is missing)
  Then a PromptRenderError is raised
  And the underlying cause is jinja2.UndefinedError (or equivalent strict-mode undefined)
  And the error message references the missing variable name "test_command"
  And no empty-string fallback is silently substituted into the output
```

---

### REQ-47: `lint_prompts(registry) -> list[LintWarning]` — static validation of the prompt catalog

The system SHALL provide a public function `lint_prompts(registry: dict[str, PromptEntry] | None = None) -> list[LintWarning]` in a new module `src/flow_engineering/prompt_lint.py` that validates the registry against 5 warning categories:

1. **`missing_placeholder`** — A `{{ var }}` placeholder in the template body is not declared in the entry's `variables` tuple. Severity: `error`.
2. **`unused_variable`** — A declared `variables` member is not referenced by any `{{ var }}` placeholder in the template body. Severity: `warning`.
3. **`template_parse_error`** — The Jinja2 template at `entry.location` fails to parse (syntax error, unclosed tag, etc.). Severity: `error`.
4. **`autoescape_disabled`** — The shared Jinja2 `Environment` does NOT have autoescape enabled (sanity check; should never fire in production). Severity: `error`.
5. **`missing_variable`** — The template body references `{{ var }}` but `var` is NOT in `variables` AND not used by any other placeholder (subset of `missing_placeholder`, but tagged for the `flow prompts lint` user-facing message). Severity: `error`.

The function SHALL accept `None` as a default for `registry`, in which case it lints `PROMPT_REGISTRY` (the project-wide default). The return type is `list[LintWarning]` where `LintWarning` is a frozen dataclass with fields `prompt_id: str`, `category: str`, `message: str`, `line: int | None = None`. The function MUST NOT raise on broken registries; it MUST return a list of warnings and let the caller decide (CLI vs. pytest fixture).

Bundled as:
- `flow prompts lint` CLI subcommand (REQ-50) — surfaces warnings to stdout in `<prompt_id>: <category>: <message>` format; exits non-zero when `--strict` is given and any `error` category is present.
- `pytest` fixture `prompt_lint_clean` — asserts the registry lints clean in CI; failing the test build if any `error` category surfaces.

#### Scenario: lint passes for well-formed prompt catalog

```gherkin
Scenario: lint passes for well-formed prompt catalog
  Given the 4 PROMPT_REGISTRY entries are well-formed (placeholders match declared variables, templates parse, autoescape enabled)
  When the user calls lint_prompts(PROMPT_REGISTRY)
  Then the result is an empty list (no warnings)
  And no error or warning is raised by the lint function itself
  And the function completes in under 100ms for the 4-entry registry (sanity)
```

#### Scenario: lint fails for prompt with undefined placeholder variable

```gherkin
Scenario: lint fails for prompt with undefined placeholder variable
  Given a broken test registry with entry "broken" having variables=("test_command",) and template "{{ test_comand }}" (typo: missing 'm')
  When the user calls lint_prompts(broken_registry)
  Then the result is a list with exactly 1 LintWarning
  And the warning has prompt_id="broken" and category="missing_placeholder"
  And the warning message references the undefined variable name "test_comand"
  And the warning line number is set to the line in the template where the typo appears
  And no Jinja2 exception is raised by lint_prompts itself (it returns the warning instead)
```

---

### PR#1 acceptance criteria

- [ ] All 7 BDD scenarios (REQ-45 ×2, REQ-46 ×3, REQ-47 ×2) pass.
- [ ] `PROMPT_REGISTRY` is importable as a single symbol with 4 migrated entries; every entry has the required 6 fields populated.
- [ ] `render_prompt(prompt_id, **variables)` correctly substitutes Jinja2 placeholders; raises `PromptRenderError` on missing variable.
- [ ] `render_prompt_safe(prompt_id, **variables)` substitutes `<{var}>` sentinel for missing variables (used by `flow prompts show` in PR#2).
- [ ] `lint_prompts(PROMPT_REGISTRY)` returns an empty list for the 4-entry registry.
- [ ] `lint_prompts(broken_registry)` returns a `LintWarning` for each broken entry across all 5 warning categories (covered by unit tests).
- [ ] The 4 existing inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) are thin re-exports around `render_prompt()` for v0.7.0.
- [ ] `scaffold.py:_env()` is preserved as a thin re-export from `prompt_render._env()`; no import cycle is introduced.
- [ ] `prompt_fn=Callable` injection point at `engram_io.py:541` is preserved as-is (testable seam still works).
- [ ] All 783 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: every public helper (`PROMPT_REGISTRY`, `render_prompt`, `render_prompt_safe`, `lint_prompts`) has RED→GREEN→REFACTOR history in commit log.

### PR#1 files to touch

**Production (~833 LOC):**
- `src/flow_engineering/prompt_registry.py` (NEW): `PROMPT_REGISTRY`, `PromptEntry` dataclass, 4 migrated entries; `~120 prod LOC`
- `src/flow_engineering/prompt_render.py` (NEW): `render_prompt()`, `render_prompt_safe()`, `PromptRenderError`, shared Jinja2 `Environment` (hoisted from `scaffold.py`); `~150 prod LOC`
- `src/flow_engineering/prompt_lint.py` (NEW): `lint_prompts()`, `LintWarning` dataclass, 5 warning categories; `~80 prod LOC`
- `prompts/strict_tdd.j2` (NEW): Jinja2 version of `STRICT_TDD_PROMPT`; `~4 LOC`
- `prompts/auto_suggest_header.j2` (NEW): Jinja2 version of `PROMPT_HEADER`; `~2 LOC`
- `prompts/auto_suggest_footer.j2` (NEW): Jinja2 version of `PROMPT_FOOTER`; `~3 LOC`
- `prompts/auto_suggest_empty.j2` (NEW): Jinja2 version of `EMPTY_PROMPT_TEXT`; `~1 LOC`
- `src/flow_engineering/strict_tdd.py` (MODIFY): replace `STRICT_TDD_PROMPT` constant with `render_prompt("strict_tdd", test_command=cmd)` call; remove inline string (1-line wrapper for v0.7.0 per D.8 alias)
- `src/flow_engineering/auto_suggest_code_refs.py` (MODIFY): replace 3 inline constants with `render_prompt("auto_suggest_header", ...)` etc.; `format_suggestion_prompt()` delegates to registry
- `src/flow_engineering/scaffold.py` (MODIFY): refactor `_env()` to be shared via `prompt_render.py`; deprecate the local copy (thin re-export)

**Tests (~2 260 LOC):**
- `tests/unit/test_prompt_registry.py` (NEW): `PROMPT_REGISTRY` schema + 4 migrated entries; rendering tests; `~250 LOC`
- `tests/unit/test_prompt_render.py` (NEW): `render_prompt()` with variables, missing variable, template error, autoescape; `~300 LOC`
- `tests/unit/test_prompt_lint.py` (NEW): `lint_prompts()` with 5 warning categories; `~250 LOC`
- `tests/bdd/req45_prompt_registry.feature` (NEW): 2 BDD scenarios
- `tests/bdd/req46_prompt_render.feature` (NEW): 3 BDD scenarios
- `tests/bdd/req47_prompt_lint.feature` (NEW): 2 BDD scenarios

---

## PR#2 — Discovery: `SKILL_CATALOG` mirror + `flow prompts` CLI + `openspec/specs/prompt-registry/spec.md` capability bootstrap

### REQ-49: `SKILL_CATALOG: dict[str, SkillEntry]` — OpenCode runtime SKILL.md mirror catalog with checksum drift detection

The system SHALL provide a `SKILL_CATALOG: dict[str, SkillEntry]` in a new module `src/flow_engineering/opencode_skill_catalog.py` that mirrors the OpenCode runtime SKILL.md agent registry for the 10 sdd-* sub-agents (sdd-init, sdd-explore, sdd-propose, sdd-design, sdd-spec, sdd-tasks, sdd-apply, sdd-verify, sdd-archive, sdd-onboard). The `SkillEntry` frozen dataclass has fields:

- **`skill_name: str`** — e.g., `"sdd-apply"`.
- **`expected_version: str`** — minimum semver of the SKILL.md frontmatter `version:` field (e.g., `"3.0"`).
- **`expected_path: str`** — absolute path to the SKILL.md file (e.g., `~/.config/opencode/skills/sdd-apply/SKILL.md`); resolved at import time.
- **`last_verified_checksum: str`** — SHA-256 of the parsed YAML frontmatter dict (per D.5: frontmatter-only to avoid whitespace false positives); populated from the sidecar `~/.flow-engineering/prompt_checksums.json` (NEW).
- **`owner: str`** — typically `"gentleman-programming"`; mirrors the `owner` convention from `PROMPT_REGISTRY`.

The system SHALL provide a public function `check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]` that:
1. Walks the catalog (or `SKILL_CATALOG` when `None`).
2. For each entry, computes the SHA-256 of the parsed YAML frontmatter dict from the on-disk `expected_path` file (per D.5: frontmatter-only checksum).
3. Compares the computed checksum against `last_verified_checksum` from the sidecar JSON.
4. Returns a `list[SkillDrift]` (empty list = no drift). `SkillDrift` is a frozen dataclass with fields `skill_name: str`, `expected_version: str`, `on_disk_version: str`, `expected_checksum: str`, `on_disk_checksum: str`, `drift_kind: str` (`"version_mismatch"` | `"checksum_mismatch"` | `"missing_file"` | `"frontmatter_parse_error"`).
5. Does NOT auto-update the sidecar JSON; per D.9, auto-update is dangerous (silently accepts upstream changes that may break `flow`).

The system SHALL also provide:
- `update_checksums(catalog=None) -> int` — walks the catalog, computes fresh frontmatter checksums, writes them to the sidecar JSON; returns the count of entries updated. Opt-in via `flow prompts check --update`.
- `init_checksums(catalog=None) -> int` — bootstrap the sidecar JSON when it does not exist; opt-in via `flow prompts check --init`. Mirrors `--init` precedent from `flow projects init`.
- `SkillVersionError(Exception)` — raised by `flow apply` / `flow verify` / `flow archive` (REQ-54, deferred) when on-disk SKILL.md `version` is less than `expected_version`; the v0.7.0 surface only WARNs via the `flow prompts check` exit code; REQ-54 enforcement is a v1.1 follow-up.

The sidecar JSON at `~/.flow-engineering/prompt_checksums.json` has shape `{skill_name: {version: str, checksum: str, last_verified_at: str}}` and is created lazily on first `flow prompts check --init` run. Per D.6, the catalog covers BOTH `~/.config/opencode/skills/sdd-*/SKILL.md` (10 files) AND `~/.config/opencode/prompts/sdd/*.md` (10 files) for a total of 20 catalog entries.

#### Scenario: check-drift detects when SKILL.md checksums don't match catalog

```gherkin
Scenario: check-drift detects when SKILL.md checksums don't match catalog
  Given a SKILL_CATALOG with 20 entries (10 skills + 10 prompts)
  And a sidecar prompt_checksums.json recording stale checksums (e.g., sdd-apply last_verified=abc123)
  And the on-disk ~/.config/opencode/skills/sdd-apply/SKILL.md has been edited since last verification (current frontmatter checksum=def456)
  When the user calls check_drift(SKILL_CATALOG)
  Then the result is a list with at least 1 SkillDrift entry
  And the drift entry has skill_name="sdd-apply" and drift_kind="checksum_mismatch"
  And the drift entry's expected_checksum equals the stale value (abc123)
  And the drift entry's on_disk_checksum equals the current value (def456)
  And the function does NOT raise; it returns the list for the caller (CLI) to surface
```

#### Scenario: check-drift passes when all SKILL.md checksums match

```gherkin
Scenario: check-drift passes when all SKILL.md checksums match
  Given a SKILL_CATALOG with 20 entries (10 skills + 10 prompts)
  And a freshly updated sidecar prompt_checksums.json where every entry's checksum matches the current on-disk frontmatter
  When the user calls check_drift(SKILL_CATALOG)
  Then the result is an empty list
  And no SkillDrift entries are returned
  And the function completes in under 1 second for the 20-entry catalog
  And the function does NOT raise; the empty list is the "clean state" signal
```

---

### REQ-50: `flow prompts {list, show, lint, check}` — CLI surface for prompt discovery + inspection

The system SHALL extend the existing `flow` CLI with a new `flow prompts` Click group containing 4 subcommands:

- **`flow prompts list [--json]`** — prints a table of every entry in `PROMPT_REGISTRY` with columns `{prompt_id, version, owner, location}`. The default output is human-readable text; `--json` emits a flat dict (mirrors `flow metrics --json` precedent per REQ-8). When `PROMPT_REGISTRY` has 4 entries, the table is grouped by `owner` (`flow/observability` for `strict_tdd`, `flow/binding` for the 3 auto-suggest entries).
- **`flow prompts show <prompt_id> [--var key=value] ...`** — renders the prompt with the given variables; uses `render_prompt_safe()` so missing declared variables get a `<{var}>` sentinel (per D.4). The `--var` flag is repeatable (`--var test_command=pytest --var foo=bar`). The output includes the metadata header (`prompt_id`, `version`, `owner`, `variables`) followed by the rendered template and a footer showing the render source and autoescape status. Exits non-zero with exit code 5 when `<prompt_id>` is not in `PROMPT_REGISTRY`.
- **`flow prompts lint [--strict]`** — runs `lint_prompts(PROMPT_REGISTRY)`; prints `<prompt_id>: <category>: <message>` lines to stdout; exits 0 when no warnings; exits 1 when any `warning` category is present; exits 2 when any `error` category is present OR when `--strict` is given and any `warning` is present (mirrors `flow drift --strict` precedent).
- **`flow prompts check [--update] [--no-fail] [--init] [--skill <name>]`** — runs `check_drift(SKILL_CATALOG)`; prints `<skill_name>: <version>: <status>` lines where status is `OK` / `DRIFT` / `MISSING` / `PARSE_ERROR`. Exits 0 when no drift, 1 when any drift detected. The `--update` flag calls `update_checksums()` to refresh the sidecar (opt-in per D.9). The `--no-fail` flag suppresses non-zero exit on drift (CI compat per D.5). The `--init` flag calls `init_checksums()` to bootstrap the sidecar when missing. The `--skill <name>` flag limits the check to one entry (debugging).

The new `flow prompts` CLI group is opt-in — `flow` without any new subcommand is byte-identical to v0.6.0 behavior. The new flags (`--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`) are all additive; no existing flag changes meaning.

#### Scenario: `flow prompts list` shows all registered prompts grouped by domain

```gherkin
Scenario: `flow prompts list` shows all registered prompts grouped by domain
  Given PROMPT_REGISTRY has 4 entries (1 flow/observability, 3 flow/binding)
  When the user runs "flow prompts list"
  Then stdout contains a header line "prompt_id                  version  owner                location"
  And stdout contains a row for "strict_tdd" with version="1.0.0" and owner="flow/observability"
  And stdout contains a row for "auto_suggest_header" with version="1.0.0" and owner="flow/binding"
  And stdout contains a row for "auto_suggest_footer" with version="1.0.0" and owner="flow/binding"
  And stdout contains a row for "auto_suggest_empty" with version="1.0.0" and owner="flow/binding"
  And stdout contains a footer line "4 prompt entries"
  And the command exits 0
```

#### Scenario: `flow prompts show <name>` renders the prompt with kwargs

```gherkin
Scenario: `flow prompts show <name>` renders the prompt with kwargs
  Given PROMPT_REGISTRY has an entry "strict_tdd" with variables=("test_command",)
  When the user runs "flow prompts show strict_tdd --var test_command=pytest"
  Then stdout contains a "prompt_id:" line with "strict_tdd"
  And stdout contains a "version:" line with "1.0.0"
  And stdout contains a "variables:" line with "test_command: pytest"
  And stdout contains the rendered string "STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
  And stdout contains a footer line showing the render source path and "autoescape=on"
  And the command exits 0
```

#### Scenario: `flow prompts lint` exits non-zero when catalog has validation errors

```gherkin
Scenario: `flow prompts lint` exits non-zero when catalog has validation errors
  Given a broken test PROMPT_REGISTRY (patched via test fixture) with 1 entry having a missing_placeholder warning
  When the user runs "flow prompts lint" (against the broken registry)
  Then stdout contains a line "broken: missing_placeholder: undefined variable 'test_comand'"
  And the command exits with code 2 (error category)
  And no traceback is printed to stderr
  And the exit code is 0 only when the registry lints clean (verified by a separate scenario)
```

---

### PR#2 acceptance criteria

- [ ] All 5 BDD scenarios (REQ-49 ×2, REQ-50 ×3) pass.
- [ ] `SKILL_CATALOG` covers all 20 entries (10 SKILL.md + 10 prompts/sdd/*.md) with SHA-256 frontmatter checksums.
- [ ] `check_drift(SKILL_CATALOG)` returns an empty list when all on-disk checksums match the sidecar.
- [ ] `flow prompts list` prints a table of all 4 entries grouped by `owner`.
- [ ] `flow prompts show strict_tdd --var test_command=pytest` renders the expected string with autoescape footer.
- [ ] `flow prompts lint` exits 0 on clean registry, exits 2 on `error` category, exits 1 on `warning` category.
- [ ] `flow prompts check` walks the catalog, SHA-256s each on-disk SKILL.md frontmatter, reports drift; `--update` flag refreshes the sidecar (opt-in per D.9).
- [ ] `flow prompts check --init` bootstraps the sidecar when it does not exist.
- [ ] `flow prompts check --no-fail` exits 0 even on drift (CI compat per D.5).
- [ ] `flow prompts check --skill sdd-apply` limits the check to one entry (debugging).
- [ ] `openspec/specs/prompt-registry/spec.md` (NEW) exists and catalogs all 4 PROMPT_REGISTRY entries + 20 SKILL_CATALOG entries + the SKILL.md mirror contract.
- [ ] `flow` without any new subcommand is byte-identical to v0.6.0 behavior; no existing flag changes meaning.
- [ ] All 783 existing tests + 7 PR#1 BDD tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: every public helper (`SKILL_CATALOG`, `check_drift`, `update_checksums`, `init_checksums`, `flow prompts {list, show, lint, check}`) has RED→GREEN→REFACTOR history in commit log.

### PR#2 files to touch

**Production (~1 900 LOC):**
- `src/flow_engineering/opencode_skill_catalog.py` (NEW): `SKILL_CATALOG`, `SkillEntry` dataclass, checksum verification, frontmatter parsing, `check_drift()`, `update_checksums()`, `init_checksums()`, `SkillVersionError`; `~120 prod LOC`
- `src/flow_engineering/cli.py` (MODIFY): `flow prompts` Click group + 4 subcommands (`list`, `show <id>`, `lint`, `check`) with all flags; `~150 prod LOC delta`
- `openspec/specs/prompt-registry/spec.md` (NEW): capability spec cataloging all 4 PROMPT_REGISTRY entries + 20 SKILL_CATALOG entries + the SKILL.md mirror contract + the `flow prompts` CLI surface contract; `~150 LOC`; bootstraps `openspec/specs/prompt-registry/` baseline (resolves the prompt-registry catalog deferral)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (MODIFY): prompt-registry hook prose referencing REQ-45 PROMPT_REGISTRY for prompt discovery; `~150 LOC` runtime-only

**Tests (~3 800 LOC):**
- `tests/unit/test_opencode_skill_catalog.py` (NEW): `SKILL_CATALOG` + checksum + drift detection (mock SKILL.md files); `~300 LOC`
- `tests/unit/test_cli_prompts.py` (NEW): full CLI surface coverage for `flow prompts list/show/lint/check` (all 9 flags); `~400 LOC`
- `tests/bdd/req49_skill_catalog.feature` (NEW): 2 BDD scenarios
- `tests/bdd/req50_cli_prompts.feature` (NEW): 3 BDD scenarios
- `tests/bdd/test_prompt_registry_steps.py` (NEW): pytest-bdd step glue shared across all 5 BDD features (`req45`, `req46`, `req47`, `req49`, `req50`); `~400 LOC`

---

## Out of Scope (deferred)

The following are explicitly out of scope for change #7 and belong to named follow-ups (mirrors the `vector-semantic-search` and `cross-project-federation` deferral patterns):

- **REQ-48 — Golden regression tests** — `tests/golden/prompts/<prompt_id>.txt` snapshots for every `PROMPT_REGISTRY` entry; `render_prompt(prompt_id, **canonical_variables)` must equal the snapshot. Defer to v1.1; bundle into PR#1 if scope allows.
- **REQ-51 — `prompt_renders.jsonl` append-only sink** — `~/.flow-engineering/prompt_renders.jsonl` parallels `metrics.jsonl`; opt-in via `FLOW_PROMPT_LOG=1`. Defer to v1.1.
- **REQ-52 — Prompt observability counters** — `prompts_render_total{prompt_id, version}`, `prompts_render_ms`, `prompts_render_failed_total{reason=missing_var|template_error|autoescape_blocked}`. Per D.10, when these land, add them to the existing `observability.py` catalog (not a new module). Defer to v1.1 (bundles with REQ-51).
- **REQ-53 — `docs/prompts.md` generated from `PROMPT_REGISTRY`** — flat list of every entry with `{prompt_id, purpose, where it appears, example output}`; cross-linked from `flow prompts show <id>`. Defer to v1.1.
- **REQ-54 — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`** — `flow apply` / `verify` / `archive` assert on startup that the on-disk SKILL.md `version` is >= the minimum; raises `SkillVersionError` (defined in REQ-49 for v0.7.0) with a remediation message. Could bundle into PR#2 if scope allows; otherwise defer to v1.1.
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

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req45_prompt_registry.feature` | NEW | REQ-45 | 2 |
| `tests/bdd/req46_prompt_render.feature` | NEW | REQ-46 | 3 |
| `tests/bdd/req47_prompt_lint.feature` | NEW | REQ-47 | 2 |
| `tests/bdd/req49_skill_catalog.feature` | NEW | REQ-49 | 2 |
| `tests/bdd/req50_cli_prompts.feature` | NEW | REQ-50 | 3 |
| **Total BDD scenarios** | | | **12** |

Step definitions land in `tests/bdd/test_prompt_registry_steps.py` (NEW; pytest-bdd glue per file). The per-REQ scenario counts match the task brief verbatim (REQ-45: 2, REQ-46: 3, REQ-47: 2, REQ-49: 2, REQ-50: 3 — totaling 12). Edge cases that do NOT fit the BDD scope are covered by unit tests:
- REQ-45: registry entry missing a required field (e.g., empty `variables` for a template with placeholders) — `tests/unit/test_prompt_registry.py`
- REQ-46: autoescape blocks HTML injection in `test_command` — `tests/unit/test_prompt_render.py::TestAutoescape`
- REQ-46: `render_prompt_safe()` sentinel substitution — `tests/unit/test_prompt_render.py::TestSafeRender`
- REQ-47: 5 warning categories individually — `tests/unit/test_prompt_lint.py::TestCategories`
- REQ-49: `init_checksums` bootstrap when sidecar missing — `tests/unit/test_opencode_skill_catalog.py::TestInit`
- REQ-49: `update_checksums` writes new sidecar — `tests/unit/test_opencode_skill_catalog.py::TestUpdate`
- REQ-50: `flow prompts show <unknown>` exits with code 5 — `tests/unit/test_cli_prompts.py::TestShowUnknownId`
- REQ-50: `flow prompts lint --strict` on warnings exits 1 — `tests/unit/test_cli_prompts.py::TestLintStrict`

This mirrors the `graph-snapshots` split where the sha256-tamper detection (REQ-30 edge case) and `--keep-last=0` two-flag safety gate (REQ-34) stayed at the unit-test layer.

---

## Traceability matrix

| REQ | Source | Notes |
|-----|--------|-------|
| REQ-45 | proposal #201 §"Architecture piece 1" + explore #198 §"Gap 1" | `src/flow_engineering/prompt_registry.py` with `PROMPT_REGISTRY: dict[str, PromptEntry]`; migrates 4 existing inline prompts (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) |
| REQ-46 | proposal #201 §"Architecture piece 2" + explore #198 §"Gap 2" | `src/flow_engineering/prompt_render.py` with `render_prompt()` + `render_prompt_safe()` + `PromptRenderError`; shared Jinja2 `Environment` hoisted from `scaffold.py:_env()`; adds `prompts/` directory at repo root |
| REQ-47 | proposal #201 §"Architecture piece 3" + explore #198 §"Gap 3" | `src/flow_engineering/prompt_lint.py` with `lint_prompts()` + `LintWarning` dataclass + 5 warning categories; bundled as `flow prompts lint` and `pytest` fixture |
| REQ-49 | proposal #201 §"Architecture piece 4" + explore #198 §"Gap 5" | `src/flow_engineering/opencode_skill_catalog.py` with `SKILL_CATALOG: dict[str, SkillEntry]`; 20 entries (10 SKILL.md + 10 prompts/sdd/*.md); SHA-256 frontmatter checksums; sidecar `~/.flow-engineering/prompt_checksums.json`; bundled as `flow prompts check` |
| REQ-50 | proposal #201 §"CLI surface" + explore #198 §"Gap 6" | `flow prompts list`, `flow prompts show <id>`, `flow prompts lint`, `flow prompts check`; mirrors `flow metrics` surface pattern; 9 new flags (`--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`) |

---

## Open Questions (carry-forward to sdd-design)

The 10 questions below MUST be resolved in the design phase before `sdd-tasks` locks the implementation contract:

1. **`prompts/` directory location** (D.1) — does the new directory live at repo root (`<repo>/prompts/`) or inside the package (`src/flow_engineering/prompts/`)? **Recommend** repo root (mirrors `openspec/` first-class artifact convention; allows future external tools to read prompt files without importing `flow_engineering`). Confirm the path matches the project's existing convention for non-Python content directories (the `templates/` directory lives inside the package — should the new directory follow suit or break the pattern?).
2. **Jinja2 autoescape scope** (D.2) — enable autoescape unconditionally or only for HTML/XML extensions? **Recommend** `select_autoescape(enabled_extensions=(), default_for_string=True)` (autoescape ALL string variables by default; defensive; prevents control-character injection). Document the choice in `openspec/specs/prompt-registry/spec.md`. Confirm that legitimate `{{ var }}` substitutions don't contain `<` or `&` in the existing 4 inline prompts (audit before design phase locks).
3. **Prompt schema versioning** (D.3) — per-prompt `version: semver` or registry-wide single version? **Recommend** per-prompt `version: semver` in `PromptEntry` (allows independent evolution of each prompt); registry has its own `schema_version` (e.g., `"1.0"`) for the `PromptEntry` shape itself. Lint fails on `schema_version` mismatch.
4. **`flow prompts show` missing-variable behavior** (D.4) — fail with error, render with empty substitution, or render with sentinel? **Recommend** (c) sentinel for `flow prompts show` (CLI is for inspection; sentinel like `<test_command>` is informative); (a) hard fail for runtime `render_prompt()` (must NOT silently inject empty strings into agent context). Confirm the sentinel format matches the project's existing convention (no precedent — design phase picks).
5. **SKILL.md checksum strategy** (D.5) — full file SHA-256 or frontmatter-only (parse YAML, hash the dict)? **Recommend** frontmatter-only (ignores whitespace drift in the body; semantic version metadata lives in frontmatter). Trade-off: loses body-change detection. Add `--strict` flag for paranoid mode (full file checksum). Confirm the YAML parser handles the SKILL.md frontmatter shape correctly (audit 10 SKILL.md files before design phase).
6. **SKILL_CATALOG coverage** (D.6) — include `prompts/sdd/*.md` (10 files) in addition to `skills/sdd-*/SKILL.md` (10 files), or just one? **Recommend** covering BOTH — they are maintained separately per OpenCode convention and the user wants drift detection on both. Total: 20 catalog entries (10 SKILL.md + 10 prompt.md). Confirm the user wants both surfaces covered (the explore notes "they appear to have overlapping content" — verify before locking).
7. **`.j2` metadata sidecars** (D.7) — prompt metadata in `.j2` YAML frontmatter, or Python-only? **Recommend** Python-only for v1 (matches existing `scaffold.py` template convention; no YAML parser round-trip needed). Defer frontmatter-style `.j2` to v1.1 if external tooling needs it. Confirm the v1 Python-only approach matches the project's existing convention (the existing 4 `.j2` files have NO frontmatter — extension would be a new pattern).
8. **`STRICT_TDD_PROMPT` migration strategy** (D.8) — silent replace, deprecation warning, or alias for one release? **Recommend** (c) alias for v0.7.0 (thin wrapper that calls `render_prompt("strict_tdd", ...)`), remove in v0.8.0. Standard deprecation pattern. Avoids breaking external imports.
9. **`flow prompts check --update` auto-update** (D.9) — report only, report + ask, or report + auto-update? **Recommend** (b) — report + ask `--update` flag. Auto-update would be dangerous (silently accepts upstream changes that may break `flow`). Confirm the explicit-flag pattern matches user mental model (i.e., `--update` is opt-in, never default).
10. **Coordination with change #6 observability counters** (D.10) — REQ-52 prompt counters (deferred to v1.1) — added to `observability.py` catalog, separate `prompt_registry` module, or deferred to change #6 extension? **Recommend** (a) — when REQ-52 lands, add 3 prompt counters (`prompts_render_total`, `prompts_render_ms`, `prompts_render_failed_total`) to the existing `observability.py` catalog. Change #6 ships the read-side (`flow metrics`); change #7 ships the write-side for prompt counters. No new module. Confirm the cross-change coordination is acceptable (change #7 must not block on change #6 counter additions).

---

## Risks (carry-forward from proposal §6)

The 12 risks below were raised in the proposal. Those that remain unmitigated after the spec phase are flagged here; mitigations are noted inline:

| # | Risk | Likelihood | Status after spec phase |
|---|---|---|---|
| 1 | change #6 (observability) does not archive before change #7 apply starts → `PROMPT_REGISTRY` mirrors an unstable catalog pattern | HIGH | UNMITIGATED — orchestrator must coordinate: change #6 ARCHIVE before change #7 APPLY. PR#1 SPEC references the observability pattern by name only and is resilient to additions (catalogs are independent modules). |
| 2 | PR#1 cumulative realistic ~3 600 LOC > 400-line review budget; reviewers lose context | MED | MITIGATED by per-commit work-unit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC). |
| 3 | Migration of `STRICT_TDD_PROMPT` / `PROMPT_HEADER` / `PROMPT_FOOTER` / `EMPTY_PROMPT_TEXT` breaks existing tests that hardcode the prompt strings | MED | MITIGATED — Run all 783 tests after migration; v0.7.0 ships thin wrapper re-exports (per D.8 alias) so external imports keep working; update test fixtures to use `render_prompt()` + golden snapshots; follow REQ-48 in v1.1. |
| 4 | The SKILL.md checksum drift detection (REQ-49) produces false positives on whitespace-only changes | MED | MITIGATED — Use frontmatter-only checksum per D.5 (parse YAML, hash the dict, ignore body whitespace); add `--strict` flag for paranoid mode (full file checksum); BDD scenario GIVEN whitespace-only diff THEN no drift. |
| 5 | BDD step def file growth precedent: decision-code-linking S3 forecast 30 LOC → actual 621 LOC (5-6× multiplier) | MED | MITIGATED — Forecast absorbs the multiplier (`test_prompt_registry_steps.py` ~400 LOC; realistic ~2 400); per-REQ step files if size exceeds 400 LOC. |
| 6 | Adding `prompts/` at repo root conflicts with future external tooling that expects `src/flow_engineering/prompts/` | LOW | MITIGATED — Document the path in `openspec/specs/prompt-registry/spec.md`; make it configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (default `<repo>/prompts/`). |
| 7 | The Jinja2 autoescape decision (D.2) blocks legitimate `{{ var }}` substitution that contains characters like `<` or `&` | LOW | MITIGATED — Use `select_autoescape(default_for_string=True)` which auto-escapes string variables; BDD scenario REQ-46 S2 covers the case. |
| 8 | `flow prompts check` exit code (non-zero on drift) breaks existing CI pipelines that run `flow apply` automatically | LOW | MITIGATED — Default is non-zero on drift; add `--no-fail` flag for CI compatibility; document in `--help` and `openspec/specs/prompt-registry/spec.md`. |
| 9 | The OpenCode SKILL.md files at `~/.config/opencode/` are user-managed (not in repo); if the user has manually edited them, drift detection fires unexpectedly | LOW | MITIGATED — Document the expected state in `openspec/specs/prompt-registry/spec.md`; provide `flow prompts check --init` to bootstrap the sidecar; per D.9 use `--update` flag (manual, not auto) for catalog refresh. |
| 10 | The `prompts/` directory at repo root conflicts with the `~/.flow-engineering/prompts/` user config directory (parallel naming) | LOW | MITIGATED — Per D.7 + D.9, use `~/.flow-engineering/prompt_checksums.json` (not `prompts/`) for the sidecar; repo-side uses `prompts/` (`.j2` files only); documented in spec. |
| 11 | Adding the Jinja2 env shared between `scaffold.py` and `prompt_render.py` creates an import cycle | LOW | MITIGATED — Refactor `_env()` to live in `prompt_render.py` (not `scaffold.py`); `scaffold.py` imports it; no cycle. BDD scenario GIVEN `render_prompt("scaffold_change_yaml", name="x")` THEN output equals scaffold.py path. |
| 12 | The strict-TDD ×6 LOC multiplier (per `decision-code-linking` S3) means the realistic forecast is ~18 710 LOC vs the 3 243 forecast → 2 chained PRs are MANDATORY | INFO | ACCEPTED — Already reflected in PR split (PR#1 ~3 600 LOC realistic; PR#2 ~3 900 LOC realistic); per-PR scope is well-defined. |

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | 4 inline prompts (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) migrated into `PROMPT_REGISTRY`; `prompt_fn=Callable` seam at `engram_io.py:541` preserved | Compatible (consumes the migration; seam preserved) |
| `decision-reality-drift` (shipped v0.3.0) | Drift path unaffected — no prompts in drift surface | Compatible (no intersection) |
| `vector-semantic-search` (shipped v0.4.0) | `VECTOR_COUNTER_NAMES` catalog at `observability.py:85` is the structural template for `PROMPT_REGISTRY`; no shared mutable state | Compatible (no intersection) |
| `cross-project-federation` (shipped v0.5.0) | `FEDERATED_COUNTER_NAMES` catalog at `observability.py:104` is the second template; "federated prompt registry" deferred per explore C.4 | Compatible (no intersection) |
| `graph-snapshots` (change #5, ARCHIVED) | `SNAPSHOT_COUNTER_NAMES` catalog at `observability.py:124` is the third template; 6-SKILL.md hand-edit pattern (`CHANGELOG.md:13`) formalized by REQ-49 | Compatible (REQ-49 supersedes the hand-edit pattern with a catalog) |
| `observability` (change #6, IN PROGRESS) | `PROMPT_REGISTRY` mirrors the observability catalog pattern; REQ-52 prompt counters (deferred) will land in `observability.py` per D.10 | MUST ARCHIVE BEFORE change #7 apply; coordinate via orchestrator |
| `prompt-registry` (#7, this change) | Standalone; no outbound deps | Self |

**Unblocks**: discoverable prompt surface for the 4 inline + 4 Jinja2 + 10 OpenCode runtime prompts already shipped (REQ-45 + REQ-49); linted prompt registry catching typos at CI time (REQ-47); CLI surface for prompt inspection (REQ-50); manifest-driven SKILL.md drift detection replacing the 6-file hand-edit pattern from `graph-snapshots` (REQ-49); and — as a foundation — a deterministic, versioned, regression-tested prompt surface that future LLM-backed REQs (e.g., "REQ-NN: `flow drift --llm-summary`" or "REQ-MM: auto-prompt-tuning") can plug into.

**Constrains**: any future change that adds a prompt MUST either add it to `PROMPT_REGISTRY` (with `version`, `owner`, `variables`, `schema_version`) or update the `PROMPT_REGISTRY` schema; the existing inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) are thin wrappers for v0.7.0 only and MUST be removed in v0.8.0 (per D.8 alias convention); the flat text default of `flow metrics` is unaffected (no changes to the observability CLI surface).

---

## References

- Explore: `openspec/changes/prompt-registry/explore.md` (Engram `sdd/prompt-registry/explore` #198 — full option matrix, 10 user-facing gaps evaluated, 5 P0/P1 gaps recommended, 5 P2 gaps deferred)
- Proposal: `openspec/changes/prompt-registry/proposal.md` (Engram `sdd/prompt-registry/proposal` #201 — Approach A recommended, 4 cooperating pieces, 10 open questions for design, 12 risks, 2-chained-PR strategy)
- Predecessor specs (format reference):
  - `openspec/changes/observability/spec.md` (change #6, closest precedent — same catalog + CLI + chained-PR pattern)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (change #5, single-PR precedent; 6-SKILL.md hand-edit pattern formalized by REQ-49)
  - `openspec/changes/archive/2026-06-26-cross-project-federation/spec.md` (change #4, chained-PR precedent)
  - `openspec/changes/archive/2026-06-26-vector-semantic-search/spec.md` (change #3, observability-adjacent counter catalog pattern; `VECTOR_COUNTER_NAMES` precedent)
- Counter catalog patterns (mirrored by `PROMPT_REGISTRY`):
  - `BINDING_COUNTER_NAMES` + backfill + inspect — `observability.py:70` (REQ-8 close, change #1)
  - `VECTOR_COUNTER_NAMES` (6 names) — `observability.py:85` (REQ-22, change #3)
  - `FEDERATED_COUNTER_NAMES` (3 names) — `observability.py:104` (REQ-26, change #4)
  - `SNAPSHOT_COUNTER_NAMES` (4 names, tuple) — `observability.py:124` (REQ-28..34, change #5)
- Jinja2 scaffold convention: `src/flow_engineering/scaffold.py:20` (`_env() -> Environment` factory) + `src/flow_engineering/templates/` (4 `.j2` files)
- Carry-forwards:
  - `observability` explore #195 line 263 (alerting is ENGINEERING, not prompt-registry) — scope-out confirmed
  - `cross-project-federation` archive-report #61 ("federated prompt registry" deferred) — resolved by deferral in Out-of-Scope
  - `graph-snapshots` CHANGELOG.md:13 (6-SKILL.md hand-edit precedent) — resolved by REQ-49
- Precedents:
  - `decision-code-linking` archive-report #119 S3 (BDD step def file 5-6× growth multiplier) — absorbed into the ×6 forecast
  - `flow drift --since` (REQ-10/11) — ISO 8601 parsing precedent (NOT used in change #7 directly; informational)
  - `flow projects init` (REQ-24) — `--init` flag pattern for `flow prompts check --init` (REQ-49)
  - `flow metrics --json` (REQ-8) — flat dict JSON precedent for `flow prompts list --json` (REQ-50)
  - `flow drift --strict` (REQ-13) — strict-mode flag pattern for `flow prompts lint --strict` (REQ-50)
- Engram DB state (2026-06-27): ~170 observations across 10 projects; 783 existing tests; 5 shipped changes + change #6 in spec; 4 inline prompt constants + 4 Jinja2 templates + 10 SKILL.md runtime files (plus 10 parallel prompts/sdd/*.md per D.6)

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_prompt_registry_module",
      "label": "prompt_registry.py (NEW — PROMPT_REGISTRY, PromptEntry dataclass, 4 migrated entries; ~120 prod LOC)",
      "file": "src/flow_engineering/prompt_registry.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_prompt_render_module",
      "label": "prompt_render.py (NEW — render_prompt() + render_prompt_safe() + PromptRenderError; shared Jinja2 Environment hoisted from scaffold.py; ~150 prod LOC)",
      "file": "src/flow_engineering/prompt_render.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_prompt_lint_module",
      "label": "prompt_lint.py (NEW — lint_prompts() + LintWarning dataclass + 5 warning categories; ~80 prod LOC)",
      "file": "src/flow_engineering/prompt_lint.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_opencode_skill_catalog_module",
      "label": "opencode_skill_catalog.py (NEW — SKILL_CATALOG, SkillEntry dataclass, checksum verification, frontmatter parsing, check_drift(); ~120 prod LOC)",
      "file": "src/flow_engineering/opencode_skill_catalog.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_strict_tdd_prompt_constant",
      "label": "STRICT_TDD_PROMPT (strict_tdd.py:13) — MIGRATION TARGET: replaced with render_prompt('strict_tdd', test_command=cmd); thin wrapper for v0.7.0 per D.8 alias",
      "file": "src/flow_engineering/strict_tdd.py",
      "line": 13,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_auto_suggest_prompt_constants",
      "label": "EMPTY_PROMPT_TEXT + PROMPT_HEADER + PROMPT_FOOTER (auto_suggest_code_refs.py:47-49) — MIGRATION TARGETS: 3 inline prompts replaced with render_prompt() calls",
      "file": "src/flow_engineering/auto_suggest_code_refs.py",
      "line": 47,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_scaffold_jinja_env",
      "label": "scaffold.py _env() Jinja2 Environment (REFACTOR target: move factory to prompt_render.py; thin re-export for backwards compat)",
      "file": "src/flow_engineering/scaffold.py",
      "line": 20,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_prompts_group",
      "label": "flow prompts CLI group (cli.py MODIFY — new Click group + 4 subcommands list/show/lint/check; ~150 prod LOC delta)",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_strict_tdd_j2",
      "label": "prompts/strict_tdd.j2 (NEW — Jinja2 version of STRICT_TDD_PROMPT with {{ test_command }} placeholder; ~4 LOC)",
      "file": "prompts/strict_tdd.j2",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_auto_suggest_header_j2",
      "label": "prompts/auto_suggest_header.j2 (NEW — Jinja2 version of PROMPT_HEADER; ~2 LOC)",
      "file": "prompts/auto_suggest_header.j2",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_auto_suggest_footer_j2",
      "label": "prompts/auto_suggest_footer.j2 (NEW — Jinja2 version of PROMPT_FOOTER; ~3 LOC)",
      "file": "prompts/auto_suggest_footer.j2",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_auto_suggest_empty_j2",
      "label": "prompts/auto_suggest_empty.j2 (NEW — Jinja2 version of EMPTY_PROMPT_TEXT; ~1 LOC)",
      "file": "prompts/auto_suggest_empty.j2",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_prompt_registry_spec",
      "label": "openspec/specs/prompt-registry/spec.md (NEW — capability spec cataloging 4 PROMPT_REGISTRY entries + 20 SKILL_CATALOG entries + flow prompts CLI contract; ~150 LOC)",
      "file": "openspec/specs/prompt-registry/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req45_prompt_registry",
      "label": "tests/bdd/req45_prompt_registry.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req45_prompt_registry.feature",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req46_prompt_render",
      "label": "tests/bdd/req46_prompt_render.feature (NEW — 3 BDD scenarios)",
      "file": "tests/bdd/req46_prompt_render.feature",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req47_prompt_lint",
      "label": "tests/bdd/req47_prompt_lint.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req47_prompt_lint.feature",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req49_skill_catalog",
      "label": "tests/bdd/req49_skill_catalog.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req49_skill_catalog.feature",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req50_cli_prompts",
      "label": "tests/bdd/req50_cli_prompts.feature (NEW — 3 BDD scenarios)",
      "file": "tests/bdd/req50_cli_prompts.feature",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_prompt_registry_steps",
      "label": "tests/bdd/test_prompt_registry_steps.py (NEW — pytest-bdd glue shared across 5 BDD features; ~400 LOC)",
      "file": "tests/bdd/test_prompt_registry_steps.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_prompt_registry",
      "label": "tests/unit/test_prompt_registry.py (NEW — PROMPT_REGISTRY schema + 4 migrated entries + rendering tests; ~250 LOC)",
      "file": "tests/unit/test_prompt_registry.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_prompt_render",
      "label": "tests/unit/test_prompt_render.py (NEW — render_prompt() with variables, missing variable, template error, autoescape; ~300 LOC)",
      "file": "tests/unit/test_prompt_render.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_prompt_lint",
      "label": "tests/unit/test_prompt_lint.py (NEW — lint_prompts() with 5 warning categories; ~250 LOC)",
      "file": "tests/unit/test_prompt_lint.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_opencode_skill_catalog",
      "label": "tests/unit/test_opencode_skill_catalog.py (NEW — SKILL_CATALOG + checksum + drift detection (mock SKILL.md files); ~300 LOC)",
      "file": "tests/unit/test_opencode_skill_catalog.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_prompts",
      "label": "tests/unit/test_cli_prompts.py (NEW — full CLI surface coverage for flow prompts list/show/lint/check; ~400 LOC)",
      "file": "tests/unit/test_cli_prompts.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    }
  ]
}
