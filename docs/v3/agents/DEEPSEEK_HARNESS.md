# DeepSeek Harness Native Adapter

> Status: **planned adapter guide**. DeepSeek Harness is treated as a full plugin-based harness, not merely a DeepSeek model client.

## Harness surfaces

The adapter must account for:

- plugin-based architecture;
- system-prompt assembly;
- ordered prompt sections;
- dynamic runtime context;
- prompt variables;
- tool schemas;
- agent-scoped overrides;
- tool ordering;
- context/token cost;
- KV-cache stability.

The model adapter is one replaceable part of the harness. The universal contract must not assume that a DeepSeek model endpoint provides the harness lifecycle, tool registry, session log, or plugin semantics.

## Assembly contract

```text
stable harness identity / policy prefix
  -> ordered plugin sections
  -> strict prompt-variable interpolation
  -> dynamic stage context
  -> selected tool schemas in declared order
  -> agent-scoped overrides
  -> model profile request
```

The adapter records the assembled section order, variable names (not secret values), selected tool schemas, ordering, and token estimate. Tool ordering and prompt-section changes can alter cache shape even when semantic content is unchanged.

## Universal accounting

The universal adapter contract therefore exposes:

```yaml
context_accounting:
  static_prompt_prefix: {digest: <digest>, tokens: <estimate>}
  dynamic_runtime_context: {tokens: <estimate>, artifact_refs: []}
  tool_schema_budget: {tokens: <estimate>, tools: []}
  tool_ordering: []
  cache_stability: {strategy: stable-prefix, invalidators: []}
```

Agent-scoped overrides are explicit artifacts. They cannot silently override canonical policy, permissions, trust, or evidence requirements. Prompt variables are validated and redacted according to the task's data policy.

## Deferred implementation

No DeepSeek Harness plugin, system prompt, tool registry, model client, or cache layer is changed by this PR. Phase 3 will implement a thin adapter that maps these concerns into the portable TaskSpec, StageRoute, and Evidence contracts without copying the harness implementation.
