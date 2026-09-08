# ZCode Native Adapter

> Status: **planned adapter guide**. ZCode is an agent runtime/harness; GLM is a model profile.

## Layer separation

ZCode owns the harness surfaces and may run GLM or another compatible profile. GLM does not define ZCode's skills, commands, subagents, plugins, MCP, permissions, or prompt lifecycle. The universal router negotiates both layers independently.

## Native mapping

| ZCode surface | v3 mapping |
|---|---|
| `AGENTS.md` | Small invariants and context/routing bootstrap |
| Skills | Canonical procedures loaded on demand |
| Commands | Native workflow entry points |
| Subagents | Stage workers with per-subagent overrides |
| Plugins | Native package target |
| MCP | Declared tool schemas and scopes |
| Per-subagent model | Model Profile mapping inside adapter |
| Thinking effort | Native reasoning-effort setting, recorded as metadata |
| Tool permissions | Capability grants and sandbox boundaries |

ZCode plugins may bundle:

```text
Skill + Command + Subagent + MCP
```

The generated package still references one canonical skill source and carries provenance/digest. A plugin cannot widen tool permission or promote its own content.

## Deferred implementation

The current PR does not add ZCode plugin files, GLM model IDs, subagent configuration, or MCP servers. Phase 3 will define the adapter capability advertisement and per-subagent model/effort mapping.
