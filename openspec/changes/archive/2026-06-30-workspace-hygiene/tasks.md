# Tasks: workspace-hygiene

> **Change**: `workspace-hygiene` — Phase 4 of the workspace-intelligence arc (write-side MVP).
> **Builds on**: `openspec/changes/workspace-hygiene/design.md` (authoritative source; 481 lines).
> **Spec**: `openspec/changes/workspace-hygiene/specs/workspace-hygiene/spec.md` (12 REQs + 13 AC).
> **Forecast**: ~335 production LOC + 18 unit tests + 8 CLI tests + 16 BDD scenarios + AC9 guard stays green.
> **Strict TDD mode**: ON — every task is a self-contained RED → GREEN → REFACTOR cycle.
> **Branch**: `codex/flow-workspace-hygiene` (off `main` at HEAD `cb82274`; working tree clean except for Phase 4 artifacts).
> **AC9 safety net**: `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` MUST stay green throughout.

---

## 1. Review Workload Forecast (MANDATORY per orchestrator protocol)

| Field | Value |
|-------|-------|
| `forecast_loc` (total changed lines, prod + tests) | **~835** |
| `forecast_prod_loc` (production only) | **~335** |
| `forecast_test_loc` (tests only, all 3 layers) | **~500** |
| `chained_pr_recommendation` | **yes** |
| `chained_pr_rationale` | Total ~835 LOC exceeds the 400-line review budget by ~2x. PR1 ships the verified core (registry + orchestrator + AC9 guard) so reviewers can audit the safety net in isolation; PR2 wires the CLI surface and proves end-to-end BDD coverage. Stacked to main. |
| `400-line budget risk` | **high** |
| `size_exception_required` | **no** (chained PRs is the safer call) |
| `size_exception_rationale` | n/a — chained PRs splits the work into ≤460 LOC slices, each under 500 LOC, each self-contained. |
| `decision_needed_before_apply` | **yes** (per preflight `delivery_strategy: ask-always`) |
| `decision_question` | "El forecast de Phase 4 es ~335 prod + ~500 test = ~835 LOC total, claramente sobre el budget de 400. ¿Querés (A) single PR con `size:exception` siguiendo tu patrón de Phase 1/3, (B) 2 chained PRs (PR1: foundations + orchestrator + AC9 guard; PR2: CLI + BDD), o (C) 3 chained PRs más granulares?" |

**Plain-text guard lines** (literal match for downstream guards):

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested work units (chained PR split)

| Unit | Goal | Likely PR | Forecast LOC | Notes |
|------|------|-----------|--------------|-------|
| WU-1 | Foundations + orchestrator | PR 1 | ~440 (250 prod + 190 test) | `registry.py` + `workspace_hygiene.py` + 18 unit tests + AC9 verification. Self-contained; AC9 guard verified before CLI wiring. |
| WU-2 | CLI surface + BDD | PR 2 | ~395 (85 prod + 310 test) | 4 Click commands on `workspace_group` + 8 CLI tests + 16 BDD scenarios + step glue. Wires the verified core to the user-facing surface. |

Each PR must land independently: tests pass, AC9 guard green, lint clean, type-check clean.

---

## 2. Task Summary Table

| T# | Title | Files affected | TDD cycle | Prod LOC | Tests added |
|----|-------|----------------|-----------|----------|-------------|
| T-1 | `registry.py` — pydantic v2 models + `RegistryError` + path helper | `src/flow_engineering/registry.py` (NEW) + `tests/unit/test_registry.py` (NEW) | RED → GREEN → REFACTOR | ~50 | 2 unit |
| T-2 | `registry.py` — `load_registry()` + `save_registry_atomic()` | same files | RED → GREEN → REFACTOR | ~40 | 3 unit |
| T-3 | `workspace_hygiene.py` — `HygieneResult` + exceptions + `_now_iso_utc()` | `src/flow_engineering/workspace_hygiene.py` (NEW) + `tests/unit/test_workspace_hygiene.py` (NEW) | RED → GREEN → REFACTOR | ~25 | 1 unit |
| T-4 | `workspace_hygiene.py` — `_is_empty_project()` with hidden-file exclusion | same files | RED → GREEN → REFACTOR | ~15 | 3 unit |
| T-5 | `workspace_hygiene.py` — `_snapshot_project()` + manifest | same files | RED → GREEN → REFACTOR | ~30 | 2 unit |
| T-6 | `workspace_hygiene.py` — `_verify_post_mutation()` + `_restore_from_snapshot()` | same files | RED → GREEN → REFACTOR | ~25 | 2 unit |
| T-7 | `workspace_hygiene.py` — `_apply_hygiene_rule()` orchestrator | same files | RED → GREEN → REFACTOR | ~40 | 3 unit |
| T-8 | `workspace_hygiene.py` — `_archive_project()` + `_restore_archived_project()` | same files | RED → GREEN → REFACTOR | ~25 | 2 unit |
| T-9 | `cli.py` — `_load_registry_for_cli()` + `workspace_fix_cmd` | `src/flow_engineering/cli.py` (MODIFIED) + `tests/unit/test_cli_workspace_hygiene.py` (NEW) | RED → GREEN → REFACTOR | ~30 | 2 CLI |
| T-10 | `cli.py` — `workspace_archive_cmd` | same files | RED → GREEN → REFACTOR | ~15 | 2 CLI |
| T-11 | `cli.py` — `workspace_archived_cmd` (text table) | same files | RED → GREEN → REFACTOR | ~25 | 2 CLI |
| T-12 | `cli.py` — `workspace_restore_cmd` | same files | RED → GREEN → REFACTOR | ~15 | 2 CLI |
| T-13 | BDD step glue + run BDD suite | `tests/bdd/test_workspace_hygiene_steps.py` (NEW) + `tests/bdd/workspace_hygiene.feature` (already exists) | RED → GREEN → REFACTOR | 0 | 16 BDD |
| T-14 | AC9 byte-identical verification | `tests/unit/test_cli_projects.py` (read-only) | Verification only | 0 | 0 |
| **Total** | | | | **~335** | **18 unit + 8 CLI + 16 BDD = 42 test items** |

---

## 3. Task Definitions

> Each task is a self-contained RED → GREEN → REFACTOR cycle. Apply agent MUST execute them in dependency order. All pytest invocations use `uv run --frozen pytest` (per preflight).

---

### T-1 — `registry.py`: pydantic v2 models + `RegistryError` + path helper

