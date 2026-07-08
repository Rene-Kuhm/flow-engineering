# Follow-up Audit

This audit separates actionable engineering debt from historical SDD noise. Do not turn every archived suggestion into work; only promote items that still affect correctness, CI, reviewer load, or the next planned slice.

## Current verdict

| Area | Verdict | Decision |
|---|---|---|
| `drift-detection-spec-align` | Resolved in this pass | Active spec now names the shipped flat modules: `drift_graph_loader.py` and `drift_observation_source.py`. |
| Runner health | Resolved | Runner is a Windows Service with `Automatic` start; Startup fallback is removed. |
| Old archived follow-ups | Audit-only | Treat archived follow-ups as historical unless they are re-promoted here or in a new SDD proposal. |
| Future drift-detection slices | Active guardrail | Must follow `openspec/config.yaml` review budget: target ≤400 LOC, hard stop >600 LOC. |

## Promotion rules

Promote a follow-up only when at least one is true:

- It blocks CI, release, or `main` health.
- It documents a live spec/implementation mismatch.
- It reduces reviewer load for the next concrete slice.
- It prevents agent/tooling drift from producing unsafe changes.

Do not promote when:

- It is only old archive commentary.
- It describes a warning accepted during archive with no current user impact.
- It would require a broad refactor without a clear one-slice boundary.

## Next recommended slice

No urgent blocker remains. If continuing drift-detection, choose one small behavior-preserving seam and write the next SDD proposal against the 400/600 LOC guardrail.

## Health checks

```powershell
Get-Service | Where-Object { $_.Name -like "actions.runner.*" } |
  Select-Object Status,StartType,Name

gh run list --repo Rene-Kuhm/flow-engineering --limit 5
```

Expected state:

- runner service: `Running`, `Automatic`
- open PRs: none unless a new work unit is intentionally opened
- latest `main` CI: success
