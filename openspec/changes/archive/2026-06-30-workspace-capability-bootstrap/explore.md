# Explore: `workspace-capability-bootstrap`

> **Change**: `workspace-capability-bootstrap`
> **Phase**: explore (1/7 of SDD cycle)
> **Author**: sdd-explore sub-agent
> **Date**: 2026-06-30
> **Project**: flow-engineering (v1.2.0, main HEAD `d077d75`)
> **Status**: COMPLETE — verdict ready for proposal phase

---

## Verdict (lead with the answer)

**Recommended approach: Approach B — Comprehensive root capability spec (~250–350 LOC).**

Create `openspec/specs/workspace/spec.md` modeled on `openspec/specs/flow-where/spec.md` (245-line template, the established gold standard for capability roots). The root anchors **3 sub-capabilities** (Phase 1 `projects-ls-extension`, Phase 3 `workspace-status`, Phase 4 `workspace-hygiene`) plus a **placeholder stub** for Phase 5 dashboard. **Phase 2 `flow-where-cross-project` is RECLASSIFIED out of `workspace` and into `flow-where`** — it is an additive extension of the existing `flow where` command, not a workspace primitive. That reclassification is the single most important finding of this exploration.

The root spec MUST:
- Reference, not duplicate, every REQ from the 3 delta specs (links over copies).
- Define the workspace boundary (project discovery + status + hygiene + dashboard).
- Cross-impact `flow-where` (Phase 2 reclassification) and `decision-drift` / `observability` / `prompt-registry` (other existing capabilities).
- Ship zero new code (this is a doc change; AC9 byte-identical guard is the only test surface to confirm nothing else broke).

---

## 1. Goal

Phase 1–4 of the workspace-intelligence arc landed as 4 separate deltas to a **non-existent root capability spec** at `openspec/specs/workspace/spec.md`. Every reviewer currently has to reconstruct the capability shape from scattered `openspec/changes/{workspace-intelligence,flow-where-cross-project,flow-workspace-status,workspace-hygiene}/` artifacts. Adding Phase 5 (dashboard) would add a 5th delta to the same orphan, widening the gap.

This change creates the root capability spec to anchor the family. **Single-file output**: `openspec/specs/workspace/spec.md`. Zero code modifications. The spec IS the deliverable.

