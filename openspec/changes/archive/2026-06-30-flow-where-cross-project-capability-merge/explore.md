<!-- explore.md: flow-where-cross-project-capability-merge — Phase 4 of the workspace-intelligence arc. Doc-only follow-up to `workspace-capability-bootstrap` (commit `acb69c3`, 2026-06-30). Reads Phase 2 source from git history (commit `27111ed`, 2026-06-29) and merges it into `openspec/specs/flow-where/spec.md` as `REQ-V1.0.5..V1.0.10` + an update to `openspec/specs/workspace/spec.md` Cross-Impact §6.1 + §7. -->
# Explore: flow-where-cross-project-capability-merge

## Goal

Recover the missing Phase 2 (`flow-where-cross-project`) delta spec, integrate it into the canonical `flow-where` capability spec at `openspec/specs/flow-where/spec.md` as new REQs `REQ-V1.0.5..V1.0.10`, and resolve the reclassification follow-up named in `openspec/specs/workspace/spec.md` Cross-Impact §6.1 + §7 row #1. The change is **doc-only**; zero code, zero tests, zero `src/` / `tests/` modifications. The verify surface uses the same 7-check family-index pattern that `workspace-capability-bootstrap` locked at design #492 §4 (Source: line presence + path validity + REQ-ID existence + Cross-Impact/Future-Changes/Drift-Detection/Family-index-callout).

## Scope

### In Scope

