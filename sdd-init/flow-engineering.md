---
project: flow-engineering
schema_version: 1
strict_tdd: true
testing:
  runner: "uv run pytest"
  alias: "make test"
  framework: "pytest>=8.0.0 + pytest-bdd>=7.0.0"
conventions:
  tdd: strict (RED→GREEN→REFACTOR enforced by `flow_engineering.strict_tdd`)
  chained_pr: required when forecast >400 LOC at TDD multiplier
  spec_as_truth: openspec/changes/{name}/{spec,design,tasks}.md is contract
---

# flow-engineering sdd-init marker

Restores Article III (Strict TDD) enforcement on `main`. The marker was
lost after 2026-07-01 (never committed). When
`flow_engineering.strict_tdd.load_sdd_init(repo_root)` reads this file and
matches one of the 4 `on_markers` patterns in `strict_tdd.py:34-44`,
it returns `{"strict_tdd": True}`, which `should_enforce_strict_tdd()`
uses to enable the Strict TDD gate at `flow apply` time.

DO NOT DELETE without first running `sdd-init --refresh` (TODO: out of
scope for v1.3 — see `openspec/changes/v1.3-platform-hardening/`).

DO NOT commit secrets here.
