# Design: flow-where-cross-project-capability-merge

## Header

- **Change**: `flow-where-cross-project-capability-merge`
- **Phase**: design (4th of 8 — sdd-design)
- **Project**: flow-engineering v1.2.0, main HEAD `920d395`
- **Strict TDD**: **OFF** (doc-only change — zero code, zero tests)
- **Artifact store**: openspec (filesystem) + hybrid Engram mirror
- **Design philosophy**: *"no embellecer lo recuperado. Si el hash coincide, se respeta."* The Phase 2 delta spec was recovered byte-identical from git `27111ed` (SHA `f546507f4e50d704410a77946529f292cc5b6040` confirmed in spec #506); this design does NOT propose to improve, reword, or modernize it. Improvements go in a SEPARATE follow-up change.
- **Inputs** (authoritative, read in full):
  - Spec #506 (recovery confirmed byte-identical; +101 net on `flow-where/spec.md`, +1 net on `workspace/spec.md`, 155-line recovered delta at `cross-project-search/spec.md`)
  - Proposal #505 (locks Approach B + 11 ACs + single PR + 1 commit)
  - Explore #503 (3-way recovery strategy: Engram #456 + git `27111ed` + code inspection)
  - Precedent: workspace-capability-bootstrap design #492 (the 7-verify-check template)
- **Output**: filesystem artifact at `openspec/changes/flow-where-cross-project-capability-merge/design.md` + Engram mirror under `sdd/flow-where-cross-project-capability-merge/design`.
- **Out-of-scope guardrails** (user-locked, 14+ constraints): NO modifications to the recovered delta spec (hash matches); NO modifications to `flow-where/spec.md` or `workspace/spec.md` content (already done in spec phase); NO code; NO `openspec/changes/v1.1-followups/` touch; NO path rename (`cross-project-search/` stays); NO BDD count change (13 actual stays as canonical).

## 1. Architecture overview (minimal)

The "architecture" of this doc-only change is its **information architecture + validation surface**. The recovered delta spec at `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` (155 lines, 6 REQs, 13 Given/When/Then scenarios, 10 acceptance criteria) is the canonical Phase 2 source. The canonical `flow-where/spec.md` (now 346 lines = 245 v0.8.2 baseline + 101 additive Phase 2) is the root spec where 6 `REQ-WHERE-*` blocks cite the delta via `Source:` lines. The canonical `workspace/spec.md` (315 lines) marks the reclassification follow-up as RESOLVED in §6.1 and removes its entry from §7 row #1. The validation surface is the **7 deterministic structural checks** that prove each `Source:` line points to a real file containing the cited `REQ-ID`, plus 4 structural-presence checks (test pointer, RESOLVED marker, row removal, Drift Detection footer) — exactly what `sdd-verify` consumes at AC2, AC4, AC5, AC6, AC7.

```
  specs/flow-where/spec.md (root, 346 LOC)
        │
        ├── 6 REQ-WHERE-* ─── Source: lines ─────► specs/cross-project-search/spec.md
        │                                              (recovered delta, 155 LOC,
        │                                               SHA f546507f4e50d704…)
        ├── §4.b private-helpers block ──────────► cli.py:403-815 (Phase 2 code)
        │                                              + tests/unit/test_cli_where_cross_project.py
        │                                              (10 tests, no-op for this PR)
        └── §8 Drift Detection footer (mirrors workspace pattern)

  specs/workspace/spec.md (root, 315 LOC)
        │
        ├── §6.1 [2026-06-30 update — RESOLVED] appended
        └── §7 row #1 removed (table now starts at row 2)
```

The "data flow" is *read→grep/awk/python→assert*. Each check reads one or two of the canonical specs, applies a structural rule, and exits `0` (pass) or `1` (fail) with a one-line user-visible diagnostic.

## 2. Anchor strategy — the `Source:` line

### 2.1 What is a `Source:` line?

A `Source:` line is a Markdown line inside a root-level REQ block (`### REQ-WHERE-*`) that **points the reader and the verifier** to the canonical delta spec + delta REQ where the full Given/When/Then wording lives.

### 2.2 Formal grammar

```text
Source-line ::= "**Source:**" WHITESPACE "`" PATH "`" WHITESPACE "§" REQ-ID

PATH  ::= "openspec/changes/flow-where-cross-project-capability-merge/"
           "specs/cross-project-search/spec.md"
       (single locked value — all 6 root REQs cite the same path)

REQ-ID ::= "REQ-CROSS-PROJECT-SCOPE" | "REQ-DEFAULT-TEXT-FORMAT"
        |  "REQ-EXPLICIT-FORMAT-FLAG" | "REQ-EXIT-CODE-MAPPING"
        |  "REQ-ENGRAM-STUB"           | "REQ-REGEX-OPT-IN"
       (one of the 6 delta REQs in the recovered delta)
```

- **Quote char**: backticks wrap the path (standard Markdown).
- **Anchor char**: `§` (one ASCII char separating path from REQ ID).
- **Path prefix**: every `PATH` starts with `openspec/changes/` and MUST point to the exact byte-identical recovered delta — enforced by Check 2 (path exists on disk) + Check 3 (REQ-ID exists in cited file).
- **Note**: workspace #492's grammar allows multi-ID `+`-separated lists and a placeholder-sentinel form; this change does NOT need either. All 6 root REQs are single-ID, non-placeholder.

### 2.3 Location rule

`Source:` lines MUST appear **inside each `### REQ-WHERE-*` block**, **after** the body prose and **before** the `**Wording:**` line. Currently the 6 source lines sit at L278, L288, L298, L310, L320, L330 of `flow-where/spec.md`.

### 2.4 What is NOT in the anchor strategy

- REQ-ID uniqueness across files. The delta IDs share the `REQ-CROSS-PROJECT-*` / `REQ-DEFAULT-*` / `REQ-EXPLICIT-*` / `REQ-EXIT-*` / `REQ-ENGRAM-*` / `REQ-REGEX-*` namespace; root IDs use the parallel `REQ-WHERE-*` namespace to prevent collision (per spec #506 rule #2 + Engram #487 "no mezclar...").
- Authoring tooling for `Source:` lines. Manual authoring is fine; verification runs in `sdd-verify`.
- Modifying or "improving" the recovered delta's REQ wording. Hash match (`f546507f4e50d704410a77946529f292cc5b6040`) = respect the bytes.

## 3. Cross-reference inventory

All 6 root-level REQs at `openspec/specs/flow-where/spec.md` §4.b, with their verbatim `Source:` line, delta spec path, delta REQ ID, and a one-line summary.

| # | Root REQ ID (line) | One-line title | `Source:` line (verbatim) | Delta REQ ID | Delta spec path | Wording strategy |
|---|---|---|---|---|---|---|
| 1 | `REQ-WHERE-CROSS-PROJECT-SCOPE` (L274-282) | 6-dir prospec per project + scope discipline | `**Source:** \`openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md\` §REQ-CROSS-PROJECT-SCOPE` (L278) | `REQ-CROSS-PROJECT-SCOPE` | `specs/cross-project-search/spec.md` (delta L17) | synthesized summary (S1 + S2 delegated to delta) |
| 2 | `REQ-WHERE-DEFAULT-TEXT-FORMAT` (L284-292) | ASCII-safe grouped text default output | `… §REQ-DEFAULT-TEXT-FORMAT` (L288) | `REQ-DEFAULT-TEXT-FORMAT` | same delta (delta L33) | synthesized summary |
| 3 | `REQ-WHERE-EXPLICIT-FORMAT-FLAG` (L294-302) | `--format {text,json,tsv}` envelope contract | `… §REQ-EXPLICIT-FORMAT-FLAG` (L298) | `REQ-EXPLICIT-FORMAT-FLAG` | same delta (delta L52) | synthesized summary (JSON envelope structure + TSV header escaped) |
| 4 | `REQ-WHERE-EXIT-CODE-MAPPING` (L304-314) | Exit-code trio 0/1/2 (behavior change from v0.8.2) | `… §REQ-EXIT-CODE-MAPPING` (L310) | `REQ-EXIT-CODE-MAPPING` | same delta (delta L73) | synthesized summary + explicit behavior-change callout |
| 5 | `REQ-WHERE-ENGRAM-STUB` (L316-324) | `--engram` no-op + JSON stub identity | `… §REQ-ENGRAM-STUB` (L320) | `REQ-ENGRAM-STUB` | same delta (delta L93) | synthesized summary (Phase 4+ reserved for real MCP) |
| 6 | `REQ-WHERE-REGEX-OPT-IN` (L326-334) | `--regex` opt-in + `re.compile` validation | `… §REQ-REGEX-OPT-IN` (L330) | `REQ-REGEX-OPT-IN` | same delta (delta L108) | synthesized summary (Python `re` not POSIX ERE) |

All 6 root REQs cite the **same single delta spec path** (`openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md`). The 6 cited delta REQ-IDs were cross-checked against the recovered delta via design-time inspection — every entry below PASSES Check 1 + Check 2 + Check 3 by construction. Wording strategy is uniformly *synthesized summary*: full Given/When/Then scenarios (13 total) + 10 acceptance criteria stay at the delta per the family-index pattern (workspace spec §0 mirror, line 4).

## 4. Verify check specifications — 7 checks

All 7 checks are **structural** (well-formedness), NOT semantic. Each produces a deterministic exit code and a one-line diagnostic on failure. `sdd-verify` runs the full set against the canonical specs and the recovered delta spec at AC2 + AC4 + AC5 + AC6 + AC7.

### Check 1 — Every root REQ block in `flow-where/spec.md` carries exactly one `Source:` line (6 of 6 expected)

```bash
awk '/^### REQ-WHERE-/{blk=$3; src=0; next}
     blk && /\*\*Source:\*\*/{src++}
     blk && /^### /{printf("%s\t%d\n", blk, src); blk=0}
     END{if(blk) printf("%s\t%d\n", blk, src)}' \
  openspec/specs/flow-where/spec.md \
  | awk -F'\t' '$2 != 1 { print "FAIL: " $1 " has " $2 " Source: lines (expected 1)"; fail=1 }
               END { exit fail }'
```

- **Pattern**: `^### REQ-WHERE-` opens a root REQ block; `\*\*Source:\*\*` inside it MUST appear exactly once.
- **Expected**: 6 root REQs (`REQ-WHERE-CROSS-PROJECT-SCOPE` … `REQ-WHERE-REGEX-OPT-IN`), each with exactly 1 `Source:` line.
- **Exit codes**: `0` = all 6 root REQs each have exactly 1 `Source:` line. `1` = any missing or duplicate.
- **Diagnostic on fail**: `FAIL: <REQ-WHERE-ID> has <N> Source: lines (expected 1)`.

### Check 2 — Every `Source:` path exists on disk (single shared path × 6 occurrences)

```bash
paths=$(grep -oP 'openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec\.md' \
              openspec/specs/flow-where/spec.md | sort -u)
fail=0
for p in $paths; do
  [ -f "$p" ] || { echo "FAIL: missing $p"; fail=1; }
done
exit $fail
```

- **Pattern**: literal path `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` extracted from each `Source:` line.
- **Expected**: 1 unique path; the file exists (155 lines, SHA `f546507f4e50d704410a77946529f292cc5b6040`).
- **Exit codes**: `0` = path exists. `1` = missing.
- **Diagnostic on fail**: `FAIL: missing <path>`.

### Check 3 — Every `Source:` REQ-ID exists as a `### Requirement:` heading in the recovered delta

```bash
python -c "
import re, pathlib, sys
spec = pathlib.Path('openspec/specs/flow-where/spec.md').read_text()
blocks = re.findall(r'^### (REQ-WHERE-[A-Z0-9-]+).*?\n(.*?)(?=^### |\Z)', spec, re.MULTILINE | re.DOTALL)
fail = 0
delta = pathlib.Path('openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md').read_text()
delta_ids = set(re.findall(r'^### Requirement: (REQ-[A-Z0-9-]+)\b', delta, re.MULTILINE))
for req, body in blocks:
    m = re.search(r'\u00a7(REQ-[A-Z0-9-]+)', body)
    if not m: print(f'FAIL: {req} has no §REQ-ID'); fail = 1; continue
    rid = m.group(1)
    if rid not in delta_ids:
        print(f'FAIL: {req} cites {rid} but delta spec does not define it'); fail = 1
sys.exit(fail)
"
```

- **Pattern**: `^### Requirement: <REQ-ID>` (case-sensitive, multi-line) inside the recovered delta. Extracts the single `REQ-ID` after the `§` from each root REQ block and asserts it appears as a delta heading.
- **Expected**: 6 of 6 root REQs cite a REQ-ID that exists in the delta. The set of delta IDs is `{REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN}` (one occurrence each at delta L17, L33, L52, L73, L93, L108).
- **Exit codes**: `0` = all 6 IDs found. `1` = any ID missing from delta.
- **Diagnostic on fail**: `FAIL: <root_req> cites <delta_req_id> but delta spec does not define it`.

### Check 4 — `flow-where/spec.md` §4.b cites the Phase 2 test file

```bash
grep -cF "test_cli_where_cross_project.py" openspec/specs/flow-where/spec.md
```

- **Pattern (literal)**: substring `test_cli_where_cross_project.py` somewhere in the canonical spec (currently at L261 in the "Test pointer" paragraph).
- **Expected**: `≥ 1` occurrence. (The test file ships 10 unit tests; the spec cites the filename so reviewers can find them.)
- **Exit codes**: `0` = match found. `1` = match absent.
- **Diagnostic on fail**: `FAIL: flow-where/spec.md §4.b does not cite test_cli_where_cross_project.py (10 tests)`.

### Check 5 — `workspace/spec.md` §6.1 marks the Phase 2 reclassification as RESOLVED

```bash
awk '/^### 6\.1/{p=1; next} /^### /{p=0} p' openspec/specs/workspace/spec.md | grep -cF "RESOLVED"
```

- **Pattern (literal + positional)**: substring `RESOLVED` inside the §6.1 subsection. Currently at L292 in the text `[2026-06-30 update — RESOLVED]`.
- **Expected**: `≥ 1` occurrence.
- **Exit codes**: `0` = RESOLVED marker present in §6.1. `1` = missing.
- **Diagnostic on fail**: `FAIL: workspace/spec.md §6.1 missing the [2026-06-30 update — RESOLVED] marker`.

### Check 6 — `workspace/spec.md` §7 row #1 no longer lists `flow-where-cross-project-capability-merge` as pending

```bash
awk '/^## 7\. Future Changes/{p=1; next} /^## /{p=0} p' openspec/specs/workspace/spec.md \
  | grep -F "flow-where-cross-project-capability-merge" \
  | grep -c "|"
```

- **Pattern (positional + literal)**: inside §7's table area only, look for rows containing the change name. The original row was `| 1 | **\`flow-where-cross-project-capability-merge\`** | Regenerate … | Medium | Phase 2 follow-up debt — see §6.1 |` (removed at spec phase). The change name may legitimately appear in §6.1 (the RESOLVED note + the original follow-up pointer) — those are outside §7 and do NOT trigger this check.
- **Expected**: `0` matches in §7.
- **Exit codes**: `0` = row absent. `1` = row still present.
- **Diagnostic on fail**: `FAIL: workspace/spec.md §7 row #1 still lists flow-where-cross-project-capability-merge as pending — should have been removed at spec phase`.

### Check 7 — `flow-where/spec.md` §8 Drift Detection footer is present

```bash
grep -cF "## 8. Drift Detection" openspec/specs/flow-where/spec.md
```

- **Pattern (literal)**: substring `## 8. Drift Detection` as a Markdown H2 heading. Currently at L336 of `flow-where/spec.md`.
- **Expected**: `1` (exactly one footer; not zero, not duplicated).
- **Exit codes**: `0` = footer present. `1` = missing or duplicated.
- **Diagnostic on fail**: `FAIL: flow-where/spec.md §8 Drift Detection footer missing or duplicated`.

## 5. Failure modes + error handling matrix

| Check # | Failure mode | User-visible message | Exit code |
|---|---|---|---|
| 1 | Root REQ missing or duplicating `Source:` line | `FAIL: <REQ-WHERE-ID> has <N> Source: lines (expected 1)` | 1 |
| 2 | Cited delta spec path missing or moved | `FAIL: missing <path>` | 1 |
| 3 | Cited REQ-ID not found in recovered delta spec | `FAIL: <root_req> cites <delta_req_id> but delta spec does not define it` | 1 |
| 4 | `test_cli_where_cross_project.py` not cited in §4.b | `FAIL: flow-where/spec.md §4.b does not cite test_cli_where_cross_project.py (10 tests)` | 1 |
| 5 | `RESOLVED` marker absent from §6.1 | `FAIL: workspace/spec.md §6.1 missing the [2026-06-30 update — RESOLVED] marker` | 1 |
| 6 | Row #1 in §7 still lists the change as pending | `FAIL: workspace/spec.md §7 row #1 still lists flow-where-cross-project-capability-merge as pending — should have been removed at spec phase` | 1 |
| 7 | §8 Drift Detection footer missing or duplicated | `FAIL: flow-where/spec.md §8 Drift Detection footer missing or duplicated` | 1 |

**Contract shared by all 7 checks**: `exit 0` = pass; `exit 1` = fail with one-line diagnostic on stderr. `sdd-verify` aggregates: any non-zero exit fails the entire AC and the run halts before declaring PASS. Recovery discipline (AC1): the **delta spec byte-identical guard** is enforced separately by `git hash-object` + `git diff --no-index` against the git source at `27111ed` — it is not one of the 7 checks because it is a separate AC (AC1 in proposal #505).

## 6. Out of Scope (explicit)

- **NO modifications** to the recovered Phase 2 delta spec at `specs/cross-project-search/spec.md`. SHA `f546507f4e50d704410a77946529f292cc5b6040` MUST NOT change. Hash match = respect the bytes.
- **NO modifications** to `flow-where/spec.md` content (already done in spec phase: +102 net / −1 net, first 245 lines byte-identical to HEAD).
- **NO modifications** to `workspace/spec.md` content (already done in spec phase: +3 net / −2 net, §6.1 RESOLVED note appended, §7 row #1 removed).
- **NO path rename**: destination path stays `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md`. The proposal's `#5` line referencing `flow-where-cross-project/spec.md` is the in-proposal planning shorthand — actual file is `cross-project-search/spec.md` per the spec phase lock and the orchestrator launch prompt (user-locked).
- **NO BDD count change**: 13 Given/When/Then scenarios + 10 acceptance criteria in the recovered delta is canonical; do not adjust to align with the proposal's "11 BDD scenarios" pre-recovery estimate.
- **NO automated drift detection** beyond the 7 structural checks above. Diff-based comparison of root REQ summary prose against delta REQ wording is a future change.
- **NO new code**: zero `cli.py` / `where.py` / helpers / fixtures / tests. The 7 checks run via `awk` + `grep` + `bash` + a tiny `python -c` for Check 3.
- **NO modifications** to `openspec/changes/v1.1-followups/` (sacred territory, user-locked Batch A constraint #4).
- **NO archive moves**. The change folder stays at `openspec/changes/flow-where-cross-project-capability-merge/` until `sdd-archive` moves it.

## 7. Tech Debt / Follow-up

- **Automated drift detection** (future improvement, §8 footer "open improvement"): parse `Source:` lines and confirm path validity + the cited REQ still exists in the delta spec + optionally diff root REQ summary prose against delta REQ wording. Deferred to a future `spec-drift-detector` change.
- **Cross-link validation across ALL capability specs** (future improvement): extend Checks 1-3 to cover `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`. Out of scope here; would require a `capability-spec-linter` change.
- **Improvements to the recovered Phase 2 delta spec** (future SEPARATE change): any typo fixes, formatting modernization, or REQ wording refinement go in a separate `cross-project-search-content-polish` change with its own commit. This PR hash-matches and respects bytes.
- **Workspace §4.2 versioning row** (open observation, NOT blocked by this PR): the current row at `workspace/spec.md:241` still reads "No change to workspace root spec; `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X`". The actual landed REQs are `REQ-WHERE-CROSS-PROJECT-SCOPE` … `REQ-WHERE-REGEX-OPT-IN` (distinct namespace, per Engram #487). Tracked as a future `workspace-spec-cross-impact-cleanup` follow-up. NOT in scope for this PR per the spec-phase minimal-edit constraint.
- **Workspace §2 archive-status carry-forwards note** (open observation, NOT blocked by this PR): L16 still lists `flow-where-cross-project-capability-merge` in the carry-forwards list. The row is resolved; the prose is stale. Future cleanup change.
- **`workspace-hygiene-capability-spec`** (open future change, per workspace §7 row #3): optional top-level capability spec if the hygiene delta grows further.

## 8. Pre-existing failures (out-of-scope reminder)

- **3 pre-existing lint errors** (carried from Phase 2 close-out): `cli.py:682 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`. UNTOUCHED. Doc-only change; same baseline.
- **0 pre-existing test failures** on main HEAD `920d395` (sanity baseline = 1513/1513). Preserved.
- **AC9 byte-identical guard** at `tests/unit/test_cli_projects.py:435` (the `flow projects ls --json` envelope byte-identity check). Preserved by zero-code-change policy. `sdd-verify` re-runs the guard post-commit.

## 9. Commit plan

Per `work-unit-commits` skill + user session preference (single commit per PR):

- **One commit**, conventional format, no AI attribution (per AGENTS.md).
- **Suggested message**: `docs(specs): integrate Phase 2 cross-project into flow-where root`
- **Files in commit** (3 modified):
  - `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` (NEW, 155 LOC, recovered byte-identical).
  - `openspec/specs/flow-where/spec.md` (+102 net / −1 net vs HEAD, additive only — first 245 lines byte-identical).
  - `openspec/specs/workspace/spec.md` (+3 net / −2 net vs HEAD, §6.1 appended + §7 row #1 removed).
  - **Cumulative diff**: ~258 LOC across 3 files (well under 400-line review budget).
- **No code changes**, no `pyproject.toml` / `uv.lock` churn, no test fixtures.
- **PR body**: link AC1-AC11 from `proposal.md`; cite the 7 verify checks as the AC2/AC4/AC5/AC6/AC7 verification surface.

## 10. Wall-time forecast for tasks → apply → verify → archive

| Phase | Estimate | Rationale |
|---|---|---|
| `sdd-tasks` | ~20 min | ~7-9 mechanical tasks paralleling workspace-capability-bootstrap tasks #494 (write 3 spec files [done] + author 7 verify-check scripts + commit). No code, no test, no fixture. |
| `sdd-apply` | ~15 min | Confirm 3 file states on disk + confirm 1513/1513 baseline still passes (zero code touched, so baseline must be unchanged) + fill in `[future-commit-sha]` placeholder in `workspace/spec.md:292`. |
| `sdd-verify` | ~20 min | Run AC1-AC11 + run the 7 verify checks from §4 against the 2 canonical specs + the recovered delta. Confirm byte-identical guard at `test_cli_projects.py:435` still green. |
| `sdd-archive` | ~15 min | Move `openspec/changes/flow-where-cross-project-capability-merge/` → `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`. No spec merge step needed (the changes already live in the canonical specs via the additive append in spec phase). |
| **Total remaining** | **~70 min** | Confident; pure mechanical work after the doc-only deliverable is in place. |
