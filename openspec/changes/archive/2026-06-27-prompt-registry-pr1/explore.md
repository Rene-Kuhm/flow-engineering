<!-- explore.md: change #7 prompt-registry. Source: manual. -->
# Explore: prompt-registry (change #7)

**Change:** `prompt-registry`
**Scope:** Investigate the existing prompt/template surface in flow-engineering (inline CLI strings + Jinja2 scaffolding + OpenCode runtime SKILL.md agent registry); identify user-facing gaps; propose REQs for change #7.
**Date:** 2026-06-27
**Status:** EXPLORED → ready for sdd-propose
**Strict TDD:** ON for the IMPLEMENTATION phase; this explore work is read-only report production.
**Builds on:** change #1 (decision-code-linking — REQ-6 auto-suggest prompt), change #4 (cross-project-federation — scaffold template reuse precedent), change #6 (observability — JSONL counter-sink catalog pattern that this change mirrors for prompts).

---

## Why this change exists

The user prompt framing lists four candidate interpretations: (1) internal prompt/system-prompt catalog for the `flow` CLI's LLM calls, (2) the OpenCode runtime SKILL.md registry at `~/.config/opencode/skills/`, (3) a registry of CLI-facing user prompts (inspect/drift/snapshots), (4) test fixtures / golden prompt registry. After investigating the codebase end-to-end, the truth is **a hybrid of (3) and (2)** with **a touch of (1)**:

- **(3) is dominant** — `flow` itself ships **inline string constants** used as user-facing prompts (TTY confirmations, strict-TDD injection, error messages) plus **Jinja2 templates** for change/project scaffolding. There is NO central registry; each prompt is a module-level `str` constant or a `.j2` file. Total: **5 inline constants + 4 Jinja2 templates** today.
- **(2) is structurally present but OUT OF REPO** — OpenCode's `~/.config/opencode/skills/sdd-*/SKILL.md` (10 files) plus `~/.config/opencode/prompts/sdd/sdd-*.md` (10 files) define the system prompts for the sdd-* sub-agents that drive the entire SDD cycle. These are the project's "agent prompt registry" in spirit, but they live outside the repo, are versioned via YAML frontmatter (`version: "3.0"`), and have no synchronisation hook with the flow-engineering codebase. Version skew between a SKILL.md change and a related `flow` CLI change cannot be detected today.
- **(1) is hypothetical** — flow-engineering has **NO LLM client dependency** (`pyproject.toml` lists `click`, `jinja2`, `watchdog`, `pydantic`, `pyyaml`, `numpy`; no `openai`, `anthropic`, `litellm`, `langchain`). The repo's only "LLM-adjacent" surface is `embedding_provider.py` (REQ-19, sentence-transformers), which takes pre-computed text and returns vectors — no prompt construction. The `flow` CLI today does NOT call any LLM.
- **(4) is nonexistent** — there are no golden prompt fixtures; no snapshot tests of rendered output; no prompt-regression CI gate.

The headline use case for change #7 (synthesized from the existing gaps): the user wants a **single source of truth for prompts** — both the user-facing strings inside `flow` AND a mirroring index of the OpenCode SKILL.md agent prompts — so that (a) inline prompts can be versioned, linted, A/B-tested, and golden-tested like the observability counters after change #6, (b) the OpenCode SKILL.md runtime surface is visible from the repo (so drift between the SKILL.md registry and the flow-engineering CLI is detectable), and (c) future LLM-backed features (when they land — e.g., a "natural-language drift summary" or "LLM-assisted spec drift detection") have a registry to plug into instead of inventing one ad-hoc.