User framing (Engram #484): *"Ahí se nota la diferencia entre 'funciona' y 'queda arquitectónicamente limpio.'"*

---

## 2. Scope

### 2.1 In

- One new file: `openspec/specs/workspace/spec.md` (root capability spec).
- Cross-references to all 4 prior delta specs + their archive locations.
- Cross-impact matrix referencing existing capabilities (`flow-where`, `decision-drift`, `observability`, `prompt-registry`).
- Engram mirror under topic_key `sdd/workspace-capability-bootstrap/explore` (this artifact).
- State file at `openspec/changes/workspace-capability-bootstrap/state.yaml` only if orchestrator requires it (NOT required for this explore phase; defer to propose).

### 2.2 Out (NON-NEGOTIABLE)

- **No code modifications.** No `src/` changes. No test changes.
- **No modification of any of the 4 prior specs** (`projects-ls-extension`, `cross-project-search`, `workspace-status`, `workspace-hygiene`).
- **No modification of any archive in `openspec/changes/archive/`**.
- **No touch of `openspec/changes/v1.1-followups/`** (sacred territory, per session preflight).
- **No introduction of new behavior** — only document what already exists.
- **No creation of `openspec/specs/workspace-hygiene/spec.md`** (separate future change, follow-up #2 in archive-report #477).
- **No consolidation of Phases 1–3 from `openspec/changes/` into `archive/`** — that's an artifact-hygiene problem, not a capability-root problem; defer.
- **No reclassification of `flow-where-cross-project` in this change** — the reclassification is RECOMMENDED here, but the spec that does it lives in `flow-where/spec.md` (separate future change).

---

## 3. Prior Art (Phase 1–4 references)

### 3.1 Phase map

| Phase | Change name | Archive location | Local artifacts | Status | Root under |
|---|---|---|---|---|---|
| 1 | `workspace-intelligence` | `openspec/changes/workspace-intelligence/` (NOT in archive yet) | explore/proposal/design/tasks + `specs/projects-ls-extension/spec.md` + status.md | ARCHIVED (status.md) but local | **workspace** ✅ |
| 2 | `flow-where-cross-project` | `openspec/changes/flow-where-cross-project/` (NOT in archive yet) | status.md ONLY — proposal/design/spec files MISSING locally | ARCHIVED (status.md) but local | **flow-where** ⚠️ (reclassification recommended — see §6) |
| 3 | `flow-workspace-status` | `openspec/changes/flow-workspace-status/` (NOT in archive yet) | explore/proposal/design/tasks + `specs/workspace-status/spec.md` + status.md | ARCHIVED (status.md) but local | **workspace** ✅ |
| 4 | `workspace-hygiene` | `openspec/changes/archive/2026-06-30-workspace-hygiene/` ✅ | explore/proposal/design/tasks + verify-report + archive-report + `specs/workspace-hygiene/spec.md` | MERGED + ARCHIVED on `main` (HEAD `d077d75`) | **workspace** ✅ |
| 5 (future) | `workspace-dashboard` | (not started) | — | TBD | **workspace** (placeholder in root spec) |

### 3.2 Pre-existing capability roots (the template)

`openspec/specs/` currently holds 4 root capability specs:

| Root | Size (LOC) | Pattern used | Anchored sub-capabilities |
|---|---|---|---|
| `decision-drift/` | (legacy single-PR) | Lightweight | — |
| `flow-where/` | 245 | **Gold standard** (mirror in style) | (none — MVP was single PR) |
| `observability/` | (legacy) | Lightweight | — |
| `prompt-registry/` | (legacy) | Lightweight | — |

**Template to follow: `openspec/specs/flow-where/spec.md`.** Its structure is:

1. Archive status header (history block at top)
2. Purpose (one paragraph: what the capability IS)
3. Source (links to archived change artifacts — canonical requirements live there)
4. Requirements (REQ-V1.0.X blocks, each with a Given/When/Then scenario)
5. Public API surface (Python-shape signatures with file:line refs)
6. CLI surface (commands, flags, exit codes, output contract example)
7. Cross-Impact (relationships to other capabilities)
8. Versioning (version history table with REQ anchors per shipped change)

The Phase 4 spec (`openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md`, 286 LOC) uses a delta-spec convention (Purpose / ADDED REQs / MODIFIED / REMOVED / BDD / AC / Cross-Refs) — **the delta-spec format is the right shape for `specs/workspace-hygiene/spec.md` later, not for the root.** The root uses the `flow-where` catalog format.

### 3.3 Engram observations already pulled

| Obs | Type | Topic | Use in this explore |
|---|---|---|---|
| #464 | architecture | `sdd/workspace-hygiene/explore` | Source for Phase 4 REQ inventory + tech debt list |
| #483 | session_summary | Phase 4 close-out | Source for current main HEAD `d077d75` + convention details (CHANGELOG per-release, sacred territory, stash workaround, byte-identical guard) |
| #484 | pattern | "Fix orphan capability roots before more deltas" | Source for the user's framing quote + the motivation for this change |
| #485 | config | `sdd-preflight/workspace-capability-bootstrap` | Source for A1/B1/C1/D1 preflight decisions |
| #455 | architecture | `sdd/flow-where-cross-project/proposal` | Source for Phase 2's 6 search dirs + 3 format decisions + "ADDITIVE to where_cmd" classification |
| #456 | specification | `sdd/flow-where-cross-project/spec` | Source for Phase 2's 6 REQs (REQ-CROSS-PROJECT-SCOPE, REQ-DEFAULT-TEXT-FORMAT, REQ-EXPLICIT-FORMAT-FLAG, REQ-EXIT-CODE-MAPPING, REQ-ENGRAM-STUB, REQ-REGEX-OPT-IN) + 7 BDD scenarios |

---

## 4. Capability Family Analysis

### 4.1 What belongs to the `workspace` capability family?

**INVESTIGATION RESULT: 3 confirmed + 1 placeholder. Phase 2 is OUT (reclassified).**

| Sub-capability | Phase | CLI surface | REQs at root level? | Confirmed |
|---|---|---|---|---|
| **`projects-ls-extension`** | 1 | `flow projects ls [--json]` | No — `--json` flag is project-discovery surface, lives in delta spec | ✅ IN |
| **`flow-where-cross-project`** | 2 | `flow where <query> --root PATH [--format ...]` | N/A — **RECLASSIFIED to `flow-where` capability** | ⚠️ OUT |
| **`workspace-status`** | 3 | `flow workspace status [--json]` | Partially — R1–R5 are workspace-primitive semantics | ✅ IN |
| **`workspace-hygiene`** | 4 | `flow workspace {fix,archive,archived,restore}` | Partially — registry schema + pollution-protocol are workspace-primitive | ✅ IN |
| **`workspace-dashboard`** (future) | 5 | `flow workspace tui` / web | TBD — visualization of workspace state | 📌 PLACEHOLDER |

### 4.2 Phase 2 reclassification (the most important finding)

Phase 2 (`flow-where-cross-project`) was tagged as "Phase 2 of the workspace-intelligence effort" in its status.md (line 45), but **its actual scope is an additive extension of the `flow where` command, not a workspace primitive**. Evidence:

1. **Phase 2's own proposal (#455)** states: *"ADDITIVE to where_cmd — do NOT replace existing where.py module API"*.
2. **Phase 2 reuses `_run_search` from `where.py`** (read-only on the existing `flow-where` module).
3. **Phase 2's 6 search directories** (`src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/`) are code+archive search targets, NOT project-discovery or project-status targets.
4. **The existing `flow-where/spec.md` (245 LOC)** is the natural home — REQs V1.0.1..V1.0.4 cover the single-project case; Phase 2's 6 REQs would become V1.0.5..V1.0.X covering the cross-project case.
5. **The semantic test**: would Phase 2's REQs make sense if `workspace` capability never existed? Yes — Phase 2 is "find code across projects." That's a `flow-where` concern, not a workspace concern.

**Recommendation**: Phase 2's delta spec (currently MISSING from `openspec/changes/flow-where-cross-project/specs/`) should be regenerated from Engram #456 and merged into `openspec/specs/flow-where/spec.md` as a new REQ-V1.0.X block. **This is a SEPARATE future change** (`flow-where-cross-project-capability-merge` or similar) and is explicitly OUT OF SCOPE for `workspace-capability-bootstrap`.

**User-visible label**: when the orchestrator reports this to the user, the framing should be: *"Phase 2 is now classified under `flow-where` (not `workspace`) — this is correct, but creates a follow-up: regenerate Phase 2's missing delta spec from Engram #456 and merge it into `flow-where/spec.md`."*

### 4.3 Phase 5 placeholder

Phase 5 (`flow workspace tui` / web dashboard) is referenced from session #483 ("Phase 5 (dashboard TUI/web) — NOT in scope of Phase 4; future work after CLI is solid"). The root capability spec SHOULD include a placeholder stub for it (1-2 paragraphs: "visualization of workspace state — deferred to a separate change"), NOT the full REQ set. This anchors the family shape and prevents the next orphan.

---

## 5. Boundary Definition

### 5.1 What the `workspace` capability IS

A `workspace` is a **collection of projects under a single projects root** (default `<root>`). The capability covers:

1. **Project discovery** — enumerate the projects; report static metadata (git presence, branch, dirty state, stack, test commands, openspec presence). *(Phase 1)*
2. **Project status aggregation** — read-only synthesis of per-project metadata into `needs_attention` rules (R1–R5: dirty, no-git, no-tests, no-openspec, no-graphify). *(Phase 3)*
3. **Project hygiene** — write-side remediation of R2 (no-git → `git init`) plus registry-mediated archive/restore of projects the user no longer maintains. *(Phase 4)*
4. **Project dashboard** *(Phase 5 placeholder)* — visualization of workspace state.

### 5.2 What the `workspace` capability IS NOT

| Out-of-scope | Why | Where it belongs |
|---|---|---|
| **Cross-project code/SDD search** | Operates on file CONTENTS across projects, not on project METADATA | `flow-where` capability (Phase 2 reclassification) |
| **SDD ceremony orchestration** | Different domain entirely | `prompt-registry` / `decision-drift` (existing) |
| **Engram operations** | Memory backend, not workspace state | (no root — Engram is a Go project, not an OpenSpec capability) |
| **Drift detection** | Already its own capability | `decision-drift` (existing) |
| **Metrics / observability counters** | Different domain | `observability` (existing) |
| **Graph index storage** | Different domain | (no root — graphify-out is a generated artifact) |

### 5.3 Boundary stress tests

| Scenario | Workspace? | Why |
|---|---|---|
| "What projects do I have?" | ✅ YES | Project discovery (Phase 1) |
| "Which of my projects need attention?" | ✅ YES | Project status aggregation (Phase 3) |
| "Initialize git on the no-git project `mockup`." | ✅ YES | Project hygiene (Phase 4) |
| "Find where I implemented X across all projects." | ❌ NO — `flow-where` | Cross-project code search (Phase 2) |
| "Archive `mockup` — I no longer maintain it." | ✅ YES | Project hygiene (Phase 4) |
| "Show me a TUI of my workspace." | ✅ YES (Phase 5) | Project dashboard |
| "What did I decide about X yesterday?" | ❌ NO — `decision-drift` | Drift detection (existing capability) |

---

## 6. REQ Candidates (root-level only)

### 6.1 Sub-capability REQ inventory

| Phase | Delta spec | REQ count | Delta spec path |
|---|---|---|---|
| 1 | `projects-ls-extension` | 5 (REQ-`--json`-FLAG, REQ-FIELD-EXTENSION, REQ-HAS-ENGRAM-STUB, REQ-SCHEMA-VERSIONING, REQ-DETERMINISTIC-ORDER) | `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` |
| 3 | `workspace-status` | 8 (REQ-R1..R5, REQ-WS-JSON-ENVELOPE, REQ-WS-TEXT-DEFAULT, REQ-WS-EMPTY-ROOT) | `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` |
| 4 | `workspace-hygiene` | 12 (REQ-HYGIENE-FIX-SURFACE, ARCHIVE-SURFACE, ARCHIVED-LISTING, RESTORE-SURFACE, REGISTRY-V1, BACKUP-LAYOUT, POLLUTION-PROTOCOL, DRY-RUN-DEFAULT, BACKUP-GATE-NONEMPTY, AC9-PRESERVATION, R1-EXPLICITLY-OUT, NO-JSON-MVP) | `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` |

**Total: 25 REQs across 3 delta specs.** Plus Phase 5 placeholder (~3 REQs, TBD).

### 6.2 REQs that TRULY belong at the root (vs. delta-internal)

A REQ is "root-level" if (a) it defines a workspace-primitive that is not specific to one delta, or (b) it establishes a contract that spans deltas. A REQ is "delta-internal" if (c) it describes the specific shape of a single command, or (d) it is a meta-requirement (e.g., "R1 explicitly out") that belongs only to the delta where the carve-out was made.

| REQ | Origin | Root-level? | Why |
|---|---|---|---|
| REQ-FIELD-EXTENSION | Phase 1 | ❌ Delta | Shape of `flow projects ls` 11-field output |
| REQ-HAS-ENGRAM-STUB | Phase 1 | ⚠️ Borderline | Stub semantics affect cross-capability contracts; mention in root |
| REQ-R1..R5 | Phase 3 | ✅ Root | These ARE the workspace-primitive status rules. The root should enumerate R1–R5 with one-line summaries and link to the delta spec for full text |
| REQ-WS-JSON-ENVELOPE | Phase 3 | ❌ Delta | JSON envelope shape is Phase 3 surface |
| REQ-WS-TEXT-DEFAULT | Phase 3 | ❌ Delta | Text default is Phase 3 surface |
| REQ-HYGIENE-REGISTRY-V1 | Phase 4 | ✅ Root | The registry schema (`~/.flow-engineering/registry.json`, `version: 1`, `projects[]/archived[]`) IS a workspace-primitive. Other capabilities may consume it later |
| REQ-HYGIENE-POLLUTION-PROTOCOL | Phase 4 | ✅ Root | The backup → mutate → verify triple IS a workspace-primitive (mutations always use it) |
| REQ-HYGIENE-DRY-RUN-DEFAULT | Phase 4 | ❌ Delta | Specific to `fix`/`archive` |
| REQ-HYGIENE-BACKUP-GATE-NONEMPTY | Phase 4 | ❌ Delta | Specific to `fix` |
| REQ-HYGIENE-AC9-PRESERVATION | Phase 4 | ✅ Root | The byte-identical guard is a workspace-level invariant (any future workspace mutation MUST preserve it) |
| REQ-HYGIENE-R1-EXPLICITLY-OUT | Phase 4 | ⚠️ Borderline | "R1 is out" is a workspace-level fact (R1 remediation is deferred), but the specific wording belongs in the Phase 4 delta spec. Root mentions: "R1 remediation deferred — see Phase 4 spec" |
| REQ-HYGIENE-NO-JSON-MVP | Phase 4 | ❌ Delta | MVP scope lock |

**Root-level REQs to synthesize (~5–7):**

| Root REQ | Synthesis source |
|---|---|
| **REQ-WORKSPACE-DISCOVERY** | Phase 1's REQ-FIELD-EXTENSION (one-paragraph summary) |
| **REQ-WORKSPACE-STATUS-RULES-R1-R5** | Phase 3's REQ-R1..R5 (one-paragraph summary each) |
| **REQ-WORKSPACE-REGISTRY-V1** | Phase 4's REQ-HYGIENE-REGISTRY-V1 (full text — schema is root-level) |
| **REQ-WORKSPACE-MUTATION-POLLUTION-PROTOCOL** | Phase 4's REQ-HYGIENE-POLLUTION-PROTOCOL (full text — invariant applies to all future mutations) |
| **REQ-WORKSPACE-ENVELOPE-BYTE-DETERMINISM** | Synthesized from Phase 1's REQ-SCHEMA-VERSIONING + Phase 3's REQ-WS-JSON-ENVELOPE + Phase 4's REQ-HYGIENE-AC9-PRESERVATION (the byte-identical invariant is workspace-level) |
| **REQ-WORKSPACE-DEFERRED-RULES** | Synthesized from Phase 4's REQ-HYGIENE-R1-EXPLICITLY-OUT (R1 remediation deferred; R3/R4 bootstrap deferred) |
| **REQ-WORKSPACE-DASHBOARD-PLACEHOLDER** | Forward-looking stub for Phase 5 |

### 6.3 What NOT to put in the root

- Full text of every delta REQ. The root must REFERENCE, not DUPLICATE. Duplication invites drift.
- Cross-capability BDD scenarios spanning Phase 1+3+4 (e.g., "discover → status → fix"). These are nice-to-have but expand the spec scope; defer to a future BDD-cross-cutting change.
- Phase 5 REQ text. Just a placeholder paragraph.

---

## 7. Sub-capability Relationship Graph

### 7.1 Dependency graph

```
                    ┌─────────────────────────────────────────┐
                    │  openspec/specs/workspace/spec.md (NEW) │
                    │  root capability — anchors family       │
                    └────────────┬─────────────┬──────────────┘
                                 │             │
                  references     │             │    references
                                 ▼             ▼
        ┌────────────────────────────────┐  ┌────────────────────────────────┐
        │  projects-ls-extension (P1)    │  │  workspace-status (P3)         │
        │  flow projects ls [--json]     │  │  flow workspace status [--json]│
        │  src/flow_engineering/cli.py   │  │  src/flow_engineering/cli.py   │
        │  Req: 11-field per project     │  │  Req: 8 REQs incl. R1-R5      │
        └─────────────┬──────────────────┘  └────────────────┬───────────────┘
                      │                                       │
                      │ shared helper                        │ shared helper
                      │                                       │
                      └────────────────┬──────────────────────┘
                                       │ _detect_project_markers
                                       ▼
                          ┌──────────────────────────────┐
                          │  workspace-hygiene (P4)      │
                          │  flow workspace {fix,         │
                          │    archive,archived,restore}  │
                          │  src/flow_engineering/cli.py │
                          │  src/flow_engineering/        │
                          │    registry.py (NEW)          │
                          │  src/flow_engineering/        │
                          │    workspace_hygiene.py (NEW) │
                          │  Req: 12 REQs                 │
                          └──────────────────────────────┘
                                       ▲
                                       │ Phase 5 (future)
                                       │
                          ┌──────────────────────────────┐
                          │  workspace-dashboard (P5)    │
                          │  flow workspace tui / web    │
                          │  STATUS: PLACEHOLDER          │
                          └──────────────────────────────┘
```

### 7.2 Cycle detection

**No cycles.** The dependency chain is strictly additive:

- Phase 3 (status) depends on Phase 1 (detection helper)
- Phase 4 (hygiene) depends on Phase 3 (registry gates) + Phase 1 (detection helper, read-only)
- Phase 5 (dashboard, future) will depend on Phase 3 (read aggregation) + Phase 4 (registry)

### 7.3 Out-of-family cross-references (Phase 2 reclassification visualized)

```
                          ┌──────────────────────────────────┐
                          │  flow-where/spec.md (EXISTING)    │
                          │  REQ-V1.0.1..V1.0.4 (single-proj) │
                          │  src/flow_engineering/where.py    │
                          └────────────────┬─────────────────┘
                                           │ additive extension
                                           ▼
                          ┌──────────────────────────────────┐
                          │  flow-where-cross-project (P2)   │
                          │  REQ-V1.0.5..V1.0.X (cross-proj)  │
                          │  --root PATH --format {t,j,s}    │
                          │  src/flow_engineering/cli.py     │
                          │  STATUS: delta spec MISSING      │
                          │    locally — only Engram #456    │
                          └──────────────────────────────────┘
```

The Phase 2 graph is OUT of the workspace family but adjacent — the workspace root spec must reference it in the Cross-Impact section as "sibling capability under `flow-where`".

### 7.4 Cross-impact summary table (to be encoded in the root spec)

| Capability | Direction | Notes |
|---|---|---|
| `flow-where` (existing) | Sibling | Phase 2 (`flow-where-cross-project`) is an additive extension; workspace status/dashboard may surface cross-project search hits in future |
| `decision-drift` (existing) | Sibling | Unrelated; workspace status doesn't surface drift |
| `observability` (existing) | Sibling | Unrelated; workspace mutations don't emit metrics |
| `prompt-registry` (existing) | Sibling | Unrelated; workspace mutations don't consume PROMPT_NAMES |

---

## 8. Open Questions

| # | Question | Tradeoff |
|---|---|---|
| **Q1** | Should `flow-where-cross-project` (Phase 2) be under `workspace` or under `flow-where`? | **Recommendation: `flow-where`.** Phase 2 is an additive extension of `flow where`, not a workspace primitive. See §4.2 for evidence. |
| **Q2** | Should the root spec enumerate ALL REQs from sub-capabilities (full duplication) or only root-level synthesized REQs (with references)? | **Recommendation: Root-level only + references.** Full duplication invites drift when delta specs evolve; references keep the root a stable index. |
| **Q3** | Should the root spec define an interface contract (input/output JSON shapes, exit codes, error envelope)? | **Recommendation: Light contract only.** The root should state the version envelope convention (`version: "1"` first key, byte-identical for unchanged roots) and the registry schema (`~/.flow-engineering/registry.json`). Detailed shapes live in delta specs. |
| **Q4** | Should Phase 5 dashboard be referenced from root now (placeholder) or added later when Phase 5 actually starts? | **Recommendation: Reference now (1–2 paragraph placeholder).** Anchors the family shape so the next orphan doesn't form. |
| **Q5** | Should the root spec include BDD scenarios that span sub-capabilities (e.g., "discover → status → fix" end-to-end)? | **Recommendation: No.** Cross-cutting BDD is a separate future change. The root stays behavior-loose; delta specs own their BDD. |
| **Q6** | Should the root spec define a workspace-level version number (`workspace: v1.0`)? | **Recommendation: Yes — use `version: "1"` envelope convention.** Mirrors the per-command envelope convention. Future deltas that bump the workspace contract (e.g., registry schema v2) would update the root spec and announce it in the version table. |
| **Q7** | Should the root spec include a Mermaid / ASCII diagram of the sub-capability graph? | **Recommendation: Yes (ASCII block, see §7.1).** Visualizes the dependency chain for reviewers; matches the cognitive-doc-design principle of recognition over recall. |
| **Q8** | Should this change reclassify Phase 2 (move `flow-where-cross-project` artifacts under `flow-where/`)? | **Recommendation: NO — out of scope.** This change documents the reclassification; a SEPARATE future change (`flow-where-cross-project-capability-merge`) regenerates Phase 2's missing delta spec from Engram #456 and merges it into `flow-where/spec.md`. |

---

## 9. Approach Candidates

### Approach A — Minimal root spec

**Scope**: Root spec = capability name + 1-paragraph boundary + sub-capability list with links + cross-impact table.

**Content shape**:
- §1 Purpose (1 paragraph)
- §2 Source (links to 3 delta specs + Phase 2 reclassification note)
- §3 Cross-Impact (table)
- §4 Versioning (table)

**LOC estimate**: ~80–120 LOC of markdown.

**Pros**:
- Fastest to write and review (~10 min).
- Zero risk of drift (no REQ duplication).
- Clear handoff to future deltas ("just append to the catalog").

**Cons**:
- Doesn't anchor the workspace-primitive REQs (R1–R5, registry schema, pollution-protocol, byte-determinism invariant). Reviewers still have to read all 3 delta specs to understand what the capability IS.
- No diagram — visual learners lose the family shape at a glance.

**Risk**: Low (doc-only).

### Approach B — Comprehensive root spec **(RECOMMENDED)**

**Scope**: Root spec = Approach A + 5–7 synthesized root-level REQs (with one-paragraph summaries linking to delta specs for full text) + ASCII dependency graph + Phase 5 placeholder + version table.

**Content shape**:
- §1 Archive status header (small — this is the FIRST root, no prior archive)
- §2 Purpose
- §3 Boundary (in/out)
- §4 Source (links to 3 delta specs + Phase 2 reclassification note)
- §5 Requirements (REQ-WORKSPACE-DISCOVERY, REQ-WORKSPACE-STATUS-RULES-R1-R5, REQ-WORKSPACE-REGISTRY-V1, REQ-WORKSPACE-MUTATION-POLLUTION-PROTOCOL, REQ-WORKSPACE-ENVELOPE-BYTE-DETERMINISM, REQ-WORKSPACE-DEFERRED-RULES, REQ-WORKSPACE-DASHBOARD-PLACEHOLDER)
- §6 Public surface (CLI verbs grouped under `flow workspace` + `flow projects`)
- §7 Sub-capability graph (ASCII)
- §8 Cross-Impact (table)
- §9 Versioning (table)

**LOC estimate**: ~250–350 LOC of markdown (under the 400-line review budget).

**Pros**:
- Anchors the workspace-primitive semantics at the root (R1–R5 + registry schema + pollution-protocol are workspace-level facts).
- Future deltas just append; reviewers always know where the family contract lives.
- ASCII graph provides visual anchor.
- Mirrors `flow-where/spec.md` template (245 LOC) — establishes precedent for other capabilities.

**Cons**:
- Synthesizing root REQs requires care to not duplicate delta wording (drift risk). Mitigation: each synthesized REQ has a "Source" line pointing to the delta spec; full text stays in delta.
- ~30–45 min to write.

**Risk**: Low (doc-only; no code, no tests, AC9 byte-identical guard untouched).

### Approach C — Full catalog (enumeration)

**Scope**: Root spec = Approach B + FULL TEXT of every REQ from every sub-capability (no synthesis, no references — just copies).

**Content shape**: All of Approach B + 25+ REQ blocks in full + 25+ BDD scenarios.

**LOC estimate**: ~800–1200 LOC of markdown (2–3× over the 400-line review budget).

**Pros**:
- Single-file overview; no need to follow links.
- "Everything you need to know about workspace in one place."

**Cons**:
- **Exceeds the 400-line review budget by 2–3×.** Would require chained PR or size:exception.
- **High drift risk.** When a delta spec evolves (e.g., Phase 4 adds a new hygiene verb), the root must be updated too. Two sources of truth that must stay in sync = bug factory.
- Future deltas expand the root, making it unwieldy.

**Risk**: Medium (drift) + High (budget overrun).

### Approach Comparison Matrix

| Dimension | A — Minimal | B — Comprehensive (RECOMMENDED) | C — Catalog |
|---|---|---|---|
| LOC | 80–120 | 250–350 | 800–1200 |
| Review budget (400) | ✅ under | ✅ under | ❌ 2–3× over |
| Drift risk | None | Low (references) | High (duplication) |
| Anchors workspace primitives? | ❌ No | ✅ Yes | ✅ Yes |
| Reviewer time to grok family? | ~5 min | ~10–15 min | ~25–40 min |
| Future delta cost | "Append to root" | "Append to root" | "Update root + delta + cross-check" |
| Matches `flow-where` template? | Partial | ✅ Yes | Over-matches (catalog != capability root) |

**Verdict: Approach B.** It matches the `flow-where/spec.md` template (the established gold standard), stays well under the 400-line budget, and anchors workspace-primitive semantics without duplicating delta REQ text.

---

## 10. Tech Debt Interactions

This section enumerates pre-existing tech debt that THIS change will surface or interact with. Per session preflight: **NO modifications** are in scope; only documentation.

| # | Tech debt item | Source | This change's interaction |
|---|---|---|---|
| **TD1** | 3 pre-existing lint errors: `cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292` | Session #483 discoveries (post-Phase-4 close-out) | OOS — document in verify-report but DO NOT touch. Verify these still exist after the spec phase. |
| **TD2** | Orphan `openspec/specs/workspace/spec.md` — does not exist | The motivation for this change | THIS CHANGE CREATES IT. No prior version exists; nothing to merge or migrate from. |
| **TD3** | Phases 1–3 artifacts still in `openspec/changes/` (not moved to `archive/`) | Session #483: "Phase 4 was the first one properly archived" | OOS — separate artifact-hygiene concern. Root spec should LINK to the live locations (`openspec/changes/workspace-intelligence/specs/...`) rather than `archive/` paths, since archive hasn't happened yet for P1–P3. |
| **TD4** | Phase 2's SDD artifacts (proposal.md, design.md, spec.md) MISSING locally — only `status.md` survives in `openspec/changes/flow-where-cross-project/` | Discovered during this explore (file enumeration §1) | Documented in §4.2 and §8 Q8. Root spec will reference Phase 2 by name + Engram #456 for content. The follow-up change regenerates the missing artifacts and merges into `flow-where/spec.md`. |
| **TD5** | AC9 byte-identical guard at `tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope` | Session #483 AC9 preservation pattern | No interaction (we don't touch code/tests). Verify it still passes post-sdd-verify. The root spec MUST cite this test by path:line in REQ-WORKSPACE-ENVELOPE-BYTE-DETERMINISM. |
| **TD6** | `_git` seam at `cli.py:3045` (used by Phase 4's `git init`) | Session #483 discoveries | No interaction (no code touch). Root spec may cite it as a future-extension point for Phase 4 R1 (deferred) or R3/R4 bootstrap. |
| **TD7** | Backup retention INDEFINITE in Phase 4 MVP — manual cleanup is operator's responsibility | Phase 4 spec REQ-HYGIENE-BACKUP-LAYOUT | Documented in Phase 4 spec; root spec's REQ-WORKSPACE-MUTATION-POLLUTION-PROTOCOL should reference it as a known operational consideration, NOT re-litigate it. |
| **TD8** | Phase 4 follow-ups queued (R1 dirty-git, R3 no-tests, R4 no-openspec, backup retention policy) | Session #483 "Next Steps" + archive-report #477 | Root spec's REQ-WORKSPACE-DEFERRED-RULES enumerates these as future changes. No code work; just documentation anchors. |

### Pre-existing failures baseline (per session #483, still true)

- **0 pre-existing test failures on main** at HEAD `d077d75` (Phase 4 close-out). All 1513/1513 tests pass, mypy clean (except RET504 OOS), ruff clean (except the 3 errors OOS).
- **This change must keep this baseline green.** sdd-verify will run `uv run --frozen pytest tests/` + `uv run --frozen mypy src/` + `uv run --frozen ruff check .` and verify zero new failures.

---

## 11. Forecast

| Metric | Estimate | Reasoning |
|---|---|---|
| Total LOC (markdown only) | ~250–350 | Approach B shape; matches `flow-where/spec.md` 245-LOC template |
| Review budget (400 lines) | ✅ Under (15–35% margin) | Approach B fits comfortably |
| Files created | 1 (`openspec/specs/workspace/spec.md`) | The ONLY deliverable |
| Files modified | 0 | Doc-only change |
| Files NOT touched | All of `src/`, `tests/`, `pyproject.toml`, `openspec/changes/archive/*`, `openspec/changes/v1.1-followups/`, `openspec/changes/{workspace-intelligence,flow-where-cross-project,flow-workspace-status}/*` | Sacred territory + read-only deltas |
| Chained PR strategy | Not needed | Single file, single PR |
| Tests added | 0 | Spec IS the deliverable; AC9 byte-identical guard is the regression net |
| Strict TDD mode | **OFF** | This is a doc change; forward `tdd: false` to sdd-apply (per session preflight) |
| Test runner | N/A | No tests in scope |
| Lint | N/A | No code changes |
| Type-check | N/A | No code changes |
| Wall-time estimate | explore=25m · propose=20m · spec=30m · design=10m · tasks=10m · apply=10m · verify=15m · archive=15m ≈ **2.5 hours total** | Doc-only; most time in spec writing (synthesizing 7 root REQs from 25 delta REQs). Significantly faster than Phase 4's 4.5–6h. |
| Engram mirror | 1 observation (this artifact's mirror) | topic_key `sdd/workspace-capability-bootstrap/explore`; type `architecture`; `capture_prompt: false` per session preflight |

---

## 12. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| **R1** | Root REQ synthesis drifts from delta REQ wording over time | Medium | Each synthesized root REQ cites its source delta REQ by exact name + path; root spec includes a "Drift Detection" footer paragraph stating that delta specs are canonical and root summaries are informational. sdd-verify checks that each `REQ-WORKSPACE-*` block in root has a `Source:` line. |
| **R2** | Reviewer misreads root spec as the canonical source for delta REQs | Medium | Root spec opens with a prominent "Canonical requirements live in delta specs; this file is the family index" callout. Matches `flow-where/spec.md` line 1. |
| **R3** | Phase 2 reclassification creates a follow-up debt that never gets done (Phase 2's missing delta spec stays missing forever) | Medium (out of this change's scope) | The root spec's Cross-Impact table flags Phase 2 as "delta spec missing — see Engram #456". The follow-up (`flow-where-cross-project-capability-merge`) is added to the workspace capability's "Future changes" list, NOT to this change's tasks. |
| **R4** | Future Phase 5 dashboard adds yet another delta to the workspace root, re-triggering the orphan problem | Low (this change directly prevents it) | Root spec includes REQ-WORKSPACE-DASHBOARD-PLACEHOLDER + Phase 5 reference in the dependency graph + "Future changes" section. Future Phase 5 just appends to root + adds its own delta spec. |
| **R5** | `sdd-verify` runs tests and a pre-existing flake causes a false positive | Low | sdd-verify uses `uv run --frozen pytest tests/ -q` and requires zero new failures vs baseline (1513/1513 at `d077d75`). The 3 OOS lint errors are documented as "pre-existing — accepted per Phase 4 close-out". |

---

## 13. Affected Areas

- **CREATE**: `openspec/specs/workspace/spec.md` (the deliverable, ~250–350 LOC).
- **NO MODIFICATIONS** anywhere else.
- **ENGRAM MIRROR**: 1 new observation, topic_key `sdd/workspace-capability-bootstrap/explore`, type `architecture`, `capture_prompt: false`, scope `project`, project `flow-engineering`.

---

## 14. Next Phase

**Recommended next phase: `sdd-propose workspace-capability-bootstrap`.**

The proposal phase will:
1. Lock Approach B (comprehensive root spec, ~250–350 LOC).
2. Lock the root-level REQ inventory (the 7 synthesized REQs in §6.2).
3. Lock the Phase 2 reclassification as a documentation statement (no code change in this PR).
4. Lock the version envelope convention (`workspace: v1` = `version: "1"` first key, byte-identical).
5. Lock the out-of-scope list (no code, no test changes, no archive-move, no Phase 2 reclassification code change).
6. Resolve any remaining open questions from §8 (the orchestrator may need user input on Q1/Q8 if the user disagrees with Phase 2 reclassification).

After proposal: spec (write the actual root spec content) → design (minimal — anchor strategy, cross-reference inventory) → tasks (1 task: write the file) → apply (write the file + verify lint/mypy/test baseline unchanged) → verify (confirm zero new failures + AC9 guard still passes) → archive (move this change folder to `archive/2026-06-30-workspace-capability-bootstrap/` and commit).

---

## 15. User-Facing Summary (for orchestrator to translate)

This explore phase found:

1. **The orphan is real and growing.** 4 deltas landed with no root spec.
2. **Phase 2 is misclassified.** It belongs under `flow-where` (not `workspace`). This is a structural correction; the root spec documents it as a future-change follow-up.
3. **The root spec anchors 3 confirmed sub-capabilities + 1 placeholder** (Phase 5 dashboard). 25 delta REQs across 3 specs → 7 synthesized root REQs.
4. **Recommended approach: Approach B** (comprehensive, ~250–350 LOC, matches the `flow-where/spec.md` template, stays well under the 400-line budget).
5. **The deliverable is a single new file.** Zero code changes, zero test changes, zero archive modifications. Fastest cycle in the workspace-intelligence arc (~2.5 hours wall time vs Phase 4's 4.5–6h).
6. **One follow-up identified**: regenerate Phase 2's missing delta spec from Engram #456 and merge into `flow-where/spec.md`. OUT OF SCOPE for this change but documented in root's Cross-Impact + Future Changes.
7. **No tech debt is regressed.** 3 pre-existing lint errors + AC9 byte-identical guard remain documented; this change adds zero new failures.