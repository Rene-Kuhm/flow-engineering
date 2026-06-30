# Design: workspace-capability-bootstrap

## Header

- **Change**: `workspace-capability-bootstrap`
- **Phase**: design (4 of 8 — sdd-design)
- **Project**: flow-engineering v1.2.0, main HEAD `d077d75`
- **Strict TDD**: **OFF** (doc-only change — no code, no tests)
- **Artifact store**: openspec (filesystem) + hybrid Engram mirror
- **Design philosophy**: *"verifiable and maintainable, not feature architecture"*. The deliverable from `sdd-spec` is already locked. This design does not re-shape it — it specifies the **verification surface** that proves the spec stays well-formed over time.
- **Inputs** (authoritative, read in full):
  - Canonical root spec: `openspec/specs/workspace/spec.md` (314 lines, under 400-line budget by 21%)
  - Change-artifact spec: `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` (129 lines, ceremony)
  - Engram `#490` (spec phase report, 7 REQ inventory)
  - Engram `#488` (proposal, Approach B locked)
  - Engram `#486` (explore, Phase 2 reclassification)
  - Gold-standard reference: `openspec/specs/flow-where/spec.md` (245 LOC, family-index template)
- **Output**: this file (`openspec/changes/workspace-capability-bootstrap/design.md`) + Engram mirror at topic_key `sdd/workspace-capability-bootstrap/design`.
- **Out-of-scope guardrails** (user-locked, 14 constraints, all in force): NO modifications to the canonical spec; NO modifications to any archived delta spec; NO new code; NO new helpers; NO `openspec/changes/v1.1-followups/` touch; NO `openspec/specs/workspace-hygiene/spec.md` creation; NO cross-capability BDD scenarios.

---

## 1. Architecture overview (minimal)

The "architecture" of this doc-only change is its **information architecture + validation surface**, not its runtime behavior. The canonical spec at `openspec/specs/workspace/spec.md` is a **family index** that anchors 7 root-level REQs (`REQ-WORKSPACE-*`) to 18+ delta REQs across 3 archived/live delta specs (Phase 1, 3, 4). Phase 5 is an intentional placeholder (no current delta source). The validation surface is the set of structural checks that prove each `Source:` line points to a real file containing the cited `REQ-ID`, plus the four structural-presence checks (Cross-Impact, Future Changes, Drift Detection, Family-index callout). This design specifies those 7 checks as concrete, runnable validation primitives — exactly what `sdd-verify` consumes at AC2 + AC11.

```
  spec.md (canonical, 314 LOC)
        │
        ├── 7 root REQs ───── Source: lines ─────► 3 delta spec files
        │                                              (Phase 1, 3, 4)
        │                                              + 1 placeholder
        │
        ├── 4 structural sections ── Cross-Impact, Future Changes,
        │                            Drift Detection, Family-index callout
        │
        └── 7 verify checks (this design) ── sdd-verify consumes at AC2/AC11
                  │
                  ├── 3 schema-shape checks (Source: presence + path + REQ-ID)
                  └── 4 structural-presence checks (Cross-Impact / Future / Drift / Family)
```

The "data flow" is *reading→grep→assert*: each check reads the canonical spec, applies a structural rule, and exits 0 (pass) or 1 (fail) with a one-line user-visible diagnostic.

---

## 2. Anchor strategy — the `Source:` line

### 2.1 Definition

A `Source:` line is a single Markdown line inside a root-level REQ block (`### REQ-WORKSPACE-*`) that **points the reader and the verifier** to the canonical delta spec + delta REQ where the full Given/When/Then wording lives.

### 2.2 Formal grammar

```text
Source-line ::= "**Source:**" WHITESPACE "`" PATH "`" WHITESPACE "§" REQ-ID-LIST
                 ("|" "`" PATH "`" WHITESPACE "§" REQ-ID-LIST)*

PATH        ::= RELATIVE-PATH-WITH-FORWARD-SLASHES        # e.g.
                 openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md
              | (empty when §7 placeholder — see REQ-WORKSPACE-DASHBOARD-PLACEHOLDER)

REQ-ID-LIST ::= REQ-ID (","? WHITESPACE? " + " REQ-ID)*
REQ-ID      ::= "REQ-" ALPHANUMERIC-DASH-UNDERSCORE-CHUNK    # e.g.
                 REQ-HYGIENE-POLLUTION-PROTOCOL,
                 REQ-`--json`-FLAG (literal backticks allowed),
                 REQ-V1.0.5
```

