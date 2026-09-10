# Model / Runtime Evaluation V6 — Claude Code Phase 3D

Phase 3D adds the first Claude-native read-only adapter boundary. It does
not change Stage Router weights, implement another runtime adapter, start
Phase 4, or make a model-quality claim.

## Decision

**CLAUDE_RUNTIME_BLOCKED**

The Claude projection and no-ASK permission boundary validate statically for
the installed CLI contract. The corrected no-tool Smoke A then reached its
finite 25-second timeout with no stdout or stderr. Because Smoke A is the
authentication/runtime/output gate, Smoke B and H03 were correctly not run.
The blocker is classified as `TIMEOUT_UNKNOWN`; no cause is inferred from a
silent timeout.

This result is not evidence that Claude, Anthropic, or any model is inferior.
No Claude quality cell completed, so there is no configuration-effect result
and no model-effect result.

## Repo truth

| Field | Value |
|---|---|
| Starting base | `fix/v3-opencode-runtime-diagnostic` |
| Starting HEAD | `6988c778d634630df2cabf236ab14fc6ca74689f` |
| Branch | `feat/v3-claude-readonly-adapter` |
| Stage Router | unchanged |
| H03 | not run; Smoke A gate failed |
| Phase decision | `CLAUDE_RUNTIME_BLOCKED` |
| Quality evidence | none |

## Installed provenance

Fresh local probes observed:

| Field | Verified value |
|---|---|
| runtime_id | `claude-code` |
| observed version | `2.1.235 (Claude Code)` |
| installed path | local-user installation; exact private path not persisted |
| immutable source commit | unavailable from the proprietary installed CLI |
| native contract revision | `claude-cli-help@2.1.235` |
| contract target | `INSTALLED_RUNTIME` |
| contract digest | `sha256:8d25516eaed8a4ad0a746efaf97de3b36e85e735ae6ba188651dc1305b6a00c5` |
| version/help probe | exit 0 |
| auth status probe | exit 0; top-level shape only; no credential values read |
| safe authentication category | `UNKNOWN` |

The exact installed native contract is checked in at
[`claude-native-contract-2.1.235.json`](../../../fixtures/v3/claude/claude-native-contract-2.1.235.json).
The snapshot records that Claude Code is proprietary and exposes no
immutable source revision through the local binary/version surface.

