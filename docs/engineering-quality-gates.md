# Engineering Quality Gates

This project is healthy when `main` stays green, SDD artifacts explain decisions without becoming bureaucracy, and drift-detection changes remain small enough to review honestly.

## Quick path

1. Keep CI green on `main` before starting the next slice.
2. Keep each SDD slice under the review budget.
3. Archive completed changes immediately.
4. Prefer one clear architectural seam over broad “while we are here” refactors.

## Hosted CI operations

Repository workflows use GitHub-hosted runners only. PR jobs must use the
audited `windows-latest` label without expressions or reusable-workflow jobs.

Verify hosted CI health:

```powershell
gh run list --repo Rene-Kuhm/flow-engineering --workflow tests --limit 5
```

For the compact project dashboard, run:

```powershell
.\scripts\system_health.ps1
```

For local Windows test runs, avoid pytest's shared `pytest-current` temp link:

```powershell
$base = Join-Path $env:TEMP "flow-engineering-pytest-$PID"
uv run pytest --basetemp="$base"
```

## SDD anti-bureaucracy rules

| Rule | Decision |
|---|---|
| Planning docs | Write only what changes reviewer/product understanding. Do not repeat implementation details already obvious from code. |
| Completed changes | Archive immediately after verify passes. No active completed folders. |
| Specs | Sync only stable cross-version behavior into `openspec/specs/`. Keep temporary reasoning in archived change docs. |
| Tasks | Tasks must map to reviewable work units, not file-by-file busywork. |
| Verify reports | Include evidence and risk, not prose theater. |

## Drift-detection slice policy

Every future drift-detection slice must satisfy this before implementation:

- One architectural seam only.
- Target review size: ≤400 changed lines.
- Hard stop: >600 changed lines requires a new chained slice before code continues.
- No mixed feature + refactor slice.
- Regression gates named before touching production code.
- Strict TDD remains RED → GREEN → REFACTOR.

Good slice shape:

```text
Extract one protocol/helper + tests + unchanged behavior proof.
```

Bad slice shape:

```text
Extract protocols, change CLI output, rewrite persistence, and update docs in one PR.
```

## Checklist before opening a PR

- [ ] `main` was green before the branch started.
- [ ] Diff is under the 400-line review budget, or explicitly chained.
- [ ] SDD artifacts are short and decision-focused.
- [ ] Tests are with the behavior they verify.
- [ ] Archive/spec sync is included only when the change is complete.
- [ ] Memory/follow-up context was checked via `docs/memory-maintenance.md` before promoting old work.
