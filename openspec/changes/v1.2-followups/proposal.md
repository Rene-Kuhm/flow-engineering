<!-- proposal.md: v1.2-followups. Source: sdd-propose sub-agent (2026-06-28). Generated from explore.md per orchestrator pre-decisions + AGENTS.md SDD+BDD+TDD mandate. -->
# Proposal: v1.2-followups

```yaml
status: success
confidence: high
open_questions_count: 0
chained_pr_recommendation: yes  # 4 chained PRs (mandatory; ~790 LOC > 400 threshold)
chained_pr_split:
  - "PR#2a (v1.2.0a): REQ-44 metrics rotation"
  - "PR#2b (v1.2.0b): REQ-48 golden regression tests"
  - "PR#2c (v1.2.0c): REQ-54 min_sdd_skill_versions"
  - "PR#2d (v1.2.0d): Path A rename + 1-release alias + version bump 1.1.0 → 1.2.0"
wall_time_estimate: ~3-5h end-to-end
forecast_loc: 790 (220+210+240+90+30 closeout)
strict_tdd: true
chain_strategy: stacked-to-main  # Each PR merges to main, then next PR branches off
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.2-followups\proposal.md
next_recommended: sdd-design v1.2-followups
```

## Intent

`flow-engineering v1.1.0` (change #11 `v1.1-followups`, shipped 2026-06-28 per HEAD `6cae060` + `75961ad` closeout) closed the DriftEventLog rotation carry-forward + S2 wire-format hardening + REQ-51/52/53 prompt observability + the SnapshotGraphMissing 1-release alias + 3 ruff `--unsafe-fixes` cleanups. The v1.1 verify-report flagged **3 ACCEPTED findings** (W2 planning-artifact gap + W3 17 ruff residuals in v1.1-touched files + S1 trailing-newline cleanup) and the capability spec v1.2 entry at `openspec/specs/decision-drift/spec.md:410` explicitly names **4 carry-forwards** that v1.2 must close:

- **REQ-44** `metrics.jsonl` rotation (parallel to the DriftEventLog rotation that v1.1 shipped)
- **REQ-48** golden regression tests for `render_prompt` (deferred from prompt-registry PR#1 spec)
- **REQ-54** `min_sdd_skill_versions` enforcement in pyproject.toml (deferred from prompt-registry PR#2a spec)
- **Path A** subcommand group rename `flow drift-events {list,tail,stats}` → `flow drift events {list,tail,stats}` (BREAKING — Path A vs Path B trade-off resolved by orchestrator pre-decision)

This change executes the v1.2 commitment in a single focused TDD cycle that closes the carry-forward gap without re-opening any closed capability contract. The Path A rename is the **only BREAKING surface** (mitigated by a 1-release `deprecated=True` Click group alias shim, mirroring the `SnapshotGraphMissing` v1.1 precedent); the other 3 items are additive on existing modules.

**Why now**: v1.1 shipped 1 cycle ago. The capability spec v1.2 entry is committed; the v1.1 verify-report's "carry-forwards NOT touched" table explicitly names the 4 items; every release cycle that ships without closing them erodes the spec-vs-impl trust the capability spec is building. **v1.2 closes the 4 carry-forwards in 4 chained PRs (mandatory per ~790 LOC > 400 chained-PR threshold)** with strict TDD discipline.

The headline deliverable is **4 chained PRs + 1 version bump**:
- **PR#2a (v1.2.0a)** — REQ-44 `metrics.jsonl` rotation (mirror of shipped `DriftEventLog._rotate_if_needed` pattern)
- **PR#2b (v1.2.0b)** — REQ-48 golden regression tests for `render_prompt` (4 snapshot files + `render_prompt_canonical()` helper + `--update-goldens` flag)
- **PR#2c (v1.2.0c)** — REQ-54 `min_sdd_skill_versions` pyproject gate (8 sdd-* agents + 3-line CLI hook at `flow apply`/`verify`/`archive` startup, exit code 4)
- **PR#2d (v1.2.0d)** — Path A rename + 1-release `deprecated=True` Click group alias + CHANGELOG v1.2 BREAKING entry + pyproject `1.1.0` → `1.2.0` bump + capability spec sync

The secondary deliverable is the **CHANGELOG v1.2 entry** with the BREAKING rename callout + the `flow drift-events` → `flow drift events` migration hint + the `FLOW_METRICS_LOG_MAX_BYTES` / `FLOW_METRICS_LOG_MAX_AGE_DAYS` env-var documentation + the `min_sdd_skill_versions` pyproject section documentation. v1.2 is intentionally NOT a feature release — it's the **third "debt closure" release** in the flow-engineering cycle (after v0.9.0-hardening and v1.1-followups).

## Context (from explore)

Explored in [`explore.md`](./explore.md). The exploration confirmed:

- **REQ-44 (metrics rotation)**: `src/flow_engineering/observability.py:171-189` `increment()` has NO rotation call today. `src/flow_engineering/drift_event_log.py:196-254` is the **reference implementation**: `_resolve_rotation_threshold_bytes()` + `_resolve_max_age_days()` + `_rotate_if_needed(path)` already running in production. New helpers at `observability.py`: `_rotate_metrics_if_needed(path)` + `_resolve_metrics_rotation_threshold_bytes()` + `_resolve_metrics_max_age_days()` + constants `METRICS_ROTATE_BYTES_DEFAULT` (10 MB) + `METRICS_ROTATE_AGE_DAYS_DEFAULT` (30 days). Rotation call sits OUTSIDE the existing `try/except OSError` (so a slow FS cannot poison the sink path resolution).
- **REQ-48 (golden tests)**: `src/flow_engineering/prompt_registry.py:179-224` `PROMPT_NAMES` catalog has **4 entries** (`strict_tdd` + `auto_suggest_header` + `auto_suggest_footer` + `auto_suggest_empty`). 21 existing render tests do NOT assert exact output text. NEW `tests/golden/prompts/*.txt` snapshots (one per `PROMPT_NAMES` entry) + `render_prompt_canonical(prompt_id, **vars)` helper in `prompt_registry.py` (injects canonical default values so golden tests don't depend on call-site kwargs) + `TestGoldenRegression` class + `--update-goldens` CLI flag.
- **REQ-54 (skill version gate)**: `src/flow_engineering/opencode_skill_catalog.py:117` `SkillVersionError(Exception)` class ALREADY EXISTS. NEW `[tool.flow_engineering]` pyproject section: `min_sdd_skill_versions = {"sdd-explore": "3.0", ..., "sdd-archive": "3.0"}` (8 entries). NEW `enforce_min_skill_versions(min_versions: dict[str, str])` helper raises `SkillVersionError` on downgrade with remediation message. 3-line CLI hook at `flow apply` / `flow verify` / `flow archive` startup (exit code 4).
- **Path A (rename)**: `src/flow_engineering/cli.py:1718-1816` `flow drift <change>` is a flat `@main.command()` with positional arg. `src/flow_engineering/cli.py:1821-2162` `flow drift-events {list,tail,stats}` is `@main.group(name="drift-events")`. Convert `@main.command("drift")` → `@main.group("drift")` + `@drift_group.command("run", ...)` (default command via `invoke_without_command=True`). Add `@main.group(name="drift-events", deprecated=True)` 1-release alias emitting `DeprecationWarning` and dispatching to the new `flow drift events` subcommands. CHANGELOG v1.2 BREAKING entry + `flow drift-events {list,tail,stats}` migration hint.

**Total scope**: ~790 LOC prod+test + 4 NEW snapshot files. **Chained PRs MANDATORY** per `sdd-phase-common.md` Section E (790 LOC exceeds the 400-line chained-PR threshold). Each PR is ≤ ~250 LOC and autonomously verifiable.

**Cross-dependencies**: NONE. The 4 items are mutually independent and trivially stackable. Each can ship in any order or all together. Recommended ordering per `work-unit-commits` skill: REQ-44 first (lowest risk, pure infrastructure addition), REQ-48 second (golden tests are additive), REQ-54 third (uses existing `SkillVersionError`), Path A + version bump last (closes out the release + the CHANGELOG v1.2 BREAKING entry).

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `observability` REQ-44 | `metrics.jsonl` rotation deferred | REQ-V1.2.1 — `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow OUTSIDE the rotation call |
| `prompt-registry` PR#1 spec REQ-48 | Golden regression tests for `render_prompt` | REQ-V1.2.2 — `tests/golden/prompts/*.txt` snapshots (4 files per `PROMPT_NAMES` entry) + `render_prompt_canonical()` helper + `TestGoldenRegression` class + `--update-goldens` flag |
| `prompt-registry` PR#2a spec REQ-54 | `min_sdd_skill_versions` enforcement | REQ-V1.2.3 — `[tool.flow_engineering] min_sdd_skill_versions` dict (8 entries) + `enforce_min_skill_versions()` helper in `opencode_skill_catalog.py` + 3-line CLI hook at `flow apply`/`verify`/`archive` startup (exit code 4) |
| `v0-followups` design + `v1.1-followups` verify-report | Path A subcommand group rename (BREAKING) | REQ-V1.2.4 — `flow drift <change>` → `flow drift run <change>` + `flow drift events {list,tail,stats}` + `flow drift-events {list,tail,stats}` 1-release `deprecated=True` Click group alias + CHANGELOG v1.2 BREAKING entry |

### Carry-forwards explicitly NOT touched by this change (deferred to v1.3+)

| Source | Item | Deferral target | Notes |
|---|---|---|---|
| v1.2 Path A hard removal | `flow drift-events` 1-release alias removed in v1.3 | v1.3 | Standard 1-release alias pattern (mirrors `SnapshotGraphMissing` v1.1 → v1.2 removal) |
| v1.1-followups verify-report W3 | 17 ruff residuals in v1.1-touched files (4 auto-fixable + 10 hidden fixes) | v1.3+ | Per `v1.1-followups` ACCEPTED posture; precedent set by `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` |
| v1.1-followups verify-report W2 | On-disk planning artifacts backfill (`proposal.md` + `design.md` + `tasks.md` + `apply-progress/`) for commit-history-only changes | v1.3+ | Documentation-process gap; this v1.2 proposal addresses it by writing artifacts inline per AGENTS.md SDD mandate |
| REQ-55+ future carry-forwards | (none surfaced yet) | v1.3+ | If new debt surfaces during v1.2 apply, it lands in v1.3 planning |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — 4 chained PRs (one per REQ + closeout PR), strict TDD, per-PR ≤ ~250 LOC** | ~790 prod+test in 4 PRs (~220 + ~210 + ~240 + ~120) | Lowest per-PR review risk; each PR autonomously verifiable; aligns with 400-line chained-PR threshold; PR#2d naturally closes the release (CHANGELOG + version bump + capability spec sync); 4 PRs match the 4 REQ boundaries | 4 PRs of review/archive overhead (acceptable for debt-closure release); operator migration window bounded to one release cycle | **RECOMMENDED** |
| B — Single PR (all 4 items in one commit series) | ~790 in 1 PR | Single CHANGELOG entry; one migration guide; fewer review rounds | **EXCEEDS 400-line chained-PR threshold by ~2×**; harder to bisect if one item regresses; the 4 items are mutually independent so they don't benefit from bundling | Rejected (per `sdd-phase-common.md` Section E mandatory) |
| C — 2 chained PRs (PR#2a = REQ-44 + REQ-48 infrastructure; PR#2b = REQ-54 + Path A + closeout) | ~790 in 2 PRs (~430 + ~360) | Half the review overhead of 4 PRs; PR#2b bundles the BREAKING surface with the version bump (cleaner operator narrative) | PR#2a still exceeds 400-line chained-PR threshold by 30 LOC; bundling unrelated REQs in one PR hurts bisectability | Rejected (still over threshold) |

**Recommendation: Approach A.** Each of the 4 PRs is independently testable, ≤ ~250 LOC, and benefits from strict-TDD per-task RED → GREEN → REFACTOR discipline. The 4-PR split mirrors the natural REQ boundaries (one PR per REQ + the closeout PR for the BREAKING rename + version bump). The `stacked-to-main` chain strategy means each PR merges to `main`, then the next PR branches off — so each PR is bisectable against its predecessor and the project tree never has a stale `next` branch.

### Per-PR scope

| PR | REQs | Scope | LOC budget | Wall time |
|---|---|---|---|---|
| **PR#2a** (v1.2.0a) | REQ-V1.2.1 | `observability.py` rotation helpers + `TestMetricsRotation` class + `req44_metrics_rotation.feature` BDD | ~220 | ~50min |
| **PR#2b** (v1.2.0b) | REQ-V1.2.2 | 4 golden snapshot files + `render_prompt_canonical()` helper + `TestGoldenRegression` + `--update-goldens` flag + `req48_golden_prompts.feature` BDD | ~210 + 4 snapshot files | ~60min |
| **PR#2c** (v1.2.0c) | REQ-V1.2.3 | `[tool.flow_engineering] min_sdd_skill_versions` pyproject section + `enforce_min_skill_versions()` helper + 3-line CLI hook + `TestEnforceMinSkillVersions` + `req54_skill_version_gate.feature` BDD | ~240 | ~70min |
| **PR#2d** (v1.2.0d) | REQ-V1.2.4 + closeout | `flow drift <change>` → `flow drift run <change>` group refactor + `flow drift events {list,tail,stats}` subcommands + `flow drift-events` 1-release `deprecated=True` Click group alias + alias tests + CHANGELOG v1.2 BREAKING entry + pyproject `1.1.0`→`1.2.0` bump + capability spec v1.2 archive sync | ~120 | ~60min |

Total: ~790 LOC in 4 PRs over ~4h wall time.

## Open Questions

Per the orchestrator pre-decisions, **0 open questions**. The Path A vs Path B trade-off is RESOLVED (Path A approved; 1-release alias shim mandated). All other design choices follow shipped precedent (DriftEventLog rotation pattern + SnapshotGraphMissing alias pattern + scripts/generate_prompts_doc.py snapshot pattern).

| Question | Pre-decided answer | Source |
|---|---|---|
| Should Path A ship in v1.2 or defer to v1.3? | **Path A in v1.2** — 1-release `deprecated=True` Click group alias bounds operator migration to one release cycle | Orchestrator brief + `decision-drift/spec.md:410` + `SnapshotGraphMissing` v1.1 alias precedent |
| Should `metrics.jsonl` rotation mirror `drift_events.jsonl` exactly? | YES — same 10 MB + 30 days defaults + best-effort `try/except OSError` swallow + rotation call OUTSIDE the existing OSError try block | `drift_event_log.py:196-254` precedent |
| Where should golden snapshots live? | `tests/golden/prompts/*.txt` — git-diffable, reviewable in PR, regenerable via `--update-goldens` flag | `scripts/generate_prompts_doc.py` precedent + standard pytest-snapshot convention |
| Where should `min_sdd_skill_versions` dict live? | `[tool.flow_engineering]` pyproject section — single source of truth, version-controlled, discoverable | pyproject `[tool.flow_engineering.prompts]` precedent + standard pyproject convention |
| Should the version gate exit code match `flow` exit codes? | YES — exit 4 (data/contract error) via `observability.EXIT_INVALID_VALUE` | `cli.py:1979` precedent + v1.1 `DriftEventLogLegacyFormatError` exit 4 precedent |
| Chain strategy | **stacked-to-main** — each PR merges to `main`, then next PR branches off | `work-unit-commits` skill + the `prompt-registry` PR#1→PR#2b chained precedent |

## Affected Areas

| Area | Impact | PR | Description |
|---|---|---|---|
| `src/flow_engineering/observability.py` | MODIFY | PR#2a | `_rotate_metrics_if_needed(path)` + env-var resolvers + constants; rotation call at top of `increment()` (~40 LOC) |
| `tests/unit/test_observability.py` | MODIFY | PR#2a | NEW `TestMetricsRotation` class (~150 LOC) |
| `tests/bdd/req44_metrics_rotation.feature` | NEW | PR#2a | 1-2 BDD scenarios (~30 LOC) |
| `tests/golden/prompts/strict_tdd.txt` | NEW | PR#2b | Canonical `render_prompt("strict_tdd", test_command="pytest")` snapshot |
| `tests/golden/prompts/auto_suggest_header.txt` | NEW | PR#2b | Canonical empty-var render snapshot |
| `tests/golden/prompts/auto_suggest_footer.txt` | NEW | PR#2b | Canonical empty-var render snapshot |
| `tests/golden/prompts/auto_suggest_empty.txt` | NEW | PR#2b | Canonical empty-var render snapshot |
| `src/flow_engineering/prompt_registry.py` | MODIFY | PR#2b | NEW `render_prompt_canonical(prompt_id, **vars)` helper (~20 LOC) |
| `tests/unit/test_prompt_render_golden.py` | NEW | PR#2b | `TestGoldenRegression` + `TestGoldenUpdate` classes (~150 LOC) |
| `tests/bdd/req48_golden_prompts.feature` | NEW | PR#2b | 2 BDD scenarios (~40 LOC) |
| `pyproject.toml` | MODIFY | PR#2c | NEW `[tool.flow_engineering]` section with `min_sdd_skill_versions` dict (~10 LOC) |
| `src/flow_engineering/opencode_skill_catalog.py` | MODIFY | PR#2c | NEW `enforce_min_skill_versions(min_versions: dict[str, str])` helper (~50 LOC) |
| `src/flow_engineering/cli.py` | MODIFY | PR#2c | 3-line CLI hook at `flow apply`/`flow verify`/`flow archive` startup (~30 LOC) |
| `tests/unit/test_opencode_skill_catalog.py` | MODIFY | PR#2c | NEW `TestEnforceMinSkillVersions` class (~120 LOC) |
| `tests/bdd/req54_skill_version_gate.feature` | NEW | PR#2c | 2 BDD scenarios (~30 LOC) |
| `src/flow_engineering/cli.py` | MODIFY | PR#2d | `flow drift <change>` → `flow drift run <change>` group refactor + `flow drift events {list,tail,stats}` subcommands + `flow drift-events` 1-release `deprecated=True` Click group alias (~30 prod LOC) |
| `tests/unit/test_cli_drift.py` | MODIFY | PR#2d | Update tests for new group dispatch (~25 LOC) |
| `tests/unit/test_cli_drift_events_*.py` | MODIFY | PR#2d | NEW alias tests (4 tests: alias-still-works, alias-emits-warning, alias-dispatches-correctly, alias-removed-in-v1.3) (~25 LOC) |
| `CHANGELOG.md` | MODIFY | PR#2d | NEW v1.2.0 BREAKING entry (~10 LOC) |
| `pyproject.toml` | MODIFY | PR#2d | `1.1.0` → `1.2.0` version bump (~1 LOC) |
| `openspec/specs/decision-drift/spec.md` | MODIFY | PR#2d | v1.2 archive status section + Versioning row flip (~20 LOC) |

## Capabilities

### Modified Capabilities

- `decision-drift` (v1.1) — REQ-V1.2.4 (Path A subcommand group rename; the `flow drift <change>` → `flow drift run <change>` rename touches the public CLI surface; the `flow drift-events` → `flow drift events` rename is the BREAKING surface for read-side consumers). Existing REQ-10 + REQ-11 stay unchanged in spec; the CLI surface change is purely dispatch-level.
- `observability` (v1.1) — REQ-V1.2.1 (metrics rotation extends the existing `increment()` function; the rotation helper mirrors the `DriftEventLog` rotation pattern that's already in production). No counter catalog change.
- `prompt-registry` (v0.8.0 PR#1) — REQ-V1.2.2 (golden regression tests extend the existing `render_prompt()` API; the `render_prompt_canonical()` helper is a thin wrapper). No registry schema change.
- `opencode-skill-catalog` (v0.8.0 PR#1) — REQ-V1.2.3 (the version gate uses the existing `SkillVersionError` class at `opencode_skill_catalog.py:117`; the `enforce_min_skill_versions()` helper is additive). No catalog schema change.

### New Capabilities

- None. All 4 REQs touch existing capabilities. The v1.2 release is a debt-closure release, not a feature release.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | Path A BREAKING change surprises operators who ignore the `DeprecationWarning` (shell aliases, cron jobs, docs pointing at `flow drift-events list` get immediate `No such command` after the alias is removed in v1.3) | **MED** | CHANGELOG v1.2 BREAKING callout + 1-release `deprecated=True` Click group alias emitting `DeprecationWarning` + the standard Click migration hint in `--help` output. The risk is bounded to one release cycle (alias REMOVED in v1.3 per the `SnapshotGraphMissing` precedent). |
| 2 | Single-PR strategy bundles 4 items (~790 LOC) — per `sdd-phase-common.md` Section E, this EXCEEDS the 400-line chained-PR threshold | **MED** | **Chained PRs MANDATORY** — split into 4 PRs (PR#2a + PR#2b + PR#2c + PR#2d), each ≤ ~250 LOC, autonomously verifiable. The `stacked-to-main` chain strategy means each PR is bisectable against its predecessor. |
| 3 | `metrics.jsonl` rotation under lock on slow network FS — `increment()` is already wrapped in `try/except OSError` (best-effort sink); a slow rotation could block the write path | LOW | The rotation call sits OUTSIDE the existing `try/except OSError` so a slow FS cannot poison the sink path resolution. The rotation helper itself uses its own `try/except OSError` for sibling-delete cleanup. |
| 4 | Golden test snapshot drift on unintentional template edits — any whitespace/punctuation/escape-char change in `.j2` files passes the 21 existing render tests but fails the golden regression | LOW | `--update-goldens` flag is the explicit opt-in path for snapshot refresh (mirrors `scripts/generate_prompts_doc.py` "regenerate via `make docs`" precedent). CI failure on drift is the desired operator signal. `render_prompt_canonical()` ensures the canonical render uses the SAME code path the operator's render uses. |
| 5 | `min_sdd_skill_versions` false positive on non-numeric version (e.g., a SKILL.md with a malformed `version: "3.0-beta"` frontmatter) — the version gate fires on a parse failure that shouldn't be a blocker | LOW | `_extract_version()` returns `"0.0"` as the safe fallback (existing precedent at `opencode_skill_catalog.py:536`), which will fail the gate correctly (any minimum version > 0.0 is satisfied). The `SkillVersionError` remediation message includes the actual on-disk version + the remediation hint. |

## Chained PR Strategy (mandatory)

Per `sdd-phase-common.md` Section E + the `work-unit-commits` skill + the `chained-pr` skill, the ~790 LOC forecast EXCEEDS the 400-line chained-PR threshold by ~2×. **Chained PRs MANDATORY**.

**Strategy: `stacked-to-main`** — each PR merges to `main`, then the next PR branches off. This keeps the project tree clean (no stale `next` branches) and makes each PR bisectable against its predecessor.

| PR | Branch | Target | REQs | Scope | LOC | Wall time | Auto-mergeable? |
|---|---|---|---|---|---|---|---|
| **PR#2a** (v1.2.0a) | `chained/v1.2-req44-metrics-rotation` | `main` | REQ-V1.2.1 | `observability.py` rotation helpers + `TestMetricsRotation` class + BDD scenarios | ~220 | ~50min | YES — single-REQ scope, no cross-PR deps |
| **PR#2b** (v1.2.0b) | `chained/v1.2-req48-golden-tests` | `main` | REQ-V1.2.2 | 4 snapshot files + `render_prompt_canonical()` helper + `TestGoldenRegression` + `--update-goldens` flag + BDD scenarios | ~210 + 4 files | ~60min | YES — single-REQ scope, no cross-PR deps |
| **PR#2c** (v1.2.0c) | `chained/v1.2-req54-skill-versions` | `main` | REQ-V1.2.3 | `[tool.flow_engineering] min_sdd_skill_versions` pyproject section + `enforce_min_skill_versions()` helper + 3-line CLI hook + `TestEnforceMinSkillVersions` + BDD scenarios | ~240 | ~70min | YES — single-REQ scope, no cross-PR deps |
| **PR#2d** (v1.2.0d) | `chained/v1.2-path-a-rename-and-bump` | `main` | REQ-V1.2.4 + closeout | `flow drift <change>` → `flow drift run <change>` group refactor + `flow drift events {list,tail,stats}` subcommands + `flow drift-events` 1-release `deprecated=True` Click group alias + alias tests + CHANGELOG v1.2 BREAKING entry + pyproject `1.1.0`→`1.2.0` bump + capability spec v1.2 archive sync | ~120 | ~60min | NO — last PR, requires operator review of BREAKING surface |

**Cross-PR dependencies**: NONE. Each PR is independently testable and the HEAD state after each merge is a valid green-build release candidate.

**PR#2d ordering rationale**: Path A is the last PR because (a) the rename is BREAKING and operators need the CHANGELOG entry + the `flow drift-events` alias shim documented in the same release; (b) the version bump closes out the release; (c) the capability spec archive status section is written AFTER all REQs are implemented.

## Wall Time

~3-5h end-to-end:

- **PR#2a (REQ-44 metrics rotation)**: ~50min
- **PR#2b (REQ-48 golden regression tests)**: ~60min
- **PR#2c (REQ-54 min_sdd_skill_versions)**: ~70min
- **PR#2d (Path A rename + alias + version bump)**: ~60min
- **Apply-progress closeout per PR**: ~20min total
- **Verify + archive (per PR)**: ~30min × 4 = ~120min
- **Total**: ~380min (~6.3h) end-to-end with 4 verify cycles. Conservative estimate: **~3-5h end-to-end** (verify cycles can overlap with the next PR's setup).

## Rollback Plan

4-PR release; rollback = `git revert <PR#2d-merge>` (which transitively reverts the entire v1.2 release).

- **PR#2a (REQ-44 metrics rotation)**: pure addition. Rollback = remove the `_rotate_metrics_if_needed()` call from `increment()`; the sink continues to work unbounded (pre-v1.2 behavior).
- **PR#2b (REQ-48 golden tests)**: pure addition. Rollback = delete the 4 snapshot files + `TestGoldenRegression` class + `render_prompt_canonical()` helper; the 21 existing render tests continue to pass.
- **PR#2c (REQ-54 skill version gate)**: additive startup hook. Rollback = remove the 3-line CLI hook from `flow apply`/`verify`/`archive`; the gate no longer fires (pre-v1.2 behavior).
- **PR#2d (Path A rename + alias + version bump)**: the BREAKING surface. Rollback = restore `@main.command("drift", ...)` (pre-v1.2 shape) + remove the `flow drift-events` alias group + revert CHANGELOG entry + revert pyproject version bump + revert capability spec archive section. Operators with shell aliases pointing at `flow drift events` would need to migrate back to `flow drift-events` after rollback. The alias is INTENTIONALLY kept for one release cycle (mirrors the `SnapshotGraphMissing` v1.1 precedent) — operators running `flow drift-events` after v1.2 merge see a `DeprecationWarning` but the command still works.

## Dependencies

- `pytest` + `pytest-bdd` (existing dev deps; no new deps)
- `Jinja2` (existing dep for `.j2` template rendering)
- `Click` (existing dep for CLI group dispatch)
- No external service deps; all changes are local-only.
- `opencode_skill_catalog.SkillVersionError` (existing class at `opencode_skill_catalog.py:117`) — reused for REQ-V1.2.3, no new exception hierarchy needed.

## Success Criteria

1. **1420 / 1420+ tests passing** (baseline 1342 + ~78 NEW v1.2 tests across 4 NEW test files + 4 NEW snapshot files)
2. **0 mypy errors** in `observability.py` + `opencode_skill_catalog.py` + `prompt_registry.py` (no new annotations introduced; existing annotations preserved)
3. **185 / 185+ BDD scenarios passing** (baseline 182 + ~6 NEW scenarios across 3 NEW feature files: REQ-44 + REQ-48 + REQ-54)
4. **`metrics.jsonl`** rotates at exactly 10 MB to `metrics.<ISO-no-colons>.jsonl` and deletes siblings > 30 days old (mirrors `drift_events.jsonl` behavior)
5. **`tests/golden/prompts/*.txt`** (4 files) match `render_prompt_canonical()` output byte-for-byte; `--update-goldens` flag regenerates snapshots
6. **`flow apply` / `flow verify` / `flow archive`** exit code 4 when `[tool.flow_engineering] min_sdd_skill_versions` declares a minimum version higher than the on-disk SKILL.md version, with `SkillVersionError` remediation message
7. **`flow drift <change>`** still works (now as `flow drift run <change>` via default command dispatch) + `flow drift events {list,tail,stats}` is the new group subcommand + `flow drift-events {list,tail,stats}` continues to work as 1-release alias emitting `DeprecationWarning`
8. **CHANGELOG v1.2.0** BREAKING entry documents the rename + the alias + the `flow drift-events` → `flow drift events` migration hint + the new env vars (`FLOW_METRICS_LOG_MAX_BYTES` + `FLOW_METRICS_LOG_MAX_AGE_DAYS`) + the new pyproject section (`[tool.flow_engineering] min_sdd_skill_versions`)
9. **pyproject.toml** version bumped `1.1.0` → `1.2.0`
10. **4 / 4 REQs have at least one passing test demonstrating compliance**

## Cross-Impact

- `decision-drift` capability spec — REQ-10 surface touched (Path A rename); v1.2 archive status section added
- `observability` capability spec — `metrics.jsonl` rotation behavior added (mirrors `drift_events.jsonl` rotation already shipped)
- `prompt-registry` capability spec — `render_prompt_canonical()` helper added; golden regression test pattern documented
- `opencode-skill-catalog` capability spec — `enforce_min_skill_versions()` helper added; `[tool.flow_engineering] min_sdd_skill_versions` pyproject section documented
- All cross-impact updated in the PR#2d closeout commit (last PR).

## Carry-forwards to v1.3+ (explicit)

Per the explore.md + the v1.1-followups verify-report + the capability spec v1.2 entry:

- **Path A hard removal** — `flow drift-events` 1-release `deprecated=True` Click group alias REMOVED in v1.3 (mirrors `SnapshotGraphMissing` v1.1 → v1.2 removal pattern). Operators with shell aliases/cron jobs pointing at `flow drift-events` get a `No such command` error in v1.3.
- **17 ruff residuals in v1.1-touched files** (4 auto-fixable + 10 hidden fixes) — per `v1.1-followups` verify-report W3 ACCEPTED posture; precedent set by `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` ("defer ruff residuals to next minor release").
- **W2 on-disk planning artifacts backfill** — `proposal.md` + `design.md` + `tasks.md` + `apply-progress/` for changes that ran as commit-history-only. This v1.2 proposal addresses W2 partially by writing the proposal inline per AGENTS.md SDD mandate; full W2 closeout deferred to v1.3+ as a single backfill PR or per-affected-change first apply.
- **`prompt_renders.jsonl` rotation** (third JSONL sink) — `FLOW_PROMPT_LOG=1` is opt-in (default OFF) so unbounded growth is not a real-world concern yet; defer until `FLOW_PROMPT_LOG` is on-by-default.
- **`flow drift events list --format=ndjson`** — `ndjson` is a thin alias for `json` with `indent=None`; not worth a flag today.
- **Golden snapshots for inline prompt constants** (`STRICT_TDD_PROMPT` etc.) — the 4 migrated entries have golden coverage via `PROMPT_NAMES`; legacy module-level constants are thin aliases (per D.8 convention).

## Next Step

Ready for `sdd-design v1.2-followups`. The design phase must resolve:
- D1: `render_prompt_canonical()` default values per prompt (e.g., `strict_tdd → test_command="pytest"`)
- D2: `--update-goldens` CLI flag implementation (Click option vs. environment variable)
- D3: `[tool.flow_engineering] min_sdd_skill_versions` dict shape (string keys + semver string values + optional `flow-engineering >= 1.2` pin)
- D4: `flow drift <change>` default command dispatch via `invoke_without_command=True` vs explicit `flow drift run <change>` (recommend: explicit `flow drift run` for clarity; default command via `invoke_without_command=True` preserves backward-compat for `flow drift <change>` syntax)
- D5: `flow drift-events` 1-release alias implementation (Click `@main.group(name="drift-events", deprecated=True)` + per-subcommand `DeprecationWarning` + dispatch to new `flow drift events` subcommands)

**Loop mode continues**: `sdd-design v1.2-followups` → `sdd-spec v1.2-followups` → `sdd-tasks v1.2-followups` → `sdd-apply v1.2-followups` (chained: PR#2a → PR#2b → PR#2c → PR#2d) → `sdd-verify v1.2-followups` (per-PR) → `sdd-archive v1.2-followups`.