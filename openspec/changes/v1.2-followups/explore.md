<!-- explore.md: v1.2-followups. Source: sdd-explore sub-agent (2026-06-28). CHUNK 3 of the "total restante" cleanup. -->
# Explore: v1.2-followups

**Change:** `v1.2-followups` (NEW change — consolidates 4 carry-forwards from v1.1 per capability spec `decision-drift/spec.md:410`)
**Date:** 2026-06-28
**Mode:** Strict TDD (per `sdd-init/flow-engineering` cached context; loop mode ACTIVE)
**HEAD at exploration:** `75961ad` (post-tech-debt cleanup; 0 ruff findings; 1342/1342 tests passing)
**Branch:** `main` (working tree CLEAN per `git status --short`)
**Pre-discussion:** capability spec already lists the v1.2 plan verbatim at `openspec/specs/decision-drift/spec.md:410`; `v1.1-followups` archive `verify-report.md` carries the explicit "carry-forwards NOT touched" table that names REQ-44/48/54 + Path A rename; the previous explore phases (drift-hardening → prompt-registry-pr1 → observability-pr1) pre-discussed each item in their original capability specs.

---

## Status

**explored → ready for `sdd-propose v1.2-followups`**. All 4 carry-forward items investigated (REQ-44 `metrics.jsonl` rotation + REQ-48 golden regression tests + REQ-54 `min_sdd_skill_versions` enforcement + Path A subcommand rename). Exploration confirmed scope + dependencies + risks + the breaking change surface for Path A. No new investigation required before proposal.

---

## Goal

Land the 4 deferred items (REQ-44 + REQ-48 + REQ-54 + Path A) in a single small TDD change that closes the v1.1 carry-forward gap (per capability spec v1.2 entry) without re-opening any closed capability contract. The Path A rename is the only BREAKING surface; the other 3 items are additive on existing modules. This is the **FINAL chunk** of the "total restante" cleanup — after this change, only W2 backfill (already-archived planning artifacts) and the 17 ruff residuals remain.

---

## Investigation findings

### REQ-44 — `metrics.jsonl` rotation

**Current state (HEAD `75961ad`):**

- `src/flow_engineering/observability.py:171-189` — `increment()` function appends one JSONL line per counter to `metrics.jsonl`. Has NO rotation call. The `try/except OSError` swallow is intentional (best-effort sink).
- `src/flow_engineering/observability.py:80-84` — `DEFAULT_METRICS_DIR` + `DEFAULT_METRICS_FILE = "metrics.jsonl"` + `_DEFAULT_PATH = DEFAULT_METRICS_DIR / DEFAULT_METRICS_FILE`.
- `src/flow_engineering/observability.py:158-163` — `_resolve_path()` env-var resolution helper (`FLOW_METRICS_PATH` overrides default).
- `src/flow_engineering/drift_event_log.py:196-254` — the **reference implementation**: `_resolve_rotation_threshold_bytes()` + `_resolve_max_age_days()` + `_rotate_if_needed(path)`. Already running in production for the drift event log.
- `tests/unit/test_observability.py:116` — `TestIncrementPathResolvesViaEnv` (env override precedent).

**Operator-visible gap:**

- `~/.flow-engineering/metrics.jsonl` grows unbounded forever (counters never stop — every CLI invocation appends at minimum 1 line).
- No `FLOW_METRICS_LOG_MAX_BYTES` / `FLOW_METRICS_LOG_MAX_AGE_DAYS` env vars.
- DriftEventLog already has the same env vars + same default values (10 MB + 30 days).

**Carry-forward source**: `observability-pr1` verify-report + `decision-drift/spec.md:410` v1.2 entry ("Carry-forwards from v1.1: REQ-44 `metrics.jsonl` rotation").

**Implementation surface** (mirrors `DriftEventLog._rotate_if_needed` exactly):

| File | Δ LOC | Notes |
|---|---|---|
| `src/flow_engineering/observability.py` | ~40 | New module-level `_rotate_metrics_if_needed(path)` + `_resolve_metrics_rotation_threshold_bytes()` + `_resolve_metrics_max_age_days()` env-var helpers + constants `METRICS_ROTATE_BYTES_DEFAULT` (10 MB) + `METRICS_ROTATE_AGE_DAYS_DEFAULT` (30 days). Call `_rotate_metrics_if_needed(_resolve_path())` at the top of `increment()` BEFORE the write (outside the `try/except OSError` so a rotation failure cannot pollute the sink path resolution). |
| `tests/unit/test_observability.py` | ~150 | NEW `TestMetricsRotation` class mirroring `test_drift_event_log.py:428` `TestRotation` (5 tests: rotates-at-max-bytes, no-rotate-below-threshold, env-override, deletes-old-siblings, OSError-swallow on slow FS). |
| `tests/bdd/` | ~30 | NEW `req44_metrics_rotation.feature` with 1-2 BDD scenarios (golden rotation under size pressure + age-based cleanup). |

