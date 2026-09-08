# Plugin, MCP, and CLI Matrix

> Status: **native capability mapping**. This table describes adapter targets, not installed integrations.

## Runtime matrix

| Runtime | Persistent instructions | Skills / lazy loading | Commands | Subagents | Plugins / hooks | MCP / tools | Permissions / sandbox | Model / reasoning |
|---|---|---|---|---|---|---|---|---|
| Codex | `AGENTS.md` | Skills, selected on demand | native/configured | native subagents | Plugins where available | MCP | config and permission profiles | reasoning effort; profile-based model |
| Claude Code | `CLAUDE.md` | Skills, selected on demand | slash commands | isolated/parallel subagents | plugins and deterministic hooks | MCP | permissions and capability boundaries | native model/effort settings |
| OpenCode | `AGENTS.md` | native skill tool, lazy | commands | agents/subagents | plugin/config surfaces | MCP | permissions | model-per-agent configuration |
| Hermes | persistent context | persistent learned skills, `/learn`-style distillation | native CLI | long-running coordination | native extensions | MCP | declared grants | configured model profiles |
| MiMo Code | persistent project instructions | Agent Skills, on-demand | commands | primary agents/subagents | native extensions | MCP | permissions | MiMo models as profiles, not runtime identity |
| ZCode | `AGENTS.md` | skills, selected on demand | commands | subagents with overrides | plugins bundle capabilities | MCP | per-tool permissions | per-subagent model and thinking effort |
| DeepSeek Harness | assembled system prompt | plugin-provided skills/context | native/plugin CLI | agent-scoped workers | plugin-based architecture | tool registry/MCP | agent-scoped overrides | model adapter and cache-aware reasoning |

Every row must report unsupported features explicitly. “Native” means the adapter maps the concept into that runtime; it does not mean the universal core copies runtime files.

For the researched Codex row, see the [official Codex capability mapping](CODEX_OFFICIAL_CAPABILITY_MAPPING.md).

## Plugin packaging target

Where the runtime supports plugins, a generated package may bundle:

```text
Plugin
  ├── Skill
  ├── Command
  ├── Subagent
  └── MCP
```

The bundle carries canonical source refs, version/digest, license, trust state, required capabilities, permissions, and generated-config provenance. The bundle is a delivery target, not a second source tree.

## MCP cost and ordering

MCP is both a capability and a context cost. The adapter contract must account for tool-schema tokens, tool ordering, result size, latency, rate limits, and permission scope. Register only the tools required by the current stage; lazy activation is preferred. A model profile that supports tools does not grant permission to use every registered tool.

## CLI and evidence surfaces

The design recognizes native commands such as skill loaders, `/learn`, Compose workflows, and `ocr scan` / `ocr review`. The universal core records the intent, selected stage, adapter, command mapping, and evidence class. It does not assume that two CLIs with similar names have identical semantics.
