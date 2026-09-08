# Claude Code Native Adapter

> Status: **planned adapter guide**. Claude-native separation is documented here; no plugin, hook, or permission configuration is installed by this PR.

## Separation of concerns

| Claude Code surface | Native purpose | v3 mapping |
|---|---|---|
| `CLAUDE.md` | Persistent project context | Invariants, domain context, and stable conventions |
| Skills | Reusable procedures | Canonical `SKILL.md` content selected per stage |
| Hooks | Deterministic lifecycle enforcement | Evidence, permission, and boundary checks that must not depend on model memory |
| Subagents | Isolated, adversarial, or parallel work | Stage workers with bounded context and write sets |
| Permissions | Capability boundaries | TaskSpec grants intersected with native permissions |
| Plugins | Packaged extensions | Generated bundle of approved skills/commands/agents/hooks/MCP |

Do not treat every instruction as `CLAUDE.md` content. Persistent context, reusable procedure, deterministic enforcement, isolated work, and capability grants have different lifecycles and review requirements.

## Adapter flow

```text
TaskSpec + StageRoute
  -> render stable CLAUDE.md context references
  -> load selected Skills lazily
  -> map commands, Subagents, Hooks, Plugins, and MCP
  -> apply native Permissions
  -> select a Model Profile and reasoning effort
  -> execute
  -> return artifacts/evidence
```

Hooks may enforce a lifecycle condition, but they cannot silently change the canonical route or promote a learned skill. A Subagent may perform adversarial review or parallel read-only research; parallel writes require a declared disjoint write set.

## Context and cost

`CLAUDE.md`, selected Skills, plugin instructions, tool schemas, and subagent context have separate cost and provenance. The adapter should keep stable project context small, load only selected procedures, and record MCP/tool-schema cost in the stage envelope.

## Deferred implementation

The current runtime remains unchanged. Phase 3 in the [Migration Plan](../MIGRATION_PLAN.md) will define generated Claude Code packaging, hook contracts, plugin manifests, permission mapping, and cross-agent artifact tests.
