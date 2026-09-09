# Runtime Capability Matrix

Phase 3B records local discovery and source provenance separately from task
quality. A runtime candidate is not a production preference. `INSTALLED` means
the executable was safely observed on this machine; it does not mean that a
complete native adapter exists.

## Observed local runtimes

Probe date: `2026-09-09` (Asia/Taipei). Probes used only `command -v` and the
runtime's version command. No executable was guessed, installed, or invoked on
a repository task.

| Runtime | Availability | Observed version | Release/source provenance | Adapter status | Task model | Stage model | Subagent model | Step/call model |
|---|---|---|---|---|---|---|---|---|
| Codex | `INSTALLED` | `codex-cli 0.153.4` | `rust-v0.153.4` → `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` | `IMPLEMENTED` | `SUPPORTED` | `TASK_PINNED` | `SUPPORTED` | design-only |
| Claude Code | `INSTALLED` | `2.1.235` | release commit not resolved; [official CLI docs](https://docs.anthropic.com/en/docs/claude-code/cli-usage) | `GUIDE_ONLY` | `SUPPORTED` | `TASK_PINNED` | `UNKNOWN` | `UNKNOWN` |
| OpenCode | `INSTALLED` | `1.18.25` | release commit not resolved; [skills](https://opencode.ai/docs/skills), [agents](https://opencode.ai/docs/agents/) | `GUIDE_ONLY` | `SUPPORTED` | `UNKNOWN` | `SUPPORTED` | `UNKNOWN` |
| Hermes | `INSTALLED` | `Hermes Agent v0.20.0 (2026.8.3)` | release commit not resolved; [official repository](https://github.com/NousResearch/hermes-agent) | `GUIDE_ONLY` | `SUPPORTED` | `TASK_PINNED` | `UNKNOWN` | `UNKNOWN` |
| MiMo Code | `UNKNOWN` | not probed; no verified executable name | checked-in capability fixture only | `UNVERIFIED` | fixture only | fixture only | fixture only | unknown |
| ZCode | `UNKNOWN` | not probed; no verified executable name | checked-in capability fixture only | `UNVERIFIED` | fixture only | fixture only | fixture only | unknown |
| DeepSeek Harness | `UNKNOWN` | not probed; no verified executable name | checked-in capability fixture only | `UNVERIFIED` | fixture only | fixture only | fixture only | unknown |

The Codex release is bound to the installed version using the Phase 2.6
first-party provenance record and [official release tag](https://github.com/openai/codex/releases/tag/rust-v0.153.4).
The [Codex repository](https://github.com/openai/codex) and release source are
not queried during normal harness execution. Other installed runtimes have
version evidence but no immutable source commit in this phase; their adapter
status remains `GUIDE_ONLY`.

## Portable concept mapping

The support column describes the native/host boundary. Availability is tracked
independently in the candidate record and must not be inferred from support.

| Portable concept | Codex evidence/surface | Support | Availability in this run |
|---|---|---|---|
| persistent project instructions | `AGENTS.md` | `NATIVE` | `INSTALLED` |
| selected skills | Codex Skills surface | `NATIVE` | `INSTALLED` |
| MCP tools | Codex MCP configuration | `NATIVE` | `INSTALLED` |
| subagents | Codex specialized subagents | `NATIVE` | `INSTALLED` |
| sandbox and approvals | Codex configuration/permission boundary | `NATIVE` | `INSTALLED` |
| reasoning effort | Codex configuration | `NATIVE` | `INSTALLED` |
| immutable candidate provenance | v3 harness metadata | `HOST_MANAGED` | `INSTALLED` |
| static/dynamic context accounting | v3 harness metrics | `HOST_MANAGED` | `INSTALLED` |
| per-inference-call model switching | no verified Phase 3B execution surface | `UNSUPPORTED` | `UNKNOWN` |

The last two rows are deliberately host-managed or unsupported; they are not
invented Codex configuration fields. The runtime candidate's declarations do
not grant permissions. Effective authority still comes from the existing
TaskSpec/policy/adapter/live-runtime intersection.

## Machine-readable records

- Runtime candidates: [`fixtures/v3/model-routing/runtime-candidates.json`](../../../fixtures/v3/model-routing/runtime-candidates.json)
- Model candidates: [`fixtures/v3/model-routing/model-candidates.json`](../../../fixtures/v3/model-routing/model-candidates.json)
- Runtime schema: [`schemas/v3/runtime-candidate.schema.json`](../../../schemas/v3/runtime-candidate.schema.json)
- Model schema: [`schemas/v3/model-candidate.schema.json`](../../../schemas/v3/model-candidate.schema.json)

The model fixture records remain separate from runtime records. Their
`AVAILABLE` status means a contract fixture is available to the harness, not
that the corresponding provider endpoint was called or that quality was
measured.
