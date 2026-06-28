<!-- proposal.md: v0.9.0-hardening. Source: sdd-propose sub-agent. -->
# Proposal: v0.9.0-hardening

```yaml
status: success
confidence: high
open_questions_count: 0
chained_pr_recommendation: no
wall_time_estimate: ~3-4h end-to-end (single PR, 3 sub-batches of strict TDD per-task)
forecast_loc: 115 prod - 15 prod added = ~100 prod removed + ~140 test LOC delta
pr_split: single PR (~200 LOC delta; well under 400 LOC chained-PR threshold)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v0.9.0-hardening\proposal.md
next_recommended: sdd-tasks v0.9.0-hardening
strict_tdd: true
chain_strategy: not_applicable
```

## Intent

`flow-engineering v0.8.0` (change #8 `drift-hardening`, shipped 2026-06-27)
intentionally added **3 compat shims** — `Finding.from_legacy`,
`DriftReport.from_legacy`, `classify_binding_legacy` — as a **1-release
migration window** for v0.7.x callers per design D9 (per
`openspec/changes/archive/2026-06-27-drift-hardening/design.md:182-186`).
The CHANGELOG v0.8.0 entry (lines 43, 44, 46, 74) explicitly commits to
**shim removal in v0.9.0**. This change executes that commitment.

The 3 shims are well-bounded: production callers in `src/` are all
internal (zero external consumers); the soft-migration paths emit
`DeprecationWarning` per `warnings.warn(..., DeprecationWarning,
stacklevel=2)` pattern; and the only real scope ambiguity is the **W2
field-name fork** which the orchestrator pre-decided at **Option B
(accept deviation)**. Removal is mechanical (delete 3 functions + update
~25 test sites). The HEAD at `a2ce3f5` has 1232/1232 tests passing
(post prompt-registry PR#2b merge) — `flow-engineering` did NOT regress
in v0.8.0; this change is **debt closure, not feature work**.

**Why now**: prompt-registry PR#2b (change #7) shipped on 2026-06-28 per
Engram #263. The v0.8.0 shim window was a 1-release promise that
operators read in CHANGELOG before upgrading. Every release that ships
without closing that window erodes the operator trust the migration
guide is trying to build. The decision-reality-drift v0.7.x callers
have had a full release to migrate; **v0.9.0 closes the window**.

The headline deliverable is **3 compat shim deletions** (W1 + W1 +
W3 from `verify-report.md`) + **the W2 Drift note** documenting the
deviation + **`Finding.__post_init__` enforcement** as the W1
recommended fix. The secondary deliverable is the **0.8.1 → 0.9.0
version bump** mandated by the public API break.

## Context (from explore)

Explored in [`explore.md`](./explore.md). The exploration confirmed:

- **W1** (`Finding.from_legacy` + `DriftReport.from_legacy`):
  0 production callers; 8 test sites (3 `Finding.from_legacy` +
  3 `DriftReport.from_legacy` + 2 mixed) need test file edits; the
  shim itself is ~96 LOC across `decision_drift.py:77-117` (41 LOC) +
  `decision_drift.py:143-197` (55 LOC).
- **W2** (`DriftReport.graph_unavailable` + `unable_reason`): the
  implementation kept `graph_unavailable: bool` canonical + added
  `unable_reason: str | None` (NEW), opposite of design D2's intent to
  rename to `unable_to_verify`. **Option B (accept deviation)**
  pre-decided by orchestrator — no rename needed; just add a Drift note
  to `archive/2026-06-27-drift-hardening/design.md`.
- **W3** (`classify_binding_legacy` 3-arg wrapper): 0 production
  callers; 11 test sites (10 in `test_decision_drift.py` + 1 in
  `test_decision_drift_v080_migration.py`) migrate to 2-arg
  `classify_binding(ref, graph_nodes)`; the wrapper is ~19 LOC at
  `decision_drift.py:267-285`.

**Total scope**: ~115 prod LOC removed (or ~100 if
`Finding.__post_init__` is added), ~25 prod LOC added (~15 for
`__post_init__` + ~10 for the Drift note), ~140 test LOC removed
(deprecated shim test fixtures deleted). Single PR, well under the
400 LOC chained-PR threshold.

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `drift-hardening` verify-report #135 | W1 — `Finding.from_legacy` + `DriftReport.from_legacy` shims | REQ-V9.1 + REQ-V9.2 — delete classmethods; migrate 8 test sites; add `Finding.__post_init__` enforcement (recommended W1 fix line 139) |
| `drift-hardening` verify-report #135 | W2 — `graph_unavailable` field-name direction-flip (impl kept canonical + added `unable_reason` instead of renaming to `unable_to_verify` per D2) | REQ-V9.5 — Drift note in `archive/2026-06-27-drift-hardening/design.md` documenting the deviation (Option B); link to CHANGELOG v0.8.0 step 3 |
| `drift-hardening` verify-report #135 | W3 — `classify_binding_legacy` 3-arg wrapper | REQ-V9.3 — delete function; migrate 11 test sites from 3-arg to 2-arg `classify_binding`; delete the now-dead `_id_map` helper at `test_decision_drift.py:61-62` |
| `drift-hardening` verify-report #135 | W1 (optional) — add `Finding.__post_init__` str→int enforcement | REQ-V9.4 — `__post_init__` that raises `TypeError` on str inputs (hard break, no 1-release soft compat — the soft compat was the W1 shim itself which v0.9.0 removes) |

### Carry-forwards explicitly NOT touched by this change (deferred)

| Source | Item | Deferral target | Notes |
|---|---|---|---|
| `drift-hardening` verify-report S1 | `DriftEvent.decision_id: str` (JSONL wire format) vs `Finding.decision_id: int` (Python) consistency | v1.0 | JSONL wire format is read by 3rd-party consumers; not a v0.9.0 scope |
| `drift-hardening` verify-report W7 | `DriftEventLog` JSONL rotation hardening (`os.fsync` + atomic-write) | v1.1 | 10 MB rotation threshold already shipped in v0.8.0 (REQ-55); only the atomic-write hardening is deferred |
| `drift-hardening` verify-report S2 | `flow drift events` read-side CLI | v1.0 | Operators use `cat ~/.flow-engineering/drift_events.jsonl | jq` in v0.8.0/v0.9.0 |
| Tech debt residuals (post v0.8.0) | 4 ruff warnings + 13 mypy errors in `decision_drift.py` | v1.0 follow-up | Pre-existing; surfaced by verify-report W9; not blockers for v0.9.0 shim removal |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Single PR, per-task TDD, 3 sub-batches** (W1+W1 → W3 → docs/meta) | ~100 prod removed + ~140 test removed = ~240 net delta | Bundles the 3 compat shim removals into one logical migration event; single CHANGELOG entry; one migration guide for operators; small enough to keep review focus | Per-task TDD means more commits (12-15 vs 6-8 for per-group) | **RECOMMENDED** |
| B — Per-shim micro-changes (3 separate tiny PRs) | ~80 each = ~240 split | Smallest possible review unit (~80 LOC each) | 3 PRs of small churn; high overhead (CI ×3, review ×3, archive ×3); one migration guide split across 3 PRs is operator-hostile; the W2 Drift note has to ship before W1+W3 anyway | Rejected |
| C — Per-group TDD (3 sub-batches = 3 commits) | ~240 in 3 commits | Fewer commits (3 vs 12-15); faster review | Per-group TDD hides silent regressions: if W1 breaks a test site, the W3 commit can't bisect it; verify-report W4 precedent shows per-task discipline catches silent drift | Rejected |

**Recommendation: Approach A.** The compat shim removal is
high-risk (silent regressions if a test site is missed) — per-task
TDD discipline (RED → GREEN → REFACTOR per task, with the SHIM-still-
exists RED test before each delete) gives bisect-ability that
per-group TDD sacrifices for fewer commits. The 12-15 commit target
is manageable (each commit ≤30 LOC delta) and matches the
`work-unit-commits` skill precedent.

### Architecture (Approach A)

3 sub-batches of strict per-task TDD, 12-15 work-unit commits total:

**Sub-batch 1: W1 (`Finding.from_legacy` + `DriftReport.from_legacy`)**
- Task V9.1.1: Write RED test `test_finding_from_legacy_attribute_removed` —
  asserts `Finding.from_legacy` does NOT exist (AttributeError)
- Task V9.1.2: GREEN — delete `Finding.from_legacy` classmethod
  (`decision_drift.py:77-117`, ~41 LOC)
- Task V9.1.3: Migrate 2 direct `Finding(decision_id="<str>", ...)` sites
  in `test_decision_drift.py:196` + `test_cli_watch_drift.py:99` →
  `Finding(decision_id=<int>, ...)`
- Task V9.1.4: Delete 3 `Finding.from_legacy` test fixtures in
  `test_decision_drift_v080_migration.py:104-146` (test_finding_from_legacy_*)
- Task V9.1.5: Write RED test `test_drift_report_from_legacy_attribute_removed`
- Task V9.1.6: GREEN — delete `DriftReport.from_legacy` classmethod
  (`decision_drift.py:143-197`, ~55 LOC)
- Task V9.1.7: Migrate 8 direct `DriftReport(scanned_at=0.0, ...)` sites
  across `test_decision_drift.py:208/535`, `test_cli_watch_drift.py:200/253`,
  `test_daemon_drift_events.py:151/175/204/289` → use ISO 8601 string
  (e.g., `"2026-06-27T12:00:00Z"`)
- Task V9.1.8: Delete 3 `DriftReport.from_legacy` test fixtures in
  `test_decision_drift_v080_migration.py:165-206` (test_drift_report_from_legacy_*)
- Task V9.1.9: KEEP 3 canonical type-contract smoke tests in
  `test_decision_drift_v080_migration.py:76-218` (decision_id int +
  scanned_at str + unable_reason default)

**Sub-batch 2: W3 (`classify_binding_legacy`) + W1 enforcement**
- Task V9.2.1: Write RED test `test_classify_binding_legacy_attribute_removed`
  — asserts `classify_binding_legacy` does NOT exist
- Task V9.2.2: GREEN — delete `classify_binding_legacy` wrapper
  (`decision_drift.py:267-285`, ~19 LOC)
- Task V9.2.3: Migrate 10 call sites in `test_decision_drift.py:74/83/95/
  104/116/125/135/142/173/188` — drop `id_map = _id_map(...)` helper lines +
  change `classify_binding_legacy(binding, nodes, id_map)` →
  `classify_binding(binding, nodes)`
- Task V9.2.4: Delete `test_classify_binding_legacy_3arg_emits_deprecation_warning`
  at `test_decision_drift_v080_migration.py:243-255`
- Task V9.2.5: Delete the `_id_map` test helper at
  `test_decision_drift.py:61-62` (now dead; only used by the 10 migrated tests)
- Task V9.2.6 (W1 enforcement): Write RED test
  `test_finding_constructor_rejects_str_decision_id` — asserts
  `Finding(decision_id="42", ...)` raises `TypeError`
- Task V9.2.7 (W1 enforcement GREEN): Add `Finding.__post_init__` that
  raises `TypeError` if `decision_id` is not `int` (hard break; no soft
  compat — the W1 shim IS the soft compat, v0.9.0 removes it)
- Task V9.2.8: Clean up the 3 `# type: ignore` comments at
  `decision_drift.py:759/772/792` (the str-coercion sites become
  unnecessary once `Finding` rejects str)

**Sub-batch 3: Docs + meta + version bump**
- Task V9.3.1: Update `openspec/specs/decision-drift/spec.md` — replace
  the v0.8.0 migration note (lines 24-41) with the v0.9.0 final note:
  "Shims removed in v0.9.0. No migration path. `Finding.decision_id:
  int` required (TypeError on str); `DriftReport.scanned_at: str` ISO
  8601 UTC Z-suffixed required; `classify_binding(ref, graph_nodes)`
  2-arg required."
- Task V9.3.2: CHANGELOG v0.9.0 entry under `## [0.9.0] - 2026-06-XX` —
  `### Changed` (BREAKING): list the 3 deletions + the `__post_init__`
  enforcement; `### Removed`: `Finding.from_legacy`,
  `DriftReport.from_legacy`, `classify_binding_legacy`; `### Migration`:
  "Replace direct `Finding(str)` with `Finding(int)`; replace direct
  `DriftReport(scanned_at=0.0)` with `DriftReport(scanned_at="1970-01-01T00:00:00Z")`;
  replace `classify_binding_legacy(binding, nodes, id_map)` with
  `classify_binding(binding, nodes)`."
- Task V9.3.3: pyproject.toml version bump `0.8.1` → `0.9.0` (line 3)
- Task V9.3.4: Add Drift note to `archive/2026-06-27-drift-hardening/design.md`
  — 10 LOC append after line 491 documenting the W2 Option B decision
  + linking to CHANGELOG v0.8.0 step 3
- Task V9.3.5: Update the 6 SKILL.md runtime files (`sdd-{propose,
  design, tasks, apply, verify, archive}/SKILL.md`) at the v0.8.0 API
  note (per `verify-report.md` line 81 precedent) — remove the
  "1-release shim" qualifier; update to "shims removed in v0.9.0"

### CLI surface

**No CLI surface changes** — the public API is a Python library
(`decision_drift.Finding` + `decision_drift.DriftReport` +
`decision_drift.classify_binding`); removing the compat shims is a
type-system + soft-deprecation event, not a CLI change. The CLI
(`flow drift scan <change>`) continues to consume `scan_change()`
which returns `DriftReport` post-shim-removal; the dataclass field
contract is identical to v0.8.0 (just no `from_legacy` compat path).

### Code sketch — REQ-V9.1 + REQ-V9.2 (W1 deletion)

```python
# src/flow_engineering/decision_drift.py (MODIFY — ~96 LOC delta)
# REQ-V9.1 + REQ-V9.2 (W1): delete from_legacy classmethods.
# The Finding + DriftReport constructors become the ONLY canonical entry points.
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any  # for __post_init__ type narrowing


_LINE_PATTERN = re.compile(r"\d+")


class DriftClass(str, Enum):
    """Mutually-exclusive classification for a single binding."""
    STILL_VALID = "STILL_VALID"
    LABEL_DRIFT = "LABEL_DRIFT"
    STALE_LOCATION = "STALE_LOCATION"
    STALE_ID = "STALE_ID"
    OBSOLETE = "OBSOLETE"
    CONTRADICTED = "CONTRADICTED"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


@dataclass(frozen=True)
class Finding:
    """One per-binding classification result.

    v0.9.0 (REQ-V9.1 + REQ-V9.4 W1 enforcement):
    - ``decision_id`` is ``int``; ``str`` raises ``TypeError`` via
      :meth:`__post_init__` (hard break — no compat shim).
    """
    decision_id: int  # was: int (REQ-56 W8); str rejected via __post_init__
    binding: CodeRef
    drift_class: DriftClass
    detail: str

    def __post_init__(self) -> None:
        # REQ-V9.4 (W1 enforcement): hard break on str inputs.
        # No DeprecationWarning; no int() coercion; pure rejection.
        if not isinstance(self.decision_id, int) or isinstance(self.decision_id, bool):
            raise TypeError(
                f"Finding.decision_id must be int, got {type(self.decision_id).__name__}"
            )


@dataclass
class DriftReport:
    """Aggregate result for a full scan of one change.

    v0.9.0 (REQ-V9.2): no compat shim — ``scanned_at`` MUST be ``str``
    ISO 8601 UTC ``Z``-suffixed; legacy ``float`` epoch inputs raise
    ``TypeError`` (hard break — no compat shim).
    """
    change_name: str
    scanned_at: str  # ISO 8601 UTC Z-suffixed (REQ-56 W8)
    graph_mtime: str | None
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    graph_unavailable: bool = False
    unable_reason: str | None = None
```

### Code sketch — REQ-V9.3 (W3 deletion)

```python
# src/flow_engineering/decision_drift.py (MODIFY — ~19 LOC delta)
# REQ-V9.3 (W3): delete classify_binding_legacy 3-arg wrapper.
# The 2-arg classify_binding(ref, graph_nodes) is the only canonical entry point.


def classify_binding(
    ref: CodeRef,
    graph_nodes: dict[str, dict],
) -> DriftClass:
    """Classify a single ``CodeRef`` against the current graph state (REQ-9).

    v0.9.0 (REQ-V9.3 W3): 2-arg signature is the ONLY entry point. The
    v0.7.x 3-arg signature ``(binding, current_nodes, current_id_map)``
    is hard-removed — 3-arg callers get ``TypeError``.
    """
    if not graph_nodes:
        return DriftClass.UNABLE_TO_VERIFY
    current_id_map: dict[str, tuple[str, int, str]] = {
        node_id: (
            str(node.get("file") or node.get("source_file", "")),
            _parse_line(node.get("line") or node.get("source_location", 0)),
            str(node.get("label", node_id)),
        )
        for node_id, node in graph_nodes.items()
    }
    return _classify_with_id_map(ref, graph_nodes, current_id_map)
```

### Dependencies

- **NO new runtime dependencies.** The change is pure deletion + a
  small `__post_init__` enforcement (~10 LOC). Stdlib `dataclasses` +
  `warnings` + `datetime` already cover everything (the `_epoch_to_iso`
  helper stays as it's used by `scan_change` at lines 647, 817 — out of
  scope for removal but in scope for KEEP).
- The `_classify_with_id_map` internal helper stays (used by the 2-arg
  primary at line 245 — KEEP per explore).
- The `unable_to_verify` enum value + counter name + CLI exit-code 2
  wording all STAY (they describe the terminal STATE, not a field name;
  explore line 134-138 confirms).

### What changes (scope)

**In scope (single PR, 3 sub-batches)**:

- **Sub-batch 1 (W1, ~5 commits)**:
  - `src/flow_engineering/decision_drift.py` (MODIFY): DELETE lines
    77-117 (`Finding.from_legacy`, ~41 LOC) + DELETE lines 143-197
    (`DriftReport.from_legacy`, ~55 LOC).
  - `tests/unit/test_decision_drift.py` (MODIFY): migrate 1 str input
    + 2 float inputs → canonical int/ISO str (lines 196, 208, 535).
  - `tests/unit/test_cli_watch_drift.py` (MODIFY): migrate 1 str input +
    2 float inputs → canonical int/ISO str (lines 99, 200, 253).
  - `tests/unit/test_daemon_drift_events.py` (MODIFY): migrate 4 float
    inputs → canonical ISO str (lines 151, 175, 204, 289).
  - `tests/unit/test_decision_drift_v080_migration.py` (MODIFY):
    delete 3 `Finding.from_legacy` test fixtures (lines 104-146) +
    delete 3 `DriftReport.from_legacy` test fixtures (lines 165-206).
  - KEEP 3 canonical type-contract smokes in
    `test_decision_drift_v080_migration.py`: decision_id int (76-101) +
    scanned_at str (152-162) + unable_reason default (209-218).

- **Sub-batch 2 (W3 + W1 enforcement, ~5 commits)**:
  - `src/flow_engineering/decision_drift.py` (MODIFY): DELETE lines
    267-285 (`classify_binding_legacy`, ~19 LOC) + ADD
    `Finding.__post_init__` (~10 LOC, raises TypeError on str input) +
    CLEANUP 3 `# type: ignore` comments at lines 759/772/792 (now
    unreachable).
  - `tests/unit/test_decision_drift.py` (MODIFY): migrate 10 call
    sites (lines 74, 83, 95, 104, 116, 125, 135, 142, 173, 188) from
    `classify_binding_legacy(binding, nodes, id_map)` to
    `classify_binding(binding, nodes)` + delete `_id_map` helper at
    lines 61-62 (now dead).
  - `tests/unit/test_decision_drift_v080_migration.py` (MODIFY):
    delete `test_classify_binding_legacy_3arg_emits_deprecation_warning`
    at lines 243-255.

- **Sub-batch 3 (Docs + meta, ~3 commits)**:
  - `openspec/specs/decision-drift/spec.md` (MODIFY): replace v0.8.0
    migration note (lines 24-41) with v0.9.0 final note.
  - `CHANGELOG.md` (MODIFY): v0.9.0 entry under
    `## [0.9.0] - 2026-06-XX` with `### Changed` (BREAKING) +
    `### Removed` + `### Migration`.
  - `pyproject.toml` (MODIFY): `version = "0.9.0"` (line 3).
  - `openspec/changes/archive/2026-06-27-drift-hardening/design.md`
    (MODIFY): append Drift note (~10 LOC) documenting the W2 Option B
    decision + linking to CHANGELOG v0.8.0 step 3.
  - `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,
    archive}/SKILL.md` (MODIFY): update the v0.8.0 API note to remove
    the "1-release shim" qualifier (mirror `verify-report.md:81`
    precedent — `--allow-empty` commit pattern).

**Out of scope (deferred to v1.0+)**:
- `DriftEvent.decision_id: str` → int JSONL wire format change (S1)
- `DriftEventLog` JSONL rotation hardening (W7, deferred to v1.1)
- `flow drift events` CLI read-side command (S2)
- Tech debt (4 ruff + 13 mypy residuals, deferred to v1.0)
- `Finding.__post_init__` removal itself (v1.0 — but in v0.9.0 the
  shim is gone so the `__post_init__` IS the contract)

### Public API surface (MODIFIED)

```python
# src/flow_engineering/decision_drift.py — REMOVED in v0.9.0
Finding.from_legacy(...)   # REMOVED — was v0.8.0 1-release compat shim
DriftReport.from_legacy(...) # REMOVED — was v0.8.0 1-release compat shim
classify_binding_legacy(...) # REMOVED — was v0.8.0 1-release compat shim

# src/flow_engineering/decision_drift.py — MODIFIED in v0.9.0
class Finding:
    decision_id: int                              # HARD BREAK — str raises TypeError
    binding: CodeRef                              # via Finding.__post_init__
    drift_class: DriftClass
    detail: str
    def __post_init__(self) -> None:              # NEW — TypeError on non-int

class DriftReport:
    change_name: str
    scanned_at: str                               # HARD BREAK — float raises TypeError
    graph_mtime: str | None
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    graph_unavailable: bool = False               # canonical (per W2 Option B)
    unable_reason: str | None = None              # NEW in v0.8.0 (REQ-56 W2)

def classify_binding(ref: CodeRef,
                     graph_nodes: dict[str, dict]) -> DriftClass:
    # 2-arg is the ONLY entry point (W3 HARD BREAK)
    ...
```

### Breaking-change policy (REQ-V9.1 + REQ-V9.2 + REQ-V9.3 + REQ-V9.4)

The 3 compat shim deletions + the `__post_init__` enforcement ARE a
public API break. Mitigation:

- **CHANGELOG v0.9.0 `### Migration` section** lists the exact
  replacements for the 3 most common legacy call patterns.
- **6 SKILL.md runtime files** updated atomically (per
  `verify-report.md:81` precedent + `--allow-empty` commit pattern from
  drift-hardening T4.5.c commit `d5f2147`).
- **`openspec/specs/decision-drift/spec.md`** updated to the v0.9.0
  final note (no migration path — the shims are gone).
- **Version bump**: `pyproject.toml` `0.8.1` → `0.9.0`. CHANGELOG
  `## [0.9.0]` entry with `### Changed` (BREAKING) + `### Removed` +
  `### Migration`.

The project has 8 archived changes and **no third-party consumers**
per Engram #92 `sdd-init` (no PyPI package; `[project.optional-
dependencies] dev` is the only install entry). Hard break is
acceptable; the v0.8.0 → v0.9.0 migration window was a 1-release
operator commitment.

### Non-breaking guarantees

- `flow drift scan <change>` exit-code semantics unchanged (0 still-
  valid, 1 drift, 2 graph_unavailable, 3 usage error).
- `flow drift scan --format=<text|json>` default text + JSON output
  byte-identical (only the dataclass field types + the absence of
  shims change; the rendered text/JSON shape is unchanged).
- `flow drift daemon` JSONL append behavior unchanged
  (`record_drift_event()` still emits 1 line per non-STILL_VALID finding).
- All existing 1232 tests pass — verified locally before PR open.
- `_epoch_to_iso` helper unchanged (used by `scan_change` at lines 647,
  817; out of scope for v0.9.0).
- `unable_to_verify` enum value + counter name + CLI exit-code 2
  wording all unchanged (describe the STATE, not the field — explore
  line 134-138).

## Open Questions

**All resolved per explore + orchestrator pre-decisions.**

| # | Question | Decision | Resolution |
|---|---|---|---|
| OQ-1 | W2 fork: rename `graph_unavailable` → `unable_to_verify` (Option A) or accept deviation (Option B)? | **Option B** (pre-decided by orchestrator) | Accept the deviation: keep `graph_unavailable: bool` canonical + `unable_reason: str | None` as the new structured-diagnostics field. Add Drift note to `archive/2026-06-27-drift-hardening/design.md` documenting the decision. Zero production code changes beyond the W1/W3 deletions. **Reasoning**: CHANGELOG v0.8.0 line 45 already says "`graph_unavailable: bool` retained as the canonical field name" — operators have been told to migrate TO `graph_unavailable`. Re-renaming in v0.9.0 would be a third direction-change on the same field in one release cycle, which is operator-hostile. The Drift note preserves the audit trail. Cost: ~5 min for the Drift note (vs Option A's ~+1h for rename + 30 LOC migration + 8 test files touched). |
| OQ-2 | Add `Finding.__post_init__` enforcement (W1 recommended fix)? | **YES** | Adds ~10 LOC + 1 RED test. Hard break on str inputs (no `DeprecationWarning`, no `int()` coercion — the W1 shim IS the soft compat, v0.9.0 removes it). Prevents silent str→int coercion bugs from v0.7.x callers that miss the CHANGELOG migration guide. |
| OQ-3 | TDD strategy: per-task (12-15 commits) vs per-group (3 commits)? | **Per-task** | Compat shim removal is high-risk (silent regressions if a test site is missed). Per-task TDD gives bisect-ability that per-group TDD sacrifices for fewer commits. The 12-15 commit target is manageable (each commit ≤30 LOC delta) and matches the `work-unit-commits` skill precedent. |
| OQ-4 | Keep or delete `_id_map` test helper at `test_decision_drift.py:61-62`? | **DELETE** | Only used by the 10 tests being migrated to 2-arg `classify_binding`. After W3 migration, the helper has zero callers. Delete in the same W3 commit to avoid dead code. |
| OQ-5 | Rename `test_decision_drift_v080_migration.py` to `test_decision_drift_dataclass_contract.py` or inline the 3 remaining smokes? | **KEEP filename; update file purpose docstring** | The filename is informative (it's the "v0.8.0 migration test file"); after v0.9.0 the file holds 3 canonical type-contract smokes that serve as a regression gate against future dataclass shape changes. Update the file-level docstring (lines 1-5) to reflect the new purpose: "Canonical type-contract smokes for `decision_drift.Finding` + `DriftReport`. After v0.9.0 these are the only remaining tests in this file; the v0.8.0 migration shim tests (from_legacy, classify_binding_legacy) were deleted when their respective compat shims were removed." |
| OQ-6 | Add Drift note to `archive/2026-06-27-drift-hardening/design.md` (W2 deviation) — where in the file? | **Append after line 491** | The file already has a `## Drift: implementation deviations from design` section at line 446-491 documenting W1 + W2 + W3 deviations. The W2 Option B resolution is the FINAL state of the W2 deviation; appending a 10 LOC note at the end of that section (line 492) preserves the historical narrative + adds the resolution. |

**OQ count: 0 open** (all 6 pre-resolved per orchestrator + explore + this proposal).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/decision_drift.py` | MODIFY | REQ-V9.1 + REQ-V9.2 (DELETE `Finding.from_legacy` + `DriftReport.from_legacy`, ~96 LOC); REQ-V9.3 (DELETE `classify_binding_legacy`, ~19 LOC); REQ-V9.4 (ADD `Finding.__post_init__`, ~10 LOC); CLEANUP 3 `# type: ignore` comments at lines 759/772/792. Net ~105 prod LOC removed (or ~95 if `__post_init__` is added). |
| `tests/unit/test_decision_drift.py` | MODIFY | REQ-V9.1.3 (1 str input migrated to int at line 196); REQ-V9.1.7 (2 float inputs migrated to ISO str at lines 208, 535); REQ-V9.2.3 (10 call sites migrated from `classify_binding_legacy` to `classify_binding` at lines 74, 83, 95, 104, 116, 125, 135, 142, 173, 188); REQ-V9.2.5 (DELETE `_id_map` helper at lines 61-62). Net ~50 test LOC removed. |
| `tests/unit/test_cli_watch_drift.py` | MODIFY | REQ-V9.1.3 (1 str input migrated to int at line 99); REQ-V9.1.7 (2 float inputs migrated to ISO str at lines 200, 253). Net ~10 test LOC delta. |
| `tests/unit/test_daemon_drift_events.py` | MODIFY | REQ-V9.1.7 (4 float inputs migrated to ISO str at lines 151, 175, 204, 289). Net ~10 test LOC delta. |
| `tests/unit/test_decision_drift_v080_migration.py` | MODIFY | REQ-V9.1.4 (DELETE 3 `Finding.from_legacy` test fixtures at lines 104-146); REQ-V9.1.8 (DELETE 3 `DriftReport.from_legacy` test fixtures at lines 165-206); REQ-V9.2.4 (DELETE `test_classify_binding_legacy_3arg_emits_deprecation_warning` at lines 243-255); KEEP 3 canonical type-contract smokes at lines 76-218; UPDATE file-level docstring. Net ~80 test LOC removed. |
| `openspec/specs/decision-drift/spec.md` | MODIFY | REQ-V9.5 — replace v0.8.0 migration note (lines 24-41) with v0.9.0 final note. Net ~18 docs LOC delta. |
| `CHANGELOG.md` | MODIFY | REQ-V9.5 — v0.9.0 entry under `## [0.9.0] - 2026-06-XX` with `### Changed` (BREAKING) + `### Removed` + `### Migration`. Net ~30 docs LOC added. |
| `pyproject.toml` | MODIFY | REQ-V9.5 — `version = "0.9.0"` (line 3). Net +1/-1 LOC. |
| `openspec/changes/archive/2026-06-27-drift-hardening/design.md` | MODIFY | REQ-V9.5 (W2 Drift note) — append ~10 LOC after line 491 documenting the W2 Option B resolution + linking to CHANGELOG v0.8.0 step 3. |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | REQ-V9.5 — update the v0.8.0 API note to remove the "1-release shim" qualifier (mirror `verify-report.md:81` precedent). Net ~60 docs LOC delta across 6 files. |

## Capabilities

### Modified Capabilities

- `decision-drift` (REQ-9..16 + REQ-55..59): the v0.8.0 1-release
  compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`,
  `classify_binding_legacy`) are removed. `Finding.decision_id: int`
  is now a hard requirement (str raises `TypeError` via new
  `Finding.__post_init__`). `DriftReport.scanned_at: str` ISO 8601
  UTC Z-suffixed is now a hard requirement (float raises `TypeError`
  since there's no compat shim to coerce). `classify_binding(ref,
  graph_nodes)` 2-arg is the only canonical entry point (3-arg raises
  `TypeError`). `DriftReport.graph_unavailable: bool` stays canonical
  (per W2 Option B) + `unable_reason: str | None` stays canonical (NEW
  in v0.8.0). The capability spec at `openspec/specs/decision-drift/
  spec.md` is updated with the v0.9.0 final migration note.

**No new capabilities.** v0.9.0 is debt closure, not new feature
work.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | **Silent regression** if a test site that passes legacy values (str `decision_id`, float `scanned_at`, 3-arg `classify_binding_legacy`) is missed in the migration → the test suite still passes GREEN but production callers break at import time | MED | Per-task TDD with the "shim-still-exists" RED test before each delete (catches missing migrations via `AttributeError`); grep audit before PR open (`rg "Finding\\(" tests/` for str inputs, `rg "scanned_at=0\\.0"` for float inputs, `rg "classify_binding_legacy"` for 3-arg callers); smoke test the 5 most common production call patterns in `tests/integration/test_drift_full_flow.py` (if present) or via `pytest --collect-only` to confirm no module-level import errors |
| 2 | **Existing operators on v0.8.0 will hit `ImportError` or `TypeError`** after upgrading to v0.9.0 if they imported the compat shims | MED | CHANGELOG v0.9.0 `### Migration` section lists the exact replacements; the v0.8.0 → v0.9.0 window was a 1-release operator commitment per CHANGELOG v0.8.0 lines 43/44/46/74; the 6 SKILL.md runtime files are updated atomically so future SDD phases don't propagate the legacy shape; project has no third-party consumers per Engram #92 `sdd-init` (no PyPI package; `[project.optional-dependencies] dev` is the only install entry) |
| 3 | **13 mypy errors in `decision_drift.py` are PRE-existing tech debt** (per `verify-report.md` W9) — will surface as errors after shim removal (the `# type: ignore` comments at lines 759/772/792 become unnecessary + get removed; the underlying mypy errors may resurface in other locations) | LOW | Cleanup commit (V9.2.8) removes the 3 `# type: ignore` comments that the W1 enforcement makes unnecessary; the remaining 10 mypy errors are out of scope for v0.9.0 (carry-forward to v1.0 tech-debt follow-up); sdd-verify will report the residual count and gate the archive on a documented "10 mypy residuals carried forward to v1.0" decision |
| 4 | **W2 deviation (Option B) is technically a spec/implementation mismatch** — design.md D2 wanted `unable_to_verify` canonical but impl kept `graph_unavailable` canonical + added `unable_reason`. The Drift note documents the decision but operators grepping for `unable_to_verify` may find it absent (it's only present in the CHANGELOG v0.8.0 step 3 + the `unable_to_verify` enum value + the `drift_unable_to_verify_total` counter name + CLI exit-code 2 wording — NOT as a field name) | LOW | The Drift note in `archive/2026-06-27-drift-hardening/design.md` (REQ-V9.5) explicitly documents the deviation + links to CHANGELOG v0.8.0 step 3; the `unable_to_verify` enum value + counter name + exit-code wording remain stable (they describe the terminal STATE, not the field — explore line 134-138 confirms); the Drift note is appended to the existing `## Drift: implementation deviations from design` section (line 446-491) which already documents W1 + W2 + W3 deviations, so operators reading the section get the full context |

## Rollback Plan

All artifacts are deletions or doc-only changes. Single revert of the
merge commit restores pre-change state:

- `src/flow_engineering/decision_drift.py` MODIFIED — the 3 compat
  shims (`Finding.from_legacy`, `DriftReport.from_legacy`,
  `classify_binding_legacy`) are restored; `Finding.__post_init__` is
  removed; the 3 `# type: ignore` comments at lines 759/772/792 are
  re-added. Reverting restores the v0.8.0 compat surface.
- `tests/unit/test_decision_drift.py` + `test_cli_watch_drift.py` +
  `test_daemon_drift_events.py` + `test_decision_drift_v080_migration.py`
  MODIFIED — the migrated test sites revert to passing legacy values;
  the 7 deleted test fixtures (3 `Finding.from_legacy` + 3
  `DriftReport.from_legacy` + 1 `classify_binding_legacy`) are
  restored. Reverting restores the v0.8.0 test surface.
- `openspec/specs/decision-drift/spec.md` MODIFIED — the v0.9.0 final
  migration note reverts to the v0.8.0 migration note (with the
  1-release shim qualifier).
- `CHANGELOG.md` + `pyproject.toml` revert cleanly to v0.8.1.
- 6 SKILL.md runtime files revert cleanly to the v0.8.0 API note
  (with the "1-release shim" qualifier).
- `archive/2026-06-27-drift-hardening/design.md` MODIFIED — the Drift
  note is removed (no production code change).

To restore the pre-v0.9.0 install: `git revert <PR-merge>`. The
dataclass field types revert to the v0.8.0 shape (int/str, no
`__post_init__`); the 3 compat shims are back; the 7 deleted test
fixtures are back. Zero data loss; zero user state touched.

## Dependencies

- **None new.** The change is pure deletion + a small `__post_init__`
  enforcement (~10 LOC). Stdlib `dataclasses` + `warnings` +
  `datetime` already cover everything.
- `_epoch_to_iso` helper stays (used by `scan_change` at lines 647,
  817; out of scope for v0.9.0 removal).
- `_classify_with_id_map` internal helper stays (used by the 2-arg
  primary at line 245; out of scope for v0.9.0 removal).
- `drift-hardening` (shipped v0.8.0) — the v0.8.0 1-release compat
  shims are the target of this change.
- `decision-reality-drift` (shipped v0.3.0) — the original
  `Finding`/`DriftReport`/`classify_binding` API that the v0.8.0
  migration broke + the v0.8.0 shims softened + this change
  hard-breaks.

## Proposed PR Strategy

**Single PR** for v0.9.0. Total scope: ~100 prod LOC removed + ~140
test LOC removed = ~240 net delta. Well under the 400 LOC chained-PR
threshold. The 3 compat shims are thematically unified (all are v0.8.0
1-release deprecation paths with the same removal deadline); splitting
into chained PRs would force each PR to re-import the legacy shape
context that the previous PR just deleted — needless friction.

**Sub-batches** within the single PR (12-15 commits total, per
`work-unit-commits` skill — each commit ≤30 LOC delta):

- Sub-batch 1 (W1, 5 commits): RED → GREEN → migrate test sites →
  RED → GREEN → migrate test sites
- Sub-batch 2 (W3 + W1 enforcement, 5 commits): RED → GREEN → migrate
  test sites → RED → GREEN (`__post_init__`) → cleanup
- Sub-batch 3 (Docs + meta, 3 commits): spec.md + CHANGELOG + version
  bump (atomic per the drift-hardening `--allow-empty` precedent)

**Commit template** (mirror drift-hardening precedent):

```
chore(v0.9.0-hardening): REQ-V9.<N>.<M> — <concise description>

- RED test: <test file>:<line>
- GREEN impl: <impl file>:<line range>
- Test sites migrated: <count>
- Risk: <low|med|high>

Refs: openspec/changes/v0.9.0-hardening/proposal.md#step-N
```

## Wall Time Estimate

**~3-4 hours end-to-end** (single PR, 3 sub-batches of strict
per-task TDD):

| Sub-batch | Time | Tasks | Commits |
|---|---|---|---|
| Sub-batch 1 (W1) | ~75 min | 9 tasks (V9.1.1..V9.1.9) | 5 commits |
| Sub-batch 2 (W3 + W1 enforcement) | ~60 min | 8 tasks (V9.2.1..V9.2.8) | 5 commits |
| Sub-batch 3 (Docs + meta) | ~30 min | 5 tasks (V9.3.1..V9.3.5) | 3 commits |
| Verify + archive | ~30 min | `sdd-verify` + `sdd-archive` | 1 merge commit |
| **TOTAL** | **~3-4 hours** | **22 tasks** | **~14 commits** |

**Per-task breakdown**:
- Sub-batch 1: ~8 min/task × 9 tasks = ~72 min
- Sub-batch 2: ~7.5 min/task × 8 tasks = ~60 min
- Sub-batch 3: ~6 min/task × 5 tasks = ~30 min
- Verify: 1 `pytest` run + 1 `ruff` run + 1 `mypy` run + 1 `sdd-verify`
  pass + 1 `sdd-archive` pass = ~30 min

## Carry-forwards (NOT in v0.9.0)

### Deferred to v1.0 (post v0.9.0)

- **`flow drift events` CLI read-side command** (verify-report S2):
  Operators use `cat ~/.flow-engineering/drift_events.jsonl | jq` in
  v0.8.0/v0.9.0; the read-side UI is a v1.0 follow-up.
- **`DriftEvent.decision_id: str` → `int` JSONL wire format change**
  (verify-report S1): JSONL is consumed by 3rd-party tools (jq scripts,
  dashboards); not a v0.9.0 scope. The Python `Finding.decision_id: int`
  + JSONL `DriftEvent.decision_id: str` inconsistency is documented in
  v0.9.0 CHANGELOG Notes for operator awareness.
- **Tech debt residuals** (post v0.9.0): 4 ruff warnings + 13 mypy
  errors in `decision_drift.py` (the 3 `# type: ignore` cleanup at
  V9.2.8 reduces by 3; 10 residuals remain). Deferred to v1.0 tech-
  debt follow-up.

### Deferred to v1.1

- **`DriftEventLog` JSONL rotation hardening** (verify-report W7):
  The 10 MB rotation threshold already shipped in v0.8.0 (REQ-55); the
  `os.fsync` atomic-write hardening + `FLOW_DRIFT_EVENT_LOG_MAX_BYTES`
  env var are deferred to v1.1 alongside the `FLOW_METRICS_MAX_BYTES`
  metrics rotation follow-up.
- **REQ-51/52/53** (drift-events-dashboard CLI surface): explicitly
  deferred from v0.8.0 per verify-report S2; carry-forward to v1.1.

### Already RESOLVED (verified closed in v0.8.0)

| Source | Item | Resolution evidence |
|---|---|---|
| `drift-hardening` apply-progress/merged.md line 8 | Strict TDD was ON for v0.8.0 | Engram #243 |
| `drift-hardening` verify-report #135 | W1 + W2 + W3 — compat shims added with 1-release removal commitment | CHANGELOG v0.8.0 lines 43/44/46/74 |

## Success Criteria

- [ ] `Finding.from_legacy` attribute is removed; accessing it raises
      `AttributeError` (REQ-V9.1, 1 RED + 1 GREEN test)
- [ ] `DriftReport.from_legacy` attribute is removed; accessing it
      raises `AttributeError` (REQ-V9.2, 1 RED + 1 GREEN test)
- [ ] `classify_binding_legacy` function is removed; calling it raises
      `NameError` (REQ-V9.3, 1 RED + 1 GREEN test)
- [ ] `Finding(decision_id="42", ...)` raises `TypeError` via new
      `Finding.__post_init__` (REQ-V9.4, 1 RED + 1 GREEN test)
- [ ] `Finding(decision_id=42, ...)` constructs successfully
      (REQ-V9.4, 1 type-contract smoke — KEPT from v0.8.0)
- [ ] `DriftReport(scanned_at="2026-06-27T12:00:00Z", ...)` constructs
      successfully (REQ-V9.2, 1 type-contract smoke — KEPT from v0.8.0)
- [ ] `DriftReport(scanned_at=0.0, ...)` raises `TypeError` (no compat
      shim to coerce) (REQ-V9.2, 1 RED + 1 GREEN test)
- [ ] `classify_binding(ref, graph_nodes)` 2-arg works for all 10
      migrated test sites (REQ-V9.3, 10 unit tests migrated)
- [ ] All existing 1232 tests pass (no regressions from shim removal)
      (1 `pytest` run)
- [ ] `ruff check` clean on changed files (1 `ruff` run)
- [ ] `mypy src/flow_engineering/decision_drift.py` shows ≤10 errors
      (down from 13 in v0.8.0; the 3 `# type: ignore` cleanup at
      V9.2.8 removes 3) (1 `mypy` run)
- [ ] `openspec/specs/decision-drift/spec.md` v0.9.0 migration note
      replaces the v0.8.0 note (no `from_legacy` / `classify_binding_legacy`
      references) (REQ-V9.5, 1 grep audit)
- [ ] CHANGELOG v0.9.0 entry under `## [0.9.0] - 2026-06-XX` lists
      all 3 deletions + the `__post_init__` enforcement + the
      migration steps (REQ-V9.5, 1 manual review)
- [ ] `pyproject.toml` `version = "0.9.0"` (REQ-V9.5, 1 manual review)
- [ ] Drift note appended to
      `archive/2026-06-27-drift-hardening/design.md` documenting the
      W2 Option B resolution (REQ-V9.5, 1 manual review)
- [ ] 6 SKILL.md runtime files updated atomically — v0.8.0 "1-release
      shim" qualifier removed (REQ-V9.5, 1 grep audit across
      `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,
      verify,archive}/SKILL.md`)
- [ ] Strict TDD evidence: every public deletion has RED→GREEN→REFACTOR
      history in commit log; per-commit work-unit splits per
      `work-unit-commits` skill (12-15 commits each ≤30 LOC delta)
- [ ] Drift detector (REQ-9..16) behavior unchanged for end users —
      the public API break is internal; CLI output + exit codes +
      JSONL append behavior byte-identical to v0.8.0

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Unrelated layer | No conflict |
| `decision-reality-drift` (shipped v0.3.0) | The original `Finding`/`DriftReport`/`classify_binding` API that the v0.8.0 migration broke + the v0.8.0 shims softened + this change hard-breaks | **MIGRATION**: hard break with explicit CHANGELOG migration steps |
| `vector-semantic-search` (shipped v0.4.0) | Unrelated layer | No conflict |
| `cross-project-federation` (shipped v0.5.0) | Unrelated layer | No conflict |
| `graph-snapshots` (shipped v0.6.0) | Unrelated layer | No conflict |
| `observability` (shipped v0.7.0) | The `record_drift_summary()` helper + `drift_unable_to_verify_total` counter name stay unchanged (counter name describes the STATE, not the field — explore line 134-138) | Compatible |
| `prompt-registry` (shipped v0.8.0 PR#1 + PR#2) | Unrelated layer; PROMPT-REGISTRY PR#2b shipped on 2026-06-28 per Engram #263 — REQ-49 + REQ-50 baseline stable | No conflict |
| `drift-hardening` (shipped v0.8.0) | The v0.8.0 1-release compat shims are the target of this change | **MIGRATION**: shim removal + Drift note append to design.md |

**Unblocks**: 3 documented carry-forwards closed (W1 + W2 + W3 from
`drift-hardening` verify-report); v0.9.0 release ships with public
API break documented + migration guide; the v0.8.0 1-release operator
commitment is honored; the W2 drift-deviation is officially
documented with the Option B resolution.

**Constrains**: any future change that touches the `Finding` /
`DriftReport` / `classify_binding` signature MUST NOT re-introduce
soft-compat shims (the v0.9.0 design is a hard break with explicit
type enforcement via `Finding.__post_init__`); the `drift_events.jsonl`
JSONL wire format is locked from v0.8.0 (no v0.9.0 changes);
`graph_unavailable: bool` stays canonical (W2 Option B — the field
name is LOCKED unless a future change ships a v1.0 migration guide).

## Artifacts

- `openspec/changes/v0.9.0-hardening/explore.md` (exploration phase,
  pre-existing)
- `openspec/changes/v0.9.0-hardening/proposal.md` (this file)
- Engram mirror: topic_key `sdd/v0.9.0-hardening/proposal`, type
  `architecture`, scope `project`

## Next Step

`sdd-design v0.9.0-hardening` — produce `design.md` with D1..D6
architecture decisions (subset of the drift-hardening D1..D12, scoped
to the v0.9.0 compat shim removal context) + Open Questions table
(0 open per this proposal §OQ) + `code_refs` block.

Loop mode continues from here: orchestrator will invoke
`sdd-spec v0.9.0-hardening` → `sdd-tasks v0.9.0-hardening` →
`sdd-apply v0.9.0-hardening` → `sdd-verify v0.9.0-hardening` →
`sdd-archive v0.9.0-hardening` in sequence.