- **Anchor char**: `§` (one character, ASCII, no ambiguity with `&` / `#` / `:` / `->`).
- **Quote char**: backticks wrap the path (standard Markdown).
- **Separator**: ` + ` (space-plus-space) joins multiple delta REQ-IDs inside one `Source:` line — used when one root REQ synthesizes multiple delta REQs (e.g. `REQ-WORKSPACE-PROJECT-IDENTITY` cites 5).
- **Empty path**: only allowed for the Phase 5 placeholder root REQ. The grammar is relaxed to a sentinel `*Forward-looking (no delta spec yet — see §7 Future Changes for the `workspace-dashboard` follow-up).*` form so the verification surface treats the placeholder case as **expected** rather than **failing**.

### 2.3 Location rule

`Source:` lines MUST appear **inside each root-level REQ block** (`### REQ-WORKSPACE-*`), **after** the body prose and **before** the `Out of scope:` line. This is the canonical spot in all 7 root REQs at lines 96, 114, 124, 134, 144, 164, 174 of the canonical spec.

### 2.4 Path prefix rule

Every non-placeholder `PATH` MUST:

1. Start with `openspec/changes/` (relative to repo root).
2. Resolve to a file that exists on disk (Check 2 enforces this).
3. For a root REQ that synthesizes multiple delta REQs spanning multiple changes, **list each on its own backtick-path** separated by ` + ` (see REQ-WORKSPACE-STATUS-DISCOVERY as the precedent at line 114 — though in practice all 8 cited delta REQs come from a single path, so this rule collapses to a single-path form for that REQ).

### 2.5 What is NOT in scope for the anchor strategy

- REQ-ID uniqueness across files. The delta IDs share namespaces per-delta (`REQ-` + `-`-separated tokens), so cross-file collisions are not a concern in this change.
- Authoring tooling for `Source:` lines. Manual authoring is fine — drift detection runs in `sdd-verify`, not in the editor.
- Renaming existing delta REQ-IDs to a new namespace. Future change if desired; out of scope.

---

## 3. Cross-reference inventory

All 7 root-level REQs at `openspec/specs/workspace/spec.md` lines 92-176, with their verbatim `Source:` line, delta spec path, delta REQ ID(s), and a one-line summary. All `Source:` paths and delta REQ IDs were cross-checked against the cited delta spec files via `grep -P "^### Requirement: <REQ-ID>"` at design time — **every entry below PASSED the existence check**.

