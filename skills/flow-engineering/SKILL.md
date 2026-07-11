---
name: flow-engineering
description: Use this skill whenever Codex, MiniMax, OpenCode, or another agent works in a flow-engineering repository, mentions stack detection, SDD context, MCP project inspection, health summaries, vertical slices, verification, or fail-closed ambiguity. Apply it before proposing, editing, or verifying repository work; it keeps context bounded, preserves unrelated changes, and separates core, MCP, and skill responsibilities.
compatibility: Compatible with Codex, MiniMax, OpenCode, and other agent runtimes. The optional flow-mcp server requires the repository's mcp extra; the workflow remains usable without MCP.
---

# flow-engineering workflow

Use this skill for repository work, not as a replacement for the core package,
the MCP transport, or project-specific governance.

## Workflow

1. Identify the repository root and read `AGENTS.md` when present.
2. Detect the stack from manifests, lockfiles, runtime files, and CI before
   choosing commands. For this repository, `uv` and `uv.lock` are canonical.
3. Load only the context needed for the task. Start with
   `docs/operating-manual.md`, `docs/stack-tooling-policy.md`, and
   `docs/glossary.md`; then load relevant governance or quality-gate docs.
4. Inspect current git state. Preserve unrelated edits, backups, and secrets.
5. Choose one small vertical slice. Target no more than 400 changed lines.
6. Explain architectural tradeoffs before introducing coupling. Use public
   interfaces and protect behavior changes with tests.
7. Run the narrowest relevant tests, static checks, and health or CI checks.
8. Verify current files and command output before claiming completion.
9. Persist non-obvious decisions, discoveries, fixes, and constraints when the
   project memory system is available.

## MCP use and boundaries

- Prefer `flow-mcp` read-only tools for bounded project detection, context, and
  health summaries when the server is available.
- Convert only approved local documents, then use the separate Engram MCP to persist requested Markdown.
- Treat MCP output as execution-surface evidence, not a replacement for
  repository files, tests, current diffs, or governance.
- The core package owns deterministic project detection, health logic, and
  domain APIs. The MCP adapter owns transport interoperability and bounded
  read-only DTOs. This skill owns agent workflow, context discipline,
  verification, and safety rules.
- Do not use MCP to execute project code, write files, read arbitrary paths,
  access the network, or expose secrets. Treat paths and returned data as
  untrusted and keep filesystem access least-privilege.

## Fail closed

Stop and report the ambiguity when the stack, root, requested scope, or
security boundary cannot be established. Gather only the minimum evidence
needed; do not guess paths, read arbitrary files, or implement by assumption.

## Output contract

Return a concise report with these headings:

```text
Status: <complete | blocked | needs-input>
Scope: <files or bounded slice>
Evidence: <commands, tests, docs, or MCP observations used>
Changes: <what changed, or what is proposed>
Risks/next step: <remaining risk or explicit next action>
```

When no change was requested, report the evidence and recommendation without
editing files. When blocked, name the missing evidence and stop.

## Repository references

Use `docs/operating-manual.md` as the routing map, `docs/stack-tooling-policy.md`
for command selection, `docs/glossary.md` for project vocabulary, and the
relevant governance and quality-gate documents as the source of truth.
