# OpenCode Native Adapter

> Status: **Phase 3C.2 narrow boundary implemented** for the installed
> OpenCode `1.18.25` release. This is a benchmark-safe, read-only vertical
> slice, not the complete OpenCode adapter or a production execution router.

## Boundary

The adapter consumes an already validated `StageRoute`; it does not rerun the
Stage Router, select skills, select a model, install tools, or mutate global
OpenCode configuration.

```text
TaskSpec + StageRoute
  -> existing CompiledExecutionBundle
  -> OpenCodeAdapter
  -> OpenCodeNativeProjection
  -> bounded `opencode run`
  -> sanitized LiveExecutionRecord
```

The implementation is intentionally small and lives in:

- [`tools/v3/opencode_adapter.py`](../../../tools/v3/opencode_adapter.py)
- [`tools/v3/opencode_native_contract.py`](../../../tools/v3/opencode_native_contract.py)
- [`schemas/v3/opencode-native-projection.schema.json`](../../../schemas/v3/opencode-native-projection.schema.json)
- [`fixtures/v3/opencode/opencode-native-contract-1.18.25.json`](../../../fixtures/v3/opencode/opencode-native-contract-1.18.25.json)

## Verified native surfaces

The checked-in contract is a narrow snapshot of the installed release, not a
copy of the complete OpenCode configuration schema.

| Portable concept | OpenCode 1.18.25 surface | Support | Availability |
|---|---|---|---|
| Project invariants | `AGENTS.md` | `NATIVE` | `INSTALLED` |
| Selected skill discovery | Native `skill` tool | `NATIVE` | `INSTALLED` |
| Canonical body delivery | Host resolves selected `SKILL.md` only | `HOST_MANAGED` | `INSTALLED` |
| Runtime config | `OPENCODE_CONFIG_CONTENT` | `NATIVE` | `INSTALLED` |
| Permission rules | v1 `permission` with `allow` / `ask` / `deny` | `NATIVE` | `INSTALLED` |
| Headless execution | `opencode run --pure --format json --agent plan --dir` | `NATIVE` | `INSTALLED` |
| Plugin loading | `--pure` plus `plugin: []` | `NATIVE` | `INSTALLED` |
| MCP loading | `mcp: {}` plus explicit projection deny | `NATIVE` | `INSTALLED` |
| Stable/dynamic context and evidence gate | Portable host metadata | `HOST_MANAGED` | `INSTALLED` |

The release tag `v1.18.25` resolves to commit
`cb7d8b2f5e44876ef98b661dc10590c915af3a9f`. The narrow contract records the
source files, contract revision, digest, verification method, and documentation
snapshot. Runtime execution does not fetch upstream source.

First-party evidence: [OpenCode v1.18.25 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.25),
[permissions](https://opencode.ai/docs/permissions/),
[configuration](https://opencode.ai/docs/config/), and
[skills](https://opencode.ai/docs/skills).

## Benchmark-safe read-only projection

For H03 the portable permission intersection is restricted to read-only access
inside an isolated fixture. The projection emits every known permission class:

- `read`, `list`, `glob`, and `grep` have a deny-by-default wildcard followed
  by an isolated-fixture allow;
- `.env`, `.env.*`, credential, and key patterns are explicit final denies;
- edit, bash, task/subagent, external directory, web, LSP, question, and all
  other known classes are explicit deny;
- plugin and MCP configuration are empty/denied;
- `--auto` and extra CLI arguments are rejected;
- `shell=False`, `stdin=DEVNULL`, an isolated `cwd`, and a finite timeout are
  host-enforced.

OpenCode resolves matching permission patterns in declaration order, with the
last match winning. The renderer therefore preserves the order of the
workspace allow and secret denies; it does not sort those nested rules.

This is a proof about the generated projection. A manifest, skill, model
profile, plugin, MCP declaration, or generated config cannot grant authority;
the effective result remains:

```text
TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime restrictions
```

The child environment removes inherited OpenCode config selectors before
setting `OPENCODE_CONFIG_CONTENT` and
`OPENCODE_DISABLE_PROJECT_CONFIG=true`. Provider credentials, if already
present for a local account, are execution-local and are never serialized.

## Selected-only skills

`SKILLS_SELECTED` carries only selected metadata references, source/ref,
digest, role, trust, and load state. Full bodies remain execution-local and are
not included in the projection or public adapter result. `NO_SKILL_NEEDED`
loads zero additional bodies and preserves its explicit reason. The adapter
does not copy the canonical library into OpenCode directories.

## Smoke status

The first bounded contract smoke ran in a temporary fixture with no skill
selection. The generated projection passed the no-ASK and native-contract
checks and left the fixture unchanged, but OpenCode returned a structured
`UnknownError` with no actionable cause. The result is therefore
`LIVE_LANE_BLOCKED` / `OPENCODE_RUNTIME_BLOCKED`, compatibility evidence only;
the H03 quality cell was not started. See the
[Phase 3C.2 dogfood trace](../evidence/PHASE3C2_OPENCODE_DOGFOOD_ROUTE.md) and
[runtime evidence](../evidence/MODEL_RUNTIME_EVAL_V4.md).

The old guide-only claim is retired, but this slice must not be read as proof
that OpenCode can complete H03 or as a comparison of OpenCode's model with
Codex's model.