| # | Root REQ ID (line) | One-line title | `Source:` line (verbatim) | Delta spec path (exists?) | Delta REQ IDs cited | Wording strategy |
|---|---|---|---|---|---|---|
| 1 | `REQ-WORKSPACE-PROJECT-IDENTITY` (L92-98) | 11-field project identity + v1 JSON envelope | `**Source:** \`openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md\` §REQ-`--json`-FLAG + REQ-FIELD-EXTENSION + REQ-HAS-ENGRAM-STUB + REQ-SCHEMA-VERSIONING + REQ-DETERMINISTIC-ORDER.` (L96) | `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` ✅ exists | 5 IDs: `REQ-`--json`-FLAG`, `REQ-FIELD-EXTENSION`, `REQ-HAS-ENGRAM-STUB`, `REQ-SCHEMA-VERSIONING`, `REQ-DETERMINISTIC-ORDER` (all 5 found at L28, L51, L90, L107, L122) | synthesized summary + full Given/When/Then at source |
| 2 | `REQ-WORKSPACE-STATUS-DISCOVERY` (L102-116) | 5 needs-attention rules R1-R5 + JSON envelope | `**Source:** \`openspec/changes/flow-workspace-status/specs/workspace-status/spec.md\` §REQ-R1-DIRTY-COMMITTED + REQ-R2-NO-GIT + REQ-R3-NO-TESTS + REQ-R4-NO-OPENSPEC-SDD-STACK + REQ-R5-NO-GRAPHIFY-INFORMATIONAL + REQ-WS-JSON-ENVELOPE + REQ-WS-TEXT-DEFAULT + REQ-WS-EMPTY-ROOT.` (L114) | `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` ✅ exists | 8 IDs (all 8 found at L17, L27, L37, L47, L51, L62, L76, L88) | synthesized summary (rules R1-R5 listed in body prose) |
| 3 | `REQ-WORKSPACE-MUTATION-SAFETY` (L120-126) | pollution-protocol triple + backup gate | `**Source:** \`openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md\` §REQ-HYGIENE-POLLUTION-PROTOCOL + REQ-HYGIENE-BACKUP-LAYOUT + REQ-HYGIENE-BACKUP-GATE-NONEMPTY.` (L124) | archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md ✅ exists | 3 IDs (all 3 found at L114, L102, L146) | synthesized summary; pollution-protocol triple spelled out in body |
| 4 | `REQ-WORKSPACE-DRY-RUN-DEFAULT` (L130-136) | dry-run default + `--yes` gating | `**Source:** \`openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md\` §REQ-HYGIENE-DRY-RUN-DEFAULT.` (L134) | same as #3 ✅ | 1 ID (found at L126) | synthesized summary |
| 5 | `REQ-WORKSPACE-R1-DEFERRED` (L140-146) | R1 dirty-git OUT OF SCOPE meta-REQ | `**Source:** \`openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md\` §REQ-HYGIENE-R1-EXPLICITLY-OUT.` (L144) | same as #3 ✅ | 1 ID (found at L174) | exact quote of canonical phrase: *"R1 dirty-git is OUT OF SCOPE for Phase 4 MVP"* |
| 6 | `REQ-WORKSPACE-REGISTRY-V1` (L150-166) | registry at `~/.flow-engineering/registry.json` v1 | `**Source:** \`openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md\` §REQ-HYGIENE-REGISTRY-V1.` (L164) | same as #3 ✅ | 1 ID (found at L80) | synthesized summary + JSON schema block |
| 7 | `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` (L170-176) | Phase 5 forward-looking stub | `**Source:** Forward-looking (no delta spec yet — see §7 Future Changes for the \`workspace-dashboard\` follow-up).` (L174) | **none** (placeholder — by design) | none (placeholder) | full text deferred to Phase 5 delta spec; §7 Future Changes lists the follow-up |

**Wording strategy classification**:

- *Synthesized summary* (5 of 7 root REQs): root REQ prose restates the delta REQ contract in 1-3 sentences; full Given/When/Then scenarios + acceptance criteria stay in the delta spec. This is the "family index" pattern from `flow-where/spec.md` (L21-37).
- *Exact-quote with provenance* (1 of 7): `REQ-WORKSPACE-R1-DEFERRED` quotes the canonical Phase 4 phrase verbatim (`"R1 dirty-git is OUT OF SCOPE for Phase 4 MVP"`) so any future writer who needs to restate it inherits the same wording.
- *Placeholder* (1 of 7): `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` has no current delta — explicitly nil. The verification surface treats this as an *expected absence* (see Check 1, *Excepted IDs* clause).

---

## 4. Verify check specifications — 7 checks

All 7 checks are structural. They do NOT validate semantic correctness; they validate well-formedness. Each check produces a deterministic exit code and a single-line diagnostic on failure. `sdd-verify` runs the full set against the canonical spec and against the 3 cited delta spec files at AC2 + AC11.

### Check 1 — Every root REQ has exactly one `Source:` line (covers all 7 REQs)

```bash
awk '/^### REQ-WORKSPACE-/ { in_block=1; req=$3; src_count=0; next }
     in_block && /\*\*Source:\*\*/ { src_count++ }
     in_block && /^### / { printf("%s\t%d\n", req, src_count); in_block=0 }
     END { if (in_block) printf("%s\t%d\n", req, src_count) }' \
  openspec/specs/workspace/spec.md \
  | awk -F'\t' '$2 != 1 { print "FAIL: " $1 " has " $2 " Source: lines"; fail=1 } END { exit fail }'
```

