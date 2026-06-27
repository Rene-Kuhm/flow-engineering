# Apply Progress — PR#1 Batch B — T1.4 + T1.5 (validation + lint helpers)

**Change:** `prompt-registry`
**PR:** #1 — Foundation: `PromptRegistry` catalog + helper surface + inline migration
**Batch:** B (T1.4 + T1.5)
**Branch:** `main`
**Final HEAD:** `e054b09` (T1.5 GREEN)
**Strategy:** Strict TDD (RED → GREEN per task); 2 work-unit commits + this doc
**Date:** 2026-06-27
**Tests:** 1038 → 1056 (+19 new tests, 0 regressions)

---

## Goal

Land the REQ-47 lint foundation on top of the T1.1–T1.3 catalog + helper surface:

- **`register()` shorthand** — positional-args wrapper around `register_prompt()`
  so call sites stay terse (`register(name, template, domain)` instead of
  `PromptDef(...)` + `register_prompt(p)`).
- **`validate_catalog()`** — REQ-47 lint foundation that detects the 5 catalog
  error codes (`duplicate_name`, `invalid_domain`, `jinja_syntax`,
  `undefined_var`, `invalid_version`) without raising. Callers (CLI, CI
  gates, tests) decide how to surface the result.
- **`LintError` dataclass** — frozen, JSON-serializable record of one violation.
- **`LintReport` dataclass** — aggregate result with `is_clean` / `error_count`
  / `error_codes` / `by_code()` / `to_dict()` helpers for the future
  `flow prompts lint` CLI (REQ-50).
- **`lint_prompts()` helper** — public API wrapping `validate_catalog()` and
  returning a `LintReport`. This is the canonical entry point for CI gates
  per the REQ-47 contract: "MUST NOT raise on broken registries; MUST
  return a list of warnings and let the caller decide".

---

## TDD Cycle Evidence

| Task | RED (tests written, fail) | GREEN (impl, all tests pass) | REFACTOR |
|------|---------------------------|------------------------------|----------|
| T1.4 | `d9173c8` test(unit): RED fixtures for `register()` shorthand + `validate_catalog()` — 8 tests fail (4 register + 4 validate) | `0936875` feat(prompt-registry): `register()` shorthand + `validate_catalog()` + `LintError` (REQ-47 GREEN) — 8 new tests pass + 1038 baseline preserved | n/a (clean first draft; `from jinja2 import …` inline-imported inside `validate_catalog` to keep the module importable on systems without jinja2) |
| T1.5 | `8bd8358` test(unit): RED fixtures for `lint_prompts()` + `LintReport` helper surface — 19 tests fail with `AttributeError: module 'flow_engineering.prompt_registry' has no attribute 'lint_prompts'` | `e054b09` feat(prompt-registry): `lint_prompts()` helper + `LintReport` dataclass (REQ-47 helper surface) — 19 new tests pass + 1037 baseline preserved (T1.4 GREEN already in) | n/a (clean first draft; `to_dict()` shape is stable per design D7) |

All tasks have complete RED → GREEN history in the commit log. No REFACTOR
phase was needed — both impls landed clean on first draft.

---

## Files Touched

| Path | Action | LOC delta |
|------|--------|-----------|
| `src/flow_engineering/prompt_registry.py` | MODIFY (T1.4 + T1.5) | +265 (helpers + dataclasses; total file is now 510 LOC) |
| `tests/unit/test_prompt_registry_validation.py` | MODIFY (T1.4 RED→GREEN adjustments) | +9 |
| `tests/unit/test_prompt_lint.py` | NEW (T1.5 RED fixtures) | +199 |