1. **Phase 2 source recovery** — extract the lost delta spec from commit `27111ed` (`openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md`) and confirm it matches the running code in `src/flow_engineering/cli.py:395-815`.
2. **Regenerate missing Phase 2 delta spec** — write `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` (or `specs/cross-project-search/spec.md`) reusing the §2 evidence verbatim from Engram #456 + git commit `27111ed`.
3. **Additive integration** in `openspec/specs/flow-where/spec.md` — add a new **§2.b Cross-Project Search** section (or new sub-section under existing §3 Requirements) carrying the 6 new REQs `REQ-V1.0.5..V1.0.10` with `Source:` lines pointing to the regenerated delta spec. Zero modifications to existing `REQ-V1.0.1..V1.0.4` prose, public API surface, or the canonical versioning table row for v0.8.2.
4. **Workspace Cross-Impact resolution** — update `openspec/specs/workspace/spec.md` §6.1 to remove (or annotate) the "Phase 2 follow-up not yet done" framing and §7 row #1 to mark the follow-up as landed (or remove it from Future Changes). Plus update §4.2 versioning table row "Phase 2 follow-up lands" to record the merge SHA.
5. **Verify surface** — design + apply a 7-check family-index pattern (mirroring workspace-capability-bootstrap's 7 verify checks) covering Source: presence, cited path validity, cited REQ-ID existence in delta, Cross-Impact/Future-Changes/Drift-Detection/Family-index-callout presence.

### Out of Scope

- NO code modifications to `src/flow_engineering/cli.py`, `where.py`, `workspace.py`, or any other source file.
- NO test additions to `tests/unit/test_cli_where_cross_project.py` or anywhere else.
- NO modifications to any archived Phase 2 spec (it does not exist locally — only `status.md` survives at `openspec/changes/flow-where-cross-project/status.md`).
- NO modifications to other capability specs (`decision-drift`, `observability`, `prompt-registry`, `workspace-hygiene`, etc.).
- NO touching `openspec/changes/v1.1-followups/`.
- NO archive moves (`openspec/changes/flow-where-cross-project/` stays as-is; no `openspec/changes/archive/2026-06-29-flow-where-cross-project/` creation — the Phase 2 change was merged into main; only its orphan ceremony artifact is local).
- NO new subcommand, NO new flag on `flow where`, NO modification to the existing `--limit` or `--no-graph` flags.

## Phase 2 Recovery

### A. Engram Recovery (source of truth — preserved across sessions)

| Engram ID | Title | What it gives us |
|-----------|-------|------------------|
| **#456** | `flow-where-cross-project spec — 6 REQs + 7 BDD scenarios locked` | Phase 2 spec summary + REQ inventory (REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN). The actual REQ definitions + BDD scenarios live in the delta spec file committed at `27111ed` (NOT in #456 — #456 is a summary pointer). |
| **#454** | `flow-where-cross-project Phase 2 explore — cross-project where extension` | Locked 6 dirs + 3 formats + exit codes; `where_cmd` original location (`cli.py:421` pre-Phase-2); reference to `_run_search` + `_parse_hits` as the read-only seam; 10-test strategy. |
| **#455** | `flow-where-cross-project proposal — Phase 2 cross-project where extension` | Locked 3 output formats + 6 dirs + exit codes + --regex + --engram stub + ADDITIVE constraint; risks matrix. |
| **#457** | `flow-where-cross-project design — ADDITIVE where_cmd extension locked` | Helper signatures + Click extension pattern + search algorithm + AC9 preservation strategy. |
| **#458** | `Tasks phase for flow-where-cross-project — 7 TDD tasks` | T-1..T-7 = 7 tasks; total ~280 LOC; strict TDD; AC9 byte-identical guard preserved. |
| **#459** | `Applied flow-where-cross-project — 9/9 gates pass` | Apply summary + 3 learned details (custom `_parse_cross_project` workaround, per-directory `_run_search` calls for rg rc=2 fail-open, end-of-line `:` collision). |
| **#460** | `flow-where-cross-project verify-report — all 9 gates pass` | Branch HEAD = `c421540` (feat) + `d223516` (chore status); `cli.py` +402/-12; `test_cli_where_cross_project.py` +295; where.py unchanged. |
| **#461** | `Archived flow-where-cross-project — final close-out bookkeeping` | Branch `codex/flow-where-cross-project` LOCAL-ONLY at archive time; push deferred to user. |
| **#462** | `Merged + pushed flow-where-cross-project to main` | Merge commit `001651b` into main (no-ff); remote main HEAD = `001651b`; local main then updated. |

**Critical observation about Engram #456**: it lists 7 BDD scenarios in the title, but the actual delta spec.md committed at `27111ed` carries **11 BDD scenarios** (S1..S11 are 11 Given/When/Then blocks across 6 REQ blocks). Engram #456 undercounts; the git source is canonical.

### B. Git History Recovery (the lost delta spec content)

The local working tree on `main` HEAD `920d395` only retains `openspec/changes/flow-where-cross-project/status.md`. The full Phase 2 SDD ceremony was committed at commit **`27111ed` (2026-06-29, "chore(archive): add flow-where-cross-project artifacts")** — 6 files / 816 insertions:

| Path (at `27111ed`) | Lines | Status on main HEAD `920d395` |
|---------------------|-------|--------------------------------|
| `openspec/changes/flow-where-cross-project/design.md` | 234 | **MISSING** (lost between `27111ed` and `920d395`; no deletion commit in git log; working tree dropped them silently) |
| `openspec/changes/flow-where-cross-project/explore.md` | 105 | **MISSING** |
| `openspec/changes/flow-where-cross-project/proposal.md` | 108 | **MISSING** |
| `openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md` | 155 | **MISSING** — THIS IS THE DELTA SPEC |
| `openspec/changes/flow-where-cross-project/tasks.md` | 200 | **MISSING** |
| `openspec/changes/flow-where-cross-project/status.md` | (45) | **PRESENT** |

**Recovery command**: `git --no-pager show 27111ed:openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md` (preserved verbatim in this explore artifact as §Phase 2 REQ Inventory below; raw content recoverable in design phase).

The fact that the files were removed without a deletion commit between `27111ed..920d395` (no commit diff-filter=D reports any removal) suggests either (a) a `git checkout -f` after a stash, or (b) a manual `rm` outside of git's tracking — both recoverably via `git show <sha>:<path>`. **No data loss**: all 5 lost files are recoverable byte-identical from `27111ed`.

### C. Code Inspection (production code confirms Phase 2 is shipped on main HEAD)

Current main HEAD `920d395` carries Phase 2 in production (the feat was merged at `001651b`, chore status at `d223516`, archive at `27111ed`, then post-archive commits `27111ed..920d395` did NOT touch `src/flow_engineering/cli.py` per `git log --diff-filter=M` between those refs):

| Helper / Surface | Location in `src/flow_engineering/cli.py` | Phase 2 REQ it satisfies |
|------------------|------------------------------------------|--------------------------|
| `_CROSS_PROJECT_DIRS` tuple | L403-410 | REQ-CROSS-PROJECT-SCOPE (6-dir prospec) |
| `_CROSS_PROJECT_DEFAULT_LIMIT: int = 50` | L413 | REQ-CROSS-PROJECT-SCOPE (limit) |
| `_tag_match_type(file_path)` | L416-432 | REQ-CROSS-PROJECT-SCOPE (type tagging) |
| `_search_projects_for_query(root, query, regex_flag, limit)` | L435-489 | REQ-CROSS-PROJECT-SCOPE (orchestrator) |
| `_strip_trailing_colon(output)` | L492-513 | (workaround; rg `def foo():` collision) |
| `_parse_cross_project(output)` | L516-551 | (workaround; `where._parse_hits` colon-segmentation bug) |
| `_ascii_safe_local(s)` | L554-561 | REQ-DEFAULT-TEXT-FORMAT (ASCII-safe) |
| `_format_where_text(...)` | L564-601 | REQ-DEFAULT-TEXT-FORMAT |
| `_format_where_json(...)` | L604-637 | REQ-EXPLICIT-FORMAT-FLAG (json envelope) |
| `_format_where_tsv(hits)` | L640-653 | REQ-EXPLICIT-FORMAT-FLAG (tsv header) |
| `_validate_regex_or_exit(query)` | L656-668 | REQ-REGEX-OPT-IN (re.compile validation) |
| `_resolve_cross_project_root(...)` | L671-682 | REQ-CROSS-PROJECT-SCOPE (--root resolution) |
| `where_cmd` Click options added | L707-734 | REQ-EXPLICIT-FORMAT-FLAG + --regex + --engram + --root |
| `where_cmd` dispatch logic | L761-815 | REQ-EXIT-CODE-MAPPING (0/1/2) |
| `@main.command(name="where")` extended | L735-815 | All 6 REQs (additive) |

Code diff stat (per Engram #460): `cli.py` +402/-12, `tests/unit/test_cli_where_cross_project.py` +295 (10 tests). `src/flow_engineering/where.py` **unchanged** (Gate 6 PASS).

## Phase 2 REQ Inventory

The **canonical REQ wording** lives in `git show 27111ed:openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md`. The regenerated delta spec will preserve these 6 REQs verbatim:

### REQ-CROSS-PROJECT-SCOPE

> The system MUST search ONLY these 6 directories per project under `--root`: `src/` (type `code`), `internal/` (type `code`), `cmd/` (type `code`), `tests/` (type `test`), `openspec/` (type `sdd`), `graphify-out/` (type `graph`). Missing subdirectories MUST be silently skipped. Files outside these 6 directories MUST NOT be scanned regardless of query match.

### REQ-DEFAULT-TEXT-FORMAT

> Without `--format`, the command MUST emit ASCII-safe text grouped by project. Each project section MUST contain: `project_name` header line, then rows of `file:line  content` (tab-aligned), then a TOTAL summary line. Output MUST NOT contain box-drawing characters or non-ASCII bytes.

### REQ-EXPLICIT-FORMAT-FLAG

> `--format {text,json,tsv}` MUST produce exactly one of three formats. `--format=text` emits the ASCII-safe grouped text. `--format=json` emits a single JSON envelope. `--format=tsv` emits TSV with header.

### REQ-EXIT-CODE-MAPPING

> The system MUST exit with code `0` when matches are found OR when no matches exist (empty set). The system MUST exit with code `1` when NO matches are found. The system MUST exit with code `2` for errors: invalid `--regex` pattern, unreadable `--root` path, or other CLI-level failures.

### REQ-ENGRAM-STUB

> `--engram` flag is accepted with no behavior change in Phase 2. The flag MUST NOT cause an error. In `--format=json` output, `engram` field MUST be present as `{enabled: false, phase: "stub"}`.

### REQ-REGEX-OPT-IN

> `--regex` flag enables regex matching (case-insensitive). Without `--regex`, matching is case-insensitive substring. When `--regex` is set, `re.compile(query)` is called at the CLI boundary to validate; exit 2 on `re.error`.

## BDD Scenario Inventory

11 Given/When/Then scenarios in the delta spec (verified via `git show 27111ed:...spec.md`):

| # | REQ | Scenario | What it asserts |
|---|-----|----------|------------------|
| S1 | REQ-CROSS-PROJECT-SCOPE | Cross-project search scans exactly 6 dirs | `proj-b/node_modules/` never scanned even when content matches |
| S2 | REQ-CROSS-PROJECT-SCOPE | Missing directory silently skipped | no error on missing `internal/` subdir |
| S3 | REQ-DEFAULT-TEXT-FORMAT | Default text output with multiple projects | `proj-a` header → rows → TOTAL line; ASCII-safe |
| S4 | REQ-DEFAULT-TEXT-FORMAT | Empty match set renders "(no matches)" | exit 0 on no-match (note: conflicts with REQ-EXIT-CODE-MAPPING S5; see Open Question Q3) |
| S5 | REQ-EXPLICIT-FORMAT-FLAG | --format=json envelope structure | first-key = version:"1"; key order `version, root, query, format, results, totals` |
| S6 | REQ-EXPLICIT-FORMAT-FLAG | --format=tsv header and body | header `project\tfile\tline\ttype\tcontent`; `\n` escape in content |
| S7 | REQ-EXIT-CODE-MAPPING | Exit 0 on match | grep convention |
| S8 | REQ-EXIT-CODE-MAPPING | Exit 1 on no match | grep convention |
| S9 | REQ-EXIT-CODE-MAPPING | Exit 2 on invalid regex | stderr mentions regex parse failure |
| S10 | REQ-ENGRAM-STUB | --engram flag accepted with no-op | output identical to invocation without --engram |
| S11 | REQ-REGEX-OPT-IN | Invalid regex exits 2 | stderr mentions regex parsing failure |

Plus 10 NEW unit tests in `tests/unit/test_cli_where_cross_project.py` (per Engram #460 Gate 1): `test_where_cmd_{text_default_groups_by_project, json_envelope_structure, tsv_header_and_body, regex_valid_and_invalid, limit_caps_hits, root_resolution, exit_code_trio, engram_noop_identity, byte_identical_across_invocations, scope_discipline_excludes_node_modules}`.

Plus 10 acceptance criteria in the delta spec's "Acceptance Criteria" section (1-10 from `git show 27111ed:...spec.md`).

## Integration Strategy

**Target**: `openspec/specs/flow-where/spec.md` (245 lines, family-index format matching `workspace/spec.md`).

**Approach**: ADDITIVE — preserve existing v0.8.2 archive status at L4-19, existing REQs REQ-V1.0.1..V1.0.4 at L62-145, and existing public API surface + CLI surface at L147-213. Append a new **§2.b Cross-Project Search (Phase 2)** section (or split into §2.b for the sub-capability and §3.b for new REQs) + extend the Versioning table with a **v0.9.0** row pointing to the regenerated delta spec.

**Structural additions** (additive only):

1. **§2.b Capability boundary extension** — extend the §2 Purpose list with a new bullet: "**Cross-project scope** (Phase 2): `flow where "<query>" --root PATH [--format {text,json,tsv}] [--regex] [--engram]` fans out across N projects under `--root`, walking 6 locked prospec dirs (`src/ internal/ cmd/ tests/ openspec/ graphify-out/`) per project; renders 3 output formats; respects exit codes `0/1/2` (grep convention)."
2. **§3.b Cross-Project sub-section** — add 6 new REQs `REQ-V1.0.5..V1.0.10` (the 6 from Phase 2) with `Source:` lines pointing to the regenerated delta spec. **Wording strategy**: synthesized summary (mirroring workspace-capability-bootstrap design §3) — full Given/When/Then stays in the delta spec.
3. **§4.b Public API additions** — extend the §4 public API surface block with the new private helpers (`_search_projects_for_query`, `_format_where_*`, `_validate_regex_or_exit`, `_resolve_cross_project_root`, `_tag_match_type`, `_parse_cross_project`, `_strip_trailing_colon`, `_ascii_safe_local`) marked as private (leading underscore).
4. **§5.b CLI surface additions** — extend the §5 CLI surface block with the new flags and exit-code contract. Document `--pretty` from `cli.py:705` while we're here as a forward-looking flag (it's already in the code at L701-706).
5. **§6 Cross-Impact row update** — add a new row: `cross-project-search (Phase 2, v0.9.0+) → REQ-CROSS-PROJECT-SCOPE … REQ-REGEX-OPT-IN | EXTENSION — REQ-V1.0.5..V1.0.10 build on REQ-V1.0.1..V1.0.4 (rg/grep seam + Exit 0); additive to `where_cmd` per `where.py` read-only contract`. Document in §6.x that Phase 2 reuses `_run_search` from where.py (read-only) and the `where()` module API stays unchanged.
6. **§7 Versioning table** — add a **v0.9.0** row (or `v0.8.3` — see Open Question Q1) for the `flow-where-cross-project` merge at commit `001651b`. The table currently only lists v0.8.2.
7. **§8 Drift Detection footer** — add a new section (mirror workspace/spec.md §8) documenting the source-of-truth rule, acceptance check, delta-evolution protocol, family-shape protocol.

**Cross-Impact row reversal**: The workspace spec §6.1 currently states Phase 2 belongs to `flow-where` (the resolution). With this PR, §6.1's "Action in this PR" should be RETROACTIVE — Phase 2 is no longer just "documented as a follow-up"; it has been MERGED into the flow-where family. §7 row #1 (`flow-where-cross-project-capability-merge`) should be removed from Future Changes once this change lands (since it IS this change). §4.2 versioning table row "Phase 2 follow-up lands" should record the actual merge SHA from this PR.

## Cross-Impact Update Plan

### Updates to `openspec/specs/workspace/spec.md`

| Section | Current state | After this PR |
|---------|---------------|---------------|
| §6.1 (L274-290) | "Phase 2 (`flow-where-cross-project`) **belongs to `flow-where`, not `workspace`**. This is a documentation statement only — no files are moved in this PR." | "Phase 2 was reclassified to `flow-where` per the user-locked principle *no mezclar 'inventario/estado/higiene del workspace' con 'búsqueda/retrieval de contenido'*. The follow-up change **`flow-where-cross-project-capability-merge`** (this PR) merged Phase 2 into the `flow-where` root spec as REQ-V1.0.5..V1.0.10. See `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` (the regenerated delta spec)." |
| §6.1 Evidence bullet 5 (L286) | "Phase 2's delta spec is MISSING locally... Full REQ content preserved in Engram #456..." | Replace with: "Phase 2's delta spec has been REGENERATED at `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` (preserved verbatim from git commit `27111ed`, 2026-06-29). Source content also preserved in Engram #456 (summary pointer) + commit `27111ed` (canonical content)." |
| §7 Future Changes row #1 (L296) | `flow-where-cross-project-capability-merge` (status: pending) | **REMOVE** this row (it IS this change; no longer future). |
| §7 Future Changes note (L16) | "Carry-forwards documented in Future Changes (§7): `flow-where-cross-project-capability-merge` (Phase 2 follow-up)..." | Update to list only the remaining carry-forwards (Phase 5 dashboard, optional workspace-hygiene, backup-retention-policy, R1/R3/R4 deferred, artifact-hygiene). Remove `flow-where-cross-project-capability-merge`. |
| §4.2 versioning table row (L241) | "Phase 2 follow-up lands | `flow-where-cross-project-capability-merge` | No change to workspace root spec; `flow-where/spec.md` gains REQ-V1.0.5..V1.0.X" | Mark as RESOLVED: "Phase 2 follow-up landed (this PR). `flow-where/spec.md` gained REQ-V1.0.5..V1.0.10." |

### Updates to `openspec/specs/flow-where/spec.md`

| Section | Current state | After this PR |
|---------|---------------|---------------|
| §4 Requirements (L62-145) | Only REQ-V1.0.1..V1.0.4 | Add §3.b (or §4.b) with REQ-V1.0.5..V1.0.10 + Source: lines |
| §2 Purpose (L21-37) | Lists 3 backends + 4 numbered bullets | Add new bullet at L37: "**Cross-project scope** (Phase 2, v0.9.0+): --root PATH + --format + --regex + --engram + 6 prospec dirs; 3 output formats; exit codes 0/1/2." |
| §4 Public API (L147-176) | Only public symbols for v0.8.2 | Add §4.b Private helpers block listing Phase 2 helpers with leading-underscore notation |
| §5 CLI surface (L184-213) | Current `--limit`, `--no-graph`, `--help` only | Add §5.b Phase 2 CLI surface: `--root`, `--format {text,json,tsv}`, `--regex`, `--engram` + new exit-code contract |
| §6 Cross-Impact (L215-223) | Lists 5 relationships | Add row: `cross-project-search (v0.9.0+, REQ-V1.0.5..V1.0.10) → EXTENSION — uses REQ-V1.0.1..V1.0.4 seam (rg/grep) but adds 6-dir prospec + 3 formatters + exit-code mapping; reuses `_run_search` from where.py (read-only).` |
| §7 Versioning table (L227-229) | Only v0.8.2 row | Add v0.9.0 row pointing to the regenerated Phase 2 delta spec |
| (NEW) §8 Drift Detection | None | Mirror workspace/spec.md §8 footer pattern with source-of-truth rule + acceptance check |

**Notes on existing content preservation**: §4 Requirements for REQ-V1.0.1..V1.0.4 (L62-145) is NOT modified. §4 Public API (L147-176) is append-only (Phase 2 helpers added in a new §4.b block). §5 CLI surface (L184-213) is append-only (§5.b). §6 Cross-Impact gains one new row (additive). §7 Versioning table gains one new row (additive).

## Open Questions

1. **Versioning bump** — current `flow-where/spec.md` Versioning table lists **v0.8.2** (the `flow-where-mvp` MVP). Should Phase 2 land as `v0.8.3` (patch — additive, no breaking) or `v0.9.0` (minor — new sub-capability surface with new CLI flags + exit-code change)? **Default**: `v0.9.0` (Phase 2 changes the exit-code contract from "always 0" to "0/1/2" — semver-correct for a minor bump because grep convention is a user-visible behavior change). **Trade-off**: `v0.8.3` is conservative but undersells the new CLI surface.

2. **Cross-Project REQ numbering** — should Phase 2 REQs be `REQ-V1.0.5..V1.0.10` (continuous with v1.0.x) or a new generation like `REQ-V2.0.1..V2.0.6` (Phase 2 is a separate sub-capability from the MVP)? **Default**: `REQ-V1.0.5..V1.0.10` (continuous — REQ-V1.0.X namespace spans all flow-where generations; matches the workspace spec pattern where REQ-WORKSPACE-* carries 7 root REQs across multiple phases).

3. **SPEC scenario S4 conflict** — S4 in the recovered delta spec asserts "Empty match set renders `(no matches)` AND exit code is 0". REQ-EXIT-CODE-MAPPING (also from the recovered delta spec) asserts "Exit code `0` when matches are found OR when no matches exist". These are CONSISTENT (both say exit 0 on no-match). BUT the current `flow-where` v0.8.2 contract is exit 0 always (REQ-V1.0.4 "Exit code `0` always") — so Phase 2 v0.9.0 would REPLACE "always 0" with "0=match-or-empty, 1=no-match". **This is a documented behavior change** — must be called out in the canonical spec's §4.b REQ-V1.0.7 (or wherever EXIT-CODE-MAPPING lands).

4. **Workspace Cross-Impact update timing** — workspace `spec.md` Cross-Impact §6.1 currently documents Phase 2 as "documented as a follow-up, not moved". When this PR lands, §6.1 must be updated. The question is whether the workspace update goes in the SAME PR (single commit, tighter audit trail) or a SEPARATE PR (cleaner separation of concerns). **Default**: SAME PR (single atomic change, easier to revert). **Trade-off**: SEPARATE PRs would let each side be reviewed in isolation but doubles the ceremony for a doc-only change.

5. **`--pretty` flag** — Phase 2 of the workspace-intelligence effort left a `--pretty` flag in `cli.py:701-706` that is "Reserved for future Unicode output (Opción media UX work)" — it's a forward-looking no-op. Should this PR document `--pretty` in the new `flow-where/spec.md` §5.b CLI surface, or leave it OOS? **Default**: DOCUMENT it briefly (one sentence noting it's reserved for future work) since it's part of the existing Click surface and reviewers reading the canonical spec would notice the gap.

6. **`--limit` bump from 20 → 50** — Phase 2 bumps the default `--limit` from `where_mod.DEFAULT_LIMIT = 20` to `_CROSS_PROJECT_DEFAULT_LIMIT = 50` (cli.py:413, L789-792). The current `flow-where/spec.md:154` documents `DEFAULT_LIMIT: int = 20`. Should this PR update line 154 to `20` (legacy MVP) + `50` (cross-project scale) as TWO constants, or keep the canonical spec at `20` and note the cross-project bump in §5.b? **Default**: keep canonical spec at `20` (MVP value) and document the cross-project bump in §5.b ("`--limit` defaults to 50 in cross-project mode; legacy single-project mode retains 20").

7. **Existing `has_engram` field** — Phase 2's `engram: {enabled: false, phase: "stub"}` in the JSON envelope is separate from the Phase 1 `has_engram` field on `flow projects ls`. Should the canonical spec explicitly cross-reference both stubs (so readers know they are DIFFERENT stubs in DIFFERENT commands), or are they clearly separate enough? **Default**: cross-reference briefly to avoid reader confusion (one sentence in §6 Cross-Impact noting "Phase 2's `--engram` is the cross-project envelope stub; Phase 1's `has_engram` field is the projects-ls stub — independent").

8. **Source: line grammar for REQ-V1.0.5..V1.0.10** — workspace spec uses `**Source:** \`<path>\` §<REQ-IDs>` (single backtick-path + `§`-prefixed IDs). Should Phase 2's Source: lines use the SAME grammar, or Phase 2's own loose style ("REQs from the cross-project delta spec")? **Default**: SAME grammar (consistency with workspace spec; one verification surface).

## Approach Candidates

### Approach A — Minimal (regenerate delta spec + minimal flow-where update)

**Scope**: Regenerate `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` from git commit `27111ed` (105-200 LOC). Append ONE new sub-section to `flow-where/spec.md` under existing §3 Requirements (or a new §3.b) with the 6 REQs and their Source: lines. Update `workspace/spec.md` §7 row #1 to mark as landed. NO new sections, NO Cross-Impact row in flow-where, NO Drift Detection footer.

**Pros**: smallest diff (well under 400-line budget); fastest apply; minimal review surface; matches the spirit of "doc-only follow-up".
**Cons**: skips the verify-check family-index pattern that workspace-capability-bootstrap established; leaves `flow-where/spec.md` inconsistent with `workspace/spec.md` (one has §8 Drift Detection, the other doesn't); the Cross-Impact table doesn't grow (so readers don't see Phase 2 in the family shape).
**Effort**: ~150-200 LOC markdown.
**Verdict**: good for a quick "debt-clearing" PR; not as good for "periodic map-ordering" hygiene (Engram #489).

### Approach B — Comprehensive (mirror workspace-capability-bootstrap's pattern) — **RECOMMENDED**

**Scope**: Regenerate delta spec + add 6 REQs to flow-where/spec.md WITH Source: lines + add §2.b capability boundary extension + add §4.b private-helpers block + add §5.b CLI surface additions + add Cross-Impact row + add §7 Versioning row (v0.9.0) + add new §8 Drift Detection footer (mirroring workspace pattern) + update workspace/spec.md §6.1 + §7 row #1 + §4.2 versioning table.

**Pros**: mirrors the workspace-capability-bootstrap design (verifiability + maintainability per Engram #491, #493); introduces 7 verify checks paralleling workspace-spec design #492; closes the "specs are decorative markdown" risk by giving flow-where the same drift-detection surface; satisfies the "periodic map-ordering" discipline (Engram #489); all 5 evidence points from workspace §6.1 are resolved.
**Cons**: bigger diff (~300-450 LOC markdown); requires more careful editing of flow-where/spec.md (additive only); 7 verify checks need to be designed and runnable; may exceed 400-line budget if not careful.
**Effort**: ~300-450 LOC markdown.

### Approach C — Pure retrieval (just regenerate the missing delta spec)

**Scope**: Only regenerate `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` from git commit `27111ed`. Do NOT touch `flow-where/spec.md` or `workspace/spec.md` (defer integration to a future change).

**Pros**: simplest possible change; no risk of disturbing the canonical specs; satisfies the "recover the lost artifact" minimal goal.
**Cons**: leaves the reclassification follow-up UN-resolved (workspace §6.1 + §7 row #1 still say "follow-up not yet done"); leaves the canon (flow-where root spec) without Phase 2 REQs; the user explicitly chose Approach B for `workspace-capability-bootstrap` to avoid this anti-pattern.
**Effort**: ~150 LOC markdown.

### Recommended Approach

**Approach B (Comprehensive)** — it mirrors the workspace-capability-bootstrap pattern that the user explicitly approved for the workspace root spec. It is the same `verifiable architecture` discipline Engram #491 + #493 + #494 document. Approach A leaves drift-detection surface inconsistent (flow-where has no §8, workspace does); Approach C leaves the reclassification follow-up unresolved. The 400-line budget fits with some care (~300-450 LOC target — tight but achievable with the same `awk/python verify-checks` pattern as workspace-capability-bootstrap design #492).

## Tech Debt interactions

| Item | State | This change's interaction |
|------|-------|----------------------------|
| 3 pre-existing ruff errors (OOS, per Phase 4 close-out) | `cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292` | **UNTOUCHED.** Doc-only change; same baseline. No new ruff errors. |
| 0 pre-existing test failures | confirmed at `001651b` merge (1235/1235 PASS) | **UNTOUCHED.** Baseline preserved. |
| AC9 byte-identical guard | `test_flow_projects_ls_json_byte_identical_envelope` | **UNTOUCHED.** No code modifications. |
| `openspec/changes/v1.1-followups/` | pre-existing local untracked state | **UNTOUCHED.** (Locked constraint.) |
| `_detect_project_markers` (Phase 1) | read-only | **UNTOUCHED.** |
| `_resolve_projects_root` (Phase 3) | read-only | **UNTOUCHED.** |
| `where.py` module API | read-only per Phase 2 design | **UNTOUCHED.** |
| `_parse_cross_project` + `_strip_trailing_colon` workarounds in `cli.py:516-551, 492-513` | documented in Engram #459 as Phase 2 workarounds for `where._parse_hits` colon-segmentation bug | **DOCUMENTED in this change's §4.b private-helpers** — readers should know these exist; possible future change `flow-where-parse-fix` could fix `where._parse_hits` and remove the workarounds. Out of scope here. |
| Missing Phase 2 SPEC.md (status.md survives, everything else lost) | the debt this PR clears | **RESOLVED.** Delta spec regenerated at `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md`. |
| Workspace §6.1 "follow-up not yet done" framing | pre-existing follow-up debt | **RESOLVED.** Workspace Cross-Impact §6.1 + §4.2 + §7 row #1 all updated to reflect the merge. |
| Workspace §7 "stash/worktree handling" mention | forwarded per Batch E constraint #18 | **UNTOUCHED.** (Not in scope; not modified by this PR.) |

## Forecast

| Metric | Value |
|--------|-------|
| `explore.md` (this file) | 380 lines (under 400 budget by 5%) |
| Estimated `proposal.md` | ~250-350 lines |
| Estimated `specs/flow-where-cross-project/spec.md` (regenerated delta spec) | 155 lines (preserved verbatim from `27111ed`) |
| Estimated updates to `openspec/specs/flow-where/spec.md` | +80-120 lines (additive only) |
| Estimated updates to `openspec/specs/workspace/spec.md` | +30-50 lines net (replace 3 sections, remove 1 row from Future Changes) |
| Estimated `design.md` | ~250-350 lines (7 verify checks paralleling workspace-capability-bootstrap design #492) |
| Estimated `tasks.md` | ~150-250 lines (mechanical, ~7-9 tasks like workspace-capability-bootstrap #494) |
| Estimated apply (doc-only) | ~10-15 minutes (mostly Edit tool calls + git add + commit) |
| Estimated verify (7 verify checks + baseline gates) | ~15-20 minutes |
| Estimated archive (move change folder + write archive-report) | ~15-20 minutes |
| **Total wall-clock** | **~2-3 hours** for full explore → propose → spec → design → tasks → apply → verify → archive |
| **Single PR or chained?** | Single PR. All changes (regenerate delta + flow-where spec update + workspace spec update) belong together atomically. |
| **400-line budget risk** | Low (~300-450 LOC target; well within budget for doc-only) |
| **`size:exception` needed?** | No |
| **Decision needed before apply?** | No |

## Verdict

**Recommended approach: B (Comprehensive)** — mirror the workspace-capability-bootstrap pattern. The user's principle from Engram #491 ("design for doc-only changes = design for verifiability") and Engram #493 ("specs must be maintainable architecture, not decorative markdown") both point to the same answer: introduce the 7-check verify surface for `flow-where/spec.md` paralleling workspace-spec's, give Phase 2 its Source: lines + Cross-Impact row + Drift Detection footer.

**Why not Approach A**: leaves flow-where/spec.md inconsistent with workspace/spec.md (the latter has §8 Drift Detection, the former doesn't). Reviewers reading both canonical specs side-by-side will notice the asymmetry.

**Why not Approach C**: leaves the "Phase 2 follow-up not yet done" framing in workspace/spec.md §6.1 + §7 row #1, which the user explicitly wanted resolved (it's the second-highest-priority follow-up after Phase 5 dashboard).

**Why B aligns with the user's "no mezclar ... con ..." principle (Engram #487)**: by giving Phase 2 a real home in `flow-where/spec.md` + resolving the workspace-side follow-up, the user-locked domain boundary becomes falsifiable (readers can SEE in the canonical spec where each capability begins and ends).

**Risk-acceptance posture**: this is a doc-only change with zero code/test modifications. The blast radius is exactly the 2 canonical specs + 1 regenerated delta spec. Strict TDD is OFF per the change precondition. The 7 verify checks (mirroring workspace-capability-bootstrap) are deterministic (awk/python regex/grep patterns) and runnable by automation.

**Next step**: hand off to `sdd-propose` for the proposal phase. The proposal will lock Approach B, define the full AC inventory (regenerate delta + 6 REQs in flow-where + workspace updates), and quote the user-locked principle as the rationale anchor.

## Risks

1. **R1 (Medium) — Spec drift between regenerated delta and canonical flow-where spec** (mitigated by Source: lines + verify check 3 analogous to workspace #492 Check 3): the 6 REQs in `flow-where/spec.md` §4.b must cite the regenerated delta via Source: lines with the exact REQ IDs (REQ-CROSS-PROJECT-SCOPE etc.). If a future drift correction updates wording in one and not the other, readers see a divergence. Mitigation: same `sdd-verify` discipline from workspace #492; verify check 3 (REQ-ID existence in cited delta) is the safety net.

2. **R2 (Medium) — Loss of test artifact on the regenerated delta spec** (mitigated by Engram #456 + git commit `27111ed` as recovery sources): the regenerated delta's "Acceptance Criteria" + 11 BDD scenarios cite the 10 unit tests in `tests/unit/test_cli_where_cross_project.py`. The canonical `flow-where/spec.md` cross-impact table should reference these test names (or the file path) so reviewers can verify the ACs are still tested. Mitigation: §4.b private-helpers block includes a one-liner "see `tests/unit/test_cli_where_cross_project.py` (10 tests)" pointer.

3. **R3 (Low) — 400-line review budget** if the doc-only diff exceeds 400 lines despite being under the "no behavior change" envelope. Mitigation: Phases A and C are the alternatives; Approach B targets ~300-450 LOC. If apply-time measurement shows > 400 LOC, fall back to Approach A (skip Drift Detection footer + skip workspace §4.2 table row update).

4. **R4 (Low) — Workspace §6.1 update wording conflicts with batch E constraint #18 ("stash/worktree" forward-looking scope description)** (same precedent as Engram #498 Special Cases §7 "stash" verification). Mitigation: this PR does not touch §7 "stash" mention; only §6.1, §4.2, and §7 row #1. Verify report must explicitly acknowledge if/when §6.1 update introduces new words that could trigger Batch E constraint #18 (low likelihood — §6.1 is about PROJECT identity boundaries, not about hygiene actions).

5. **R5 (Low) — Existing `flow-where/spec.md` §4 prose (REQ-V1.0.1..V1.0.4) carries a lot of granularity (path prefixes, helper signatures, return types)**; adding §4.b will visually densify the spec beyond 245 → ~325-365 lines. Mitigation: §4.b is a separate sub-section (clear visual break via `---` separators); add a §0 "How to read this spec" callout in `flow-where/spec.md` clarifying that REQs REQ-V1.0.1..V1.0.4 are MVP single-project and REQ-V1.0.5..V1.0.10 are cross-project (mirroring workspace spec's "Family index, not canonical source" callout).

## Cross-references (Engram + git)

### Engram observations (preserved across sessions, this change's inputs)

- `#454` Phase 2 explore (105 lines recovered in git `27111ed`)
- `#455` Phase 2 proposal
- `#456` Phase 2 spec summary + 6 REQ titles + 7 BDD titles (UNDERCOUNTS scenarios — actual is 11)
- `#457` Phase 2 design — helper signatures locked
- `#458` Phase 2 tasks — 7 TDD tasks
- `#459` Phase 2 apply — 9/9 gates, 3 learned details (workarounds)
- `#460` Phase 2 verify — `c421540` (feat) + `d223516` (chore status); +402/-12 cli.py, +295 tests
- `#461` Phase 2 archive — branch LOCAL-ONLY at archive time
- `#462` Phase 2 merge + push — `001651b` (no-ff) → remote main

### Workspace capability anchor observations

- `#486` workspace-bootstrap explore (Phase 2 reclassification surfaced)
- `#487` Pattern: Workspace vs Where — domain separation principle (USER-LOCKED)
- `#488` workspace-bootstrap proposal (Approach B locked)
- `#489` Pattern: Periodically stop adding features and order the map (USER-LOCKED)
- `#490` workspace-bootstrap spec — 7 root REQs (the reference for this PR's structure)
- `#491` Pattern: Design phase for doc-only changes = design for verifiability (USER-LOCKED)
- `#492` workspace-bootstrap design — 7 verify checks at §4 (the reference for this PR's verify surface)
- `#493` Pattern: Specs must be maintainable architecture, not decorative markdown (USER-LOCKED)
- `#494` workspace-bootstrap tasks — 9 mechanical tasks from §4 verify checks (the reference for this PR's tasks)
- `#498` workspace-bootstrap archive report at commit `acb69c3`
- `#499` Session summary: insyd (workspace-capability-bootstrap closed)
- `#500` Pattern: Clean architectural trail is craftsmanship, not busywork (USER-LOCKED)
- `#501` SDD preflight for THIS change (flow-where-cross-project-capability-merge)

### Git references

- `27111ed` (2026-06-29) — Phase 2 SDD ceremony committed (the source of the lost delta spec). SHA recoverable via `git --no-pager show 27111ed:openspec/changes/flow-where-cross-project/specs/cross-project-search/spec.md`.
- `c421540` — Phase 2 feat commit (`feat(where): add cross-project search with --format + 6-dir prospec + --regex/--engram`).
- `d223516` — Phase 2 chore status commit.
- `001651b` — Phase 2 merge commit (no-ff) into main.
- `920d395` — main HEAD (post workspace-capability-bootstrap close-out).

### Files this change touches

- `openspec/changes/flow-where-cross-project-capability-merge/specs/flow-where-cross-project/spec.md` (NEW, ~155 lines, regenerated from `27111ed`)
- `openspec/specs/flow-where/spec.md` (modified, additive — extends from 245 → ~325-365 lines)
- `openspec/specs/workspace/spec.md` (modified, edit-only — §6.1 + §4.2 + §7 row #1 updated; net change +30 to +50 lines or net delta ~0 after the §7 row removal)

### Files this change does NOT touch (locked constraints)

- `src/flow_engineering/cli.py` (read-only; Phase 2 code is the deliverable, this PR is the documentation of that code)
- `src/flow_engineering/where.py` (read-only per Phase 2 design)
- `tests/unit/test_cli_where_cross_project.py` (read-only; Phase 2 tests are the deliverable)
- `openspec/changes/v1.1-followups/` (locked constraint)
- `openspec/changes/flow-where-cross-project/` (orphan ceremony folder — stays as-is, only `status.md` is local)
- `openspec/changes/workspace-capability-bootstrap/` (already archived to `openspec/changes/archive/2026-06-30-workspace-capability-bootstrap/`)
- Any other spec or code file.
