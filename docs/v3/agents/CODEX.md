# Codex Native Adapter

> Status: **Phase 2 vertical slice implemented**. The slice compiles validated data artifacts; it does not install Codex configuration or implement the general stage router.

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

The Phase 2 adapter receives a validated stage route, renders a data-only
Codex-native projection, resolves selected Skills, and maps MCP, Subagents,
permissions, sandbox, and reasoning effort. It returns portable status,
artifacts, evidence, and failures to the core; native execution side effects
remain outside this slice.

```text
TaskSpec
  -> Codex adapter capability check
  -> selected Skills + declared tools
  -> Codex config / permission profile
  -> native execution or subagent
  -> explicit artifacts and evidence
```

The adapter may expose Codex-specific details internally. The universal core
sees only capabilities, grants, model profile reference, and artifacts. Any
future generated configuration must include canonical source refs, adapter
version, and digest; the current slice records those in the portable bundle
and projection provenance.

The current slice makes the route-consumer portion concrete in
[`tools/v3/codex_adapter.py`](../../../tools/v3/codex_adapter.py):
[`CompiledExecutionBundle`](../../../schemas/v3/compiled-execution-bundle.schema.json)
is compiled first, then projected to
[`CodexNativeProjection`](../../../schemas/v3/codex-native-projection.schema.json).
The projection is validated data only; it does not write `.codex/config.toml`,
install MCP, enable plugins, or change permissions. See the [official surface
mapping](../CODEX_OFFICIAL_CAPABILITY_MAPPING.md) for source evidence and
support classifications.

## Deferred implementation

The current slice does not modify root `AGENTS.md` beyond the compact
bootstrap, create Codex runtime files, change permissions, or add a model ID.
It is the Phase 2 implementation target in the [Migration Plan](../MIGRATION_PLAN.md);
native execution, config generation side effects, and other runtime adapters
remain follow-up work.
