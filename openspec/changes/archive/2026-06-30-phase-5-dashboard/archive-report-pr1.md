# Archive Report (Partial) — phase-5-dashboard PR1

> **Archive type**: **PARTIAL** — PR1 of 3 chained PRs (Option B, feature-branch-chain).
> **Final archive timing**: after PR3 lands on tracker `phase-5-dashboard`. At that point this file is replaced by `archive-report.md` and the change folder moves to `openspec/changes/archive/2026-06-30-phase-5-dashboard/`.
> **Project**: flow-engineering v1.2.0
> **Mode**: hybrid (this file on disk + mirror to Engram observation topic `sdd/phase-5-dashboard/archive-report-pr1`).

---

## Status

**PR1 CLOSED — success.** PR2 and PR3 remain pending.

| Field | Value |
|---|---|
| Change | `phase-5-dashboard` |
| PR | **PR1** of 3 (data layer only) |
| Verdict | PASS WITH WARNINGS (1 WARNING, 2 SUGGESTIONS, 0 CRITICAL) |
| Verify report | [`verify-report.md`](./verify-report.md) (262 LF) |
| Apply report | Engram `#545` (`sdd/phase-5-dashboard/apply-progress-pr1`) |
| Verify memory | Engram `#547` (`sdd/phase-5-dashboard/verify-report-pr1`) |
| Branch carrying PR1 | `phase-5-dashboard-pr1` at commit `6651add` |
| Tracker branch | `phase-5-dashboard` at commit `b9da84b` (spec chore carried separately) |
| Main HEAD | `6133e70` |
| Strategy | feature-branch-chain (per Pattern #542, Option B locked at tasks #543) |

---

## PR1 Change Summary

PR1 ships the **data layer only** of the read-only Rich dashboard. Two files committed, **498 insertions**, **0 deletions**.

| File | LOC | Status |
|---|---|---|
| `src/flow_engineering/dashboard.py` | **179** | NEW |
| `tests/unit/test_dashboard.py` | **319** | NEW (13 strict-TDD tests across 4 test classes) |

### Public surface shipped

- `_run_subprocess_json(cmd, *, timeout=10)` — internal helper; `subprocess.run(..., capture_output=True, text=True, encoding="utf-8", check=False)` with three specific failure modes.
- `DashboardSubprocessError(RuntimeError)` — non-zero exit / `TimeoutExpired`.
- `DashboardParseError(ValueError)` — JSON decode failure / non-dict top-level.
- `DashboardFlowNotFoundError(FileNotFoundError)` — `flow` binary missing on PATH (subclasses `FileNotFoundError` so existing `OSError` handlers still catch it).
- `fetch_project_list(*, flow_bin="flow")` — DS1: `flow projects ls --json`.
- `fetch_status_summary(*, flow_bin="flow")` — DS2: `flow workspace status --json`.
- `fetch_archived_projects()` — DS5: direct `load_registry()` read with graceful missing-file → empty list.

### Deliberate non-shipping (deferred to PR2 / PR3)

| Not in PR1 | Lands in | Why |
|---|---|---|
| Click `flow workspace dashboard` integration | **PR3** (Wave 5, task T12) | Read-only data layer must integrate before CLI wiring |
| Rich rendering (4 sections: Header/Needs/Archived/Footer + Composer) | **PR2** (Wave 4, tasks T7–T11) | Pure functions (T4–T6) come first; renderers consume them |
| `filter_by_rules` (`--filter RULES`) | **PR2** (Wave 3, task T4) | Logic layer |
| `sort_projects` (`--sort FIELD`) | **PR2** (Wave 3, task T5) | Logic layer |
| `color_code` (red/yellow/green thresholds) | **PR2** (Wave 3, task T6) | Logic layer |
| `--no-color` flag handling | **PR3** (Wave 5, task T12) | CLI integration point |
| Color-coded row styles | **PR2** (Wave 4, task T8) | Renderer level |
| `verify-checks.sh` script | **PR3** (Wave 6, task T13) | One-shot infra; ships with the CLI registration PR |
| Full-suite 1513 + 24 = 1537 AC walkthrough | **PR3** (Wave 7, tasks T14 + T15) | Final consolidation |

---

## PR1 Verification

### 13 ACs — PR1 subset (7 PASSED in PR1, 6 DEFERRED to PR2/PR3)

| AC | Description | Scope | Result |
|---|---|---|---|
| **AC3** | Subprocess `flow projects ls --json` | **PR1** | **PASS** |
| **AC4** | Subprocess `flow workspace status --json` | **PR1** | **PASS** |
| **AC5** | Registry read (missing → empty list) | **PR1** | **PASS** |
| **AC11** | Zero new runtime deps | **PR1** | **PASS** |
| **AC12** | AC9 byte-identical guard preserved | **PR1** | **PASS** |
| **AC13** | Full suite 1526/1526 | **PR1** | **PASS** |
| **AC15** | `flow workspace status` text unchanged | **PR1** | **PASS** |
| AC1 | `flow workspace dashboard` registered | PR3 | DEFERRED |
| AC2 | Default output = Rich table | PR2 | DEFERRED |
| AC6 | Filter logic | PR2 | DEFERRED |
| AC7 | Sort logic | PR2 | DEFERRED |
| AC8 | `--no-color` flag | PR3 | DEFERRED |
| AC9 | Color coding | PR2 | DEFERRED |
| AC10 | Rich rendering (4 sections) | PR2 | DEFERRED |
| AC14 | `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` resolved | TRACKER (`b9da84b`) | RESOLVED-AT-TRACKER (not in PR1) |

**PR1 ACs**: **7/7 PASS**. See `verify-report.md` §"13 ACs Verification" for evidence rows.

### 8 verify checks — all PASS on tracker `phase-5-dashboard` @ `b9da84b`

| # | Description | Result |
|---|---|---|
| 1 | Every root REQ has exactly one `Source:` line (12/12) | **PASS** |
| 2 | Every `Source:` path exists on disk (4/4 unique) | **PASS** |
| 3 | Every cited REQ-ID exists in the cited delta spec (28/28) | **PASS** |
| 4 | §6 Cross-Impact mentions `flow-where-cross-project-capability-merge` (4 matches) | **PASS** |
| 5 | §7 Future Changes mentions `workspace-dashboard` (11 matches) | **PASS** |
| 6 | §8 Drift Detection footer present (2 matches) | **PASS** |
| 7 | "Family index, not canonical source" callout in first 10 lines (L4) | **PASS** |
| 8 (NEW) | Every dashboard REQ `Source:` points to `phase-5-dashboard` delta spec (6/6) | **PASS** |

### Baseline preservation

| Gate | Result |
|---|---|
| Full suite `uv run --frozen pytest -q` | **1526/1526** (1513 baseline + 13 new) in 68.20s |
| AC9 byte-identical guard (`test_flow_projects_ls_json_byte_identical_envelope`) | PASS |
| `flow workspace status` text tests (10 cases) | PASS |
| Type check (`mypy src/`) | Clean — no issues in 33 source files |
| Ruff (new files only) | Clean |
| Ruff (whole project) | 3 pre-existing OOS errors at exact expected locations (`cli.py:682`, `test_cli_where_cross_project.py:33`, `test_cli_where_cross_project.py:295`) |

### PR1 commit hygiene + guards

| Field | Expected | Actual | Result |
|---|---|---|---|
| Commit SHA | `6651add` | `6651addca7f3d55612830d10c157edff3d76d877` | PASS |
| Branch | `phase-5-dashboard-pr1` | `phase-5-dashboard-pr1` | PASS |
| Commit subject | `feat(dashboard): …` | `feat(dashboard): PR1 — subprocess wrappers + fetchers (Wave 1+2)` | PASS |
| AI attribution | absent | rg on `co-authored\|anthropic\|gpt\|gemini\|opencode\|generated\|automatically` → 0 matches | PASS |
| Files in commit | 2 | 2 (via `git show --name-only`) | PASS |
| Insertions | ~498 | 498 | PASS |
| **LOC guard** (`dashboard.py` < 250) | < 250 | **179** | PASS |
| **cli.py guard** | 0 modifications | `git diff main..HEAD -- src/flow_engineering/cli.py` → empty | PASS |
| **pyproject.toml guard** | untouched | no diff | PASS |
| **registry.py guard** | untouched | no diff (referenced only, never modified) | PASS |
| `--json` flag guard (Pattern #538) | not added on dashboard | n/a (CLI not wired) | PASS |
| `rich` promotion guard | not promoted to direct dep | transitive via `uv.lock:1215` | PASS |
| `v1.1-followups/` guard | untouched | untracked, never tracked | PASS |

---

## PR1 SDD Cycle Wall-Clock

End-to-end Phase 5 arc PR1 sub-cycle (measured from session timestamps, June 30 2026):

| Phase | Duration |
|---|---|
| sdd-explore (5 alternatives surfaced) | ~25 min |
| sdd-propose (Approach E locked) | ~20 min |
| sdd-spec (placeholder → 6 root REQs + 7 delta-internal REQs) | ~28 min |
| sdd-design (641 LF, 7 TDD waves, 8 verify checks, 3 split options) | ~25 min |
| sdd-tasks (15 tasks across 7 waves, Option B locked) | ~25 min |
| sdd-apply PR1 (Wave 1+2, strict TDD ON) | ~25 min |
| sdd-verify PR1 (7 ACs + 8 checks + baseline gates) | ~8 min |
| **sdd-archive PR1 (this report)** | ~10 min |
| **PR1 subtotal** | **~165 min (~2.75h)** |

PR1 is the **fastest phase in the workspace-intelligence arc** (which had previously averaged ~50 min per phase for the four prior cleanup cycles).

---

## PR1 Risks and Carry-Forward

### Architecture-level (settled, documented for traceability)

1. **Spec chore carried on tracker separately from PR1.** Pre-existing uncommitted `workspace/spec.md` modifications (the 6 dashboard REQs from sdd-spec phase) were committed as a SEPARATE chore `b9da84b` on tracker `phase-5-dashboard`, NOT included in PR1. This honors Pattern #546 ("Spec changes need separate commit before PR chain") and was explicitly authorized by the user at apply time. PR1 commit contains ONLY the two new code files.
2. **PR1 branched off main, not off tracker.** The user-locked `feature-branch-chain` setup has PR1 as the first child of `main` (parent `6133e70`). The tracker accumulates the spec chore and the future merged integration. PR1 → tracker merge at user-merge time requires a 3-way merge. The merge is clean (no overlap: spec.md lives on tracker; dashboard.py + test_dashboard.py live on PR1).
3. **PR1 commit message body says "stacked-to-main" but the chain strategy is `feature-branch-chain`.** Cosmetic wording inaccuracy in the message body. The branch topology and review budget are correct; only the message is mislabeled. **No amend** (user-locked: "no tocar commits verdes por estética").
4. **AC14 (`REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` resolution) verified on tracker, not in PR1.** PR1 itself is branched off main and does not contain the placeholder resolution. The placeholder resolution lands via the tracker chore `b9da84b`. PR description (when the user opens the PR on the tracker) should mention this so reviewers don't get confused.

### Design-level carry-overs (downstream PRs, NOT blocking PR1)

- **R1**: §3 row 5 + §5 row "tui (future)" + §7 row #2 cleanup is still deferred. PR1's `workspace/spec.md` on tracker preserves these byte-identical per design §10 (Out of Scope).
- **R2**: PR3 introduces the actual `--json`-less CLI registration; no `--json` flag must be added to `flow workspace dashboard` (Pattern #538 — one identity per command).
- **R3**: `rich` promotion to direct dep is zero-cost but must NOT happen in PR1 (preserves "no new runtime deps" guard); deferred to PR3 if needed at all.

### Deviations from design (intentional, documented)

- Design §2.4 specified `DashboardBinaryNotFoundError`; implementation uses `DashboardFlowNotFoundError` per user Batch C #16. The class subclasses `FileNotFoundError` so existing `OSError` handlers still catch it (design intent preserved).
- `_run_subprocess_json` raises `DashboardParseError` for non-dict JSON top-level (defensive default against future schema drift).

---

## Warnings and Suggestions (carried forward to PR2/PR3 verify)

| # | Severity | Description | Action |
|---|---|---|---|
| W1 | WARNING | PR1 base branch is `main`, not tracker `phase-5-dashboard`. A 3-way merge (no-FF or merge commit) is required when the user merges PR1 to the tracker. | User merges PR1 → tracker after this archive. 3-way merge is clean (no file overlap). |
| S1 | SUGGESTION | PR1 commit message body says "stacked-to-main" (cosmetic). | Accepted; no amend (user-locked). Optionally correct via a follow-up commit if desired. |
| S2 | SUGGESTION | AC14 placeholder resolution is verified on tracker only. | Mention in PR description when user opens PR1 on tracker. |

---

## PR2 and PR3 Status (Pending)

### PR2 — `feat(dashboard): filter + sort + color + rich rendering` (Wave 3 + Wave 4)

- **Status**: pending
- **Tasks**: T4 `filter_by_rules`, T5 `sort_projects`, T6 `color_code`, T7 `render_header`, T8 `render_needs_table`, T9 `render_archived`, T10 `render_footer`, T11 `render_dashboard` (composer)
- **LOC estimate**: ~200 LOC (per tasks #543 forecast)
- **Tests estimate**: +11 new tests (3 + 4 + 3 + 1 + 2 + 1 + 1 + 2 = wait, design says 8 PR2 tests across 8 classes)
- **Base branch**: will branch off `phase-5-dashboard-pr1` AFTER PR1 merges to tracker `phase-5-dashboard`
- **Independence**: depends on PR1 (uses fetcher return type contracts)
- **Strict TDD**: ON

### PR3 — `feat(dashboard): click integration + verify script + ACs` (Wave 5 + Wave 6 + Wave 7)

- **Status**: pending
- **Tasks**: T12 `workspace_dashboard_cmd` Click handler at `cli.py:3034`, T13 `verify-checks.sh` script, T14 full-suite AC walkthrough, T15 AC1–AC15 walkthrough + visual capture
- **LOC estimate**: ~150 LOC code (Click integration at `cli.py:3034` +32 LOC + renderers glued at the CLI level) + ~60 LOC verify script
- **Tests estimate**: +4 CliRunner tests for T12
- **Base branch**: will branch off `phase-5-dashboard-pr2` AFTER PR2 merges
- **Independence**: depends on PR2 (uses renderer return types)
- **Strict TDD**: ON
- **Non-runtime infra**: `verify-checks.sh` (8 structural checks from design §8) ships with this PR

### Final archive timing

After PR3 lands on tracker `phase-5-dashboard`:

1. The change folder `openspec/changes/phase-5-dashboard/` moves to `openspec/changes/archive/2026-06-30-phase-5-dashboard/`.
2. This `archive-report-pr1.md` is REPLACED by a consolidated `archive-report.md` (full cycle closure, all 15 ACs passed, all 8 verify checks at HEAD).
3. PR1 + PR2 + PR3 partial reports are subsumed by the final report; PR3 verify report at that moment supersedes this one.
4. The next phase (post-Phase-5) is independent of this change.

---

## PR1 Branch Topology and Merge Plan

```
main (6133e70)
 │
 ├── phase-5-dashboard (tracker) @ b9da84b
 │    └─ chore(specs): add dashboard REQs to workspace root spec
 │       (66 ins + 4 del in openspec/specs/workspace/spec.md ONLY)
 │
 └── phase-5-dashboard-pr1 @ 6651add
      └─ feat(dashboard): PR1 — subprocess wrappers + fetchers (Wave 1+2)
         (2 NEW files / 498 ins / 0 del; zero modifications elsewhere)
```

**Merge command** (user executes after this archive):

```bash
git checkout phase-5-dashboard
git merge --no-ff phase-5-dashboard-pr1 -m "merge: PR1 of phase-5-dashboard (data layer)"
```

The 3-way merge is clean because:

- tracker carries ONLY `openspec/specs/workspace/spec.md` modification
- PR1 carries ONLY `src/flow_engineering/dashboard.py` + `tests/unit/test_dashboard.py` (NEW)
- No file overlap → merge resolves trivially

PR2 then branches off `phase-5-dashboard` (after the merge); PR3 branches off `phase-5-dashboard-pr2` (after PR2 merges).

---

## Cross-Traceability (Engram observations)

| ID | Topic | Purpose |
|---|---|---|
| #535 | `sdd/phase-5-dashboard/explore` | 5 alternatives + tradeoffs surfaced |
| #536 | `sdd/pattern/chained-pr-option-B` | Chained-PR Option B decision pattern |
| #537 | `sdd/phase-5-dashboard/proposal` | Approach E Rich-only read-only dashboard |
| #538 | `sdd/pattern/no-json-on-dashboard` | Pattern — one identity per command (no `--json` on dashboard) |
| #539 | `sdd/phase-5-dashboard/spec` | 6 root REQs + 7 delta-internal REQs |
| #541 | `sdd/phase-5-dashboard/design` | 641 LF, 7 TDD waves, 8 verify checks |
| #542 | `sdd/pattern/chain-by-wave` | Pattern — chain by wave, not by capability |
| #543 | `sdd/phase-5-dashboard/tasks` | 15 tasks, Option B locked |
| #544 | `sdd/pattern/pure-pr1` | Pattern — PR1 = pure data layer |
| #545 | `sdd/phase-5-dashboard/apply-progress-pr1` | PR1 apply result |
| #546 | `sdd/pattern/spec-changes-separate-commit` | Pattern — spec chore on tracker, code on PR |
| #547 | `sdd/phase-5-dashboard/verify-report-pr1` | PR1 verify result (1 WARNING, 2 SUGGESTIONS) |
| (this report) | `sdd/phase-5-dashboard/archive-report-pr1` | PR1 partial archive closure |

---

## v1.1-followups Status

| Field | Value |
|---|---|
| Classification | Someone else's in-progress work (different change, different PR strategy) |
| Touched in PR1 | **NO** |
| Touched in this archive | **NO** |
| Contamination check | **CLEAN** — `openspec/changes/v1.1-followups/` remains untracked, never tracked, no files read/written from this archive |

---

## Strict TDD Compliance Recap

| Check | Result | Evidence |
|---|---|---|
| TDD evidence table in apply-progress | PASS | Engram #545 TDD Cycle Evidence (RED / GREEN / TRIANGULATE / REFACTOR) |
| All tasks have tests | PASS | 13 tests across 4 classes for 3 PR1 tasks (T1=8, T2=2, T3=3) |
| RED confirmed | PASS | Tests written first; collection failed before implementation |
| GREEN confirmed | PASS | `uv run --frozen pytest tests/unit/test_dashboard.py -v` → 13/13 PASSED |
| Triangulation adequate | PASS | T1: 4 paths (happy + 3 error); T2: 2 (happy + error); T3: 3 (happy + missing + corrupt) |
| Safety net for modified files | PASS (N/A new) | Both files are NEW; verified by `git diff main..HEAD` showing only 2 new files |
| Zero trivial assertions | PASS | Assertion Quality Audit in `verify-report.md` found no tautologies, no smoke-only assertions, no ghost loops |

---

## Artifacts

- **NEW**: `openspec/changes/phase-5-dashboard/archive-report-pr1.md` (this file, partial archive for PR1)
- **Mirrored to**: Engram observation topic `sdd/phase-5-dashboard/archive-report-pr1` (`capture_prompt: false`, `type: "architecture"`, `project: "insyd"`, `scope: "project"`)
- **Untouched**: `openspec/changes/v1.1-followups/` (sacred territory)
- **Untouched**: PR1 commit `6651add` (no amend; user-locked)
- **Untouched**: `openspec/specs/workspace/spec.md` on tracker (preserved by spec chore `b9da84b`, not by this archive)
- **NOT created**: `openspec/changes/archive/2026-06-30-phase-5-dashboard/` (final archive after PR3)
- **NOT created**: consolidated `archive-report.md` (created at PR3 final archive time)

---

## SDD Cycle Complete (PR1)

PR1 of `phase-5-dashboard` is **fully planned, implemented, verified, and partially archived**. The change folder remains at `openspec/changes/phase-5-dashboard/` and will host PR2 + PR3 over the next two apply/verify/archive cycles before the final archive.

**Ready for**: user merges PR1 to tracker `phase-5-dashboard`, then `sdd-apply PR2` (Wave 3+4 — filter + sort + color + Rich rendering).