# Codex Official Capability Mapping

> Evidence snapshot: 2026-09-08. This is a source map for the Phase 2
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
| Filesystem/network safety | sandbox modes and approval policy | `NATIVE` | Effective permissions intersect TaskSpec, policy, manifest, route budget, and live runtime restrictions. A projection cannot widen them. |
| Model reasoning effort | `model_reasoning_effort` and native subagent settings | `NATIVE` | Model profile validates the level; observable artifacts remain the portable reasoning boundary. |
| Static prompt prefix | No universal Codex config field | `HOST_MANAGED` | Bundle metadata records the stability strategy; projection labels it host-managed. |
| Dynamic runtime context | No universal Codex config field | `HOST_MANAGED` | Stage context remains an adapter/host concern and is not invented as a Codex setting. |
| Tool-schema budget and ordering | No portable Codex setting with this contract | `HOST_MANAGED` | Bundle tracks the boundary; MCP schema loading remains lazy and stage-local. |
| Evidence gate and reroute | No native Codex equivalent | `HOST_MANAGED` | Evidence status and reroute artifacts stay in the portable bundle; Codex is not treated as the router. |
| Native skill learning/promotion | No verified canonical promotion surface for this slice | `UNSUPPORTED` | Learning proposals remain governed by the v3 core policy. |

## Adapter boundary

`CodexAdapter` consumes a validated `StageRoute`; it does not select skills or
call a general router. `SKILLS_SELECTED` resolves and verifies only the listed
records. `NO_SKILL_NEEDED` resolves no additional skills and preserves the
explicit reason. Both paths produce a portable bundle and a validated
projection, while evidence failure produces a blocked bundle with a declared
reroute hint.

The projection is an immutable data artifact for a later native execution
integration. It does not create `.codex/config.toml`, install MCP servers,
enable plugins, or grant permissions as a side effect.
