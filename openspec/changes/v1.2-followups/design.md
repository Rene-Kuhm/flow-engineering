<!-- design.md: v1.2-followups. Source: sdd-design sub-agent (2026-06-28). Mirror v1.1-followups design.md. -->
# Design: v1.2-followups

> Mirror of Engram `sdd/v1.2-followups/design` (topic_key upsert). Format mirrors [`openspec/changes/archive/2026-06-28-v1.1-followups/design.md`](../archive/2026-06-28-v1.1-followups/design.md). All 4 open questions pre-resolved by orchestrator.

```yaml
status: success
confidence: high
open_questions_resolved: 4/4
architecture_decisions: 4  # D1..D4
chain_strategy: stacked-to-main
pr_split: 4 chained PRs  # PR#2a (REQ-44) + PR#2b (REQ-48) + PR#2c (REQ-54) + PR#2d (Path A + bump)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.2-followups\design.md
next_recommended: sdd-tasks v1.2-followups
strict_tdd: true
```

## Status

**designed → ready for `sdd-tasks v1.2-followups`**. 4 carry-forwards from `decision-drift/spec.md:410` (REQ-44 + REQ-48 + REQ-54 + Path A) → 4 decisions, one per chained PR. ~790 LOC exceeds 400-line threshold → chained PRs mandatory.

---

## Architecture Decisions

### D1 (PR#2a): metrics.jsonl rotation — mirror of DriftEventLog

