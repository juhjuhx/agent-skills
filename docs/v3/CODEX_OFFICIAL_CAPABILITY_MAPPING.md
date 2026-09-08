# Codex Official Capability Mapping

> Evidence snapshot: 2026-09-08. This is a source map for the Phase 2.6
> runtime-provenance correction, not runtime logic and not a claim that this
> repository installs Codex configuration.

## Sources

The observed local runtime is `codex-cli 0.153.4`. The installed-runtime
contract is bound to the official `rust-v0.153.4` release tag, which resolves
to commit `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`. The source snapshot used
by the earlier Phase 2.5 slice is a different upstream commit and is retained
only for explicit comparison.

First-party evidence used for this mapping:

- [Codex customization](https://developers.openai.com/codex/concepts/customization)
- [Codex Skills](https://developers.openai.com/codex/skills)
- [Codex 0.153.4 release](https://github.com/openai/codex/releases/tag/rust-v0.153.4)
- [Codex 0.153.4 configuration schema](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/config.schema.json)
- [Earlier Codex source snapshot](https://github.com/openai/codex/blob/45305dd229c01e6cb6e122f6559e4f9b805bae6/codex-rs/core/config.schema.json)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex basic configuration](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Codex advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex sandboxing](https://learn.chatgpt.com/docs/sandboxing)
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Codex plugins](https://learn.chatgpt.com/docs/build-plugins)
- [Codex schema generation notes](https://github.com/openai/codex/blob/main/codex-rs/core/src/config/schema.md)

URLs are evidence only; the adapter does not hard-code them. The exact
release/tag resolution and source digests are recorded below and in the
checked-in contract fixtures.

## Versioned contract targets

| Target | Runtime evidence | Contract source commit | Full schema digest | Support | Availability | Executable default |
|---|---|---|---|---|---|---|
| `INSTALLED_RUNTIME` | `codex-cli 0.153.4`; `rust-v0.153.4` | `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` | `sha256:692da7699367f6f4fbbd46c0021278c1311440bcebf0bcb9b836690c05e56196` | `NATIVE` | `INSTALLED` | **yes** |
| `SOURCE_SNAPSHOT` / `UPSTREAM_PREVIEW` | no installed-runtime claim | `45305dd229c01e6cb6e122f6559e4f9b805bae6` | `sha256:2e1fcf1cbb20f255c3baca2e174b4a3c954cef577a130587b8935e2d12c8ade6` | `NATIVE` | `UPSTREAM_ONLY` | no |

The complete schema digests differ. That does not by itself imply a change to
the projection contract: after resolving the relevant `$ref`/`allOf` shapes,
the six emitted fields compare as follows:

| Projected field | Release vs source snapshot |
|---|---|
| `model` | `IDENTICAL` |
| `model_provider` | `IDENTICAL` |
| `model_reasoning_effort` | `IDENTICAL` |
| `approval_policy` | `IDENTICAL` |
| `sandbox_mode` | `IDENTICAL` |
| `agents` | `IDENTICAL` |

`IDENTICAL` here means identical relevant resolved field shape, not identical
full upstream files. The release target remains the only default executable
target because field compatibility does not establish runtime provenance.

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
checked-in installed-runtime contract at
[`fixtures/v3/codex/codex-native-config-contract.json`](../../fixtures/v3/codex/codex-native-config-contract.json).
That fixture is derived from the release
[`codex-rs/core/config.schema.json`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/config.schema.json)
at `rust-v0.153.4` →
`3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`. Its `contract_digest` is the
SHA-256 of that complete upstream schema file. Runtime validation does not
fetch upstream or inspect the installed binary.

The earlier source comparison is retained at
[`fixtures/v3/codex/codex-native-config-contract-source-snapshot.json`](../../fixtures/v3/codex/codex-native-config-contract-source-snapshot.json).
It is explicitly `SOURCE_SNAPSHOT` / `UPSTREAM_ONLY`; it cannot satisfy an
`INSTALLED_RUNTIME` validation request. If the observed runtime version has no
verified release mapping, the adapter returns `RUNTIME_CONTRACT_UNVERIFIED`
instead of silently falling back to a current-main or preview contract.

At this pinned source revision, `AskForApproval` accepts scalar
`on-request`, scalar `never`, or a full `granular` object. The Codex adapter
preserves the two scalar forms. It validates the native object shape but
rejects granular input as `UNSUPPORTED` because this portable adapter does
not yet have an exact mapping for every granular control; it never invents a
partial granular syntax. The pinned schema is authoritative for this
projection snapshot, so obsolete or unverified values such as `untrusted` and
`on-failure` fail closed even if a general documentation page mentions them.

The contract fixtures record `runtime_id`, observed version, release tag and
commit when available, `contract_target`, source commit, documentation
snapshot date, full-source digest, verification method, support, availability,
source revision, native contract revision, scope, and update process. Changing
the release or source target requires re-checking the first-party schema,
updating the narrow subset and tests together, and reviewing the adapter
mapping. Support (`NATIVE`, `EMULATED`, `HOST_MANAGED`, `UNSUPPORTED`) remains
separate from availability (`INSTALLED`, `RELEASE_SUPPORTED`, `UPSTREAM_ONLY`,
`UNKNOWN`).

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
