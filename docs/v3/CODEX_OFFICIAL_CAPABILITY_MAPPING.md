# Codex Official Capability Mapping

> Evidence snapshot: 2026-09-08. This is a source map for the Phase 2.5
> vertical slice, not runtime logic and not a claim that this repository
> installs Codex configuration.

## Sources

The mapping was checked against the local Codex CLI (`codex-cli 0.153.4`) and
first-party documentation/source:

- [Codex customization](https://developers.openai.com/codex/concepts/customization)
- [Codex Skills](https://developers.openai.com/codex/skills)
- [Codex configuration schema at the researched source revision](https://github.com/openai/codex/blob/45305dd229c01e6cb6e122f6559e4f9b805bae6/codex-rs/core/config.schema.json)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex basic configuration](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Codex advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex sandboxing](https://learn.chatgpt.com/docs/sandboxing)
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Codex plugins](https://learn.chatgpt.com/docs/build-plugins)

The source revision recorded for reproducibility is
`45305dd229c01e6cb6e122f6559e4f9b805bae6`, the `openai/codex` main revision
inspected for this slice. URLs are evidence only; the adapter does not
hard-code them.

## Portable concept to native surface

| Portable concept | Codex native surface | Support | Phase 2 mapping |
|---|---|---|---|
| Persistent invariants and routing bootstrap | Project/user `AGENTS.md` | `NATIVE` | Projection references the small project file; it does not paste selected skill bodies into it. |
| Selected skill procedures | `.agents/skills` discovery roots and `SKILL.md` progressive disclosure | `NATIVE` | `SkillResolver` resolves only `StageRoute.selected_skills`, verifies digest/trust, and retains bodies only for selected on-demand skills. |
| MCP servers and tools | `[mcp_servers.<name>]` in trusted/user Codex config | `NATIVE` | Projection contains stage-local server references and a schema-cost field; no MCP server is installed or eagerly loaded. |
| Isolated/parallel work | `agents` configuration and subagent definitions/spawn surface | `NATIVE` | Projection can record route-required capacity; it does not implement a universal scheduler. |
| Packaged extensions | Codex plugin manifest and plugin `skills/`/hooks | `NATIVE` | Support is advertised, but no plugin is enabled without a selected declared reference. |
| Deterministic lifecycle checks | `.codex/hooks.json`, inline hooks, or plugin hooks | `NATIVE` | Hook paths are projected only when the stage grants the `hooks` capability. |
| Runtime configuration | `.codex/config.toml`, profiles, and `-c/--config` | `NATIVE` | Only verified fields are emitted: model, provider, reasoning effort, approval policy, sandbox mode, and route-required agents. |
| Filesystem/network safety | sandbox modes and approval policy | `NATIVE` (bounded) | `read` and `workspace-write` are exact native mappings. `workspace-read` is host-managed and blocked by this projection unless a separate path-enforcement boundary exists; external or destructive write is blocked. A projection cannot widen authority. |
| Model reasoning effort | `model_reasoning_effort` and native subagent settings | `NATIVE` | Model profile validates the level; observable artifacts remain the portable reasoning boundary. |
| Static prompt prefix | No universal Codex config field | `HOST_MANAGED` | Bundle metadata records the stability strategy; projection labels it host-managed. |
| Dynamic runtime context | No universal Codex config field | `HOST_MANAGED` | Stage context remains an adapter/host concern and is not invented as a Codex setting. |
| Tool-schema budget and ordering | No portable Codex setting with this contract | `HOST_MANAGED` | Bundle tracks the boundary; MCP schema loading remains lazy and stage-local. |
| Evidence gate and reroute | No native Codex equivalent | `HOST_MANAGED` | Evidence status and reroute artifacts stay in the portable bundle; Codex is not treated as the router. |
| Native skill learning/promotion | No verified canonical promotion surface for this slice | `UNSUPPORTED` | Learning proposals remain governed by the v3 core policy. |

## Pinned native config contract

The adapter validates the small set of config keys it emits against the
checked-in narrow contract at
[`fixtures/v3/codex/codex-native-config-contract.json`](../../fixtures/v3/codex/codex-native-config-contract.json).
That fixture is derived from the pinned
[`codex-rs/core/config.schema.json`](https://github.com/openai/codex/blob/45305dd229c01e6cb6e122f6559e4f9b805bae6/codex-rs/core/config.schema.json)
revision `45305dd229c01e6cb6e122f6559e4f9b805bae6`. Runtime validation does
not fetch upstream.

At this pinned source revision, `AskForApproval` accepts scalar
`on-request`, scalar `never`, or a full `granular` object. The Codex adapter
preserves the two scalar forms. It validates the native object shape but
rejects granular input as `UNSUPPORTED` because this portable adapter does
not yet have an exact mapping for every granular control; it never invents a
partial granular syntax. The pinned schema is authoritative for this
projection snapshot, so obsolete or unverified values such as `untrusted` and
`on-failure` fail closed even if a general documentation page mentions them.

The contract fixture records the source revision, native contract revision,
scope, and update process. Changing the revision requires re-checking the
first-party schema, updating the narrow subset and tests together, and
reviewing the adapter mapping.

## Permission projection fidelity

The portable permission intersection remains the authority. The Codex
projection can only narrow or exactly represent that result:

| Portable filesystem level | Codex result | Classification |
|---|---|---|
| `none` | no native sandbox projection | `BLOCKED` |
| `read` | `read-only` | `NATIVE_EXACT` |
| `workspace-read` | no projection without host path enforcement | `HOST_MANAGED` |
| `workspace-write` | `workspace-write` | `NATIVE_EXACT` |
| `external-write` | no `danger-full-access` fallback | `BLOCKED` |
| `destructive` | no `danger-full-access` fallback | `BLOCKED` |
| unknown future level | no projection | `BLOCKED` |

`danger-full-access` is never generated as a broad approximation for a
portable permission that Codex cannot represent exactly. A manifest, model,
skill, MCP declaration, or generated projection describes requirements; none
of them grants OS authority.

## Serializable boundary

The projection and `AdapterResult.to_dict()` retain selected skill IDs,
source paths, refs, digests, roles, load state, and byte metrics. Full
`SKILL.md` content is execution-local and is deliberately omitted from
normal projection, evidence, provenance, and serialized adapter results.
This protects private or licensed skill bodies while preserving enough
provenance to reproduce or invalidate a derived projection.

## Adapter boundary

`CodexAdapter` consumes a validated `StageRoute`; it does not select skills or
call a general router. `SKILLS_SELECTED` resolves and verifies only the listed
records. `NO_SKILL_NEEDED` resolves no additional skills and preserves the
explicit reason. Both paths produce a portable bundle and a validated
projection, while evidence failure produces a blocked bundle with a declared
reroute hint. Native config values are checked against the pinned narrow
contract before a projection is emitted.

The projection is an immutable data artifact for a later native execution
integration. It does not create `.codex/config.toml`, install MCP servers,
enable plugins, or grant permissions as a side effect.