- **Pattern (regex)**: `^### REQ-WORKSPACE-` opens a root REQ block; `\*\*Source:\*\*` inside it MUST appear exactly once.
- **Expected**: 7 root REQs, each with exactly one `Source:` line. The placeholder (REQ 7) carries a `Source:` line whose value is `Forward-looking (no delta spec yet — …)` — counted as 1, NOT 0.
- **Exit codes**: `0` = all 7 root REQs each have exactly one `Source:` line. `1` = any root REQ is missing or duplicating a `Source:` line.
- **Diagnostic on fail**: `FAIL: REQ-WORKSPACE-<ID> has <N> Source: lines (expected 1)`.

### Check 2 — Every `Source:` path exists on disk (covers 6 of 7 REQs; REQ 7 is placeholder)

```bash
grep -oP 'openspec/changes/[^\s`]+\.md' openspec/specs/workspace/spec.md \
  | sort -u \
  | while read -r path; do
      [ -f "$path" ] || { echo "FAIL: missing $path"; exit 1; }
    done
```

- **Pattern (regex)**: `openspec/changes/[\w/.-]+\.md` extracted from each `Source:` line that contains a backtick-wrapped path.
- **Expected**: 3 unique paths (one per Phase) — `workspace-intelligence/.../projects-ls-extension/spec.md`, `flow-workspace-status/.../workspace-status/spec.md`, `archive/2026-06-30-workspace-hygiene/.../workspace-hygiene/spec.md`.
- **Exit codes**: `0` = all cited paths exist. `1` = any path missing or moved.
- **Diagnostic on fail**: `FAIL: missing <path>`.
- **Excepted**: REQ-WORKSPACE-DASHBOARD-PLACEHOLDER has no path — its `Source:` line uses the forward-looking form, which the regex above does not match (no `openspec/changes/` prefix in its body). No false positive.

### Check 3 — Every `Source:` REQ-ID exists in the cited delta spec (covers 18 delta REQ-IDs across 6 root REQs)

```bash
python -c "
import re, pathlib, sys
spec = pathlib.Path('openspec/specs/workspace/spec.md').read_text()
blocks = re.findall(r'^### (REQ-WORKSPACE-[A-Z0-9-]+).*?\n(.*?)(?=^### |\Z)',
                    spec, re.MULTILINE | re.DOTALL)
fail = 0
for req, body in blocks:
    if 'forward-looking' in body.lower(): continue  # placeholder exempt
    src = re.search(r'\`([^\`]+)\`\s+§([^\n]+)', body)
    if not src: continue
    path, ids = src.group(1), re.findall(r'REQ-[\`\w-]+', src.group(2))
    src_text = pathlib.Path(path).read_text()
    for rid in ids:
        if not re.search(rf'^### Requirement: {re.escape(rid)}\b', src_text, re.MULTILINE):
            print(f'FAIL: {req} cites {rid} but {path} does not define it'); fail = 1
sys.exit(fail)
"
```

- **Pattern (regex)**: `^### Requirement: <REQ-ID>` (case-sensitive, multi-line). The cited `REQ-ID` must appear as a heading under a `### Requirement:` block in the cited file.
- **Expected**: 18 distinct delta REQ-IDs across 6 of 7 root REQs (5 + 8 + 3 + 1 + 1 + 1 = 19 actually — see count table below). REQ-WORKSPACE-DASHBOARD-PLACEHOLDER carries zero IDs and is exempt by the placeholder clause.
- **Exit codes**: `0` = every cited REQ-ID exists in its cited file. `1` = any cited REQ-ID missing.
- **Diagnostic on fail**: `FAIL: <root_req> cites <delta_req_id> but <path> does not define it`.

**Cited-REQ count by root REQ** (matches §3 inventory):

| Root REQ | Delta REQ-ID count |
|---|---|
| REQ-WORKSPACE-PROJECT-IDENTITY | 5 |
| REQ-WORKSPACE-STATUS-DISCOVERY | 8 |
| REQ-WORKSPACE-MUTATION-SAFETY | 3 |
| REQ-WORKSPACE-DRY-RUN-DEFAULT | 1 |
| REQ-WORKSPACE-R1-DEFERRED | 1 |
| REQ-WORKSPACE-REGISTRY-V1 | 1 |
| REQ-WORKSPACE-DASHBOARD-PLACEHOLDER | 0 (placeholder) |
| **Total** | **19** |

