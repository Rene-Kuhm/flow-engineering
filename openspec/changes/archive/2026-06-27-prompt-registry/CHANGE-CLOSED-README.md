<!-- README.md: prompt-registry final closure README. CHANGE #7 FULLY CLOSED 2026-06-28. -->
# prompt-registry — change #7 FULLY CLOSED

**Status**: **ARCHIVED — CHANGE #7 (`prompt-registry`) FULLY CLOSED** as of 2026-06-28 PR#2b archive.

All 3 PRs of the `prompt-registry` change have shipped and been archived:

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

openspec/changes/archive/2026-06-27-prompt-registry-pr2a/
├── tasks-pr2.md              # full PR#2 task list (T1.1..T3.12)
├── verify-report-pr2a.md     # PR#2a closeout + T2.5 re-verify
├── apply-progress-pr2a.md    # 4 sub-batches A1/A2/A3/B1 + T2.5 follow-up
└── archive-report.md

openspec/changes/archive/2026-06-27-prompt-registry-pr2b/
├── apply-progress-pr2b.md    # 3 sub-batches B1/B2/B3 closeout
├── verify-report-pr2b.md     # PR#2b closeout (PASS WITH WARNINGS)
├── README-pr2b-skeleton.md   # the PR#2b-only skeleton that lived here pre-archive
└── archive-report.md         # this archive's audit trail
```

## What shipped (cumulative across the 3 PRs)

| PR | REQs | W-fixes resolved | Test count | HEAD at archive |
|----|------|------------------|------------|-----------------|
| **PR#1** (2026-06-27) | REQ-45 (PromptRegistry catalog) + REQ-46 (render_prompt helpers) + REQ-47 (lint_prompts validator) | (deferred 10 W-fixes to PR#2b) | 1125 baseline | `4bbcc21` |
| **PR#2a** (2026-06-27) | REQ-49 (SKILL_CATALOG mirror + SHA-256 drift detection + `flow prompts {check, lint}` CLI) | T2.5 follow-up: C1 (nested `metadata.version` fallback) + W1 (4-flag matrix) + W2 (stderr WARN + 4 observability counters) | 1125 → 1199 (+74) | `0dea408` |
| **PR#2b** (2026-06-28) | REQ-50 (`flow prompts list --json` + `flow prompts show <id>` with sentinel substitution + exit 5) | W1 (lint taxonomy alias map) + W2 (`select_autoescape`) + W3 (prompts/ directory + 4 .j2 files) + W4 (`scaffold._env()` hoist) + W7 (`[tool.flow_engineering.prompts]` section) + W8 (pyproject.toml version 0.8.1) + W9 (ruff --fix on changed files) + W10 (REQ-45 S1 BDD strengthen) | 1199 → 1232 (+33) | `50c3b64` |

**Final capability spec**: `openspec/specs/prompt-registry/spec.md` reflects the FULL post-archive state with explicit `## PR#{N} archive status (DATE)` sections for all 3 PRs + a unified `## PR#1 + PR#2a + PR#2b Scope (post-archive 2026-06-28)` table + Versioning v1.0 → v1.1 → v1.2 history.

## Verify verdict at PR#2b archive

**`PASS WITH WARNINGS`** — 0 CRITICAL, 4 WARNING, 6 SUGGESTION. All 4 WARNING findings accepted as future follow-ups per drift-hardening precedent (PR#2b's 4 WARNING + 6 SUGGESTION is the smallest carry-forward footprint of any change in this repo). Optional T3.13 follow-up (~25 LOC + 3 doc touch-ups, ~30 min) documented in `verify-report-pr2b.md` §"Pre-archive fixes" if user wants fully clean lint surface before push.

## Carry-forwards (after PR#2b archive)

### Deferred to `v0.9.0-hardening` (next change — already exploring)

- Removal of v0.8.0 1-release compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`) per CHANGELOG v0.8.0 lines 43/44/46/74 ("removed in v0.9.0")
- `pyproject.toml` bump 0.8.1 → 0.9.0

### Deferred to v1.1 (post-`v0.9.0-hardening`)

- **REQ-48** — golden regression tests via `tests/golden/prompts/<prompt_id>.txt` snapshots
- **REQ-51** — `prompt_renders.jsonl` append-only sink (`FLOW_PROMPT_LOG=1` gate)
- **REQ-52** — `prompts_render_total{...}` / `prompts_render_ms` / `prompts_render_failed_total{...}` counters (lands in `observability.py` per D10)
- **REQ-53** — generated `docs/prompts.md` from `PROMPT_REGISTRY` at build time
- **REQ-54** — `min_sdd_skill_versions: dict[str, str]` gate in `pyproject.toml`

### Deferred to v0.8.x schema migrations (independent of PR#2 chain)

- `PromptDef` → `PromptEntry` (5 fields → 6 fields: add `template_id` + `location` + `schema_version` as separate fields)
- `PROMPT_NAMES: tuple` → `PROMPT_REGISTRY: dict` shape migration
- `PromptDomain(str, Enum)` → `PromptDomain(StrEnum)` UP042 ruff finding (requires `--unsafe-fixes`)
- The `LINT_CATEGORY_SPEC_ALIASES` mapping shim (W1 of PR#2b) covers the spec/impl taxonomy gap until the schema migration lands

### Optional T3.13 follow-up (NOT blocking; accepted per drift-hardening precedent)

If the user wants a fully clean lint surface before push to origin (~30 min, ~25 LOC):

- **W-A3** (~10 LOC) — Add `from typing import Any` to `tests/unit/test_cli_prompts.py:18-27` (fixes F821 × 3); apply `ruff --fix` (fixes UP037); split `test_cli_prompts.py:507` assertion into 2 lines (PT018).
- **W-A1** (~6 LOC) — Add `variables: list[str]` to `_serialize_prompts_list` at `cli.py:2820-2827`; add 1 unit test assertion.
- **W-A4** (doc-only) — Update `CHANGELOG.md:16` + `apply-progress-pr2b.md:146,212` + `spec.md:48` to say `prompt_registry._env()` instead of `prompt_render._env()`.

If declined (default), the 3 fixes remain as carry-forwards into v0.8.x.

## Next steps (post-change #7 closure)

1. **Orchestrator pushes to origin**: `git push origin main` — closes change #7 entirely.
2. **`sdd-explore v0.9.0-hardening`** (already explored per `openspec/changes/v0.9.0-hardening/explore.md`) — ready for the next `sdd-propose` + `sdd-design` + `sdd-spec` + `sdd-tasks` cycle when the orchestrator decides to schedule it.
3. **v1.1 cluster** (post-`v0.9.0-hardening`) — REQ-48/51..54 + federated prompts + i18n + A/B testing; separate change when ready.

## Reference

- **Capability spec**: `openspec/specs/prompt-registry/spec.md` (the canonical source of truth for prompt-registry behavior)
- **CHANGELOG**: `CHANGELOG.md` — `## [0.8.1] - 2026-06-28` entry documents REQ-50 + 8 W-fixes
- **pyproject.toml**: `version = "0.8.1"` (was `0.8.0` at PR#2a archive)
- **Engram chain decisions**: `sdd/prompt-registry/pr2-chain-decision` (chained PR strategy) + `sdd/prompt-registry/apply-progress-pr2b` (PR#2b apply-progress checkpoint) + `sdd/prompt-registry/archive-report-pr2b` (this archive's audit trail)

**Topic**: sdd/prompt-registry/change-closure-readme