# NEXT CODEX PROMPT
# PHASE 3D — CLAUDE READ-ONLY EXECUTION BOUNDARY PROPOSAL

Repository:
juhjuhx/agent-skills

Current OpenCode diagnostic branch:
fix/v3-opencode-runtime-diagnostic

Current decision:
OPENCODE_RUNTIME_BLOCKED

Do not start Phase 4. Do not modify Stage Router weights. Do not implement
adaptive routing. Do not keep creating OpenCode diagnostic subphases. Do not
install runtimes, models, MCP servers, plugins, dependencies, credentials, or
new accounts. Do not broaden permissions or use bypass/auto approval.

This is a proposal only. Do not execute it in the current Phase 3C.3 run.

============================================================
0. MISSION
============================================================

Establish whether the already-installed Claude Code runtime can provide the
next trustworthy live execution configuration under a bounded read-only
boundary. The goal is a safe contract smoke and, only after it passes, one
unchanged H03 API/interface-design cell.

OpenCode remains a valid static adapter with explicit status:

OPENCODE_RUNTIME_BLOCKED
cause = PROVIDER_NOT_CONFIGURED

Do not treat Codex/OpenCode/Claude comparisons as MODEL_EFFECT. A completed
Claude cell would be a CONFIGURATION_EFFECT candidate because runtime,
provider/model, tool implementation, and system behavior may all differ.

============================================================
1. FRESH SOURCE TRUTH FIRST
============================================================

Verify before edits or execution:

- git status --short
- git branch --show-current
- git rev-parse HEAD
- installed `claude --version`
- installed `claude --help` and the exact print/headless help surface
- official release/source/documentation for the observed version

Installed behavior and versioned first-party source win over current-main
documentation. Record runtime version, release/tag/commit where available,
documentation snapshot, headless invocation, output format, tool/permission
controls, and model/effort selection granularity. Never serialize credentials.

============================================================
2. PRESERVE THE UNIVERSAL FLOW
============================================================

Consume the existing contracts without redesigning them:

TaskSpec
  -> existing Stage Router
  -> StageRoute
  -> selected skill references/bodies only
  -> CompiledExecutionBundle
  -> Claude-native projection
  -> bounded execution evidence

Claude adapter-specific fields belong only in a Claude projection. Do not put
Claude CLI/config syntax in StageRoute or the universal router. Do not change
Stage Router weights or select models in the skill router.

============================================================
3. CLAUDE READ-ONLY CONTRACT
============================================================

Research the installed version and first-party source for the actual
separation of:

- CLAUDE.md persistent context;
- Skills and selected procedure delivery;
- hooks, if available, as deterministic lifecycle controls;
- subagents, only when the TaskSpec actually requires isolation;
- permissions/tool restrictions and read-only/plan modes;
- plugins and MCP, both disabled for the H03 lane;
- model/reasoning selection, only if already configured and observable.

The target H03 authority is:

- read/list/glob/grep inside an isolated fixture: ALLOW only when explicitly
  supported by the installed contract;
- edit/write, shell/bash, task/subagent, web/network, external paths, secrets,
  plugins, and MCP: DENY;
- zero unresolved ASK paths for noninteractive execution;
- no global config mutation and no project/global capability widening;
- shell=False, stdin=DEVNULL, isolated cwd, finite timeout.

If the installed Claude contract cannot prove every reachable permission class
is ALLOW or DENY, stop with `CLAUDE_CONTRACT_BLOCKED`. Do not use interactive
approval, broad auto-approval, or a longer timeout as a workaround.

============================================================
4. DOGFOOD ROUTING
============================================================

Use using-superpowers as resident task/session authority and the existing
Stage Router. Every active development stage emits a StageRoute or
NO_SKILL_NEEDED(reason). Do not reload the whole catalog. Load only selected
skill bodies after route selection. Record unrelated selections as
ROUTING_DEFECT without changing routing weights.

============================================================
5. TWO-STEP GATE
============================================================

STEP A — contract smoke:

- temporary fixture with one harmless file;
- read one bounded value and return structured output;
- no writes, shell, network, web, plugins, MCP, or subagents;
- no raw prompt/stdout/stderr/logs/credentials in evidence;
- independent workspace digest check;
- explicit runtime/provider/model identity only when safely observable.

STEP B — H03:

Run the existing unchanged H03 only when the smoke has exit success, usable
output, no ASK path, unchanged workspace, and an independent verifier can
check the DecisionRecord/API artifact against the existing acceptance criteria.
Terminal outcome must be VERIFIED_SUCCESS, PARTIAL, FAILED, or BLOCKED.

============================================================
6. EVIDENCE BOUNDARY
============================================================

Use only these evidence classes:

REAL_EXECUTION
HOST_MANAGED_FIXTURE
MOCK

Only REAL_EXECUTION supports live quality/reliability conclusions. Keep
runtime compatibility probes separate. Record metric semantics explicitly:
PER_RUN latency; model/tool calls, tokens, and cost are null/UNKNOWN unless
the installed runtime proves their aggregation. Never infer model_calls=1
from process launch.

Record task/fixture/route/skill/permission/runtime/model/effort/instruction
digests, confounders, terminal and stage outcomes, and security evidence.

============================================================
7. SECURITY GATE
============================================================

Independently verify:

- no permission widening;
- no unresolved ASK;
- no shell=True or inherited interactive stdin;
- finite timeout and isolated cwd;
- no global config mutation;
- no .env/credential/auth/session serialization;
- no plugin/MCP auto-install or loading;
- no raw prompt/output/log persistence;
- a model/provider selector cannot grant OS authority.

If any boundary is UNKNOWN, classify the lane as blocked rather than guessing.

============================================================
8. OUTPUTS AND STOP RULE
============================================================

Create only the smallest needed Claude projection, focused tests, one
sanitized smoke record, and an evidence update. Do not build a runtime
manager, registry, scheduler, generic adapter framework, or database.

Decision options:

- `CLAUDE_SECOND_CONFIGURATION_ESTABLISHED`: smoke and independently verified
  H03 both complete;
- `CLAUDE_RUNTIME_BLOCKED`: projection is valid but provider/headless runtime
  blocks execution;
- `CLAUDE_CONTRACT_BLOCKED`: least-privilege/no-ASK boundary cannot be proved.

If Claude is blocked, make a cost/benefit decision about remaining installed
runtimes. Do not automatically return to OpenCode debugging. Do not start
Phase 4 or claim model-routing evidence from a blocked lane.
