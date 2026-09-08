# OpenCode Native Adapter

> Status: **planned adapter guide**. OpenCode-specific configuration remains outside the universal routing core.

## Native surfaces

| OpenCode surface | v3 mapping |
|---|---|
| `AGENTS.md` | Small persistent invariants and routing/context bootstrap |
| Native skill tool | Lazy loading of selected canonical Skills |
| Agents / subagents | Stage-specific workers and isolated review or research |
| Model-per-agent configuration | Adapter-side Model Profile selection |
| Permissions | Capability grants, sandbox, and external-write boundaries |
| Commands | Native entry points mapped to stage actions |
| MCP | Stage-scoped tools, schemas, latency, and context cost |

The adapter must account for MCP context cost. A tool's schema and returned context consume the stage budget even when the tool call itself is short. Use lazy, stage-scoped activation and avoid registering every tool for every task.

## Model separation

OpenCode can select different providers and models per agent. The adapter translates a portable Model Profile into that native configuration. The universal core must not keep OpenCode-specific model IDs, provider names, or config syntax in routing decisions.

```text
TaskSpec capabilities
  -> OpenCode adapter capabilities
  -> OpenCode native skill tool / agent / command
  -> model-per-agent profile mapping
  -> permissions + MCP grants
  -> evidence artifacts
```

An OpenCode subagent can be used for research, implementation, review, or verification according to the stage route. Its output is still a portable artifact, not an implicit policy update.

## Deferred implementation

No OpenCode config, MCP server, model catalog, or native command is changed by this PR. Phase 3 follows the Codex adapter and tests parity at the TaskSpec/artifact boundary.
