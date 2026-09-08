# Codex Native Adapter

> Status: **planned adapter guide**. This document maps native concepts; it does not install or implement a Codex adapter.

## Native mapping

| Codex concept | v3 responsibility |
|---|---|
| `AGENTS.md` | Small invariants, routing bootstrap, and context-loading policy |
| Skills | Canonical procedures loaded lazily by selected registry refs |
| Plugins | Packaged native extensions when available |
| Subagents | Isolated or parallel stage work with explicit write sets |
| MCP | Declared tools and schemas with stage-scoped permissions |
| Config / permission profiles | Capability and sandbox grants |
| Reasoning effort | Native execution setting; portable artifacts remain explicit |

## AGENTS.md boundary

Codex `AGENTS.md` stays small. It should contain:

1. invariants and non-negotiable safety rules;
2. the routing bootstrap: registry → task classification → TaskSpec → stages;
3. the context-loading policy: load only selected `SKILL.md` files and required references.

It must not contain hundreds of skill workflows. The canonical registry and lazy loader are the source for those procedures.

## Stage execution

The planned adapter receives a stage route, renders Codex-native instructions/configuration, selects native Skills, and maps MCP, Subagents, permissions, sandbox, and reasoning effort. It returns portable status, artifacts, evidence, and failures to the core.

```text
TaskSpec
  -> Codex adapter capability check
  -> selected Skills + declared tools
  -> Codex config / permission profile
  -> native execution or subagent
  -> explicit artifacts and evidence
```

The adapter may expose Codex-specific details internally. The universal core sees only capabilities, grants, model profile reference, and artifacts. Generated configuration must include canonical source refs, adapter version, and digest.

## Deferred implementation

The current PR does not modify root `AGENTS.md` beyond the compact bootstrap, create Codex files, change permissions, or add a model ID. Phase 2 in the [Migration Plan](../MIGRATION_PLAN.md) is the implementation target.
