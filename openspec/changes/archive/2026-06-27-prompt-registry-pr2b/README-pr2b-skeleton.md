<!-- README.md: prompt-registry PR#2b active scope skeleton. Created 2026-06-27 by sdd-archive PR#2a closeout. -->
# prompt-registry — PR#2b active scope skeleton

**Status**: PR#1 archived 2026-06-27 (see `openspec/changes/archive/2026-06-27-prompt-registry-pr1/archive-report.md`). PR#2a archived 2026-06-27 (see `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/archive-report.md`). This folder is reserved for **PR#2b** planning artifacts.

## PR#1 (archived)

REQ-45 + REQ-46 + REQ-47 — foundation surface (catalog + render + lint). The full PR#1 proposal/spec/design/tasks/explore/verify-report + apply-progress are now under:

```
openspec/changes/archive/2026-06-27-prompt-registry-pr1/
├── proposal.md
├── spec.md
├── design.md
├── tasks.md
├── explore.md
├── verify-report-pr1.md
├── apply-progress/
│   ├── pr1-batch-a.md
│   ├── pr1-batch-b.md
│   ├── pr1-batch-c.md
│   └── pr1-merged.md
└── archive-report.md
```

## PR#2a (archived)

REQ-49 — `SKILL_CATALOG` mirror catalog (20 entries) + SHA-256 frontmatter drift detection + sidecar JSON I/O + `flow prompts {check, lint}` Click subcommands (4-flag matrix: `--init`/`--update`/`--no-fail`/`--skill`). Full PR#2a tasks/verify-report/apply-progress + archive-report are under:

```
openspec/changes/archive/2026-06-27-prompt-registry-pr2a/
├── tasks-pr2.md              # full PR#2 task list (T1.1..T3.12)
├── verify-report-pr2a.md     # PR#2a closeout + T2.5 re-verify
├── apply-progress-pr2a.md    # 4 sub-batches A1/A2/A3/B1 + T2.5 follow-up
└── archive-report.md         # this archive's audit trail
```

