# Proposal: flow-where-cross-project-capability-merge

> **Change**: `flow-where-cross-project-capability-merge`
> **Type**: doc-only (zero code, zero tests)
> **Approach**: B — Comprehensive (mirror workspace-capability-bootstrap pattern)
> **Strict TDD**: OFF
> **Phase**: propose (Phase 4 of workspace-intelligence arc)
> **Builds on**: explore #503 (Phase 2 recovery from `27111ed`, 6 REQs + 11 BDD scenarios + 10 ACs)
> **Artifact store**: openspec

## 1. Intent

Integrate the shipped Phase 2 cross-project search capability (`flow-where-cross-project`, merged into `main` at commit `001651b`) into the canonical `flow-where` root spec as 6 new root REQs (`REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN`), regenerate the Phase 2 delta spec byte-identical from git commit `27111ed`, and resolve the `workspace/spec.md` §6.1 + §7 row #1 reclassification follow-up as LANDED by this PR.

**Rationale anchor (user-locked)**: *"no mezclar 'inventario/estado/higiene del workspace' con 'búsqueda/retrieval de contenido'"* (Engram #487) — Phase 2 belongs to `flow-where`; the workspace reclassification follow-up is now resolved.

## 2. Scope

### In Scope

1. **Regenerate Phase 2 delta spec** at `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` — byte-identical recovery from `git show 27111ed:openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md` (155 lines).
2. **Additive Phase 2 integration in `openspec/specs/flow-where/spec.md`** — preserve existing 245 lines verbatim; append new §0 callout + §2.b + §3.b + §4.b + §5.b + §6 Cross-Impact row + §7 Versioning row (v0.9.0) + §8 Drift Detection footer.
3. **6 root REQs** `REQ-WHERE-CROSS-PROJECT-SCOPE` / `REQ-WHERE-DEFAULT-TEXT-FORMAT` / `REQ-WHERE-EXPLICIT-FORMAT-FLAG` / `REQ-WHERE-EXIT-CODE-MAPPING` / `REQ-WHERE-ENGRAM-STUB` / `REQ-WHERE-REGEX-OPT-IN` with `Source:` lines pointing to the regenerated delta spec.
4. **Update `openspec/specs/workspace/spec.md`** §6.1 (retroactively resolved framing) + §7 row #1 (REMOVE) + §4.2 versioning table row (mark RESOLVED).
5. **7 verify checks** (paralleling workspace-capability-bootstrap design #492 pattern: Source: presence + path validity + REQ-ID existence + Cross-Impact + Future-Changes + Drift-Detection footer + Family-index position).
6. **Single PR, 1 commit, no chained, no `size:exception`.**

### Out of Scope

- NO code modifications to `cli.py`, `where.py`, or any other source file.
- NO test modifications (Phase 2 tests are shipped; this PR documents them only).
- NO modifications to existing `flow-where/spec.md` REQ-V1.0.1..V1.0.4 prose.
- NO touching `openspec/changes/v1.1-followups/`.
- NO modifications to any other capability spec.
- NO new subcommand, NO new flag, NO modification to existing flags.
- NO reconstruction of Phase 2 spec from memory — byte-identical recovery only.

## 3. Approach B Locked

**Approach B (Comprehensive)** — reaffirmed from explore #503 verdict. Mirrors the workspace-capability-bootstrap pattern (Engram #491, #493, #494) for a doc-only change: 7 verify checks, Source: lines, Cross-Impact row, Drift Detection footer, workspace §6.1 + §7 resolution.

### Content Shape (4 parts)

| Part | File | Action | LOC |
|------|------|--------|-----|
| **Part 1** | `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` | **Create** (regenerate delta spec byte-identical from `27111ed`) | ~155 |
| **Part 2** | `openspec/specs/flow-where/spec.md` | **Append** (additive: §0 + §2.b + §3.b + §4.b + §5.b + §6 row + §7 row + §8) | +80 to +120 |
| **Part 3** | `openspec/specs/workspace/spec.md` | **Edit** (§6.1 + §4.2 + §7 row #1 REMOVE) | small net |
| **Part 4** | `openspec/changes/flow-where-cross-project-capability-merge/design.md` | **Create** (7 verify checks paralleling workspace #492) | ~200-280 |

**Approach A (Minimal)** skipped — leaves flow-where without §8 Drift Detection footer (inconsistent with workspace spec); Approach C (Pure retrieval) skipped — leaves §6.1 + §7 row #1 unresolved.

## 4. Phase 2 Recovery Strategy (Mandatory Discipline)

Recovery via `git show 27111ed:openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md` — do NOT reconstruct from memory or code inspection.

**3-way triangulation** (per explore #503 §B):
1. **Engram #456** — REQ list + BDD scenario titles (summary pointer; NOT canonical content)
2. **Git history `git show`** — byte-identical delta spec content (canonical; preserved at `27111ed`)
3. **Code inspection (`cli.py:395-815`)** — verification that recovered spec describes production behavior

**Git SHA**: `27111ed` (2026-06-29, "chore(archive): add flow-where-cross-project artifacts")
**Source path recovered**: `openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md`
**Destination path**: `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md`

Delta spec content is **155 lines** covering:
- 6 REQs: REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN
- 11 BDD scenarios (S1..S11)
- 10 acceptance criteria (AC1..AC10)

## 5. Six Root REQs (Additive in flow-where/spec.md)

Each root REQ has: unique `REQ-WHERE-*` ID (distinct from delta `REQ-CROSS-PROJECT-*`), synthesized summary wording, and a `Source:` line pointing to the regenerated delta spec.

| Root ID | Title | Delta ID (Source) | Summary |
|---------|-------|-------------------|---------|
| `REQ-WHERE-CROSS-PROJECT-SCOPE` | Search 6 prospec directories per project | `REQ-CROSS-PROJECT-SCOPE` | `flow where "<query>" --root PATH` fans out across N projects, scanning exactly 6 locked directories (`src/ internal/ cmd/ tests/ openspec/ graphify-out/`) per project; missing subdirs silently skipped; files outside the 6 dirs NEVER scanned. |
| `REQ-WHERE-DEFAULT-TEXT-FORMAT` | ASCII-safe grouped text output | `REQ-DEFAULT-TEXT-FORMAT` | Default (no `--format`) emits ASCII-safe text grouped by project: `project_name` header → `file:line  content` rows → TOTAL summary. No box-drawing chars, no non-ASCII bytes. |
| `REQ-WHERE-EXPLICIT-FORMAT-FLAG` | Three format modes via --format | `REQ-EXPLICIT-FORMAT-FLAG` | `--format {text,json,tsv}` produces exactly one of three formats. JSON envelope: `version:"1"` first key, `results[]` + `totals`. TSV: header `project\tfile\tline\ttype\tcontent`. |
| `REQ-WHERE-EXIT-CODE-MAPPING` | grep-convention exit codes | `REQ-EXIT-CODE-MAPPING` | Exit `0` = matches found OR empty set; exit `1` = no matches; exit `2` = errors (invalid regex, unreadable --root). **Behavior change from v0.8.2** (which was always exit 0). |
| `REQ-WHERE-ENGRAM-STUB` | --engram accepted no-op | `REQ-ENGRAM-STUB` | `--engram` flag accepted with zero behavior change. JSON envelope carries `engram: {enabled: false, phase: "stub"}`. Phase 4+ reserved for real Engram MCP. |
| `REQ-WHERE-REGEX-OPT-IN` | --regex enables re.search | `REQ-REGEX-OPT-IN` | `--regex` enables case-insensitive regex matching. `re.compile(query)` validates at CLI boundary; exit 2 on `re.error`. |

**Naming rationale**: `REQ-WHERE-*` (not `REQ-V1.0.5..V1.0.10`) — distinct namespace from delta `REQ-CROSS-PROJECT-*` to clearly distinguish root-level synthesized summaries from delta-level canonical wording.

**Source: line grammar**: `**Source:** \`<path>\` §<REQ-ID>` (matches workspace spec pattern).

## 6. flow-where/spec.md Integration Plan

**Constraint**: existing 245 lines preserved verbatim. Only additive appends.

### New sections to append (in order)

**§0 "How to read this spec" callout** (new, ~8 lines):
```
> This spec has two generations: REQ-V1.0.1..V1.0.4 (v0.8.2, MVP
> single-project) and REQ-WHERE-CROSS-PROJECT-SCOPE..REQ-WHERE-REGEX-OPT-IN
> (v0.9.0, Phase 2 cross-project). Canonical wording for Phase 2 lives in
> the delta spec cited under each REQ's Source: line.
```

**§2.b Cross-Project Search (Phase 2)** (new, ~5 lines — extends §2 Purpose):
- Adds one bullet to the §2 Purpose list: "**Cross-project scope** (Phase 2, v0.9.0+): `--root PATH` fans out across N projects; 6 prospec dirs; 3 output formats; exit codes 0/1/2."

**§3.b Cross-Project Search** (new sub-section, ~5 lines heading):
- Clear `---` separator + sub-section heading before the 6 REQ blocks.

**§4.b Cross-Project Search REQs** (new, ~50-60 lines — the 6 REQ blocks):
- Each `REQ-WHERE-*` block: ID, Title, 1-2 sentence synthesized summary, `Source:` line pointing to regenerated delta spec with delta REQ ID.
- **Out of scope** callout per REQ block: what stays at delta level (Given/When/Then scenarios, specific helper signatures, CLI argument details).

**§4.b private-helpers block** (~15 lines):
- Lists Phase 2 helpers: `_search_projects_for_query`, `_format_where_text`, `_format_where_json`, `_format_where_tsv`, `_validate_regex_or_exit`, `_resolve_cross_project_root`, `_tag_match_type`, `_parse_cross_project`, `_strip_trailing_colon`, `_ascii_safe_local`.
- **Test citation**: `tests/unit/test_cli_where_cross_project.py` (10 tests — `test_where_cmd_{text_default_groups_by_project, json_envelope_structure, tsv_header_and_body, regex_valid_and_invalid, limit_caps_hits, root_resolution, exit_code_trio, engram_noop_identity, byte_identical_across_invocations, scope_discipline_excludes_node_modules}`).

**§5.b Cross-Project CLI surface** (new, ~20 lines):
- `--root PATH`, `--format {text,json,tsv}`, `--regex`, `--engram`, `--pretty` (forward-looking no-op) flags.
- New exit-code contract: `0` = match-or-empty, `1` = no-match, `2` = error.
- `--limit` defaults to 50 in cross-project mode (vs 20 in single-project MVP).

**§6 Cross-Impact** (append one row, ~3 lines):
- Row: `cross-project-search (v0.9.0+, REQ-WHERE-CROSS-PROJECT-SCOPE … REQ-WHERE-REGEX-OPT-IN) → EXTENSION — additive to REQ-V1.0.1..V1.0.4; reuses `_run_search` from where.py (read-only); new 6-dir prospec + 3 formatters + exit-code mapping.`

**§7 Versioning** (append one row, ~2 lines):
- Row: `v0.9.0 | 2026-06-30 | flow-where-cross-project-capability-merge (#<N>) | REQ-WHERE-CROSS-PROJECT-SCOPE … REQ-WHERE-REGEX-OPT-IN — cross-project search extension with 6-dir prospec + 3 formats + exit-code mapping | SHIPPED`

**§8 Drift Detection footer** (new, ~15 lines — mirror workspace/spec.md §8 pattern):
```
## 8. Drift Detection

> **How drift is mitigated between this root and the Phase 2 delta spec.**

- **Source-of-truth rule**: Each `REQ-WHERE-*` block in §4.b carries a
  `Source:` line citing the exact delta spec path + delta REQ ID. Canonical
  wording (Given/When/Then scenarios, acceptance criteria) lives at the
  delta; root-level summaries exist for navigation only.
- **Acceptance check**: `sdd-verify` validates that every `REQ-WHERE-*`
  block has a `Source:` line, and that the cited delta spec path exists
  (Check 1 + Check 2 + Check 3 in the verify report).
- **Delta-evolution protocol**: When a delta REQ is updated, the
  corresponding root REQ summary should be reviewed for drift.
```

### Target length
- flow-where/spec.md: **245 → ~325-365 lines** (delta +80 to +120)

## 7. workspace/spec.md Update Plan

**Constraint**: only §6.1 + §7 row #1 + §4.2 versioning table. Must NOT introduce new "stash"-triggering words (per Batch E constraint #18 carry-over from workspace-capability-bootstrap archive-report Engram #498).

### §6.1 (L274-290) — Retroactively resolved framing

Replace current "Phase 2 follow-up not yet done" language with:
```
Phase 2 (`flow-where-cross-project`) was historically filed under the
"workspace-intelligence" arc but **belongs to `flow-where`, NOT `workspace`**.
The follow-up change **`flow-where-cross-project-capability-merge`** (this PR)
merged Phase 2 into the `flow-where` root spec as REQ-WHERE-CROSS-PROJECT-SCOPE
through REQ-WHERE-REGEX-OPT-IN. See `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md`
(the regenerated delta spec, preserved byte-identical from git commit `27111ed`).
```

**Evidence bullet 5** (L286): Replace "MISSING locally" with:
```
Phase 2's delta spec has been REGENERATED at
`openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md`
(preserved verbatim from git commit `27111ed`, 2026-06-29).
```

### §4.2 versioning table (L241) — Mark RESOLVED

Replace:
```
| Phase 2 follow-up lands | `flow-where-cross-project-capability-merge` | No change to workspace root spec; `flow-where/spec.md` gains REQ-V1.0.5..V1.0.X |
```

With:
```
| Phase 2 follow-up landed | `flow-where-cross-project-capability-merge` | RESOLVED (this PR). `flow-where/spec.md` gained REQ-WHERE-CROSS-PROJECT-SCOPE … REQ-WHERE-REGEX-OPT-IN (v0.9.0). Delta spec regenerated from git commit `27111ed`. |
```

### §7 Future Changes row #1 — REMOVE

Delete the entire row for `flow-where-cross-project-capability-merge` (status: pending). It IS this change; no longer future.

### §7 Future Changes note (L16 carry-forwards list) — Update

Remove `flow-where-cross-project-capability-merge` from the carry-forwards list in the archive status block.

### §7 new entries (if needed)

If there are remaining follow-ups, add new rows (e.g., `workspace-hygiene-capability-spec`, R1 dirty-git, etc.). None added in this PR — leave for future planning.

### Word-safety check (Batch E constraint #18 carry-over)
- §6.1 new wording: "REGENERATED", "byte-identical", "git commit", "27111ed" — no "stash" or "worktree" trigger words.
- §7 row removal: only removes the row; no new words introduced.

### Target length
- workspace/spec.md: **~314 lines → ~312-316 lines** (small net reduction after §7 row removal, small addition to §6.1)

## 8. Seven Verify Checks (Paralleling workspace-capability-bootstrap Design #492)

Each check: pattern + exit code semantics + one-line failure diagnostic.

### Check 1: Source: line presence (6/6 expected)
```
Pattern: grep -c "^\*\*Source:\*\*" openspec/specs/flow-where/spec.md
Expected: 6 (one per REQ-WHERE-*)
Exit 0: all 6 present
Exit 1: fewer than 6 found — diagnostic: "missing Source: line for N REQs"
Exit 2: grep error
```

### Check 2: Source: path validity
```
Pattern: for each Source: path cited in flow-where/spec.md, test -f <path>
Expected: all 6 paths exist on disk
Exit 0: all paths exist
Exit 1: any path missing — diagnostic: "delta spec not found at <path>"
Exit 2: test command error
```

### Check 3: Source: REQ-ID existence in cited delta
```
Pattern: for each Source: line "…spec.md → REQ-<ID>", grep "REQ-<ID>" <path>
Expected: every cited delta REQ-ID found in cited file
Exit 0: all REQ-IDs found
Exit 1: any REQ-ID missing — diagnostic: "REQ-<ID> not found in delta spec"
Exit 2: grep error
```

### Check 4: Test file pointer in flow-where/spec.md §4.b
```
Pattern: grep -c "test_cli_where_cross_project.py" openspec/specs/flow-where/spec.md
Expected: >= 1
Exit 0: test pointer found
Exit 1: test pointer absent — diagnostic: "Phase 2 test file not cited in §4.b"
Exit 2: grep error
```

### Check 5: workspace/spec.md §6.1 marks reclassification RESOLVED
```
Pattern: grep "RESOLVED" openspec/specs/workspace/spec.md
Expected: >= 1 occurrence in §6.1 context
Exit 0: RESOLVED found
Exit 1: RESOLVED not found — diagnostic: "§6.1 reclassification not marked RESOLVED"
Exit 2: grep error
```

### Check 6: workspace/spec.md §7 row #1 no longer lists flow-where-cross-project-capability-merge
```
Pattern: grep "flow-where-cross-project-capability-merge" openspec/specs/workspace/spec.md | grep -c "^| 1 |"
Expected: 0 (row removed)
Exit 0: row absent
Exit 1: row still present — diagnostic: "§7 row #1 still lists flow-where-cross-project-capability-merge as pending"
Exit 2: grep error
```

### Check 7: Drift Detection footer present in flow-where/spec.md
```
Pattern: grep -c "^## 8. Drift Detection" openspec/specs/flow-where/spec.md
Expected: 1
Exit 0: footer present
Exit 1: footer absent — diagnostic: "§8 Drift Detection footer missing from flow-where/spec.md"
Exit 2: grep error
```

## 9. Forecast

| Metric | Value |
|--------|-------|
| `explore.md` (done) | 344 lines |
| `proposal.md` (this) | ~250-300 lines |
| Delta spec (regenerated) | 155 lines (byte-identical from `27111ed`) |
| flow-where/spec.md updates | +80 to +120 lines |
| workspace/spec.md updates | small net (~+0 to +2 lines) |
| design.md (7 verify checks) | ~200-280 lines |
| tasks.md (~7-9 tasks) | ~150-200 lines |
| **Cumulative diff for review** | **~250-320 lines** (under 400 budget) |
| **Single PR or chained?** | Single PR, 1 commit, no chained |
| **`size:exception`?** | No |
| **400-line budget risk** | Low |
| **Decision needed before apply?** | No |

## 10. Acceptance Criteria (11 ACs for sdd-verify)

| AC | Description | Verify method |
|----|-------------|---------------|
| **AC1** | Delta spec regenerated byte-identical from `27111ed` | `diff <(git show 27111ed:...) <(cat specs/flow-where-cross-project/spec.md)` — empty diff |
| **AC2** | 6 root REQs each with `Source:` line in `flow-where/spec.md` | Check 1 (grep count = 6) |
| **AC3** | Each `Source:` path exists on disk | Check 2 (all 6 paths `test -f`) |
| **AC4** | Each `Source:` REQ-ID exists in cited delta spec | Check 3 (all cited REQ-IDs found) |
| **AC5** | `flow-where/spec.md` references `test_cli_where_cross_project.py` (10 tests) | Check 4 (grep >= 1) |
| **AC6** | `workspace/spec.md` §6.1 marks reclassification as RESOLVED | Check 5 (grep RESOLVED in §6.1) |
| **AC7** | `workspace/spec.md` §7 row #1 no longer lists `flow-where-cross-project-capability-merge` | Check 6 (grep count = 0 for pending row) |
| **AC8** | AC9 byte-identical guard still passes (zero code changes) | `test_flow_projects_ls_json_byte_identical_envelope` still green |
| **AC9** | Full suite 1513/1513 still passes (zero regressions) | `uv run pytest` clean |
| **AC10** | NO modifications to existing flow-where code in `cli.py` | `git diff --name-only -- src/flow_engineering/cli.py` empty |
| **AC11** | Cumulative diff under 400-line review budget | `git diff --stat` additions+deletions < 400 |

## 11. Open Questions (All Resolved)

| # | Question | Resolution |
|---|----------|------------|
| Q1 | Recovery strategy | `git show 27111ed:<path>` — byte-identical recovery; do NOT reconstruct from memory |
| Q2 | Root REQ naming | `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (different from delta `REQ-CROSS-PROJECT-*` to distinguish root summaries from delta canonical wording) |
| Q3 | flow-where integration | ADDITIVE only — preserve existing 245 lines verbatim; append Phase 2 sections |
| Q4 | workspace §7 update | REMOVE the `flow-where-cross-project-capability-merge` entry from §7 Future Changes row #1 |
| Q5 | Delivery | Single PR, 1 commit, no chained, no `size:exception` |
| Q6 | Versioning | v0.9.0 (exit-code change from "always 0" to "0/1/2" = user-visible behavior change; semver-correct minor bump) |

## 12. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **R1** Spec drift root↔delta (Source: lines go stale) | Medium | Check 3 (REQ-ID existence in cited delta) is the safety net; Source: lines are the contract |
| **R2** Loss of test pointer | Medium | §4.b cites `tests/unit/test_cli_where_cross_project.py` (10 tests) explicitly |
| **R3** 400-line budget overrun | Low | Fallback: Approach A (skip §8 Drift Detection footer + skip §4.2 table row update) |
| **R4** §6.1 update wording conflicts with Batch E constraint #18 | Low | This PR does NOT touch §7 "stash" mention; §6.1 new wording uses only "REGENERATED", "byte-identical", "27111ed" — no stash/worktree trigger words |
| **R5** flow-where/spec.md densification (245 → ~325-365 lines) | Low | §0 "How to read this spec" callout + clear `---` separators for §3.b/§4.b/§5.b breaks |

## 13. Rollback Plan

**Single command**: `git revert <this-PR-commit>` + move `openspec/specs/flow-where/spec.md` + `openspec/specs/workspace/spec.md` back to pre-PR state + delete the regenerated delta spec. This is a doc-only change; rollback has zero code/test blast radius.

## 14. Dependencies

- Git commit `27111ed` must be reachable (it is — on `main` history).
- Phase 2 code (`cli.py:395-815`) is already on `main` HEAD `920d395` (shipped; not touched by this PR).
- `sdd-verify` needs awk or python for the 7 checks (any POSIX tool; works on Windows via Git Bash / WSL).
