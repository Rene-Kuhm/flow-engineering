# MCP and skill distribution

The hybrid distribution has three deliberately separate surfaces: deterministic
project intelligence in the core package, a narrow read-only MCP adapter, and a
portable agent workflow skill.

## Local checkout: canonical setup

From the checkout containing `pyproject.toml`, install the optional MCP extra:

```bash
uv sync --extra mcp
uv run --extra mcp flow-mcp
```

Configure an MCP client with a stdio entry that runs from that checkout:

```json
{
  "mcpServers": {
    "flow-engineering": {
      "command": "uv",
      "args": [
        "run", "--directory", "/path/to/flow-engineering",
        "--extra", "mcp", "flow-mcp"
      ]
    }
  }
}
```

The `--directory` value must point to the checkout containing
`pyproject.toml`; this keeps client startup independent of its working
directory. If a published release includes the MCP extra, installing
`flow-engineering[mcp]` from the package index is an alternative to the local
checkout, not the canonical development path.

Load `skills/flow-engineering/SKILL.md` through the agent runtime's normal
skill mechanism. The skill remains useful when MCP is unavailable.

## Responsibilities and security boundaries

| Surface | Owns | Does not own |
|---|---|---|
| Core package | Deterministic project detection, health logic, and domain APIs | Agent orchestration or transport concerns |
| MCP adapter | Transport interoperability and three bounded read-only tools: detection, allowlisted context, and health summary | Arbitrary file access, writes, project-code execution, network access, or secret exposure |
| Skill | Stack-first workflow, bounded context, verification, memory, and fail-closed behavior | Core business logic or MCP transport |

The context tool reads only the documented root allowlist and bounds file and
total output. Treat MCP input paths and returned data as untrusted; run the
server with the least filesystem access practical.
