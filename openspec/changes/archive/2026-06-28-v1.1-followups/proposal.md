<!-- proposal.md: v1.1-followups. Source: sdd-propose sub-agent (2026-06-28). Backfilled 2026-06-28 from engram `sdd/v1.1-followups/proposal` summary + verify-report.md + commit history per W2 cleanup. -->
# Proposal: v1.1-followups

```yaml
status: success
confidence: high
open_questions_count: 0  # All OQs resolved per explore + orchestrator pre-decisions
chained_pr_recommendation: no  # Single PR; ~720 prod + ~1000 test = ~1720 total LOC well over 400 chained-PR threshold but operationally a single-cycle release
wall_time_estimate: ~4-6h end-to-end
forecast_loc: 720 prod + 1000 tests = 1720 total
pr_split: single PR (~1720 LOC delta; operationally a single-cycle debt-closure release despite >400 LOC threshold)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.1-followups\proposal.md
next_recommended: sdd-design v1.1-followups
strict_tdd: true
chain_strategy: not_applicable
```

## Intent

`flow-engineering v1.0.0` (change #10 `v1.0-followups`, shipped 2026-06-28 per HEAD `54d5cdb`) closed the JSONL wire-format `decision_id: int` flip + shipped the `flow drift-events {list,tail,stats}` read-side CLI + cleaned 12 mypy residuals in `decision_drift.py`. The v1.0 verify-report flagged **5 SUGGESTION findings** (S1 DriftEventLog rotation + S2 wire-format hardening drop defensive shim + S3 REQ-51 `prompt_renders.jsonl` sink + S4 REQ-52 prompt observability counters + S5 REQ-53 `docs/prompts.md` auto-gen) + W7 DriftEventLog rotation carry-forward from `drift-hardening` — all explicitly **deferred to v1.1** per capability spec `openspec/specs/decision-drift/spec.md` (v1.1 planning note). This change executes that v1.1 commitment: closes the 5 SUGGESTIONs + adds the 6th item (REQ-V1.1.6 ruff `--unsafe-fixes` + `SnapshotGraphMissing` 1-release alias) into a single focused v1.1.0 release.

The 6 REQs are well-bounded, low-risk, and the work is heavily precedented:

- **REQ-V1.1.1** is an env-var-gated rotation function (`_rotate_if_needed(path)`) + age-based sibling cleanup + best-effort `try/except OSError`. Mirrors the `metrics.jsonl` rotation policy from `observability` REQ-44 (deferred separately).
- **REQ-V1.1.2** removes the v1.0 defensive `str→int` shim, replaces it with a hard `DriftEventLogLegacyFormatError(ValueError)` + a `--strict` flag on `flow drift-events {list,tail,stats}` that aborts with the CHANGELOG v1.0 `sed` migration hint. Mirrors the v0.8.0→v0.9.0 compat-shim removal pattern (`Finding.from_legacy` → `TypeError`).
- **REQ-V1.1.3** is a NEW `prompt_renders.jsonl` opt-in sink (`FLOW_PROMPT_LOG=1` gate) + `--render-count` / `--render-history` flags on `flow prompts show`. Mirrors the `drift_events.jsonl` sink precedent.
- **REQ-V1.1.4** is 3 NEW observability counters + a `DOMAIN_BY_PREFIX` extension. Mirrors `drift_*_total` counter catalog pattern.
- **REQ-V1.1.5** is a NEW `scripts/generate_prompts_doc.py` + `docs/prompts.md` generated artifact + `make docs` target. Mirrors the capability spec `decision-drift/spec.md` precedent.
- **REQ-V1.1.6** is `uv run --frozen ruff check --fix --unsafe-fixes src/flow_engineering/decision_drift.py` (3 fixes: UP022 + UP042 + C419) + `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename with 1-release alias. Mirrors v0.8.0→v0.9.0 `from_legacy` shim removal pattern.

The HEAD at `ec97348` has **1275 / 1275 tests passing** (verified at `openspec/specs/decision-drift/spec.md` v1.0 entry). Strict TDD is ON; the change follows `work-unit-commits` discipline (each commit ≤30 LOC delta; per-task RED → GREEN → REFACTOR markers per the `v0.9.0-hardening` precedent). Total scope: **~720 prod LOC + ~1000 test LOC = ~1720 total** — well over the 400 LOC chained-PR threshold but the 6 REQs are tightly coupled (especially REQ-V1.1.3 + V1.1.4 sharing the `_emit_render_record` hook) so a single-cycle release is the right granularity.

**Why now**: v1.0 shipped 1 day ago (HEAD `54d5cdb` → `ec97348` is 1 commit of archive closeout). The capability spec v1.1 planning note is committed; the v1.0 verify-report's S1..S5 + W7 are explicit; the `drift-hardening` verify-report's W7 mirrors the DriftEventLog rotation carry-forward. Every release cycle that ships without closing these items erodes the spec-vs-impl trust the capability spec is building. **v1.1 closes the SUGGESTIONs + the W7 rotation + the ruff cleanup in a single focused debt-closure release**.

The headline deliverable is **6 REQs** (S1 rotation + S2 hardening + S3 sink + S4 counters + S5 docs + W6 ruff cleanup). The secondary deliverable is the **CHANGELOG v1.1 entry** with the wire-format hardening `sed` migration hint + the DriftEventLog rotation env-var documentation + the `prompt_renders.jsonl` opt-in gate docs. v1.1 is intentionally NOT a feature release — it's the **second "debt closure" release** before the project enters the v1.x feature cycle.

## Context (from explore)

Explored in [`explore.md`](./explore.md). The exploration confirmed:

- **REQ-V1.1.1 (rotation)**: `_rotate_if_needed(path)` is NEW; `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` env-var resolution helpers exist at `drift_event_log.py:197-218` but the rotation itself was never wired; rotation MUST run INSIDE the existing `threading.Lock` at line 98 (D11 contract).
- **REQ-V1.1.2 (S2 hardening)**: `_legacy_warn_emitted` flag at `drift_event_log.py:96` + defensive block at `lines 140-149` must be REMOVED; NEW `DriftEventLogLegacyFormatError(ValueError)` exception must be raised on legacy `str` lines; CLI must gain `--strict` flag at `cli.py:1818/1905/1987/2036` (3 `flow drift-events` subcommands).
- **REQ-V1.1.3 (sink)**: NEW `prompt_render_log.py` (~80 LOC) + `_emit_render_record()` hook in `prompt_registry.py:758`; opt-in via `FLOW_PROMPT_LOG=1` + optional `FLOW_PROMPT_LOG_PATH` override.
- **REQ-V1.1.4 (counters)**: EXTEND `DOMAIN_BY_PREFIX` at `observability.py:495` with `"prompts_": "prompt"`; ADD 3 counters (`prompts_render_total` + `prompts_render_ms` + `prompts_render_failed_total`); WRAP `render_prompt()` + `render_prompt_safe()` at `prompt_registry.py:758`.
- **REQ-V1.1.5 (docs)**: NEW `scripts/generate_prompts_doc.py` (~100 LOC) walks `PROMPT_NAMES` + reads `.j2` template bodies + renders example via `render_prompt_safe()` + emits `docs/prompts.md` (~120 LOC).
- **REQ-V1.1.6 (ruff)**: 3 ruff fixes on `decision_drift.py` (UP022 + UP042 + C419) + `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename at `snapshot_manager.py:81-101` + 1-release alias via PEP 562 `__getattr__` at `snapshot_manager.py:104-123`.

**Total scope**: ~720 prod LOC + ~1000 test LOC = ~1720 total. Single PR; operationally a single-cycle debt-closure release despite >400 LOC threshold (the 6 REQs are tightly coupled; splitting into chained PRs would multiply review × archive overhead without reducing review risk). Strict TDD per `work-unit-commits` (18-22 commits across 6 sub-batches; each commit ≤30 LOC delta).

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `v1.0-followups` verify-report S1 | `DriftEventLog` rotation deferred | REQ-V1.1.1 — `_rotate_if_needed(path)` + `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` (default 10 MB) + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort OSError + rotation INSIDE existing `threading.Lock` |
| `v1.0-followups` verify-report S2 | Defensive `str→int` shim hardening (WARN → error) | REQ-V1.1.2 — REMOVE `_legacy_warn_emitted` flag + defensive block; ADD `DriftEventLogLegacyFormatError(ValueError)`; CLI `--strict` flag aborts with exit 4 + CHANGELOG v1.0 `sed` migration hint |
| `prompt-registry` PR#1 spec REQ-51 | `prompt_renders.jsonl` sink | REQ-V1.1.3 — NEW `src/flow_engineering/prompt_render_log.py` + `PromptRenderEvent` + `PromptRenderLog` + `record_prompt_render()` opt-in via `FLOW_PROMPT_LOG=1` + `flow prompts show --render-count --render-history` flags |
| `prompt-registry` PR#1 spec REQ-52 | Prompt observability counters | REQ-V1.1.4 — `prompts_render_total{domain, prompt_id, status}` + `prompts_render_ms{domain, prompt_id, count}` + `prompts_render_failed_total{domain, prompt_id, error}`; `DOMAIN_BY_PREFIX['prompts_'] = 'prompt'`; `record_prompt_render_summary()` helper |
| `prompt-registry` PR#1 spec REQ-53 | `docs/prompts.md` auto-generated | REQ-V1.1.5 — `scripts/generate_prompts_doc.py` + generated `docs/prompts.md` + `make docs` Makefile target |
| `v0.9.0-hardening` verify-report S2 | 12 ruff `--unsafe-fixes` cleanup at `decision_drift.py` | REQ-V1.1.6 — `ruff check --fix --unsafe-fixes` on `decision_drift.py` (3 fixes: UP022 + UP042 + C419) + `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename + 1-release PEP 562 alias |

### Carry-forwards explicitly NOT touched by this change (deferred)

| Source | Item | Deferral target | Notes |
|---|---|---|---|
| `observability` REQ-44 | `metrics.jsonl` rotation | v1.2+ | Out of v1.1 scope per orchestrator brief; v1.1 scopes to DriftEventLog only |
| `prompt-registry` PR#2a REQ-48 | Golden regression tests for prompts | v1.2+ | Next-feature territory |
| `prompt-registry` PR#2a REQ-54 | `min_sdd_skill_versions` pyproject gate | v1.2+ | Tooling gate; pairs with the v1.2 sdd-process change |
| `v1.0-followups` design | Path A `flow drift-events` subcommand group rename (BREAKING) | v1.2+ | Path A is more idiomatic with `flow metrics {summary,export,aggregate}` but BREAKING; Path B is non-breaking; v1.0 shipped Path B; Path A deferred until namespace grows further |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Single PR, per-task TDD, 6 sequential sub-batches (A=rotation, B=S2 hardening, C=sink, D=counters, E=docs, F=ruff+version bump)** | ~720 prod + ~1000 test = ~1720 total | Bundles the 5 SUGGESTIONs + the W7 rotation + the ruff cleanup + the alias into one logical v1.1 release; single CHANGELOG entry; one migration guide for operators; the 6 REQs share infrastructure (`_emit_render_record` hook) so splitting into chained PRs multiplies review overhead | Per-task TDD means ~18-22 commits (vs ~6 for per-group); total LOC > 400 chained-PR threshold | **RECOMMENDED** |
| B — Chained 2-PR split (PR#1 = REQ-V1.1.1..V1.1.3 rotation+hardening+sink; PR#2 = REQ-V1.1.4..V1.1.6 counters+docs+ruff+version bump) | ~860 each = ~1720 split | Smaller review unit per PR; incremental delivery; first PR ships the operator-visible DriftEventLog rotation earlier | 2 PRs of large churn; high overhead (CI ×2, review ×2, archive ×2); one CHANGELOG v1.1 entry split across 2 PRs is operator-hostile; the 12 ruff `--unsafe-fixes` cleanup has to ship with the CHANGELOG anyway; the 2 PRs share `_emit_render_record` hook forcing serialized review anyway | Rejected |
| C — Per-group TDD (6 sub-batches = 6 commits) | ~1720 in 6 commits | Fewer commits (6 vs 18-22); faster review | Per-group TDD hides silent regressions: if rotation breaks a test site, the S2 hardening commit can't bisect it; the v0.9.0-hardening per-task TDD discipline caught 3 design deviations (W1/W2/W3) via the "shim-still-exists" RED-before-GREEN pattern | Rejected |

**Recommendation: Approach A.** The DriftEventLog rotation (REQ-V1.1.1) is a non-breaking operator-feature; the S2 hardening (REQ-V1.1.2) is a hard-break operator migration; the sink (REQ-V1.1.3) + counters (REQ-V1.1.4) + docs (REQ-V1.1.5) introduce new surfaces; the ruff cleanup (REQ-V1.1.6) is internal cleanup. All 6 are independently testable and benefit from per-task TDD discipline. The 18-22 commit target is manageable (each commit ≤30 LOC delta) and matches the `work-unit-commits` skill precedent used by `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups`.

### Sub-batch sequencing rationale

| Sub-batch | REQ | Why this position |
|---|---|---|
| **A** | REQ-V1.1.1 (rotation) | Lowest risk; pure infrastructure addition; no behavior change to existing callers |
| **B** | REQ-V1.1.2 (S2 hardening) | Hard-break migration; ships AFTER rotation so operators can rotate their legacy `str` lines during migration |
| **C** | REQ-V1.1.3 (sink) | NEW file; opt-in (default off); no behavior change to existing callers |
| **D** | REQ-V1.1.4 (counters) | DEPENDS on REQ-V1.1.3 hook (`_emit_render_record`); ships immediately after |
| **E** | REQ-V1.1.5 (docs) | Pure doc generation; idempotent; no behavior change |
| **F** | REQ-V1.1.6 (ruff + alias + version bump) | LAST per `v0.9.0-hardening` + `v1.0-followups` precedent; version bump + alias deprecation warning close out the release |

## Affected areas

- `src/flow_engineering/drift_event_log.py` (A + B — rotation + S2 hardening)
- `src/flow_engineering/cli.py` (B — `--strict` flag on 3 subcommands)
- `src/flow_engineering/prompt_render_log.py` (C — NEW)
- `src/flow_engineering/prompt_registry.py` (C + D — sink wire + counter emission)
- `src/flow_engineering/observability.py` (D — 3 counters + DOMAIN_BY_PREFIX extension)
- `scripts/generate_prompts_doc.py` (E — NEW)
- `docs/prompts.md` (E — generated artifact)
- `Makefile` (E — `docs:` target)
- `src/flow_engineering/snapshot_manager.py` (F — canonical class + alias)
- `src/flow_engineering/decision_drift.py` (F — ruff auto-fix)
- `CHANGELOG.md` (F — v1.1 entry)
- `pyproject.toml` (F — version bump 1.0.0 → 1.1.0)
- `openspec/specs/decision-drift/spec.md` (F — v1.1 archive section)
- `openspec/specs/prompt-registry/spec.md` (F — v1.1 archive section)
- `tests/unit/test_drift_event_log.py` (A + B)
- `tests/unit/test_prompt_render_log.py` (C — NEW)
- `tests/unit/test_prompt_render.py` (C — 2 instrumentation tests)
- `tests/unit/test_cli_prompts_show_render.py` (C — 3 CLI flag tests)
- `tests/unit/test_observability_prompt_counters.py` (D — NEW)
- `tests/unit/test_generate_prompts_doc.py` (E — NEW)
- `tests/unit/test_snapshot_graph_missing_error.py` (F — NEW)

## Capabilities touched

- `decision-drift` (v1.0) — REQ-V1.1.1 (rotation) + REQ-V1.1.2 (hardening)
- `observability` (v0.7.0) — REQ-V1.1.4 (prompt counters)
- `prompt-registry` (v0.8.0 PR#1) — REQ-V1.1.3 (sink) + REQ-V1.1.5 (docs)
- `graph-snapshots` (v0.6.0) — REQ-V1.1.6 (alias)

## Rollback plan

- Single-PR release; rollback = `git revert <v1.1.0-commit>`.
- REQ-V1.1.2 S2 hardening is the only non-trivial rollback surface: operators who upgraded to v1.1 with legacy `str` JSONL lines and DIDN'T run the `sed` migration get a hard error instead of a soft WARN. Default mode (without `--strict`) preserves the soft-WARN behavior; only `--strict` aborts. Operators running without `--strict` see no behavior change vs v1.0.
- REQ-V1.1.6 alias is intentional (mirrors v0.8.0→v0.9.0 compat-shim pattern); v1.2 removes the alias.

## Dependencies

- `pytest` + `pytest-bdd` (existing dev deps; no new deps)
- `ruff` (existing dev dep; `--unsafe-fixes` is built-in)
- `python-jinja2` (existing dep for `.j2` template rendering)
- No external service deps; all changes are local-only.

## Success criteria

1. **1342 / 1342 tests passing** (baseline 1275 + ~67 NEW v1.1 tests across 6 NEW test files)
2. **0 mypy errors** in `decision_drift.py` (carried forward from v1.0 T4.3 cleanup)
3. **182 / 182 BDD scenarios passing** (unchanged from v1.0 baseline)
4. **`docs/prompts.md`** generated + committed + idempotent
5. **`flow drift-events {list,tail,stats} --strict`** exits 4 on legacy lines + emits CHANGELOG v1.0 `sed` migration hint
6. **`flow metrics --domain=prompt`** groups `prompts_render_total{...}` counters correctly
7. **`SnapshotGraphMissingError is SnapshotGraphMissing == True`** (PEP 562 alias verified live)
8. **6 / 6 REQs have at least one passing test demonstrating compliance**

## Cross-impact

- `decision-drift` capability spec — REQ-55 (DriftEventLog JSONL writer) updated to include rotation sub-REQ
- `observability` capability spec — REQ-12 (counter catalog) extended with 3 prompt counters
- `prompt-registry` capability spec — REQ-45 + REQ-46 extended with sink + render-history flags
- `graph-snapshots` capability spec — `SnapshotGraphMissingError` added as canonical exception
- All cross-impact updated in the F-sub-batch (last sub-batch).

## Wall time

~4-6h end-to-end:
- A (rotation): ~45 min
- B (S2 hardening): ~45 min
- C (sink): ~75 min
- D (counters): ~45 min
- E (docs): ~30 min
- F (ruff + alias + version bump): ~30 min
- Apply-progress closeout docs per sub-batch: ~30 min total
- Verify + archive: ~45 min

## Carry-forwards to v1.2+ (explicit)

Per the explore.md Risk section + the carry-forwards-not-touched table:

- REQ-44 `metrics.jsonl` rotation (mirrors REQ-V1.1.1 pattern)
- REQ-48 golden regression tests for prompts
- REQ-54 `min_sdd_skill_versions` pyproject gate
- Path A `flow drift-events` subcommand group rename (BREAKING)
- 9 remaining ruff `--unsafe-fixes` cleanup at `decision_drift.py` (the 3 fixed in v1.1 are the easiest; remaining 9 require semantic refactors)
- 16 ruff errors in non-v1.1-touched files (e.g., `watcher.py` `state_path` unused, `orchestrator.py` imports, etc.)