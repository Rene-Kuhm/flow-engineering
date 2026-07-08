<!-- exploration.md: drift-jsonl-rotation-helper change. Phase: explore (sdd-explore). Scope: map the rotation-helper duplication for drift_events.jsonl + metrics.jsonl and propose a minimal Slice-2 refactor. NOT a design / spec / tasks doc. -->
# Explore: drift-jsonl-rotation-helper (Slice 2 — unified JSONL rotation)

> **Change**: `drift-jsonl-rotation-helper` (new at `openspec/changes/drift-jsonl-rotation-helper/`).
> **Slice**: 2 of 3 candidate slices from `openspec/changes/drift-detection/explore.md` §4.
> **Builds on**: `openspec/changes/drift-detection/{explore.md, proposal.md}` (Slice 1 already shipped at `cf7a052`).
> **Authoring**: sdd-explore sub-agent, 2026-07-08.
> **Mode**: hybrid (this file + Engram `sdd/drift-jsonl-rotation-helper/explore`).
> **Strict TDD**: ON per `.specify/memory/constitution.md` Article III + `sdd-init/flow-engineering.md` (`strict_tdd: true`).
> **Constitutional posture**: Article VII (400-LOC PR-diff budget). Slice 2 is a pure-duplication refactor — fits easily under budget.

## Intent (locked from the orchestrator kick-off)

Continue drift-detection Slice 2: **unify JSONL rotation logic for `drift_events.jsonl` and `metrics.jsonl` without opening unrelated features.** Lock scope discipline. Do NOT touch CLI, observability semantics, daemon, or any other domain.

## Context

Slice 1 of `drift-detection` (`drift-detection`) shipped the `GraphLoader` + `ObservationSource` Protocol extraction (`cf7a052` on `origin/main`). Two follow-up slices were identified but explicitly deferred:

- **Slice 2** (THIS change) — "Unified JSONL rotation helper" for `drift_events.jsonl` + `metrics.jsonl`. ~80 LOC delta per `openspec/changes/drift-detection/explore.md` §4.2.
- **Slice 3** — "Per-finding `graph_unavailable` refinement + new counter + delta spec + new BDD scenarios" (depends on Slice 1, separate change, NOT this one).

The user's strategic framing per Engram #2058: ship Slice 1 first (DONE), then ship Slice 2 as a focused debt-closure PR, then approach Slice 3 with its own delta spec.

This explore phase maps (a) exactly which rotation code is duplicated, (b) what the helper's signature contract should be, (c) what tests stay green as the regression gate, and (d) what risks exist before the proposal phase locks scope.

---

## 1. Current state of JSONL rotation

### 1.1 The two duplicated helpers (the only target of Slice 2)

| Sink | File | Helper | Lines | Glob pattern | Env var (size) | Env var (age) | Default size | Default age |
|------|------|--------|-------|--------------|----------------|---------------|--------------|-------------|
| `drift_events.jsonl` | `src/flow_engineering/drift_event_log.py` | `_rotate_if_needed` + `_resolve_rotation_threshold_bytes` + `_resolve_max_age_days` | 196-254 | `drift_events.*.jsonl` | `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` | `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` | `ROTATE_BYTES_DEFAULT` (10 MB) | `ROTATE_AGE_DAYS_DEFAULT` (30 d) |
| `metrics.jsonl` | `src/flow_engineering/observability.py` | `_rotate_metrics_if_needed` + `_delete_stale_metrics_siblings` + `_resolve_metrics_rotation_threshold_bytes` + `_resolve_metrics_max_age_days` | 223-311 | `metrics.*.jsonl` | `FLOW_METRICS_LOG_MAX_BYTES` | `FLOW_METRICS_LOG_MAX_AGE_DAYS` | `METRICS_ROTATE_BYTES_DEFAULT` (10 MB) | `METRICS_ROTATE_AGE_DAYS_DEFAULT` (30 d) |

