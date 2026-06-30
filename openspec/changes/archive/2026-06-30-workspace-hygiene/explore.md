# Explore: workspace-hygiene — Phase 4 of workspace-intelligence

> Read-only exploration. No source files modified. The mutation counterpart to Phase 3 (`flow workspace status`); adds `flow workspace fix` + `flow workspace archive` to resolve the needs-attention rules surfaced by Phase 3.

## Goal

Add a **write-side surface** to flow-engineering that fixes the hygiene issues `flow workspace status` (Phase 3) reports: `git init` for projects flagged by R2, `git stash`/clean for R1, registry archive for projects the user wants to ignore, and snapshot/rollback support so every mutation is reversible. Stand on Phase 3's detection; introduce no new detection logic.

## Scope

### In

- `flow workspace fix <project> [--rules R1,R2,...] [--dry-run] [--backup] [--yes]` — applies Phase 3 needs-attention remediations to one project
- `flow workspace archive <project> [--reason "..."]` — marks a project archived in the flow registry; excluded from `flow projects ls` + `flow workspace status`
- `flow workspace archived` — lists archived projects (read-only mirror of the registry)
- `flow workspace restore <project> --from <timestamp>` — restores a project from a fix-backup
- Snapshot directory at `<root-or-platform-default>/.flow-engineering/backups/<project>/<UTC-timestamp>/`
- Registry file at `<root-or-platform-default>/.flow-engineering/registry.json` carrying the archive set
- Backing git subprocess seam `_run_git(...)` reusing `_git` precedent (`cli.py:3045`) — read-only on Phase 1/2/3 detection code
- New tests in `tests/unit/test_cli_workspace_hygiene.py` + extensions to `tests/unit/_workspace_fixtures.py`
- Pollution-protocol triple (`backup → mutate → verify`) borrowed from Engram #387, encoded as a single helper `_apply_hygiene_rule(project, rule, backup_dir)` that produces a verifiable proof line

### Out

- `flow workspace status` — byte-identical preserved (AC9 / Phase 3 contract)
- `flow projects ls` — byte-identical preserved (AC9 / Phase 1 contract)
- `flow where` (Phase 2) — untouched
- Phase 5 dashboard, real Engram/Graphify integration
- Writing inside any project other than the explicit `git init` + `.gitignore` + `git add . + git -c init.defaultBranch=main commit -m "initial"` triple for R2
- Renaming projects (different change)
- Bootstrap scripts for non-Python/Go/Rust stacks
- Auto-fixing R3 (no tests) — too template-dependent; documented as future-work, not Phase 4
- Auto-fixing R4 (no openspec) — too semantic to bootstrap without template engine; future-work
- `%APPDATA%` filesystem writes
- TUI / interactive prompts (Phase 5 territory)
- `flow projects backfill` / `flow projects alias` (REQ-24/27)

## Prior Art (workspace-intelligence arc)

| Phase | Change | Engram | Role for Phase 4 |
|---|---|---|---|
| Phase 1 | `flow-projects-ls--json` (v1 envelope, 11 fields) | #436–#444 | **Hard contract**: byte-identical `flow projects ls --json`. Phase 4 MUST NOT mutate the envelope. |
| Phase 2 | `flow-where-cross-project` (cross-project `flow where`) | #454–#462 | **Pattern**: ADDITIVE only; reuse `_run_search` directly, never duplicate module APIs. Phase 4's git subprocess calls follow `_git` (`cli.py:3045`) precedent, NOT raw `subprocess.run`. |
| Phase 3 | `flow-workspace-status` (5 rules R1–R5) | #445–#452 | **Hard contract**: 5 needs-attention rules are LOCKED. Phase 4 fixes those rules' outputs; must NOT alter R1–R5 logic. The `workspace_group` Click group at `cli.py:2982` is the registered home — fix/archive/restore attach as siblings of `status`. |
| Engram #387 | REQ-A-0 design pollution | #387 | **Process rule**: BACKUP → DELETE → VERIFY triple when reproductions touch user-real state. Phase 4 applies this to destructive ops (git init, archive, restore). |

**3 unflushed items from session #453** explicitly named by the user: `mockup`, `mockup-2-blog`, `flow-image-generator-main`. Live `flow projects ls --json` (this run) also surfaces 5 more `has_git:false` projects: `.atl`, `.opencode`, `Gestor-de-Contrase-as`, `openspec`, `sdd-init`. Phase 4 decisions for these 8 partition naturally: **3 user-identified** → real candidates for `git init`; **5 config/dotfiles** → archive candidates (mark ignored, leave filesystem untouched).

