# Explore: flow-workspace-status — Phase 3 of workspace-intelligence

> Read-only exploration. No source files modified. `flow projects ls --json` is the **only** data source; everything this change displays is already in the v1 envelope from Phase 1 (`cb63b7d`, archived via Engram #444).

## 1. Existing data sources — Phase 1 v1 envelope

`flow projects ls --json` emits `{"version":"1","root":"<abs>","projects":[{name, path, has_git, branch|null, dirty|null, remote|null, stack, test_commands[], has_openspec, has_graphify, has_engram}, ...]}`. Top-level key order enforced by CPython 3.7+ dict order; `version` is **first**. **No `generated_at`** (AC8 byte-determinism fix, #443). Live verified 6008 bytes byte-identical across two consecutive invocations on `<root>` (#444). Detection in `_detect_project_markers()` (`cli.py:2586`, 63 LOC). Phase 3 aggregation is **purely** post-hoc on those JSON bytes — no new probes, no second scan.

## 2. Phase 3 scope

User-locked (verbatim): "qué proyectos están dirty, cuáles no tienen git, cuáles tienen tests, cuáles tienen OpenSpec/Graphify, qué necesita atención." Out: Phase 2 (`flow where`), Phase 4 (hygiene), Phase 5 (dashboard), real Engram integration, Graphify profundo, modifying `_detect_project_markers()`, sub-processing `<root>`.

## 3. New subcommand — `flow workspace status`

Top-level `flow` group, NOT under `flow projects` (different capability: synthesis vs inventory; user verbatim locks this name). CLI:

```
flow workspace status [--root PATH] [--json]
```

- `--root PATH` — overrides `FLOW_PROJECTS_ROOT` env + Windows default. Mirrors `flow projects ls --root`.
- `--json` — mandatory for Phase 2/4/5 to consume; default is human-readable ASCII.

## 4. Output structure

**Default (text, ASCII-safe)**:

```
Workspace status — <root>                          N projects
  DIRTY
    my-app             main  (3 files)
    blog               main  (1 file)
  TOTAL: 2 / N dirty
  NO GIT
    scratch/
  TOTAL: 1 / N no-git
  NO TESTS
    api/, scratch/
  TOTAL: 2 / N no-tests
  OPENSPEC / GRAPHIFY / ENGRAM coverage
    openspec:  K / N      graphify:  K / N    engram:  0 / N  (stubs)
  NEEDS ATTENTION (M / N)
    my-app    dirty + no-openspec
    scratch/  no-git + no-tests
```

ASCII tables per `flow status` / `flow search` precedent (`cli.py:225-230`, `cli.py:640-659`).

**`--json` envelope (machine-readable)**:

```
{
  "version": "1",
  "root": "<path>",
  "generated_at": "<ISO8601 UTC>",          // Phase 3 envelope owns this
  "totals": { projects, dirty, no_git, no_tests, has_openspec, has_graphify, has_engram, needs_attention },
  "projects": [ ...verbatim from Phase 1... ],
  "needs_attention": [ { "name", "reasons": ["dirty","no-openspec"], "path" }, ... ]
}
```

Phase 3's `generated_at` is a **separate** envelope — does NOT mutate Phase 1 output (the byte-identical guard test in `test_cli_projects.py` stays unaffected).

## 5. Needs-attention rules

| # | Condition | Field parsed |
|---|-----------|--------------|
| R1 | `has_git==true and dirty==true` | uncommitted work |
| R2 | `has_git==false` | no version control |
| R3 | `test_commands==[]` | no detected tests |
| R4 | `has_openspec==false and stack in {Python,Go,Rust}` | SDD-adjacent stack missing spec |
| R5 | `has_graphify==false and stack in {Python,Go}` | **INFORMATIONAL ONLY in v1** (Phase 1 stub returns always false) |

Multiple reasons per project collapse into one entry. Rendering strings locked at sdd-spec time.

## 6. Approach (high-level)

- New `@main.group(name="workspace")` in `cli.py`; subcommand `status`. Mirror `metrics` group structure (`cli.py:1120-1302`) for `--json` + `json.dumps(..., ensure_ascii=False, indent=2)` precedent.
- Internal helper `_summarize_workspace_status(envelope) -> dict` returns `totals` + `needs_attention`. Pure function, no I/O, fully unit-testable.
- `flow workspace status` calls `_detect_project_markers` **directly via import** — single scan, zero subprocess overhead, deterministic ordering. (Avoids shell-out duplication of ~0.5s.)
- Extract `_resolve_projects_root(root: Path | None) -> Path` helper shared with `projects_ls` to avoid drift.

## 7. Test strategy

**File location**: NEW `tests/unit/test_cli_workspace_status.py`. Keeps Phase 1's 14 tests isolated; one-subcommand-one-file discipline.

**Reuse**: 9 `make_fake_*` helpers from `test_cli_projects.py:58-138` — moved to `tests/unit/_workspace_fixtures.py` (or kept imported). Lock at sdd-propose.

**New fixtures**: `empty_projects_root`, `all_clean_projects_root`, `mixed_needs_attention_projects_root`.

**10 unit tests**: (1) default text headers; (2) empty root; (3) DIRTY block R1; (4) NO GIT R2; (5) NO TESTS R3; (6) `--json` totals match; (7) `--json` reasons collapse; (8) byte-deterministic across calls (mirror AC8); (9) `version` first key; (10) invalid `--root` exits 2 + stderr.

Runner: `uv run pytest tests/unit/test_cli_workspace_status.py -v`. Strict TDD applies (`sdd-init/insyd` preflight).

## 8. Risks

| Risk | Mitigation |
|---|---|
| **Stale data** between JSON gen and status consume | Direct `_detect_project_markers` import — no staleness window. `generated_at` only in Phase 3 envelope. |
| **R1–R4 false positives/negatives** (WIP scratch project not "needs-attention"; Go library legitimately lacks openspec) | Document each rule in `--help`; surface `reasons:[]` in JSON so users can override. |
| **Phase 2/4/5 schema coupling** | Lock `version:"1"` in spec; CHANGELOG on additive fields only. |
| **Empty projects (degenerate)** | Test #2; render `(no projects to report)`; exit 0. |
| **`has_graphify` / `has_engram` stubs** (always false in Phase 1) | Render as informational coverage; do NOT count in `needs_attention`. Phase 2 un-stubs. |
| **R5 semantics shift** when Phase 2 un-stubs graphify | Document `disabled_in_v1` in spec; re-evaluate at Phase 2. |

## 9. Out-of-scope restated

Phase 2 (`flow where`), Phase 4 (hygiene), Phase 5 (dashboard), real Engram integration, Graphify parsing profundo, other projects under `<root>` (read-only targets only), `%APPDATA%`, re-implementing detection, new subcommands beyond `flow workspace status`.

## 10. Recommended approach (single sentence)

**Add `flow workspace status` as a NEW top-level group in `cli.py` reusing `_detect_project_markers` via direct import (no subprocess), rendering an ASCII-safe human report by default + a `version:"1"` JSON envelope with `generated_at` + `totals` + `projects` + `needs_attention` blocks under `--json`, with needs-attention = R1∪R2∪R3∪R4 (R5 informational only), and ship 10 new unit tests in a NEW `tests/unit/test_cli_workspace_status.py` reusing Phase 1's `make_fake_*` helpers** — well under 400-line review budget, no chained PR needed.

## Next step

`sdd-propose flow-workspace-status` — lock the proposal, R1–R4 rules, JSON envelope shape (`totals` + `projects` + `needs_attention`), test-file split (new file vs extension), and the `_resolve_projects_root` shared helper. Then spec → design → tasks → apply → verify → archive.
