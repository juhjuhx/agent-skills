# Model Profile Contract

> Status: **provider/profile contract proposal**. The universal routing core does not register or hard-code new model names in this PR.

## Separation

Agent runtimes:

`Codex`, `Claude Code`, `OpenCode`, `Hermes`, `MiMo Code`, `ZCode`, `DeepSeek Harness`.

Model/provider profiles:

`OpenAI / GPT`, `Anthropic / Claude`, `DeepSeek`, `GLM`, `MiMo`, and future providers.

An agent runtime supplies orchestration surfaces. A model profile describes an inference endpoint or local model's measured capabilities. `ZCode` is not `GLM`; `MiMo Code` is not a MiMo model; `DeepSeek Harness` is not merely a DeepSeek client.

The universal core must never contain logic such as:

```text
if model == codex
```

Capability and policy negotiation belongs in the adapter/profile boundary. Identity-specific logic belongs only inside the adapter.

## Proposed profile

```yaml
model_profile:
  id: provider/model@immutable-ref
  provider: <provider-id>
  model: <provider-model-id>
  adapter_protocol: <native-or-compatible-protocol>
  capabilities:
    text: true
    multimodal: false
    tools: true
    structured_output: true
    streaming: true
    reasoning_effort: [low, medium, high]
    code_editing: measured
    long_context: measured
  limits:
    context_tokens: <number-or-unknown>
    max_output_tokens: <number-or-unknown>
    max_tool_schema_tokens: <number-or-unknown>
    max_parallel_requests: <number-or-unknown>
  economics:
    input_cost: <measured-or-unknown>
    output_cost: <measured-or-unknown>
    cache_behavior: <measured-or-unknown>
  reliability:
    tool_success_rate: <measurement>
    structured_output_rate: <measurement>
    latency_p50: <measurement>
    latency_p95: <measurement>
    last_probe: <timestamp>
  data_policy:
    region: <declared-or-unknown>
    retention: <declared-or-unknown>
    training_use: <declared-or-unknown>
```

## Negotiation order

1. Filter profiles that cannot satisfy hard input/output, tool, context, data, or permission requirements.
2. Prefer measured capability over provider marketing text.
3. Select reasoning effort within the stage budget; effort is not a substitute for evidence.
4. Keep provider fallback within the same policy, data, permission, and acceptance envelope.
5. Record the profile, adapter, probe epoch, cost, and any fallback in the stage artifact.

The model profile never receives authority to install a skill, widen a sandbox, add an MCP server, or mark a task complete.

## Cost and context

The profile exposes both prompt cost and tool-schema cost. A route can fail a budget check because MCP schemas, tool ordering, dynamic context, or long artifacts consume the context window even when the skill text itself is small. Static adapter prefix, dynamic stage context, tool schemas, and cache stability are tracked separately.

## Runtime/profile matrix

| Runtime | Possible profile families | Contract boundary |
|---|---|---|
| Codex | OpenAI/GPT and compatible providers | Codex adapter negotiates tools, sandbox, effort |
| Claude Code | Anthropic/Claude and compatible providers | Claude adapter maps permissions, hooks, plugins |
| OpenCode | Configured provider profiles | OpenCode adapter maps per-agent model config |
| Hermes | Configured provider profiles | Hermes adapter maps learning and long-running state |
| MiMo Code | MiMo and future profiles | Runtime and model remain separate |
| ZCode | GLM and future profiles | ZCode adapter maps per-subagent model/effort |
| DeepSeek Harness | DeepSeek and compatible profiles | Harness adapter maps prompt/tool/cache contracts |

The table is a design target, not a claim that every integration is installed or supported today.
