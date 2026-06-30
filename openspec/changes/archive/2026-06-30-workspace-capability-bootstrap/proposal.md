# Proposal: `workspace-capability-bootstrap`

> **Change**: `workspace-capability-bootstrap`
> **Phase**: propose (2/7 of SDD cycle)
> **Author**: sdd-propose sub-agent
> **Date**: 2026-06-30
> **Project**: flow-engineering (v1.2.0, main HEAD `d077d75`)
> **Artifact store**: `openspec` (write `openspec/changes/workspace-capability-bootstrap/proposal.md` + Engram mirror)
> **Strict TDD**: OFF (doc change only)
> **Status**: LOCKED — ready for spec phase

---

## 1. Header

| Field | Value |
|-------|-------|
| Change | `workspace-capability-bootstrap` |
| Purpose | Create the orphan root capability spec at `openspec/specs/workspace/spec.md` |
| Builds on | explore #486 (Approach B Comprehensive, Phase 2 reclassification, 7 root REQs) |
| Single deliverable | `openspec/specs/workspace/spec.md` (~250–350 LOC markdown) |
| Strict TDD | OFF — doc/spec change, no tests required |
| Forecast | Single PR, 1 commit, ~250–350 LOC, under 400-line budget |
| Engram mirror | topic_key `sdd/workspace-capability-bootstrap/proposal`; type `architecture`; `capture_prompt: false` |

---

## 2. Approach B Locked

**Approach B (Comprehensive)** is locked as the sole approach.

| Dimension | Value |
|-----------|-------|
| Content shape | Name + boundary + capability list + cross-refs + 7 root-level REQs + Drift Detection footer + Future Changes section |
| Modeled on | `openspec/specs/flow-where/spec.md` (245 LOC gold standard) |
| LOC estimate | ~250–350 markdown lines |
| Review budget (400 lines) | ✅ Under by 15–35% |
| Chained PRs | None — single PR |
| `size:exception` | Not needed |

**What Approach B delivers**: A family-index root spec that anchors 3 confirmed sub-capabilities + 1 Phase 5 placeholder. 7 synthesized root-level REQs (each citing its delta source via `Source:` line). ASCII dependency graph. Phase 2 reclassification documented in Cross-Impact. Future Changes section naming the `flow-where-cross-project-capability-merge` follow-up.

**What it does NOT do**: Duplicate delta REQ text (drift prevention). Enumerate all 25 delta REQs (catalog would be 800–1200 LOC, 2–3× over budget).

---

## 3. Capability Family Locked

**Confirmed workspace capability family — 3 sub-capabilities + 1 placeholder:**

| Phase | Sub-capability | CLI surface | Role |
|-------|---------------|-------------|------|
| 1 | `projects-ls-extension` | `flow projects ls [--json]` | Read discovery — project metadata enumeration |
| 3 | `workspace-status` | `flow workspace status [--json]` | Read aggregation — needs-attention synthesis |
| 4 | `workspace-hygiene` | `flow workspace {fix,archive,archived,restore}` | Write/mutation — registry-mediated project lifecycle |
| 5 (future) | `workspace-dashboard` | `flow workspace tui` / web | Visualization — **placeholder stub only** |

**Capability boundary (user-locked):**

- **workspace** = inventory/status/hygiene of projects (CRUD on project identity and state).
- **where** = search/retrieval of content within projects.
- These are intentionally separate domains. Do not mix them.

**Phase 2 is NOT in this family** (see §4).

---

## 4. Phase 2 Reclassification (USER-LOCKED)

### 4.1 Statement

Phase 2 (`flow-where-cross-project`) **belongs to `flow-where` capability, NOT `workspace`**.

User rationale (verbatim): *"no mezclar 'inventario/estado/higiene del workspace' con 'búsqueda/retrieval de contenido'"*.

### 4.2 Evidence (from Engram #456 + proposal #455)