**Scope-out reminder**: this change does NOT add an LLM client. It builds the registry/catalog/lint/golden-test surface so that **future LLM-backed REQs** (e.g., "REQ-NN: `flow drift --llm-summary`" or "REQ-MM: auto-prompt-tuning") have a deterministic, versioned, regression-tested prompt surface to plug into. The registry must be **provider-agnostic** (it stores `prompt_id + template + variables` — the LLM call itself is someone else's job).

---

## A. Current State

### A.1 Inline prompt constants in `src/flow_engineering/` (5 total)

| File | Constant | Line | Length | Purpose |
|---|---|---|---|---|
| `strict_tdd.py` | `STRICT_TDD_PROMPT` | 13 | 1 line | System-injected TDD reminder |
| `auto_suggest_code_refs.py` | `EMPTY_PROMPT_TEXT` | 47 | 1 line | Empty-list TTY message |
| `auto_suggest_code_refs.py` | `PROMPT_HEADER` | 48 | 1 line | TTY interactive header |
| `auto_suggest_code_refs.py` | `PROMPT_FOOTER` | 49 | 3 lines | TTY interactive footer (multi-line) |
| `engram_io.py` | (5× `prompt_fn=None` kwargs) | 541, 570, 680, 716 | n/a | Callable injection point (testable seam, not a prompt) |

**Count**: 4 actual prompt strings + 1 prompt-function injection pattern. All 4 are **module-level `str` constants**, no templating, no parameter validation, no version metadata, no i18n hook.

**`STRICT_TDD_PROMPT` details** (strict_tdd.py:13-16):

```python
STRICT_TDD_PROMPT = (
    "STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. "
    "You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
)
```

- Single `{test_command}` placeholder, `.format()`-rendered in `build_strict_tdd_instruction()` (line 84).
- No validation that `test_command` is non-empty (would render as `(unknown — check project)` fallback at line 83).
- No version stamp, no schema, no tests asserting the rendered string beyond `build_strict_tdd_instruction` returning a non-empty string (`tests/unit/test_strict_tdd.py:75`).

**`PROMPT_HEADER`/`FOOTER`/`EMPTY_PROMPT_TEXT` details** (auto_suggest_code_refs.py:47-51):

```python
EMPTY_PROMPT_TEXT: str = "No auto-suggested bindings available."
PROMPT_HEADER: str = "Auto-suggested code bindings:"
PROMPT_FOOTER: str = (
    "Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)"
)
```

- 3 related constants assembled by `format_suggestion_prompt(refs)` (line 89).
- The output format is a multi-line string with f-string interpolation in the loop body (line 100: `f"  [{i}] {r.label} ({r.file}:{r.line}, score={r.confidence:.2f}, id={r.id})"`).
- Format is golden-tested via `TestFormatSuggestionPrompt` in `tests/unit/test_auto_suggest.py:289-307` (2 tests, very narrow).

### A.2 Jinja2 templates in `src/flow_engineering/templates/` (4 files, all scaffolding-related)

| Path | LOC | Purpose |
|---|---|---|
| `new-change/change.yaml.j2` | 4 | Renders `change.yaml` manifest for `flow new` |
| `new-change/explore/exploration.md.j2` | 3 | Renders placeholder `exploration.md` |
| `new-project/README.md.j2` | 18 | Renders bootstrap `README.md` |
| `new-project/flow-version.j2` | 1 | Renders `.flow-version` file |

Loaded via `scaffold.py`:

- `_TEMPLATE_DIR = Path(__file__).parent / "templates"` (line 17).
- `_env() -> Environment` factory at line 20 — single shared `Environment` with `FileSystemLoader`, `autoescape=select_autoescape()`, `keep_trailing_newline=True`.
- Used in 3 functions: `render_new_change()` (line 28), `render_new_project()` (line 70), `scaffold_change()` (line 100).
- All templates use `{{ var }}` interpolation (no `{% if %}` blocks except the `for p in cross_projects` loop in `change.yaml.j2:3`).

**Pattern observed**: the Jinja2 environment is **scoped to `scaffold.py` only**. There is no shared prompt-rendering module that other parts of `flow` can reuse. Adding a new prompt template today means either (a) adding a new `.j2` file under `templates/` AND threading a new `_env()` call through the relevant caller, or (b) inlining a new `str` constant in a new module.

### A.3 The OpenCode runtime SKILL.md agent registry (NOT in repo — structurally critical context)

The `~/.config/opencode/` directory has TWO parallel registries for the sdd-* sub-agents that drive the entire SDD workflow:

**A.3.1 Skill registry** — `~/.config/opencode/skills/` (24 skill directories total, 10 sdd-* + 14 other tools):

| Skill | SKILL.md LOC | Frontmatter `version` |
|---|---|---|
| `sdd-init` | ~120 | 3.0 |
| `sdd-explore` | ~140 | 2.0 |
| `sdd-propose` | ~150 | (TBD) |
| `sdd-design` | (similar) | (TBD) |
| `sdd-spec` | (similar) | (TBD) |
| `sdd-tasks` | (similar) | (TBD) |
| `sdd-apply` | ~250 | 3.0 |
| `sdd-verify` | (similar) | (TBD) |
| `sdd-archive` | (similar) | (TBD) |
| `sdd-onboard` | (similar) | (TBD) |

**A.3.2 Prompt registry** — `~/.config/opencode/prompts/sdd/` (10 `.md` files):

| File | Author | Frontmatter `version` |
|---|---|---|
| `sdd-explore.md` | gentleman-programming | 2.0 |
| `sdd-init.md` | gentleman-programming | 3.0 |
| `sdd-apply.md` | gentleman-programming | 3.0 |
| `sdd-propose.md` | gentleman-programming | (TBD) |
| `sdd-design.md` | gentleman-programming | (TBD) |
| `sdd-spec.md` | gentleman-programming | (TBD) |
| `sdd-tasks.md` | gentleman-programming | (TBD) |
| `sdd-verify.md` | gentleman-programming | (TBD) |
| `sdd-archive.md` | gentleman-programming | (TBD) |
| `sdd-onboard.md` | gentleman-programming | (TBD) |

**Pattern observed**: every sdd-* file has a `## ORCHESTRATOR GATE` block at the top that says "If you loaded this skill via the `skill()` tool, you are the ORCHESTRATOR — STOP. Do NOT execute these instructions inline. Delegate to the dedicated `sdd-XXX` sub-agent using your platform's delegation primitive." This is a runtime-only contract — not enforced by `flow` itself.

**The version skew problem**: SKILL.md files are versioned (e.g., `version: "3.0"`) but the flow-engineering repo has no awareness of these versions. When the SKILL.md for `sdd-apply` gets bumped from 3.0 → 4.0 (changing, say, the strict-TDD injection contract), nothing in `flow apply` reflects that. There is NO bidirectional link. The 4 commands in `flow` that produce change artifacts (`new`, `new-project`, `apply`, `verify`) were **built without a contract** to the SKILL.md that runs them.

**Relationship to change #7**: the user prompt's interpretation #2 ("runtime SKILL.md registry, managed via OpenCode runtime, NOT in the repo") matches reality. Change #7 should ship **a mirror catalog in the repo** — not a copy of the SKILL.md files themselves (that would create two sources of truth), but a structured `prompts/registry.toml` (or similar) listing the expected SKILL.md name, expected version, expected path, and last-verified checksum. `flow prompts check` then asserts that the on-disk SKILL.md matches the catalog — surfacing drift. This is exactly the catalog pattern that change #6 ships for observability counters, applied to the prompt surface.

### A.4 `flow` CLI surface relevant to prompts (existing commands that RENDER or CONSUME prompts)

| Command | Line | Prompt-related behaviour |
|---|---|---|
| `flow new <change>` | cli.py:48 | Calls `scaffold_change()` → `render_new_change()` → Jinja2 templates |
| `flow new-project <name>` | cli.py:80 | Calls `render_new_project()` → Jinja2 templates |
| `flow save <change>` (REQ-6 path) | engram_io.py:532-577 | May invoke `auto_suggest_code_refs()` which uses `PromptFn` to render the TTY prompt |
| `flow apply <change>` | orchestrator.py:39 | Delegates to `sdd-apply` sub-agent (runtime OpenCode SKILL.md `sdd-apply/SKILL.md`) — the agent's prompt is NOT in the repo |
| `flow verify <change>` | orchestrator.py:150 | Delegates to `sdd-verify` sub-agent (runtime SKILL.md) — same |
| `flow archive <change>` | orchestrator.py:265 | Delegates to `sdd-archive` sub-agent (runtime SKILL.md) — same |
| `flow drift <change>` | cli.py:1101+ | Does NOT delegate; renders drift report locally — no prompt involved |
| `flow snapshot ...` | cli.py:1547+ | Does NOT delegate; renders snapshot table — no prompt involved |
| `flow metrics` | cli.py:977+ | Does NOT delegate; renders counter summary — no prompt involved |
| `flow inspect <change>` | cli.py:936+ | Does NOT delegate; renders decision table — no prompt involved |

**Observation**: 4 of the 9 user-facing CLI subcommands (`apply`, `verify`, `archive`, and the SKILL.md-running variant of `new`) **delegate to runtime agent prompts that live outside the repo**. The `apply` / `verify` / `archive` flow is the **architecturally critical case** because those commands are how the SDD cycle actually progresses — but the prompts driving them are NOT in version control alongside the code that invokes them.

### A.5 Test coverage of existing prompts

| Test file | LOC | What it asserts |
|---|---|---|
| `tests/unit/test_strict_tdd.py` | 119 | `build_strict_tdd_instruction` returns a non-empty string with the test command injected; `STRICT_TDD_PROMPT.format(test_command=cmd)` shape only |
| `tests/unit/test_auto_suggest.py` (`TestFormatSuggestionPrompt`) | ~50 | `format_suggestion_prompt(refs)` returns a deterministic multi-line string for non-empty + empty inputs |
| `tests/unit/test_scaffold.py` | 82 | `render_new_change` / `render_new_project` produce the expected files (file existence + content presence — NOT a golden snapshot) |
| `tests/unit/test_observability_*.py` | n/a | NOT prompt-related; included for catalogue parallel |

**Coverage gaps for change #7**:

- No BDD feature file covers any prompt surface (`grep -r "prompt|Prompt" tests/bdd/ --include="*.feature"` shows only the interactive-prompt scenario in `req6_auto_suggest.feature:5` which tests user-TTY behavior, not the prompt surface).
- No golden snapshot test of the rendered prompt output (any tweak to `PROMPT_HEADER` would silently change behavior).
- No test asserts that `STRICT_TDD_PROMPT` contains the expected `{test_command}` placeholder (only the post-render assertion exists).
- No test exercises the OpenCode SKILL.md mirror catalog (does not exist).

### A.6 Deferred work from prior changes (sourced from archive reports — anything prompt-related)

| Source | Item | Status |
|---|---|---|
| observability explore #195 line 263 | "Alerting via daemon (`flow watch`) is a different change (#7 prompt-registry territory)" | INFORMAL — the prior explore agent flagged alerting as "change #7 territory" without elaborating. Change #7 should reframe: alerting is an ENGINEERING decision, NOT a prompt-registry decision. Scope this OUT of change #7. |
| cross-project-federation archive-report #61 | Specified the "project" field on observations; deferred the broader "federated prompt registry" question (no actual prompt registry existed at the time) | INFORMAL — no concrete prompt-registry ask was filed |
| graph-snapshots archive-report | 6 SKILL.md runtime files updated with the snapshot hook (`CHANGELOG.md:13` notes) | INFORMAL — change #5 confirmed the pattern of updating 6 SKILL.md files when shipping a flow change. This is the precedent change #7 formalizes (a CATALOG of SKILL.md files instead of hand-edits). |
| decision-code-linking archive-report S3 | BDD step def file 621 LOC vs 30 LOC forecast (5-6× growth) | PATTERN PRECEDENT — applies to change #7 BDD step def growth |

---

## B. Gap Analysis

10 user-facing gaps. Severity is rated against the project's needs (1 active user, 783 tests, 5 shipped changes + change #6 in spec, ~170 observations, ~10 SKILL.md runtime files).

### Gap 1 — No central prompt registry (single source of truth) [HIGH]

**What**: Prompt constants live as inline `str` literals at the top of `strict_tdd.py` and `auto_suggest_code_refs.py`. To find "all prompts in `flow`" today, a developer must `grep -r "PROMPT\|prompt" src/flow_engineering/` and read module docstrings. There is no `PROMPT_REGISTRY` constant analogous to `VECTOR_COUNTER_NAMES` or `SNAPSHOT_COUNTER_NAMES` (observability.py:70, 124).

**Why HIGH**: When a future change adds an LLM-backed feature (e.g., `flow drift --llm-summary`), the developer has to either (a) invent a new module-level constant or (b) extend `scaffold.py`. No precedent. The cost of NOT having a registry compounds: 4 prompts today → 40 prompts in 18 months. Cataloging now is cheap; cataloging later is expensive.

**Proposed REQ**: **REQ-45** — `src/flow_engineering/prompt_registry.py` (NEW) with `PROMPT_REGISTRY: dict[str, PromptEntry]` mapping `prompt_id → {template, variables, version, owner, location, schema_version}`. Migrate `STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER` into the registry.

---

### Gap 2 — No Jinja2-backed prompt rendering layer (template engine) [HIGH]

**What**: `scaffold.py` has a private `_env() -> Environment` factory used only for scaffolding templates. There is no shared prompt-rendering module that other parts of `flow` can call. `STRICT_TDD_PROMPT.format(test_command=...)` uses Python `str.format()` (no autoescape, no schema validation, no filter pipeline). The auto-suggest prompt uses f-strings inside a loop (no templating layer at all).

**Why HIGH**: Jinja2 is already a project dependency (`pyproject.toml:18`). Adopting it for ALL prompt rendering gives us autoescape, custom filters (`upper`, `quote`, `truncate`), and a single mental model. Without it, every prompt is a hand-rolled string assembly.

**Proposed REQ**: **REQ-46** — `src/flow_engineering/prompt_render.py` (NEW) with `render_prompt(prompt_id, **variables) -> str`. Backed by a Jinja2 `Environment` shared with `scaffold.py` but exposed publicly. Adds a `prompts/` directory at repo root for `.j2` files. Migrates `STRICT_TDD_PROMPT`, `PROMPT_HEADER/FOOTER/EMPTY_PROMPT_TEXT` to `.j2` files.

---

### Gap 3 — No prompt linting (typos, broken placeholders, missing variables) [MEDIUM]

**What**: `STRICT_TDD_PROMPT.format(test_command="x")` would render `"STRICT TDD MODE IS ACTIVE. Test runner: x. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."` — fine. But a typo like `STRICT_TDD_PROMPT = "...Test runner: {test_comand}..."` (missing `m`) would only fail at format-time when `test_command="x"` is passed and a `KeyError` is raised. No lint catches this at test-collection or CI time. Same for `f"  [{i}] {r.label} ({r.file}:{r.line}, score={r.confidence:.2f}, id={r.id})"` — a typo in `.confidence` (e.g., `.confidance`) would render `0.00` silently instead of failing.

**Why MEDIUM**: For 4 prompts today, manual review catches this. For 40 prompts, it does not. The cost of NOT having a lint is "silent prompt corruption" — a deployed prompt with a typo breaks the user experience without any CI signal.

**Proposed REQ**: **REQ-47** — `src/flow_engineering/prompt_lint.py` (NEW) with `lint_registry(registry) -> list[LintWarning]`. Validates: (a) all `{{ var }}` placeholders match declared `variables`, (b) all declared `variables` are used by at least one placeholder, (c) Jinja2 templates parse cleanly, (d) autoescape is enabled. Bundled as `flow prompts lint` CLI subcommand and as a pytest fixture (`prompt_lint_clean`).

---

### Gap 4 — No prompt regression tests (golden snapshots) [MEDIUM]

**What**: No golden-file tests assert that `STRICT_TDD_PROMPT` renders to a specific string. The closest is `test_strict_tdd.py:75` which only asserts the result is non-empty. If a developer tweaks the prompt wording, no test fails. There is NO prompt snapshot regression suite.

**Why MEDIUM**: Prompts ARE user-facing artifacts. A typo in a TTY confirmation prompt is as user-visible as a typo in a CLI error message. Golden regression tests would catch prompt drift in CI.

**Proposed REQ**: **REQ-48** — `tests/unit/test_prompt_registry.py` (NEW) with `pytest` golden snapshots for every entry in `PROMPT_REGISTRY`. For each entry, `render_prompt(prompt_id, **canonical_variables)` must equal the snapshot at `tests/golden/prompts/<prompt_id>.txt`. Adds a BDD feature `tests/bdd/req48_prompt_golden.feature` with 2 scenarios (golden match + golden update).

---

### Gap 5 — No OpenCode SKILL.md mirror catalog (version skew detection) [HIGH]

**What**: The OpenCode runtime SKILL.md files at `~/.config/opencode/skills/sdd-*/SKILL.md` (10 files) drive the entire SDD cycle. They are versioned (`version: "3.0"` in YAML frontmatter). The flow-engineering repo has NO awareness of them — no manifest, no checksum, no lint. If `sdd-apply/SKILL.md` changes from 3.0 to 4.0, nothing in the repo surfaces it.

**Why HIGH**: This is the MOST IMPORTANT gap. The SDD cycle depends on these SKILL.md files being aligned with the `flow apply` / `flow verify` / `flow archive` commands. Version skew between them silently breaks the workflow. Today, the only signal is "the apply step seems to not be doing what the spec says" — far too late.

**Proposed REQ**: **REQ-49** — `src/flow_engineering/opencode_skill_catalog.py` (NEW) with `SKILL_CATALOG: dict[str, SkillEntry]` mapping `skill_name → {expected_version, expected_path, last_verified_checksum, owner}`. `flow prompts check` walks the catalog, computes SHA-256 of each on-disk SKILL.md, compares against `last_verified_checksum`, and exits non-zero on drift. Adds 1 BDD feature with 2 scenarios (clean state + drift detected).

---

### Gap 6 — No `flow prompts` CLI subcommand (observability-style read surface) [MEDIUM]

**What**: There is no `flow prompts` subcommand. The user cannot ask "list all prompts in `flow`" or "show me the rendered output of STRICT_TDD_PROMPT for `pytest`". The closest is `grep -r PROMPT src/` which is what this explore report literally had to do.

**Why MEDIUM**: Once a registry exists (REQ-45), it needs a CLI surface. Otherwise the registry is library-internal and not discoverable. The observability change #6 ships `flow metrics` for exactly this reason.

**Proposed REQ**: **REQ-50** — `flow prompts list`, `flow prompts show <prompt_id>`, `flow prompts lint`, `flow prompts check` (SKILL.md drift). Mirrors the `flow metrics` surface pattern. `flow prompts list` renders a table of `{prompt_id, version, owner, location}`; `flow prompts show <id>` renders the resolved template with a `--var key=value` option (repeatable).

---

### Gap 7 — No prompt version tracking (no diff capture on changes) [MEDIUM]

**What**: When `STRICT_TDD_PROMPT` changes (a developer tweaks wording), the diff is captured by git but is NOT captured in any prompt-specific artifact. There is no per-prompt changelog. There is no `PROMPT_CHANGELOG.md`.

**Why MEDIUM**: For LLM prompts (when they land), the wording is the API. A diff to the prompt wording IS a behavior change that the user should be able to audit. The observability change #6 ships a JSONL counter-sink precisely to capture observability events; an analogous `prompt_renders.jsonl` would capture every render (with prompt_id, version, variables, output) for offline analysis.

**Proposed REQ**: **REQ-51** (lower priority) — `prompt_renders.jsonl` append-only sink at `~/.flow-engineering/prompt_renders.jsonl` (parallels `metrics.jsonl`). Each render emits `{prompt_id, version, variables, output, ts}`. Opt-in via `FLOW_PROMPT_LOG=1`. `flow prompts show <id>` consults the sink to report "this prompt has been rendered N times in the last 30 days".

---

### Gap 8 — No prompt observability (which prompts are called how often, latency?) [MEDIUM]

**What**: Tied to REQ-51. There are NO counters like `prompt_render_total{prompt_id=...}`, `prompt_render_ms`, `prompt_render_failed_total`. When a prompt fails to render (e.g., missing variable), the failure is silent (a `KeyError` would propagate up to the caller).

**Why MEDIUM**: Same justification as REQ-51. For 4 prompts today, manual review is fine. For 40 prompts, observability is mandatory.

**Proposed REQ**: **REQ-52** (lower priority, bundles with REQ-51) — `prompts_render_total{prompt_id, version}`, `prompts_render_ms`, `prompts_render_failed_total{reason=missing_var|template_error|autoescape_blocked}`. Wired into `render_prompt()` and emitted via `observability.increment()`.

---

### Gap 9 — No prompt documentation (system prompts for end users are undocumented) [LOW-MEDIUM]

**What**: `PROMPT_HEADER` and `PROMPT_FOOTER` are user-facing TTY messages. They are NOT documented in any user-visible doc. The user discovers the prompt format only by running `flow save <change>` interactively. The `STRICT_TDD_PROMPT` injection is documented only in the AGENTS.md runtime contract (NOT in `FLOW.md` or `README.md`).

**Why LOW-MEDIUM**: For a 1-user tool this is acceptable. But the precedent of having user-facing CLI output strings scattered across `src/` (not in any doc) makes it hard for a future contributor to know "what does `flow` show the user?".

**Proposed REQ**: **REQ-53** (lower priority, v1.1) — `docs/prompts.md` (NEW) — a flat list of every entry in `PROMPT_REGISTRY` with `{prompt_id, purpose, where it appears, example output}`. Generated from the registry at build time (NOT hand-maintained). `flow prompts show <id>` cross-links to this doc.

---

### Gap 10 — Coupling with OpenCode runtime SKILL.md (cannot version-lock from the repo) [HIGH]

**What**: Tied to REQ-49 but with a different angle. The `flow apply` / `flow verify` / `flow archive` commands delegate to sdd-* sub-agents. The SKILL.md for each sub-agent defines the agent's prompt AND its contract with the orchestrator. If the SKILL.md changes (e.g., `sdd-apply` no longer expects `apply-progress` to be persisted in Engram), `flow apply` may silently break. There is NO version pin between the CLI and the SKILL.md.

**Why HIGH**: This is the SAME gap as #5 but framed as a version-pin problem rather than a drift-detection problem. The fix is the same catalog + a version assertion at CLI startup: `flow apply` checks that `~/.config/opencode/skills/sdd-apply/SKILL.md` has version >= the `MIN_SDD_APPLY_VERSION` declared in `pyproject.toml`. If not, exit with a clear error.

**Proposed REQ**: **REQ-54** — Add `min_sdd_skill_versions: dict[str, str]` to `pyproject.toml` (`[tool.flow_engineering]` section). `flow apply` / `verify` / `archive` assert at startup that the on-disk SKILL.md version is >= the minimum. Exits with `SkillVersionError` and a remediation message. Bundles naturally with REQ-49's catalog.

---

## C. Proposed Scope for Change #7

### C.1 Recommendation: TOP 5 gaps to address

The user prompt asks for the TOP 3-5. Based on severity + effort + precedent (change #6 observability catalog pattern):

| Priority | Gap | REQ | Effort |
|---|---|---|---|
| **P0 (must)** | Gap 1 — No central prompt registry | **REQ-45** `prompt_registry.py` with `PROMPT_REGISTRY` | M |
| **P0 (must)** | Gap 2 — No Jinja2 prompt rendering | **REQ-46** `prompt_render.py` + `prompts/` directory | M |
| **P0 (must)** | Gap 5 — No SKILL.md mirror catalog | **REQ-49** `opencode_skill_catalog.py` + `flow prompts check` | M |
| **P1 (should)** | Gap 3 — No prompt linting | **REQ-47** `prompt_lint.py` + `flow prompts lint` | S |
| **P1 (should)** | Gap 6 — No `flow prompts` CLI | **REQ-50** `flow prompts list/show/lint/check` | M |

Lower-priority (defer to v1.1 or a follow-up change):

- Gap 4 (golden regression) — **REQ-48** (could bundle into PR#1 if scope allows)
- Gap 7 (version tracking sink) — **REQ-51** (defer to v1.1)
- Gap 8 (prompt observability counters) — **REQ-52** (defer to v1.1, bundles with REQ-51)
- Gap 9 (prompt docs) — **REQ-53** (defer to v1.1)
- Gap 10 (version-pin enforcement) — **REQ-54** (could bundle into PR#2 if scope allows)

### C.2 REQ-by-REQ complexity forecast

For the P0/P1 scope (5 REQs):

| REQ | Title | Forecast LOC prod | Forecast LOC test | TDD multiplier ×6 | BDD scenarios |
|---|---|---|---|---|---|
| REQ-45 | `prompt_registry.py` + `PROMPT_REGISTRY` migration | ~120 | ~250 | ~720 | 2 |
| REQ-46 | `prompt_render.py` + `prompts/*.j2` migration | ~150 | ~300 | ~900 | 3 |
| REQ-47 | `prompt_lint.py` + `flow prompts lint` | ~80 | ~250 | ~600 | 2 |
| REQ-48 | `tests/unit/test_prompt_registry.py` golden snapshots | n/a (test only) | ~200 | ~200 | 2 |
| REQ-49 | `opencode_skill_catalog.py` + `flow prompts check` | ~120 | ~300 | ~720 | 2 |
| REQ-50 | `flow prompts list/show/lint/check` CLI | ~150 | ~400 | ~900 | 3 |
| **Total** | | **~620 prod** | **~1 700 test** | **~4 040 realistic** | **14 BDD** |

Plus shared infrastructure:

- `src/flow_engineering/prompt_registry.py` — NEW (~120 prod LOC; the registry dataclass + 4 migrated entries)
- `src/flow_engineering/prompt_render.py` — NEW (~150 prod LOC; Jinja2 env + `render_prompt()` API + filter pipeline)
- `src/flow_engineering/prompt_lint.py` — NEW (~80 prod LOC; `lint_registry()` + warning types)
- `src/flow_engineering/opencode_skill_catalog.py` — NEW (~120 prod LOC; `SKILL_CATALOG` + checksum verification)
- `src/flow_engineering/cli.py` — `flow prompts` group + 4 subcommands (~150 prod LOC delta)
- `prompts/strict_tdd.j2`, `prompts/auto_suggest_header.j2`, `prompts/auto_suggest_footer.j2`, `prompts/auto_suggest_empty.j2` — NEW (~30 total LOC of templates)
- `openspec/specs/prompt-registry/spec.md` — NEW (~150 LOC; capability spec cataloging all registry entries; resolves the SKILL.md drift detection contract)
- `CHANGELOG.md` v0.7.0 entry (~25 LOC)
- `pyproject.toml` version bump 0.6.0 → 0.7.0 (or whatever change #6 archives at)

**Grand total forecast**: ~1 250 LOC prod + test; realistic ×6 TDD multiplier: **~7 500 LOC**.

### C.3 PR split recommendation

**Recommend: 2 PRs (chained)** because the cumulative ~7 500 LOC realistic > the 400-line review budget:

| PR | Scope | REQs | Forecast LOC | Realistic ×6 |
|---|---|---|---|---|
| **PR#1** | Foundation: registry + Jinja2 rendering + lint | REQ-45 + REQ-46 + REQ-47 | ~600 | ~3 600 |
| **PR#2** | Discovery: CLI surface + SKILL.md mirror + version-pin | REQ-50 + REQ-49 + REQ-54 (optional) | ~650 | ~3 900 |

Per-PR work-unit commit splits per `work-unit-commits` skill convention (5-6 commits each ≤400 LOC).

Rationale for 2 PRs over 1:

- Cumulative realistic LOC ~7 500 is ~19× the 400-line review budget; even with per-commit splits the review load is heavy.
- PR#1 (registry + rendering + lint) is the "library" — high internal value, no user-visible CLI surface.
- PR#2 (CLI + SKILL.md mirror) is the "user-facing" surface — `flow prompts` is the new discoverability tool.

Chained-PR-as-commits pattern from `work-unit-commits` SKILL mitigates review tractability.

### C.4 Recommended 6-8 specific REQs

P0 (must, this change):

- **REQ-45** — `src/flow_engineering/prompt_registry.py` with `PROMPT_REGISTRY: dict[str, PromptEntry]` mapping `prompt_id → {template_id, version, owner, location, variables, schema_version}`. Migrates the 4 existing inline prompts.
- **REQ-46** — `src/flow_engineering/prompt_render.py` with `render_prompt(prompt_id, **variables) -> str`. Backed by a shared Jinja2 `Environment`. Adds `prompts/` directory at repo root for `.j2` files. Migrates the 4 existing inline prompts to `.j2`.
- **REQ-49** — `src/flow_engineering/opencode_skill_catalog.py` with `SKILL_CATALOG: dict[str, SkillEntry]`. `flow prompts check` walks the catalog, computes SHA-256 of each on-disk SKILL.md, reports drift.

P1 (should, this change):

- **REQ-47** — `src/flow_engineering/prompt_lint.py` with `lint_registry(registry) -> list[LintWarning]`. `flow prompts lint` surfaces warnings. CI integration via a `pytest` fixture (`prompt_lint_clean`).
- **REQ-50** — `flow prompts list` / `flow prompts show <id>` / `flow prompts lint` / `flow prompts check` CLI subcommands. Mirrors the `flow metrics` surface pattern.

P2 (could, v1.1 follow-up — listed for completeness):

- **REQ-48** — Golden regression tests via `pytest` snapshots at `tests/golden/prompts/<prompt_id>.txt`.
- **REQ-51** — `prompt_renders.jsonl` append-only sink at `~/.flow-engineering/prompt_renders.jsonl`.
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters wired into `render_prompt()`.
- **REQ-53** — `docs/prompts.md` generated from `PROMPT_REGISTRY` at build time.
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` in `pyproject.toml`; `flow apply` / `verify` / `archive` assert version >= minimum at startup.

### C.5 Dependencies on prior changes

- **observability (change #6, IN PROGRESS)** — REQ-47 lint + REQ-50 CLI mirror the observability catalog pattern (`VECTOR_COUNTER_NAMES`, `SNAPSHOT_COUNTER_NAMES`). Change #7 should wait for change #6 to ARCHIVE so the JSONL counter sink pattern is stable.
- **graph-snapshots (change #5, ARCHIVED)** — confirmed the precedent of updating 6 SKILL.md runtime files per `flow` change. REQ-49 formalizes the catalog so this hand-edit pattern can be replaced with a manifest-driven approach.
- **decision-code-linking (change #1)** — REQ-45/46/47 migrate the existing `STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER` from `strict_tdd.py` and `auto_suggest_code_refs.py`. These modules must be updated to call `render_prompt()` instead of returning inline strings. No breaking CLI behavior change expected.

**Coordination requirement**: change #6 archive should complete BEFORE change #7 apply starts (so the observability catalog pattern is stable and can be reused as a template for `PROMPT_REGISTRY`).

---

## D. Open Questions

10 questions for the design phase. Each is labeled with which prior change it relates to.

### D.1 Should `PROMPT_REGISTRY` live in `src/flow_engineering/` or in a top-level `prompts/` directory?

Today `templates/` lives inside `src/flow_engineering/templates/` (scaffold.py:17). REQ-46 proposes adding `prompts/` at the repo root. The question is whether the new directory should mirror `templates/`'s location or be hoisted.

**Relates to**: scaffold.py templates convention.

**Design needs**: Pick one. Recommend hoisting `prompts/` to repo root (mirrors `openspec/` convention for first-class artifacts; allows future external tools to read the prompt files without importing flow_engineering).

### D.2 Jinja2 autoescape: scope to all prompts or only specific types?

Jinja2 `select_autoescape()` defaults to enabling autoescape for HTML/XML extensions. For CLI prompts the autoescape behavior is irrelevant (no HTML involved). The question is whether to enable autoescape unconditionally (defensive) or disable it (no false positives).

**Relates to**: scaffold.py _env() at line 20-25.

**Design needs**: Recommend enable autoescape (`select_autoescape(enabled_extensions=())` with `default_for_string=True`) so untrusted variable substitution cannot inject control characters. Document the choice.

### D.3 Prompt schema versioning: per-prompt or registry-wide?

A prompt's template can change in two ways: (a) wording change (semver minor), (b) variable signature change (semver major). Should the registry track per-prompt versions or a single registry-wide version?

**Relates to**: REQ-45 PromptEntry schema.

**Design needs**: Recommend per-prompt `version: semver` in `PromptEntry`. Registry has its own `schema_version` (e.g., `"1.0"`). Lint fails on `schema_version` mismatch.

### D.4 Should `flow prompts show <id>` render with empty variables or fail?

If a prompt declares `{test_command}` but the user calls `flow prompts show strict_tdd` without `--var test_command=...`, should the render (a) fail with a clear error, (b) render with empty substitution `Test runner: .`, or (c) render with a sentinel like `<test_command>`?

**Relates to**: REQ-50 CLI surface.

**Design needs**: Pick one. Recommend (c) for `flow prompts show` (CLI is for inspection; sentinel is informative); (a) for runtime `render_prompt()` (must NOT silently inject empty strings into agent context).

### D.5 SKILL.md catalog: full checksum or partial (YAML frontmatter only)?

REQ-49 proposes SHA-256 of the entire SKILL.md file. But the YAML frontmatter (top ~10 lines) carries the meaningful version metadata. The body can have whitespace-only changes that trigger false-positive drift signals.

**Relates to**: REQ-49.

**Design needs**: Recommend frontmatter-only checksum (extract YAML, parse, hash the dict) — ignores whitespace drift in the body. Trade-off: loses body-change detection. Alternative: full checksum with `--strict` flag for paranoid mode.

### D.6 SKILL.md catalog: include `prompts/sdd/*.md` or only `skills/sdd-*/SKILL.md`?

There are 10 files in each directory, and they appear to have overlapping content (the SKILL.md is the user-facing metadata, the prompts/sdd/*.md is the actual prompt). Should REQ-49 cover both, or just one?

**Relates to**: A.3 OpenCode registry structure.

**Design needs**: Recommend covering BOTH (`skills/sdd-*/SKILL.md` AND `prompts/sdd/*.md`). They are maintained separately per OpenCode convention and the user would want drift detection on both.

### D.7 What goes in the `prompts/` directory — `.j2` files only, or also metadata sidecars?

Jinja2 templates are pure files. But the registry entry (`PROMPT_REGISTRY[prompt_id]`) has metadata (variables, version, owner, location) that could live either (a) inside the `.j2` file (as YAML frontmatter, like SKILL.md) or (b) in Python code only.

**Relates to**: REQ-45 + REQ-46.

**Design needs**: Recommend Python-only for v1 (matches existing `scaffold.py` template convention; no YAML parser needed). Defer frontmatter-style `.j2` to v1.1 if external tooling needs it.

### D.8 Migration strategy for `STRICT_TDD_PROMPT` — silent or loud?

REQ-45 migrates `STRICT_TDD_PROMPT` from `strict_tdd.py` to `PROMPT_REGISTRY`. Should the migration be (a) silent (no deprecation warning; just moved), (b) loud (deprecation warning on import), or (c) alias (both names export the same value for one release)?

**Relates to**: REQ-45 migration.

**Design needs**: Recommend (c) alias for one release (v0.7.0) then remove in v0.8.0. Standard deprecation pattern. Avoids breaking external imports.

### D.9 Should `flow prompts check` auto-update the checksum on drift detection?

If `flow prompts check` detects that a SKILL.md has changed (different checksum), should it (a) report only, (b) report + ask to update, (c) report + auto-update the catalog?

**Relates to**: REQ-49.

**Design needs**: Recommend (b) — report + ask `--update` flag. Auto-update would be dangerous (silently accepts upstream changes that may break flow).

### D.10 Coordination with change #6 observability: separate counters or unified?

REQ-52 proposes `prompts_render_total` / `prompts_render_ms` counters. Change #6 already ships 31+ counters in `observability.py`. Should prompt counters (a) be added to the same observability.py catalog, (b) live in a separate `prompt_registry` module, or (c) be deferred to change #6 extension?

**Relates to**: change #6 observability REQ-35 catalog.

**Design needs**: Recommend (a) — add 3 prompt counters to the existing catalog when REQ-52 lands. Change #6 ships the read-side; change #7 ships the write-side for prompt counters. No new module.

---

## E. Files to Touch

### E.1 Production files

| File | LOC delta | Type | Notes |
|---|---|---|---|
| `src/flow_engineering/prompt_registry.py` | +120 | **NEW** | `PROMPT_REGISTRY`, `PromptEntry` dataclass, 4 migrated entries |
| `src/flow_engineering/prompt_render.py` | +150 | **NEW** | Jinja2 `Environment` (shared with scaffold.py), `render_prompt()`, filter pipeline |
| `src/flow_engineering/prompt_lint.py` | +80 | **NEW** | `lint_registry()`, `LintWarning` dataclass, 5 warning categories |
| `src/flow_engineering/opencode_skill_catalog.py` | +120 | **NEW** | `SKILL_CATALOG`, `SkillEntry` dataclass, checksum verification, frontmatter parsing |
| `src/flow_engineering/strict_tdd.py` | +5 / -3 | modify | Replace `STRICT_TDD_PROMPT` constant with `render_prompt("strict_tdd", test_command=cmd)` call; remove inline string |
| `src/flow_engineering/auto_suggest_code_refs.py` | +10 / -6 | modify | Replace 3 inline constants with `render_prompt("auto_suggest_header", ...)`, etc.; `format_suggestion_prompt()` delegates to registry |
| `src/flow_engineering/scaffold.py` | +10 / -5 | modify | Refactor `_env()` to be shared via `prompt_render.py`; deprecate the local copy |
| `src/flow_engineering/cli.py` | +150 | modify | `flow prompts` group + 4 subcommands (`list`, `show <id>`, `lint`, `check`) |
| `prompts/strict_tdd.j2` | +4 | **NEW** | Jinja2 version of STRICT_TDD_PROMPT |
| `prompts/auto_suggest_header.j2` | +2 | **NEW** | Jinja2 version of PROMPT_HEADER |
| `prompts/auto_suggest_footer.j2` | +3 | **NEW** | Jinja2 version of PROMPT_FOOTER |
| `prompts/auto_suggest_empty.j2` | +1 | **NEW** | Jinja2 version of EMPTY_PROMPT_TEXT |
| `openspec/specs/prompt-registry/spec.md` | +150 | **NEW** | Capability spec cataloging all registry entries + SKILL.md mirror contract |
| `CHANGELOG.md` | +25 | modify | v0.7.0 entry (or whatever change #6 archives at) |
| `pyproject.toml` | +5 / -1 | modify | version bump 0.6.0 → 0.7.0; new `[tool.flow_engineering.prompts]` section for registry path + lint settings |

**Production total**: ~833 LOC delta (forecast ~833; realistic ×6 = ~5 000).

### E.2 Test files

| File | LOC delta | Type | Notes |
|---|---|---|---|
| `tests/unit/test_prompt_registry.py` | +250 | **NEW** | PROMPT_REGISTRY schema + 4 migrated entries; rendering tests |
| `tests/unit/test_prompt_render.py` | +300 | **NEW** | render_prompt() with variables, missing variable, template error |
| `tests/unit/test_prompt_lint.py` | +250 | **NEW** | lint_registry() with 5 warning categories |
| `tests/unit/test_opencode_skill_catalog.py` | +300 | **NEW** | SKILL_CATALOG + checksum + drift detection (mock SKILL.md files) |
| `tests/unit/test_cli_prompts.py` | +400 | **NEW** | full CLI surface coverage for `flow prompts list/show/lint/check` |
| `tests/bdd/req45_prompt_registry.feature` | +60 | **NEW** | 2 scenarios: registry has 4 entries, entries have required schema fields |
| `tests/bdd/req46_prompt_render.feature` | +80 | **NEW** | 3 scenarios: render with vars, render missing var fails, autoescape blocks HTML injection |
| `tests/bdd/req47_prompt_lint.feature` | +60 | **NEW** | 2 scenarios: clean registry lints clean, broken registry lints 3+ warnings |
| `tests/bdd/req49_skill_catalog.feature` | +80 | **NEW** | 2 scenarios: clean SKILL.md match, drift detected |
| `tests/bdd/req50_cli_prompts.feature` | +80 | **NEW** | 3 scenarios: list renders table, show renders prompt, check exits non-zero on drift |
| `tests/bdd/test_prompt_registry_steps.py` | +400 | **NEW** | pytest-bdd step glue shared across the 5 BDD features |

**Test total**: ~2 260 LOC (forecast; realistic ×6 = ~13 560).

### E.3 Runtime-only files (NOT in repo)

| File | LOC delta | Notes |
|---|---|---|
| `~/.config/opencode/skills/sdd-propose/SKILL.md` | +30 | Add `## Prompt registry hook` section: reference to REQ-45 PROMPT_REGISTRY for prompt discovery |
| `~/.config/opencode/skills/sdd-design/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-tasks/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-apply/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-verify/SKILL.md` | +40 | Add `Step 6c` sub-step: run `flow prompts check` and surface drift warnings |
| `~/.config/opencode/skills/sdd-archive/SKILL.md` | +20 | same |

**Runtime total**: ~150 LOC.

### E.4 Grand total

| Category | Forecast | Realistic ×6 |
|---|---|---|
| Production | ~833 LOC | ~5 000 LOC |
| Test | ~2 260 LOC | ~13 560 LOC |
| Runtime (SKILL.md) | ~150 LOC | (no multiplier) |
| **Grand total** | **~3 243 LOC** | **~18 710 LOC** |

Per-delegation batch ceiling (Engram #112, ≤6 tasks OR ≤150 LOC prod per delegation, ~15 min runtime): production work needs **~6 delegations** (833 / 150 = 5.5; round up). Test work needs **~15 delegations** (2 260 / 150 = 15). Total **~21 delegations** spread across 2 PRs (PR#1 = ~10 delegations, PR#2 = ~11 delegations). At ~15 min/delegation: ~5.25 hours total.

### E.5 Out-of-scope reminders (NOT in change #7)

These follow-ups land in v1.1 or named changes:

- **REQ-48** Golden regression tests — defer to v1.1 (could bundle into PR#1 if scope allows)
- **REQ-51** `prompt_renders.jsonl` sink — defer to v1.1
- **REQ-52** Prompt observability counters — defer to v1.1
- **REQ-53** `docs/prompts.md` — defer to v1.1
- **REQ-54** `min_sdd_skill_versions` enforcement — defer to v1.1 or bundle into PR#2
- **LLM client integration** (any actual `openai` / `anthropic` / `litellm` dependency) — NEVER (out of project scope per C.5)
- **i18n / multi-language prompts** — defer to v1.1+ (no current need)
- **Prompt A/B testing infrastructure** — defer to v1.1+ (only 4 prompts today)
- **External prompt marketplace / community registry** — NEVER (single-user tool)

---

## F. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | change #6 observability does not land before change #7 apply starts → JSONL counter-sink pattern unstable | HIGH | Coordinate with change #6 archive; change #7 PROPOSE waits for change #6 ARCHIVE |
| 2 | Migration of `STRICT_TDD_PROMPT` / `PROMPT_HEADER` / `PROMPT_FOOTER` / `EMPTY_PROMPT_TEXT` breaks existing tests that hardcode the prompt strings | MEDIUM | Run all 783 tests after migration; update test fixtures to use `render_prompt()` + golden snapshots; follow REQ-48 in v1.1 |
| 3 | The SKILL.md checksum drift detection (REQ-49) produces false positives on whitespace-only changes | MEDIUM | Use frontmatter-only checksum (parse YAML, hash the dict, ignore body whitespace); see D.5 |
| 4 | Adding `prompts/` at repo root conflicts with future external tooling that expects `src/flow_engineering/prompts/` | LOW | Document the path in `openspec/specs/prompt-registry/spec.md`; make it configurable via `pyproject.toml` |
| 5 | The Jinja2 autoescape decision (D.2) blocks legitimate `{{ var }}` substitution that contains characters like `<` or `&` | LOW | Use `select_autoescape(default_for_string=True)` which auto-escapes string variables; test with BDD scenario REQ-46 S2 |
| 6 | `flow prompts check` exit code (non-zero on drift) breaks existing CI pipelines that run `flow apply` automatically | LOW | Default is non-zero on drift; add `--no-fail` flag for CI compatibility |
| 7 | BDD step def file growth (decision-code-linking S3 precedent: 5-6× forecast) likely applies | LOW | Forecast ×6 multiplier baked in (~18 710 realistic) |
| 8 | The OpenCode SKILL.md files at `~/.config/opencode/` are user-managed (not in repo); if the user has manually edited them, drift detection fires unexpectedly | LOW | Document the expected state in `openspec/specs/prompt-registry/spec.md`; provide `flow prompts check --init` to bootstrap the catalog |
| 9 | The `prompts/` directory at repo root conflicts with the `~/.flow-engineering/prompts/` user config directory (parallel naming) | LOW | Rename repo-side to `src/flow_engineering/prompt_templates/` or accept the parallel; document in spec |
| 10 | Adding the Jinja2 env shared between `scaffold.py` and `prompt_render.py` creates an import cycle | LOW | Refactor `_env()` to a private function in `scaffold.py`; `prompt_render.py` imports it |

---

## G. Recommendation Summary

**For the orchestrator**:

1. **Scope**: 5 P0/P1 REQs (REQ-45, REQ-46, REQ-47, REQ-49, REQ-50). Defer 5 P2 REQs to v1.1.
2. **Forecast**: ~3 243 LOC total; ~18 710 LOC realistic ×6 TDD multiplier.
3. **PR split**: 2 chained PRs (PR#1: registry+render+lint; PR#2: CLI+SKILL.md mirror).
4. **Coordination**: Wait for change #6 (observability) to ARCHIVE before starting change #7 apply.
5. **Next recommended phase**: `sdd-propose prompt-registry` (5 REQs + approach matrix).
6. **Side benefit**: Change #7 formalizes the SKILL.md catalog so future `flow` changes can replace the 6-file hand-edit pattern (graph-snapshots archive precedent) with a manifest-driven approach.

**Key dependencies resolved**:

- ✓ Change #1 (decision-code-linking) — 4 inline prompts identified for migration
- ✓ Change #5 (graph-snapshots) — 6-SKILL.md hand-edit precedent formalized
- ⏳ Change #6 (observability) — JSONL counter-sink catalog pattern must be stable before change #7 apply
- ❌ Change #4 (cross-project-federation) — no prompt-registry dependency

---

## H. Structured Metadata

- **total_gaps_identified:** 10 (5 P0/P1, 5 P2)
- **recommended_reqs:** 5 (REQ-45, REQ-46, REQ-47, REQ-49, REQ-50)
- **deferred_reqs:** 5 (REQ-48, REQ-51, REQ-52, REQ-53, REQ-54)
- **forecast_loc_production:** ~833
- **forecast_loc_test:** ~2 260
- **forecast_loc_runtime_skill:** ~150
- **forecast_loc_grand_total:** ~3 243
- **forecast_loc_realistic_x6:** ~18 710
- **pr_split:** 2 chained PRs (PR#1: registry+render+lint; PR#2: CLI+SKILL.md mirror)
- **bdd_feature_files_new:** 5
- **bdd_scenarios_new:** 14
- **inline_prompt_constants_today:** 4 (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`)
- **jinja2_templates_today:** 4 (`change.yaml.j2`, `exploration.md.j2`, `README.md.j2`, `flow-version.j2`)
- **opencode_skill_files_today:** 10 (`~/.config/opencode/skills/sdd-*/SKILL.md`)
- **opencode_prompt_files_today:** 10 (`~/.config/opencode/prompts/sdd/*.md`)
- **new_modules_after_change_7:** 4 (`prompt_registry.py`, `prompt_render.py`, `prompt_lint.py`, `opencode_skill_catalog.py`)
- **topic_key:** `sdd/prompt-registry/explore`
- **type:** architecture
- **scope:** project
- **capture_prompt:** false (automated artifact)
- **next_recommended:** `sdd-propose prompt-registry` (5 REQs + approach matrix)

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_strict_tdd_prompt",
      "label": "STRICT_TDD_PROMPT constant (single inline prompt string with {test_command} placeholder)",
      "file": "src/flow_engineering/strict_tdd.py",
      "line": 13,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_auto_suggest_prompts",
      "label": "EMPTY_PROMPT_TEXT + PROMPT_HEADER + PROMPT_FOOTER constants (3 inline prompts for TTY interactive confirmation)",
      "file": "src/flow_engineering/auto_suggest_code_refs.py",
      "line": 47,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_prompt_fn",
      "label": "prompt_fn Callable injection point in save_phase (testable seam for REQ-6 auto-suggest)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 541,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_scaffold_jinja_env",
      "label": "scaffold.py _env() Jinja2 Environment (single shared instance, scoped to scaffold module only)",
      "file": "src/flow_engineering/scaffold.py",
      "line": 20,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_templates_directory",
      "label": "templates/ directory (4 Jinja2 .j2 files for new-change and new-project scaffolding)",
      "file": "src/flow_engineering/templates",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_init",
      "label": "~/.config/opencode/skills/sdd-init/SKILL.md (agent prompt v3.0; not in repo)",
      "file": "C:\\Users\\insyd\\.config\\opencode\\skills\\sdd-init\\SKILL.md",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_explore",
      "label": "~/.config/opencode/skills/sdd-explore/SKILL.md (agent prompt v2.0; not in repo)",
      "file": "C:\\Users\\insyd\\.config\\opencode\\skills\\sdd-explore\\SKILL.md",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_apply",
      "label": "~/.config/opencode/skills/sdd-apply/SKILL.md (agent prompt v3.0; drives flow apply)",
      "file": "C:\\Users\\insyd\\.config\\opencode\\skills\\sdd-apply\\SKILL.md",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_prompts_sdd_directory",
      "label": "~/.config/opencode/prompts/sdd/*.md (10 parallel prompt files mirroring skills/)",
      "file": "C:\\Users\\insyd\\.config\\opencode\\prompts\\sdd",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_apply_verify_archive",
      "label": "CLI commands that delegate to sdd-* sub-agents (apply, verify, archive — driven by SKILL.md runtime)",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_strict_tdd",
      "label": "tests/unit/test_strict_tdd.py (119 LOC; 8 tests; covers STRICT_TDD_PROMPT rendering only)",
      "file": "tests/unit/test_strict_tdd.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_auto_suggest",
      "label": "tests/unit/test_auto_suggest.py (~325 LOC; covers PROMPT_HEADER/FOOTER/EMPTY_PROMPT_TEXT format_suggestion_prompt)",
      "file": "tests/unit/test_auto_suggest.py",
      "line": 1,
      "confidence": 0.90,
      "source": "manual"
    }
  ]
}
