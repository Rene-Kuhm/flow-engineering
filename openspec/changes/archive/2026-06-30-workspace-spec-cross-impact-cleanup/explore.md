# Explore: workspace-spec-cross-impact-cleanup

> **Phase**: 1/8 — `sdd-explore`
> **Change**: `workspace-spec-cross-impact-cleanup` (doc-only)
> **Project**: flow-engineering v1.2.0 · main HEAD `780285f` (post `flow-where-cross-project-capability-merge` merge)
> **Strict TDD**: OFF (doc-only — no behavior, no tests)
> **Artifact store**: openspec (filesystem) + Engram mirror (topic_key `sdd/workspace-spec-cross-impact-cleanup/explore`)
> **Scope locks**: W1 + W2 ONLY. NO expansion. NO code. NO `v1.1-followups/` touch. NO modifications outside `workspace/spec.md` and this artifact.

## Goal

Surface the exact locations and design space for two stale-prose warnings (W1 + W2) carried forward from the `flow-where-cross-project-capability-merge` verify phase (#513). The follow-up landed via commits `6e21d4d` (apply) + `8d51c5f` (archive chore). Two stale references in the workspace root spec survived the merge. This change is the smallest, cheapest fix in the workspace-intelligence arc: clean those two lines so the workspace root spec is "impeccable" before Phase 5 dashboard adds a new delta on top.

## Scope

- **In scope**: 2 prose fixes in `openspec/specs/workspace/spec.md` (1 edit at L16, 1 edit at L241). Total ~2 lines / ~3 words net change.
- **Out of scope**: any other stale prose; any code; any test; any helper; any archive move; any `v1.1-followups/` touch; any new verify check; any change to `openspec/specs/flow-where/spec.md`; any change to any prior archive.
- **Protected artifacts (must remain intact)**:
  - Source: lines for the 7 root REQs at L96, L114, L124, L134, L144, L164, L174
  - Drift Detection footer at L305-313
  - "Family index" callout at L4
  - §6.1 Cross-Impact content at L274-292 (including the RESOLVED note at L292)
  - §7 Future Changes table at L296-303 (rows #2–#7)
  - All 7 verify checks from `workspace-capability-bootstrap` design #492 §4

## W1 Investigation

### Exact location

- **File**: `openspec/specs/workspace/spec.md`
- **Line**: 241
- **Section**: §4.2 Versioning — "Family event / Trigger / Impact on root spec" table, last row

### Verbatim current text (line 241)

```
| Phase 2 follow-up lands | `flow-where-cross-project-capability-merge` | No change to workspace root spec; `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X` |
```

### Stale reference

The third column references `REQ-V1.0.5..V1.0.X`. That string was a **forward-looking placeholder** authored during the `workspace-capability-bootstrap` cycle (Engram #490 / #492) before Phase 2 actually integrated. After the apply phase of `flow-where-cross-project-capability-merge` (commit `6e21d4d`), the 6 root REQs landed in `openspec/specs/flow-where/spec.md` with a different namespace:

- `REQ-WHERE-CROSS-PROJECT-SCOPE` (L274)
- `REQ-WHERE-DEFAULT-TEXT-FORMAT`
- `REQ-WHERE-EXPLICIT-FORMAT-FLAG`
- `REQ-WHERE-EXIT-CODE-MAPPING`
- `REQ-WHERE-ENGRAM-STUB`
- `REQ-WHERE-REGEX-OPT-IN` (L326)

Confirmed by grep on `openspec/specs/flow-where/spec.md` (only 2 of 6 shown above; all 6 are present in the canonical spec).

### Multiplicity check

`grep -F "REQ-V1.0.5" openspec/specs/workspace/spec.md` returns **1 match** (L241 only). No other occurrences of the stale namespace anywhere in the spec.

### Fix shape (recommended)

Replace the stale namespace with the actual namespace, matching the exact phrasing already used in the §6.1 RESOLVED note at L292 (consistency principle: a reviewer reading both locations sees the same wording):

**Proposed text for line 241**:

```
| Phase 2 follow-up lands | `flow-where-cross-project-capability-merge` | No change to workspace root spec; `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) |
```

Diff is purely the third column fragment `REQ-V1.0.5..V1.0.X` → `` `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) ``. Net ≈ 10 word-tokens changed, 0 lines added, 0 lines removed.

## W2 Investigation

### Exact location

- **File**: `openspec/specs/workspace/spec.md`
- **Line**: 16
- **Section**: "Archive status (2026-06-30)" header (which spans L6–L16), the last sentence of that block

### Verbatim current text (line 16)

```
**Carry-forwards documented in Future Changes** (§7): `flow-where-cross-project-capability-merge` (Phase 2 follow-up), Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.
```

### Stale reference

The first item in the comma-separated carry-forwards list — `` `flow-where-cross-project-capability-merge` (Phase 2 follow-up) `` — is now stale because:

1. The follow-up has landed (apply commit `6e21d4d`, archive chore `8d51c5f`, archived at `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`).
2. The corresponding row was already removed from §7 Future Changes during apply (per verify-report #513 AC7: "workspace §7 row removed | PASSED | §7 contains 0 table rows referencing this change").
3. The §6.1 RESOLVED note at L292 explicitly records that the reclassification is RESOLVED and the §7 row is removed.
4. Therefore listing it as a "carry-forward documented in Future Changes" contradicts the rest of the file.

### Section context

This sentence is **NOT inside §7** — it sits in the Archive status header block (L6–L16), which is the close-out summary for the `workspace-capability-bootstrap` change. The sentence is a meta-statement pointing forward to §7 to give the reader a one-line summary of what follow-ups remain. Now that one of those follow-ups has landed, the pointer is stale.

The §7 Future Changes table itself (L296–L303) is INTACT and does NOT contain `flow-where-cross-project-capability-merge`. So the fix is purely in the meta-pointer sentence at L16; §7 is untouched.

### Multiplicity check

`grep -F "Carry-forwards documented in Future Changes" openspec/specs/workspace/spec.md` returns **1 match** (L16 only). The stale item appears once in the spec.

### Fix shape (recommended)

**Remove the stale item from the carry-forwards list**, matching the precedent set by verify-report #513 AC7 (where the §7 row itself was removed rather than replaced with a "landed" marker). Grammar-wise, deleting one item from a comma-separated list with a closing "R1/R3/R4 deferred rules" item keeps the sentence well-formed.

**Proposed text for line 16**:

```
**Carry-forwards documented in Future Changes** (§7): Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.
```

Diff: remove `` `flow-where-cross-project-capability-merge` (Phase 2 follow-up), `` (44 characters). 0 lines added, 0 lines removed. The remaining 4 carry-forwards are all still valid (Phase 5 placeholder, optional top-level capability, backup retention policy, R1/R3/R4 deferred remediation — none of these have shipped).

### Alternative (NOT recommended)

Replace the stale item with a "landed" marker like `` `flow-where-cross-project-capability-merge` (LANDED 2026-06-30, see §6.1) ``. This adds an audit-trail sentence to the archive-status block of a change that already shipped its own archive-report. The information is already preserved in:

- §6.1 RESOLVED note at L292 (full RESOLVED narrative)
- Engram #514 (consolidated archive-report for the merge change)
- `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/archive-report.md`

Adding a "landed" marker at L16 would duplicate information that's already in a more authoritative location. Recommend removing cleanly.

## Protected Artifacts Verification

All 7 user-locked "must remain intact" categories were re-verified by reading the spec and cross-referencing against the design's verification surface (Engram #492):

| Protected artifact | Location | Status |
|---|---|---|
| Source: lines (7 root REQs) | L96, L114, L124, L134, L144, L164, L174 | INTACT — W1/W2 do not touch any REQ block |
| Drift Detection footer | L305-313 | INTACT — fix is at L16 + L241, far from §8 |
| "Family index" callout | L4 (inside blockquote) | INTACT — fix is at L16 + L241 |
| §6.1 Cross-Impact content | L274-292 | INTACT — both fixes are outside §6.1 |
| §7 Future Changes table | L296-303 (rows #2–#7) | INTACT — fix is at L16 (Archive status meta-pointer, not §7) |
| Verify check surface (design #492 §4) | 7 checks | STILL PASS — see table below |

### Verify check re-validation

Each of the 7 checks from design #492 §4 was re-checked against the proposed fixed spec. All 7 still pass after the W1 + W2 edits:

| # | Check | Pre-fix | Post-fix |
|---|---|---|---|
| 1 | Every root REQ has exactly 1 `Source:` line (7/7) | PASS | PASS (no REQ block touched) |
| 2 | Every `Source:` path exists (3 unique paths) | PASS | PASS (no Source: path touched) |
| 3 | Every cited delta REQ-ID exists in its delta | PASS (19 IDs across 6 root REQs) | PASS (no cited ID touched) |
| 4 | Cross-Impact mentions `flow-where-cross-project-capability-merge` | PASS (L290, L292) | PASS (L290 + L292 remain) |
| 5 | §7 Future Changes lists `workspace-dashboard` | PASS (L298) | PASS (L298 untouched) |
| 6 | Drift Detection footer present | PASS (L305 H2) | PASS (L305 untouched) |
| 7 | "Family index" callout in first 10 lines | PASS (L4) | PASS (L4 untouched) |

**Conclusion**: the 7 verify checks survive the minimal fix unchanged. The verification surface remains intact; no new check is added (out of scope per user locks).

## Other Stale Prose Survey (INFORMATIONAL ONLY — NOT IN SCOPE)

The following stale-prose locations were identified during investigation but are **explicitly OUT OF SCOPE** per the user's "W1 + W2 ONLY" lock. Listed here for the audit trail only; do NOT include in this change's scope. Each could be a future named cleanup change.

1. **§4.1 ASCII diagram — L221** (`flow-where-cross-project-capability-merge follow-up`): the diagram describes the follow-up as if forward-looking ("Phase 2 (flow-where-cross-project) reclassified HERE / See §6.1 Cross-Impact for rationale + §7 for the / flow-where-cross-project-capability-merge follow-up"). The follow-up has landed, so this diagram text is technically stale. However, §4.1 is not in the protected list and the wording is descriptive enough to remain accurate ("See §6.1 for rationale" still points to a valid section). Future `workspace-spec-cross-impact-cleanup` v2 candidate.

2. **§6.1 RESOLVED note — L292** (`Merge SHA is \`[future-commit-sha]\``): the actual merge SHA is `6e21d4d96fbc9d94a0814c0f677cd03cb1f4bb07` (apply commit). The `[future-commit-sha]` placeholder is now stale. **HOWEVER**, §6.1 is PROTECTED INTACT per user locks; this cannot be touched in this change. Future cleanup change candidate (e.g., `workspace-spec-cross-impact-cleanup` v2 OR a tiny §6.1-update change).

3. **§6.1 follow-up pointer — L290** (`**Follow-up** (\`flow-where-cross-project-capability-merge\`): See §7 Future Changes.`): the pointer now leads to a non-existent §7 row. **HOWEVER**, §6.1 is PROTECTED INTACT; cannot touch. Future cleanup candidate.

**All three informational items are protected by user locks** (either explicit "§6.1 INTACT" or implicit "W1 + W2 ONLY"). They are out of scope by design.

## Open Questions

1. **W1 — Generic vs enumerated?**: should the §4.2 prose say "REQ-WHERE-*" generically, or enumerate the 6 specific REQ IDs (start..end range)?
   - **Recommendation**: enumerate the range ("`REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs)"). Tradeoffs: enumerated matches the exact wording used in §6.1 RESOLVED note (consistency); gives a reviewer concrete IDs to spot-check; survives future renames less gracefully than a generic wildcard. Generic ("`REQ-WHERE-*`") is shorter but introduces a wildcard pattern that's harder for readers to spot-check against the §3 sub-capability table.

2. **W2 — Remove vs "landed" marker?**: should the carry-forward entry at L16 be removed cleanly, or replaced with a "landed" marker (audit trail)?
   - **Recommendation**: remove cleanly. Tradeoffs: remove matches the verify-report #513 AC7 precedent (where the §7 row itself was deleted, not marked); the audit trail is already preserved in §6.1 RESOLVED note + Engram #514 + archived `archive-report.md`. Landed-marker would duplicate information already in a more authoritative location.

3. **Multiplicity — are there other instances?**: are there other occurrences of the same stale prose elsewhere in the spec?
   - **Answer (from grep)**: NO. Only 1 instance of `REQ-V1.0.5` in the spec (L241). Only 1 instance of the carry-forward entry (L16). No multiplier. The fix is genuinely 2 single-line edits.

4. **Verify check — auto-detect future staleness?**: should this change introduce a verify check (e.g., Check 8) that detects future stale prose automatically?
   - **Recommendation**: NO. Tradeoffs: a new check would exceed user-locked "doc-only / no new helpers" scope. The 7 existing checks already protect Source: path validity, REQ-ID existence, structural presence (Cross-Impact, Future, Drift, Family). Adding Check 8 is the right move for a SEPARATE future change (e.g., the named `spec-drift-detector` follow-up from verify-report #513 S1).

5. **§4.1 / §6.1 stale-but-protected prose**: how do we handle the three informational items in the "Other Stale Prose Survey"?
   - **Recommendation**: defer to a future cleanup change that explicitly unlocks §6.1 (or §4.1) edits. The current change respects the user locks strictly. A future `workspace-spec-cross-impact-cleanup` v2 OR a dedicated `workspace-spec-followup-pointer-update` change could clean them up in one PR.

## Approach Candidates

### Approach A — Minimal (RECOMMENDED)

- **What**: fix exactly W1 (L241) + W2 (L16). Two single-line edits. Total ≈ 3 word-tokens net change.
- **Pros**:
  - Lowest risk: surgical, no scope creep, no architectural decision needed.
  - Respects all 14 user-locked constraints verbatim.
  - 7 verify checks unaffected; no new tests needed (doc-only).
  - Trivial commit hygiene: single PR, single commit, well under 400-line review budget.
  - Matches the established precedent from verify-report #513 AC7 (clean removal of the stale §7 row).
- **Cons**:
  - Leaves 3 informational stale-prose items in §4.1 + §6.1 untouched (acceptable: protected by user locks).
  - Does not add auto-detection for future staleness (deferred to `spec-drift-detector` follow-up per S1).
- **Effort**: **Low** (~5 min in spec phase, ~5 min in apply phase, ~10 min in verify phase).

### Approach B — Comprehensive (NOT recommended for this change)

- **What**: Approach A + add a verify check (Check 8) that scans for stale prose patterns in `Source:` lines and §7/§6 cross-impact pointers.
- **Pros**:
  - Closes the loop on future staleness (prevents W1/W2 from recurring).
  - Aligns with the spirit of S1 (spec-drift-detector follow-up).
- **Cons**:
  - **Exceeds user-locked "doc-only" scope** if the check requires new code (it would).
  - Could be implemented as a pure-text `grep`/`awk` one-liner (matching the style of the existing 7 checks from design #492 §4), but adding the check still requires updating design #492 + re-running all checks.
  - Adds review surface (the new check + its failure mode) on a change that the user explicitly scoped to "W1+W2 only".
- **Effort**: **Medium** (~30 min added across spec/design/apply/verify phases). **Defer to a SEPARATE named follow-up** (`spec-drift-detector` per S1, or fold into `capability-spec-linter` per S2).

### Approach C — Catalog (EXPLICITLY REJECTED by user)

- **What**: enumerate ALL stale prose in `workspace/spec.md` (3 informational items + W1 + W2 = 5 total) and fix in one PR.
- **Pros**:
  - One-shot cleanup, no future cleanup-change debt.
- **Cons**:
  - **Explicitly rejected by user** ("W1 + W2 ONLY, no other prose fixes, no scope expansion").
  - 2 of the 3 informational items are inside §6.1, which is **PROTECTED INTACT** per user locks. Cannot touch them in this change.
  - Scope expansion would require re-running the entire constraint matrix (15+ user locks from workspace-capability-bootstrap + flow-where-cross-project-capability-merge).
- **Effort**: would be Low if §6.1 weren't protected, but **Medium-High** if it were (requires re-locking constraints). **Reject as recommended.**

### Recommended approach: A (Minimal)

The user's scope lock is unambiguous ("W1 + W2 ONLY"). Approach A is the only one that respects it without qualification. Approach B's auto-detection is the right idea but belongs in a SEPARATE named follow-up change.

## Tech Debt Interactions

This change **preserves** the existing tech-debt baseline and does NOT modify any of it:

| Tech-debt item | Pre-this-change state | Post-this-change state |
|---|---|---|
| 3 pre-existing ruff errors | `cli.py:682 RET504`, `test_cli_where_cross_project.py:{33 UP035, 295 W292}` | UNCHANGED (zero code touched) |
| Pre-existing test failures | 0 (1513/1513 baseline on `780285f`) | UNCHANGED (no test run needed; doc-only) |
| AC9 byte-identical guard (`tests/unit/test_cli_projects.py:435`) | GREEN (last verified 0.17s in verify-report #513) | UNCHANGED (zero code touched; re-verified by `sdd-verify` AC8) |
| `openspec/changes/v1.1-followups/` (sacred territory) | UNTOUCHED | UNTOUCHED (sacred, user-locked) |
| 4 archive specs | UNTOUCHED | UNTOUCHED |
| `openspec/specs/flow-where/spec.md` | UNTOUCHED (346 LF) | UNTOUCHED |
| mypy clean (32 source files) | clean | UNCHANGED (no source file touched) |
| Engram memory | 20 prior observations for the arc | +1 mirror observation for this explore phase |

The AC9 byte-identical guard is preserved by the zero-code-change policy. `sdd-verify` re-runs the guard at AC8 of this change to confirm.

## Forecast

This is the smallest cycle in the workspace-intelligence arc. The fix is mechanical:

- `sdd-explore` (this phase): ~15 min
- `sdd-propose`: ~10 min (tiny proposal — 2 follow-up items, 6 constraints, no risks beyond scope lock)
- `sdd-spec`: ~5 min (delta spec is ~10 lines — just the 2 edits in `MODIFIED Requirements` + rationale)
- `sdd-design`: ~5 min (no new design surface — re-validate the 7 checks from #492)
- `sdd-tasks`: ~5 min (2 tasks: "edit L16", "edit L241", plus verify)
- `sdd-apply`: ~5 min (2 single-line edits + 1 commit + re-read the file)
- `sdd-verify`: ~10 min (run all 7 verify checks + confirm AC9 byte-identical guard + mypy/ruff baselines)
- `sdd-archive`: ~5 min (move change folder to `archive/2026-06-30-workspace-spec-cross-impact-cleanup/`)

**Total cycle**: ~60 min wall-clock. ~5-10 LOC of prose changes. Trivially under the 400-line review budget. Single PR, single commit, no chained PRs needed.

## Verdict

**Recommended approach: A — Minimal.** Fix W1 (L241) and W2 (L16) surgically; leave everything else intact.

### Rationale

1. **User locks are explicit and tight** ("W1 + W2 ONLY"). Approach A is the only approach that satisfies them without re-litigating scope.
2. **The fix is mechanically trivial**: 2 single-line edits at known locations. No design ambiguity.
3. **The verification surface is pre-built**: 7 verify checks from design #492 already protect the spec's structural well-formedness. Re-running them after the edit is a 1-minute check.
4. **Approach B's auto-detection is the right idea but in the wrong change**: it belongs in `spec-drift-detector` (S1 follow-up), where it can be designed properly with its own scope, its own ACs, and its own verify surface.
5. **Approach C is explicitly rejected**: 2 of the 3 informational stale-prose items are inside the §6.1 PROTECTED zone. Cannot touch them in this change.

### Next step

Ready for `sdd-propose`. The proposal will:
- Re-state the W1 + W2 scope verbatim from this explore.
- Define 4-6 acceptance criteria (AC1: W1 fixed + matches §6.1 wording; AC2: W2 fixed + carry-forwards list grammatically intact; AC3: 7 verify checks still pass; AC4: AC9 byte-identical guard still green; AC5: no other section touched; AC6: under 400-line budget).
- Carry forward all user locks from the explore launch prompt.
- Cite the 2 informational stale-prose items as future named changes (not in this PR's scope).

## Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Scope creep during apply** — apply phase may be tempted to also clean the §4.1 L221 stale diagram text or §6.1 L290 follow-up pointer. | **Low** (mitigated by user locks + this explore's "Other Stale Prose Survey" section explicitly deferring them) | Apply phase reads this explore's §"Open Questions" Q5 + §"Other Stale Prose Survey" before editing; only L16 + L241 may change. |
| 2 | **Wording drift between §4.2 fix and §6.1 RESOLVED note** — if W1's fix uses different REQ-IDs or phrasing than §6.1's RESOLVED note, future readers see two slightly different versions of the same fact. | **Low** | Recommended W1 fix uses the exact same "REQ-WHERE-CROSS-PROJECT-SCOPE through REQ-WHERE-REGEX-OPT-IN" phrasing as §6.1 L292. Spec phase enforces this consistency. |
| 3 | **Verify check Check 4 regression** — Check 4 (Cross-Impact mentions `flow-where-cross-project-capability-merge`) could fail if either edit accidentally removes all remaining mentions. | **Low** | Grep confirms 5 mentions currently (L16, L221, L241, L290, L292); W2 fix removes only L16 (carry-forwards pointer, not a structural reference). After fix: 4 mentions remain (L221, L241, L290, L292). Check 4 still passes. |
| 4 | **§6.1 RESOLVED note `[future-commit-sha]` placeholder still stale** — protected by user lock, but a reviewer may flag it as a follow-up nit. | **Low** (informational only) | §"Other Stale Prose Survey" item #2 documents this as a future cleanup candidate. Acknowledge in PR body if asked. |
| 5 | **Engram mirror drift** — if the explore.md on disk and the Engram observation diverge, future sessions may act on stale context. | **Very Low** | Mirror is written with `topic_key: "sdd/workspace-spec-cross-impact-cleanup/explore"` for upsert; both copies carry the same content block. |

## Relevant Files

- `openspec/specs/workspace/spec.md` (315 LF) — the target file for the 2 edits (READ ONLY in this phase)
- `openspec/specs/flow-where/spec.md` (346 LF) — INTACT, contains the 6 REQ-WHERE-* IDs that W1 fix will reference
- `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/` — INTACT, contains the source-of-truth for the landed merge
- `openspec/changes/workspace-spec-cross-impact-cleanup/explore.md` — NEW (this artifact)
- `openspec/changes/workspace-spec-cross-impact-cleanup/` — NEW change folder (sibling of this file)
- Engram `sdd/workspace-spec-cross-impact-cleanup/explore` — NEW mirror observation (topic_key for upsert)
- Engram `#513` (sdd/flow-where-cross-project-capability-merge/verify-report) — origin of W1 + W2 warnings
- Engram `#492` (sdd/workspace-capability-bootstrap/design) — origin of the 7 verify checks
- Engram `#490` (sdd/workspace-capability-bootstrap/spec) — origin of the W1 placeholder text
- Engram `#514` (sdd/flow-where-cross-project-capability-merge/archive-report) — confirms W2 follow-up has fully landed