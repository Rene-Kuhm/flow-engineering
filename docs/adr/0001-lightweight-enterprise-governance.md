# ADR 0001: Keep Enterprise Governance Lightweight and Evidence-Based

## Status

Accepted

## Context

The project is being matured toward enterprise readiness, but the repo already has significant SDD and documentation surface area. Adding heavy process would make future agents slower and increase the risk of stale instructions.

## Decision

Governance stays lightweight and evidence-based:

- `docs/enterprise-readiness.md` tracks enterprise gaps.
- `docs/change-governance.md` defines Definition of Done, changelog/release-note rules, ADR triggers, and SDD/OpenSpec hygiene.
- `CHANGELOG.md` is the release-note source of truth.
- ADRs are reserved for durable decisions, not routine fixes.

## Consequences

This gives future maintainers an audit trail without making every slice bureaucratic. The tradeoff is that maintainers must still exercise judgment: not every decision deserves an ADR, and not every commit deserves a changelog entry.

## Evidence

- User direction: keep slices small and professional; avoid bureaucracy.
- CI evidence: `tests` run `28992758186` passed on `main` before this ADR work began.
- Operational evidence: `health-monitor` run `28992222994` passed on `main`.