| Evidence | Source |
|----------|--------|
| Phase 2 proposal #455 states "ADDITIVE to where_cmd — do NOT replace existing where.py module API" | Engram #456 / proposal #455 |
| Phase 2 reuses `_run_search` from `where.py` (read-only on existing `flow-where` module) | `openspec/changes/flow-where-cross-project/status.md:25` |
| Phase 2's 6 search directories (`src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/`) are **code content** targets, not project-metadata targets | `status.md:20` |
| The semantic test: Phase 2's REQs would make sense if `workspace` capability never existed — "find code across projects" is a `flow-where` concern | Engram #486 §4.2 |

### 4.3 Phase 2 delta spec is MISSING locally

The delta spec for Phase 2 is **not present** at `openspec/changes/flow-where-cross-project/specs/`. Only `status.md` survives locally. Full Phase 2 REQ content is preserved in **Engram #456** (6 REQs: REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN).

### 4.4 Action in this PR

- Phase 2 is **documented as a follow-up cross-capability change** in this PR's root spec (Cross-Impact + Future Changes sections).
- **No files are moved** in this PR.
- **No modifications** to any archived Phase 2 artifacts.

### 4.5 Follow-up change (separate, out-of-scope for this PR)

| Field | Value |
|-------|-------|
| Follow-up name | `flow-where-cross-project-capability-merge` |
| Scope | Regenerate Phase 2 delta spec from Engram #456 + merge into `openspec/specs/flow-where/spec.md` as REQ-V1.0.5..V1.0.X + commit |
| Trigger | Future change; NOT this PR |

---

## 5. Seven Root-Level REQs

Each synthesized root REQ has:
- **ID**: `REQ-WORKSPACE-XXX-NAME` (kebab-case)
- **Source**: path + delta REQ ID (for drift detection)
- **Wording**: 1-2 sentence summary at root level (NOT a copy of delta wording)
- **Out of scope**: what stays at delta level

---

### REQ-WORKSPACE-PROJECT-IDENTITY

**Source**: `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` → REQ-FIELD-EXTENSION (Table §2, rows 1–11) + REQ-SCHEMA-VERSIONING + REQ-DETERMINISTIC-ORDER

