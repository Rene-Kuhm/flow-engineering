# Drift Detection Regression Set

Use this as the minimum verification contract for drift-detection slices. It keeps future work small while still protecting the seams that have broken before: graph loading, observation loading, typed errors, CLI output, and event logging.

## Quick path

For any drift-detection code or spec change, run the baseline set:

```powershell
uv run pytest `
  tests/unit/test_decision_drift_graph_loader.py `
  tests/unit/test_decision_drift_observation_source.py `
  tests/unit/test_drift_exceptions.py `
  tests/unit/test_cli_drift.py `
  -q
```

Before pushing a drift-detection behavior change, add the relevant focused tier below.

## Focused tiers

| If the slice touches... | Also run... | Why |
|---|---|---|
| graph snapshot loading or envelope handling | `uv run pytest tests/unit/test_decision_drift_graph_loader.py tests/unit/test_decision_drift_snap_id.py -q` | Protects graph read contracts and stable snapshot identity. |
| Engram/observation loading | `uv run pytest tests/unit/test_decision_drift_observation_source.py tests/unit/test_engram_io_code_refs.py -q` | Protects observation-to-code reference mapping. |
| drift event log or event CLI | `uv run pytest tests/unit/test_drift_event_log.py tests/unit/test_cli_drift_events_list.py tests/unit/test_cli_drift_events_tail.py tests/unit/test_cli_drift_events_stats.py tests/unit/test_cli_drift_events_alias.py -q` | Protects event persistence and operator-facing reads. |
| CLI drift command behavior | `uv run pytest tests/unit/test_cli_drift.py tests/unit/test_cli_watch_drift.py -q` | Protects command output and watch behavior. |
| OpenSpec/BDD behavior contract | `uv run pytest tests/bdd/test_decision_reality_drift_steps.py tests/bdd/test_req_v1_0_drift_events_steps.py tests/bdd/test_req4_drift_steps.py -q` | Protects user-facing scenarios instead of implementation shape. |

## Review guardrail

- Keep drift-detection slices below the review budget in `openspec/config.yaml`: target <=400 changed lines, hard stop >600 without an explicit exception.
- Do not broaden the regression set just to look safer. Add a test only when it protects a behavior or seam the slice actually touches.
- If a bug fix changes drift behavior, include the regression test in the same commit as the fix.

## Definition of done for drift slices

- [ ] Baseline set passed locally.
- [ ] Relevant focused tier passed locally.
- [ ] CI passed after push.
- [ ] Any spec/doc alignment change names the shipped flat modules, for example `drift_graph_loader.py` and `drift_observation_source.py`.
- [ ] Any remaining follow-up is recorded in `docs/follow-up-audit.md` or a current OpenSpec change, not hidden in chat.
