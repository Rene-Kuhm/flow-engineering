# Security Policy

Security work in this repository is handled as operational engineering, not as
after-the-fact cleanup. Report suspected issues privately and rotate exposed
credentials immediately.

## Supported versions

The supported branch is `main`. Security fixes are applied there first.

## Reporting a vulnerability

Do not open a public issue for secrets, token exposure, credential misuse, or
exploitable behavior.

Report privately to the repository owner with:

- affected command, workflow, script, or file path;
- reproduction steps;
- expected impact;
- whether any token, key, or credential was exposed;
- suggested mitigation, if known.

## Immediate response rules

| Finding | Required first action |
|---------|-----------------------|
| Exposed GitHub token | Revoke or rotate the token before continuing development. |
| Exposed OpenAI/OpenCode token | Revoke or rotate the token and inspect recent usage. |
| Runner credential exposure | Remove the runner registration and re-register it with a fresh token. |
| Secret committed to git | Rotate the secret, then clean history only with an explicit recovery plan. |
| CI or runner compromise suspicion | Stop the runner service and inspect recent workflow runs before restarting. |

## Security gates for changes

Require extra review for changes touching:

- secrets, tokens, environment variables, or credentials;
- GitHub Actions, runner setup, or service configuration;
- filesystem writes, shell execution, subprocesses, or path traversal surfaces;
- authentication, authorization, payments, or external API calls;
- dependency installation or tool bootstrapping.

## Local baseline

Before merging security-sensitive work:

```powershell
git status --short
uv run ruff check .
uv run mypy src tests
uv run pytest -q --basetemp .pytest_tmp
.\scripts\system_health.ps1
```

See `docs/security-baseline.md` for token rotation and review rules.
