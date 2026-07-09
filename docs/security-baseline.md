# Security Baseline

This baseline keeps secrets, dependency drift, and runner-sensitive changes from
becoming invisible operational risk.

## Quick path

1. Never paste live tokens into chat, docs, commits, PRs, logs, or screenshots.
2. If a token is exposed, rotate it first; cleanup comes second.
3. Use environment variables or platform secret stores for credentials.
4. Treat runner, CI, filesystem, and shell-execution changes as sensitive.
5. Merge only after local verification, green CI, and a healthy runner check.

## Token rotation rules

| Secret type | Rotate when | Notes |
|-------------|-------------|-------|
| GitHub PAT | Any exposure, suspicious use, or owner change | Prefer short-lived or fine-grained tokens. |
| GitHub runner token | Any runner re-registration or compromise suspicion | Registration/removal tokens are short-lived; do not store them. |
| OpenAI key | Any exposure, usage anomaly, or team access change | Inspect provider usage after rotation. |
| OpenCode/OpenRouter key | Any exposure, billing anomaly, or machine handoff | Keep provider keys outside the repo. |
| Local `.env` values | Any machine transfer, screenshot leak, or shared terminal log | `.env` files must stay untracked. |

## Secret handling rules

- Do not commit credentials, API keys, tokens, cookies, private keys, or session
  dumps.
- Do not document real secret values; use placeholders like `<TOKEN>` or
  `REDACTED`.
- Do not paste secrets into AI chats. If it happens, revoke the secret.
- Keep `.env`, `.env.*`, local credential files, and generated runner
  credentials out of git.
- Prefer least-privilege, fine-grained tokens with expiration dates.

## Sensitive change review

Require extra review before merging changes that touch:

- `.github/workflows/**` or `.github/dependabot.yml`;
- runner installation, service configuration, or startup scripts;
- subprocess, shell, filesystem, or path-handling code;
- authentication, authorization, payment, or external API integration;
- dependency installation, lockfiles, or bootstrap scripts.

## Dependency security

Dependency maintenance is handled by Dependabot. See
`docs/dependency-updates.md`.

Routine minor/patch updates can merge after green CI. Major updates, security
updates, and runtime behavior changes need explicit review notes.

## Incident response

When security posture is uncertain, stop adding features.

| Step | Action |
|------|--------|
| 1 | Identify the exposed asset, affected path, and time window. |
| 2 | Rotate or revoke the credential before cleanup. |
| 3 | Inspect recent GitHub Actions runs, runner status, and provider usage. |
| 4 | Patch the root cause with a focused change and regression check if possible. |
| 5 | Record the finding and mitigation in memory and docs if it affects future work. |

## Verification commands

Use this baseline before merging sensitive changes:

```powershell
git status --short
uv run ruff check .
uv run ruff check --select S102,S105,S106,S107,S108,S301,S302,S303,S304,S305,S306,S307,S308,S310,S312,S313,S314,S315,S316,S317,S318,S319,S321,S323,S501,S502,S503,S504,S505,S506,S507,S508,S509,S601,S602,S604,S605,S606,S608,S609,S610,S611,S612 src scripts
uv run mypy src tests
uv run pytest -q --basetemp .pytest_tmp
.\scripts\system_health.ps1
```

The CI workflow runs the same focused Ruff security rule set. Full
`ruff --select S` remains an audit tool until existing low-signal findings are
triaged and intentionally fixed or documented.

For CI or runner changes, also inspect the latest workflow run:

```powershell
gh run list --repo Rene-Kuhm/flow-engineering --branch main --limit 5
```
