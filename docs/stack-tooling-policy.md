# Stack Tooling Policy

Codex, MiniMax, OpenCode, and other agents MUST dispatch commands from the
target repository's detected stack. This repository is evidence for its own
Python workflow; it is not a default command set for every repository.

## Dispatch sequence

1. Inspect manifests, lockfiles, runtime/version files, and existing CI or task
   configuration before running install, lint, type-check, test, or build
   commands.
2. Identify the canonical package manager and toolchain from that evidence.
   Prefer the repository's checked-in lockfile and scripts over global tools or
   agent defaults.
3. Use the repository's documented, locked, and CI-tested versions when they
   exist. Do not replace a stable tested version with `latest` merely because
   a newer release exists; upgrade only as an explicit change.
4. If the stack is clear, run only its commands. Never impose this repository's
   Python/uv commands on a Next.js, Go, Java, or other stack.

## Compact detection table

| Evidence found first | Canonical dispatch (confirm scripts/CI) |
|---|---|
| `pyproject.toml` + `uv.lock` | `uv` with the checked-in dependency lock; Python versions come from `requires-python` and CI/runtime configuration; this repo uses Ruff, mypy, pytest, and coverage |
| `package.json` + `pnpm-lock.yaml` | `pnpm` scripts and the declared Node runtime |
| `package.json` + `yarn.lock` or `package-lock.json` | the matching Yarn or npm scripts and declared Node runtime |
| `go.mod` / `go.sum` | Go toolchain and repository targets, including `go test` where configured |
| `pom.xml` or `build.gradle` / `gradlew` | Maven or the checked-in Gradle wrapper and the declared Java runtime |
| Other or mixed evidence | Follow the repository's own documented entrypoint; do not guess |

## This repository's baseline

Current repository evidence is `pyproject.toml`, `uv.lock`, and CI: Python
3.12 and 3.13 are tested; `uv` is canonical; Ruff, strict mypy, pytest, and
an 80% coverage floor are configured. `uv.lock` supplies resolved tool
versions, while `pyproject.toml` ranges and agent memory do not justify
blindly installing newer releases.

## Ambiguous stack: fail closed

If manifests, lockfiles, runtime files, or CI disagree or do not identify a
canonical toolchain, STOP before changing dependencies or running guessed
commands. Report the conflicting or missing evidence, ask for one
repository-owner decision, and resume only after the stack and package
manager are explicit. A guessed command that happens to work is not evidence
of the correct toolchain.