**AC9 byte-identical contract preservation** (Phase 3 verify report #460 + Phase 1 archive #444) is the binding guard. The unit test `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` remains green throughout Phase 4. Phase 4's envelope is **separate** (`version: "1.1"` candidate) — see Open Question §Q4.

## Operation Surface Analysis

Phase 3 surfaces 5 rules; Phase 4 decides which become actionable.

| Rule | Phase 4 action | Risk |
|---|---|---|
| **R1** dirty-committed | `flow workspace fix --rules R1` → `git stash push -u -m "flow-hygiene:<ts>"` + verify. Reversible via `git stash pop` (built-in). | **Medium** — `-u` for untracked; conflict on index corruption. Pollution-protocol wraps. |
| **R2** no-git | `flow workspace fix --rules R2` → `git init` + `.gitignore` + `git -c init.defaultBranch=main commit --allow-empty -m "initial"`. Creates a new repo; **irreversible** without `.git/` removal. | **High** — `git init` undoes uncleanly; future remote conflict. Requires `--yes` AND `--backup` for non-empty projects. |
| **R3** no-tests | **OUT OF SCOPE** — bootstrap a tests/ scaffold is template-dependent (pytest vs jest vs cargo test). | **N/A** — future change |
| **R4** no-openspec on SDD stack | **OUT OF SCOPE** — openspec/ skeleton is semantic (5 sub-dirs, AGENTS.md, gitignore), not just a directory. Wrong scaffold breaks SDD ceremony. | **N/A** — future change |
| **R5** no-graphify (informational) | No action. Phase 1 stub returns always false. | **None** |

**Cross-cutting operations**:

- **`flow workspace archive <project>`** — registry-only mutation; adds to `registry.archived[]`. `flow projects ls` + `flow workspace status` filter on membership (omitted, not errored). Reversible via `flow workspace restore`.
- **`flow workspace restore <project> --from <timestamp>`** — reads a backup directory and restores snapshotted files. For R1, prints the stash ref (`git stash list`) instead of auto-popping (decoupling from user intent).
- **Backup layout**: `<backup-root>/<project>/<UTC-ISO-timestamp>/`. Contains JSON manifest `{"project", "rule", "files_copied", "git_refs", "ts"}` plus verbatim copy of non-`.git/` files for R2. Compression is future-work.

## CLI Shape Options

Three candidate surfaces. Option A is recommended.

### Option A — Two-verb split (`fix` + `archive`) with shared `--dry-run`/`--backup`/`--yes`

```
flow workspace fix <project> [--rules R1,R2] [--dry-run] [--backup] [--yes]
flow workspace archive <project> [--reason "..."] [--yes]
flow workspace archived                             # list
flow workspace restore <project> --from <ts>
```

- Default behavior of `fix` = **dry-run** + **no backup** = `--dry-run` is on by default; `--apply` flips it OFF? Actually no — `--apply` is implicit; `--dry-run` is explicit dry-run. Default = no mutation unless `--yes`. Default = backup OFF unless `--backup`.
- Cross-rule semantics: omitting `--rules` defaults to "fix every applicable rule for this project"; explicit `--rules R2` is a focused single-rule fix.
- `archive` is its own verb because (1) registry mutation is orthogonal to filesystem mutation; (2) callers can archive without ever touching `.git/`; (3) verbs read more naturally in scripts.

### Option B — Single `fix` with `--archive` flag

```
flow workspace fix <project> [--rules R1,R2,archive] [--dry-run] [--backup] [--yes]
```

- One verb, flags enable behaviors. Pros: uniform surface. Cons: `--rules archive` overloads "rule" semantics (archive isn't a Phase 3 rule — it's a registry op); harder to compose in scripts.

### Option C — `clean` for filesystem + `archive` for registry

```
flow workspace clean <project> [--rules R1,R2] [--dry-run] [--backup] [--yes]
flow workspace archive <project> [--yes]
flow workspace restore <project> --from <ts>
```

- `clean` reads as filesystem-only, `archive` reads as registry-only. Closer to mental model. Cons: Phase 3 contract calls R1+R2 "needs attention" — terminology drift (`clean` vs `fix`) requires user documentation.

### Comparison

| Aspect | A (recommended) | B (one-verb) | C (`clean`/`archive`) |
|---|---|---|---|
| Read-cognitive-load | Low — `fix <project>` is the obvious command | Medium — flags encode mode | Low — verb encodes mode |
| Scriptability | High — 4 distinct verbs = 4 stable CLI handles | Medium — `flow workspace fix --rules archive` is awkward | High — same as A |
| Phase 3 rule parity | Perfect — `--rules R1,R2,R3,R4` mirrors R1–R4 | Perfect | Imperfect — `R3/R4` aren't actionable in Phase 4 |
| Pollution vector | Worst case: 4 verbs × N projects = high blast radius | Slightly lower (single verb) | Same as A |
| Test count (LOC est.) | ~150 prod + ~280 test = **~430 LOC** | ~120 prod + ~260 test = ~380 LOC | ~130 prod + ~260 test = ~390 LOC |
| Review budget (400) | **Right at the edge → chained PR** | Slightly over → chained PR | Slightly over → chained PR |

**Verdict on shape**: Option A. Best readability and explicit-script handle. Cost is an inevitable `size:exception` or a 2-PR chain (PR1: prod surface + fixtures; PR2: tests + verification gates). The existing preflight says `chain_strategy: ask-always` — we will surface "chained PRs" to the user at sdd-tasks time.

## Safety Guardrails (pollution protocol integration)

Phase 4 WRITES. Without guardrails it can destroy 8 user projects in one command. The following are non-negotiable defaults:

1. **`--dry-run` is the default behavior**, returning a structured plan without mutating. Production exit code 0 on dry-run; exit code 0 on successful mutation; exit code 1 on user-decline (`--yes` missing); exit code 2 on rule-failure (e.g., `git stash` conflict).
2. **`--yes` is required for any mutation**. No `--yes` → no write; emits plan only. (Mouse-driven interactives like `click.confirm()` are out — the orchestrator prompt explicitly excludes TUI/interactive prompts from Phase 4.)
3. **`--backup` is OPT-IN for R1, RECOMMENDED for R2.** Without `--backup`, R2 refuses to run on projects containing files (defensive guard: if a project is non-empty AND `has_git` is false, R2 defaults to **REFUSE** rather than mutate). Output: `refusing R2 on non-empty project '<name>' without --backup; pass --backup to snapshot existing files`.
4. **Pollution protocol triple (Engram #387)**: every mutation runs through a single helper:

```python
def _apply_hygiene_rule(project_path, rule, backup_dir):
    # Step 1 — backup (if --backup)
    snapshot = _snapshot_files(project_path, backup_dir) if backup_dir else None
    # Step 2 — mutate
    result = _run_rule(project_path, rule)
    # Step 3 — verify
    if not _verify_postcondition(project_path, rule):
        if snapshot: _restore_from_snapshot(snapshot)
        raise SystemExit(2)
    return result
```

5. **All subprocess calls behind the existing `_git(...)` seam** (`cli.py:3045`). No direct `subprocess.run` from new code. Unit tests `monkeypatch.setattr(cli, "_git", fake_git)` per Phase 3 pattern.
6. **Registry writes are atomic** (`os.replace` on temp file) — see `project_aliases.py` precedent. Concurrent `flow workspace archive` against the same project is last-write-wins WITH a JSON manifest writing the writer's PID + ts.
7. **AC9 byte-identical**: `flow workspace fix --dry-run <project>` MUST NOT modify any file under the project. A dedicated test `test_fix_dry_run_does_not_mutate_filesystem` verifies file mtimes unchanged after dry-run.
8. **Test pollution guard**: NO test writes to `C:\dev\proyects\**` — only `tmp_path`. The existing `_workspace_fixtures.py` pattern enforces this; Phase 4 inherits.

## Approach Candidates

### Approach A — Minimal hygiene: R2 + archive + restore (RECOMMENDED)

- **Operations**: R2 (`git init`) for `has_git:false`; archive as first-class verb for ignored projects; restore for backup rollback.
- **Skipped**: R1 (deferred — `git stash` is well-understood by users who can do it themselves); R3, R4 (template-dependent).
- **Safety**: dry-run default + `--yes` for write + `--backup` required for non-empty projects + pollution-protocol triple.
- **LOC**: 110 prod + 230 test = ~340 LOC (under 400).
- **Tests**: +18 in NEW `test_cli_workspace_hygiene.py`.
- **Risk**: Low. R2 = git init (well-understood); archive = registry-only.
- **Why recommended**: Directly addresses #453's 3 unflushed items. Single PR, no size:exception. Provides archive escape hatch for the 5 other `has_git:false` projects.

### Approach B — Full hygiene suite: A + R1 (cautious expansion)

- **Operations**: A + R1 (`git stash push -u -m "flow-hygiene:<ts>"`).
- **Skipped**: R3, R4.
- **Safety**: same as A + R1-specific override (user responsible for `git stash pop`; we don't auto-pop).
- **LOC**: 150 prod + 290 test = ~440 LOC.
- **Tests**: +24.
- **Risk**: Medium. `git stash -u` on dirty projects with large untracked files can be slow; on WSL/cygwin paths conflicts with EOL conventions are possible.
- **Why not yet**: 440 LOC crosses 400-line budget → size:exception or chained PR. Best done as PR-2 follow-up after Approach A proves the registry layer works.

### Approach C — Archive-first (registry only)

- **Operations**: archive verb + restore; NO filesystem mutation.
- **Skipped**: R1, R2.
- **Safety**: maximum — no filesystem writes. Registry atomicity via `os.replace` precedent.
- **LOC**: 80 prod + 150 test = ~230 LOC.
- **Tests**: +12.
- **Risk**: Very low. But doesn't address "projects without git" — only "projects I want to ignore".
- **Why not standalone**: Phase 4's `fix` is a hygiene surface; without `git init` users still face R2. Archive-only is the registry half; full Phase 4 = Approach A.

### Selection matrix

| Approach | LOC | Test count | Budget (400) | Risk | Solves #453's 3 items? | Recommended |
|---|---|---|---|---|---|---|
| **A** (R2 + archive + restore) | 340 | +18 | **Under** | Low | **Yes** (R2 for users who want git; archive for those who don't) | **Yes** |
| **B** (A + R1) | 440 | +24 | Over (10%) | Medium | Yes (R2 covers; R1 doesn't apply to #453's 3) | Not yet |
| **C** (archive only) | 230 | +12 | Under | Very low | Partial (archive solves "ignore them"; doesn't solve "give them git") | No |

**Verdict**: Approach A. Solves the user's pending decisions, stays under budget, defers safely.

## Tech Debt Interactions

| # | Pre-existing finding | Source | Phase 4 interaction |
|---|---|---|---|
| 1 | `if __name__ == '__main__': main()` block fires before `workspace_group` registration at `cli.py:2665` | #453 / #452 | Phase 4 registers `fix`, `archive`, `archived`, `restore` AFTER line 2665 (consistent with `workspace_status` at line 2987). Bug NOT introduced by Phase 4 and NOT fixed here — out of scope (separate change). |
| 2 | 4 pre-existing test failures | #453 | Phase 4 baseline at HEAD `27111ed`: `uv run --frozen pytest tests/ -q --collect-only` reports `1444 tests collected`. Phase 4 will (a) NOT regress any of those tests and (b) NOT fix the 4 failing ones — out of scope. Verify gates confirm green/yellow parity with main. |
| 3 | Latent helper extraction opportunity | #453 | Phase 4 may INTRODUCE a candidate (`_apply_hygiene_rule`) that future cleanup passes can extract into `src/flow_engineering/hygiene.py`. We do NOT preempt the extraction — it lives in `cli.py` adjacent to the `workspace_*` commands. |
| 4 | `_detect_project_markers` is Phase 1+2+3 source-of-truth | #444, #452 | Phase 4 READS the same data via direct in-process import (mirrors Phase 3's `_summarize_workspace_status`). Phase 4 does NOT modify `_detect_project_markers`. |
| 5 | `_git` subprocess seam | `cli.py:3045` | Phase 4 REUSES `_git` for git stash + git init + git commit. NO new `subprocess.run` calls. |
| 6 | `flow projects` already filters for `flow-projects-ls--json` | #444 | Phase 4's `archive` excludes projects from `flow projects ls`. Modifying Phase 1's envelope would violate AC9. Two options: (i) Phase 4 introduces its OWN filtered view via `_filter_archived(projects)` consumed by Phase 3's renderer (no Phase 1 changes); (ii) raise a future ticket. **Recommended: (i)** — renders cleanly without mutating the contract. |

## Open Questions

1. **Should `flow workspace fix` require explicit `--yes` for destructive ops, or should `git stash` (R1) be excluded from the destructive set?** R1 is reversible via `git stash pop`; R2 (`git init`) is partially irreversible. R1 could be `--yes`-free; R2 must require `--yes`. Affects Approach A defaults.
2. **Phase 4 vs the v1 JSON envelope — own v1.1 or extend Phase 3's v1?** Phase 3 owns its v1 envelope. Options: (a) extend Phase 3's envelope (mutates Phase 3 contract — rejected), (b) own `flow workspace fix --json` v1.1 with `{version, planned_actions}`, (c) text-only. Recommend (b) for fix; v1.0 for archive (registry-only).
3. **Archive as a separate command or a flag on `fix`?** Approach A uses separate verbs (cleaner scripts); B/C collapse. Orchestrator prompt favors A; flag for user at sdd-propose.
4. **Where do backups live?** Options: `<root>/.flow-engineering/backups/`, `~/.flow-engineering/backups/`, or `<project>/.flow-backup-<ts>/`. Recommend `~/.flow-engineering/backups/<project>/<ts>/` — out of project tree, survives workspace reorganization. Parallel to `~/.engram/`.
5. **Does Phase 4 mutate the workspace registry cache, or only on-disk state?** Phase 4 owns `<backup-root>/registry.json`. It does NOT mutate any Phase 1/2/3 cache. Future PR may add registry envelope field once Phase 1's contract permits.
6. **Per-project vs batch interaction — interactive prompts in CLI?** Strict NO-interactive (preflight; Phase 5). All batches: `--dry-run` → user reviews → re-invoke with `--yes`. Tested.
7. **Does `archive` block both `flow workspace status` AND `flow projects ls`?** Both. They share the registry. Phase 1's byte-identical guard re-runs at every Phase 4 verify gate.
8. **`git init` initial commit message — empty commit or first-snapshot commit?** Phase 4 default = `git -c init.defaultBranch=main commit --allow-empty -m "initial"`. User can override with `--initial-message`. Empty is friendlier for users who want a real first commit themselves.
9. **What if `--backup` requested but backup destination is unwritable?** Surface clean error (exit code 2) BEFORE any mutation. Pollution-protocol triple enforces "backup first, mutate second" — backup helper aborts before reaching step 2.
10. **Should `flow workspace restore` undo R1's `git stash push` automatically, or print the stash ref?** Recommend: print the stash ref. Auto-popping couples to user intent. Document in spec.
11. **`registry.json` schema versioning?** Phase 4 emits `version: "1"` for the registry itself (orthogonal to v1 envelope). Future migrations back-compatible via read-registry-version seam.
12. **Does Phase 4 cross the 400-line review budget?** Approach A = 340 LOC, **under by 15%** (margin). Approach B = 440, **over by 10%**. If proposal picks B, chained PR required. Decision belongs at sdd-tasks time per preflight `chain_strategy: ask-always`.

## Forecast

| Field | Value |
|---|---|
| Estimated changed lines (approach A) | ~340 LOC (110 prod + 230 test) |
| 400-line budget risk | **Low** (15% margin under) |
| Chained PRs recommended | No (single PR viable) |
| Suggested split | 1 PR, 2 commits (prod + tests) |
| Delivery strategy | `ask-always` (preflight default) — surface "single PR vs chained" to user at sdd-tasks |
| Chain strategy | stacked-to-main only if user picks chained |
| New tests | +18 in `tests/unit/test_cli_workspace_hygiene.py` (NEW) |
| Test baseline | 1444 collect-only at HEAD `27111ed` |
| Post-apply | 1462–1480 depending on refactor opportunities |
| Phase contracts impacted | AC9 (Phase 1 + Phase 3 byte-identical) — preserved by read-only protocol |
| Files modified | `src/flow_engineering/cli.py` (+110), `tests/unit/test_cli_workspace_hygiene.py` (NEW +230), `tests/unit/_workspace_fixtures.py` (+~10 helper) |
| Files NOT modified | `_detect_project_markers`, `_resolve_projects_root`, `where.py`, `project_aliases.py`, all Phase 1/2/3 test files |
| Wall-time estimate (full cycle) | explore (this) = 25 min · propose = 30 min · spec = 45 min · design = 60 min · tasks = 30 min · apply (TDD) = 90 min · verify = 20 min · archive = 15 min. **≈ 4.5–6 hours** of focused work across one or two sittings |

## Verdict (recommended approach + rationale)

**Recommended**: Approach A — Minimal hygiene with the Option A CLI shape (two verbs: `fix` + `archive`, plus `archived` + `restore`).

**Rationale**:

1. **Solves the user's stated pending work** (session #453): 3 unflushed projects get either `git init` (R2) or `archive` — both reversible.
2. **Stays under 400-line review budget** with 15% margin — single PR, no chained slicing needed unless the user pushes for `git stash` (R1) inclusion.
3. **Default safety posture**: `--dry-run` is the default behavior; `--yes` required for any mutation; `--backup` enforced for R2 on non-empty projects. Pollution-protocol triple (`backup → mutate → verify`) wraps every rule.
4. **AC9 byte-identical preserved**: read-only on Phase 1/2/3 code; Phase 4's own envelope is `version: "1.1"` (separate from Phase 3's `v1`); dry-run explicitly tested for non-mutation.
5. **Reuses existing seams**: `_git` (`cli.py:3045`), `_detect_project_markers`, `_resolve_projects_root`, `project_aliases.py` atomic-write precedent, `where._run_search` per-directory pattern. No new top-level imports beyond `datetime`, `shutil`, `zipfile` (compress is optional future).
6. **Defers safely**: R3/R4 (test bootstrap, openspec bootstrap) are template-dependent and one-shot expensive — out of scope for v1. Future change can ship them as a single follow-up.
7. **Registry-on-disk**: `<backup-root>/registry.json` parallels `~/.engram/` patterns; cross-platform via `Path.home() / ".flow-engineering"`.

**Verdict on open questions 1, 3, 4, 8, 10**: the recommended defaults are explicit in the verdict above (--yes for write; separate `archive` verb; backups in `~/.flow-engineering/backups/`; `git init` initial = empty commit; `restore` prints stash ref). The remaining open questions (2, 5, 6, 7, 9, 11, 12) belong at sdd-spec / sdd-design time and are flagged for the next phase.

## Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | `git init` on a project with non-empty directory silently creates a repo; if user later adds a remote with non-trivial history, push is rejected | **High** | R2 refuses non-empty projects without `--backup`; backup is mandatory for non-empty. Documented in spec + tested. |
| 2 | `_apply_hygiene_rule` swallows exceptions on verify and aborts with exit 2 — could leave partial state on edge cases | **Medium** | Pollution-protocol: verify-before-commit semantics. Backup helper runs FIRST; mutation step runs in try/except; on any exception, restore from snapshot + exit 2. Tested with simulated failure (monkeypatch the mutation to raise). |
| 3 | `registry.json` corruption (mid-write crash) leaves archive set inconsistent across `flow projects ls` + `flow workspace status` | **Medium** | Atomic write via `os.replace` on temp file. `read_registry()` rejects malformed JSON with a clean error + recovery hint. Tested. |
| 4 | `archive` mutation, if applied to a project the user genuinely uses, silently hides it from `flow projects ls`; user might not notice until a workflow breaks | **Medium** | `archive` requires `--yes`; `--reason "..."` is recommended via env variable convention. `flow workspace archived` lists everything archived — prominently documented in help text. |
| 5 | `--backup` requires `<backup-root>` to be writable; if filesystem is full, mutation proceeds without backup and user discovers this only at the next restore attempt | **Low** | Backup helper MUST succeed before mutation; if it fails, exit 2 with no mutation. Tested with read-only backup dir. |

## Affected Areas

- `src/flow_engineering/cli.py` — register `fix`, `archive`, `archived`, `restore` subcommands under existing `@main.group(name="workspace")` at `cli.py:2982`. Add helpers `_apply_hygiene_rule`, `_run_registry`, `_snapshot_for_backup`, `_read_registry`, `_write_registry`, `_filter_archived`. Reuse `_git` seam at `cli.py:3045`. Reuse `_detect_project_markers` direct import (no subprocess). Estimated: +110 LOC, -0 LOC.
- `tests/unit/test_cli_workspace_hygiene.py` — NEW file with ~18 tests: dry-run non-mutation, `--yes` gating, backup persistence, R2 success/refusal paths, archive add/list/restore, registry atomicity, AC9 byte-identical preserved.
- `tests/unit/_workspace_fixtures.py` — extend with `make_fake_unmanaged_project` (no-git, non-empty), `make_fake_managed_project` (no-git, empty), `make_fake_dirty_project` (git + dirty). Estimated: +~10 LOC.

## Ready for Proposal

**Yes** — proceed to `sdd-propose workspace-hygiene`. Lock the approach (Approach A + Option A CLI shape), the 4 verb surface (`fix`, `archive`, `archived`, `restore`), the pollution-protocol triple as a single helper, the registry schema, and the backup layout at `~/.flow-engineering/backups/<project>/<UTC-ISO-timestamp>/`. Then spec → design → tasks → apply → verify → archive.