**Estimated total**: ~220 LOC (well within budget — no CLI surface change).

---

### REQ-48 — Golden regression tests for prompts

**Current state (HEAD `75961ad`):**

- `src/flow_engineering/prompt_registry.py:179-224` — `PROMPT_NAMES` catalog with **4 entries** (`strict_tdd` + `auto_suggest_header` + `auto_suggest_footer` + `auto_suggest_empty`).
- `src/flow_engineering/prompt_registry.py:759-912` — `render_prompt(name, **kwargs)` is the canonical render entry point. Falls back to `.format()` for templates without Jinja placeholders (REQ-46 W5).
- `src/flow_engineering/prompt_registry.py:188` — `strict_tdd` declares `(test_command,)` as its variables. Other 3 prompts declare empty variable tuples.
- `prompts/strict_tdd.j2` — single template file. Content: `STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. ...`
- `prompts/auto_suggest_{header,footer,empty}.j2` — header/footer/empty sentinels.
- `tests/unit/test_prompt_render.py` — 21 tests covering happy path + error paths (missing var, template error, unknown prompt, etc.). **NO golden snapshot coverage today.**
- `scripts/generate_prompts_doc.py` — the precedent for "snapshot from PROMPT_NAMES catalog" (REQ-V1.1.5 docs/prompts.md).

**Operator-visible gap:**

- Any unintentional change to a template body (whitespace, punctuation, escape char) passes the 21 unit tests because none of them assert exact output text.
- The `docs/prompts.md` auto-gen captures template bodies inline (REQ-V1.1.5) but no test enforces byte-identical match against the on-disk template.

**Carry-forward source**: `prompt-registry-pr1` spec REQ-48 (deferred to v1.2 per capability spec `decision-drift/spec.md:410`).

**Implementation surface**:

| File | Δ LOC | Notes |
|---|---|---|
| `tests/golden/prompts/strict_tdd.txt` | NEW snapshot | Result of `render_prompt("strict_tdd", test_command="pytest")` — canonical example output. |
| `tests/golden/prompts/auto_suggest_header.txt` | NEW snapshot | Empty-var render (header text only). |
| `tests/golden/prompts/auto_suggest_footer.txt` | NEW snapshot | Empty-var render. |
| `tests/golden/prompts/auto_suggest_empty.txt` | NEW snapshot | Empty-var render. |
| `tests/unit/test_prompt_render_golden.py` | ~150 | NEW file. `TestGoldenRegression` class with 4 tests (`test_strict_tdd_matches_snapshot`, etc.) + `TestGoldenUpdate` class with 2 tests (`--update-goldens` CLI flag regenerates snapshots; default mode fails on drift). |
| `src/flow_engineering/prompt_registry.py` | ~20 | NEW `render_prompt_canonical(prompt_id, **vars)` helper that injects canonical default values (`test_command="pytest"` for `strict_tdd`, `{}` for the others) so the golden tests don't depend on call-site kwargs. |
| `tests/bdd/` | ~40 | NEW `req48_golden_prompts.feature` with 2 BDD scenarios (golden match on first run, golden update via explicit flag). |

**Estimated total**: ~210 LOC + 4 NEW snapshot files. Snapshots are committed artifacts; future template changes require `--update-goldens` to regenerate.

---

### REQ-54 — `min_sdd_skill_versions` enforcement in pyproject.toml

**Current state (HEAD `75961ad`):**