| Field | Value |
|-------|-------|
| **Task ID** | T-1 |
| **Title** | Implement `registry.py` pydantic models + atomic-write foundation |
| **Goal** | Establish the pydantic v2 schema (`Registry`, `ProjectEntry`, `ArchivedEntry`), the `RegistryError` exception, the `DEFAULT_REGISTRY_PATH` constant, and the `registry_path()` helper that resolves `~/.flow-engineering/registry.json` via `Path.home()`. No load/save logic in this task — that comes in T-2. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_registry.py::test_registry_model_accepts_minimal_payload -xvs` (test imports `Registry`, `ProjectEntry`, `ArchivedEntry`, `RegistryError`, `DEFAULT_REGISTRY_PATH`, `registry_path`; constructs `Registry(version=1, projects=[], archived=[])`; asserts `r.version == 1`, `r.projects == []`, `r.archived == []`; asserts `RegistryError` is subclass of `RuntimeError`; asserts `registry_path() == Path.home() / ".flow-engineering" / "registry.json"` under a monkeypatched `Path.home` returning `tmp_path`). |
| **GREEN — minimal implementation** | Create `src/flow_engineering/registry.py` with: `class ProjectEntry(BaseModel)` (model_config `extra="forbid"`, `frozen=False`; fields `name: str`, `path: Path`, `has_git: bool`, `has_openspec: bool`, `has_tests: bool`, `has_graphify: bool`, `last_status_check: str`); `class ArchivedEntry(BaseModel)` (same config; fields `name: str`, `path: Path`, `archived_at: str`, `reason: str`); `class Registry(BaseModel)` (same config; `version: Literal[1] = 1`, `projects: list[ProjectEntry] = Field(default_factory=list)`, `archived: list[ArchivedEntry] = Field(default_factory=list)`); `class RegistryError(RuntimeError)` with `user_message: str`; `DEFAULT_REGISTRY_PATH: Path = Path.home() / ".flow-engineering" / "registry.json"` (computed at import-time — see Risk Notes); `def registry_path() -> Path: return Path.home() / ".flow-engineering" / "registry.json"`. |
| **REFACTOR — cleanup** | Add `__all__` to lock the public surface; add module docstring citing the `project_aliases.py:164` precedent; add type annotations on every signature; verify `extra="forbid"` rejects unknown fields in unit test #2. |
| **Files affected** | `src/flow_engineering/registry.py` (NEW, ~50 LOC); `tests/unit/test_registry.py` (NEW, ~25 LOC for 2 tests). |
| **Pre-requisites** | none (this is the foundation task). |
| **Acceptance criteria** | REQ-HYGIENE-REGISTRY-V1 (partial — schema only; atomic write lands in T-2). |
| **Risk notes** | `DEFAULT_REGISTRY_PATH` is evaluated at module import time. If `Path.home()` differs across test contexts, the constant is stale. Mitigated by `registry_path()` accessor (always re-evaluates) — use the accessor in T-2's `load_registry`/`save_registry_atomic`. Do NOT cache the constant. |

---

### T-2 — `registry.py`: `load_registry()` + `save_registry_atomic()`

| Field | Value |
|-------|-------|
| **Task ID** | T-2 |
| **Title** | Implement atomic load/save with crash-recovery contract |
| **Goal** | Round-trip a `Registry` model through `~/.flow-engineering/registry.json` atomically. Missing file → empty registry. Malformed JSON → `RegistryError`. Crash during `os.replace` → prior file intact. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_registry.py::test_load_registry_missing_file_returns_empty -xvs` (test deletes the registry file under a tmp_path monkeypatched `Path.home`, calls `load_registry(path=...)`, asserts `result.version == 1` and both lists empty). Then `test_save_registry_atomic_round_trip` (write a registry, read it back, assert field-by-field equality). Then `test_save_registry_atomic_no_partial_on_crash` (monkeypatch `os.replace` to raise `OSError`; assert the prior `registry.json` content is unchanged and the temp file is cleaned up). |
| **GREEN — minimal implementation** | Add `def load_registry(*, path: Path | None = None) -> Registry:` that calls `registry_path()` if `path is None`; if `path.exists()` → `json.loads(path.read_text(encoding="utf-8"))` and `Registry.model_validate(parsed)` (raises `RegistryError` on `ValidationError` or `json.JSONDecodeError`); if `path.exists()` is False → return `Registry()`. Add `def save_registry_atomic(registry: Registry, *, path: Path | None = None) -> None:` that: (1) resolves `target` via `registry_path()`; (2) `target.parent.mkdir(parents=True, exist_ok=True)`; (3) `serialized = json.dumps(registry.model_dump(mode="json"), ensure_ascii=False, indent=2)`; (4) `fd, tmp_path_str = tempfile.mkstemp(prefix=".registry-", suffix=".json.tmp", dir=str(target.parent))`; (5) in a try-block, `os.fdopen(fd, "w", encoding="utf-8")` → write → flush → `os.fsync`; (6) `Path(tmp_path_str).replace(target)`; (7) in except, suppress-and-unlink the temp file and re-raise. |
| **REFACTOR — cleanup** | Extract `_serialized_payload(registry: Registry) -> str` helper for testability; ensure `Path` fields serialize as POSIX strings on Windows (pydantic v2 `model_dump(mode="json")` handles this); add `try/except (OSError, ValidationError, json.JSONDecodeError)` → raise `RegistryError(user_message=...)` with a clear message. |
| **Files affected** | `src/flow_engineering/registry.py` (T-1 + ~40 LOC); `tests/unit/test_registry.py` (+~50 LOC for 3 tests, total 5 tests in the file). |
| **Pre-requisites** | T-1 (models must exist before load/save can reference them). |
| **Acceptance criteria** | REQ-HYGIENE-REGISTRY-V1 (full — schema + atomic write + missing-file + malformed-JSON handling). |
| **Risk notes** | `tempfile.mkstemp` is atomic on POSIX + Windows when both paths are on the same filesystem; we force `dir=str(target.parent)` to guarantee that. Do NOT use `tempfile.NamedTemporaryFile` (closes the fd too early on Windows — see `project_aliases.py:180-184` precedent). `os.fsync` is REQUIRED before `os.replace` to ensure durability on power-loss scenarios. |

---

### T-3 — `workspace_hygiene.py`: `HygieneResult` + exception hierarchy + `_now_iso_utc()`