Copy `_rotate_if_needed(path)` + env-var resolvers from `drift_event_log.py:196-254` into `observability.py:171-189`. Env vars `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days). Rotation at top of `increment()` BEFORE existing `try/except OSError` (slow FS cannot poison sink path resolution). Best-effort `try/except OSError` on rename + sibling unlink.

| Option | Decision |
|---|---|
| Mirror DriftEventLog verbatim | **CHOSEN** |
| Per-counter rotation policy | Rejected |
| External logrotate | Rejected |
| Tail-only truncation | Rejected |

### D2 (PR#2b): golden regression snapshots per PROMPT_NAMES

`tests/golden/prompts/{strict_tdd,auto_suggest_header,auto_suggest_footer,auto_suggest_empty}.txt` — one snapshot per `PROMPT_NAMES` entry at `prompt_registry.py:179-224`. NEW `render_prompt_canonical(prompt_id, **vars)` helper injects canonical defaults (`test_command="pytest"` for `strict_tdd`; `{}` for others). `TestGoldenRegression` asserts byte-match. NEW `--update-goldens` Click option on `flow prompts show <id>` regenerates; default mode fails on drift.

| Option | Decision |
|---|---|
| On-disk snapshots + `--update-goldens` flag | **CHOSEN** |
| Inline string assertions | Rejected |
| `pytest-snapshot` plugin | Rejected |
| Auto-update on mismatch | Rejected |

### D3 (PR#2c): `[tool.flow_engineering] min_sdd_skill_versions` enforcement

NEW pyproject section: `min_sdd_skill_versions = {"sdd-explore": "3.0", ..., "sdd-archive": "3.0"}` (8 entries). NEW `enforce_min_skill_versions(min_versions: dict[str, str])` helper at `opencode_skill_catalog.py:117` reuses existing `SkillVersionError` — parses on-disk `SKILL.md`, compares `(MAJOR, MINOR)` tuple, raises with remediation message. 3-line CLI hook at `flow apply` / `flow verify` / `flow archive` startup → exit 4.

| Option | Decision |
|---|---|
| pyproject section + helper + 3-line CLI hook | **CHOSEN** |
| Hardcoded version pins | Rejected |
| Per-skill CLI flag | Rejected |
| CI-only enforcement | Rejected |

### D4 (PR#2d): Path A rename + 1-release `deprecated=True` alias

Convert `@main.command("drift", ...)` at `cli.py:1718` → `@main.group("drift")` + `@drift_group.command("run", ...)` (default via `invoke_without_command=True`). Add `@main.group(name="drift-events", deprecated=True)` at `cli.py:1821` — emits `DeprecationWarning` + delegates to new `flow drift events {list,tail,stats}` subcommands. Alias REMOVED in v1.3 (mirrors `SnapshotGraphMissing` v1.1 precedent). CHANGELOG v1.2.0 BREAKING entry + pyproject `1.1.0` → `1.2.0` bump.

| Option | Decision |
|---|---|
| Path A + 1-release Click `deprecated=True` alias | **CHOSEN** |
| Path B (status quo) | Rejected |
| 2-release alias | Rejected |
| No alias (immediate BREAKING) | Rejected |

---

## Architecture Sketches

**D1** — `_rotate_metrics_if_needed(_resolve_path())` at top of `increment()` OUTSIDE `try/except OSError`. Helper byte-identical to `drift_event_log.py:220-254` with metric prefix + env-var names.

**D2** — snapshots (UTF-8, trailing newline). `TestGoldenRegression.test_<prompt>_matches_snapshot` calls `render_prompt_canonical(<prompt>, **canonical_vars)` + asserts byte-identical. `TestGoldenUpdate` invokes `--update-goldens` + asserts rewrite.

**D3** — `[tool.flow_engineering] min_sdd_skill_versions = {...}`. On `SkillVersionError`: emit stderr JSON `{error, skill, expected, found, hint}` + `sys.exit(4)`.

**D4** — `@main.group(name="drift-events", deprecated=True)` auto-emits `DeprecationWarning`; handler re-emits with `stacklevel=2` + delegates via `ctx.forward(new_drift_events_list)`.

---

## Open Questions

0 open. All 4 pre-empted design-phase questions resolved per orchestrator brief + explore.md + proposal.md §"Open Questions".

---

## Risks

| # | Risk | Like | Mitigation |
|---|---|---|---|
| 1 | Path A BREAKING surprises operators with shell aliases pointing at `flow drift-events` after alias removal in v1.3 | **MED** | CHANGELOG BREAKING callout + 1-release `deprecated=True` alias + Click migration hint. Bounded to one release cycle. |
| 2 | Single-PR bundles 4 items (~790 LOC) — exceeds 400-line threshold by ~2× | **MED** | **Chained PRs MANDATORY** — 4 PRs (`stacked-to-main`), each ≤ ~250 LOC. PR#2d last. |
| 3 | Rotation under lock on slow network FS | LOW | Rotation OUTSIDE existing `try/except OSError`; helper uses own `try/except OSError`. |
| 4 | Golden snapshot drift on unintentional template edits | LOW | `--update-goldens` is explicit opt-in; CI failure is desired signal. |
| 5 | `min_sdd_skill_versions` false positive on non-numeric version | LOW | `_extract_version()` returns `"0.0"` fallback (precedent at `opencode_skill_catalog.py:536`); fails gate correctly. |

---

## code_refs

21 manual code_refs nodes (D1..D4) bound to files at specific line numbers, with confidence 0.85-0.95. Sources all `manual` (D1..D4 author-verified against live code per explore.md).

- **PR#2a (D1)**: `src/flow_engineering/observability.py:171-189` (rotation helpers, mod) + `drift_event_log.py:196-254` (reference pattern) + `tests/unit/test_observability.py` NEW `TestMetricsRotation` + `tests/bdd/req44_metrics_rotation.feature` NEW.
- **PR#2b (D2)**: `src/flow_engineering/prompt_registry.py` NEW `render_prompt_canonical` helper + `tests/golden/prompts/*.txt` (4 NEW snapshots) + `tests/unit/test_prompt_render.py` NEW `TestGoldenRegression`+`TestGoldenUpdate` + `tests/bdd/req48_golden_prompts.feature` NEW.
- **PR#2c (D3)**: `pyproject.toml` NEW `[tool.flow_engineering]` section + `opencode_skill_catalog.py:117` (existing `SkillVersionError`) + `cli.py` NEW 3-line startup hook at `flow apply`/`flow verify`/`flow archive` + `tests/unit/test_skill_version_gate.py` NEW `TestEnforceMinSkillVersions` + `tests/bdd/req54_skill_version_gate.feature` NEW.
- **PR#2d (D4)**: `cli.py:1718-1816` (group refactor) + `cli.py:1821-2162` (1-release `deprecated=True` Click group alias) + `CHANGELOG.md` NEW v1.2.0 BREAKING entry + `pyproject.toml` NEW `1.2.0` bump + `openspec/specs/decision-drift/spec.md` v1.2 archive status + `tests/unit/test_cli_drift.py` (rename tests) + `tests/unit/test_cli_drift_events.py` NEW alias tests.
- **Cross-cutting precedents**: `openspec/specs/prompt-registry/spec.md` (golden tests + skill version sync) + `decision-drift/spec.md` (v1.2 archive status) + `snapshot_manager.py:104-123` (PEP 562 alias pattern) + `snapshot_manager.py:81-101` (`SnapshotGraphMissingError` canonical) + `pyproject.toml:106-108` (`[tool.flow_engineering.prompts]` precedent) + `cli.py:1979` (exit-code-4 precedent) + `opencode_skill_catalog.py:536` (`_extract_version` safe fallback).

---

## Status

success — 4 decisions, 0 open questions, ready for sdd-tasks.