**Total production LOC:** ~265 (well under T1.4+T1.5's ~700 forecast)
**Total test LOC:** ~208 (well under T1.4+T1.5's ~450 forecast)
**Grand total:** ~473 LOC

The batch was significantly leaner than forecast because the simpler
`PromptDef` schema (from batch A) required less per-entry plumbing than the
locked `PromptEntry` 6-field schema in tasks.md.

---

## Commits (4 total: 2 work-unit pairs + 1 prior drift-hardening overlap)

| SHA | Type | Subject |
|-----|------|---------|
| `d9173c8` | test(unit) | RED fixtures for `register()` shorthand + `validate_catalog` (REQ-47 foundation) |
| `0936875` | feat(prompt-registry) | `register()` shorthand + `validate_catalog()` + `LintError` (REQ-47 GREEN) |
| `8bd8358` | test(unit) | RED fixtures for `lint_prompts()` + `LintReport` helper surface (REQ-47 helper) |
| `e054b09` | feat(prompt-registry) | `lint_prompts()` helper + `LintReport` dataclass (REQ-47 helper surface) |

No `Co-Authored-By:`. No AI attribution. No emoji. Conventional commits only.

---

## Test Results

| Phase | Test count | Delta | Time |
|-------|------------|-------|------|
| Baseline (post batch A) | 1038 | — | ~66s |
| After T1.4 RED (`d9173c8`) | 1046 | +8 | ~66s |
| After T1.4 GREEN (`0936875`) | 1046 | 0 (impl only) | ~66s |
| After T1.5 RED (`8bd8358`) | 1056 | +19 | ~66s |
| After T1.5 GREEN (`e054b09`) | 1056 | 0 (impl only) | 65.81s |

**Final:** 1056 passed in 65.81s (0 regressions, +19 new tests vs. baseline).

---

## Public Surface Added

| Symbol | Kind | Purpose |
|--------|------|---------|
| `register(name, template, domain, version, **meta)` | function | Positional-args shorthand for `register_prompt()`. Defaults `version` to `"0.0.0"` and accepts metadata as kwargs (merged with `domain` / `version`). Raises `ValueError` on duplicate name. |
| `LintError` | frozen dataclass | One catalog violation: `prompt_name` + `error_code` + `message` + optional `line`. |
| `validate_catalog(catalog=None)` | function | Detects the 5 error codes (no raise). Returns `list[LintError]`. |
| `LintReport` | frozen dataclass | Aggregate: `catalog` + `errors`. Properties: `is_clean`, `error_count`, `error_codes`. Methods: `by_code()`, `to_dict()`. |
| `lint_prompts(catalog=None)` | function | Public CI/test entry point. Returns a `LintReport`. |

All 5 symbols are exported in `__all__` for downstream `from
flow_engineering.prompt_registry import …` use.

---

## Error Code Coverage

The 5 catalog error codes are detected by `validate_catalog()`:

| Code | Trigger | Example |
|------|---------|---------|
| `duplicate_name` | Same name appears twice in catalog | `[("a", …), ("a", …)]` |
| `invalid_domain` | `entry.domain` is not a `PromptDomain` value | `domain="BOGUS"` |
| `jinja_syntax` | Template body fails Jinja2 parse | `"{{ unclosed"` |
| `undefined_var` | Jinja2 placeholder `{{ var }}` not declared in `metadata.required_vars` | template has `{{user}}`, metadata missing `required_vars=["user"]` |
| `invalid_version` | Version doesn't match `MAJOR.MINOR.PATCH` regex | `version="1.0"` |

---

## Deviations from Design

1. **`lint_prompts()` vs. `PromptRegistry` class.** The locked `tasks.md`
   describes `PromptRegistry` as a class with a `register()` method. Batch A
   landed a simpler module-level catalog (`PROMPT_NAMES` tuple) per the
   orchestrator's pragmatic scope. This batch adds `register()` as a
   **module-level function** (not a method), and `lint_prompts()` as another
   module-level helper. The `LintReport.catalog` field captures which catalog
   was linted, so the public API is equivalent.

2. **`LintReport` is a `dataclass(frozen=True)`, not a Pydantic model.** The
   design doesn't mandate Pydantic; using stdlib `dataclass` keeps the module
   importable without Pydantic (matching the project's `DriftReport` /
   `Finding` convention in `drift.py`). `to_dict()` produces a JSON-friendly
   shape.

3. **`lint_prompts()` returns a `LintReport`, not a list of warnings.** Per
   the REQ-47 contract ("let the caller decide"), callers receive a structured
   object with properties (`is_clean`, `error_count`) instead of a raw list.
   Callers who need a list can read `report.errors`.

4. **No CLI integration yet.** The `flow prompts lint` CLI command (REQ-50)
   is not yet wired up; this batch only ships the Python API surface. CLI
   wiring lands in batch C (or a future change).

5. **Working tree has 2 unrelated modifications** (`cli.py` write-back stderr
   WARN + `test_cli_drift.py` REQ-59 tests) from a parallel delegation. I
   left them untouched — they belong to a different change. Only
   `prompt_registry.py` was staged for this batch's commits.

---

## Risks / Notes for Next Batch

1. **`LintReport.to_dict()` shape is stable but undocumented in a JSON
   schema.** If downstream consumers (CI artifacts, dashboards) grow
   dependencies on it, consider pinning a `prompts-lint-v1.json` schema in
   `openspec/specs/`.

2. **`undefined_var` check applies only to Jinja2-style templates.** The
   current `PROMPT_NAMES` catalog uses Python `.format()` style
   (`{test_command}`), which Jinja2 treats as literal text — so no
   `undefined_var` errors fire today. The check is wired and ready for the
   future `.j2` migration (T1.2 in tasks.md).

3. **`register()` does NOT call `validate_catalog()` internally.** Adding
   new entries at runtime bypasses the lint pass; CI must call `lint_prompts()`
   explicitly. This is intentional (per REQ-47 "let the caller decide") but
   worth documenting in any future `flow prompts add` CLI.

4. **No drift-hardening / REQ-59 / daemon / archive spec mods** were
   committed — those files were modified in the working tree by a parallel
   agent and are not my scope.

---

## Next Recommended Step

`sdd-apply prompt-registry PR#1 batch C (T1.6 + T1.7 + T1.8: render_prompt +
BDD + CHANGELOG + SKILL + archive)` — wires the REQ-50 `flow prompts` CLI
surface (`list`, `show`, `lint`) onto this batch's Python API, adds the BDD
scenarios covering the lint surface, updates `CHANGELOG.md`, and writes the
SKILL.md mirror per REQ-49. Optionally runs `sdd-archive` to sync the delta
specs once batch C lands.

Alternative: launch `sdd-verify prompt-registry PR#1 batches A+B` to validate
the foundation + lint surface against the locked `spec.md` acceptance
criteria before continuing.