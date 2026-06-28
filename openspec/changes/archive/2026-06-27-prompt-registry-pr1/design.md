<!-- design.md: change #7 prompt-registry. Source: manual. -->
# Design: prompt-registry

> Mirror of Engram `sdd/prompt-registry/design` (topic_key upsert after file
> creation). Reference format mirrors
> [`openspec/changes/observability/design.md`](../observability/design.md)
> (D1–D12) — change #6 is the closest precedent (catalog + CLI + chained-PR
> pattern). All 10 open questions from proposal #201 are resolved below. The
> Engram `code_refs` block is appended at file end so `flow inspect <change>`
> can render the binding surface.

```yaml
status: success
confidence: high
open_questions_resolved: 10/10
architecture_decisions: 12  # D1..D12
file_created: C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\design.md
next_recommended: sdd-tasks prompt-registry
```

## Goal

`prompt-registry` ships the **catalog + render + lint + CLI + SKILL.md mirror**
surface that turns the existing three disconnected prompt worlds into a single,
discoverable, versioned, golden-testable registry. Today the codebase has **4
inline prompt constants** (`STRICT_TDD_PROMPT` at `strict_tdd.py:13` plus
`EMPTY_PROMPT_TEXT` / `PROMPT_HEADER` / `PROMPT_FOOTER` at
`auto_suggest_code_refs.py:47-49`), **4 Jinja2 scaffolding templates** at
`src/flow_engineering/templates/` (loaded via a private `_env()` in
`scaffold.py:20` that is NOT exposed to any other module), and **10 OpenCode
runtime SKILL.md agent prompts** at `~/.config/opencode/skills/sdd-*/SKILL.md`
that drive the entire SDD cycle yet live **outside the repo** with no version
pin, no checksum, and no drift detection. Four of nine user-facing CLI
subcommands (`apply`, `verify`, `archive`, plus the SKILL-running variant of
`new`) delegate to sdd-* sub-agents whose prompts the repo cannot see.

This change adds the **registry + render + lint + CLI** surface on top of the
existing `_env()` Jinja2 factory in `scaffold.py` and introduces the
**SKILL_CATALOG** mirror for the OpenCode runtime SKILL.md surface so that
drift between `flow` and the agent prompts that drive the SDD cycle becomes
detectable in CI rather than discoverable in a confused `flow apply` run three
weeks later. All artifacts are additive on top of change #6's observability
catalog pattern (the `VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` template
that this change mirrors for `PROMPT_REGISTRY`).

## Architecture Overview

`prompt-registry` ships four cooperating modules + one CLI group + one
sidecar:

```
$ flow prompts {list, show <id>, lint, check}        # cli.py (NEW group, 4 subcommands)
   │
   ├─► list / show <id> ──► prompt_registry.PROMPT_REGISTRY  (NEW module, 4 entries)
   │                       │
   │                       └─► prompt_render.render_prompt()  (NEW module, Jinja2 shared with scaffold.py)
   │                              │
   │                              └─► prompts/<id>.j2  (NEW .j2 files at repo root)
   │
   ├─► lint ─────────────► prompt_lint.lint_prompts()  (NEW module, 5 warning categories)
   │
   └─► check ────────────► opencode_skill_catalog.check_drift()  (NEW module, 20 entries)
                                  │
                                  ├─► ~/.config/opencode/skills/sdd-*/SKILL.md  (10 files, RUNTIME)
                                  ├─► ~/.config/opencode/prompts/sdd/*.md         (10 files, RUNTIME)
                                  └─► ~/.flow-engineering/prompt_checksums.json   (NEW sidecar)
```

Each new module's responsibility:

- **`prompt_registry.py`** — `PROMPT_REGISTRY: dict[str, PromptEntry]` mapping
  `prompt_id → {template_id, version, owner, location, variables, schema_version}`.
  Migrates the 4 existing inline prompts. Sibling of `observability.py`'s
  `VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES`.
- **`prompt_render.py`** — `render_prompt()` + `render_prompt_safe()` +
  `PromptRenderError`. Shared Jinja2 `Environment` hoisted out of
  `scaffold.py:_env()` so it is reusable across modules. `prompts/` directory
  at repo root for `.j2` files.
- **`prompt_lint.py`** — `lint_prompts()` + `LintWarning` dataclass + 5
  warning categories (`missing_placeholder`, `unused_variable`,
  `template_parse_error`, `autoescape_disabled`, `missing_variable`).
- **`opencode_skill_catalog.py`** — `SKILL_CATALOG: dict[str, SkillEntry]` for
  20 entries (10 `SKILL.md` + 10 `prompts/sdd/*.md`). SHA-256 of frontmatter
  YAML dict; sidecar JSON at `~/.flow-engineering/prompt_checksums.json`.
  `check_drift()`, `update_checksums()`, `init_checksums()`, `SkillVersionError`.
- **`cli.py` (MODIFY)** — `flow prompts` Click group + 4 subcommands
  (`list`, `show <id>`, `lint`, `check`) with 7 new flags. ~150 prod LOC delta.

## Open Questions Resolution (all 10 from proposal §5)

### OQ-1: `prompts/` directory location — repo root or inside the package?

**Decision**: **Repo root (`<repo>/prompts/`)**. Mirrors the `openspec/`
first-class artifact convention (which sits at repo root and is read by external
tools without importing `flow_engineering`); allows future external tooling
to read prompt files without `import flow_engineering`. The existing
`src/flow_engineering/templates/` convention is **NOT mirrored** because
template files have a different audience (scaffolding output, not prompt
content) and the existing in-package location blocks external tools.

**Rationale**: The `openspec/` precedent (also at repo root) is the structural
template. Templates generate other files (project scaffolding); prompts are
rendered and shipped to runtime agents. Putting them at repo root lets a
future LLM-backed feature (e.g., `flow drift --llm-summary`) read the prompt
template without paying the `flow_engineering` import cost.

**Alternatives considered**: (a) `src/flow_engineering/prompts/` — mirrors
the `templates/` convention but blocks external readers; rejected. (b)
Hybrid — both — adds two locations for the same thing; rejected.

**Affects**: REQ-46 (D3 template engine), REQ-50 (CLI surface).

### OQ-2: Jinja2 autoescape scope — all strings or HTML/XML extensions only?

**Decision**: **`select_autoescape(enabled_extensions=(), default_for_string=True)`**
— autoescape ALL string variables by default. Defensive; prevents
control-character injection through variable substitution even though no
current prompt template renders HTML.

**Rationale**: An audit of the 4 existing inline prompts (the proposal's OQ-2
recommendation) confirms none of them injects `<` or `&` through `{{ var }}`
substitution. The autoescape cost is negligible for these templates (4 entries,
<10 KB total) and the defensive default is the right call for a registry that
will grow. The `default_for_string=True` flag auto-escapes ALL string
variables — Jinja2's `select_autoescape()` defaults to enabling autoescape
ONLY for `.html` / `.htm` / `.xml` / `.xhtml` extensions which does NOT match
this use case (the `.j2` extension has no default autoescape).

**Alternatives considered**: (a) `autoescape=False` — fastest but unsafe;
rejected. (b) `select_autoescape()` default (extensions only) — wrong for
`.j2` files; rejected.

**Affects**: REQ-46 (D3 template engine), REQ-47 (lint — autoescape_disabled
warning category).

### OQ-3: Prompt schema versioning — per-prompt semver or registry-wide single version?

**Decision**: **Per-prompt `version: semver` (e.g., `"1.0.0"`) inside
`PromptEntry` + registry-wide `schema_version` (e.g., `"1.0"`) for the
`PromptEntry` shape itself.** Lint fails on `schema_version` mismatch across
entries (defensive: every entry MUST declare the same schema version).

**Rationale**: Each prompt can evolve independently — a wording tweak is
semver minor, a variable-signature change is semver major. Registry-wide
versioning would force every change to bump a global number, conflating
unrelated changes. The `schema_version` is a separate, structural invariant
that prevents schema drift across entries.

**Alternatives considered**: (a) Single registry-wide semver — forces
synchronous evolution; rejected. (b) No versioning — observability gap;
rejected.

**Affects**: REQ-45 (PromptEntry dataclass).

### OQ-4: `flow prompts show` missing-variable behavior — fail / empty / sentinel?

**Decision**: **`render_prompt()` (runtime) hard-fails on missing variables
with `PromptRenderError`; `render_prompt_safe()` (CLI inspection) substitutes
`<{var_name}>` sentinel for missing declared variables.** `flow prompts show`
uses the safe variant; runtime callers (production code paths) use the hard
variant.

**Rationale**: Runtime callers MUST NOT silently inject empty strings into
agent context — that would degrade the user-visible prompt quality without
any error signal. CLI inspection is a human-facing diagnostic; a sentinel like
`<test_command>` is informative ("you missed this variable") and never reaches
runtime. The split mirrors the Python convention `int()` vs `int_or_default()`
— strict and safe variants of the same primitive.

**Alternatives considered**: (a) Both paths fail — bad UX for CLI inspection;
rejected. (b) Both paths substitute empty — silent corruption risk; rejected.
(c) Single function with `safe=True` kwarg — conflated contract; rejected.

**Affects**: REQ-46 (render_prompt + render_prompt_safe), REQ-50 (flow
prompts show).

### OQ-5: SKILL.md checksum strategy — full file SHA-256 or frontmatter-only?

**Decision**: **Frontmatter-only SHA-256**: parse YAML, hash the canonical
JSON dict (sorted keys, no whitespace). Ignore body whitespace. `--strict`
flag on `flow prompts check` flips to full-file SHA-256 for paranoid mode
(writes a different sidecar field `checksum_strict`).

**Rationale**: Whitespace-only drift in the SKILL.md body would otherwise
trigger false-positive drift signals (a developer reformats a code block →
checksum changes → `flow prompts check` reports drift → on-call noise).
Semantic version metadata lives in the frontmatter; that's what drift
detection actually cares about. The full-file mode (`--strict`) is the
escape hatch when the user wants to catch body changes too.

**Alternatives considered**: (a) Full file SHA-256 — false-positive prone;
rejected as default. (b) Per-line frontmatter regex — fragile; rejected. (c)
Full AST hash — overkill; rejected.

**Affects**: REQ-49 (check_drift), REQ-50 (flow prompts check --strict).

### OQ-6: SKILL_CATALOG coverage — both `skills/sdd-*/SKILL.md` AND `prompts/sdd/*.md`?

