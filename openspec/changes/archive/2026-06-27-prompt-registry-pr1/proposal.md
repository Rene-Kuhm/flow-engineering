<!-- proposal.md: change #7 prompt-registry. Source: manual. -->
# Proposal: prompt-registry

```yaml
status: success
confidence: high
open_questions_count: 10
chained_pr_recommendation: yes
wall_time_estimate: ~4-5h end-to-end (2 chained PRs)
forecast_loc: 833 production + 2260 tests = 3243 grand-total
pr_split: 2 chained PRs (PR#1 foundation: registry+render+lint; PR#2 discovery: CLI+SKILL.md mirror)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\prompt-registry\proposal.md
next_recommended: sdd-spec prompt-registry
```

## Intent

`flow-engineering` has been quietly accumulating **prompt-shaped
artifacts across three disconnected surfaces** without a unifying
catalog. Today the codebase ships **4 inline prompt constants**
(`STRICT_TDD_PROMPT` at `src/flow_engineering/strict_tdd.py:13` plus
`EMPTY_PROMPT_TEXT` / `PROMPT_HEADER` / `PROMPT_FOOTER` at
`src/flow_engineering/auto_suggest_code_refs.py:47-49`), **4 Jinja2
scaffolding templates** at `src/flow_engineering/templates/` (loaded
via a private `_env()` in `scaffold.py:20` that is NOT exposed to any
other module), and **10 OpenCode runtime SKILL.md agent prompts** at
`~/.config/opencode/skills/sdd-*/SKILL.md` that drive the entire SDD
cycle (used by `flow apply` / `flow verify` / `flow archive` via
delegation) yet live **outside the repo** with no version pin, no
checksum, and no drift detection. Four of nine user-facing CLI
subcommands (`apply`, `verify`, `archive`, and the SKILL.md-running
variant of `new`) delegate to sdd-* sub-agents whose prompts the repo
cannot see. This change ships the **catalog + render + lint + CLI**
surface that turns those three prompt worlds into a single,
discoverable, versioned, golden-testable registry — analogous to the
`VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` catalog pattern that
change #6 ships for observability counters. As a one-time side
benefit, change #7 formalizes the **mirror catalog** for the OpenCode
SKILL.md runtime surface so that drift between `flow` and the agent
prompts that drive the SDD cycle becomes detectable in CI rather than
discoverable in a confused `flow apply` run three weeks later.

## Context (from explore)

Explored in [`explore.md`](./explore.md) and Engram #198. Ten
user-facing gaps evaluated; **5 P0/P1** gaps recommended for change
#7, 5 P2 gaps deferred to v1.1. The exploration confirmed: the
inline + Jinja2 prompt surface is **small today** (4 inline + 4
templates) and trivially discoverable via `grep -r PROMPT src/`, but
will **not scale** — change #1 already added the
`prompt_fn=Callable` injection point (`engram_io.py:541`) which is a
testability seam without a registry to back it; a future LLM-backed
change (e.g., `flow drift --llm-summary`) would have to invent its own
catalog unless change #7 lands first. The exploration also confirmed:
the **only** missing pieces are (a) a `PROMPT_REGISTRY` constant in a
dedicated module, (b) a shared `render_prompt()` Jinja2 helper that
hoists `_env()` out of `scaffold.py`'s private scope, (c) a
`lint_registry()` validator, (d) a `SKILL_CATALOG` for the runtime
SKILL.md surface with checksum drift detection, and (e) a `flow prompts`
CLI subcommand — all additive, all non-breaking, all mirroring the
proven observability catalog pattern. The strict-TDD ×6 LOC multiplier
(established in `decision-code-linking` archive-report #119 S3 and
re-affirmed in `cross-project-federation` archive-report) forecasts
the work at ~3 243 LOC forecast → ~18 710 realistic, comfortably
justifying a **2 chained PRs** split (mirrors `cross-project-federation`
chained-PR pattern).

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `graph-snapshots` archive-report CHANGELOG.md:13 | "6 SKILL.md runtime files updated with the snapshot hook" | Resolved — REQ-49 `SKILL_CATALOG` formalizes the catalog so future `flow` changes can replace the 6-file hand-edit pattern with a manifest-driven approach |
| `observability` explore #195 line 263 | "Alerting via daemon (`flow watch`) is a different change (#7 prompt-registry territory)" | Clarified — alerting is an ENGINEERING decision, NOT a prompt-registry decision. Scope this OUT of change #7 |
| `cross-project-federation` archive-report #61 | "broader 'federated prompt registry' question deferred" | Resolved — change #7 ships the local `PROMPT_REGISTRY` first; federated extension deferred to a "federated-prompts" follow-up if the need arises |
| `decision-code-linking` archive-report #119 S3 | BDD step def file 5-6× growth precedent | Forecast absorbs the multiplier (`tests/bdd/test_prompt_registry_steps.py` ~400 LOC) |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — `PromptRegistry` class + JSON-backed catalog** (mirrors observability counter catalog pattern) | ~3 243 | Lowest risk (mirrors proven observability pattern); best discoverability (single `PROMPT_REGISTRY` constant); addresses ALL 3 prompt surfaces (inline, Jinja2, OpenCode runtime); non-breaking (existing call sites migrated via thin `render_prompt()` wrapper); enables golden regression tests via `PROMPT_REGISTRY` as source of truth | New module `prompt_registry.py` + sidecar JSON; ~120 prod LOC just for the registry | **RECOMMENDED** |
| B — YAML-based prompt files + Jinja2 everywhere | ~4 500 | Industry-standard (Rails i18n style); prompts editable without Python; better diff ergonomics | Bigger migration (5 modules touched); YAML parser needed; doesn't naturally cover the OpenCode runtime SKILL.md surface (which is Markdown, not YAML) | Rejected — overkill for 4 prompts today |
| C — Extend OpenCode runtime registry only (`flow prompts sync`) | ~800 | Smallest change; reuses existing user-managed SKILL.md files | Doesn't address inline prompt sprawl or Jinja2 duplication; couples repo to user-side runtime edits; no version pin from the repo side | Rejected — ignores 2 of 3 surfaces |

**Recommendation: Approach A.** Lowest risk (mirrors proven
observability catalog pattern that change #6 ships), best
discoverability (a single `PROMPT_REGISTRY` constant + a `flow prompts`
subcommand), preserves the project's offline-first principle (no new
runtime dependencies; Jinja2 is already a dependency), and unifies all
3 prompt surfaces — inline + Jinja2 + OpenCode runtime — into a
single mental model. Approach B is overkill for 4 prompts today and
pulls in a YAML parser; Approach C ignores 2 of 3 surfaces.

### Architecture (Approach A)

Four cooperating modules, all additive on top of the existing
`_env()` Jinja2 factory in `scaffold.py` that change #1 shipped:

1. **`PromptRegistry` catalog** (NEW `src/flow_engineering/prompt_registry.py`)
   — `PROMPT_REGISTRY: dict[str, PromptEntry]` mapping
   `prompt_id → {template_id, version, owner, location, variables,
   schema_version}`. `PromptEntry` is a `frozen=True` dataclass.
   Mirrors `VECTOR_COUNTER_NAMES` / `SNAPSHOT_COUNTER_NAMES` catalog
   pattern at `observability.py:85, 124`. Migrates the 4 existing
   inline prompts (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`,
   `PROMPT_HEADER`, `PROMPT_FOOTER`) into the registry.
2. **`render_prompt()` helper** (NEW `src/flow_engineering/prompt_render.py`)
   — `render_prompt(prompt_id, **variables) -> str`. Backed by a
   shared Jinja2 `Environment` (hoisted out of `scaffold.py:_env()`).
   Adds a `prompts/` directory at repo root for `.j2` files (mirrors
   the `templates/` convention but hoisted per D.1). Adds 4 `.j2`
   files (`strict_tdd.j2`, `auto_suggest_header.j2`,
   `auto_suggest_footer.j2`, `auto_suggest_empty.j2`). Existing
   inline constants become thin wrappers around `render_prompt()`
   for one release (v0.7.0) per D.8.
3. **`lint_registry()` validator** (NEW `src/flow_engineering/prompt_lint.py`)
   — `lint_registry(registry) -> list[LintWarning]`. Validates:
   (a) all `{{ var }}` placeholders match declared `variables`,
   (b) all declared `variables` are used by at least one placeholder,
   (c) Jinja2 templates parse cleanly, (d) autoescape is enabled.
   Bundled as `flow prompts lint` CLI subcommand and as a `pytest`
   fixture (`prompt_lint_clean`). Powers REQ-47.
4. **`SKILL_CATALOG` mirror** (NEW `src/flow_engineering/opencode_skill_catalog.py`)
   — `SKILL_CATALOG: dict[str, SkillEntry]` mapping
   `skill_name → {expected_version, expected_path,
   last_verified_checksum, owner}`. `flow prompts check` walks the
   catalog, computes SHA-256 of each on-disk SKILL.md frontmatter
   (per D.5, frontmatter-only to avoid whitespace false positives),
   compares against `last_verified_checksum`, and exits non-zero on
   drift. Sidecar JSON at `~/.flow-engineering/prompt_checksums.json`
   per D.5. Powers REQ-49.

### CLI surface (proposed)

```bash
# New in change #7:
flow prompts list
  [--json]                      # REQ-50 — flat dict mirror of `flow metrics --json`

flow prompts show <prompt_id>
  [--var key=value] ...         # REQ-50 — repeatable; renders with sentinel for missing vars per D.4

flow prompts lint
  [--strict]                    # REQ-47 — warnings as errors

flow prompts check
  [--update]                    # REQ-49 — manual catalog update on drift detection per D.9
  [--no-fail]                   # REQ-49 — exit 0 even on drift (CI compat)
  [--init]                      # REQ-49 — bootstrap the sidecar JSON
  [--skill <name>]              # REQ-49 — limit to one skill (debugging)
```

### Proposed output examples

**`flow prompts list`** (REQ-50):

```
flow-engineering prompt registry
─────────────────────────────────────────────────────────────────
prompt_id                  version  owner                location
─────────────────────────────────────────────────────────────────
strict_tdd                 1.0.0    flow/observability   prompts/strict_tdd.j2
auto_suggest_header        1.0.0    flow/binding         prompts/auto_suggest_header.j2
auto_suggest_footer        1.0.0    flow/binding         prompts/auto_suggest_footer.j2
auto_suggest_empty         1.0.0    flow/binding         prompts/auto_suggest_empty.j2
scaffold_change_yaml       1.0.0    flow/scaffold        src/flow_engineering/templates/new-change/change.yaml.j2
scaffold_exploration_md    1.0.0    flow/scaffold        src/flow_engineering/templates/new-change/explore/exploration.md.j2
scaffold_readme            1.0.0    flow/scaffold        src/flow_engineering/templates/new-project/README.md.j2
scaffold_flow_version      1.0.0    flow/scaffold        src/flow_engineering/templates/new-project/flow-version.j2
─────────────────────────────────────────────────────────────────
8 prompt entries · 0 lint warnings · registry schema_version=1.0
```

**`flow prompts show strict_tdd --var test_command=pytest`** (REQ-50):

```
prompt_id:   strict_tdd
version:     1.0.0
owner:       flow/observability
variables:   {test_command: pytest}
─────────────────────────────────────────────────────────────────
STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow
strict-tdd.md. Do NOT fall back to Standard Mode.
─────────────────────────────────────────────────────────────────
(rendered via Jinja2 · autoescape=on · source: prompts/strict_tdd.j2)
```

**`flow prompts check`** (REQ-49):

```
flow-engineering opencode skill drift check
─────────────────────────────────────────────────────────────────
skill             expected_version  on_disk_version  status
─────────────────────────────────────────────────────────────────
sdd-init          3.0               3.0              OK
sdd-explore       2.0               2.0              OK
sdd-propose       3.0               3.0              OK
sdd-design        3.0               2.0              DRIFT (expected 3.0, found 2.0)
sdd-spec          3.0               3.0              OK
sdd-tasks         3.0               3.0              OK
sdd-apply         3.0               3.0              OK
sdd-verify        3.0               3.0              OK
sdd-archive       3.0               3.0              OK
sdd-onboard       3.0               3.0              OK
─────────────────────────────────────────────────────────────────
9 skills verified · 1 drift detected (sdd-design)
Run `flow prompts check --update` to refresh the sidecar checksum.
Exit code: 1
```

**`flow prompts lint`** (REQ-47):

```
flow-engineering prompt registry lint
─────────────────────────────────────────────────────────────────
strict_tdd.j2                        OK
auto_suggest_header.j2               OK
auto_suggest_footer.j2               OK
auto_suggest_empty.j2                OK
─────────────────────────────────────────────────────────────────
8 prompts linted · 0 warnings · 0 errors
```

### Dependencies

- **NO new runtime dependencies.** Jinja2 is already a project
  dependency (`pyproject.toml:18`, used by `scaffold.py`); reusing the
  existing `_env()` factory removes the only "but Jinja2 is heavy"
  objection. stdlib `hashlib` (SHA-256) + `pathlib` + `dataclasses` +
  `typing` cover the registry.
- Reuses `_env() -> Environment` from `scaffold.py:20` (REFACTOR
  target: move the factory into `prompt_render.py`; keep the
  scaffold.py import as a thin re-export for backwards compatibility).
- Reuses the `PROMPT_REGISTRY` constant pattern from
  `VECTOR_COUNTER_NAMES` (observability.py:85), `FEDERATED_COUNTER_NAMES`
  (observability.py:104), `SNAPSHOT_COUNTER_NAMES` (observability.py:124).
- Sidecar state at `~/.flow-engineering/prompt_checksums.json` (NEW)
  parallels `~/.flow-engineering/metrics.jsonl` (REQ-8 close).

### What changes (scope)

**In scope (PR#1 — foundation)**:
- `src/flow_engineering/prompt_registry.py` (NEW): `PROMPT_REGISTRY`,
  `PromptEntry` dataclass, 4 migrated entries.
- `src/flow_engineering/prompt_render.py` (NEW): Jinja2 `Environment`
  shared with scaffold.py, `render_prompt()` API, filter pipeline.
- `src/flow_engineering/prompt_lint.py` (NEW): `lint_registry()`,
  `LintWarning` dataclass, 5 warning categories.
- `prompts/strict_tdd.j2` (NEW), `prompts/auto_suggest_header.j2`
  (NEW), `prompts/auto_suggest_footer.j2` (NEW),
  `prompts/auto_suggest_empty.j2` (NEW).
- `src/flow_engineering/strict_tdd.py` (MODIFY): replace
  `STRICT_TDD_PROMPT` constant with `render_prompt("strict_tdd",
  test_command=cmd)` call; remove inline string (1-line wrapper for
  v0.7.0 per D.8 alias).
- `src/flow_engineering/auto_suggest_code_refs.py` (MODIFY): replace 3
  inline constants with `render_prompt("auto_suggest_header", ...)`,
  etc.; `format_suggestion_prompt()` delegates to registry.
- `src/flow_engineering/scaffold.py` (MODIFY): refactor `_env()` to be
  shared via `prompt_render.py`; deprecate the local copy.
- `tests/unit/test_prompt_registry.py` (NEW): PROMPT_REGISTRY schema
  + 4 migrated entries; rendering tests (~250 LOC).
- `tests/unit/test_prompt_render.py` (NEW): render_prompt() with
  variables, missing variable, template error (~300 LOC).
- `tests/unit/test_prompt_lint.py` (NEW): lint_registry() with 5
  warning categories (~250 LOC).
- `tests/bdd/req45_prompt_registry.feature` (NEW),
  `tests/bdd/req46_prompt_render.feature` (NEW),
  `tests/bdd/req47_prompt_lint.feature` (NEW).

**In scope (PR#2 — discovery + integration)**:
- `src/flow_engineering/opencode_skill_catalog.py` (NEW):
  `SKILL_CATALOG`, `SkillEntry` dataclass, checksum verification,
  frontmatter parsing.
- `src/flow_engineering/cli.py` (MODIFY): `flow prompts` group + 4
  subcommands (`list`, `show <id>`, `lint`, `check`) (~150 prod LOC
  delta).
- `openspec/specs/prompt-registry/spec.md` (NEW): capability spec
  cataloging all 8+10 registry entries + SKILL.md mirror contract
  (~150 LOC).
- `tests/unit/test_opencode_skill_catalog.py` (NEW): SKILL_CATALOG +
  checksum + drift detection (mock SKILL.md files) (~300 LOC).
- `tests/unit/test_cli_prompts.py` (NEW): full CLI surface coverage
  for `flow prompts list/show/lint/check` (~400 LOC).
- `tests/bdd/req49_skill_catalog.feature` (NEW),
  `tests/bdd/req50_cli_prompts.feature` (NEW).
- `tests/bdd/test_prompt_registry_steps.py` (NEW): pytest-bdd glue
  shared across the 5 BDD features (~400 LOC).
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md`
  (MODIFY): prompt registry hook prose (~150 LOC, runtime-only).
- `CHANGELOG.md` (MODIFY): v0.7.0 entry post-PR#2-merge.

**Out of scope (deferred to v1.1 or named follow-up changes)**:
- **REQ-48** — golden regression tests via `pytest` snapshots at
  `tests/golden/prompts/<prompt_id>.txt` (defer to v1.1; bundle if
  PR#1 scope allows)
- **REQ-51** — `prompt_renders.jsonl` append-only sink at
  `~/.flow-engineering/prompt_renders.jsonl` (defer to v1.1)
- **REQ-52** — `prompts_render_total{...}` /
  `prompts_render_ms` / `prompts_render_failed_total{...}` counters
  wired into `render_prompt()` (defer to v1.1, bundles with REQ-51)
- **REQ-53** — `docs/prompts.md` generated from `PROMPT_REGISTRY` at
  build time (defer to v1.1)
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` in
  `pyproject.toml`; `flow apply` / `verify` / `archive` assert version
  >= minimum at startup (defer to v1.1 or bundle into PR#2)
- **LLM client integration** (any `openai` / `anthropic` /
  `litellm` dependency) — NEVER (out of project scope per explore C.5)
- **i18n / multi-language prompts** — defer to v1.1+ (no current need)
- **Prompt A/B testing infrastructure** — defer to v1.1+ (only 8
  prompts today)
- **External prompt marketplace / community registry** — NEVER
  (single-user tool)
- **Federated prompt registry** (per-project prompt catalogs) — defer
  until cross-project-federation extension surfaces a concrete need

### Public API surface (NEW)

```python
# prompt_registry.py — NEW
@dataclass(frozen=True)
class PromptEntry:
    template_id: str             # relative path to .j2 file (without extension)
    version: str                 # semver of the entry
    owner: str                   # e.g., "flow/observability"
    location: str                # absolute path resolved at import time
    variables: tuple[str, ...]   # declared variable names
    schema_version: str          # PromptEntry schema version (e.g., "1.0")

PROMPT_REGISTRY: dict[str, PromptEntry] = {
    "strict_tdd": PromptEntry(
        template_id="strict_tdd",
        version="1.0.0",
        owner="flow/observability",
        location="<repo>/prompts/strict_tdd.j2",
        variables=("test_command",),
        schema_version="1.0",
    ),
    "auto_suggest_header": PromptEntry(
        template_id="auto_suggest_header",
        version="1.0.0",
        owner="flow/binding",
        location="<repo>/prompts/auto_suggest_header.j2",
        variables=(),
        schema_version="1.0",
    ),
    "auto_suggest_footer": PromptEntry(
        template_id="auto_suggest_footer",
        version="1.0.0",
        owner="flow/binding",
        location="<repo>/prompts/auto_suggest_footer.j2",
        variables=(),
        schema_version="1.0",
    ),
    "auto_suggest_empty": PromptEntry(
        template_id="auto_suggest_empty",
        version="1.0.0",
        owner="flow/binding",
        location="<repo>/prompts/auto_suggest_empty.j2",
        variables=(),
        schema_version="1.0",
    ),
}

# prompt_render.py — NEW
def render_prompt(prompt_id: str, **variables: Any) -> str:
    """Render a prompt from PROMPT_REGISTRY with the given variables.
    Raises PromptRenderError on missing variable or template parse error.
    """
    ...

def render_prompt_safe(prompt_id: str, **variables: Any) -> str:
    """Render with sentinel substitution for missing variables (CLI show mode).
    """
    ...

class PromptRenderError(Exception):
    """Raised when render_prompt fails (missing var, template parse, etc.).
    """
    ...

# prompt_lint.py — NEW
@dataclass(frozen=True)
class LintWarning:
    prompt_id: str
    category: str                # "missing_placeholder" | "unused_variable" | "template_parse_error" | "autoescape_disabled" | "missing_variable"
    message: str
    line: int | None = None

def lint_registry(registry: dict[str, PromptEntry]) -> list[LintWarning]:
    """Validate the registry: placeholders match variables, templates parse, autoescape on.
    """
    ...

# opencode_skill_catalog.py — NEW
@dataclass(frozen=True)
class SkillEntry:
    skill_name: str              # e.g., "sdd-apply"
    expected_version: str        # semver minimum from pyproject.toml
    expected_path: str           # absolute path to SKILL.md
    last_verified_checksum: str  # SHA-256 of frontmatter YAML dict
    owner: str                   # e.g., "gentleman-programming"

SKILL_CATALOG: dict[str, SkillEntry] = {
    "sdd-init": SkillEntry(
        skill_name="sdd-init",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-init/SKILL.md",
        last_verified_checksum="<sha256>",
        owner="gentleman-programming",
    ),
    # ... 9 more entries
}

def check_drift(catalog: dict[str, SkillEntry] | None = None) -> list[SkillDrift]:
    """Walk the catalog; SHA-256 each on-disk frontmatter; compare against last_verified.
    Returns list of SkillDrift (empty if all match).
    """
    ...

class SkillVersionError(Exception):
    """Raised by flow apply / verify / archive when on-disk SKILL.md version < expected.
    """
    ...
```

### Non-breaking guarantees

- `STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`,
  `PROMPT_FOOTER` are re-exported from `strict_tdd.py` /
  `auto_suggest_code_refs.py` as thin wrappers around `render_prompt()`
  for v0.7.0 (per D.8 alias convention). Removed in v0.8.0. External
  imports keep working.
- `scaffold.py:_env()` is preserved as a thin re-export from
  `prompt_render._env()`. No existing scaffold call site breaks.
- `prompt_fn=Callable` injection point at `engram_io.py:541` is
  unchanged — registry is additive; the callable seam still works.
- `flow` CLI without any new subcommand is byte-identical to v0.6.0
  behavior. The new `flow prompts` group is opt-in.
- All existing 783 tests pass — verified locally before PR#1 open.
- The user's `~/.flow-engineering/metrics.jsonl` is NOT touched.
  The new sidecar `~/.flow-engineering/prompt_checksums.json` is
  created lazily on first `flow prompts check --init` run.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/prompt_registry.py` | **NEW** | `PROMPT_REGISTRY`, `PromptEntry` dataclass, 4 migrated entries (~120 prod LOC) |
| `src/flow_engineering/prompt_render.py` | **NEW** | Jinja2 `Environment` (shared with scaffold.py), `render_prompt()`, `render_prompt_safe()`, filter pipeline (~150 prod LOC) |
| `src/flow_engineering/prompt_lint.py` | **NEW** | `lint_registry()`, `LintWarning` dataclass, 5 warning categories (~80 prod LOC) |
| `src/flow_engineering/opencode_skill_catalog.py` | **NEW** | `SKILL_CATALOG`, `SkillEntry` dataclass, checksum verification, frontmatter parsing (~120 prod LOC) |
| `src/flow_engineering/strict_tdd.py` | MODIFY | Replace `STRICT_TDD_PROMPT` constant with `render_prompt("strict_tdd", test_command=cmd)` call; remove inline string (1-line wrapper for v0.7.0 per D.8) |
| `src/flow_engineering/auto_suggest_code_refs.py` | MODIFY | Replace 3 inline constants with `render_prompt("auto_suggest_header", ...)`, etc.; `format_suggestion_prompt()` delegates to registry |
| `src/flow_engineering/scaffold.py` | MODIFY | Refactor `_env()` to be shared via `prompt_render.py`; deprecate the local copy (thin re-export) |
| `src/flow_engineering/cli.py` | MODIFY | `flow prompts` group + 4 subcommands (`list`, `show <id>`, `lint`, `check`) (~150 prod LOC delta) |
| `prompts/strict_tdd.j2` | **NEW** | Jinja2 version of STRICT_TDD_PROMPT (1 file, ~4 LOC) |
| `prompts/auto_suggest_header.j2` | **NEW** | Jinja2 version of PROMPT_HEADER (1 file, ~2 LOC) |
| `prompts/auto_suggest_footer.j2` | **NEW** | Jinja2 version of PROMPT_FOOTER (1 file, ~3 LOC) |
| `prompts/auto_suggest_empty.j2` | **NEW** | Jinja2 version of EMPTY_PROMPT_TEXT (1 file, ~1 LOC) |
| `openspec/specs/prompt-registry/spec.md` | **NEW** | Capability spec cataloging all 8+10 registry entries + SKILL.md mirror contract (~150 LOC) |
| `tests/unit/test_prompt_registry.py` | NEW | PROMPT_REGISTRY schema + 4 migrated entries; rendering tests (~250 LOC) |
| `tests/unit/test_prompt_render.py` | NEW | render_prompt() with variables, missing variable, template error (~300 LOC) |
| `tests/unit/test_prompt_lint.py` | NEW | lint_registry() with 5 warning categories (~250 LOC) |
| `tests/unit/test_opencode_skill_catalog.py` | NEW | SKILL_CATALOG + checksum + drift detection (mock SKILL.md files) (~300 LOC) |
| `tests/unit/test_cli_prompts.py` | NEW | Full CLI surface coverage for `flow prompts list/show/lint/check` (~400 LOC) |
| `tests/bdd/req45_prompt_registry.feature` | NEW | 2 scenarios: registry has 4 entries, entries have required schema fields |
| `tests/bdd/req46_prompt_render.feature` | NEW | 3 scenarios: render with vars, render missing var fails, autoescape blocks HTML injection |
| `tests/bdd/req47_prompt_lint.feature` | NEW | 2 scenarios: clean registry lints clean, broken registry lints 3+ warnings |
| `tests/bdd/req49_skill_catalog.feature` | NEW | 2 scenarios: clean SKILL.md match, drift detected |
| `tests/bdd/req50_cli_prompts.feature` | NEW | 3 scenarios: list renders table, show renders prompt, check exits non-zero on drift |
| `tests/bdd/test_prompt_registry_steps.py` | NEW | pytest-bdd glue shared across the 5 BDD features (~400 LOC) |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | Prompt registry hook prose (~150 LOC runtime-only) |
| `CHANGELOG.md` | MODIFY | v0.7.0 entry post-PR#2-merge |
| `pyproject.toml` | MODIFY | Version bump 0.6.0 → 0.7.0; new `[tool.flow_engineering.prompts]` section for registry path + lint settings |

## Capabilities

### New Capabilities
- `prompt-registry`: catalog of all `flow` CLI prompt artifacts (4
  inline + 4 Jinja2 + 10 OpenCode runtime SKILL.md) as a single
  discoverable, versioned, golden-testable surface. Includes
  `PROMPT_REGISTRY` (REQ-45), `render_prompt()` shared Jinja2 helper
  (REQ-46), `lint_registry()` validator (REQ-47), `SKILL_CATALOG` with
  checksum drift detection (REQ-49), and the `flow prompts
  list/show/lint/check` CLI subcommand (REQ-50). All additive; existing
  inline constants remain as thin wrappers for v0.7.0 (per D.8 alias
  convention) and the `prompt_fn=Callable` injection point at
  `engram_io.py:541` is preserved. Includes the
  `openspec/specs/prompt-registry/spec.md` capability spec cataloging
  all registry entries + the SKILL.md mirror contract.

### Modified Capabilities
- None. `decision-code-linking` (REQ-1..8), `decision-reality-drift`
  (REQ-9..16), `vector-semantic-search` (REQ-17..22),
  `cross-project-federation` (REQ-23..27), `graph-snapshots`
  (REQ-28..34), and `observability` (REQ-35..39) all ship unchanged.
  The new `prompt_registry` module is a sibling of `observability.py`
  — same catalog pattern, same dataclass discipline, same CLI surface
  shape — but no shared mutable state, no shared event sink, no shared
  lookup table. The new read-side helpers consume no existing event
  format; no schema bump, no event-type discriminator added, no
  `prompt_id` field injected into existing JSONL events.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | change #6 (observability) does not archive before change #7 apply starts → `PROMPT_REGISTRY` mirrors an unstable catalog pattern | HIGH | Change #7 PROPOSE waits for change #6 ARCHIVE; PR#1 SPEC references the observability pattern by name only and is resilient to additions (catalogs are independent modules) |
| 2 | PR#1 cumulative realistic ~3 600 LOC > 400-line review budget; reviewers lose context | MED | Per-commit work-unit splits per `work-unit-commits` skill; 5-6 commits each ≤400 LOC; mirror `cross-project-federation` chained-PR pattern |
| 3 | Migration of `STRICT_TDD_PROMPT` / `PROMPT_HEADER` / `PROMPT_FOOTER` / `EMPTY_PROMPT_TEXT` breaks existing tests that hardcode the prompt strings | MED | Run all 783 tests after migration; v0.7.0 ships thin wrapper re-exports (per D.8 alias) so external imports keep working; update test fixtures to use `render_prompt()` + golden snapshots; follow REQ-48 in v1.1 |
| 4 | The SKILL.md checksum drift detection (REQ-49) produces false positives on whitespace-only changes | MED | Use frontmatter-only checksum per D.5 (parse YAML, hash the dict, ignore body whitespace); add `--strict` flag for paranoid mode (full file checksum); BDD scenario GIVEN whitespace-only diff THEN no drift |
| 5 | BDD step def file growth precedent: decision-code-linking S3 forecast 30 LOC → actual 621 LOC (5-6× multiplier) | MED | Forecast absorbs the multiplier (`test_prompt_registry_steps.py` ~400 LOC; realistic ~2 400); per-REQ step files if size exceeds 400 LOC |
| 6 | Adding `prompts/` at repo root conflicts with future external tooling that expects `src/flow_engineering/prompts/` | LOW | Document the path in `openspec/specs/prompt-registry/spec.md`; make it configurable via `[tool.flow_engineering.prompts] directory` in `pyproject.toml` (default `<repo>/prompts/`) |
| 7 | The Jinja2 autoescape decision (D.2) blocks legitimate `{{ var }}` substitution that contains characters like `<` or `&` | LOW | Use `select_autoescape(default_for_string=True)` which auto-escapes string variables; BDD scenario REQ-46 S2 covers the case |
| 8 | `flow prompts check` exit code (non-zero on drift) breaks existing CI pipelines that run `flow apply` automatically | LOW | Default is non-zero on drift; add `--no-fail` flag for CI compatibility; document in `--help` and `openspec/specs/prompt-registry/spec.md` |
| 9 | The OpenCode SKILL.md files at `~/.config/opencode/` are user-managed (not in repo); if the user has manually edited them, drift detection fires unexpectedly | LOW | Document the expected state in `openspec/specs/prompt-registry/spec.md`; provide `flow prompts check --init` to bootstrap the sidecar; per D.9 use `--update` flag (manual, not auto) for catalog refresh |
| 10 | The `prompts/` directory at repo root conflicts with the `~/.flow-engineering/prompts/` user config directory (parallel naming) | LOW | Per D.7 + D.9, use `~/.flow-engineering/prompt_checksums.json` (not `prompts/`) for the sidecar; repo-side uses `prompts/` (`.j2` files only); documented in spec |
| 11 | Adding the Jinja2 env shared between `scaffold.py` and `prompt_render.py` creates an import cycle | LOW | Refactor `_env()` to live in `prompt_render.py` (not `scaffold.py`); `scaffold.py` imports it; no cycle. BDD scenario GIVEN `render_prompt("scaffold_change_yaml", name="x")` THEN output equals scaffold.py path |
| 12 | The strict-TDD ×6 LOC multiplier (per `decision-code-linking` S3) means the realistic forecast is ~18 710 LOC vs the 3 243 forecast → 2 chained PRs are MANDATORY | INFO | Already reflected in PR split (PR#1 ~3 600 LOC realistic; PR#2 ~3 900 LOC realistic); per-PR scope is well-defined |

## Rollback Plan

All artifacts are additive. Single revert of each merge commit restores
pre-change state:

- New modules (`prompt_registry.py`, `prompt_render.py`,
  `prompt_lint.py`, `opencode_skill_catalog.py`) are pure additions;
  no existing function modified. Deleting them removes the registry but
  does not break any runtime behavior.
- Existing inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`,
  `PROMPT_HEADER`, `PROMPT_FOOTER`) become thin wrappers around
  `render_prompt()` in v0.7.0 (per D.8 alias). If rollback is needed
  within v0.7.0, revert the wrapper replacement; the inline strings
  return.
- `scaffold.py:_env()` is preserved as a thin re-export from
  `prompt_render._env()`. Reverting restores the local copy.
- The 4 new `.j2` files (`prompts/*.j2`) are NEW; deleting them
  re-enables the inline strings.
- `flow prompts` CLI group is opt-in; without it, no CLI behavior
  changes. The new flags are all additive.
- `openspec/specs/prompt-registry/spec.md` is a NEW file; deleting it
  removes the capability spec but does not break any runtime behavior
  (the catalog is informational).
- 5 BDD feature files are NEW; removing them disables BDD coverage for
  the new REQs but does not break the existing 783 tests.
- The user's `~/.flow-engineering/prompt_checksums.json` is a NEW
  sidecar; deleting it forces `flow prompts check --init` on next run.

To restore the pre-change-#7 install: `git revert <PR#1-merge> <PR#2-merge>`.
The JSONL event format is unchanged; the user's existing metrics data
survives intact.

## Dependencies

- **None new.** Jinja2 is already a project dependency
  (`pyproject.toml:18`, used by `scaffold.py:20`); reusing the existing
  `_env()` factory covers all rendering. stdlib `hashlib` (SHA-256) +
  `pathlib` + `dataclasses` + `typing` + `yaml` (frontmatter parsing,
  already a dep) cover the registry + catalog.
- `decision-code-linking` (shipped v0.2.0) — `STRICT_TDD_PROMPT` and
  the 3 auto-suggest constants are the source artifacts for migration.
  The `prompt_fn=Callable` injection point at `engram_io.py:541` is
  preserved as-is.
- `vector-semantic-search` (shipped v0.4.0) — `VECTOR_COUNTER_NAMES`
  catalog at `observability.py:85` is the structural template for
  `PROMPT_REGISTRY`. Same dataclass discipline, same `*_NAMES`
  constant pattern.
- `cross-project-federation` (shipped v0.5.0) — `FEDERATED_COUNTER_NAMES`
  catalog at `observability.py:104` is the second template.
- `graph-snapshots` (change #5, IN PROGRESS) — `SNAPSHOT_COUNTER_NAMES`
  catalog at `observability.py:124` is the third template; the
  6-SKILL.md hand-edit pattern (`CHANGELOG.md:13`) is the precedent
  REQ-49 formalizes.
- `observability` (change #6, IN PROGRESS) — `PROMPT_REGISTRY`
  mirrors the observability catalog pattern. MUST ARCHIVE before
  change #7 apply starts (so the catalog pattern is stable and
  reusable as a template).
- `prompt-registry` (#7, this change) — standalone; no outbound deps.

## Open Questions (for sdd-design)

The 10 questions below MUST be resolved in the design phase before
`sdd-spec` locks the requirement contract. Mirror of
[`explore.md`](./explore.md) §D, expanded with design-phase specifics.

1. **`prompts/` directory location** (D.1 from explore): does the
   new directory live at repo root (`<repo>/prompts/`) or inside the
   package (`src/flow_engineering/prompts/`)? **Recommend** repo root
   (mirrors `openspec/` first-class artifact convention; allows future
   external tools to read prompt files without importing
   `flow_engineering`). Decision needed: confirm the path matches the
   project's existing convention for non-Python content directories
   (the `templates/` directory lives inside the package — should the
   new directory follow suit or break the pattern?).

2. **Jinja2 autoescape scope** (D.2 from explore): enable autoescape
   unconditionally or only for HTML/XML extensions? **Recommend**
   `select_autoescape(default_for_string=True)` (autoescape ALL string
   variables by default; defensive; prevents control-character
   injection). Document the choice in
   `openspec/specs/prompt-registry/spec.md`. Decision needed: confirm
   that legitimate `{{ var }}` substitutions don't contain `<` or `&`
   in the existing 4 inline prompts (audit before design phase locks).

3. **Prompt schema versioning** (D.3 from explore): per-prompt
   `version: semver` or registry-wide single version? **Recommend**
   per-prompt `version: semver` in `PromptEntry` (allows independent
   evolution of each prompt); registry has its own `schema_version`
   (e.g., `"1.0"`) for the `PromptEntry` shape itself. Lint fails on
   `schema_version` mismatch.

4. **`flow prompts show` missing-variable behavior** (D.4 from
   explore): fail with error, render with empty substitution, or
   render with sentinel? **Recommend** (c) sentinel for
   `flow prompts show` (CLI is for inspection; sentinel like
   `<test_command>` is informative); (a) hard fail for runtime
   `render_prompt()` (must NOT silently inject empty strings into
   agent context). Decision needed: confirm the sentinel format
   matches the project's existing convention (no precedent — design
   phase picks).

5. **SKILL.md checksum strategy** (D.5 from explore): full file
   SHA-256 or frontmatter-only (parse YAML, hash the dict)? **Recommend**
   frontmatter-only (ignores whitespace drift in the body; semantic
   version metadata lives in frontmatter). Trade-off: loses
   body-change detection. Add `--strict` flag for paranoid mode
   (full file checksum). Decision needed: confirm the YAML parser
   handles the SKILL.md frontmatter shape correctly (audit 10 SKILL.md
   files before design phase).

6. **SKILL_CATALOG coverage** (D.6 from explore): include
   `prompts/sdd/*.md` (10 files) in addition to
   `skills/sdd-*/SKILL.md` (10 files), or just one? **Recommend**
   covering BOTH — they are maintained separately per OpenCode
   convention and the user wants drift detection on both. Total: 20
   catalog entries (10 SKILL.md + 10 prompt.md). Decision needed:
   confirm the user wants both surfaces covered (the explore notes
   "they appear to have overlapping content" — verify before locking).

7. **`.j2` metadata sidecars** (D.7 from explore): prompt metadata
   in `.j2` YAML frontmatter, or Python-only? **Recommend**
   Python-only for v1 (matches existing `scaffold.py` template
   convention; no YAML parser round-trip needed). Defer
   frontmatter-style `.j2` to v1.1 if external tooling needs it.
   Decision needed: confirm the v1 Python-only approach matches the
   project's existing convention (the existing 4 `.j2` files have NO
   frontmatter — extension would be a new pattern).

8. **`STRICT_TDD_PROMPT` migration strategy** (D.8 from explore):
   silent replace, deprecation warning, or alias for one release?
   **Recommend** (c) alias for v0.7.0 (thin wrapper that calls
   `render_prompt("strict_tdd", ...)`), remove in v0.8.0. Standard
   deprecation pattern. Avoids breaking external imports.

9. **`flow prompts check --update` auto-update** (D.9 from explore):
   report only, report + ask, or report + auto-update? **Recommend**
   (b) — report + ask `--update` flag. Auto-update would be
   dangerous (silently accepts upstream changes that may break
   flow). Decision needed: confirm the explicit-flag pattern matches
   user mental model (i.e., `--update` is opt-in, never default).

10. **Coordination with change #6 observability counters** (D.10 from
    explore): REQ-52 prompt counters (deferred to v1.1) — added to
    `observability.py` catalog, separate `prompt_registry` module, or
    deferred to change #6 extension? **Recommend** (a) — when REQ-52
    lands, add 3 prompt counters (`prompts_render_total`,
    `prompts_render_ms`, `prompts_render_failed_total`) to the
    existing `observability.py` catalog. Change #6 ships the read-side
    (`flow metrics`); change #7 ships the write-side for prompt
    counters. No new module. Decision needed: confirm the cross-change
    coordination is acceptable (change #7 must not block on change #6
    counter additions).

## Success Criteria

- [ ] `PROMPT_REGISTRY` is a single `dict[str, PromptEntry]` constant in
      `src/flow_engineering/prompt_registry.py` with 4 entries
      migrated from inline constants (REQ-45, 2 BDD scenarios)
- [ ] `render_prompt(prompt_id, **variables)` is the single render
      API; backed by a shared Jinja2 `Environment` (REQ-46, 3 BDD
      scenarios)
- [ ] `lint_registry()` returns zero warnings for the 4-entry
      registry; surfaces 5 warning categories on broken registries
      (REQ-47, 2 BDD scenarios)
- [ ] `SKILL_CATALOG` covers all 10 `sdd-*/SKILL.md` files with
      SHA-256 checksums; `flow prompts check` exits non-zero on drift
      (REQ-49, 2 BDD scenarios)
- [ ] `flow prompts list` renders a table of `{prompt_id, version,
      owner, location}` for all 4 entries (REQ-50, included in list
      scenario)
- [ ] `flow prompts show <id>` renders the resolved template with
      `--var key=value` substitution and sentinel for missing vars
      (REQ-50, included in show scenario)
- [ ] `flow prompts lint` exits 0 on clean registry, exits non-zero
      on warnings with `--strict` (REQ-50, included in lint scenario)
- [ ] `flow prompts check` walks the catalog, SHA-256s each on-disk
      SKILL.md frontmatter, reports drift; `--update` flag refreshes
      the sidecar (REQ-50, included in check scenario)
- [ ] The 4 existing inline constants (`STRICT_TDD_PROMPT`,
      `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`) are thin
      wrappers around `render_prompt()` for v0.7.0 (per D.8 alias)
- [ ] All existing 783 tests pass; `ruff check` clean on changed files
- [ ] Strict TDD evidence: every public helper has RED→GREEN→REFACTOR
      history in commit log; per-commit work-unit splits per
      `work-unit-commits` skill (5-6 commits each ≤400 LOC)
- [ ] Secrets invariant: a prompt containing `secrets.yaml` (via a
      future code_refs integration) does NOT leak the file path into
      the rendered output beyond the documented variable substitution
- [ ] REQ-1..8 (decision-code-linking) unchanged
- [ ] REQ-9..16 (decision-reality-drift) unchanged
- [ ] REQ-17..22 (vector-semantic-search) unchanged
- [ ] REQ-23..27 (cross-project-federation) unchanged
- [ ] REQ-28..34 (graph-snapshots) unchanged
- [ ] REQ-35..39 (observability) unchanged — no shared mutable state,
      no shared event sink, no shared lookup table with the new
      `prompt_registry.py` module
- [ ] The `prompt_fn=Callable` injection point at `engram_io.py:541`
      is preserved as-is (testable seam still works)
- [ ] `scaffold.py:_env()` is preserved as a thin re-export from
      `prompt_render._env()` (no import cycle)
- [ ] `openspec/specs/prompt-registry/spec.md` is NEW; no existing
      capability spec modified

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | 4 inline prompts (`STRICT_TDD_PROMPT`, etc.) migrated into `PROMPT_REGISTRY`; `prompt_fn=Callable` seam preserved | Compatible (consumes the migration) |
| `decision-reality-drift` (shipped v0.3.0) | Drift path unaffected — no prompts in drift surface | Compatible (no intersection) |
| `vector-semantic-search` (shipped v0.4.0) | `VECTOR_COUNTER_NAMES` catalog at `observability.py:85` is the structural template for `PROMPT_REGISTRY`; no shared mutable state | Compatible (no intersection) |
| `cross-project-federation` (shipped v0.5.0) | `FEDERATED_COUNTER_NAMES` catalog at `observability.py:104` is the second template; "federated prompt registry" deferred | Compatible (no intersection) |
| `graph-snapshots` (change #5, IN PROGRESS) | `SNAPSHOT_COUNTER_NAMES` catalog at `observability.py:124` is the third template; 6-SKILL.md hand-edit pattern (`CHANGELOG.md:13`) formalized by REQ-49 | Compatible (REQ-49 supersedes the hand-edit pattern with a catalog) |
| `observability` (change #6, IN PROGRESS) | `PROMPT_REGISTRY` mirrors the observability catalog pattern; REQ-52 prompt counters (deferred) will land in `observability.py` per D.10 | MUST ARCHIVE BEFORE change #7 apply; coordinate via orchestrator |
| `prompt-registry` (#7, this change) | Standalone; no outbound deps | Self |

**Unblocks**: discoverable prompt surface for the 4 inline + 4 Jinja2
+ 10 OpenCode runtime prompts already shipped (REQ-45 + REQ-49);
linted prompt registry catching typos at CI time (REQ-47); CLI
surface for prompt inspection (REQ-50); manifest-driven SKILL.md
drift detection replacing the 6-file hand-edit pattern from
`graph-snapshots` (REQ-49); and — as a foundation — a
deterministic, versioned, regression-tested prompt surface that
future LLM-backed REQs (e.g., "REQ-NN: `flow drift --llm-summary`"
or "REQ-MM: auto-prompt-tuning") can plug into.

**Constrains**: any future change that adds a prompt MUST either
add it to `PROMPT_REGISTRY` (with `version`, `owner`, `variables`,
`schema_version`) or update the `PROMPT_REGISTRY` schema; the
existing inline constants (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`,
`PROMPT_HEADER`, `PROMPT_FOOTER`) are thin wrappers for v0.7.0
only and MUST be removed in v0.8.0 (per D.8 alias convention); the
flat text default of `flow metrics` is unaffected (no changes to
the observability CLI surface).

## Estimated Effort

- **Apply LOC (forecast)**: ~833 production + ~2 260 tests = ~3 243
  forecast total. Realistic ×6 TDD multiplier (per `decision-code-linking`
  S3 precedent): ~18 710 realistic.
- **Chained PR strategy**: **YES — 2 chained PRs** (mandatory given the
  realistic LOC exceeds the 400-line review budget by ~47×):
  - **PR#1 (foundation)** — REQ-45 + REQ-46 + REQ-47 + the 4 new
    `.j2` files. Forecast ~600; realistic ~3 600.
  - **PR#2 (discovery + integration)** — REQ-49 + REQ-50 +
    `openspec/specs/prompt-registry/spec.md` bootstrap. Forecast
    ~650; realistic ~3 900.
  - Per-PR work-unit commit splits per `work-unit-commits` skill
    (5-6 commits each ≤400 LOC).
- **Phase estimate**:
  - ~25min explore (DONE; Engram #198)
  - ~12min propose (this phase)
  - ~35min design
  - ~30min spec
  - ~25min tasks
  - ~120-150min apply across 2 chained PRs (PR#1 ~70min, PR#2 ~60min)
  - ~20min verify
  - ~12min archive
  - **Total ~4.5-5h end-to-end**

## References

- Explore: [`explore.md`](./explore.md) (Engram #198, full option matrix)
- Prior patterns:
  - `openspec/changes/observability/` (change #6, closest precedent — same catalog + CLI + chained-PR pattern)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/` (change #5, single-PR precedent; 6-SKILL.md hand-edit pattern formalized by REQ-49)
  - `openspec/changes/archive/2026-06-26-cross-project-federation/` (change #4, chained-PR precedent)
  - `openspec/changes/archive/2026-06-26-vector-semantic-search/` (change #3, observability-adjacent counter catalog pattern)
- Counter catalog patterns: REQ-22 (`VECTOR_COUNTER_NAMES` at
  `observability.py:85`), REQ-26 (`FEDERATED_COUNTER_NAMES` at
  `observability.py:104`), REQ-26 T1.7 (`SNAPSHOT_COUNTER_NAMES` at
  `observability.py:124`) — all structural templates for
  `PROMPT_REGISTRY`
- Jinja2 scaffold convention: `src/flow_engineering/scaffold.py:20`
  (`_env() -> Environment` factory) + `src/flow_engineering/templates/`
  (4 `.j2` files)
- Carry-forwards: `observability` explore #195 line 263 (alerting is
  ENGINEERING, not prompt-registry); `cross-project-federation`
  archive-report #61 ("federated prompt registry" deferred);
  `graph-snapshots` CHANGELOG.md:13 (6-SKILL.md hand-edit precedent)
- Precedent: `decision-code-linking` archive-report #119 S3
  (BDD step def file 5-6× growth multiplier) — absorbed into
  the ×6 forecast

## Next Step

Ready for `sdd-design prompt-registry`. The 10 open questions above
MUST be resolved in the design phase (especially #1 `prompts/`
directory location, #5 SKILL.md checksum strategy, #6 SKILL_CATALOG
coverage, and #10 observability cross-change coordination) before
`sdd-spec` locks the requirement contract. **2 chained PRs** —
foundation PR#1 first (REQ-45 + REQ-46 + REQ-47 + 4 new `.j2` files),
discovery PR#2 second (REQ-49 + REQ-50 + spec bootstrap).
Coordination: change #6 observability MUST archive before change
#7 apply starts.

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
      "label": "prompt_lint.py (NEW — lint_registry() + LintWarning dataclass + 5 warning categories; ~80 prod LOC)",
      "file": "src/flow_engineering/prompt_lint.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_opencode_skill_catalog_module",
      "label": "opencode_skill_catalog.py (NEW — SKILL_CATALOG, SkillEntry dataclass, checksum verification, frontmatter parsing; ~120 prod LOC)",
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
      "id": "src_flow_engineering_scaffold_jinja_env_factory",
      "label": "scaffold.py _env() (line 20) — REFACTOR TARGET: hoisted into prompt_render._env(); scaffold.py keeps thin re-export",
      "file": "src/flow_engineering/scaffold.py",
      "line": 20,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_templates_directory",
      "label": "src/flow_engineering/templates/ (4 .j2 files for new-change and new-project scaffolding) — EXISTING; scaffold.py still loads them via prompt_render._env() after refactor",
      "file": "src/flow_engineering/templates",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_prompts_group",
      "label": "flow prompts CLI group (cli.py, NEW) — 4 subcommands (list, show <id>, lint, check); ~150 prod LOC delta; mirrors flow metrics surface pattern",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "prompts_repo_root_directory",
      "label": "<repo>/prompts/ (NEW — repo root location per D.1) — 4 .j2 files (strict_tdd, auto_suggest_header, auto_suggest_footer, auto_suggest_empty); mirrors openspec/ first-class artifact convention",
      "file": "prompts",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_prompt_registry_spec",
      "label": "openspec/specs/prompt-registry/spec.md (NEW — capability spec cataloging 8 prompt entries + 10 SKILL.md catalog entries + drift detection contract; ~150 LOC)",
      "file": "openspec/specs/prompt-registry/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "flow_engineering_prompt_checksums_sidecar",
      "label": "~/.flow-engineering/prompt_checksums.json (NEW sidecar, parallel to metrics.jsonl) — SHA-256 frontmatter checksums per skill; bootstrapped via `flow prompts check --init`",
      "file": ".flow-engineering/prompt_checksums.json",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_apply",
      "label": "~/.config/opencode/skills/sdd-apply/SKILL.md (v3.0) — cataloged in SKILL_CATALOG; flow apply delegates to this agent",
      "file": "~/.config/opencode/skills/sdd-apply/SKILL.md",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_verify",
      "label": "~/.config/opencode/skills/sdd-verify/SKILL.md — cataloged in SKILL_CATALOG; flow verify delegates to this agent",
      "file": "~/.config/opencode/skills/sdd-verify/SKILL.md",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_archive",
      "label": "~/.config/opencode/skills/sdd-archive/SKILL.md — cataloged in SKILL_CATALOG; flow archive delegates to this agent",
      "file": "~/.config/opencode/skills/sdd-archive/SKILL.md",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_prompt_fn_seam",
      "label": "engram_io.py prompt_fn=Callable injection point (line 541) — PRESERVED AS-IS (testable seam still works); no migration needed",
      "file": "src/flow_engineering/engram_io.py",
      "line": 541,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_vector_counter_names_template",
      "label": "VECTOR_COUNTER_NAMES catalog (observability.py:85) — STRUCTURAL TEMPLATE for PROMPT_REGISTRY; same dataclass discipline, same *_NAMES constant pattern",
      "file": "src/flow_engineering/observability.py",
      "line": 85,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req45_prompt_registry",
      "label": "tests/bdd/req45_prompt_registry.feature (NEW — 2 BDD scenarios: registry has 4 entries, entries have required schema fields)",
      "file": "tests/bdd/req45_prompt_registry.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req46_prompt_render",
      "label": "tests/bdd/req46_prompt_render.feature (NEW — 3 BDD scenarios: render with vars, render missing var fails, autoescape blocks HTML injection)",
      "file": "tests/bdd/req46_prompt_render.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req47_prompt_lint",
      "label": "tests/bdd/req47_prompt_lint.feature (NEW — 2 BDD scenarios: clean registry lints clean, broken registry lints 3+ warnings)",
      "file": "tests/bdd/req47_prompt_lint.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req49_skill_catalog",
      "label": "tests/bdd/req49_skill_catalog.feature (NEW — 2 BDD scenarios: clean SKILL.md match, drift detected)",
      "file": "tests/bdd/req49_skill_catalog.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req50_cli_prompts",
      "label": "tests/bdd/req50_cli_prompts.feature (NEW — 3 BDD scenarios: list renders table, show renders prompt, check exits non-zero on drift)",
      "file": "tests/bdd/req50_cli_prompts.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_prompt_registry_steps",
      "label": "tests/bdd/test_prompt_registry_steps.py (NEW — pytest-bdd glue shared across 5 BDD features; ~400 LOC; realistic ~2400 per ×6 multiplier)",
      "file": "tests/bdd/test_prompt_registry_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_prompts",
      "label": "tests/unit/test_cli_prompts.py (NEW — full CLI surface coverage for flow prompts list/show/lint/check; ~400 LOC)",
      "file": "tests/unit/test_cli_prompts.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}