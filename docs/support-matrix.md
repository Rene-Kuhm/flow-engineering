# Support Matrix

This file defines what the project promises versus what is only expected to work. Use it before changing CI, runner setup, packaging, or platform-specific code.

## Runtime support

| Area | Supported | Evidence |
|---|---|---|
| Python | 3.12, 3.13 | GitHub Actions `tests` matrix runs both versions. |
| Minimum Python | >=3.12 | `pyproject.toml` declares `requires-python = ">=3.12"`. |
| Primary CI OS | Windows GitHub-hosted runner | `.github/workflows/test.yml` runs on `windows-latest` for pushes and pull requests. |
| Local development OS | Windows, Linux, macOS | Code is intended to be portable Python, but Linux/macOS are not currently CI-gated. |
| Runner shell | Windows PowerShell 5.1 | Workflows use `powershell -ExecutionPolicy Bypass -NoProfile`. |

## Support levels

| Level | Meaning |
|---|---|
| CI-gated | Breakage should block merge or trigger an immediate fix. |
| Supported | Maintainers intend it to work and should fix reported issues, but CI may not cover it yet. |
| Best effort | Useful when it works, but not a release promise. |

Current support level:

| Platform | Level | Notes |
|---|---|---|
| Windows + Python 3.12/3.13 | CI-gated | Primary operational environment. |
| Linux + Python 3.12/3.13 | Supported | Keep code portable; add CI before making enterprise release claims. |
| macOS + Python 3.12/3.13 | Supported | Keep code portable; add CI before making enterprise release claims. |
| Python <3.12 | Unsupported | Outside `pyproject.toml` contract. |

## Change rules

- Do not introduce Windows-only behavior in core Python modules unless documented and tested.
- Keep runner/workflow scripts PowerShell-native while the primary runner is Windows.
- If Linux/macOS behavior becomes release-critical, add CI coverage before marking it CI-gated.
- Any support-level change should update this file, README compatibility, and `docs/enterprise-readiness.md`.
