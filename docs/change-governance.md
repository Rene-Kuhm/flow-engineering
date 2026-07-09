# Change Governance

Use this as the lightweight operating policy for changes. It keeps work reviewable, auditable, and reversible without turning the project into paperwork.

## Definition of Done

A slice is done only when all relevant checks are true:

- The change has one clear purpose and stays inside the review budget.
- Local verification relevant to the slice passed.
- CI passed after push.
- Health visibility is current when the change touches CI, runner, release, or operations.
- Documentation changed only when it helps future operators or reviewers.
- Non-obvious decisions, bug fixes, and gotchas are saved to memory.
- Follow-ups are explicit: closed, promoted, or deliberately deferred.

## Changelog and release notes

Use `CHANGELOG.md` as the release-note source of truth.

Record entries when a change affects users, operators, security posture, release/recovery, CI, runner behavior, or AI/memory workflow. Skip purely internal refactors unless they change supportability or risk.

## ADR policy

Use ADRs for durable decisions that future agents or maintainers should not rediscover.

Create an ADR when a decision changes one of these areas:

- architecture boundaries;
- persistence or memory model;
- CI/release/security operations;
- runner topology;
- SDD workflow rules;
- public CLI behavior or compatibility guarantees.

Do not create ADRs for routine bug fixes, typo fixes, or temporary follow-ups.

## ADR format

Store ADRs in `docs/adr/` using this shape:

```markdown
# ADR NNNN: Title

## Status

Accepted | Proposed | Superseded by ADR NNNN

## Context

What forces made the decision necessary?

## Decision

What are we deciding?

## Consequences

What gets better, worse, or constrained?

## Evidence

What code, CI run, doc, incident, or user requirement proves this was grounded?
```

## SDD/OpenSpec use

Keep SDD/OpenSpec active only when it guides current work. Archived or historical specs are reference material, not automatic backlog. Promote old follow-ups only after current code, tests, and product intent confirm they still matter.