| Field | Value |
|-------|-------|
| **Task ID** | T-3 |
| **Title** | Implement result dataclass + exception hierarchy + timestamp helper |
| **Goal** | Establish the public type surface that all orchestrator helpers return / raise. No mutation logic in this task — helpers land in T-4..T-8. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_hygiene_result_frozen_dataclass -xvs` (construct `HygieneResult(rule_id="R2_GIT_INIT", project="mockup", action_taken="git init", dry_run=False, backup_path=None, success=True, error=None)`; assert frozen: `result.rule_id = "X"` raises `dataclasses.FrozenInstanceError`; assert `MutationGateError("--yes required")` is a `PermissionError` subclass; assert `EmptyProjectError(...)` is a `ValueError` subclass; assert `_now_iso_utc()` returns a string matching `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`). |
| **GREEN — minimal implementation** | Create `src/flow_engineering/workspace_hygiene.py` with: `@dataclass(frozen=True) class HygieneResult` (fields: `rule_id: str`, `project: str`, `action_taken: str`, `dry_run: bool`, `backup_path: Path | None`, `success: bool`, `error: str | None`); `class MutationGateError(PermissionError)` with `user_message: str`; `class EmptyProjectError(ValueError)` with `user_message: str`, `project: Path`, `non_empty_files: list[str]`; `HIDDEN_SYSTEM_FILES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})`; `def _now_iso_utc() -> str: return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`. |
| **REFACTOR — cleanup** | Add module docstring citing `_apply_hygiene_rule` as the central entrypoint and the pollution-protocol triple contract; add `__all__`; type-annotate every signature. |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (NEW, ~25 LOC); `tests/unit/test_workspace_hygiene.py` (NEW, ~15 LOC for 1 test). |
| **Pre-requisites** | none. |
| **Acceptance criteria** | REQ-HYGIENE-FIX-SURFACE (partial — type surface); REQ-HYGIENE-DRY-RUN-DEFAULT (partial — gate exception type). |
| **Risk notes** | `_now_iso_utc` MUST end in `Z` (UTC) per the spec's backup directory naming convention. Use `datetime.now(timezone.utc)` not `datetime.utcnow()` (the latter is deprecated in 3.12). Frozen dataclass + pydantic `BaseModel` do NOT play well together — keep `HygieneResult` as a plain frozen dataclass; the persistent state goes through `Registry` (pydantic). |

---

### T-4 — `workspace_hygiene.py`: `_is_empty_project()` with hidden-file exclusion

| Field | Value |
|-------|-------|
| **Task ID** | T-4 |
| **Title** | Implement empty-project detection per REQ-HYGIENE-BACKUP-GATE-NONEMPTY |
| **Goal** | Return `True` iff the project has no user-visible content. `.DS_Store`, `Thumbs.db`, `desktop.ini` are OS junk and excluded. `.gitignore`, `.env`, `.vscode/` are user content and count. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_is_empty_project_excludes_os_junk -xvs` (3 parametrized cases via `@pytest.mark.parametrize`: (a) truly empty dir → `True`; (b) dir containing only `.DS_Store`, `Thumbs.db`, `desktop.ini` → `True`; (c) dir containing `.gitignore` and `README.md` → `False`). |
| **GREEN — minimal implementation** | Add `def _is_empty_project(project_path: Path) -> bool:` that returns `not any(not (p.name in HIDDEN_SYSTEM_FILES) for p in project_path.iterdir())` — True iff all entries are either absent or in `HIDDEN_SYSTEM_FILES`. Do NOT recurse — first-level entries only. |
| **REFACTOR — cleanup** | Add a docstring explaining why `HIDDEN_SYSTEM_FILES` is limited to those 3 (design D-table row 6); add a test case for "dir with `.vscode/` subdir counts as non-empty" (1-line addition to the parametrize). |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (T-3 + ~15 LOC); `tests/unit/test_workspace_hygiene.py` (+~30 LOC for 3 parametrized tests, total 4 tests). |
| **Pre-requisites** | T-3 (uses `HIDDEN_SYSTEM_FILES`). |
| **Acceptance criteria** | REQ-HYGIENE-BACKUP-GATE-NONEMPTY (full — empty detection is the gate's input). |
| **Risk notes** | Do NOT use `pathlib.Path.glob("*")` — that excludes dotfiles by default. Use `iterdir()` and check `p.name` against the exclusion set. Do NOT recurse — empty-project means the user has not started work yet, and a subdirectory is itself user content. |

---

### T-5 — `workspace_hygiene.py`: `_snapshot_project()` with `manifest.json`

| Field | Value |
|-------|-------|
| **Task ID** | T-5 |
| **Title** | Implement pre-mutation snapshot with manifest |
| **Goal** | Copy the project's pre-mutation files (excluding `.git/`) to `~/.flow-engineering/backups/<project_name>/<UTC-ISO-ts>/` and write a `manifest.json` with the spec's required fields. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_snapshot_project_creates_manifest_and_files -xvs` (build a tmp project with `README.md` + `.gitignore`; call `_snapshot_project(project_path, backup_root)`; assert the snapshot dir exists; assert `manifest.json` parses with the 7 spec fields present: `project_name`, `project_path`, `rule_id`, `git_status_pre`, `files_count`, `bytes_total`, `created_at`; assert `README.md` and `.gitignore` exist in the snapshot dir; assert `.git/` is NOT in the snapshot). |
| **GREEN — minimal implementation** | Add `def _snapshot_project(project_path: Path, backup_root: Path, *, rule_id: str = "R2") -> Path:` that: (1) creates `backup_root / project_path.name / _now_iso_utc()` (parents=True); (2) writes `manifest.json` with `{project_name, project_path, rule_id, git_status_pre=(project_path / ".git").exists(), files_count=N, bytes_total=B, created_at=_now_iso_utc()}`; (3) `shutil.copytree(project_path, snapshot_dir / "files", ignore=shutil.ignore_patterns(".git"), dirs_exist_ok=False)`; (4) returns `snapshot_dir`. |
| **REFACTOR — cleanup** | Extract `_compute_snapshot_stats(src: Path) -> tuple[int, int]` for testability (returns `(files_count, bytes_total)` walking `src` excluding `.git/`); add a docstring linking to design.md §Data Flow (pollution-protocol triple). |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (T-4 + ~30 LOC); `tests/unit/test_workspace_hygiene.py` (+~25 LOC for 2 tests, total 6 tests). |
| **Pre-requisites** | T-3 (uses `_now_iso_utc`). |
| **Acceptance criteria** | REQ-HYGIENE-BACKUP-LAYOUT (full — manifest shape + file copy). |
| **Risk notes** | `shutil.copytree` with `dirs_exist_ok=False` will fail if the snapshot dir already exists; that is desired behavior (snapshot dir is fresh per UTC-ISO timestamp). If two `fix` invocations land in the same UTC second (rare but possible), the second will fail with `FileExistsError` — this is acceptable; user can re-run. The `created_at` field MUST equal the directory name; capture it once at the top of the function. |

---

### T-6 — `workspace_hygiene.py`: `_verify_post_mutation()` + `_restore_from_snapshot()`

| Field | Value |
|-------|-------|
| **Task ID** | T-6 |
| **Title** | Implement post-mutation verifier + snapshot restore |
| **Goal** | Verify that the `git init` mutation produced a valid `.git/` directory; on failure, restore the project from the snapshot. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_verify_post_mutation_returns_true_on_valid_git -xvs` (build a project, run real `git init`, call `_verify_post_mutation(project_path, snapshot)`, assert `True`). Then `test_restore_from_snapshot_round_trip` (snapshot a project with file `A.md`, delete the file, call `_restore_from_snapshot(snapshot, project)`, assert `A.md` is back and identical to the pre-snapshot content). Then `test_pollution_protocol_restore_on_verify_fail` (snapshot a project, run real `git init` to make a valid `.git/`, monkeypatch `_verify_post_mutation` to return False, run the full triple, assert the project's `.git/` was removed and pre-mutation files are restored). |
| **GREEN — minimal implementation** | Add `def _verify_post_mutation(project_path: Path, pre_snapshot: Path) -> bool:` that returns `True` iff `(project_path / ".git").is_dir() and (project_path / ".git" / "HEAD").is_file() and (project_path / ".git" / "config").is_file()`. Add `def _restore_from_snapshot(snapshot: Path, target: Path) -> None:` that: (1) `shutil.rmtree(target / ".git", ignore_errors=True)`; (2) `shutil.rmtree(target)` (preserves the dir name but wipes content); (3) `target.mkdir(parents=True, exist_ok=True)`; (4) `shutil.copytree(snapshot / "files", target, dirs_exist_ok=True)`. |
| **REFACTOR — cleanup** | Extract `_git_metadata_intact(project_path: Path) -> bool` helper (re-used for the verify check); add type hints on `Path` operations; verify `shutil.rmtree` + `mkdir` is atomic-enough for the test isolation (it is — `tmp_path` is per-test). |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (T-5 + ~25 LOC); `tests/unit/test_workspace_hygiene.py` (+~35 LOC for 3 tests, total 9 tests). |
| **Pre-requisites** | T-5 (snapshot must exist for restore). |
| **Acceptance criteria** | REQ-HYGIENE-POLLUTION-PROTOCOL (full — verify + restore on failure). |
| **Risk notes** | `_verify_post_mutation` only checks for the existence of `.git/`, `HEAD`, and `config` — it does NOT run `git status` (that would be a more thorough check but adds 100ms+ per call and a subprocess dependency for a low-likelihood failure mode). The pollution-protocol triple in T-7 wires the verify failure to the restore call. |

---

### T-7 — `workspace_hygiene.py`: `_apply_hygiene_rule()` orchestrator

| Field | Value |
|-------|-------|
| **Task ID** | T-7 |
| **Title** | Implement central orchestrator with pollution-protocol triple |
| **Goal** | The single entrypoint that wires together snapshot → mutate → verify → restore. Validates `--yes` and `--backup` gates before any mutation. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_apply_hygiene_rule_dry_run_does_not_mutate -xvs` (build a non-empty project, call `_apply_hygiene_rule(entry, "R2_GIT_INIT", dry_run=True, yes=True, backup=True, backup_root=tmp)`, assert `result.dry_run is True`, `result.success is True`, no `.git/` was created, no backup was created, registry was not written). Then `test_apply_hygiene_rule_refuses_without_yes` (assert `MutationGateError` is raised with `user_message` containing `"--yes"`). Then `test_apply_hygiene_rule_refuses_non_empty_without_backup` (assert `EmptyProjectError` is raised with `non_empty_files` containing `"README.md"`). |
| **GREEN — minimal implementation** | Add `def _apply_hygiene_rule(project: ProjectEntry, rule_id: str, *, dry_run: bool, yes: bool, backup: bool, backup_root: Path) -> HygieneResult:` that: (1) gate check: `if not yes and not dry_run: raise MutationGateError("--yes required for `flow workspace fix` mutations")`; (2) backup check: `if not dry_run and not _is_empty_project(project.path) and not backup: raise EmptyProjectError(...)`; (3) if `backup and (not _is_empty_project(...) or yes): snapshot = _snapshot_project(project.path, backup_root)`; (4) if `dry_run: return HygieneResult(... dry_run=True, action_taken="would-run-git-init", success=True, backup_path=snapshot if backup else None)`; (5) call `_git("init", str(project.path))` (import the `_git` seam from `flow_engineering.cli`); (6) `if not _verify_post_mutation(project.path, snapshot): _restore_from_snapshot(snapshot, project.path); return HygieneResult(..., success=False, error="verify failed")`; (7) load registry, append the project to `projects[]` with `last_status_check=_now_iso_utc()`, `save_registry_atomic(registry)`; (8) return `HygieneResult(..., success=True, backup_path=snapshot)`. |
| **REFACTOR — cleanup** | Extract `_load_and_append_project(entry: ProjectEntry) -> None` helper; add explicit `from flow_engineering.cli import _git` import at module top (circular-import safe: `cli.py` does not import `workspace_hygiene` at module load); add a docstring citing the pollution-protocol triple diagram in design.md §Data Flow. |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (T-6 + ~40 LOC); `tests/unit/test_workspace_hygiene.py` (+~45 LOC for 3 tests, total 12 tests). |
| **Pre-requisites** | T-4 (empty check), T-5 (snapshot), T-6 (verify + restore), T-2 (load/save registry). |
| **Acceptance criteria** | REQ-HYGIENE-FIX-SURFACE (full — R2 happy path); REQ-HYGIENE-DRY-RUN-DEFAULT (full — gate + dry-run); REQ-HYGIENE-BACKUP-GATE-NONEMPTY (full — empty + backup gate); REQ-HYGIENE-POLLUTION-PROTOCOL (full — restore on verify fail); REQ-HYGIENE-REGISTRY-V1 (partial — registry update on success). |
| **Risk notes** | The `_git` import from `flow_engineering.cli` introduces a soft dependency. To avoid a circular import, the `cli.py` module-level code does NOT import `workspace_hygiene` — only the new Click commands inside the `workspace_group` block (T-9..T-12) do. Verify with `uv run --frozen python -c "import flow_engineering.cli"` after T-9 lands. If the import chain breaks, fall back to `subprocess.run` inline (loses testability — last resort). |

---

### T-8 — `workspace_hygiene.py`: `_archive_project()` + `_restore_archived_project()`

| Field | Value |
|-------|-------|
| **Task ID** | T-8 |
| **Title** | Implement registry archive/restore operations |
| **Goal** | Move an entry between `projects[]` and `archived[]` immutably; default `--reason` to `"manual archive"`; raise `RegistryError` if the name is not in the source list. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_workspace_hygiene.py::test_archive_project_moves_entry_with_default_reason -xvs` (build a registry with one `ProjectEntry` named `mockup`; call `_archive_project(registry, "mockup", reason=None)`; assert returns a NEW `Registry` (input unchanged) with `projects=[]` and `archived=[ArchivedEntry(name="mockup", reason="manual archive")]`). Then `test_restore_archived_project_reverses_archive` (registry with one `ArchivedEntry`; call `_restore_archived_project(registry, "mockup")`; assert new `Registry` has `projects=[...]` and `archived=[]`). Then `test_archive_project_raises_for_missing_name` (assert `RegistryError` raised with message containing `"not found"`). |
| **GREEN — minimal implementation** | Add `def _archive_project(registry: Registry, project_name: str, reason: str | None) -> Registry:` that: (1) find the `ProjectEntry` in `registry.projects`; if not found raise `RegistryError(user_message=f"Project `{project_name}` not found in registry...")`; (2) build new `projects=[p for p in registry.projects if p.name != project_name]`; (3) build `archived_entry = ArchivedEntry(name=found.name, path=found.path, archived_at=_now_iso_utc(), reason=reason or "manual archive")`; (4) return `registry.model_copy(update={"projects": new_projects, "archived": [*registry.archived, archived_entry]})`. Add `def _restore_archived_project(registry: Registry, project_name: str) -> Registry:` that mirrors the same pattern (finds in `archived[]`, moves to `projects[]` with `last_status_check=_now_iso_utc()`). |
| **REFACTOR — cleanup** | Extract `_move_entry(registry, name, *, from_field, to_field, reason_override=None)` shared helper; ensure `model_copy(update=...)` produces an independent model (pydantic v2 deep-copies by default); add explicit type annotations. |
| **Files affected** | `src/flow_engineering/workspace_hygiene.py` (T-7 + ~25 LOC); `tests/unit/test_workspace_hygiene.py` (+~30 LOC for 3 tests, total 15 tests). |
| **Pre-requisites** | T-2 (uses `Registry`, `ProjectEntry`, `ArchivedEntry`); T-3 (uses `_now_iso_utc`). |
| **Acceptance criteria** | REQ-HYGIENE-ARCHIVE-SURFACE (full — `--reason` default + entry move); REQ-HYGIENE-RESTORE-SURFACE (full — reverse move). |
| **Risk notes** | The function returns a NEW `Registry`; the caller (the Click command) is responsible for calling `save_registry_atomic(registry)` after the move. Do NOT mutate the input in place — that violates the pydantic v2 contract and surprises callers. If the user passes `--reason=""` (empty string), treat it as a reason (not as None); the `"or"` default only fires on actual `None`. |

---

### T-9 — `cli.py`: `_load_registry_for_cli()` + `workspace_fix_cmd`

| Field | Value |
|-------|-------|
| **Task ID** | T-9 |
| **Title** | Wire `flow workspace fix` Click command with dry-run default |
| **Goal** | Register the first verb on the existing `workspace_group` at `cli.py:2982`. The command resolves the project by name from the workspace root, calls `_apply_hygiene_rule` (which handles all gates), and prints the result. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py::test_workspace_fix_dry_run_default -xvs` (build a tmp workspace with a non-git project `mockup`; invoke `runner.invoke(main, ["workspace", "fix", "mockup"], env={"FLOW_PROJECTS_ROOT": str(root)})`; assert `result.exit_code == 0`, `result.output` contains `"[DRY-RUN]"` or similar planned-action marker, no `.git/` created). Then `test_workspace_fix_happy_path_creates_git_and_backup` (same setup with `--yes --backup`; assert `.git/` exists, `~/.flow-engineering/backups/mockup/<ts>/manifest.json` exists, registry has the entry). |
| **GREEN — minimal implementation** | Add to `cli.py` (right after the existing `workspace_status` definition, around line 3024): `def _load_registry_for_cli() -> Registry: return load_registry()` (thin wrapper for testability). Add `def _resolve_project_path(name: str, root: Path) -> Path:` that returns `root / name` after a pre-flight check (refuse if `name` is empty, if `root / name` is not a directory, or if the resolved path equals the `~/.flow-engineering/` registry dir or the `flow-engineering` repo path). Add `@workspace_group.command(name="fix")` with `@click.argument("project")` + `--dry-run/--no-dry-run` (default True) + `--yes` (is_flag) + `--backup/--no-backup` (default False) options; the body resolves the project path, loads the registry, builds a `ProjectEntry` from `_detect_project_markers(path)` (Phase 1 read-only consumer), calls `_apply_hygiene_rule(...)`, and prints the `HygieneResult.action_taken` with a `[DRY-RUN]` prefix when `dry_run=True`; on `MutationGateError` / `EmptyProjectError` / `RegistryError` → `click.echo(error.user_message, err=True)` + `raise SystemExit(2)`. |
| **REFACTOR — cleanup** | Extract the pre-flight guard into a shared `_workspace_hygiene_preflight(target: Path) -> None` (also used by T-10, T-12); add a module-level import `from flow_engineering import workspace_hygiene` near the top of `cli.py`. |
| **Files affected** | `src/flow_engineering/cli.py` (T-9..T-12 add ~85 LOC across all 4 commands); `tests/unit/test_cli_workspace_hygiene.py` (NEW, ~50 LOC for 2 tests). |
| **Pre-requisites** | T-7 (orchestrator must exist). |
| **Acceptance criteria** | REQ-HYGIENE-FIX-SURFACE (full — surface + pre-flight); REQ-HYGIENE-DRY-RUN-DEFAULT (full — dry-run default + missing-yes refusal); REQ-HYGIENE-BACKUP-GATE-NONEMPTY (full — non-empty without --backup refuses). |
| **Risk notes** | Click `--dry-run/--no-dry-run` flag pair: when neither is passed, Click uses the default (True). The `--dry-run` form is explicit; `--no-dry-run` is the escape hatch. DO NOT add a separate `--no-dry-run` boolean — Click handles both forms. `_detect_project_markers` is imported (read-only) from `flow_engineering.cli` itself; do NOT redefine or modify it. |

---

### T-10 — `cli.py`: `workspace_archive_cmd`

| Field | Value |
|-------|-------|
| **Task ID** | T-10 |
| **Title** | Wire `flow workspace archive` Click command |
| **Goal** | Register the second verb. The command looks up the named project in the registry, calls `_archive_project` + `save_registry_atomic`, and prints `archived: <name> (reason: <reason>)`. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py::test_workspace_archive_happy_path -xvs` (registry with one project `mockup-2-blog`; invoke `["workspace", "archive", "mockup-2-blog", "--reason", "deprecated", "--yes"]`; assert exit 0, stdout contains `"archived: mockup-2-blog (reason: deprecated)"`, registry file now has `mockup-2-blog` in `archived[]`). Then `test_workspace_archive_refuses_without_yes` (same setup without `--yes`; assert non-zero exit, stderr contains `"--yes"`, registry unchanged). |
| **GREEN — minimal implementation** | Add `@workspace_group.command(name="archive")` with `@click.argument("project")` + `--reason` (default None) + `--yes` (is_flag) options. Body: gate check `if not yes: click.echo("--yes required for `flow workspace archive`", err=True); raise SystemExit(2)`; `registry = _load_registry_for_cli()`; `try: new_reg = workspace_hygiene._archive_project(registry, project, reason) except RegistryError as e: click.echo(e.user_message, err=True); raise SystemExit(2)`; `save_registry_atomic(new_reg)`; `click.echo(f"archived: {project} (reason: {reason or 'manual archive'})")`. |
| **REFACTOR — cleanup** | Reuse the gate-check pattern from T-9 via a shared `_require_yes(yes: bool, command: str) -> None` helper; add a typed return annotation. |
| **Files affected** | `src/flow_engineering/cli.py` (T-9 + ~15 LOC); `tests/unit/test_cli_workspace_hygiene.py` (+~40 LOC for 2 tests, total 4 tests). |
| **Pre-requisites** | T-8 (`_archive_project`); T-2 (`save_registry_atomic`); T-9 (imports + pre-flight pattern). |
| **Acceptance criteria** | REQ-HYGIENE-ARCHIVE-SURFACE (full — `--reason` optional + default). |
| **Risk notes** | The archive command does NOT touch the filesystem (no `.git/` to create, no files to move) — only the registry. This is the simplest of the 4 commands. The "missing project" error path uses the `RegistryError.user_message` from T-8. |

---

### T-11 — `cli.py`: `workspace_archived_cmd` (text table only)

| Field | Value |
|-------|-------|
| **Task ID** | T-11 |
| **Title** | Wire `flow workspace archived` Click command (text-only) |
| **Goal** | Register the third verb. Renders a fixed-width text table with columns `NAME  ARCHIVED_AT  REASON`. No `--json` / `--format` flag in MVP. Rejects `--json` with a clear error. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py::test_workspace_archived_text_table -xvs` (registry with 2 archived entries; invoke `["workspace", "archived"]`; assert exit 0, stdout contains header `NAME  ARCHIVED_AT  REASON`, stdout contains a row for each name). Then `test_workspace_archived_empty_registry_message` (empty registry; invoke; assert exit 0, stdout contains `(no archived projects)`). |
| **GREEN — minimal implementation** | Add `@workspace_group.command(name="archived")` with no arguments/options, but explicitly reject `--json` via `ctx = click.get_current_context(); if "--json" in ctx.args: click.echo("--json is unsupported for `flow workspace archived` in MVP", err=True); raise SystemExit(2)`. Body: `registry = _load_registry_for_cli()`; if `not registry.archived: click.echo("(no archived projects)"); return`; else render: `click.echo("NAME  ARCHIVED_AT  REASON")`; for each `archived` entry: `click.echo(f"{entry.name}  {entry.archived_at}  {entry.reason}")`. |
| **REFACTOR — cleanup** | Extract `_render_archived_text_table(entries: list[ArchivedEntry]) -> str` for testability; use `textwrap` or fixed-width formatting (e.g., `{name:<24}  {archived_at:<20}  {reason}`) — confirm the spec REQ-HYGIENE-ARCHIVED-LISTING "fixed-width text table" requirement. |
| **Files affected** | `src/flow_engineering/cli.py` (T-10 + ~25 LOC); `tests/unit/test_cli_workspace_hygiene.py` (+~40 LOC for 2 tests, total 6 tests). |
| **Pre-requisites** | T-10 (imports + pre-flight pattern). |
| **Acceptance criteria** | REQ-HYGIENE-ARCHIVED-LISTING (full — text table + 3 columns + empty case); REQ-HYGIENE-NO-JSON-MVP (full — `--json` rejected). |
| **Risk notes** | The `--json` rejection is best-effort via `ctx.args` inspection; a future Click version might surface this differently. The cleanest long-term approach is a custom decorator that errors on unknown options, but MVP accepts the `ctx.args` approach to avoid Click 8.x API churn. The text table MUST be human-readable; the BDD AC8 asserts the header line is present. |

---

### T-12 — `cli.py`: `workspace_restore_cmd`

| Field | Value |
|-------|-------|
| **Task ID** | T-12 |
| **Title** | Wire `flow workspace restore` Click command |
| **Goal** | Register the fourth verb. Reverses an archive: moves the entry from `archived[]` back to `projects[]`, saves the registry, prints `restored: <name>`. |
| **RED — failing test first** | `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py::test_workspace_restore_happy_path -xvs` (registry with `mockup-2-blog` in `archived[]`; invoke `["workspace", "restore", "mockup-2-blog", "--yes"]`; assert exit 0, stdout contains `"restored: mockup-2-blog"`, registry now has `mockup-2-blog` in `projects[]` and `archived[]` is empty). Then `test_workspace_restore_refuses_without_yes` (assert non-zero exit, stderr contains `"--yes"`, registry unchanged). |
| **GREEN — minimal implementation** | Add `@workspace_group.command(name="restore")` with `@click.argument("project")` + `--yes` (is_flag) options. Body: gate check `if not yes: click.echo("--yes required for `flow workspace restore`", err=True); raise SystemExit(2)`; `registry = _load_registry_for_cli()`; `try: new_reg = workspace_hygiene._restore_archived_project(registry, project) except RegistryError as e: click.echo(e.user_message, err=True); raise SystemExit(2)`; `save_registry_atomic(new_reg)`; `click.echo(f"restored: {project}")`. |
| **REFACTOR — cleanup** | Reuse `_require_yes` from T-10; add a type annotation. |
| **Files affected** | `src/flow_engineering/cli.py` (T-11 + ~15 LOC); `tests/unit/test_cli_workspace_hygiene.py` (+~40 LOC for 2 tests, total 8 tests). |
| **Pre-requisites** | T-8 (`_restore_archived_project`); T-10 (gate pattern). |
| **Acceptance criteria** | REQ-HYGIENE-RESTORE-SURFACE (full — reverse archive + --yes gate). |
| **Risk notes** | The restore command does NOT touch the filesystem (the project's directory on disk is untouched; only the registry is updated). This is symmetric with T-10's archive command. If the project directory on disk has been deleted between archive and restore, the restored registry entry will point to a non-existent path — that is acceptable for MVP (the user can re-`fix` the project). |

---

### T-13 — BDD step glue + run BDD suite

| Field | Value |
|-------|-------|
| **Task ID** | T-13 |
| **Title** | Implement pytest-bdd step glue for the 16 scenarios in `tests/bdd/workspace_hygiene.feature` |
| **Goal** | Wire Given/When/Then steps to the production code so the 16 scenarios in the existing feature file (already at `tests/bdd/workspace_hygiene.feature`) pass under `uv run --frozen pytest tests/bdd/workspace_hygiene.feature -q`. |
| **RED — failing test first** | `uv run --frozen pytest tests/bdd/workspace_hygiene.feature -q` (should report 16 scenarios with step collection errors — the `@scenario` decorators reference undefined step functions). |
| **GREEN — minimal implementation** | Create `tests/bdd/test_workspace_hygiene_steps.py` with: (1) imports (`pytest`, `pytest_bdd`, `click.testing.CliRunner`, `from flow_engineering import cli as cli_mod`, `from flow_engineering import workspace_hygiene`, `from flow_engineering.registry import Registry, ProjectEntry, ArchivedEntry, save_registry_atomic, registry_path`); (2) a `@pytest.fixture` `tmp_workspace(tmp_path, monkeypatch)` that monkeypatches `Path.home` and `cli_mod._git` to a fake that returns `CompletedProcess(returncode=0, stdout="", stderr="")`; (3) `@pytest.fixture` `cli_runner()` returning a `CliRunner`; (4) step definitions for the 16 scenarios, parametrized: ~7 Given steps (workspace setup, registry setup, post-mutation-verifier mock), ~3 When steps (`I run the CLI ...`, `the registry write is interrupted ...`), ~12 Then steps (exit code, stdout/stderr content, file existence, registry content). Use the `req_*.feature` precedent in `tests/bdd/test_cross_project_federation_steps.py` for style. Use `@scenario("workspace_hygiene.feature", "<scenario_name>")` per scenario. |
| **REFACTOR — cleanup** | Extract shared Given steps into `@given` reusable functions (`a_workspace_root_with_*`, `a_registry_with_*`); consolidate Then steps where the assertion is identical across scenarios; add `from tests.unit._workspace_fixtures import make_python_project` (or write a Phase-4-isolated `make_fake_unmanaged_project` if you prefer the new-fixture pattern from design.md §File Changes). |
| **Files affected** | `tests/bdd/test_workspace_hygiene_steps.py` (NEW, ~80-200 LOC); `tests/bdd/workspace_hygiene.feature` (already exists, NOT modified). |
| **Pre-requisites** | T-9..T-12 (all 4 CLI commands must be wired and unit-tested before BDD glue can call them end-to-end). |
| **Acceptance criteria** | REQ-HYGIENE-DRY-RUN-DEFAULT, REQ-HYGIENE-BACKUP-GATE-NONEMPTY, REQ-HYGIENE-FIX-SURFACE, REQ-HYGIENE-BACKUP-LAYOUT, REQ-HYGIENE-ARCHIVE-SURFACE, REQ-HYGIENE-ARCHIVED-LISTING, REQ-HYGIENE-RESTORE-SURFACE, REQ-HYGIENE-AC9-PRESERVATION, REQ-HYGIENE-POLLUTION-PROTOCOL, REQ-HYGIENE-REGISTRY-V1, REQ-HYGIENE-R1-EXPLICITLY-OUT (all 12 REQs validated via 16 BDD scenarios). |
| **Risk notes** | BDD step files can grow large (~200 LOC for 16 scenarios with ~5 steps each). Stay disciplined: reuse Given/When/Then definitions across scenarios via parametrization. The feature file already exists — do NOT modify it; only the step glue is new. The AC10 (byte-identical for non-targets) scenario is the hardest to set up; build the workspace with 2 projects, capture the `flow projects ls --json` bytes for the non-target, run the archive, then re-invoke and assert byte equality. |

---

### T-14 — AC9 byte-identical verification

| Field | Value |
|-------|-------|
| **Task ID** | T-14 |
| **Title** | Verify AC9 byte-identical guard stays green throughout Phase 4 |
| **Goal** | Confirm the existing `test_flow_projects_ls_json_byte_identical_envelope` test at `tests/unit/test_cli_projects.py:435` passes after all 13 prior tasks. No code changes in this task — pure verification + log. |
| **RED — failing test first** | n/a (this is a verification task, not a RED-GREEN cycle). The task EXISTS because AC9 is the regression net for the entire change. |
| **GREEN — minimal implementation** | Run: `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs` and assert exit 0. Then run the full Phase 1/2/3 test files to confirm no collateral damage: `uv run --frozen pytest tests/unit/test_cli_projects.py tests/unit/test_cli_workspace_status.py -q`. Then run the full unit test suite: `uv run --frozen pytest tests/unit -q`. Log the results in a comment block at the bottom of `tests/unit/test_cli_workspace_hygiene.py` for traceability. |
| **REFACTOR — cleanup** | If the AC9 test ever fails after a Phase 4 change, the failure is a **BLOCKER** — do NOT proceed to archive. The fix is almost always: a Phase 4 code path accidentally called `_detect_project_markers` with mutated state, or added a timestamp field to the Phase 1 envelope. Use the failure message to localize the regression. |
| **Files affected** | none (read-only verification); optional log comment in `tests/unit/test_cli_workspace_hygiene.py` (~5 LOC). |
| **Pre-requisites** | T-1..T-13 (all production code + tests must be in place for AC9 to be a meaningful check). |
| **Acceptance criteria** | REQ-HYGIENE-AC9-PRESERVATION (full — guard green). |
| **Risk notes** | The test name MUST be cited verbatim: `test_flow_projects_ls_json_byte_identical_envelope`. The line number `435` is the current location at HEAD `cb82274`; if it shifts by 1-2 lines in a future commit, update the cite in the verification log but keep the test name exact. The test docstring at line 438 references "AC8" (the Phase 1 designation) — the Phase 4 designation is "AC9" (per design.md and the spec). Both labels point to the same byte-identical contract. |

---

## 4. Task Ordering & Dependency Graph

```text
T-1 (registry models) ──► T-2 (load/save) ──┐
                                            ├──► T-7 (apply_hygiene_rule) ──► T-9 (workspace_fix_cmd) ─┐
T-3 (HygieneResult) ──► T-4 (is_empty) ─┐                                          │                 │
                       │                 ├──► T-7                                       │                 │
                       └─► T-5 (snapshot) ──► T-6 (verify + restore) ──► T-7 ────────┤                 │
                                                                                     ▼                 │
T-3 ──► T-8 (archive/restore_archived) ────────────────────────────────────► T-10 (archive_cmd) ────┤
                                                                                                     │
                                                                                     T-11 (archived_cmd)│
                                                                                                     │
                                                                                     T-12 (restore_cmd)│
                                                                                                     ▼
                                                                                                    T-13 (BDD glue)
                                                                                                     │
                                                                                                     ▼
                                                                                                    T-14 (AC9 verify)
```

**Parallelizable** (test setup, fixture creation can be drafted in parallel with production tasks):
- T-13's step glue can be drafted in parallel with T-9..T-12 (the glue is exercised once the commands exist).
- T-14's verification script can be drafted in parallel with all other tasks.

**Strictly sequential**:
- T-1 → T-2 (T-2 depends on T-1's models).
- T-3 → T-4, T-5, T-6, T-7, T-8 (all use the exception types and `_now_iso_utc`).
- T-4, T-5, T-6, T-2 → T-7 (orchestrator wires all of them).
- T-7, T-8 → T-9..T-12 (CLI commands call orchestrator functions).
- T-9..T-12 → T-13 (BDD glue invokes CLI commands).
- T-1..T-13 → T-14 (AC9 verification is the last step).

**Order**: foundations first (T-1, T-3) → helpers next (T-2, T-4, T-5, T-6) → orchestrator (T-7, T-8) → CLI commands (T-9, T-10, T-11, T-12) → BDD glue (T-13) → AC9 verification (T-14).

---

## 5. Forecast (detailed)

| Category | Estimate |
|----------|----------|
| Total production LOC | ~335 (sum of T-1..T-12 prod columns) |
| Total test LOC (unit) | ~18 unit tests × 12 LOC avg = ~216 |
| Total test LOC (CLI) | ~8 CLI tests × 25 LOC avg = ~200 |
| Total test LOC (BDD) | ~16 scenarios + step glue = ~200 |
| **Total test LOC** | **~616** |
| **Total changed lines (prod + test)** | **~951** |
| 400-line review budget | exceeded by ~2.4x → **HIGH RISK** |
| `size:exception` required? | **no** (chained PRs splits to ≤460 LOC per PR) |
| New test files | 4 (`tests/unit/test_registry.py`, `tests/unit/test_workspace_hygiene.py`, `tests/unit/test_cli_workspace_hygiene.py`, `tests/bdd/test_workspace_hygiene_steps.py`) |
| New production files | 2 (`src/flow_engineering/registry.py`, `src/flow_engineering/workspace_hygiene.py`) |
| Modified production files | 1 (`src/flow_engineering/cli.py`, +~85 LOC for 4 new commands + import) |
| New BDD feature files | 0 (already exists at `tests/bdd/workspace_hygiene.feature`) |

---

## 6. Review Workload Forecast (structured)

```yaml
forecast_loc: 951
forecast_prod_loc: 335
forecast_test_loc: 616
chained_pr_recommendation: yes
chained_pr_rationale: |
  Total ~951 LOC exceeds the 400-line review budget by ~2.4x. PR1 ships the
  verified core (registry + orchestrator + AC9 guard) so reviewers can audit
  the safety net in isolation before any user-facing surface lands. PR2 wires
  the CLI verbs and proves end-to-end BDD coverage. Both PRs land stacked
  to main.
400_line_budget_risk: high
size_exception_required: no
size_exception_rationale: null
decision_needed_before_apply: yes
decision_question: |
  El forecast de Phase 4 es ~335 prod + ~616 test = ~951 LOC total, claramente
  sobre el budget de 400. ¿Querés (A) single PR con `size:exception` siguiendo
  tu patrón de Phase 1/3, (B) 2 chained PRs (PR1: foundations + orchestrator +
  AC9 guard; PR2: CLI + BDD), o (C) 3 chained PRs más granulares?
```

---

## 7. Suggested Task Ordering for Chained PRs

If the user picks **Option B (2 chained PRs, stacked-to-main)**:

### PR 1 — Foundations + Orchestrator (~440 LOC)
- **Tasks**: T-1, T-2, T-3, T-4, T-5, T-6, T-7, T-8, T-14
- **Files created**:
  - `src/flow_engineering/registry.py` (~90 LOC)
  - `src/flow_engineering/workspace_hygiene.py` (~215 LOC)
  - `tests/unit/test_registry.py` (~75 LOC, 5 tests)
  - `tests/unit/test_workspace_hygiene.py` (~210 LOC, 15 tests)
- **Files modified**: none in `cli.py` (CLI commands are PR 2)
- **Verification**:
  - `uv run --frozen pytest tests/unit/test_registry.py tests/unit/test_workspace_hygiene.py -q` → all 20 tests pass
  - `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs` → green (AC9 guard)
  - `uv run --frozen pytest tests/unit -q` → no regressions in existing test suite
  - `uv run --frozen ruff check src/flow_engineering/registry.py src/flow_engineering/workspace_hygiene.py tests/unit/test_registry.py tests/unit/test_workspace_hygiene.py`
  - `uv run --frozen mypy src/flow_engineering/registry.py src/flow_engineering/workspace_hygiene.py`
- **Self-contained**: yes — no Click commands added, so the surface is internal-only; reviewers can audit the safety net without parsing CLI plumbing.
- **Rollback**: `git revert <sha>` deletes the two new files; no `_git` seam or `cli.py` touched.

### PR 2 — CLI Surface + BDD (~510 LOC)
- **Tasks**: T-9, T-10, T-11, T-12, T-13
- **Files modified**:
  - `src/flow_engineering/cli.py` (+~85 LOC, 4 new Click commands + import)
- **Files created**:
  - `tests/unit/test_cli_workspace_hygiene.py` (~200 LOC, 8 tests)
  - `tests/bdd/test_workspace_hygiene_steps.py` (~200 LOC, 16 scenarios)
- **Verification**:
  - `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py -q` → 8 tests pass
  - `uv run --frozen pytest tests/bdd/workspace_hygiene.feature -q` → 16 scenarios pass
  - `uv run --frozen pytest tests/unit -q` → no regressions
  - `uv run --frozen pytest tests/ -q` → full suite green
  - `uv run --frozen ruff check src/flow_engineering/cli.py tests/unit/test_cli_workspace_hygiene.py tests/bdd/test_workspace_hygiene_steps.py`
  - `uv run --frozen mypy src/flow_engineering/cli.py`
- **Depends on**: PR 1 (must be merged first; the CLI commands call orchestrator functions).
- **Self-contained**: yes — wires the verified core to the user-facing verbs; BDD proves end-to-end behavior.
- **Rollback**: `git revert <sha>` removes the 4 Click commands + the test files; orchestrator remains in place (PR 1) and can be reused by a future CLI shape.

If the user picks **Option A (single PR with `size:exception`)**:
- All 14 tasks in one PR, single commit per user's pattern, ~951 LOC.

If the user picks **Option C (3 chained PRs)**:
- **PR 1a** (Registry only): T-1, T-2 → ~165 LOC
- **PR 1b** (Orchestrator + helpers): T-3..T-8 → ~280 LOC
- **PR 2** (CLI + BDD + AC9): T-9..T-14 → ~510 LOC

---

## 8. Out-of-Scope Task Reminders

**NO tasks** for any of the following (per locked constraints #1, #6, #9, #13, #20, design.md §Out of Scope, spec §7):

- R1 dirty-git remediation (locked constraint #9: deferred to a future change; Phase 4 makes no commitment).
- R3 no-tests bootstrap.
- R4 no-openspec bootstrap.
- `--json` / `--format` output flag on any of the 4 verbs (locked constraint #6; REQ-HYGIENE-NO-JSON-MVP explicitly rejects it).
- Backup retention / pruning policy.
- TUI / interactive prompts (Phase 5).
- Web dashboard (Phase 5).
- Registry migration tooling (no v0 → v1).
- The orphan `openspec/specs/workspace/spec.md` capability spec (locked constraint #20: document as Tech Debt Follow-up, do NOT create tasks).
- The 4 pre-existing test failures from session #453.
- The `__name__ == '__main__'` guard bug at `cli.py:2665`.
- Modifications to Phase 1 code (`_detect_project_markers` at `cli.py:3137`, `projects_ls` envelope assembly).
- Modifications to Phase 2 code (`where.py`, cross-project search).
- Modifications to Phase 3 code (`workspace_status`, `_summarize_workspace_status`, `_resolve_projects_root`).
- Any `git add` / uncommitted-file handling / index manipulation. Per locked constraint #9, no R1 dirty-git remediation code path may exist; the worktree, index, and untracked-file state MUST remain untouched for dirty projects.

---

## 9. Commit Plan (per `work-unit-commits` skill)

Two options:

### Option X — Single commit per chained PR (matches user's pattern from Phase 1/3)

- **PR 1 commit message**:
  ```text
  feat(workspace): add registry + orchestrator for write-side hygiene

  - registry.py: pydantic v2 v1 schema + atomic write (project_aliases.py:164 pattern)
  - workspace_hygiene.py: orchestrator + pollution-protocol triple
    (_snapshot_project → mutate → _verify_post_mutation → restore on failure)
  - tests: 18 unit tests for registry + orchestrator
  - AC9 byte-identical guard preserved (test_flow_projects_ls_json_byte_identical_envelope)
  - R1 deferred; no `_git` seam or cli.py touched yet
  ```
- **PR 2 commit message**:
  ```text
  feat(workspace): add 4 write-side CLI verbs (fix, archive, archived, restore)

  - cli.py: 4 new Click commands on workspace_group at cli.py:2982
  - tests: 8 CLI unit tests + 16 BDD scenarios with pytest-bdd step glue
  - pollution-protocol triple verified end-to-end via BDD
  - AC9 byte-identical guard still green
  ```

### Option Y — 2-commit split per chained PR (T-1..T-8 prod / T-9..T-13+tests + BDD)

- **PR 1**:
  - Commit 1: T-1..T-8 (production: registry.py + workspace_hygiene.py)
  - Commit 2: T-1..T-8 (unit tests)
- **PR 2**:
  - Commit 1: T-9..T-12 (cli.py additions)
  - Commit 2: T-13 (BDD glue + 16 scenarios) + 8 CLI tests

**Recommendation**: Option X (single commit per PR). The user has shipped every prior change as a single commit per PR (per session #453 pattern). The strict TDD evidence lives in the diff (RED test → GREEN impl → REFACTOR per task). Slicing at the prod/tests boundary breaks the work-unit pattern. If the user wants Option Y, the orchestrator can adjust at apply time.

---

## 10. Pre-existing Failures (out-of-scope reminder)

The following are **NOT addressed** by any task in this change (per design.md §Pre-existing Failures, mirrored here for traceability):

1. **4 pre-existing test failures from session #453** (observed at HEAD `cb82274`). Not regressed by Phase 4; not fixed. `sdd-apply` may see them in the full test suite output and should NOT mark them as Phase 4 regressions.
2. **`__name__ == '__main__'` guard bug at `cli.py:2665`** — pre-existing in a different file area; unrelated to Phase 4. New commands register AFTER line 2982 (consistent with `workspace_status` at line 2987).
3. **Phase 1 stub fields** (`has_graphify`, `has_engram`) — read-only consumers in Phase 4; not in scope.

---

## 11. Acceptance Criteria → REQ Mapping (traceability)

| AC | REQ | Task(s) implementing | BDD scenario |
|----|-----|----------------------|--------------|
| AC1 | REQ-HYGIENE-DRY-RUN-DEFAULT | T-7, T-9, T-13 | dry-run on non-git project does not mutate filesystem |
| AC2 | REQ-HYGIENE-DRY-RUN-DEFAULT | T-7, T-9, T-13 | fix without --yes refuses and mentions --yes |
| AC3 | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | T-4, T-7, T-9, T-13 | non-empty fix without --backup refuses and mentions --backup |
| AC4 | REQ-HYGIENE-FIX-SURFACE + REQ-HYGIENE-BACKUP-LAYOUT | T-5, T-6, T-7, T-9, T-13 | non-empty fix with --yes --backup creates .git and backup |
| AC5 | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | T-4, T-7, T-9, T-13 | empty fix with --yes (no --backup) creates .git and no backup |
| AC6 | REQ-HYGIENE-ARCHIVE-SURFACE | T-8, T-10, T-13 | archive with --reason records the user-supplied value |
| AC7 | REQ-HYGIENE-ARCHIVE-SURFACE | T-8, T-10, T-13 | archive without --reason defaults to "manual archive" |
| AC8 | REQ-HYGIENE-ARCHIVED-LISTING | T-11, T-13 | archived outputs a text table with three columns |
| AC9 | REQ-HYGIENE-RESTORE-SURFACE | T-8, T-12, T-13 | restore reverses a prior archive |
| AC10 | REQ-HYGIENE-AC9-PRESERVATION | T-14, T-13 (BDD scenario) | workspace-hygiene commands preserve flow projects ls --json bytes for non-targets |
| AC11 | REQ-HYGIENE-POLLUTION-PROTOCOL | T-6, T-7, T-13 | post-mutation verify failure triggers restore from snapshot |
| AC12 | REQ-HYGIENE-REGISTRY-V1 | T-1, T-2, T-13 | registry write is atomic on interruption |
| AC13 | REQ-HYGIENE-R1-EXPLICITLY-OUT | T-7 (no R1 path), T-9, T-13 | fix on a dirty-git project does not remediate the dirty state |

---

## 12. Risk Summary

| # | Risk | Severity | Mitigation | Task(s) |
|---|------|----------|------------|---------|
| 1 | **PR diff exceeds 400-line review budget** (~951 LOC) | **High** | Chained PRs (PR 1 = foundations + orchestrator + AC9 guard, PR 2 = CLI + BDD); orchestrator MUST pause and ask user per `delivery_strategy: ask-always`. | T-14 + all of WU-1 / WU-2 split |
| 2 | **`_git` import from `cli.py` in `workspace_hygiene.py` introduces circular import** | Medium | Verify with `uv run --frozen python -c "import flow_engineering.cli"` after T-9 lands; fall back to inline `subprocess.run` only as a last resort. | T-7, T-9 |
| 3 | **`DEFAULT_REGISTRY_PATH` is stale across test contexts** (evaluated at module import time) | Medium | Use `registry_path()` accessor (always re-evaluates `Path.home()`) in T-2's `load_registry`/`save_registry_atomic`. The constant is for documentation only. | T-1, T-2 |
| 4 | **AC9 byte-identical guard regression** (any Phase 4 code path that mutates `_detect_project_markers` output for non-targets) | Medium | T-14 is the explicit verification step. Existing test at `tests/unit/test_cli_projects.py:435` is the safety net. Phase 1/2/3 code paths are READ-ONLY. | T-14 |
| 5 | **Two `fix` invocations in the same UTC second fail** (snapshot dir collision) | Low | Acceptable per design §Migration / Rollout. Documented in T-5 risk notes. | T-5 |
| 6 | **Restore of an archived project whose directory was deleted** leaves a stale registry entry | Low | Acceptable for MVP. User can re-`fix` the project. | T-12 |

---

## 13. Strict TDD Cycle (per-task contract)

Every task in T-1..T-13 follows this discipline (per preflight `strict_tdd: ON`):

1. **RED**: write the failing pytest test (or step glue for BDD); run the exact invocation cited in the task's RED field; confirm it fails for the right reason (ImportError, AssertionError, etc.).
2. **GREEN**: add the minimum production code to make the test pass; run the same pytest invocation; confirm green.
3. **REFACTOR**: clean up typing, docstrings, edge cases; rerun the full test file to confirm no regressions.

**AC9 safety net**: after every task, run `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs` to confirm the byte-identical contract is preserved. This is in addition to the task's own pytest invocation.

**TDD evidence**: the diff per task shows RED (failing test) → GREEN (impl) → REFACTOR (cleanup). The user can audit the evidence by inspecting the commit history.

---

## 14. Open Questions

None. All 4 open questions from the proposal were resolved before the spec phase (locked constraints #10, #11, #12, #13). The orchestrator's preflight preflight (`chained_pr_strategy: ask-always`) flags ONE decision: which PR strategy to use. See Section 6 / Section 7.