**Honest fact check on the prior explore.md**: `openspec/changes/drift-detection/explore.md` §2.8 claimed a "3rd copy of the pattern at `prompt_render_log.py:200`". **This is INCORRECT.** `prompt_render_log.py` (198 LOC total) has NO rotation helper — `PromptRenderLog.append` uses `_lock + path.open("a")` with no size check and no env-var hook. Slice 2 therefore covers EXACTLY 2 production copies, not 3. The discoverer noted this so future explore/proposal phases don't repeat the error.

### 1.2 Behaviour the duplicated helpers share (verbatim)

Both helpers implement the same algorithm:

1. Read the size threshold from env (default on missing/invalid).
2. If threshold > 0 and `path.exists()` and `path.stat().st_size >= threshold`:
   - Generate an ISO-no-colons stamp (`%Y%m%dT%H%M%SZ`).
   - Compute the rotated name (`<base>.<stamp>.jsonl`).
   - Rename `path` → rotated (best-effort; OSError swallowed).
3. If age threshold > 0:
   - Compute cutoff = now − (max_age_days × 86400).
   - Walk `path.parent.glob("<prefix>.*.jsonl")` (skipping `path` itself).
   - `unlink()` siblings whose `st_mtime < cutoff` (best-effort; OSError swallowed).

