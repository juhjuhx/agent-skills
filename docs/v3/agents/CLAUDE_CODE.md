# Claude Code Native Adapter

> Status: **Phase 3D read-only boundary**. The repository now has a small
> `ClaudeAdapter`/`ClaudeNativeProjection` for the installed Claude Code
> `2.1.235` CLI. It is a host-managed benchmark boundary, not a complete
> production adapter and not a claim of successful live execution.

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

## Phase 3D bounded read-only projection

The executable projection is deliberately narrower than the universal
manifest:

- `--permission-mode dontAsk` removes prompt-bearing permission paths;
- `--tools` and `--allowed-tools` are restricted to `Read`, `Glob`, and
  `Grep` for the file-read lane;
- `--safe-mode`, `--no-session-persistence`, `--no-chrome`,
  `--strict-mcp-config`, an empty `mcpServers` object, and
  `--disable-slash-commands` isolate optional capability surfaces;
- Bash, Edit/Write, subagents, web, plugins, MCP execution, and Chrome are
  explicitly unavailable or denied;
- `shell=False`, `stdin=DEVNULL`, an isolated cwd, and an external finite
  timeout are host controls;
- the installed `2.1.235` help surface does not expose `--max-turns`, so the
  projection does not invent that flag;
- `--bare` and bypass permission modes are intentionally not used because
  they can alter authentication or authority semantics.

Canonical selected `SKILL.md` procedures are resolved by digest and loaded
only into execution-local memory when needed. The projection stores only
skill references, provenance, roles, load state, and byte counts. Claude's
native skill surface is therefore classified as `HOST_MANAGED` for this
slice: the canonical library is not copied into Claude directories, and
`safe-mode` is used for the benchmark boundary.

The installed CLI contract is pinned in
[`claude-native-contract-2.1.235.json`](../../../fixtures/v3/claude/claude-native-contract-2.1.235.json)
and validated before projection. The implementation uses the external
runtime evidence contract; it does not fetch documentation during execution.
The official surfaces used for this mapping are the [CLI reference](https://code.claude.com/docs/en/cli-usage),
[permission modes](https://code.claude.com/docs/en/permission-modes),
[tools reference](https://code.claude.com/docs/en/tools-reference), and
[authentication guide](https://code.claude.com/docs/en/authentication).

Phase 3D's first no-tool smoke reached the finite timeout without usable
output. It is recorded as compatibility evidence only; Smoke B and H03 are
gated and no Claude quality or model-effect claim is made.

## Deferred implementation

The native runtime configuration and Stage Router remain unchanged. Future
work may add a verified read-only Smoke B/H03 lane, then broader generated
Claude packaging, hook contracts, plugin manifests, permission mapping, and
cross-agent artifact tests only after evidence and source provenance justify
them. This slice does not install or mutate Claude plugins, hooks, MCP, or
global configuration.