**T2.5 follow-up fixes** (between initial PR#2a apply at HEAD `83e55b9` and archive at HEAD `0dea408`) resolved 3 verify findings end-to-end on the real OpenCode SKILL.md corpus:
- **C1** — `parse_frontmatter` nested `metadata.version` fallback (`_extract_version` helper)
- **W1** — `flow prompts check` 4-flag matrix complete (added `--update`/`--no-fail`/`--skill` + `--init` + `_resolve_check_action` helper + `CheckAction` dataclass)
- **W2** — `flow prompts check` stderr WARN summary when drift detected + 4 observability counters via `observability.increment()` / `observability.observe()`

Test baseline: 1125 (pre-PR#2a) → 1187 (post-PR#2a) → **1199** (post-T2.5 follow-up) — all passing, ruff clean, mypy clean on `opencode_skill_catalog.py`.

The canonical capability spec lives at `openspec/specs/prompt-registry/spec.md` and now carries the PR#1 archive status header + PR#2a archive status header + the post-archive scope table.

## PR#2b (active — REQ-50 + 8 W-fix carry-forwards)

**Decision** (cached at engram `sdd/prompt-registry/pr2-chain-decision`): PR#2 forecast 1560 LOC exceeded 400-line review budget → chained PRs. Chain strategy: **stacked-to-main** (per proposal #201 precedent + C4 auto-forecast). PR#2a merged first (REQ-49); PR#2b stacks on top.

### Scope

- REQ-50 — `flow prompts list --json` + `flow prompts show <id> --var key=value` (repeatable) with sentinel substitution + exit 5 on unknown id (sdd-tasks T3.1 + T3.2)
- 8 W-fix carry-forwards from PR#1 verify-report (bundled into PR#2b batch C):
  - **W1** — `lint_prompts` spec-taxonomy alias map (`LINT_CATEGORY_SPEC_ALIASES` in `prompt_registry.py`)
  - **W2** — `select_autoescape(default_for_string=True)` for `_safe_jinja_env()` (HTML escape blocks Jinja2 `{{ var }}` injection)
  - **W3** — restore `prompts/` directory + 4 `.j2` files at repo root (per D1/D2)
  - **W4** — hoist `scaffold._env()` to shared `prompt_render._env()` (per D3)
  - **W7** — `[tool.flow_engineering.prompts] directory = "prompts"` in `pyproject.toml`
  - **W8** — bump `pyproject.toml` version to `0.8.0` (CHANGELOG already claims `0.8.0`)
  - **W9** — `uv run ruff check --fix` on changed files (3 of 5 auto-fixable)
  - **W10** — strengthen BDD scenarios for REQ-45 S1/S2 to match spec Gherkin shape
- Capability spec sync (T3.11) — add REQ-50 sections to `openspec/specs/prompt-registry/spec.md`; document W-fix resolutions
- CHANGELOG + closeout (T3.12) — `## [0.8.0] - 2026-06-27` entry + 3 BDD scenarios for REQ-50 + closeout tests
- Forecast: ~720 LOC, ~36 work-unit commits (per `tasks-pr2.md:54-55` PR#2b batch table)
- Files: `src/flow_engineering/cli.py` (MODIFY — `flow prompts list` + `flow prompts show <id>`), `src/flow_engineering/prompt_registry.py` (MODIFY — `LINT_CATEGORY_SPEC_ALIASES` + autoescape), `src/flow_engineering/prompt_render.py` (MODIFY — `_env()` factory with `select_autoescape`), `src/flow_engineering/scaffold.py` (REFACTOR — replace local `_env()` with re-export), `prompts/strict_tdd.j2` + `prompts/auto_suggest_{header,footer,empty}.j2` (NEW), `pyproject.toml` (MODIFY — `[tool.flow_engineering.prompts]` section + version bump), `tests/bdd/req45_prompt_registry.feature` (MODIFY — strengthen S1/S2 per W10), `openspec/specs/prompt-registry/spec.md` (MODIFY — add REQ-50 sections + W-fix resolution notes)

### Already-RESOLVED at commit `613f716` (PR#1 verify, verify only, no work needed in PR#2b)
- **W5** — re-test the 4 migrated entries via `render_prompt(name, **kwargs)` (25 tests passing)
- **W6** — `PromptRenderError` exception class (implemented + tested)

### Already-RESOLVED in PR#2a (commit `0dea408` post-T2.5 fixes)
- **T2.2 W1** — `flow prompts check` 4-flag matrix (`--init` + `--update` + `--no-fail` + `--skill`)
- **T2.4 W2** — `flow prompts check` stderr WARN + 4 observability counters
- **C1** — nested `metadata.version` fallback for the real OpenCode SKILL.md corpus

## Carry-forwards deferred to v1.1 (NOT PR#2b)

- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt` snapshots
- **REQ-51** — `prompt_renders.jsonl` append-only sink (`FLOW_PROMPT_LOG=1` gate)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (lands in `observability.py` per D10)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_REGISTRY` at build time
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` gate in `pyproject.toml`

## Out-of-scope reminders (deferred beyond PR#2b — v0.8.x schema migrations)

- `PromptDef` → `PromptEntry` schema migration (5 fields → 6 fields: add `template_id` + `location` + `schema_version` as separate fields)
- `PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict` shape migration

The `LINT_CATEGORY_SPEC_ALIASES` mapping shim (W1 in PR#2b) covers the spec/impl taxonomy gap until the schema migration lands.

## Next recommended step

`sdd-apply prompt-registry PR#2b` (template cached at engram `sdd/prompt-registry/apply-prompt-template-pr2b`). Apply batches ready per `tasks-pr2.md:114-122` (B1: T3.1 + T3.2 REQ-50 CLI surface; B2: T3.3..T3.6 W1+W2+W3+W4 lint+autoescape+prompts+scaffold hoist; B3: T3.7..T3.9 W7+W8+W9 pyproject + ruff; B4: T3.10..T3.12 W10 BDD + spec sync + CHANGELOG closeout). When PR#2b completes:
1. `sdd-verify prompt-registry PR#2b` (verify 12 tasks + REQ-50 acceptance criteria)
2. `sdd-archive prompt-registry PR#2b` (move to `archive/2026-06-27-prompt-registry-pr2b/`)
3. `git push` to origin
4. `sdd-explore v1.1 prompt-registry` (REQs 48/51..54 + v0.8.x schema migrations + a possible `prompt-registry v1.1` change)

## Reference

- PR#2b tasks: `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/tasks-pr2.md` (T3.x breakdown)
- PR#2a verify-report: `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/verify-report-pr2a.md`
- PR#2a archive-report: `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/archive-report.md`
- PR#2a apply-progress: `openspec/changes/archive/2026-06-27-prompt-registry-pr2a/apply-progress-pr2a.md`
- PR#1 archive: `openspec/changes/archive/2026-06-27-prompt-registry-pr1/`
- Capability spec: `openspec/specs/prompt-registry/spec.md` (PR#1 + PR#2a archive status headers + post-archive scope table)
- PR#2 chain decision: engram topic_key `sdd/prompt-registry/pr2-chain-decision`
- PR#2b apply prompt template (cached): engram topic_key `sdd/prompt-registry/apply-prompt-template-pr2b`
