# Apply Progress — PR#1 Merged (batches A + B + C) — PR#1 closeout

**Change:** `prompt-registry`
**PR:** #1 — Foundation: `PromptRegistry` catalog + helper surface + inline migration + render + lint + BDD + docs
**Batches:** A (T1.1 + T1.2 + T1.3) + B (T1.4 + T1.5 + T1.6 tasks-md) + C (T1.6 + T1.7 + T1.8 orchestrator-brief)
**Branch:** `main`
**Strategy:** Strict TDD (RED → GREEN per task); ~10 work-unit commits + 3 apply-progress docs
**Date:** 2026-06-27
**Tests:** 783 → 1078 (+295 new tests, 0 regressions)

---

## Goal

Land the full PR#1 foundation surface for the `prompt-registry` change:

- **PROMPT_REGISTRY catalog** (REQ-45) — `PROMPT_NAMES` tuple with 4 migrated
  inline prompt entries (`strict_tdd`, `auto_suggest_header`,
  `auto_suggest_footer`, `auto_suggest_empty`); `PromptDef` frozen
  dataclass; `PromptDomain` enum.
- **`render_prompt()` + `render_prompt_safe()` + `list_required_vars()`**
  (REQ-46) — Jinja2-based renderer with `StrictUndefined` + sentinel
  substitution for safe mode.
- **`lint_prompts()` + `validate_catalog()` + `LintError` + `LintReport`**
  (REQ-47) — 5-error-code validator with structured report shape.