First-party sources used for the mapping are the [CLI reference](https://code.claude.com/docs/en/cli-usage),
[permission modes](https://code.claude.com/docs/en/permission-modes),
[tools reference](https://code.claude.com/docs/en/tools-reference),
[authentication](https://code.claude.com/docs/en/authentication),
[settings](https://code.claude.com/docs/en/settings), and
[sub-agents](https://code.claude.com/docs/en/sub-agents).

## Headless contract mapping

Support and availability are separate. `NATIVE` means the installed CLI
surface exists; `HOST_MANAGED` means the universal boundary is enforced by
the adapter/process rather than claimed as a Claude field.

| Portable concept | Claude native surface | Support | Availability / use |
|---|---|---|---|
| persistent project context | `CLAUDE.md` | `NATIVE` | installed, disabled for benchmark by `--safe-mode` |
| reusable skills | Claude Skills | `NATIVE` | installed, selected canonical bodies host-managed for this slice |
| selected procedure delivery | `--append-system-prompt` | `HOST_MANAGED` | execution-local only; no native skill directory is populated |
| deterministic lifecycle hooks | Hooks | `NATIVE` | installed, disabled; no hook added |
| isolated/parallel work | Subagents / Agent | `NATIVE` | installed, denied for H03 |
| packaged extensions | Plugins | `NATIVE` | installed, no plugin loaded or installed |
| external tools | MCP / `--mcp-config` | `NATIVE` | installed, strict empty `{"mcpServers":{}}`; execution denied |
| no prompt-bearing permission path | `--permission-mode dontAsk` | `NATIVE` | installed, required |
| available tools | `--tools` | `NATIVE` | installed, `Read,Glob,Grep` only for Smoke B |
| approval allowlist | `--allowed-tools` | `NATIVE` | installed, same read-only list |
| structured output | `--output-format json` | `NATIVE` | installed, required |
| optional customization isolation | `--safe-mode` | `NATIVE` | installed, required |
| session isolation | `--no-session-persistence` | `NATIVE` | installed, required |
| Chrome | `--no-chrome` | `NATIVE` | installed, disabled |
| model selection | `--model` | `NATIVE` | installed, intentionally not selected |
| effort control | `--effort` | `NATIVE` | installed, not varied |
| static/dynamic context envelope | adapter metadata | `HOST_MANAGED` | not emitted as invented Claude config fields |
| `--max-turns` | no installed help surface | `UNSUPPORTED` | omitted; external finite timeout remains |

`--settings` and `--setting-sources` were present in installed help but were
not used. The boundary preserves authentication state without importing
arbitrary permission, plugin, hook, or MCP configuration. `--bare` was not
used because the installed help states that it skips keychain/OAuth and
changes customization/auth behavior.

## Permission strategy

The effective authority remains:

```text
TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime restrictions
```

The adapter accepts only `none`, `read`, or `workspace-read` for this
projection. `none` is `NATIVE_EXACT`; read scopes are `HOST_MANAGED` because
the isolated cwd/path boundary is enforced outside the Claude permission
names. Every other portable filesystem level blocks rather than mapping to a
broader native mode.

The projection requires `dontAsk`, explicitly supplies the read-only tool
surface, denies Edit/Write/Bash/Agent/AskUserQuestion/Web/MCP/plugins/Chrome,
and records a resolved ALLOW/DENY result for every listed control. It never
uses `plan`, `auto`, `bypassPermissions`, `--bare`, or
`--dangerously-skip-permissions`.

Model profiles, skill metadata, MCP declarations, and plugin declarations are
not inputs to the permission intersection and cannot widen it.

## Selected-only skills and serialization

`ClaudeAdapter` consumes a validated StageRoute and resolves only the
selected metadata records. Canonical bodies are loaded only into an
execution-local tuple when `execute()` is explicitly called. The projection,
`ClaudeAdapterResult.to_dict()`, and live evidence retain only ID, source/ref,
digest, role, trust, load state, and byte counts. Raw skill bodies, prompts,
stdout, stderr, environment, session state, and credentials are not
serialized.

`NO_SKILL_NEEDED` resolves zero bodies and preserves its reason. The adapter
does not invoke the Stage Router and does not select models or extra skills.

## Smoke gates and H03

### Conformance corrections before the final smoke

The installed `2.1.235` help did not expose `--max-turns`; the projection
was corrected to omit that flag. The empty MCP value was corrected from `{}`
to the CLI-accepted empty server object `{"mcpServers":{}}`. These changes
were validated by the checked-in installed contract and focused tests.

### Smoke A

The final corrected probe was a no-tool, isolated, noninteractive command:

```text
claude -p <prompt>
--output-format json
--permission-mode dontAsk
--tools ""
--allowed-tools ""
--safe-mode
--no-session-persistence
--no-chrome
--strict-mcp-config
--mcp-config {"mcpServers":{}}
--disable-slash-commands
--max-budget-usd 0.25
```

Process controls were `shell=False`, `stdin=DEVNULL`, isolated temporary
cwd, and a finite 25-second timeout. Result: launched, timed out at
`25016.1 ms`, stdout `0` bytes, stderr `0` bytes, output format unknown.
The result is a compatibility/runtime blocker only. No identical retry was
made.

The sanitized append-only record is
[`live-claude-smoke-a-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-claude-smoke-a-001.json).

### Smoke B and H03

Smoke B was not eligible because Smoke A failed. H03 was not run. There is
therefore no Claude DecisionRecord, no independent H03 verification, no
terminal quality outcome, and no Claude/Codex configuration-effect result.

## Metrics

| Metric | Value | Semantics |
|---|---:|---|
| process wall time | `25016.1 ms` | observed host `PER_RUN` timer |
| model calls | `null` | `UNKNOWN`; launch is not a model-call count |
| tool calls | `null` | `UNKNOWN`; no usable runtime output |
| tokens | `null` | `UNKNOWN`; no installed-version usage output |
| cost | `null` | `UNKNOWN`; no billing value exposed |
| quality | not measured | Smoke A is not a quality task |

The adapter has no model/effort selection in this run. No `MODEL_EFFECT`,
`REASONING_EFFORT_EFFECT`, or Pareto quality point is emitted.

## Security review

Static projection and serialization tests verify:

- no unresolved ASK action;
- no write, shell, browser, web, subagent, plugin, or MCP authority;
- no external directory or secret-path grant;
- model/skill/MCP/plugin declarations cannot grant permission;
- explicit argv, `shell=False`, `stdin=DEVNULL`, finite timeout, isolated cwd;
- no `--auto`, bypass mode, `--bare`, or global Claude configuration mutation;
- raw prompt, output, logs, skill bodies, environment, and credentials are
  excluded from public results.

Runtime process success was not used as a safety proof; the silent timeout is
retained as `TIMEOUT_UNKNOWN`.

## Routing defects observed

The dogfood route recorded unrelated `brandkit` and `llm-council` selections,
and an `understand` knowledge-graph procedure that was not needed. None was
loaded or executed, and Stage Router weights remain unchanged. See
[`PHASE3D_CLAUDE_DOGFOOD_ROUTE.md`](PHASE3D_CLAUDE_DOGFOOD_ROUTE.md).

## Runtime candidate cost/benefit after Claude blockage

| Candidate | Verified state | Evidence value | Cost / blocker |
|---|---|---|---|
| Codex | installed, native adapter, prior real lane | high; existing execution baseline | already available; no new adapter needed |
| OpenCode | static adapter valid; live provider `anthropic` not configured | medium if a provider is supplied | do not revisit in this phase; provider/auth boundary is external |
| Claude Code | installed; static projection valid; Smoke A timeout | potentially high, but currently unverified | further diagnosis is low-value after this dedicated stop |
| Hermes | previously observed installed candidate, adapter guide only | medium; different learning/runtime architecture | requires fresh safe headless research; no adapter implemented here |
| MiMo Code | executable availability not verified | unknown | no safe lane or provenance |

The single next candidate proposed is **Hermes read-only contract research**,
not a Hermes adapter implementation. It is chosen because it is the only
remaining observed candidate that can test a materially different harness
boundary without returning to the blocked OpenCode lane; the next prompt
must stop if its approval/auth/tool boundary cannot be proved.

## Review status

- contract/code review: static projection and installed-field conformance pass;
- security/hardening: zero-ASK and no-widening checks pass statically;
- simplification: one adapter, one native contract validator, pure projection,
  no manager/registry/service hierarchy;
- verification: focused Claude tests pass; full repository verification is
  recorded with the delivery commit;
- OCR: one auth precheck is recorded in the delivery summary; if it remains
  unauthenticated, native OCR is `BLOCKED_BY_AUTH`.
