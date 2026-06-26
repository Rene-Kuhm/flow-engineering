# Contributing

## Adding a new transition

1. Update `src/flow_engineering/state.py` — extend `_FORWARD` dict
2. Add CLI subcommand in `src/flow_engineering/cli.py`
3. Add unit tests in `tests/unit/test_<module>.py`
4. Update `FLOW.md` with the transition
5. Update `spec/spec.md` REQ-* with BDD scenario

## Adding a new drift signal

1. Add regex pattern to `src/flow_engineering/drift.py` (`_STRUCTURAL_PATTERNS`, `_TRANSIENT_PATTERNS`, `_CONTRACT_PATTERNS`)
2. Add unit test in `tests/unit/test_drift.py`
3. If the signal needs a new `FailureClass` value, also update:
   - `DriftReport.action()` in `drift.py`
   - `should_retry()` in `retries.py`

## Plugin development

The OpenCode plugin lives in `plugins/flow-engineering.js` and is loaded automatically by OpenCode when present in the project root.

Key rules:

- **One-shot reminder**: use `globalThis.__flow_reminded` to avoid spamming the user.
- **Command namespacing**: prefix `flow ` commands with `[flow-engineering {version}]`.
- **Coexistence**: do not assume sole ownership of `tool.execute.before` — graphify plugin may also fire.

## Releasing

```bash
# Bump version
uv version --bump minor  # or major / patch

# Tag
git tag v$(uv version --short)
git push --tags
```

The `uv tool install .` flow respects `.flow-version` per project.