### Check 4 — Cross-Impact section explicitly mentions `flow-where-cross-project-capability-merge`

```bash
grep -F "flow-where-cross-project-capability-merge" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `flow-where-cross-project-capability-merge` somewhere in the file (currently at L290 and L296 per §6.1 + §7).
- **Exit codes**: `0` = mention present. `1` = mention missing.
- **Diagnostic on fail**: `FAIL: §6 Cross-Impact must mention the flow-where-cross-project-capability-merge follow-up`.
- **Rationale**: AC6 + AC7 require Cross-Impact to document the Phase 2 reclassification and the named follow-up. A future maintainer editing this spec must not silently drop the future-change pointer.

### Check 5 — Future Changes section explicitly mentions Phase 5 dashboard placeholder

```bash
grep -F "workspace-dashboard" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `workspace-dashboard` somewhere in the file (currently at L80, L172, L174, L215, L297).
- **Exit codes**: `0` = mention present. `1` = mention missing.
- **Diagnostic on fail**: `FAIL: §7 Future Changes must list workspace-dashboard`.

### Check 6 — Drift Detection footer present

```bash
grep -F "Drift Detection" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `Drift Detection` somewhere in the file (currently at L304 as the §8 H2 heading).
- **Exit codes**: `0` = footer present. `1` = missing.
- **Diagnostic on fail**: `FAIL: §8 Drift Detection footer missing`.

### Check 7 — "Family index" callout in the first 10 lines of the file

```bash
head -n 10 openspec/specs/workspace/spec.md | grep -F "Family index" >/dev/null
```

- **Pattern (literal + positional)**: substring `Family index` in lines 1-10 (currently at L4 inside the > blockquote).
- **Exit codes**: `0` = callout present in first 10 lines. `1` = missing or moved.
- **Diagnostic on fail**: `FAIL: 'Family index, not canonical source' callout must appear in the first 10 lines`.
- **Rationale**: AC3 + AC4 require the prominent callout at the top. This check enforces the position rule — drift here would mean the callout was pushed down by other content, hiding the family's navigation contract.

---

## 5. Failure modes + error handling matrix

| Check # | Failure mode | User-visible message | Exit code |
|---|---|---|---|
| 1 | Root REQ missing or duplicating `Source:` | `FAIL: REQ-WORKSPACE-<ID> has <N> Source: lines (expected 1)` | 1 |
| 2 | Cited delta spec path missing or moved | `FAIL: missing <path>` | 1 |
| 3 | Cited REQ-ID does not exist in cited delta spec | `FAIL: <root_req> cites <delta_req_id> but <path> does not define it` | 1 |
| 4 | Cross-Impact does not name the Phase 2 merge follow-up | `FAIL: §6 Cross-Impact must mention the flow-where-cross-project-capability-merge follow-up` | 1 |
| 5 | Future Changes does not list the Phase 5 placeholder | `FAIL: §7 Future Changes must list workspace-dashboard` | 1 |
| 6 | Drift Detection footer missing | `FAIL: §8 Drift Detection footer missing` | 1 |
| 7 | Family-index callout not in first 10 lines | `FAIL: 'Family index, not canonical source' callout must appear in the first 10 lines` | 1 |

**All 7 checks use the same contract**: `exit 0` = pass (or expected absence for placeholder clauses in Check 1/2/3); `exit 1` = fail with one-line diagnostic on stderr. `sdd-verify` aggregates: any non-zero exit fails the entire AC and the run halts before declaring PASS.

---

## 6. Out of Scope (explicit)

- **NO modifications** to `openspec/specs/workspace/spec.md` content (314 lines as-written is final; locked at spec phase).
- **NO modifications** to any of the 4 prior archived specs (`workspace-intelligence/projects-ls-extension`, `flow-where-cross-project/status.md`, `flow-workspace-status/workspace-status`, `archive/2026-06-30-workspace-hygiene/workspace-hygiene`).
- **NO automated drift detection** beyond the 7 structural checks above. Diff-based comparison of root REQ summaries vs delta REQ wording is a future enhancement.
- **NO modifications** to `openspec/changes/v1.1-followups/` (sacred territory, user-locked constraint #3).
- **NO new code**: no helper modules, no new test files beyond the verify scripts themselves. The 7 checks above run via `bash` + `awk` + `grep` + a tiny `python -c` for Check 3.
- **NO cross-capability BDD scenarios**: root spec is a family index, not a behavioral spec. Phase 4's 16 BDD scenarios + Phase 3's 7 scenarios remain canonical and untouched.
- **NO creation** of `openspec/specs/workspace-hygiene/spec.md` (separate future change, user-locked constraint #4).
- **NO modifications** to `openspec/specs/flow-where/spec.md`. Phase 2 reclassification is documented only; the merge into `flow-where/spec.md` is a follow-up change.

---

## 7. Tech Debt / Follow-up

- **Automated drift detection** (future improvement): diff root REQ summary prose against delta REQ wording; surface notable drift as a CI failure. Deferred until a CI hook for OpenSpec specs exists (per canonical spec §8 *Open improvement*).
- **Cross-link validation across ALL capability specs** (future improvement): extend Checks 2/3 to cover `flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`. Out of scope for this change; would require a separate `capability-spec-linter` change.
- **Future change `flow-where-cross-project-capability-merge`** (Engram #456 + canonical §7 row #1): regenerate Phase 2 delta spec from Engram #456, then merge the 6 REQs into `openspec/specs/flow-where/spec.md` as `REQ-V1.0.5..V1.0.X`. Medium priority.
- **Future change `workspace-hygiene-capability-spec`** (canonical §7 row #3): optional top-level capability spec for the write-side if the delta grows further. Low priority.
- **Future change `workspace-dashboard` (Phase 5)** (canonical §7 row #2): TUI or web visualization. Low priority; requires CLI solidification first.
- **Backup retention policy** (`backup-retention-policy` follow-up, canonical §7 row #4): INDEFINITE retention in Phase 4 MVP is a known operator concern. Low priority, not blocking.

---

## 8. Pre-existing failures (out-of-scope reminder)

- **3 pre-existing lint errors** (carried from Phase 4 close-out; remain OOS): `cli.py:682 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`.
- **0 pre-existing test failures** on main HEAD `d077d75` (sanity baseline = 1513/1513).
- **AC9 byte-identical guard** at `tests/unit/test_cli_projects.py:435` preserved by zero-code-change policy. `sdd-verify` re-runs the guard post-commit to confirm.

---

## 9. Commit plan

Per `work-unit-commits` skill + user session preference ("single commit per PR"):

- **One commit**, conventional format, no AI attribution (per AGENTS.md).
- **Commit message**: `chore(specs): bootstrap workspace root capability spec`
- **Files in commit**: just the 2 spec files — `openspec/specs/workspace/spec.md` (NEW, canonical) + `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` (NEW, ceremony artifact). No code changes; no pyproject/lockfile churn.
- **PR body**: link AC1-AC11 from `proposal.md`; cite the 7 verify checks as the AC2/AC11 verification surface.

---

## 10. Wall-time forecast for tasks → apply → verify → archive

| Phase | Estimate | Rationale |
|---|---|---|
| `sdd-tasks` | ~10 min | One task family: write the 2 spec files (already done at spec phase) + author the 7 verify-check one-liners + commit. No code, no test, no fixture. |
| `sdd-apply` | ~10 min | Confirm files exist on disk + confirm 1513/1513 baseline still passes (zero code touched, so baseline must be unchanged). |
| `sdd-verify` | ~15 min | Run AC1-AC11 + run the 7 verify checks from §4 against the canonical spec (Checks 1, 4-7) and the 3 cited delta specs (Checks 2, 3). Confirm byte-identical guard still green. |
| `sdd-archive` | ~15 min | Move `openspec/changes/workspace-capability-bootstrap/` → `openspec/changes/archive/2026-06-30-workspace-capability-bootstrap/`. The canonical spec is the source-of-truth — no merge step needed (deltas would normally be merged INTO it, but this change IS the canonical spec; nothing to merge from a delta spec into it because the canonical spec was authored directly). |
| **Total remaining** | **~50 min** | Confident; this is the simplest change in the SDD cycle since `flow-where-mvp` (#13, v0.8.2). |