- `pyproject.toml:106-108` — `[tool.flow_engineering.prompts]` table exists (single key `directory = "prompts"`). No `[tool.flow_engineering]` umbrella section today.
- `src/flow_engineering/opencode_skill_catalog.py:117` — `SkillVersionError(Exception)` class already exists (raised on parse errors). The exception hierarchy is ready to be reused for the version gate.
- `src/flow_engineering/opencode_skill_catalog.py:463-475` — existing error sites that raise `SkillVersionError` for parse failures (file-not-found, no-frontmatter, YAML parse failed, frontmatter-not-a-dict).
- `C:\Users\insyd\.config\opencode\skills\sdd-apply\SKILL.md:6` — SKILL.md frontmatter carries `version: "3.0"` (MAJOR.MINOR string). All 20 catalog entries in `opencode_skill_catalog.py` declare `expected_version="3.0"` (REQ-49 D2 baseline).
- `src/flow_engineering/cli.py` — `flow apply` / `flow verify` / `flow archive` (the SDD commands) currently have NO startup hook for skill version enforcement.

**Operator-visible gap:**

- An operator on an outdated OpenCode runtime (`sdd-apply` SKILL.md version `"2.5"` vs the codebase's `"3.0"` minimum) gets silent breakage — the orchestrator dispatches the sub-agent and the missing-version gate never fires.
- No declarative pin in `pyproject.toml` that says "this project requires these minimum skill versions".

**Carry-forward source**: `prompt-registry-pr2a` spec REQ-54 (deferred to v1.2 per capability spec `decision-drift/spec.md:410`).

**Implementation surface**:

| File | Δ LOC | Notes |
|---|---|---|
| `pyproject.toml` | ~10 | NEW `[tool.flow_engineering]` section: `min_sdd_skill_versions = {"sdd-explore": "3.0", "sdd-propose": "3.0", "sdd-spec": "3.0", "sdd-design": "3.0", "sdd-tasks": "3.0", "sdd-apply": "3.0", "sdd-verify": "3.0", "sdd-archive": "3.0"}`. Optional `flow-engineering >= 1.2` for forward compat. |
| `src/flow_engineering/opencode_skill_catalog.py` | ~50 | NEW `enforce_min_skill_versions(min_versions: dict[str, str])` helper. Parses each on-disk `SKILL.md`, extracts the `version` frontmatter field, compares as tuple `(MAJOR, MINOR)`, raises `SkillVersionError` with remediation message on violation (e.g., `"sdd-apply requires >= 3.0, found 2.5; run 'opencode skill install sdd-apply@latest'"`). |
| `src/flow_engineering/cli.py` | ~30 | Add `_enforce_min_skill_versions_or_exit()` call at the top of the `flow apply` / `flow verify` / `flow archive` Click commands (the 3 SDD entry points). |
| `tests/unit/test_opencode_skill_catalog.py` | ~120 | NEW `TestEnforceMinSkillVersions` class (~6 tests: passes-on-current-version, raises-on-downgrade, skips-missing-skill, skips-non-SDD-skill, parses-non-numeric-version-gracefully, exit-code-on-CLI). |
| `tests/bdd/` | ~30 | NEW `req54_skill_version_gate.feature` with 2 BDD scenarios (clean startup vs blocked startup). |

**Estimated total**: ~240 LOC (well within budget — no CLI surface change; only ADDITIVE startup gate).

---

### Path A — Subcommand group rename for `flow drift-events`

**Current state (HEAD `75961ad`):**

- `src/flow_engineering/cli.py:1718-1816` — `flow drift <change_name>` is a flat `@main.command()` with a positional `change_name` argument (REQ-10/11/14). Existing CLI surface: `flow drift <change> [--json] [--include-obsolete] [--write-back] [--since] [--graph-json] [--snapshot]`.
- `src/flow_engineering/cli.py:1821-2162` — `flow drift-events {list,tail,stats}` is a `@main.group(name="drift-events")` parallel command. Existing surface: `flow drift-events {list,tail,stats} [--since] [--until] [--change] [--event-class] [--limit] [--format] [--path] [--strict]`.
- `src/flow_engineering/cli.py:1825-1829` — the docstring on `drift_events_group` explicitly labels itself "Path B (parallel command — preserves the `flow drift <change>` surface)". This was the v1.0 design choice.

**The Path A vs Path B trade-off (the ONLY real ambiguity in this change)**:

| Approach | Command shape | Pros | Cons | Effort |
|---|---|---|---|---|
| **Path A** (BREAKING) | `flow drift events {list,tail,stats}` | Idiomatic with `flow metrics {summary,export,aggregate}` + `flow prompts {list,show,render}` group pattern; `flow drift` becomes a single group namespace (mirrors Click best practice + the project's `flow metrics` / `flow prompts` precedent). | BREAKING — operators with shell aliases / cron jobs / docs pointing at `flow drift-events list` get an immediate `No such command` error. Requires 1-release alias shim + CHANGELOG entry + migration hint. | ~30 prod LOC (rename + 1-release alias) + ~50 test LOC |
| **Path B** (status quo, non-breaking) | `flow drift-events {list,tail,stats}` | Zero operator friction; no migration needed. | Inconsistent with the `flow metrics` / `flow prompts` group pattern; the hyphenated name is an outlier. | 0 LOC (do nothing — keep what v1.0 shipped) |

**BREAKING nature explained**: Click dispatches `@main.group("drift")` + `@main.group("drift").command("events")` differently from `@main.command("drift")` with a positional arg. Converting `flow drift <change>` (positional arg) to `flow drift <subcommand>` (group with subcommands) is a hard CLI surface flip. The mitigation is the **same 1-release alias pattern** that v0.8.0→v0.9.0 used for `Finding.from_legacy` and v1.0→v1.1 used for `SnapshotGraphMissing`: keep `flow drift-events` working as a deprecated alias for one release, raise a stderr `DeprecationWarning`, document the migration in CHANGELOG v1.2.

**Carry-forward source**: `v0-followups` design → `v1.1-followups` design → capability spec `decision-drift/spec.md:410` ("Path A subcommand group rename for `flow drift-events` (BREAKING)").

**Implementation surface** (Path A):

| File | Δ LOC | Notes |
|---|---|---|
| `src/flow_engineering/cli.py` | ~30 | Convert `@main.command("drift", ...)` (line 1718) → `@main.group("drift")` + `@drift_group.command("run", ...)` (or keep `drift` as the default command via `invoke_without_command=True` + manual `ctx.invoked_subcommand` dispatch). Add `@main.group(name="drift-events", deprecated=True)` 1-release alias that emits `DeprecationWarning` and dispatches to the new `drift events` subcommands. |
| `tests/unit/test_cli_drift.py` + `test_cli_drift_events_*` | ~50 | NEW tests for the alias (4 tests: alias-still-works, alias-emits-warning, alias-dispatches-correctly, alias-removed-in-v1.3). Update existing `test_cli_drift.py` tests for the new group dispatch (most stay byte-identical; only the `--help` output changes). |
| `CHANGELOG.md` | ~10 | NEW `v1.2.0` entry documenting the BREAKING rename + 1-release alias + `flow drift-events {list,tail,stats}` migration hint. |

**Estimated total**: ~90 LOC. The 1-release alias minimizes operator pain; the migration cost is bounded to one release cycle.

---

## Dependency analysis

Per the exploration, the 4 items have a clean dependency graph (1 cross-dependency):

1. **REQ-44 (metrics rotation)** — INDEPENDENT (touches only `observability.py` + new test class)
2. **REQ-48 (golden tests)** — INDEPENDENT (NEW test file + snapshot artifacts + tiny helper in `prompt_registry.py`)
3. **REQ-54 (skill version gate)** — INDEPENDENT (pyproject section + helper in `opencode_skill_catalog.py` + 3-line CLI hook at `flow apply`/`verify`/`archive` startup)
4. **Path A (rename)** — INDEPENDENT of REQ-44/48/54 (touches only `cli.py` + alias tests + CHANGELOG)

Cross-dependencies: NONE. Each item can ship in any order or all together.

**Recommended ordering for a single-PR delivery** (per `work-unit-commits` skill):
- **Commit 1**: REQ-44 (metrics rotation) — RED → GREEN → REFACTOR on `test_observability.py` `TestMetricsRotation`
- **Commit 2**: REQ-48 (golden tests) — commit snapshots first (existing canonical output), then `TestGoldenRegression` tests
- **Commit 3**: REQ-54 (skill version gate) — pyproject section FIRST, then `enforce_min_skill_versions()`, then CLI hook
- **Commit 4**: Path A (rename + 1-release alias) — rename group first, then add `deprecated=True` alias shim, then update CHANGELOG
- **Commit 5**: pyproject `1.1.0`→`1.2.0` bump + capability spec sync

**Chained-PR risk** (per `sdd-phase-common.md` Section E):
- Estimated total LOC delta: ~220 (REQ-44) + ~210 (REQ-48) + ~240 (REQ-54) + ~90 (Path A) = **~760 LOC** prod+test.
- 760 LOC **exceeds the 400-line chained-PR threshold**.
- **Chained-PRs recommended: YES** — split per the 4 commit boundaries above; each PR is ≤ ~250 LOC and autonomously verifiable.
- Forecast (mandatory per Section E): `Decision needed before apply: No` (the 4 sub-PRs are mutually independent and trivially stackable); `Chained PRs recommended: Yes`; `400-line budget risk: High (if single PR) / Low (if chained)`.

---

## Open Questions table

Per the brief ("pre-discussed; 0 truly open per spec"), there are no genuinely open questions. The items below were pre-discussed in capability specs and prior explore phases; this table captures the **closed decision** for each.

| Question | Pre-discussed answer | Source |
|---|---|---|
| Should `metrics.jsonl` rotation mirror `drift_events.jsonl` exactly (same defaults)? | YES — same 10 MB + 30 days + best-effort `OSError` swallow + `try/except OSError` outside the rotation call (so a slow FS cannot poison the sink path resolution). | `drift_event_log.py:196-254` precedent + `decision-drift/spec.md:410` v1.2 entry |
| Should the golden snapshot live on disk (`tests/golden/prompts/*.txt`) or in-line in the test? | On disk — git-diffable, reviewable in PR, regenerable via `--update-goldens` flag. | `scripts/generate_prompts_doc.py` precedent + standard pytest-snapshot convention |
| Where should the `min_sdd_skill_versions` dict live? | `pyproject.toml` `[tool.flow_engineering]` section — single source of truth per project, version-controlled, discoverable. | pyproject `[tool.flow_engineering.prompts]` precedent + standard pyproject convention |
| Should the version gate exit code be the same as `flow` exit codes? | YES — exit 4 (data/contract error), reusing the existing `observability.EXIT_*` enum. | `cli.py:1979` precedent (`observability.EXIT_INVALID_VALUE`) + v1.1 `DriftEventLogLegacyFormatError` exit 4 precedent |
| **Should Path A ship in v1.2, or defer again to v1.3?** | **RECOMMEND Path A in v1.2** — the inconsistency with `flow metrics {summary,export,aggregate}` and `flow prompts {list,show,render}` is the only outstanding CLI surface outlier; the longer it ships as Path B, the more operator scripts/scripts depend on the hyphenated name. The 1-release alias shim bounds migration pain to one release. | `decision-drift/spec.md:410` ("if `flow drift` namespace grows further") + 1-release alias precedent (`Finding.from_legacy` v0.9.0, `SnapshotGraphMissing` v1.1) |

---

## Proposed approach

Per-item recommendation:

| Item | Approach | Confidence |
|---|---|---|
| **REQ-44 metrics rotation** | **Adopt** — direct copy of `drift_event_log.py:196-254` rotation pattern into `observability.py` with `FLOW_METRICS_LOG_MAX_BYTES` + `FLOW_METRICS_LOG_MAX_AGE_DAYS` env vars. Same defaults (10 MB + 30 days). Best-effort OSError swallow outside the rotation call. | HIGH (100% — mirror of shipped code) |
| **REQ-48 golden regression tests** | **Adopt** — `tests/golden/prompts/*.txt` snapshots + `TestGoldenRegression` class + `--update-goldens` flag. 4 snapshots (one per `PROMPT_NAMES` entry). | HIGH (95% — standard pytest-snapshot convention + `scripts/generate_prompts_doc.py` precedent) |
| **REQ-54 skill version gate** | **Adopt** — `[tool.flow_engineering] min_sdd_skill_versions` dict + `enforce_min_skill_versions()` helper + 3-line CLI hook at `flow apply`/`verify`/`archive` startup. Exit code 4 + `SkillVersionError` + remediation message. | HIGH (95% — `SkillVersionError` class already exists, just need to wire the gate) |
| **Path A rename** | **Adopt with 1-release alias shim** — convert `@main.command("drift")` → `@main.group("drift")` + `@drift_group.command("run")` (default command via `invoke_without_command=True`); keep `flow drift-events` working as a `deprecated=True` Click group that emits a `DeprecationWarning` and dispatches to the new `drift events` subcommands. CHANGELOG v1.2 entry documents the BREAKING nature + migration hint. | MEDIUM (80% — the breaking change is real, but the 1-release alias shim is a proven pattern; risk = operator surprise if they ignore the deprecation warning) |

---

## Proposed REQs

Following the v1.1 numbering convention (`REQ-V1.X.N`):

| REQ | Title | Touched files | LOC estimate |
|---|---|---|---|
| **REQ-V1.2.1** | `metrics.jsonl` rotation: `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) + best-effort `try/except OSError` swallow. Mirrors `DriftEventLog._rotate_if_needed` exactly. | `src/flow_engineering/observability.py`, `tests/unit/test_observability.py` | ~220 |
| **REQ-V1.2.2** | Golden regression tests for `render_prompt`: `tests/golden/prompts/*.txt` snapshots per `PROMPT_NAMES` entry (4 files) + `render_prompt_canonical(prompt_id, **vars)` helper + `TestGoldenRegression` + `--update-goldens` flag for explicit regeneration. BDD: `tests/bdd/req48_golden_prompts.feature` (2 scenarios). | `tests/golden/prompts/*.txt`, `src/flow_engineering/prompt_registry.py`, `tests/unit/test_prompt_render_golden.py`, `tests/bdd/req48_golden_prompts.feature` | ~210 + 4 snapshot files |
| **REQ-V1.2.3** | `[tool.flow_engineering] min_sdd_skill_versions` enforcement: NEW pyproject section (dict of `sub-agent-name → minimum-version`) + `enforce_min_skill_versions(min_versions)` helper in `opencode_skill_catalog.py` (raises `SkillVersionError` on downgrade) + 3-line CLI hook at `flow apply`/`flow verify`/`flow archive` startup (exit code 4). | `pyproject.toml`, `src/flow_engineering/opencode_skill_catalog.py`, `src/flow_engineering/cli.py`, `tests/unit/test_opencode_skill_catalog.py`, `tests/bdd/req54_skill_version_gate.feature` | ~240 |
| **REQ-V1.2.4** | Path A subcommand group rename: `flow drift <change>` → `flow drift run <change>` + `flow drift events {list,tail,stats}` (group subcommand). `flow drift-events {list,tail,stats}` remains as a 1-release `deprecated=True` Click group alias emitting `DeprecationWarning` + dispatching to the new `flow drift events` subcommands. CHANGELOG v1.2 BREAKING entry. | `src/flow_engineering/cli.py`, `tests/unit/test_cli_drift.py`, `tests/unit/test_cli_drift_events_*.py`, `CHANGELOG.md` | ~90 |
| **REQ-V1.2.5** | Versioning: pyproject `1.1.0`→`1.2.0` bump + capability spec `decision-drift/spec.md` v1.2 archive status section + CHANGELOG v1.2 entry. | `pyproject.toml`, `openspec/specs/decision-drift/spec.md`, `CHANGELOG.md` | ~30 |

**Total LOC delta**: ~790 LOC prod+test + 4 NEW snapshot files.

---

## Out of scope (deferred to v1.3+)

| Item | Reason | Deferral target |
|---|---|---|
| Remaining 17 ruff residuals in v1.1-touched files (4 auto-fixable + 10 hidden fixes) | Per `v1.1-followups` verify-report W3 ACCEPTED posture; `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent set "defer ruff residuals to next minor" | v1.3+ (next minor release) |
| W2 backfill of on-disk planning artifacts (`proposal.md` + `design.md` + `tasks.md` + `apply-progress/`) for changes that ran as commit-history-only | Documentation-process gap; `v1.1-followups` verify-report W2 ACCEPTED posture | v1.3+ (could be done as a single backfill PR or as part of each affected change's first apply) |
| `prompt_renders.jsonl` rotation (the third JSONL sink) | `prompt_renders.jsonl` is opt-in via `FLOW_PROMPT_LOG=1` (default OFF) so unbounded growth is not a real-world concern yet. Defer until `FLOW_PROMPT_LOG` is on-by-default. | v1.3+ (depends on `FLOW_PROMPT_LOG` becoming default) |
| `flow drift events list --format=ndjson` | `ndjson` format is just a thin alias for `json` with `indent=None`; not worth a flag today | v1.3+ (if operators request it) |
| Golden snapshots for inline prompt constants (`STRICT_TDD_PROMPT` etc.) | The 4 migrated entries have the golden test via `PROMPT_NAMES`; the legacy module-level constants are thin aliases (`prompt_registry.py:179-224` docstring notes "thin aliases that delegate to `get_prompt_template()`") | v1.3+ (only if a future change wants to assert legacy alias identity) |
| `enforce_min_skill_versions` for non-SDD skills (e.g., the 10 OpenCode runtime sdd-* agents per the REQ-49 catalog) | Today the catalog has 20 entries (10 skills × 2 surfaces), but `enforce_min_skill_versions` only needs to enforce on the 8 sdd-* agents that the orchestrator dispatches. The other 12 entries (surface="prompt" variants) are not dispatcher targets. | v1.3+ (if operator feedback shows the gate should also cover non-SDD skills) |

---

## Risks identified

- **LOW**: `metrics.jsonl` rotation under lock on slow network FS — `increment()` is already wrapped in `try/except OSError` (best-effort sink); the rotation call sits OUTSIDE the try block so a slow rotation does not poison the sink path resolution.
- **LOW**: golden test snapshot drift — `--update-goldens` flag is the explicit opt-in path; CI failure on drift is the desired operator signal. Mirrors `scripts/generate_prompts_doc.py` "regenerate via `make docs`" precedent.
- **LOW**: `min_sdd_skill_versions` false positive on parse failure — `_extract_version()` returns `"0.0"` as the safe fallback (existing precedent at `opencode_skill_catalog.py:536`), which will fail the gate correctly (any minimum version > 0.0 is satisfied).
- **MED**: Path A breaking change surprises operators who ignore the `DeprecationWarning` — mitigation is the CHANGELOG v1.2 BREAKING callout + 1-release alias shim + the standard Click `deprecated=True` warning. The risk is bounded to one release cycle (the alias is REMOVED in v1.3 per the `SnapshotGraphMissing` precedent).
- **MED**: Single-PR strategy bundles 4 items (~790 LOC) — per `sdd-phase-common.md` Section E, 790 LOC exceeds the 400-line chained-PR threshold. **Chained PRs recommended** (see Dependency analysis above).
- **LOW**: golden tests for templates with no Jinja placeholders + `.format()` fallback path (the W5 fallback at `prompt_registry.py:862-903`) — the canonical render must use the SAME code path the operator's render uses. The `render_prompt_canonical` helper ensures this by going through `render_prompt` (no shortcut).
- **LOW**: `[tool.flow_engineering]` section collision with existing `[tool.flow_engineering.prompts]` — both are valid TOML tables under the same parent; no collision risk.

---

## Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `observability` PR#2 + `decision-drift/spec.md:410` | REQ-44 `metrics.jsonl` rotation | REQ-V1.2.1 |
| `prompt-registry` PR#1 spec REQ-48 | Golden regression tests for `render_prompt` | REQ-V1.2.2 |
| `prompt-registry` PR#2a spec REQ-54 | `min_sdd_skill_versions` enforcement | REQ-V1.2.3 |
| `v0-followups` design + `decision-drift/spec.md:410` | Path A subcommand group rename (BREAKING) | REQ-V1.2.4 |

## Carry-forwards explicitly NOT touched by this change (deferred to v1.3+)

| Source | Item | Deferral target |
|---|---|---|
| `v1.1-followups` verify-report W3 | 17 ruff residuals in v1.1-touched files | v1.3+ (acceptable-residual-ruff precedent) |
| `v1.1-followups` verify-report W2 | On-disk planning artifacts backfill (`proposal.md` + `design.md` + `tasks.md` + `apply-progress/`) for commit-history-only changes | v1.3+ (documentation-process gap) |
| `prompt-registry` PR#2a | `prompt_renders.jsonl` rotation (third JSONL sink) | v1.3+ (depends on `FLOW_PROMPT_LOG` default) |

---

## Ready for proposal

**Yes.** The 4 items are mutually independent, the rotation pattern has a shipped precedent (`DriftEventLog._rotate_if_needed`), the `SkillVersionError` exception already exists, the golden test pattern is standard pytest-snapshot, and the Path A rename has a proven 1-release alias shim precedent (`Finding.from_legacy`, `SnapshotGraphMissing`).

**Orchestrator should**:
1. Launch `sdd-propose v1.2-followups` to draft the formal proposal with REQ-V1.2.1..V1.2.5 + the per-PR work-unit plan (chained PRs recommended).
2. Pre-cache the delivery strategy as `auto-chain` (4 chained PRs + 1 version bump PR) per `sdd-phase-common.md` Section E + the `work-unit-commits` skill.
3. Surface the Path A BREAKING trade-off to the operator as a CONVERSATIONAL question (not a blocking CLI prompt) before `sdd-tasks` — the operator needs to opt in to the rename (or alternatively request Path B status quo).