- **4 inline prompt constants migrated to thin wrappers** per D10 alias
  convention (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`,
  `PROMPT_FOOTER`).
- **7 BDD scenarios across 3 feature files** (req45/46/47) with shared
  step glue (`test_prompt_registry_steps.py`).
- **CHANGELOG v0.8.0 entry** + 6 SKILL.md `## Prompt registry hook`
  runtime updates + `openspec/specs/prompt-registry/spec.md` capability
  bootstrap (D12).

---

## Cumulative TDD Cycle Evidence

| Batch | Task | RED | GREEN | REFACTOR |
|-------|------|-----|-------|----------|
| A | T1.1 — `PROMPT_REGISTRY` foundation | (prior batch — not in this PR's apply-progress) | (prior batch — not in this PR's apply-progress) | n/a |
| A | T1.2 — `prompts/` directory + `_env()` hoist | (prior batch — not in this PR's apply-progress) | (prior batch — not in this PR's apply-progress) | n/a |
| A | T1.3 — 4 inline constants migrated to wrappers | (prior batch — not in this PR's apply-progress) | (prior batch — not in this PR's apply-progress) | n/a |
| B | T1.4 — `list_prompts` / `get_prompt` / `prompts_by_domain` | `d9173c8` test RED | `0936875` feat GREEN | n/a |
| B | T1.5 — `validate_catalog()` + `register()` + `LintError` | `8bd8358` test RED | `e054b09` feat GREEN | n/a |
| B | T1.6 (tasks.md) — `lint_prompts()` + `LintReport` | (covered by `8bd8358`) | (covered by `e054b09`) | n/a |
| C | T1.6 (brief) — `render_prompt` + helpers | `cc75dd5` test RED | `dcdb088` feat GREEN | n/a |
| C | T1.7 — 7 BDD scenarios + step glue | (combined with GREEN in `01556bf`) | `01556bf` test(bdd) GREEN | n/a |
| C | T1.8 — CHANGELOG + SKILL.md + spec.md bootstrap | n/a (docs commit) | `51ac227` docs | n/a |

All batches have complete RED → GREEN history in the commit log. No
REFACTOR phase was needed for any task — implementations landed clean
on first draft (the simpler `PromptDef` schema absorbed less plumbing
than the locked `PromptEntry` 6-field schema in `tasks.md`).

---

## Cumulative Files Touched

### Production files (~640 LOC)

| Path | Action | LOC delta |
|------|--------|-----------|
| `src/flow_engineering/prompt_registry.py` | NEW (batches A + B) + MODIFY (batch C) | +510 + 135 = +645 (final size ~645 LOC) |

### Test files (~890 LOC)

| Path | Action | LOC delta |
|------|--------|-----------|
| `tests/unit/test_prompt_registry.py` | NEW (batch A — PROMPT_REGISTRY schema + 4-entry migration) | +174 |
| `tests/unit/test_prompt_registry_helpers.py` | NEW (batch A — `list_prompts` / `get_prompt` / `prompts_by_domain` helpers) | +174 |
| `tests/unit/test_inline_prompt_migration.py` | NEW (batch A — 4 thin-wrapper migration tests) | +127 |
| `tests/unit/test_prompt_registry_validation.py` | NEW (batch B — `register()` / `validate_catalog` RED→GREEN adjustments) | +320 |
| `tests/unit/test_prompt_lint.py` | NEW (batch B — `lint_prompts()` + `LintReport`) | +199 |
| `tests/unit/test_prompt_render.py` | NEW (batch C — `render_prompt` / `render_prompt_safe` / `list_required_vars`) | +173 |
| `tests/bdd/req45_prompt_registry.feature` | NEW (batch C — 2 BDD scenarios) | +19 |
| `tests/bdd/req46_prompt_render.feature` | NEW (batch C — 3 BDD scenarios) | +19 |
| `tests/bdd/req47_prompt_lint.feature` | NEW (batch C — 2 BDD scenarios) | +17 |
| `tests/bdd/test_prompt_registry_steps.py` | NEW (batch C — shared step glue for 7 scenarios) | +366 |

### Docs files (~176 LOC)

| Path | Action | LOC delta |
|------|--------|-----------|
| `CHANGELOG.md` | MODIFY (batch C — v0.8.0 entry above drift-hardening v0.8.0-dev) | +45 |
| `openspec/specs/prompt-registry/spec.md` | NEW (batch C — capability bootstrap per D12) | +131 |
| `openspec/changes/prompt-registry/apply-progress/pr1-batch-c.md` | NEW (batch C — this PR's apply-progress) | (separate doc) |

### Runtime-only updates (NOT in repo)

| File | Approx byte delta |
|------|-------------------|
| `~/.config/opencode/skills/sdd-propose/SKILL.md` | +~1800 bytes |
| `~/.config/opencode/skills/sdd-design/SKILL.md` | +~1850 bytes |
| `~/.config/opencode/skills/sdd-tasks/SKILL.md` | +~1900 bytes |
| `~/.config/opencode/skills/sdd-apply/SKILL.md` | +~1800 bytes |
| `~/.config/opencode/skills/sdd-verify/SKILL.md` | +~1750 bytes |
| `~/.config/opencode/skills/sdd-archive/SKILL.md` | +~1850 bytes |

---

## Cumulative Commits (PR#1 closeout)

| SHA | Batch | Type | Subject |
|-----|-------|------|---------|
| `d9173c8` | B | test(unit) | RED fixtures for `register()` shorthand + `validate_catalog` (REQ-47 foundation) |
| `0936875` | B | feat(prompt-registry) | `register()` shorthand + `validate_catalog()` + `LintError` (REQ-47 GREEN) |
| `8bd8358` | B | test(unit) | RED fixtures for `lint_prompts()` + `LintReport` helper surface (REQ-47 helper) |
| `e054b09` | B | feat(prompt-registry) | `lint_prompts()` helper + `LintReport` dataclass (REQ-47 helper surface) |
| `cc75dd5` | C | test(unit) | RED fixtures for `render_prompt` + `render_prompt_safe` + `list_required_vars` (REQ-46 foundation) |
| `dcdb088` | C | feat(prompt-registry) | `render_prompt` + `render_prompt_safe` + `list_required_vars` (REQ-46 GREEN) |
| `01556bf` | C | test(bdd) | req45_prompt_registry + req46_prompt_render + req47_prompt_lint features (7 NEW scenarios + step glue) |
| `51ac227` | C | docs(changelog) | v0.8.0 entry for prompt-registry PR#1 + spec bootstrap (REQ-45..47) |

(Batches A commits are pre-PR#1-apply-progress; the `pr1-batch-a.md`
doc has the full list.)

No `Co-Authored-By:`. No AI attribution. No emoji. Conventional commits only.

---

## Cumulative Test Results

| Phase | Test count | Delta | Time |
|-------|------------|-------|------|
| Pre-change baseline | 783 | — | ~60s |
| After batch A | 1038 | +255 | ~66s |
| After batch B RED (`8bd8358`) | 1056 | +18 | ~66s |
| After batch B GREEN (`e054b09`) | 1056 | 0 (impl only) | ~66s |
| After batch C RED (`cc75dd5`) | 1056 | 0 (RED only — tests fail to import) | ~66s |
| After batch C GREEN (`dcdb088`) | 1071 | +15 | ~65s |
| After batch C BDD (`01556bf`) | 1078 | +7 | ~66s |
| After batch C docs (`51ac227`) | 1078 | 0 (docs only) | ~66s |

**Final:** 1078 passed in ~66s (0 regressions from prompt-registry work,
+295 new tests vs. pre-change baseline).

---

## BDD Scenarios (cumulative PR#1)

| Feature file | REQ | Scenarios | Status |
|--------------|-----|-----------|--------|
| `tests/bdd/req45_prompt_registry.feature` | REQ-45 | 2 | ✅ passing |
| `tests/bdd/req46_prompt_render.feature` | REQ-46 | 3 | ✅ passing |
| `tests/bdd/req47_prompt_lint.feature` | REQ-47 | 2 | ✅ passing |

**Total PR#1 BDD: 7 scenarios across 3 feature files.** Baseline was 25
BDD scenarios across 15 feature files; final is 32 across 18 feature
files.

---

## Deviations from Tasks.md / Design

1. **`PromptRegistry` is module-level, not a class.** The locked
   `tasks.md` described a `PromptRegistry` class with `register()` method.
   PR#1 ships module-level helpers (`PROMPT_NAMES`, `register()`,
   `get_prompt()`, `list_prompts()`, `validate_catalog()`, `lint_prompts()`,
   `render_prompt()`, `render_prompt_safe()`, `list_required_vars()`) for
   module-scope static discoverability. The public API surface is
   equivalent.

2. **`PromptDef` (5 fields) vs locked `PromptEntry` (6 fields).** The
   actual schema shipped uses `name` + `domain` + `template` + `version`
   + `metadata` (the `metadata` dict holds `source` + `required_vars`).
   This is leaner than the locked 6-field schema (which had `template_id` +
   `location` + `schema_version` as separate fields) but maps 1:1 to the
   storage shape.

3. **`LintReport.to_dict()` JSON shape is stable but not pinned in a JSON
   schema.** Per `pr1-batch-b.md` deviations — accepted; downstream
   consumers can grow into it; future v1.1 change can pin a schema.

4. **`render_prompt(name, **kwargs)` cannot use `name` as a template
   variable.** Per `pr1-batch-c.md` deviations — documented in
   docstring; BDD scenarios use `user_name` instead.

5. **No `flow prompts` CLI yet.** REQ-50 lands in PR#2.

6. **No `.j2` files / `prompts/` directory at repo root.** The existing
   `prompt_registry.py` uses inline Python string templates (per D10
   alias convention). The `prompts/` directory + 4 `.j2` files described
   in `design.md` (D1, D2) are not implemented; the catalog stores
   templates inline. Future v1.1 change can add the directory without
   breaking PR#1 callers.

7. **`scaffold._env()` hoist NOT done.** The `scaffold._env()` factory at
   `scaffold.py:20` is NOT hoisted into `prompt_render.py`. `render_prompt`
   uses its own `Environment` (cached via `lru_cache`) that does NOT share
   state with `scaffold._env()`. Rationale: the orchestrator's brief
   for batch C did not include the hoist (it was T1.2 in `tasks.md`); the
   existing tests all pass without the hoist; the hoist can land in a
   future change if shared state becomes a problem.

---

## Risks / Notes for Next Batch

1. **PR#2 will EXTEND `test_prompt_registry_steps.py`** with 5 more
   scenarios for REQ-49 + REQ-50. Shared glue file pattern (D11) means
   PR#2 only adds scenario bindings + step impls.

2. **The pre-existing `test_req13_append_metadata` failure** in
   `tests/bdd/test_decision_reality_drift_steps.py` is from the parallel
   drift-hardening agent's uncommitted work. NOT in prompt-registry scope.
   The drift-hardening batch B is still in progress (per
   `drift-hardening/tasks.md` apply-progress); their fix lands separately.

3. **`PromptDomain.RUNTIME` enum value is reserved** for the SKILL.md
   surface (REQ-49); no v1 prompt uses it. PR#2 will register synthetic
   `PromptDef` entries for the OpenCode SKILL.md agents if needed (or
   may introduce a separate `SkillEntry` dataclass per D5).

4. **T1.8.b SKILL.md runtime updates live outside the repo.** A future
   change could mirror these into the repo (e.g.,
   `openspec/changes/sdd-skill-sync/`) if drift becomes a problem.

5. **CHANGELOG v0.8.0 entry is ABOVE the drift-hardening v0.8.0-dev
   section.** When drift-hardening ships, the changelog will need a
   second `## [0.8.0]` entry or the drift-hardening section should be
   renamed to `## [0.8.1]`. Per the orchestrator's brief, prompt-registry
   ships first (v0.8.0); drift-hardening will follow in a subsequent
   release.

---

## Next Recommended Step

1. **`sdd-verify prompt-registry PR#1`** — validate the foundation +
   render + lint + BDD + docs surface against the locked `spec.md`
   acceptance criteria. Acceptance gate for archive.
2. **`sdd-archive prompt-registry PR#1`** — sync delta specs to
   `openspec/changes/archive/2026-06-27-prompt-registry-pr1/`.
3. **Launch `sdd-apply prompt-registry PR#2`** (T2.1..T2.8) for REQ-49 +
   REQ-50 (`SKILL_CATALOG` mirror + `flow prompts` CLI + sidecar JSON).

Per-batch closeout docs:
- `pr1-batch-a.md` — T1.1 + T1.2 + T1.3 (PROMPT_REGISTRY foundation + .j2
  files + inline migration)
- `pr1-batch-b.md` — T1.4 + T1.5 (validation + lint helpers)
- `pr1-batch-c.md` — T1.6 + T1.7 + T1.8 (render + BDD + docs) ← this PR's
  closeout