# Contributing

## Review-first contribution workflow

Every contribution starts with review, not implementation. This protects the
existing architecture, behavior, and delivery guarantees while keeping the
project open to useful collaboration.

1. Open an issue describing the problem, intended outcome, scope, and risks.
2. Wait for a maintainer to add the `status:approved` label before writing code.
3. Create a focused branch from the latest `main` and keep the change below the
   repository's review budget whenever possible.
4. Open a draft pull request linked with `Closes #<issue>` so design and scope
   can be reviewed before the change is considered complete.
5. Add tests for behavior changes and regression coverage for bug fixes in the
   same work unit.
6. Request maintainer review and address findings. Changes that affect public
   behavior, architecture, security, persistence, CI, or releases require an
   explicit risk review.
7. Merge only after the required checks pass and a maintainer approves the PR.

Maintainers may close or request redesign of contributions that bypass the
approved issue, broaden scope without agreement, weaken tests or security, or
conflict with documented architecture. Approval to explore an idea is not
approval to merge it.

### Collaboration and authorship

Use real authorship information for genuine collaboration. A co-author must
have materially contributed to the change, and the email used for attribution
must be associated with that person's GitHub account. Never add automated
tools, language models, or people who did not contribute as co-authors.

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