**Decision**: **BOTH surfaces, 20 catalog entries total** (10 SKILL.md + 10
prompts/sdd/*.md). Two distinct `SkillEntry` records per sdd-* agent, one
for each file. `flow prompts check` reports drift per file.

**Rationale**: The two surfaces are maintained separately per the OpenCode
convention (the `SKILL.md` is user-facing metadata; the `prompts/sdd/*.md`
is the actual agent prompt). They have overlapping content but are
independent files — drift on one is a real signal that should not be
masked by the other. The cost of 20 entries (vs 10) is negligible
(SHA-256 over ~6 KB frontmatter is <1ms per file).

**Alternatives considered**: (a) Single surface only (SKILL.md) — drops
`prompts/sdd/*.md` coverage; rejected. (b) Single surface only
(`prompts/sdd/*.md`) — drops SKILL.md coverage; rejected.

**Affects**: REQ-49 (SKILL_CATALOG 20 entries).

### OQ-7: `.j2` metadata sidecars — Python-only or YAML frontmatter in `.j2` files?

**Decision**: **Python-only for v1.** `PromptEntry` dataclass in
`prompt_registry.py` is the single source of truth for metadata; the `.j2`
files contain ONLY template body (no YAML frontmatter). Mirrors the existing
`scaffold.py` convention where `templates/*.j2` have NO frontmatter.

**Rationale**: The 4 existing `.j2` files at `src/flow_engineering/templates/`
have no frontmatter — adding YAML frontmatter would be a NEW pattern. The
registry metadata is small (6 fields per entry) and is naturally Python data.
If external tooling later needs frontmatter-style `.j2`, the v1.1 follow-up
can add it without breaking v1 callers (frontmatter would be an additive
parse step).

**Alternatives considered**: (a) YAML frontmatter in `.j2` — adds YAML
parser round-trip and a new pattern; rejected for v1. (b) Hybrid
(Python + optional frontmatter) — confusing; rejected.

**Affects**: REQ-45 (registry schema), REQ-46 (template format).

### OQ-8: `STRICT_TDD_PROMPT` migration strategy — silent replace, deprecation, or alias?

**Decision**: **Alias for v0.7.0; remove in v0.8.0.** The 4 existing inline
constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`,
`PROMPT_FOOTER`) become thin wrappers that call `render_prompt("strict_tdd",
test_command=...)` etc. for v0.7.0. Removed in v0.8.0 per the project's
standard deprecation pattern.

**Rationale**: External imports of these constants must keep working for
v0.7.0 (no breaking changes); the v0.8.0 removal gives downstream consumers
one full release cycle to migrate. The thin wrappers are 1-line functions
that just call `render_prompt()` — no duplication of template content. The
`prompt_fn=Callable` injection point at `engram_io.py:541` is preserved
as-is — the registry is additive, the seam still works.

**Alternatives considered**: (a) Silent replace — breaks external imports;
rejected. (b) Loud deprecation warning on import — pollutes startup logs;
rejected for v1 (consider for v0.7.x maintenance).

**Affects**: REQ-45 (migration), REQ-50 (CLI surface), D10 inline prompt
migration strategy.

### OQ-9: `flow prompts check --update` auto-update — report only, ask, or auto?

**Decision**: **Report + opt-in `--update` flag.** Default `flow prompts
check` reports drift and exits non-zero (1). `--update` writes fresh
checksums to the sidecar JSON and exits 0. `--no-fail` flag suppresses
non-zero exit on drift (CI compat — same pattern as `flow drift --no-fail`).
Auto-update is **never** the default (silently accepting upstream changes
that may break `flow` is too dangerous).

**Rationale**: Mirrors the explicit-flag precedent from `flow projects
backfill --confirm` (cross-project-federation D3) and `flow snapshot prune
--confirm` (graph-snapshots D10). Auto-update would let a malicious or
buggy upstream SKILL.md change silently propagate into the user's sidecar.
The `--update` flag is opt-in by design.

**Alternatives considered**: (a) Report-only — user has to manually edit
the sidecar JSON; rejected (poor UX). (b) Auto-update — silent corruption
risk; rejected.

**Affects**: REQ-49 (update_checksums), REQ-50 (--update / --no-fail flags).

### OQ-10: REQ-52 prompt observability counters — same catalog as observability or separate?

**Decision**: **Same `observability.py` catalog** when REQ-52 lands in v1.1.
Add 3 counters (`prompts_render_total{prompt_id, version}`,
`prompts_render_ms`, `prompts_render_failed_total{reason}`) to the existing
catalog (alongside `VECTOR_COUNTER_NAMES`, `FEDERATED_COUNTER_NAMES`,
`SNAPSHOT_COUNTER_NAMES`). Change #6 ships the read-side (`flow metrics`);
change #7 ships the write-side for prompt counters. **No new module**; the
write-side is wired into `render_prompt()` via `observability.increment()`.

**Rationale**: The observability catalog is the project's single counter
registry (REQ-8 close contract). Splitting prompt counters into a separate
module would fragment `flow metrics` output and break the prefix-based
`DOMAIN_BY_PREFIX` grouping (REQ-37). The catalog is forward-compatible —
adding 3 new counter names is a `VECTOR_COUNTER_NAMES`-style list literal
update.

**Alternatives considered**: (a) Separate `prompt_registry` counters module
— fragments `flow metrics`; rejected. (b) Deferred to a `prompt-metrics`
follow-up change — REQ-52 already listed in out-of-scope; rejected as
redundant (D10 is the resolution, not a re-deferral).

**Affects**: D8 cross-PR consistency (REQ-52 lands later), observability
catalog extension.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | Module layout: where do `PROMPT_REGISTRY` / `render_prompt` / `lint_prompts` / `SKILL_CATALOG` live? | **Four new sibling modules**: `prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`, `opencode_skill_catalog.py` — all in `src/flow_engineering/`, siblings of `observability.py`. NO new package, NO sub-package. Each module owns one concern: registry / render / lint / skill catalog. | The four concerns are independent enough to warrant separate modules but small enough that a sub-package would be ceremony (matches `graph-snapshots` D1 — 6 methods in `snapshot_manager.py`, not a `snapshot/` sub-package). The proposal's "4 cooperating pieces" map 1:1 to 4 modules. Each module is importable as `from flow_engineering.prompt_X import Y` — same flat import style the project uses today. |
| **D2** | Prompt storage format | **`.j2` Jinja2 files for template body + Python dataclass constants for metadata.** `prompts/<id>.j2` files contain ONLY the template body. `PROMPT_REGISTRY` in `prompt_registry.py` is the metadata source of truth: 4 entries (`strict_tdd`, `auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`). | Mirrors the existing `templates/*.j2` convention (no YAML frontmatter) and the existing `observability.py` catalog convention (Python dataclass constants). Pure-JSON sidecar state (`~/.flow-engineering/prompt_checksums.json`) for runtime-mutable SKILL.md checksums. No YAML-in-Jinja round-trip cost. |
| **D3** | Template engine | **Jinja2** (already a project dependency via `pyproject.toml:18`, used by `scaffold.py:20`). The `_env() -> Environment` factory is hoisted from `scaffold.py:20-25` into `prompt_render.py`; `scaffold.py:_env()` becomes a thin re-export. `autoescape=select_autoescape(enabled_extensions=(), default_for_string=True)` per OQ-2. `keep_trailing_newline=True` (preserves existing `_env()` behavior). | Jinja2 is already a project dependency — no new runtime dep. The existing `_env()` factory at `scaffold.py:20` proves the pattern works for 4 templates; reusing it for 4 prompts adds zero new runtime weight. `f-strings` would lose autoescape, AST validation, and the lint hook. Mako would add a new runtime dep. |
| **D4** | Catalog structure | **Flat `dict[str, PromptEntry]`** keyed by `prompt_id` (kebab-or-snake-case). Same shape as `VECTOR_COUNTER_NAMES` (list) and `FEDERATED_COUNTER_NAMES` (list) — but a `dict` because prompt lookup is by ID, not iteration. `PromptEntry` is a `frozen=True` dataclass with 6 fields (D3 per-prompt semver + OQ-3 schema_version). | List-style catalogs (`VECTOR_COUNTER_NAMES`) work for prefix-based grouping (REQ-37); dict-style catalogs work for direct ID lookup (`render_prompt("strict_tdd")`). Prompts are accessed by ID, not iterated, so `dict` is the natural shape. Nested `{domain: {name: ...}}` adds a layer of indirection the lookup path doesn't need. |
| **D5** | SKILL.md checksum sidecar format | **JSON sidecar at `~/.flow-engineering/prompt_checksums.json`** with shape `{skill_name: {version: str, checksum: str, last_verified_at: str}}`. SHA-256 over canonicalized frontmatter YAML dict (sorted keys, no whitespace) per OQ-5. `--strict` writes a sibling `checksum_strict` field with full-file SHA-256. | JSON mirrors the existing `~/.flow-engineering/metrics.jsonl` (REQ-8 close contract). Per-skill dict enables `flow prompts check --skill <name>` to read just one entry without parsing the whole file. `last_verified_at` (ISO 8601) is the audit trail for when the sidecar was last refreshed. |
| **D6** | SKILL.md discovery | **Glob `~/.config/opencode/skills/sdd-*/SKILL.md` AND `~/.config/opencode/prompts/sdd/*.md`** at `SKILL_CATALOG` import time. The 20 entries are hard-coded in `SKILL_CATALOG` (10 sdd-* agents × 2 surfaces) for determinism; runtime discovery (`glob`) is used as a sanity check that the expected files exist (warns on missing files via `MISSING` drift status). | Hard-coded catalog matches `VECTOR_COUNTER_NAMES` (deterministic list literal). Glob at import time catches the case where the user deleted a SKILL.md directory (returns `MISSING` drift status in `check_drift()`). Per-agent config file would add a new artifact; the file-existence glob is sufficient. |
| **D7** | Lint ruleset | **`lint_prompts()` runs 5 warning categories** (per REQ-47): `missing_placeholder` (error — `{{ var }}` in template but not in declared `variables`), `unused_variable` (warning — declared but no `{{ var }}` reference), `template_parse_error` (error — Jinja2 `Environment.parse()` fails), `autoescape_disabled` (error — sanity check on the shared `Environment`), `missing_variable` (error — tagged for the CLI user-facing message). All 5 implemented via `jinja2.meta.find_undeclared_variables(env.parse(template))` + `Environment.parse()` for parse errors. | Jinja2 `Environment.parse()` is the AST parser; `meta.find_undeclared_variables()` is the public API for extracting referenced variables. Both are stdlib-of-jinja2 (no new dep). Placeholder validation alone would miss the autoescape check; AST parsing alone would miss the unused-variable check; the 5 categories together cover the full lint surface. |
| **D8** | Drift detection cadence | **On-invocation with cached sidecar.** `flow prompts check` reads the sidecar JSON, walks the catalog, SHA-256s each on-disk frontmatter, compares. No scheduled run; no daemon. The sidecar is the cache. `--update` refreshes the sidecar. | Mirrors the on-invocation pattern of `flow drift <change>` (REQ-10/11, no scheduled run). A scheduled drift check would add a daemon (`flow watch`) which is out-of-scope (out-of-scope #10 in `cross-project-federation`). The sidecar JSON makes re-checks cheap (read ~1 KB file). |
| **D9** | Exit codes | **`flow prompts` exit codes**: `0` = clean (no drift, no lint errors), `1` = drift detected / lint warnings present, `2` = lint errors present (`--strict` also maps warnings → errors → exit 2), `3` = usage error (invalid prompt id, invalid flag combo), `5` = unknown prompt id on `flow prompts show <unknown>`. Per subcommand: `list` → `0`; `show` → `0` (success) / `5` (unknown id); `lint` → `0` (clean) / `1` (warnings) / `2` (errors or `--strict`); `check` → `0` (clean) / `1` (drift, unless `--no-fail`) / `3` (usage). | Mirrors `flow metrics` exit code conventions (REQ-37 D9: `2` = usage, `3` = data, `4` = I/O). `1` for drift/warnings matches `flow drift --no-fail` semantics. `5` for unknown prompt id mirrors the `flow inspect <unknown>` convention (cli.py:940). JSON to stderr on errors (no traceback to user). |
| **D10** | Inline prompt migration strategy | **Gradual alias for v0.7.0; remove in v0.8.0.** `STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER` become thin 1-line wrappers around `render_prompt("strict_tdd", ...)`, `render_prompt("auto_suggest_empty")`, etc. External imports keep working for v0.7.0. Removed in v0.8.0 per project deprecation pattern. | Gradual migration avoids breaking external imports (`strict_tdd.py:84` calls `STRICT_TDD_PROMPT.format(test_command=cmd)`; tests in `tests/unit/test_strict_tdd.py:75` assert the rendered string). Drop-in migration would require updating 4 modules + their tests + their callers in one PR; the LOC overhead is comparable but the risk surface is much larger. The thin wrappers are byte-equivalent in output for callers that pass the same variables. |
| **D11** | Cross-PR consistency between PR#1 and PR#2 | **Shared `prompts/` directory + shared `~/.flow-engineering/prompt_checksums.json` sidecar + shared BDD glue file.** PR#1 lands `prompt_registry.py` + `prompt_render.py` + `prompt_lint.py` + the 4 `.j2` files + 4 inline constants migrated to wrappers. PR#2 lands `opencode_skill_catalog.py` + `flow prompts` CLI group + `openspec/specs/prompt-registry/spec.md` + the SKILL.md hook prose on `~/.config/opencode/skills/sdd-*/SKILL.md`. PR#1 carries the `prompts/` directory so PR#2 can `os.listdir(prompts_dir)` to verify `.j2` files match the registry; PR#2 carries the sidecar JSON so PR#1's `--strict` test (which asserts sidecar existence after `check --init`) has a stable target. Shared BDD glue file at `tests/bdd/test_prompt_registry_steps.py` covers all 5 BDD features. | Mirrors the chained-PR pattern from `cross-project-federation` (PR#1: backend foundation; PR#2: production integration) and `observability` (PR#1: read-side helpers; PR#2: Prometheus export). The shared sidecar JSON is the cross-PR coordination point — PR#1's tests assert the sidecar shape exists after `check --init`, PR#2's tests assert the sidecar updates after `check --update`. |
| **D12** | `openspec/specs/prompt-registry/spec.md` bootstrap | **YES — bootstrap in PR#2.** Copy REQ-45..50 from `openspec/changes/prompt-registry/spec.md` to `openspec/specs/prompt-registry/spec.md` as `v1.0` capability spec. The capability spec catalogs ALL 4 `PROMPT_REGISTRY` entries + 20 `SKILL_CATALOG` entries + the SKILL.md mirror contract + the `flow prompts` CLI surface contract. Marks as `v1.0`. Pattern: kebab-case folder per capability (mirrors observability D11). | Mirrors observability D11 (`openspec/specs/observability/spec.md` is the FIRST capability spec, bootstrapping the baseline). Cross-project-federation archive-report #61 explicitly defers the prompt-registry spec catalog to a future change — this IS that change. The spec is INFORMATIONAL (catalog + BDD scenarios); runtime code in `prompt_registry.py` / `prompt_render.py` / `prompt_lint.py` / `opencode_skill_catalog.py` does NOT import it. Once the baseline exists, future changes (e.g., `prompt-render-counters` for REQ-52) add specs to the same baseline. |

## Data Flow

### Prompt render (REQ-46)

```
render_prompt("strict_tdd", test_command="pytest")
   │
   ▼
PROMPT_REGISTRY["strict_tdd"]                         # prompt_registry.py
   │
   ├─► entry.template_id == "strict_tdd"
   ├─► entry.variables == ("test_command",)
   ├─► entry.location  == "<repo>/prompts/strict_tdd.j2"
   │
   ▼
shared_env = prompt_render._env()                     # hoisted from scaffold.py:20
   │
   ├─► loader = FileSystemLoader(<repo>/prompts)
   ├─► autoescape = select_autoescape(default_for_string=True)   # D2 (OQ-2)
   ├─► keep_trailing_newline = True
   │
   ▼
template = shared_env.get_template("strict_tdd.j2")
   │
   ▼
parsed = shared_env.parse("strict_tdd.j2")            # AST for lint
   │                                                   # jinja2.meta.find_undeclared_variables(parsed)
   │                                                   # → {"test_command"} (matches declared variables)
   ▼
rendered = template.render(test_command="pytest")
   │
   ▼
"STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
```

### Prompt lint (REQ-47)

```
lint_prompts(PROMPT_REGISTRY)
   │
   ▼
for prompt_id, entry in PROMPT_REGISTRY.items():
   │
   ├─► try:
   │     parsed = shared_env.parse(entry.location)
   │     declared = entry.variables                      # from PromptEntry
   │     referenced = jinja2.meta.find_undeclared_variables(parsed)
   │     │
   │     ├─► for ref in referenced - declared:
   │     │     warnings.append(LintWarning(prompt_id, "missing_placeholder",
   │     │                                  f"undefined variable '{ref}'", line=...))
   │     │
   │     ├─► for var in declared - referenced:
   │     │     warnings.append(LintWarning(prompt_id, "unused_variable",
   │     │                                  f"declared variable '{var}' not used", line=None))
   │     │
   │     └─► if not shared_env.autoescape:
   │           warnings.append(LintWarning(prompt_id, "autoescape_disabled",
   │                                       "autoescape is off", line=None))
   │
   └─► except jinja2.TemplateSyntaxError as exc:
         warnings.append(LintWarning(prompt_id, "template_parse_error",
                                     f"syntax error: {exc.message}",
                                     line=exc.lineno))
   │
   ▼
return warnings  # [] when clean; caller (CLI or pytest fixture) decides
```

### SKILL.md drift check (REQ-49)

```
check_drift(SKILL_CATALOG)
   │
   ▼
sidecar = json.loads(~/.flow-engineering/prompt_checksums.json)
   │
   ▼
for skill_name, entry in SKILL_CATALOG.items():
   │
   ├─► if not entry.expected_path.exists():
   │     drifts.append(SkillDrift(skill_name, entry.expected_version, "MISSING",
   │                              expected_checksum=entry.last_verified_checksum,
   │                              on_disk_checksum="", drift_kind="missing_file"))
   │     continue
   │
   ├─► try:
   │     frontmatter_yaml = read_frontmatter(entry.expected_path)   # parse YAML between --- markers
   │     canonical = json.dumps(frontmatter_yaml, sort_keys=True, separators=(",",":"))
   │     on_disk_checksum = sha256(canonical.encode("utf-8")).hexdigest()
   │
   ├─► except yaml.YAMLError as exc:
   │     drifts.append(SkillDrift(skill_name, entry.expected_version, "PARSE_ERROR",
   │                              expected_checksum=entry.last_verified_checksum,
   │                              on_disk_checksum="", drift_kind="frontmatter_parse_error"))
   │     continue
   │
   ├─► on_disk_version = frontmatter_yaml.get("version", "0.0")
   │
   ├─► if on_disk_checksum != entry.last_verified_checksum:
   │     drift_kind = "checksum_mismatch"
   │
   ├─► elif on_disk_version != entry.expected_version:
   │     drift_kind = "version_mismatch"
   │
   └─► else:
         continue  # no drift
   │
   ▼
return drifts  # [] when clean
```

### `flow prompts check --update` (REQ-49 + D9)

```
$ flow prompts check --update
   │
   ▼
@click check_prompts(...)                              # cli.py (NEW)
   │
   ├─► if --init:
   │     init_checksums(SKILL_CATALOG)                 # bootstrap sidecar
   │
   ├─► if --update:
   │     update_checksums(SKILL_CATALOG)               # refresh sidecar
   │     click.echo(json.dumps({updated: N, sidecar: str(...)}), err=True)
   │     sys.exit(0)
   │
   ├─► drifts = check_drift(SKILL_CATALOG)
   │
   ├─► for drift in drifts:
   │     click.echo(f"{drift.skill_name}: {drift.expected_version}: {drift.drift_kind}")
   │
   ├─► if drifts and not --no-fail:
   │     sys.exit(1)
   │
   └─► else:
         sys.exit(0)
```

## File Changes

### New files (~833 LOC production + ~2 260 LOC test)

| File | LOC prod | LOC test | Purpose |
|---|---|---|---|
| `src/flow_engineering/prompt_registry.py` | ~120 | — | `PROMPT_REGISTRY`, `PromptEntry` dataclass, 4 migrated entries; `REGISTRY_SCHEMA_VERSION` constant. |
| `src/flow_engineering/prompt_render.py` | ~150 | — | Jinja2 `Environment` (shared with `scaffold.py`), `render_prompt()`, `render_prompt_safe()`, `PromptRenderError`. |
| `src/flow_engineering/prompt_lint.py` | ~80 | — | `lint_prompts()`, `LintWarning` dataclass, 5 warning categories; `lint_registry_or_default()` helper. |
| `src/flow_engineering/opencode_skill_catalog.py` | ~120 | — | `SKILL_CATALOG`, `SkillEntry` dataclass (20 entries), `SkillDrift` dataclass, `check_drift()`, `update_checksums()`, `init_checksums()`, `SkillVersionError`, frontmatter parser. |
| `prompts/strict_tdd.j2` | ~4 | — | Jinja2 version of `STRICT_TDD_PROMPT`. |
| `prompts/auto_suggest_header.j2` | ~2 | — | Jinja2 version of `PROMPT_HEADER`. |
| `prompts/auto_suggest_footer.j2` | ~3 | — | Jinja2 version of `PROMPT_FOOTER`. |
| `prompts/auto_suggest_empty.j2` | ~1 | — | Jinja2 version of `EMPTY_PROMPT_TEXT`. |
| `openspec/specs/prompt-registry/spec.md` | ~150 | — | Capability spec cataloging 4 `PROMPT_REGISTRY` entries + 20 `SKILL_CATALOG` entries + SKILL.md mirror contract + `flow prompts` CLI surface contract. Bootstrap of `openspec/specs/prompt-registry/` baseline (D12). |
| `tests/unit/test_prompt_registry.py` | — | ~250 | `PROMPT_REGISTRY` schema + 4 migrated entries; rendering tests; frozen-dataclass mutation guard. |
| `tests/unit/test_prompt_render.py` | — | ~300 | `render_prompt()` with variables, missing variable, template error; `render_prompt_safe()` sentinel substitution; autoescape blocks HTML injection. |
| `tests/unit/test_prompt_lint.py` | — | ~250 | `lint_prompts()` with all 5 warning categories; clean registry lints clean; broken registry lints 3+ warnings. |
| `tests/unit/test_opencode_skill_catalog.py` | — | ~300 | `SKILL_CATALOG` schema + 20 entries; checksum computation; `check_drift()` with mock SKILL.md files; `init_checksums` / `update_checksums` sidecar write/read; `SkillVersionError` raised on `min_sdd_skill_versions` (REQ-54 stub). |
| `tests/unit/test_cli_prompts.py` | — | ~400 | Full CLI surface coverage for `flow prompts list/show/lint/check` (all 7 flags: `--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`); exit code matrix (0/1/2/3/5). |
| `tests/bdd/req45_prompt_registry.feature` | — | ~60 | 2 BDD scenarios. |
| `tests/bdd/req46_prompt_render.feature` | — | ~80 | 3 BDD scenarios. |
| `tests/bdd/req47_prompt_lint.feature` | — | ~60 | 2 BDD scenarios. |
| `tests/bdd/req49_skill_catalog.feature` | — | ~80 | 2 BDD scenarios. |
| `tests/bdd/req50_cli_prompts.feature` | — | ~80 | 3 BDD scenarios. |
| `tests/bdd/test_prompt_registry_steps.py` | — | ~400 | pytest-bdd glue shared across all 5 BDD features. |

### Modified files (~350 LOC delta)

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/strict_tdd.py` | +3 / -3 | Replace `STRICT_TDD_PROMPT` constant (3 lines) with 1-line wrapper: `STRICT_TDD_PROMPT = render_prompt("strict_tdd", test_command=cmd)` shape. Actually: keep the constant as a string for backwards compat (callers use `.format(test_command=cmd)`) AND route `build_strict_tdd_instruction` through `render_prompt_safe()` so the `.format()` legacy path still works for v0.7.0. |
| `src/flow_engineering/auto_suggest_code_refs.py` | +10 / -10 | Replace 3 inline constants (`EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) with thin wrappers that delegate to `render_prompt()`. `format_suggestion_prompt()` continues to use the constants — no behavior change. |
| `src/flow_engineering/scaffold.py` | +5 / -10 | `_env()` becomes a thin re-export from `prompt_render._env()`. The `FileSystemLoader` switches from `templates/` to the configurable prompts directory (default `<repo>/prompts/`); existing `_env()` callers get `templates/` via a separate `scaffold._env()` that points to the package templates. |
| `src/flow_engineering/cli.py` | +150 | New `flow prompts` Click group + 4 subcommands (`list`, `show <id>`, `lint`, `check`) with 7 flags (`--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`). ~150 prod LOC delta. |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | +150 (runtime-only) | Add `## Prompt registry hook` section referencing REQ-45 `PROMPT_REGISTRY` for prompt discovery. Runtime-only; not in repo. |
| `CHANGELOG.md` | +25 | v0.7.0 entry post-PR#2-merge. |
| `pyproject.toml` | +10 | Version bump to 0.7.0; new `[tool.flow_engineering.prompts]` section for registry path + lint settings + sidecar path. |

**Production total**: ~833 LOC across 4 new + 3 modified + 4 new `.j2` files + 1 new spec file = 12 files.
**Test total**: ~2 260 LOC across 5 new unit + 5 new BDD feature + 1 BDD glue = 11 files.
**Strict-TDD ratio**: ~2.7× (within the 2-4× target band from
`decision-code-linking` S3 precedent; the realistic ×6 multiplier is
absorbed into the 2-chained-PR split).

## Module/File Layout

For each NEW file:

### `src/flow_engineering/prompt_registry.py` (NEW, ~120 prod LOC)

**Purpose**: Central `PROMPT_REGISTRY` catalog of all `flow` prompt artifacts,
mirroring the `VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` catalog
pattern at `observability.py:90, 129`.

**Public API**:
```python
REGISTRY_SCHEMA_VERSION: str = "1.0"

@dataclass(frozen=True)
class PromptEntry:
    template_id: str             # relative path to .j2 file (without extension)
    version: str                 # semver of the entry (e.g., "1.0.0")
    owner: str                   # e.g., "flow/observability"
    location: str                # absolute path to .j2 file (resolved at import time)
    variables: tuple[str, ...]   # declared Jinja2 variable names
    schema_version: str          # "1.0" (must match REGISTRY_SCHEMA_VERSION)

PROMPT_REGISTRY: dict[str, PromptEntry] = {
    "strict_tdd": PromptEntry(...),
    "auto_suggest_header": PromptEntry(...),
    "auto_suggest_footer": PromptEntry(...),
    "auto_suggest_empty": PromptEntry(...),
}

def get_prompts_dir() -> Path:
    """Return the configured prompts directory (from pyproject.toml or default <repo>/prompts/)."""
```

**Test file**: `tests/unit/test_prompt_registry.py` (~250 LOC; covers schema
validation, 4-entry migration, frozen-dataclass mutation guard, `get_prompts_dir()`).

### `src/flow_engineering/prompt_render.py` (NEW, ~150 prod LOC)

**Purpose**: Shared Jinja2 `Environment` (hoisted from `scaffold.py:20`) +
`render_prompt()` + `render_prompt_safe()` + `PromptRenderError`.

**Public API**:
```python
class PromptRenderError(Exception): ...
class PromptNotFoundError(PromptRenderError): ...

def _env(prompts_dir: Path | None = None) -> Environment:
    """Build the shared Jinja2 Environment. Hoisted from scaffold.py:20."""

def render_prompt(prompt_id: str, **variables: Any) -> str:
    """Render a prompt from PROMPT_REGISTRY. Hard-fails on missing variable."""

def render_prompt_safe(prompt_id: str, **variables: Any) -> str:
    """Render with <{var_name}> sentinel for missing declared variables."""
```

**Test file**: `tests/unit/test_prompt_render.py` (~300 LOC; covers rendering
with variables, missing variable, template error, autoescape, safe sentinel).

### `src/flow_engineering/prompt_lint.py` (NEW, ~80 prod LOC)

**Purpose**: `lint_prompts()` validator with 5 warning categories.

**Public API**:
```python
@dataclass(frozen=True)
class LintWarning:
    prompt_id: str
    category: str                # "missing_placeholder" | "unused_variable" | "template_parse_error" | "autoescape_disabled" | "missing_variable"
    message: str
    line: int | None = None

def lint_prompts(registry: dict[str, PromptEntry] | None = None) -> list[LintWarning]:
    """Validate the registry. None defaults to PROMPT_REGISTRY."""

# Severity map for flow prompts lint CLI
LINT_CATEGORY_SEVERITY: dict[str, str] = {
    "missing_placeholder": "error",
    "unused_variable": "warning",
    "template_parse_error": "error",
    "autoescape_disabled": "error",
    "missing_variable": "error",
}
```

**Test file**: `tests/unit/test_prompt_lint.py` (~250 LOC; covers all 5
warning categories, clean registry lints clean, broken registry lints 3+
warnings).

### `src/flow_engineering/opencode_skill_catalog.py` (NEW, ~120 prod LOC)

**Purpose**: `SKILL_CATALOG` mirror for the OpenCode runtime SKILL.md surface
with SHA-256 frontmatter checksums and `check_drift()`.

**Public API**:
```python
SIDECAR_PATH: Path = Path.home() / ".flow-engineering" / "prompt_checksums.json"

@dataclass(frozen=True)
class SkillEntry:
    skill_name: str              # e.g., "sdd-apply"
    surface: str                 # "skill" | "prompt"  (20 entries: 10 of each)
    expected_version: str        # semver minimum from frontmatter
    expected_path: str           # absolute path to file
    last_verified_checksum: str  # SHA-256 of frontmatter YAML dict
    owner: str                   # typically "gentleman-programming"

@dataclass(frozen=True)
class SkillDrift:
    skill_name: str
    surface: str
    expected_version: str
    on_disk_version: str
    expected_checksum: str
    on_disk_checksum: str
    drift_kind: str              # "checksum_mismatch" | "version_mismatch" | "missing_file" | "frontmatter_parse_error"

class SkillVersionError(Exception): ...

SKILL_CATALOG: dict[str, SkillEntry] = {
    "sdd-init/skill": SkillEntry(...),
    "sdd-init/prompt": SkillEntry(...),
    # ... 18 more entries
}

def _sidecar_path() -> Path: ...
def _read_sidecar() -> dict[str, dict[str, str]]: ...
def _write_sidecar(sidecar: dict[str, dict[str, str]]) -> None: ...
def check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]: ...
def update_checksums(catalog: dict[str, SkillEntry] | None = None) -> int: ...
def init_checksums(catalog: dict[str, SkillEntry] | None = None) -> int: ...
def _compute_frontmatter_checksum(path: Path) -> str: ...
def _parse_frontmatter(path: Path) -> dict[str, Any]: ...
```

**Test file**: `tests/unit/test_opencode_skill_catalog.py` (~300 LOC; covers
catalog schema, 20 entries, checksum computation, `check_drift()` with mock
SKILL.md files, `init_checksums` / `update_checksums` sidecar I/O,
`SkillVersionError`).

## Data Model

### `PromptEntry` dataclass

```python
@dataclass(frozen=True)
class PromptEntry:
    template_id: str             # e.g., "strict_tdd"
    version: str                 # semver "1.0.0"
    owner: str                   # "flow/observability" | "flow/binding" | "flow/scaffold"
    location: str                # absolute path; resolved at import time
    variables: tuple[str, ...]   # declared Jinja2 variable names (may be empty)
    schema_version: str          # MUST equal REGISTRY_SCHEMA_VERSION ("1.0")
```

**Validation rules** (enforced by `lint_prompts` and unit tests):
- `template_id` MUST be non-empty and kebab-or-snake-case `[a-z0-9_-]+`.
- `version` MUST be valid semver (`^\d+\.\d+\.\d+$`).
- `owner` MUST be non-empty and contain a `/` (e.g., `flow/observability`).
- `location` MUST point to an existing file under `get_prompts_dir()`.
- `variables` MUST be a tuple of unique strings (no duplicates).
- `schema_version` MUST equal `REGISTRY_SCHEMA_VERSION` (defensive: lint
  fails on mismatch).

### `LintWarning` dataclass

```python
@dataclass(frozen=True)
class LintWarning:
    prompt_id: str
    category: str                # see LINT_CATEGORY_SEVERITY
    message: str
    line: int | None = None      # template line number; None for global checks
```

### `SkillEntry` dataclass

```python
@dataclass(frozen=True)
class SkillEntry:
    skill_name: str              # "sdd-apply" (without surface suffix)
    surface: str                 # "skill" | "prompt"
    expected_version: str        # semver "3.0"
    expected_path: str           # absolute path
    last_verified_checksum: str  # 64-char hex (SHA-256)
    owner: str                   # "gentleman-programming"
```

**Validation rules**:
- `skill_name` MUST be non-empty and lowercase `[a-z0-9-]+`.
- `surface` MUST be in `{"skill", "prompt"}`.
- `expected_version` MUST be valid semver `MAJOR.MINOR`.
- `expected_path` MUST be an absolute path; `last_verified_checksum` MUST be
  64-char lowercase hex.
- 20 catalog entries: 10 skill (one per sdd-* agent) + 10 prompt (one per
  sdd-* agent).

### Sidecar JSON shape

```json
{
  "sdd-apply/skill": {
    "version": "3.0",
    "checksum": "abc123...",
    "last_verified_at": "2026-06-27T12:00:00Z"
  },
  "sdd-apply/prompt": {
    "version": "3.0",
    "checksum": "def456...",
    "last_verified_at": "2026-06-27T12:00:00Z"
  }
}
```

Keys are `<skill_name>/<surface>`. Values include the on-disk version at the
time of last verification (for diff against current `expected_version`),
the SHA-256 of the canonicalized frontmatter YAML dict, and the ISO 8601
timestamp of the last `check --update` invocation.

## Algorithm Details

### Render with sentinel substitution (REQ-46, OQ-4)

**Pseudocode** (`render_prompt_safe`):

```python
def render_prompt_safe(prompt_id: str, **variables: Any) -> str:
    """Render with <{var_name}> sentinel for missing declared variables.

    Used by `flow prompts show <id>` only. Runtime callers MUST use
    `render_prompt()` for hard-fail behavior.
    """
    entry = PROMPT_REGISTRY[prompt_id]                 # KeyError → PromptNotFoundError
    declared = set(entry.variables)
    provided = set(variables.keys())
    missing = declared - provided

    if missing:
        # Sentinel substitution: build a "safe" kwargs dict where missing
        # vars get the literal <{var_name}> sentinel.
        safe_kwargs: dict[str, Any] = dict(variables)
        for var_name in missing:
            safe_kwargs[var_name] = f"<{var_name}>"
        variables = safe_kwargs

    try:
        return _env().get_template(entry.template_id + ".j2").render(**variables)
    except jinja2.UndefinedError as exc:
        raise PromptRenderError(f"undefined variable in {prompt_id}: {exc.message}") from exc
```

**Edge cases**:
- Unknown `prompt_id` → `KeyError` from `PROMPT_REGISTRY[prompt_id]`; wrapped
  in `PromptNotFoundError` by the caller (CLI exits 5).
- Empty `variables` for a template with no declared variables → renders as-is.
- `test_command="pytest"` substituted → autoescape converts `<` to `&lt;`
  (defensive; BDD scenario REQ-46 S2 asserts the autoescape case).
- Template parse error → wrapped in `PromptRenderError`; CLI exits 3.

### Frontmatter checksum (REQ-49, OQ-5)

**Pseudocode**:

```python
import hashlib
import json
import re
from pathlib import Path

FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def _compute_frontmatter_checksum(path: Path) -> str:
    """SHA-256 of the canonicalized YAML frontmatter dict.

    Reads the file, extracts the YAML block between `---` markers, parses
    via PyYAML, canonicalizes via JSON-dump with sorted keys, and hashes.
    Returns the 64-char lowercase hex digest.
    """
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise SkillVersionError(f"{path}: no YAML frontmatter found")
    raw_yaml = match.group(1)
    parsed = yaml.safe_load(raw_yaml)
    if not isinstance(parsed, dict):
        raise SkillVersionError(f"{path}: frontmatter is not a YAML dict")
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

**Edge cases**:
- File missing → `Path.read_text()` raises `FileNotFoundError`; caller
  wraps in `SkillDrift(drift_kind="missing_file")`.
- No frontmatter → regex fails to match → `SkillVersionError`; caller wraps
  in `SkillDrift(drift_kind="frontmatter_parse_error")`.
- Frontmatter not a dict (e.g., a YAML scalar) → `SkillVersionError`; same
  drift_kind.
- Unicode in frontmatter → `ensure_ascii=False` preserves UTF-8 bytes
  before hashing.

### Drift check (REQ-49, D8)

**Pseudocode**:

```python
def check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]:
    catalog = catalog or SKILL_CATALOG
    sidecar = _read_sidecar()                          # {} when missing
    drifts: list[SkillDrift] = []

    for key, entry in catalog.items():
        sidecar_entry = sidecar.get(key, {})
        expected_checksum = sidecar_entry.get("checksum", "")
        expected_version = sidecar_entry.get("version", entry.expected_version)
        # If sidecar has no entry yet, use the catalog's expected_version
        # (covers the first-ever check before --init).

        if not Path(entry.expected_path).exists():
            drifts.append(SkillDrift(
                skill_name=entry.skill_name, surface=entry.surface,
                expected_version=expected_version, on_disk_version="",
                expected_checksum=expected_checksum, on_disk_checksum="",
                drift_kind="missing_file",
            ))
            continue

        try:
            on_disk_checksum = _compute_frontmatter_checksum(Path(entry.expected_path))
            frontmatter = _parse_frontmatter(Path(entry.expected_path))
            on_disk_version = str(frontmatter.get("version", "0.0"))
        except (SkillVersionError, yaml.YAMLError) as exc:
            drifts.append(SkillDrift(
                skill_name=entry.skill_name, surface=entry.surface,
                expected_version=expected_version, on_disk_version="",
                expected_checksum=expected_checksum, on_disk_checksum="",
                drift_kind="frontmatter_parse_error",
            ))
            continue

        if on_disk_checksum != expected_checksum:
            drifts.append(SkillDrift(
                skill_name=entry.skill_name, surface=entry.surface,
                expected_version=expected_version, on_disk_version=on_disk_version,
                expected_checksum=expected_checksum, on_disk_checksum=on_disk_checksum,
                drift_kind="checksum_mismatch",
            ))
        elif on_disk_version != expected_version:
            drifts.append(SkillDrift(
                skill_name=entry.skill_name, surface=entry.surface,
                expected_version=expected_version, on_disk_version=on_disk_version,
                expected_checksum=expected_checksum, on_disk_checksum=on_disk_checksum,
                drift_kind="version_mismatch",
            ))

    return drifts
```

**Edge cases**:
- Empty catalog → empty `drifts` list.
- Sidecar missing (first run before `--init`) → `expected_checksum=""` →
  every entry reports `checksum_mismatch`. Mitigation: BDD scenario GIVEN
  fresh install THEN `flow prompts check --init` bootstraps the sidecar
  AND exits 0.
- All checksums match → empty `drifts`; CLI exits 0.
- One entry missing → one `SkillDrift` with `drift_kind="missing_file"`;
  CLI prints the missing file path, exits 1 (unless `--no-fail`).

## Error Handling

| Error mode | Exit code | User-facing message (stderr unless noted) | Affected subcommand |
|---|---|---|---|
| Unknown prompt id on `show` | 5 | `{"error": "unknown prompt id", "prompt_id": "<id>", "hint": "run 'flow prompts list' to see available"}` (stderr) | `flow prompts show <unknown>` |
| Template parse error on render | 3 | `{"error": "template parse error", "prompt_id": "<id>", "cause": "<jinja2 message>"}` (stderr) | `render_prompt(<id>)` |
| Missing variable on `render_prompt()` | 3 | `{"error": "missing variable", "prompt_id": "<id>", "variable": "<name>"}` (stderr) | `render_prompt(<id>)` |
| Lint clean | 0 | (stdout) `<prompt_id>: OK` per entry; footer `4 prompts linted · 0 warnings · 0 errors` | `flow prompts lint` |
| Lint warnings (no `--strict`) | 1 | (stdout) `<prompt_id>: <category>: <message>` lines; footer `4 prompts linted · N warnings · 0 errors` | `flow prompts lint` |
| Lint errors OR `--strict` with warnings | 2 | (stdout) `<prompt_id>: <category>: <message>` lines; footer `4 prompts linted · N warnings · M errors` | `flow prompts lint` |
| `--strict` flag with no warnings | 0 | (stdout) same as clean lint | `flow prompts lint --strict` |
| Drift detected (default) | 1 | (stdout) `<skill_name>/<surface>: <expected_version>: <drift_kind>` per entry; footer `20 skills verified · N drift detected` | `flow prompts check` |
| `--no-fail` flag with drift | 0 | (stdout) same as drift | `flow prompts check --no-fail` |
| `--update` flag | 0 | (stderr) `{"updated": N, "sidecar": "<path>"}`; (stdout) `<skill_name>: OK` | `flow prompts check --update` |
| `--init` flag (first run) | 0 | (stderr) `{"initialized": N, "sidecar": "<path>"}`; (stdout) `<skill_name>: OK` | `flow prompts check --init` |
| SKILL.md missing file | 1 | (stdout) `<skill_name>/<surface>: MISSING` | `flow prompts check` |
| Frontmatter parse error | 1 | (stdout) `<skill_name>/<surface>: PARSE_ERROR` | `flow prompts check` |
| Usage error (invalid flag combo) | 2 | Click's standard usage error message | all `flow prompts` subcommands |
| Sidecar I/O failure | 4 | `{"error": "sidecar write failed", "path": "<path>", "cause": "<strerror>"}` (stderr) | `flow prompts check --update` / `--init` |

**Rationale**: empty/no-matches → exit 0; usage errors → exit 2 (Click
standard); data errors → exit 3 (`git`/`curl` convention); I/O errors → exit
4 (`flow snapshot rollback` precedent from graph-snapshots); drift/warnings
→ exit 1 (`flow drift --no-fail` precedent); unknown id → exit 5 (`flow
inspect <unknown>` precedent at cli.py:940). JSON to stderr keeps stdout
clean for piping (`flow prompts lint | grep error`).

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `PROMPT_REGISTRY` schema | All 4 entries have required 6 fields; `schema_version` matches `REGISTRY_SCHEMA_VERSION`; mutation guard (frozen dataclass raises `FrozenInstanceError`). |
| Unit | `render_prompt()` with variables | Render `strict_tdd` with `test_command="pytest"`; assert output string equals expected. |
| Unit | `render_prompt()` missing variable | Render `strict_tdd` without kwargs → `PromptRenderError` mentioning `test_command`. |
| Unit | `render_prompt_safe()` sentinel | Render `strict_tdd` without kwargs → output contains `<test_command>` literal. |
| Unit | Autoescape blocks HTML injection | Render `strict_tdd` with `test_command="<script>alert(1)</script>"` → output contains `&lt;script&gt;` (escaped). |
| Unit | `lint_prompts()` 5 categories | For each category, build a broken registry with the specific defect; assert 1 `LintWarning` with the expected `category`. |
| Unit | `lint_prompts()` clean registry | Call with `PROMPT_REGISTRY` → returns `[]`. |
| Unit | `lint_prompts()` performance | 4-entry registry lints in <100ms (sanity). |
| Unit | `SKILL_CATALOG` schema | All 20 entries have required 6 fields; 10 skill + 10 prompt split; every sdd-* agent appears twice (one per surface). |
| Unit | `_compute_frontmatter_checksum()` | Mock SKILL.md with known frontmatter; assert SHA-256 matches precomputed digest. |
| Unit | `check_drift()` clean state | Mock SKILL.md with matching sidecar → returns `[]`. |
| Unit | `check_drift()` checksum mismatch | Mock SKILL.md with edited content → returns 1 `SkillDrift` with `drift_kind="checksum_mismatch"`. |
| Unit | `check_drift()` missing file | Mock expected_path that doesn't exist → returns 1 `SkillDrift` with `drift_kind="missing_file"`. |
| Unit | `check_drift()` whitespace-only diff (REQ-49 negative test) | Mock SKILL.md with body whitespace changed but frontmatter unchanged → returns `[]` (frontmatter-only checksum per OQ-5). |
| Unit | `init_checksums()` | Sidecar missing → writes all 20 entries; returns 20. |
| Unit | `update_checksums()` | Sidecar stale → overwrites with fresh checksums; returns count. |
| Unit | `flow prompts list` | Text table has 4 entries grouped by owner; `--json` emits flat dict. |
| Unit | `flow prompts show <id>` | Renders expected string with `--var key=value`; sentinel for missing var; exit 5 on unknown id. |
| Unit | `flow prompts lint` | Exit codes 0/1/2 across warning/error scenarios; `--strict` flag maps warnings → errors. |
| Unit | `flow prompts check` | Exit 0 clean; exit 1 drift; `--no-fail` exit 0 drift; `--update` exit 0 + sidecar write; `--init` exit 0 + sidecar bootstrap; `--skill <name>` filters to one entry. |
| BDD (REQ-45) | Registry has 4 entries | GIVEN 4 inline prompts migrated WHEN `import PROMPT_REGISTRY` THEN dict has 4 keys + every entry has 6 required fields |
| BDD (REQ-45) | KeyError on unknown | GIVEN PROMPT_REGISTRY WHEN `PROMPT_REGISTRY["nonexistent"]` THEN raises KeyError |
| BDD (REQ-46) | Render with no kwargs | GIVEN `auto_suggest_header` with variables=() WHEN `render_prompt("auto_suggest_header")` THEN returns template as-is |
| BDD (REQ-46) | Render with kwargs | GIVEN `strict_tdd` with variables=("test_command",) WHEN `render_prompt("strict_tdd", test_command="pytest")` THEN output equals expected |
| BDD (REQ-46) | Render missing var fails | GIVEN `strict_tdd` WHEN `render_prompt("strict_tdd")` THEN raises PromptRenderError mentioning test_command |
| BDD (REQ-47) | Lint passes for well-formed | GIVEN 4 PROMPT_REGISTRY entries are well-formed WHEN `lint_prompts(PROMPT_REGISTRY)` THEN returns `[]` |
| BDD (REQ-47) | Lint fails for typo | GIVEN broken entry "broken" with `{{ test_comand }}` WHEN `lint_prompts(broken_registry)` THEN 1 LintWarning with category=missing_placeholder |
| BDD (REQ-49) | Check-drift detects drift | GIVEN sidecar stale + on-disk SKILL.md edited WHEN `check_drift(SKILL_CATALOG)` THEN returns 1 SkillDrift with drift_kind=checksum_mismatch |
| BDD (REQ-49) | Check-drift passes when fresh | GIVEN sidecar fresh + on-disk unchanged WHEN `check_drift(SKILL_CATALOG)` THEN returns `[]` |
| BDD (REQ-50) | list shows all prompts | GIVEN 4 entries WHEN `flow prompts list` THEN stdout has 4 rows + footer "4 prompt entries" |
| BDD (REQ-50) | show renders with kwargs | GIVEN strict_tdd WHEN `flow prompts show strict_tdd --var test_command=pytest` THEN stdout contains rendered string + "autoescape=on" footer |
| BDD (REQ-50) | lint exits non-zero on errors | GIVEN broken registry WHEN `flow prompts lint` THEN exits 2 |
| Secrets invariant | Catalog doesn't leak paths | GIVEN a prompt template mentions `secrets.yaml` WHEN `render_prompt("strict_tdd", test_command="pytest")` THEN output contains ONLY "pytest"; no path leaks |

**Unit test count forecast**: ~30-35 new unit tests across 5 new files
(`test_prompt_registry.py` ~8, `test_prompt_render.py` ~10, `test_prompt_lint.py` ~8,
`test_opencode_skill_catalog.py` ~10, `test_cli_prompts.py` ~12).

**BDD scenarios**: 12 (per spec REQ-45 ×2, REQ-46 ×3, REQ-47 ×2, REQ-49 ×2, REQ-50 ×3).

**Coverage targets**: 95% line coverage on the new helpers; 100% coverage on
the error-path branches (D9). `ruff check` clean on all changed files.

**Strict TDD order** per `decision-code-linking` S3 precedent:
1. `prompt_registry.py` `PROMPT_REGISTRY` — RED: 4-entry schema →
   GREEN: dataclass + 4 entries → REFACTOR: frozen guard
2. `prompt_render.py` `_env()` — RED: import fails → GREEN: hoisted factory → REFACTOR
3. `prompt_render.py` `render_prompt()` — RED: missing function → GREEN: basic render → REFACTOR: missing-var error path
4. `prompt_render.py` `render_prompt_safe()` — RED: missing function → GREEN: sentinel substitution → REFACTOR: edge cases
5. `prompt_lint.py` `lint_prompts()` — RED: empty list → GREEN: 5 categories → REFACTOR: severity map
6. `opencode_skill_catalog.py` `_compute_frontmatter_checksum()` — RED: missing → GREEN: SHA-256 of fixture → REFACTOR: canonical JSON
7. `opencode_skill_catalog.py` `check_drift()` — RED: missing → GREEN: 4 drift kinds → REFACTOR: sidecar I/O
8. `cli.py` `flow prompts list/show/lint/check` — RED: CliRunner → GREEN: flag matrix → REFACTOR: exit code D9
9. `tests/bdd/req45/46/47/49/50_*.feature` + `test_prompt_registry_steps.py` — RED → GREEN → REFACTOR

## Migration / Rollout

**No data migration** is required. The user's existing `~/.flow-engineering/metrics.jsonl`
stays untouched. Two opt-in rollout paths:

1. **Operators who want prompt discovery** — run `flow prompts list` (no flags).
   No migration, no setup. The 4-entry registry is populated at import time.

2. **Operators who want SKILL.md drift detection** — run `flow prompts check --init`
   once to bootstrap `~/.flow-engineering/prompt_checksums.json`. Subsequent
   `flow prompts check` invocations report drift.

**Rollback** per-PR (revert merge; all additive):
- PR#1 revert: 4 inline constants return to their inline-string form. The 4
  new modules (`prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`)
  become unused; deleting them restores the v0.6.0 prompt surface byte-identically.
- PR#2 revert: `flow prompts` CLI group disappears. `SKILL_CATALOG` module
  becomes unused; deleting it restores the v0.7.0-PR#1 state.
- `openspec/specs/prompt-registry/spec.md` is a NEW file; deleting it
  removes the capability spec but does not break runtime behavior.
- 5 BDD feature files are NEW; removing them disables BDD coverage for
  the new REQs but does not break the existing 783 tests.
- The user's `~/.flow-engineering/prompt_checksums.json` is a NEW sidecar;
  deleting it forces `flow prompts check --init` on next run.
- The 4 new `.j2` files (`prompts/*.j2`) are NEW; deleting them re-enables
  the inline strings.
- The `~/.config/opencode/skills/sdd-*/SKILL.md` updates are runtime-only;
  reverting them does not affect `flow` behavior.

To restore the pre-change-#7 install: `git revert <PR#1-merge> <PR#2-merge>`.
The JSONL event format is unchanged; the user's existing metrics data
survives intact.

## Open Questions — RESOLVED (all 10 from proposal §5)

| # | Question | Resolution |
|---|---|---|
| **1** | `prompts/` directory location | **Repo root (`<repo>/prompts/`)** per D1 + D2. Mirrors `openspec/` first-class artifact convention; allows future external tooling to read prompt files without `import flow_engineering`. `src/flow_engineering/templates/` is NOT mirrored (different audience, blocks external readers). Configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (default `<repo>/prompts/`). |
| **2** | Jinja2 autoescape scope | **`select_autoescape(enabled_extensions=(), default_for_string=True)`** per D3. Autoescape ALL string variables by default (defensive against untrusted variable substitution). BDD scenario REQ-46 S2 explicitly tests the autoescape case for `<` and `&` characters in `test_command`. |
| **3** | Prompt schema versioning | **Per-prompt `version: semver` (e.g., `"1.0.0"`) in `PromptEntry`** per D3. Registry-wide `schema_version` constant (e.g., `"1.0"`) for the `PromptEntry` shape itself; lint fails on `schema_version` mismatch across entries. |
| **4** | `flow prompts show` missing-variable behavior | **(c) Sentinel for `flow prompts show` via `render_prompt_safe()`; (a) hard fail for runtime `render_prompt()`** per D3. Sentinel format: `<{var_name}>` (e.g., `<test_command>`); informative for CLI inspection, prevents silent corruption in runtime. |
| **5** | SKILL.md checksum strategy | **Frontmatter-only SHA-256** per D3. Parse YAML between `---` markers, canonicalize via `json.dumps(parsed, sort_keys=True, separators=(",", ":"))`, hash. Ignores whitespace drift in the body. `--strict` flag flips to full-file SHA-256 for paranoid mode. BDD scenario GIVEN whitespace-only body diff THEN no drift (REQ-49 negative test). |
| **6** | SKILL_CATALOG coverage | **BOTH surfaces, 20 entries total** per D6. 10 `~/.config/opencode/skills/sdd-*/SKILL.md` + 10 `~/.config/opencode/prompts/sdd/*.md`. Each sdd-* agent appears twice in the catalog (one entry per surface). `flow prompts check` reports drift per entry. |
| **7** | `.j2` metadata sidecars | **Python-only for v1** per D2 + D7. `PromptEntry` dataclass in `prompt_registry.py` is the single source of truth; `.j2` files contain ONLY template body. Defer frontmatter-style `.j2` to v1.1 if external tooling needs it (additive, non-breaking). |
| **8** | `STRICT_TDD_PROMPT` migration strategy | **(c) Alias for v0.7.0, remove in v0.8.0** per D10. The 4 existing inline constants become thin 1-line wrappers around `render_prompt()` for v0.7.0; removed in v0.8.0 per project deprecation pattern. External imports keep working for one release cycle. |
| **9** | `flow prompts check --update` auto-update | **(b) Report + opt-in `--update` flag** per D9. Default `flow prompts check` reports drift + exits 1; `--update` writes fresh checksums + exits 0; `--no-fail` suppresses non-zero exit (CI compat). Auto-update is NEVER the default (silent corruption risk). |
| **10** | REQ-52 prompt observability counters | **Same `observability.py` catalog** per D12. When REQ-52 lands in v1.1, add 3 counters (`prompts_render_total`, `prompts_render_ms`, `prompts_render_failed_total`) to the existing catalog alongside `VECTOR_COUNTER_NAMES` / `FEDERATED_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES`. Change #6 ships the read-side (`flow metrics`); change #7 ships the write-side for prompt counters. No new module. |

**Resolved: 10/10. Remaining: 0.**

## Unblocks / Constraints

**Unblocks**:
- **Discoverable prompt surface** for the 4 inline + 4 Jinja2 + 10 OpenCode
  runtime prompts already shipped (REQ-45 + REQ-49). `flow prompts list`
  answers "what prompts exist in `flow`?" without `grep -r PROMPT src/`.
- **Linted prompt registry** catching typos at CI time (REQ-47). The
  `prompt_lint_clean` pytest fixture is the regression gate; failing the
  test build if any `error` category surfaces.
- **CLI surface for prompt inspection** (REQ-50). `flow prompts show <id>`
  renders the resolved template with `--var key=value` substitution.
- **Manifest-driven SKILL.md drift detection** replacing the 6-file
  hand-edit pattern from `graph-snapshots` (REQ-49). `flow prompts check`
  walks the catalog, SHA-256s each on-disk SKILL.md frontmatter, reports
  drift; `--update` flag refreshes the sidecar.
- **Deterministic, versioned, regression-tested prompt surface** that future
  LLM-backed REQs (e.g., "REQ-NN: `flow drift --llm-summary`" or "REQ-MM:
  auto-prompt-tuning") can plug into.
- **The project's `openspec/specs/` baseline** (D12) — change #6 was the
  FIRST capability spec; change #7 is the SECOND, solidifying the kebab-case
  convention.

**Constrains**:
- Any future change that adds a prompt MUST either add it to
  `PROMPT_REGISTRY` (with `version`, `owner`, `variables`, `schema_version`)
  or update the `schema_version` constant. The BDD scenario "GIVEN a
  prompt THEN its entry is in the registry" enforces this.
- The 4 existing inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`,
  `PROMPT_HEADER`, `PROMPT_FOOTER`) are thin wrappers for v0.7.0 only and
  MUST be removed in v0.8.0 (per D10 alias convention).
- The `prompt_fn=Callable` injection point at `engram_io.py:541` is preserved
  as-is (testable seam still works).
- The flat text default of `flow metrics` is unaffected (no changes to
  the observability CLI surface).
- `scaffold.py:_env()` is preserved as a thin re-export from
  `prompt_render._env()` (no import cycle, per D11).

## Out-of-Scope (consolidated)

The following 15 items are explicitly out of scope for change #7 and belong
to named follow-ups (mirrors `vector-semantic-search` and `cross-project-federation`
deferral patterns):

1. **REQ-48** — Golden regression tests (`tests/golden/prompts/<prompt_id>.txt`
   snapshots for every `PROMPT_REGISTRY` entry). Defer to v1.1; bundle into
   PR#1 if scope allows.
2. **REQ-51** — `prompt_renders.jsonl` append-only sink at
   `~/.flow-engineering/prompt_renders.jsonl`. Parallels `metrics.jsonl`.
   Opt-in via `FLOW_PROMPT_LOG=1`. Defer to v1.1.
3. **REQ-52** — Prompt observability counters (`prompts_render_total{prompt_id,
   version}`, `prompts_render_ms`, `prompts_render_failed_total{reason}`).
   Per D12, when these land, add them to the existing `observability.py`
   catalog (not a new module). Defer to v1.1 (bundles with REQ-51).
4. **REQ-53** — `docs/prompts.md` generated from `PROMPT_REGISTRY` at build
   time. Flat list of every entry with `{prompt_id, purpose, where it
   appears, example output}`. Defer to v1.1.
5. **REQ-54** — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`;
   `flow apply` / `verify` / `archive` assert at startup that the on-disk
   SKILL.md version is >= the minimum; raises `SkillVersionError`. Could
   bundle into PR#2 if scope allows; otherwise defer to v1.1.
6. **LLM client integration** — any actual `openai` / `anthropic` /
   `litellm` / `langchain` dependency. NEVER (out of project scope per
   explore C.5; the registry is provider-agnostic and the LLM call is
   someone else's job).
7. **i18n / multi-language prompts** — defer to v1.1+ (no current need; 1
   active user).
8. **Prompt A/B testing infrastructure** — defer to v1.1+ (only 4 prompts
   today; no statistical power for A/B).
9. **External prompt marketplace / community registry** — NEVER (single-user
   tool; out of project scope).
10. **Federated prompt registry** (per-project prompt catalogs) — defer
    until `cross-project-federation` extension surfaces a concrete need;
    resolution from explore C.4 / archive-report #61.
11. **Histogram metric type in observability** for `prompts_render_ms` — v1
    (when REQ-52 lands) emits `summary` type; `histogram` type deferred
    until someone needs bucket math.
12. **Prompt template caching** — Jinja2 templates are already cached by
    the `Environment`; no additional layer needed for v1.
13. **Async `render_prompt_async()`** — v1 is sync; async variant deferred
    until a real async caller materializes (none in the current codebase).
14. **Per-prompt-per-language sidecar files** — defer to i18n work (v1.1+).
15. **CLI flags for prompt introspection beyond `list/show/lint/check`** —
    defer until a real use case surfaces.

## Risks

The 12 risks from proposal §6 are reduced to 7 carry-forwards + 0 new
risks identified during the design phase. The risks below incorporate
the mitigations noted in the proposal:

| # | Risk | Likelihood | Severity | Status |
|---|---|---|---|---|
| 1 | `observability` (change #6) does not archive before change #7 apply starts → `PROMPT_REGISTRY` mirrors an unstable catalog pattern | HIGH | MED | MITIGATED — orchestrator must coordinate: change #6 ARCHIVE before change #7 APPLY. PR#1 SPEC references the observability pattern by name only (catalogs are independent modules; PR#1 SPEC is resilient to additions). |
| 2 | PR#1 cumulative realistic ~3 600 LOC > 400-line review budget; reviewers lose context | MED | MED | MITIGATED — per-commit work-unit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC). Mirror `cross-project-federation` chained-PR pattern. |
| 3 | Migration of `STRICT_TDD_PROMPT` / `PROMPT_HEADER` / `PROMPT_FOOTER` / `EMPTY_PROMPT_TEXT` breaks existing tests that hardcode the prompt strings | MED | MED | MITIGATED — Run all 783 tests after migration; v0.7.0 ships thin wrapper re-exports (per D10 alias) so external imports keep working; update test fixtures to use `render_prompt()` + golden snapshots (REQ-48 in v1.1). |
| 4 | SKILL.md checksum drift detection produces false positives on whitespace-only changes | MED | LOW | MITIGATED — Frontmatter-only checksum per D3 + OQ-5 (parse YAML, hash canonical dict, ignore body whitespace); `--strict` flag for paranoid mode (full file SHA-256); BDD scenario GIVEN whitespace-only diff THEN no drift (REQ-49 negative test). |
| 5 | BDD step def file growth precedent: decision-code-linking S3 forecast 30 LOC → actual 621 LOC (5-6× multiplier) | MED | MED | MITIGATED — Forecast absorbs the multiplier (`test_prompt_registry_steps.py` ~400 LOC; realistic ~2 400); per-REQ step files if size exceeds 400 LOC. |
| 6 | Adding `prompts/` at repo root conflicts with future external tooling that expects `src/flow_engineering/prompts/` | LOW | LOW | MITIGATED — Document the path in `openspec/specs/prompt-registry/spec.md`; make it configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (default `<repo>/prompts/`). |
| 7 | The Jinja2 autoescape decision (D3) blocks legitimate `{{ var }}` substitution that contains `<` or `&` | LOW | LOW | MITIGATED — `select_autoescape(default_for_string=True)` auto-escapes string variables; BDD scenario REQ-46 S2 covers the case explicitly. The `test_command` variable is the canonical autoescape probe. |

## Cross-Impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | 4 inline prompts (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) migrated into `PROMPT_REGISTRY`; `prompt_fn=Callable` seam at `engram_io.py:541` preserved | Compatible (consumes the migration; seam preserved per D10) |
| `decision-reality-drift` (shipped v0.3.0) | Drift path unaffected — no prompts in drift surface | Compatible (no intersection) |
| `vector-semantic-search` (shipped v0.4.0) | `VECTOR_COUNTER_NAMES` catalog at `observability.py:90` is the structural template for `PROMPT_REGISTRY`; no shared mutable state | Compatible (no intersection) |
| `cross-project-federation` (shipped v0.5.0) | `FEDERATED_COUNTER_NAMES` catalog at `observability.py:109` is the second template; "federated prompt registry" deferred per explore C.4 | Compatible (no intersection) |
| `graph-snapshots` (change #5, ARCHIVED at HEAD `e0f863b`) | `SNAPSHOT_COUNTER_NAMES` catalog at `observability.py:129` is the third template; 6-SKILL.md hand-edit pattern (`CHANGELOG.md:13`) formalized by REQ-49 | Compatible (REQ-49 supersedes the hand-edit pattern with a catalog) |
| `observability` (change #6, IN PROGRESS) | `PROMPT_REGISTRY` mirrors the observability catalog pattern; REQ-52 prompt counters (deferred) will land in `observability.py` per D12 | MUST ARCHIVE BEFORE change #7 apply; coordinate via orchestrator |
| `prompt-registry` (#7, this change) | Standalone; no outbound deps | Self |

**Unblocks** (consolidated):
- Discoverable prompt surface for the 4 inline + 4 Jinja2 + 10 OpenCode
  runtime prompts already shipped (REQ-45 + REQ-49).
- Linted prompt registry catching typos at CI time (REQ-47).
- CLI surface for prompt inspection (REQ-50).
- Manifest-driven SKILL.md drift detection replacing the 6-file hand-edit
  pattern from `graph-snapshots` (REQ-49).
- A deterministic, versioned, regression-tested prompt surface that future
  LLM-backed REQs can plug into.

**Constrains**:
- Any future change that adds a prompt MUST either add it to `PROMPT_REGISTRY`
  or update the `schema_version` constant.
- The 4 existing inline constants are thin wrappers for v0.7.0 only and
  MUST be removed in v0.8.0 (per D10 alias convention).
- The flat text default of `flow metrics` is unaffected.

## Chained PR Strategy

**TWO CHAINED PRs** (per proposal #201 + spec #204):

| PR | Scope | Forecast prod LOC | Forecast test LOC | Realistic ×6 TDD | Acceptance |
|---|---|---|---|---|---|
| **PR#1 — Foundation** | REQ-45 + REQ-46 + REQ-47 + 4 new `.j2` files + 4 inline constants migrated to wrappers + `scaffold._env()` refactor | ~600 | ~1 600 | ~3 600 | All 783 existing tests pass + 7 new BDD scenarios + 26 new unit tests; `ruff check` clean; `STRICT_TDD_PROMPT` thin-wrapper equivalence green |
| **PR#2 — Discovery + integration** | REQ-49 + REQ-50 + `openspec/specs/prompt-registry/spec.md` bootstrap + `flow prompts` CLI group + 6 SKILL.md hook updates + `~/.flow-engineering/prompt_checksums.json` sidecar | ~650 | ~1 700 | ~3 900 | All PR#1 tests + 783 existing tests pass + 5 new BDD scenarios + 12 new unit tests; `ruff check` clean; SHA-256 round-trip green; secrets-invariant BDD green |

**Chain strategy**: stacked-to-main (consistent with prior 6 changes).
**400-line review budget risk**: HIGH per-PR — both PRs exceed budget.

**Mitigation**: per-commit work-unit splits per `work-unit-commits` skill
convention. PR#1 commits (target ≤400 LOC each):

1. `feat(prompt_registry): PROMPT_REGISTRY + PromptEntry dataclass + 4 entries` (~120 prod + 100 test = 220 LOC) — REQ-45 foundation
2. `feat(prompt_render): hoisted _env() from scaffold.py + render_prompt() + PromptRenderError` (~150 prod + 200 test = 350 LOC) — REQ-46
3. `feat(prompt_lint): lint_prompts() + LintWarning + 5 categories` (~80 prod + 150 test = 230 LOC) — REQ-47
4. `feat(strict_tdd + auto_suggest): migrate 4 inline constants to thin wrappers around render_prompt()` (~30 prod + 100 test = 130 LOC) — REQ-45 migration
5. `feat(scaffold): refactor _env() to be shared via prompt_render.py; deprecated local copy` (~10 prod + 50 test = 60 LOC) — D1 refactor
6. `feat(prompts): 4 new .j2 files (strict_tdd, auto_suggest_header, auto_suggest_footer, auto_suggest_empty)` (~10 prod + 50 test = 60 LOC) — REQ-45 template migration
7. `feat(prompt_registry): 3 BDD feature files (REQ-45, REQ-46, REQ-47) + test_prompt_registry_steps.py` (~0 prod + 200 test = 200 LOC) — BDD layer

PR#2 commits (target ≤400 LOC each):

1. `feat(opencode_skill_catalog): SKILL_CATALOG + 20 entries + SkillEntry + SkillDrift + frontmatter parser` (~120 prod + 100 test = 220 LOC) — REQ-49 foundation
2. `feat(opencode_skill_catalog): check_drift + update_checksums + init_checksums + SkillVersionError` (~80 prod + 150 test = 230 LOC) — REQ-49 functions
3. `feat(cli): flow prompts Click group + 4 subcommands (list, show, lint, check) + 7 flags` (~150 prod + 200 test = 350 LOC) — REQ-50 CLI
4. `feat(opencode_skill_catalog): 1 BDD feature (REQ-49) + test_prompt_registry_steps.py extension` (~0 prod + 100 test = 100 LOC) — REQ-49 BDD
5. `feat(cli): 1 BDD feature (REQ-50) + test_cli_prompts.py expansion` (~0 prod + 150 test = 150 LOC) — REQ-50 BDD
6. `docs(specs): bootstrap openspec/specs/prompt-registry/spec.md (4 entries + 20 SKILL_CATALOG + CLI surface contract)` (~150 docs + 50 test = 200 LOC) — D12 + archive-report #61 resolution
7. `docs(skills): 6 SKILL.md hook prose updates (sdd-propose, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive)` (~150 docs + 0 test = 150 LOC) — runtime-only REQ-49 hook
8. `docs(changelog): v0.7.0 entry + 4 SKILL.md updates + pyproject.toml version bump` (~35 docs + 0 test = 35 LOC) — final

The per-commit diffs stay focused (≤400 LOC each) so review remains tractable
even though each PR is large cumulatively. This is the chained-PR-as-commits
pattern from the `work-unit-commits` skill.

## Decision ↔ Code Binding

12 architecture decisions bind to concrete anchor points:

- **D1** (module layout: 4 new sibling modules) → `src/flow_engineering/prompt_registry.py:1`, `src/flow_engineering/prompt_render.py:1`, `src/flow_engineering/prompt_lint.py:1`, `src/flow_engineering/opencode_skill_catalog.py:1`
- **D2** (`.j2` files at repo root + Python dataclass metadata) → `prompts/strict_tdd.j2`, `prompts/auto_suggest_header.j2`, `prompts/auto_suggest_footer.j2`, `prompts/auto_suggest_empty.j2`
- **D3** (Jinja2 + `select_autoescape(default_for_string=True)`) → `src/flow_engineering/scaffold.py:20` (current `_env()` factory; refactor target)
- **D4** (flat `dict[str, PromptEntry]` catalog) → `src/flow_engineering/prompt_registry.py` (NEW)
- **D5** (JSON sidecar at `~/.flow-engineering/prompt_checksums.json`) → `src/flow_engineering/opencode_skill_catalog.py:SIDECAR_PATH`
- **D6** (glob discovery + 20 hard-coded catalog entries) → `src/flow_engineering/opencode_skill_catalog.py:SKILL_CATALOG`
- **D7** (5 lint warning categories) → `src/flow_engineering/prompt_lint.py:lint_prompts`
- **D8** (on-invocation drift detection with cached sidecar) → `src/flow_engineering/opencode_skill_catalog.py:check_drift`
- **D9** (exit codes 0/1/2/3/5) → `src/flow_engineering/cli.py` (NEW `flow prompts` group)
- **D10** (thin wrapper alias for v0.7.0) → `src/flow_engineering/strict_tdd.py:13` (migrated `STRICT_TDD_PROMPT`), `src/flow_engineering/auto_suggest_code_refs.py:47-49` (migrated 3 constants)
- **D11** (shared `prompts/` directory + sidecar JSON + BDD glue file across PRs) → `tests/bdd/test_prompt_registry_steps.py` (NEW; shared across PR#1 + PR#2)
- **D12** (`openspec/specs/prompt-registry/spec.md` bootstrap in PR#2) → `openspec/specs/prompt-registry/spec.md` (NEW; second capability spec after `observability`)

---

## Structured Metadata

- **decisions_count**: 12 (D1..D12)
- **open_questions_resolved**: 10/10 (all from propose #201)
- **open_questions_remaining**: 0
- **file_count**: 8 new + 7 modified + 11 new test = 26 total (8 prod new + 11 test new + 7 prod modified; 4 `.j2` files counted in prod new)
- **loc_forecast**: ~833 production + ~2 260 test = ~3 243 total
- **loc_realistic_x6**: ~18 710 (per `decision-code-linking` S3 precedent)
- **pr_count**: 2 (PR#1 foundation: registry+render+lint; PR#2 discovery: CLI+SKILL.md mirror)
- **bdd_feature_files_new**: 5
- **bdd_scenarios_new**: 12
- **inline_prompt_constants_today**: 4 (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`)
- **jinja2_templates_today**: 4 (`change.yaml.j2`, `exploration.md.j2`, `README.md.j2`, `flow-version.j2`)
- **opencode_skill_files_today**: 10 (`~/.config/opencode/skills/sdd-*/SKILL.md`)
- **opencode_prompt_files_today**: 10 (`~/.config/opencode/prompts/sdd/*.md`)
- **new_modules_after_change_7**: 4 (`prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`, `opencode_skill_catalog.py`)
- **sidecar_files_new**: 1 (`~/.flow-engineering/prompt_checksums.json`)
- **next_recommended**: `sdd-tasks prompt-registry`

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
      "label": "opencode_skill_catalog.py (NEW — SKILL_CATALOG, SkillEntry dataclass, SkillDrift dataclass, check_drift(), update_checksums(), init_checksums(), SkillVersionError, frontmatter parser; ~120 prod LOC)",
      "file": "src/flow_engineering/opencode_skill_catalog.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_scaffold_env_refactor",
      "label": "scaffold.py _env() Jinja2 Environment (refactor target: hoisted to prompt_render.py; preserved as thin re-export; line 20)",
      "file": "src/flow_engineering/scaffold.py",
      "line": 20,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_strict_tdd_prompt_migration",
      "label": "STRICT_TDD_PROMPT (strict_tdd.py:13) — MIGRATION TARGET: replaced with render_prompt('strict_tdd', test_command=cmd); thin wrapper for v0.7.0 per D10 alias",
      "file": "src/flow_engineering/strict_tdd.py",
      "line": 13,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_auto_suggest_prompts_migration",
      "label": "EMPTY_PROMPT_TEXT + PROMPT_HEADER + PROMPT_FOOTER (auto_suggest_code_refs.py:47-49) — MIGRATION TARGETS: 3 inline prompts replaced with render_prompt() calls",
      "file": "src/flow_engineering/auto_suggest_code_refs.py",
      "line": 47,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_prompt_fn_seam",
      "label": "prompt_fn Callable injection point in save_phase (testable seam for REQ-6 auto-suggest; preserved as-is per D10)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 541,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_prompts_group",
      "label": "flow prompts subcommand group (NEW — 4 subcommands: list, show, lint, check; ~150 prod LOC delta)",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_strict_tdd_j2",
      "label": "prompts/strict_tdd.j2 (NEW — Jinja2 version of STRICT_TDD_PROMPT; ~4 LOC)",
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
      "id": "openspec_specs_prompt_registry_spec_bootstrap",
      "label": "openspec/specs/prompt-registry/spec.md (NEW — capability spec cataloging 4 PROMPT_REGISTRY entries + 20 SKILL_CATALOG entries + CLI surface contract; bootstraps openspec/specs/prompt-registry/ baseline; ~150 LOC; per D12)",
      "file": "openspec/specs/prompt-registry/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_prompt_counter_extension",
      "label": "observability.py catalog extension (FUTURE REQ-52 — add 3 prompt counters to existing VECTOR_COUNTER_NAMES / FEDERATED_COUNTER_NAMES / SNAPSHOT_COUNTER_NAMES catalog per D12)",
      "file": "src/flow_engineering/observability.py",
      "line": 129,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}