**Wording**: A project is identified by 11 static metadata fields (`name`, `path`, `has_git`, `branch`, `dirty`, `remote`, `stack`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram`). The v1 JSON envelope uses `version: "1"` as its first key. The `projects` array is sorted alphabetically by `name`. `null` represents missing data.

**Out of scope**: The specific git-detection subprocess mechanics; the stack-detection heuristics; Phase 2 stub (`has_engram` stays `false` in MVP).

---

### REQ-WORKSPACE-STATUS-DISCOVERY

**Source**: `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` → REQ-R1-DIRTY-COMMITTED + REQ-R2-NO-GIT + REQ-R3-NO-TESTS + REQ-R4-NO-OPENSPEC-SDD-STACK + REQ-R5-NO-GRAPHIFY-INFORMATIONAL

**Wording**: The workspace status surface SHALL surface 5 needs-attention rules: R1 dirty-committed, R2 no-git, R3 no-tests, R4 no-openspec-on-SDD-adjacent-stack (R4 informational-only in MVP), R5 no-graphify (informational-only in v1). Text default and `--json` envelope are both provided. R1 is explicitly deferred in Phase 4 (see REQ-WORKSPACE-R1-DEFERRED).

**Out of scope**: R1 remediation (Phase 4 explicitly defers it); R3/R4 bootstrap actions; Phase 5 dashboard integration.

---

### REQ-WORKSPACE-MUTATION-SAFETY

**Source**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-POLLUTION-PROTOCOL + REQ-HYGIENE-BACKUP-LAYOUT + REQ-HYGIENE-BACKUP-GATE-NONEMPTY

**Wording**: Every workspace mutation SHALL execute the pollution-protocol triple: backup snapshot → apply rule → verify post-mutation. On verify failure, the system SHALL restore from the snapshot and exit code 2. `flow workspace fix` SHALL refuse to mutate a non-empty project unless `--backup` is passed (non-empty = has_git absent AND has visible user files; hidden system files excluded). Backups are stored at `~/.flow-engineering/backups/<project>/<UTC-ISO>/` with a manifest; retention is INDEFINITE in MVP.

**Out of scope**: Backup pruning/TTL (deferred to future change); R1 remediation in the fix command.

---

### REQ-WORKSPACE-DRY-RUN-DEFAULT

**Source**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-DRY-RUN-DEFAULT

**Wording**: `flow workspace fix` and `flow workspace archive` default to dry-run mode (plan only, exit 0, no filesystem or registry mutation). Passing `--yes` switches to execute mode. Both commands refuse to mutate without `--yes`.

**Out of scope**: `--yes` gating on `flow workspace restore` and `flow workspace archived` (those commands are not mutation-level).

---

### REQ-WORKSPACE-R1-DEFERRED

**Source**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-R1-EXPLICITLY-OUT

**Wording**: R1 dirty-git remediation is OUT OF SCOPE for the workspace-hygiene MVP. `flow workspace fix` SHALL NOT execute any R1 remediation. R3 no-tests and R4 no-openspec bootstrap are also deferred. These are future changes.

**Out of scope**: R1 remediation implementation; R3/R4 bootstrap implementation.

---

### REQ-WORKSPACE-REGISTRY-V1

**Source**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` → REQ-HYGIENE-REGISTRY-V1

**Wording**: The system SHALL persist a registry at `~/.flow-engineering/registry.json` with schema `version: 1`, `projects: list[ProjectEntry]`, `archived: list[ArchivedEntry]`. Missing file returns empty default. Writes are atomic via `tempfile + os.replace`. Read-only consumers (`flow projects ls --json`, `flow workspace status`) MUST NOT create the registry.

**Out of scope**: Registry schema v2 (future change); registry migration tooling from v0.

---

### REQ-WORKSPACE-DASHBOARD-PLACEHOLDER

**Source**: Forward-looking (no delta spec yet)

**Wording**: Phase 5 of the workspace-intelligence arc will add a `workspace-dashboard` sub-capability (TUI or web visualization of workspace state). This REQ is a placeholder stub — the full requirement text will live in the Phase 5 delta spec. The root spec remains open until Phase 5 ships.

**Out of scope**: Phase 5 implementation; Phase 5 dashboard REQ text.

---

## 6. Sub-Capability Relationship Graph

```
                         ┌──────────────────────────────────────┐
                         │  openspec/specs/workspace/spec.md (NEW) │
                         │  root capability — anchors family       │
                         └──────────────┬───────────────┬──────────┘
                                        │               │
                         references     │               │    references
                                        ▼               ▼
              ┌─────────────────────────────────┐  ┌─────────────────────────────┐
              │  projects-ls-extension (P1)    │  │  workspace-status (P3)       │
              │  flow projects ls [--json]     │  │  flow workspace status [--json]│
              │  Phase 1 delta: 5 REQs          │  │  Phase 3 delta: 8 REQs incl.   │
              │  Source: workspace-intelligence │  │  R1–R5 rules                   │
              └──────────────┬──────────────────┘  └──────────────┬──────────────┘
                             │                                     │
                             │ _detect_project_markers (shared     │
                             │  helper, read-only on P1 surface)   │
                             └─────────────────┬───────────────────┘
                                               ▼
                             ┌──────────────────────────────────────┐
                             │  workspace-hygiene (P4)               │
                             │  flow workspace {fix,archive,          │
                             │    archived,restore}                   │
                             │  Phase 4 delta: 12 REQs                 │
                             │  Registry + pollution-protocol        │
                             └──────────────────┬───────────────────┘
                                                ▲
                                                │ Phase 5 (future)
                                                │
                             ┌──────────────────────────────────────┐
                             │  workspace-dashboard (P5)              │
                             │  flow workspace tui / web              │
                             │  STATUS: PLACEHOLDER STUB              │
                             └──────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │  flow-where (EXISTING capability, OUTSIDE workspace family)  │
    │  Phase 2 (flow-where-cross-project) reclassified HERE       │
    │  Follow-up: flow-where-cross-project-capability-merge       │
    └─────────────────────────────────────────────────────────────┘
```

**No cycles.** The dependency chain is strictly additive:
- Phase 3 depends on Phase 1 helper (`_detect_project_markers`, read-only)
- Phase 4 depends on Phase 3 registry gating + Phase 1 helper
- Phase 5 (future) will depend on Phase 3 + Phase 4

---

## 7. Spec Structure (Proposed Content Shape for sdd-spec)

Modeled on `openspec/specs/flow-where/spec.md` (245 LOC gold standard). Sections for `openspec/specs/workspace/spec.md`:

1. **Archive status header** — "NEW capability bootstrap — no prior root spec exists; anchors Phase 1–4 + Phase 5 placeholder"
2. **Purpose** (1 paragraph) — workspace = inventory/status/hygiene of projects
3. **Capability boundary** — workspace vs. where (explicit non-overlap statement)
4. **Sub-capabilities** (3 confirmed + 1 placeholder) — cross-refs to delta specs
5. **Requirements** — 7 synthesized root-level REQs (each with `Source:` line)
6. **Public API surface** — `flow projects ls`, `flow workspace status`, `flow workspace {fix,archive,archived,restore}`; no new Python API
7. **CLI surface** — command table
8. **Sub-capability graph** — ASCII diagram (above)
9. **Cross-Impact** — Phase 2 reclassification documented; `flow-where` sibling; other capabilities (decision-drift, observability, prompt-registry) unrelated
10. **Versioning** — version table with Phase anchors; Phase 5 TBD
11. **Future Changes** — `flow-where-cross-project-capability-merge` follow-up named; Phase 5 dashboard stub
12. **Drift Detection footer** — "Canonical requirements live in delta specs; this file is the family index"

---

## 8. Forecast

| Metric | Estimate |
|--------|----------|
| Total LOC (markdown) | ~250–350 |
| Review budget (400 lines) | ✅ Under by 15–35% |
| Files created | 1 (`openspec/specs/workspace/spec.md`) |
| Files modified | 0 |
| Files NOT touched | All of `src/`, `tests/`, `openspec/changes/archive/*`, `openspec/changes/v1.1-followups/*`, prior archived delta specs |
| Chained PRs | None |
| `size:exception` | Not needed |
| Tests added | 0 |
| Wall-time: spec | ~30 min |
| Wall-time: design | ~10 min |
| Wall-time: tasks | ~10 min |
| Wall-time: apply | ~10 min |
| Wall-time: verify | ~15 min |
| Wall-time: archive | ~15 min |
| **Total remaining** | **~90 min** |

---

## 9. Acceptance Criteria (for sdd-verify)

| # | Criterion |
|---|-----------|
| AC1 | `openspec/specs/workspace/spec.md` exists and references all 4 sub-capabilities (Phase 1 `projects-ls-extension`, Phase 3 `workspace-status`, Phase 4 `workspace-hygiene`, Phase 5 `workspace-dashboard` placeholder) |
| AC2 | Each of the 7 root-level REQs has a `Source:` line citing the exact delta spec path + REQ ID |
| AC3 | Phase 2 reclassification documented in Cross-Impact section (Phase 2 = `flow-where`, not `workspace`) |
| AC4 | Phase 5 dashboard placeholder documented in Future Changes section |
| AC5 | `flow-where-cross-project-capability-merge` follow-up named in Future Changes |
| AC6 | Drift Detection footer present with explicit drift mitigation strategy |
| AC7 | AC9 byte-identical guard still passes (`test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435`) — zero code changes |
| AC8 | Full suite 1513/1513 still passes — zero regressions |
| AC9 | NO modifications to any of the 4 prior archived specs (`projects-ls-extension`, `cross-project-search`, `workspace-status`, `workspace-hygiene`) |
| AC10 | `openspec/changes/v1.1-followups/` UNTOUCHED |
| AC11 | Spec length 250–350 LOC (under 400-line budget) |

---

## 10. Out of Scope (Explicit)

- **No code modifications** — no `src/` changes, no test changes, no `pyproject.toml` changes
- **No modifications** to existing root capability specs (`flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`)
- **No creation** of `openspec/specs/workspace-hygiene/spec.md` (separate future change)
- **No modifications** to any of the 4 prior archived change specs
- **No artifact-hygiene moves** — Phases 1–3 stay in their current `openspec/changes/` locations (not moved to `archive/`)
- **No Phase 2 reclassification code changes** — only documented as a follow-up in this spec
- **No Phase 5 dashboard implementation** — placeholder reference only
- **No `size:exception`**
- **No chained PRs**
- **No `openspec/changes/v1.1-followups/` touch** — sacred territory

---

## 11. Open Questions (All Resolved)

| # | Question | Answer |
|---|----------|--------|
| Q1 | Phase 2 reclassification — workspace or flow-where? | **`flow-where`** — user accepted reclassification rationale. Phase 2 is documented as a follow-up in this PR. |
| Q2 | Root REQ coverage — full enumeration or synthesized? | **7 synthesized** (not full 25). Each synthesized REQ has a `Source:` line citing the delta. |
| Q3 | Root spec role — canonical source or family index? | **Family index only.** Canonical requirements live in delta specs. Root has prominent callout to this effect. |
| Q4 | Phase 5 dashboard — reference now or add later? | **Reference now (1-2 paragraph placeholder)** to prevent the next orphan. |
| Q5 | Phase 2 follow-up name? | **`flow-where-cross-project-capability-merge`** — regenerate Phase 2 delta spec from Engram #456 + merge into `flow-where/spec.md`. |

---

## 12. Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Root REQ synthesis drifts from delta REQ wording over time | Medium | Each synthesized root REQ has a `Source:` line citing exact delta spec path + REQ ID. Root spec includes a Drift Detection footer stating delta specs are canonical. sdd-verify checks each `REQ-WORKSPACE-*` has a `Source:` line. |
| R2 | Reviewer misreads root spec as the canonical source for delta REQs | Medium | Root spec opens with a prominent callout: "Canonical requirements live in delta specs; this file is the family index." Matches `flow-where/spec.md` line 1 pattern. |
| R3 | Phase 2 follow-up (`flow-where-cross-project-capability-merge`) never gets done — Phase 2 delta spec stays missing forever | Medium (out of this PR's scope) | Named explicitly in Cross-Impact + Future Changes sections. Engram #456 has full content. Follow-up is a separate future change, not blocking this PR. |
| R4 | Phase 5 dashboard adds yet another orphan delta, re-triggering the problem this change solves | Low (this change directly prevents it) | Root spec includes `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` + Phase 5 in dependency graph + Future Changes section. Future Phase 5 appends to root + adds its own delta spec. |
| R5 | Pre-existing flake from `test_where.py` causes false positive in sdd-verify | Low | Baseline at `d077d75` is 1513/1513 passing. sdd-verify uses frozen deps and requires zero new failures. |

---

## 13. Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/workspace/spec.md` | **NEW** | The single deliverable — root capability spec, ~250–350 LOC |
| `openspec/changes/workspace-capability-bootstrap/proposal.md` | NEW | This proposal artifact |
| Engram `sdd/workspace-capability-bootstrap/proposal` | NEW | Engram mirror of proposal |
| `src/` | **UNTOUCHED** | No code changes |
| `tests/` | **UNTOUCHED** | No test changes |
| `openspec/changes/archive/` | **UNTOUCHED** | No archive modifications |
| `openspec/changes/v1.1-followups/` | **UNTOUCHED** | Sacred territory — not touched |

---

## 14. Next Phase

**Recommended next phase: `sdd-spec workspace-capability-bootstrap`**

The spec phase will mechanically write `openspec/specs/workspace/spec.md` following the structure in §7 of this proposal. All 7 root-level REQs are locked (§5). The Phase 2 reclassification text is locked (§4). All 14 user-locked constraints are encoded as AC1–AC11 (§9) + §10 out-of-scope.

After spec: `sdd-design` (minimal — anchor strategy, cross-reference inventory) → `sdd-tasks` (1 task: write the file) → `sdd-apply` (write + verify lint/mypy/test baseline unchanged) → `sdd-verify` (confirm AC1–AC11) → `sdd-archive` (move this change folder to `archive/` and commit).
