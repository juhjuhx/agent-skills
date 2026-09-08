# MiMo Code Native Adapter

> Status: **planned adapter guide**. MiMo Code and MiMo models are deliberately separate layers.

## Layer separation

- **MiMo Code** is an agent runtime with native Agent Skills, primary agents, subagents, permissions, MCP, commands, and Compose workflow.
- **MiMo models** are model/provider profiles selected through the separate [Model Profile Contract](../MODEL_PROFILE_CONTRACT.md).

The runtime may execute a non-MiMo profile when capability and policy negotiation allow it. A model name must not be used as a runtime identity test.

## Native mapping

| MiMo Code surface | v3 mapping |
|---|---|
| Agent Skills | Canonical Skills, loaded on demand |
| Primary agents | Stage owner or orchestrator adapter |
| Subagents | Isolated research, implementation, review, or verification |
| Permissions | Narrow TaskSpec and policy grants |
| MCP | Stage-scoped tools and schema budget |
| Commands | Native command mapping to stage actions |
| Compose | Native workflow surface translated to portable stage artifacts |

## Compose versus using-superpowers

Compose may describe how MiMo Code sequences native work. `using-superpowers` remains the orchestration authority for the cross-runtime lifecycle:

```text
using-superpowers: classify -> TaskSpec -> plan stages -> route per stage -> evidence gate
Compose:           native MiMo Code workflow execution within those stage contracts
```

Compose can be used by an adapter, but it does not replace stage-local routing, role slots, capability negotiation, or the evidence gate.

## Deferred implementation

No MiMo Code command, Skill, MCP, permission, or model configuration is changed here. Phase 3 will compare Compose events with the portable TaskSpec, StageRoute, and handoff artifacts.
