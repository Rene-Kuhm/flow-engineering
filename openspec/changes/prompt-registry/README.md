<!-- README.md: prompt-registry PR#2 active scope skeleton. Created 2026-06-27 by sdd-archive PR#1 closeout. -->
# prompt-registry — PR#2 active scope skeleton

**Status**: PR#1 archived 2026-06-27 (see `openspec/changes/archive/2026-06-27-prompt-registry-pr1/archive-report.md`). This folder is reserved for **PR#2** planning artifacts.

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

The canonical capability spec lives at `openspec/specs/prompt-registry/spec.md` and now carries the PR#1 archive status header + scope table.

## PR#2 (active — to launch)

**REQ-49** — `SKILL_CATALOG` mirror catalog + checksum drift detection:
- `src/flow_engineering/opencode_skill_catalog.py` (NEW) — `SKILL_CATALOG: dict[str, SkillEntry]`, `SkillEntry` dataclass, SHA-256 frontmatter checksums, `check_drift()` helper
- Sidecar JSON at `~/.flow-engineering/prompt_checksums.json` (lazy bootstrap via `flow prompts check --init`)

**REQ-50** — `flow prompts {list,show,lint,check}` CLI subcommand group:
- `src/flow_engineering/cli.py` (MODIFY) — 4 subcommands, ~150 prod LOC delta, mirrors `flow metrics` surface pattern
- 7 flags total: `--json`, `--var`, `--strict`, `--update`, `--no-fail`, `--init`, `--skill`

**Carry-forwards resolved by PR#2** (from PR#1 verify-report W1..W10):
- W1 — `lint_prompts` spec-taxonomy alias map (or rename to spec taxonomy)
- W2 — `select_autoescape(default_for_string=True)` for `_safe_jinja_env()`
- W3 — restore `prompts/` directory + 4 `.j2` files at repo root (per D1/D2)
- W4 — hoist `scaffold._env()` to shared `prompt_render._env()`
- W5 — re-test the 4 migrated entries via `render_prompt(name, **kwargs)` end-to-end (already RESOLVED at `613f716`; verify)
- W6 — `PromptRenderError` exception class (already RESOLVED at `613f716`; verify)
- W7 — `[tool.flow_engineering.prompts] directory = "prompts"` in `pyproject.toml`
- W8 — bump `pyproject.toml` version to `0.8.0` (CHANGELOG already claims `0.8.0`)
- W9 — `uv run ruff check --fix` on changed files (3 of 5 auto-fixable)
- W10 — strengthen BDD scenarios for REQ-45 S1/S2 to match spec Gherkin shape

## Carry-forwards deferred to v0.8.x (NOT PR#2)

- `PromptDef` → `PromptEntry` schema migration (5 fields → 6 fields: add `template_id` + `location` + `schema_version` as separate fields)
- `PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict` shape migration

## Out-of-scope reminders (deferred beyond PR#2)

- **REQ-48** — golden regression tests via `pytest` snapshots (defer to v1.1)
- **REQ-51** — `prompt_renders.jsonl` append-only sink (defer to v1.1)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (defer to v1.1)
- **REQ-53** — `docs/prompts.md` generated from `PROMPT_REGISTRY` at build time (defer to v1.1)
- **REQ-54** — `min_sdd_skill_versions` gate in `pyproject.toml` (defer to v1.1 or bundle into PR#2)

## Next recommended step

`sdd-tasks prompt-registry PR#2` — break REQ-49 + REQ-50 + the W-fix carry-forwards (W1/W2/W3/W4/W6/W7/W8/W9/W10) into implementation tasks. Use the existing PR#1 proposal REQ-49/50 section as the input.

## Reference

- PR#1 archive: `openspec/changes/archive/2026-06-27-prompt-registry-pr1/`
- PR#1 capability spec: `openspec/specs/prompt-registry/spec.md` (with PR#1 archive status header)
- PR#1 verify-report: `openspec/changes/archive/2026-06-27-prompt-registry-pr1/verify-report-pr1.md`
- PR#1 archive-report: `openspec/changes/archive/2026-06-27-prompt-registry-pr1/archive-report.md`
- Precedent pattern: `openspec/changes/archive/2026-06-27-observability-pr2/` (PR#2-only archive pattern; same change-name root folder deleted after PR#1 archive)
</content>