The only structural difference: `drift_event_log._rotate_if_needed` inlines the age-cleanup loop; `observability._rotate_metrics_if_needed` delegates to a separate `_delete_stale_metrics_siblings` helper. Slice 2 unifies both into a single function with the age loop inlined (matching `drift_event_log`'s current shape — the simplest form).

### 1.3 The 4 env-var indirection sites

Each helper has its own private env-var resolver:

```python
# drift_event_log.py (lines 196-217)
def _resolve_rotation_threshold_bytes() -> int:
    raw = os.environ.get("FLOW_DRIFT_EVENT_LOG_MAX_BYTES")
    if raw is None or raw == "":
        return ROTATE_BYTES_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return ROTATE_BYTES_DEFAULT
    return max(0, value)
# _resolve_max_age_days: same shape for FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS

# observability.py (lines 223-254)
def _resolve_metrics_rotation_threshold_bytes() -> int:
    # identical body except METRICS_LOG_MAX_BYTES_ENV + METRICS_ROTATE_BYTES_DEFAULT
# _resolve_metrics_max_age_days: same for FLOW_METRICS_LOG_MAX_AGE_DAYS
```

The 4 resolution functions (2 per module) are byte-for-byte clones modulo the env-var name + default constant. The unified helper MUST keep each call-site's env-var name as a parameter so the existing operator contract (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` → `drift_events`, `FLOW_METRICS_LOG_MAX_BYTES` → `metrics`) is preserved verbatim.

### 1.4 What stays UNCHANGED in Slice 2

- Operator contract: env-var names, default values, ISO-stamp format, glob prefix.
- Wire format: rotated files keep their `<prefix>.<ISO-stamp>.jsonl` naming.
- Public API: `DriftEventLog.append`, `observability.increment` — both call the unified helper internally.
- Lock semantics: `DriftEventLog._lock` wraps the rotation+append (D11 contract preserved).
- Test surface: `tests/unit/test_drift_event_log.py` (563 LOC, 5 rotation tests in `TestRotation`) + `tests/unit/test_observability.py` (372 LOC, `TestMetricsRotation` with 7 tests) stay green as the strict regression gate.
- BDD surface: `tests/bdd/req44_metrics_rotation.feature` (`metrics.jsonl` rotation, REQ-V1.2.1) + any BDD scenarios touching rotation thresholds keep passing.

### 1.5 What's NOT in scope (explicit deferrals)

- Slice 3 (per-finding `graph_unavailable` + new counter + delta spec + new BDD) — separate change.
- `prompt_render_log.py` rotation — the file has no rotation helper today; adding one would be a **new feature** (not refactor) and must be a separate change gated by an explicit operator requirement.
- OTel push (cross-repo) — out of scope.
- Cross-project drift federation — out of scope.
- `flow archive rotate` (the read-only archive preview at `src/flow_engineering/cli/rotation.py`) — **NOT a JSONL rotation**; it walks `openspec/changes/archive/` directories. Different concern. Explicitly out of scope.
- Test infrastructure changes (no new fixtures, no new conftest modules).

---

## 2. Architectural debt the duplication creates

### 2.1 The DRY violation (verbatim duplication of ~58 LOC)

`_rotate_if_needed` (29 LOC of executable code) + `_resolve_rotation_threshold_bytes` (10 LOC) + `_resolve_max_age_days` (10 LOC) in `drift_event_log.py` are duplicated 1-to-1 by `_rotate_metrics_if_needed` (24 LOC) + `_resolve_metrics_rotation_threshold_bytes` (15 LOC) + `_resolve_metrics_max_age_days` (15 LOC) + `_delete_stale_metrics_siblings` (28 LOC) in `observability.py`.

Extracting a single helper:

- Removes ~58 LOC of pure duplication.
- Eliminates 4 parallel env-var resolvers (2 per module) → 1 parameterized resolver.
- Makes the algorithm **visible in one place** for the next maintainer.
- Future JSONL sinks (e.g., `prompt_renders.jsonl` rotation when/if added) can opt-in by passing the new glob prefix.

### 2.2 Drift risk across the two copies

Without a shared helper, any fix to one helper (e.g., "ignore read-only FS on Windows network shares" → special-case `errno.EPERM`) must be manually ported to the other. The two REQ timelines confirm this is a real risk: REQ-V1.1.1 shipped drift-event rotation (v1.1.0) and REQ-V1.2.1 shipped metrics rotation (v1.2.0) — the gap is exactly the period where the two helpers could silently diverge.

A single helper makes divergence **structurally impossible** (only one implementation to maintain).

### 2.3 Reviewer + onboarding cost

Today a reviewer must read both `_rotate_if_needed` and `_rotate_metrics_if_needed` to verify they implement the same algorithm. The pattern is repeated in 4 unit test files (`TestRotation` + `TestMetricsRotation`) and 1 BDD feature (`req44_metrics_rotation.feature`). A unified helper reduces review surface to ~1 helper + 2 thin call-site wrappers + 1 shared test file.

### 2.4 What a unified helper does NOT solve (be honest)

- Does NOT add rotation to `prompt_render_log.py` — that is a feature, not a refactor.
- Does NOT change the ISO-stamp format, env-var names, or any operator contract.
- Does NOT enable async rotation (current code is synchronous per `append` call).
- Does NOT touch the CLI surface (`flow drift-events stats`, `flow metrics`) — those read the rotated siblings and stay unchanged.

---

## 3. Candidate approaches

### Approach A — Inline helper at each call site (NO REFACTOR)

**What**: Keep `_rotate_if_needed` in `drift_event_log.py` and `_rotate_metrics_if_needed` in `observability.py` exactly as they are today.

- **Pros**: No risk; zero LOC delta; no tests to rewrite.
- **Cons**: Continues ~58 LOC of duplication; drift risk is real; reviewer must read both copies; contradicts `openspec/changes/drift-detection/explore.md` §2.8 + the user's strategic framing.
- **Effort**: Zero.
- **Verdict**: REJECTED — does the same refactor work Slice 2 was created to ship.

### Approach B — Single shared helper in `src/flow_engineering/_jsonl_rotation.py` **[RECOMMENDED]**

**What**: Create a new module containing:

1. `def _rotate_jsonl_if_needed(path, *, glob_prefix, max_bytes_env, max_age_days_env, default_max_bytes, default_max_age_days) -> None` (the unified helper, ~30 LOC of executable code).
2. `def _resolve_jsonl_rotation_threshold_bytes(max_bytes_env, default_max_bytes) -> int` and `_resolve_jsonl_max_age_days(max_age_days_env, default_max_age_days) -> int` (~20 LOC total).
3. The module is private (leading underscore convention used elsewhere: `_shared.py`, `_resolve_*` helpers, `_DummyBackend` pre-Slice 1).

Then in `drift_event_log.py`:

```python
from flow_engineering._jsonl_rotation import _rotate_jsonl_if_needed
# Inside DriftEventLog.append (replacing the call at line 141):
_rotate_jsonl_if_needed(
    self.path,
    glob_prefix="drift_events",
    max_bytes_env="FLOW_DRIFT_EVENT_LOG_MAX_BYTES",
    max_age_days_env="FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS",
    default_max_bytes=ROTATE_BYTES_DEFAULT,
    default_max_age_days=ROTATE_AGE_DAYS_DEFAULT,
)
```

And in `observability.py`:

```python
from flow_engineering._jsonl_rotation import _rotate_jsonl_if_needed
# Inside increment (replacing the call at line 211):
_rotate_jsonl_if_needed(
    path,
    glob_prefix="metrics",
    max_bytes_env=METRICS_LOG_MAX_BYTES_ENV,
    max_age_days_env=METRICS_LOG_MAX_AGE_DAYS_ENV,
    default_max_bytes=METRICS_ROTATE_BYTES_DEFAULT,
    default_max_age_days=METRICS_ROTATE_AGE_DAYS_DEFAULT,
)
```

**Pros**:
- Pure deduplication: ~58 LOC of pure duplication removed.
- Single source of truth for the algorithm.
- Zero behavior change: env-var names, defaults, glob prefix, ISO-stamp format, lock semantics all preserved.
- Future-proofs: a 3rd JSONL sink (whenever `prompt_renders.jsonl` rotation is added) reuses the helper by passing a different `glob_prefix`.
- Minimal API surface (1 helper + 2 resolvers); no class hierarchy (Article IV satisfied — only 2 call-sites today).
- Keeps the existing public exports of `drift_event_log.py` and `observability.py` (`DriftEventLog`, `DriftEvent`, `DriftEventLogLegacyFormatError`, `ROTATE_*`, `METRICS_*`, `METRICS_LOG_*_ENV`) unchanged.

**Cons**:
- 1 new module imports in 2 places (cheap).
- 4 helper definitions (`_resolve_*`) collapse to 2 (parameterized). The "look" of `drift_event_log.py` slightly changes (the 3 env-var helpers disappear).
- Strict TDD: must write RED tests against the new helper covering both env-var schemes before the GREEN implementation lands.

**Effort**: Low (~80 LOC total: 30 prod helper + 20 prod resolvers + 30 test file).

**Risk**:
- **API risk**: None — public surface unchanged.
- **Test risk**: 12 existing rotation tests across `TestRotation` (5) + `TestMetricsRotation` (7) must stay green as the regression gate. 0 edits to those files (strict gate).
- **Spec risk**: Zero — pure refactor; REQ-V1.1.1 + REQ-V1.2.1 wording stays valid.

**Verdict**: RECOMMENDED.

### Approach C — `RotatingJsonlSink` class hierarchy

**What**: Define a `RotatingJsonlSink` base class with `append()`, `read_all()`, `rotate_if_needed()`. Subclass into `DriftEventSink` and `MetricsSink`.

- **Pros**: OOP-style; explicit class hierarchy; clean separation.
- **Cons**: Constitution Article IV ("Reject abstractions that don't earn their keep in the first 3 use cases"). Only 2 call-sites today → violates "2+ concrete cases demand them" clause (we have exactly 2, not 3+). Adds class boilerplate, `__init__` overrides, `__all__` exports. `DriftEventLog` and `observability.increment` have very different shapes (one is a class with state, the other is a module-level function) → a unifying class would distort one or both.
- **Effort**: Medium (class boilerplate + 2 refactors).
- **Verdict**: REJECTED — premature abstraction per Article IV.

### Approach D — Single shared helper + `RotatingJsonlSink` (Approach B + C combined)

- **Verdict**: REJECTED — stacks two abstractions; both violate Article IV in different ways.

---

## 4. Module + signature contract (frozen for proposal)

If the proposal locks Approach B, the helper signature MUST be:

```python
# src/flow_engineering/_jsonl_rotation.py

def _rotate_jsonl_if_needed(
    path: Path,
    *,
    glob_prefix: str,
    max_bytes_env: str,
    max_age_days_env: str,
    default_max_bytes: int,
    default_max_age_days: int,
) -> None:
    """Best-effort size + age rotation for any JSONL sink (REQ-V1.1.1 + REQ-V1.2.1).
    
    1. Read threshold + max_age from env via the parameterized resolver.
    2. If size >= threshold: rename path to f"{glob_prefix}.<stamp>.jsonl".
    3. If max_age > 0: walk siblings matching f"{glob_prefix}.*.jsonl" and
       unlink those older than the cutoff.
    4. All FS operations wrapped in try/except OSError (best-effort).
    """


def _resolve_jsonl_rotation_threshold_bytes(
    *, env: str, default: int
) -> int:
    """Read env var; default on missing/empty/invalid; clamp negative → 0."""


def _resolve_jsonl_max_age_days(
    *, env: str, default: int
) -> int:
    """Read env var; default on missing/empty/invalid; clamp negative → 0."""
```

**Design choices locked here** (pre-proposal, so the proposal phase can move fast):

- **No `**kwargs` sprawl** — 6 named params make the helper's contract grep-discoverable.
- **Private module name** (`_jsonl_rotation`) — leading-underscore signals "not in `__all__`"; matches `_DummyBackend` convention and the prior `_resolve_*` helpers.
- **No class** — function with keyword-only args satisfies Article IV (Anti-Abstraction).
- **No new public exports** — the helper is consumed internally by 2 modules only; no `__all__` churn downstream.
- **No new env vars** — preserves operator contract verbatim.
- **No new tests downstream** — the 12 existing rotation tests + BDD scenarios are the strict regression gate.
- **One new test file** — `tests/unit/test_jsonl_rotation.py` exercises the helper in isolation (RED-first per strict TDD).

---

## 5. Strict-TDD posture (locked)

Per `.specify/memory/constitution.md` Article III + `sdd-init/flow-engineering.md` (`strict_tdd: true`), every implementation task MUST have a preceding RED test task. The proposal phase will encode:

```
T1.1 RED  : tests/unit/test_jsonl_rotation.py — helper contract tests (no class, no kwargs sprawl)
T1.2 GREEN: src/flow_engineering/_jsonl_rotation.py — _rotate_jsonl_if_needed + 2 resolvers
T1.3 REFACTOR: extract _stamp_now() if shared by the 2 callers
T2.1 RED  : tests/unit/test_drift_event_log.py + test_observability.py — call-site REGRESSION ASSERTIONS
        (no edits to those files — pure regression gate; the existing 12 tests stay green)
T2.2 GREEN: drift_event_log.py — replace _rotate_if_needed definition with helper CALL
T2.3 GREEN: observability.py — replace _rotate_metrics_if_needed definition with helper CALL
T2.4 REFACTOR: drop the now-unused _resolve_rotation_threshold_bytes / _resolve_max_age_days /
        _resolve_metrics_rotation_threshold_bytes / _resolve_metrics_max_age_days from the
        respective modules (no behavior change; just unused-code removal)
T3.1 VERIFY: ruff + mypy clean on the 3 touched files; existing 12 rotation tests + 2 BDD
        scenarios green; new 4+ contract tests green
```

Total estimated LOC: ~30 (prod helper) + ~20 (prod resolvers) + ~50 (new test file) = ~100 LOC. Comfortably under the 400-LOC single-PR budget.

---

## 6. Risks (summary)

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| r1: Helper signature drift — env-var-name → constant mismatch between caller and helper. | Low | Pin signatures via strict type hints + RED tests in `tests/unit/test_jsonl_rotation.py` exercising BOTH env-var schemes (`FLOW_DRIFT_EVENT_LOG_*` AND `FLOW_METRICS_LOG_*`). The test asserts that `monkeypatch.setenv` on env var X only affects output for the matching glob_prefix. |
| r2: ISO-stamp format divergence between the two existing helpers (they're identical today; tomorrow one could change). | Low | Both helpers today use `datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")`. Extract to a private `_stamp_now()` function inside the helper module so both call-sites share it. Single source of truth for the stamp format. |
| r3: Strict TDD: tests must be written first. The unified helper MUST have tests that exercise BOTH env-var schemes. | Low (already institutionalized) | Proposal explicitly mandates `T1.1 RED` before `T1.2 GREEN`. The 4+ contract tests assert (a) default-on-missing, (b) default-on-invalid-int, (c) clamp-negative-to-0, (d) size-threshold triggers rename, (e) age-threshold deletes old siblings. |
| r4: prompt_render_log.py is intentionally NOT touched (no rotation in production today). Discovery should be flagged. | Low | This exploration records the fact. Future "add rotation to prompt_renders" change can adopt the same helper by adding a 3rd caller with `glob_prefix="prompt_renders"`. Out of scope for Slice 2. |
| r5: `flow archive rotate` (read-only archive preview at `src/flow_engineering/cli/rotation.py`) looks related but is NOT a JSONL rotation. Reviewer confusion risk. | Low | Document the boundary explicitly in the helper's docstring (mention "JSONL file rotation"; cross-reference `flow archive rotate` as a separate concern). |
| r6: Loss of the `_delete_stale_metrics_siblings` helper extraction (observability.py already extracted this for testability in REQ-V1.2.1; the unified helper inlines the age loop). | Low | 2 RED test cases from `TestMetricsRotation` (`test_deletes_rotated_siblings_older_than_max_age_days` + `test_age_cleanup_skips_when_max_age_days_is_zero`) directly assert the inlined age behavior. If the regression gate catches any diff, swap to keep `_delete_stale_siblings` as a private helper inside `_jsonl_rotation.py` (still inside the helper module). |
| r7: `DriftEventLog._lock` wraps `_rotate_if_needed` today (D11 contract). The unified helper MUST be called inside the same `with self._lock` block. | Low | The helper itself does NOT take a lock; it's a pure FS rotation. `DriftEventLog.append` keeps its `with self._lock:` wrapper and calls the helper inside it. `observability.increment` (single-process sink, no lock) calls the helper outside any lock — same as today. |
| r8: The unified helper lands a single new module name. Existing test imports (`from flow_engineering.drift_event_log import _resolve_rotation_threshold_bytes` etc.) — any test that imports the private resolvers breaks. | Low | Pre-flight check: `grep -rn "_resolve_rotation_threshold_bytes\| _resolve_metrics_rotation_threshold_bytes\| _resolve_max_age_days\| _resolve_metrics_max_age_days" tests/` (expected: 0 matches per Article IV private-helper convention). If any test imports a private resolver, refactor the test to use the public API instead. |
| r9: Token cost from the prior `explore.md` claiming a "3rd copy at `prompt_render_log.py:200`" — a future explore could re-import the wrong assertion. | Low | This file records the correction explicitly in §1.1 + §2.4. Engram `sdd/drift-jsonl-rotation-helper/explore` carries the same correction. |

---

## 7. Recommendation

**Lock Approach B: extract a single `_rotate_jsonl_if_needed` helper into `src/flow_engineering/_jsonl_rotation.py`. Have `drift_event_log.DriftEventLog.append` AND `observability.increment` delegate to it.**

Why:

1. **Lowest blast radius for highest debt-closure value.** ~58 LOC of verbatim duplication collapses to 1 helper + 2 thin call-site wrappers. Future JSONL sinks opt-in by passing a different `glob_prefix`.
2. **Fits the 400-LOC budget with massive headroom.** ~100 LOC total; ~80% under budget. No REQ-CLI-SPLIT-5 justification needed.
3. **Pure refactor — zero behavior change.** Operator contract (env vars, defaults, ISO format, glob prefix) preserved verbatim. 12 existing rotation tests + `req44_metrics_rotation.feature` BDD scenarios stay green.
4. **Satisfies Constitution Article IV (Anti-Abstraction).** Function with keyword-only args, not a class hierarchy — only 2 callers, no 3rd concrete use today.
5. **Strict TDD-ready.** 4+ RED contract tests + 12 existing regression tests + 2 existing BDD scenarios = clear pass/fail signal at every commit.
6. **Honest fact-check on prior `drift-detection/explore.md` §2.8**: the "3rd copy at `prompt_render_log.py:200`" claim is INCORRECT (the file has no rotation helper). This exploration records the correction so the proposal phase does not duplicate the error.
7. **Independent of Slice 1** — does not depend on `GraphLoader` / `ObservationSource` / typed exceptions. Could ship in parallel or after — no coupling.
8. **Author's note on the explore workflow**: `openspec/changes/drift-detection/apply-progress.md` and `tasks.md` are stale (per user kick-off prompt). Slice 1 is ACTUALLY DONE on `origin/main` (HEAD = `cf7a052`); the tasks checkboxes were not updated post-merge. Slice 2 lives in a separate change folder for auditability hygiene so the archive closure of Slice 1 is not entangled with Slice 2's proposal/spec/design/tasks.

### Why NOT ship all 3 slices at once

- Slice 3 (per-finding `graph_unavailable`) requires a delta spec + new BDD scenarios — a different change shape.
- Combining 3 slices dilutes review focus; reviewers see one big refactor PR instead of 3 focused ones.
- Slice 3 has a prerequisite on Slice 1's typed exception hierarchy — Slice 2 has no such prerequisite and CAN ship earlier (or in parallel).

---

## 8. Ready for proposal

**Yes.** Slice 2 is concrete, small (~100 LOC total), low-risk (zero public-API change, zero spec change, zero BDD scenario change), and creates the seam for any future JSONL sink that adds rotation.

The `proposal.md` will:

- Lock Approach B as the implementation strategy.
- Document the helper's signature contract verbatim from §4 above.
- Pin the strict-TDD posture with the T1.x / T2.x / T3.x task ordering from §5 above.
- Include the rollback plan (`git revert` the merge commit; helpers are additive).
- Note the fact-check correction on the prior `drift-detection/explore.md` §2.8 "3rd copy" claim (so future archives don't repeat the error).
- Include a "Size estimate" section (production: ~30 + 20 = ~50 LOC; test: ~50 LOC; total: ~100 LOC).
- Note the constitutional posture (Article VII: 100 LOC under 400 budget; Article IV: function not class).

---

## Relevant files

- `src/flow_engineering/drift_event_log.py:196-254` — `_resolve_rotation_threshold_bytes` + `_resolve_max_age_days` + `_rotate_if_needed` (TARGET of refactor).
- `src/flow_engineering/observability.py:223-311` — `_resolve_metrics_rotation_threshold_bytes` + `_resolve_metrics_max_age_days` + `_delete_stale_metrics_siblings` + `_rotate_metrics_if_needed` (TARGET of refactor).
- `src/flow_engineering/_jsonl_rotation.py` — NEW (helper module).
- `tests/unit/test_drift_event_log.py:428-560` — `TestRotation` (5 tests; strict regression gate; ZERO edits).
- `tests/unit/test_observability.py:182-372` — `TestMetricsRotation` (7 tests; strict regression gate; ZERO edits).
- `tests/unit/test_jsonl_rotation.py` — NEW (4+ RED contract tests covering both env-var schemes).
- `tests/bdd/req44_metrics_rotation.feature` — `metrics.jsonl` rotation BDD scenarios; regression gate.
- `openspec/changes/drift-detection/explore.md` §2.8 + §4.2 — Slice 2 sizing + debt rationale; **NOTE**: contains an INCORRECT claim about a "3rd copy" at `prompt_render_log.py:200`.
- `openspec/changes/drift-detection/proposal.md` — Slice 1 + Slice 2 + Slice 3 deferral map; Slice 2 sizing at §"Out of Scope".
- `src/flow_engineering/prompt_render_log.py` — confirmed NO rotation helper today (198 LOC); intentionally UNTOUCHED in Slice 2.
- `src/flow_engineering/cli/rotation.py` — the `flow archive rotate` read-only archive preview; **NOT** a JSONL rotation; explicitly out of scope.
- `.specify/memory/constitution.md` Article III (Strict TDD) + Article IV (Anti-Abstraction) + Article VII (400-LOC PR budget) — governance anchors.
- `sdd-init/flow-engineering.md` — `strict_tdd: true` marker; enforces RED-first gate.
