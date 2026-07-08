# Dependency Updates

Dependabot is enabled to keep supply-chain maintenance visible and reviewable.

## What Dependabot watches

| Ecosystem | Directory | Schedule | PR volume control |
|-----------|-----------|----------|-------------------|
| GitHub Actions | `/` | Weekly, Monday 09:00 America/New_York | Max 3 open PRs, grouped minor/patch updates |
| uv / Python | `/` | Weekly, Monday 09:30 America/New_York | Max 3 open PRs, grouped minor/patch updates |

## Review rules

- Treat security updates as priority work.
- Keep minor/patch grouped updates small and CI-driven.
- Review major updates separately; do not batch risky majors with routine updates.
- Do not merge a dependency PR unless CI is green.
- If a dependency PR changes runtime behavior, add or update tests before merging.

## Why this is enterprise-critical

Manual dependency checks get forgotten. Dependabot turns dependency drift into visible, reviewable pull requests while preserving the project's small-slice discipline.
