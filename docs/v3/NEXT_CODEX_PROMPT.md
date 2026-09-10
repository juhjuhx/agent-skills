# NEXT CODEX PROMPT
# PHASE 3E — HERMES READ-ONLY RUNTIME CANDIDATE RESEARCH

Repository:
juhjuhx/agent-skills

Current proposal base:
feat/v3-claude-readonly-adapter

Current decision:
CLAUDE_RUNTIME_BLOCKED

This is a proposal only. Do not execute it as part of Phase 3D.

============================================================
0. MISSION
============================================================

Evaluate exactly one remaining runtime candidate: the already installed
Hermes runtime, if its executable and safe headless contract can be verified.

The objective is a bounded read-only compatibility boundary, not a complete
Hermes adapter and not a model-quality comparison. Do not return to OpenCode
debugging, do not start Phase 4, do not modify Stage Router weights, and do
not implement adaptive routing.

Do not install Hermes, models, providers, MCP servers, plugins, dependencies,
credentials, or accounts. Do not modify global configuration.

============================================================
1. FRESH SOURCE TRUTH
============================================================

Before edits or execution, verify:

- repository status, branch, and HEAD;
- whether a Hermes executable is actually present;
- installed Hermes version and exact local help;
- official Hermes release/source/documentation for that version;
- authentication category without reading credential contents;
- the exact noninteractive invocation and output contract.

Do not guess an executable name or reuse current-main syntax. Installed
behavior wins over unversioned documentation. Record runtime version, release
or source revision where available, documentation snapshot, invocation
contract, model-selection granularity, permission controls, and availability.

============================================================
2. PRESERVE THE UNIVERSAL FLOW
============================================================

Use the existing contracts:

TaskSpec
  -> existing Stage Router
  -> StageRoute
  -> selected skill references/bodies only
  -> CompiledExecutionBundle
  -> Hermes-native projection only if required by evidence
  -> bounded execution evidence

Do not put Hermes CLI/config fields in TaskSpec, StageRoute, or the universal
router. Do not choose models in the Stage Router. A runtime switch remains an
explicit handoff, not an invisible stage mutation.

============================================================
3. DOGFOOD ROUTING
============================================================

Use using-superpowers as resident task/session authority and the existing
Stage Router unchanged. Every active development stage must emit a valid
StageRoute or `NO_SKILL_NEEDED(reason)`. Load only selected SKILL.md bodies
after selection. Do not load the full catalog. Record unrelated selections
as routing defects without changing weights.

============================================================
4. HERMES SAFETY GATE
============================================================

Freshly establish whether the installed Hermes contract can represent all
reachable actions as explicit ALLOW or DENY in a noninteractive run.

For the candidate read-only lane, target:

- read/list/glob/grep inside an isolated fixture: ALLOW only if proven;
- write/edit, shell, subagents, web/network, external paths, secrets,
  plugins, and MCP: DENY;
- no unresolved approval prompt or interactive input;
- shell=False, stdin=DEVNULL, isolated cwd, finite timeout;
- no credential, raw prompt, raw output, or session serialization.

If Hermes `--oneshot` or its equivalent bypasses approval controls, do not use
it for a write-capable benchmark. If the native contract cannot prove the
read-only boundary, stop with `HERMES_CONTRACT_BLOCKED` or
`HERMES_RUNTIME_BLOCKED` and do not weaken permissions.

============================================================
5. TWO-LEVEL PROBE
============================================================

Run only after the installed contract is understood:

SMOKE A — no-tool runtime/auth/output:

- exact bounded deterministic prompt;
- tools disabled where the installed contract supports this;
- no MCP/plugins/custom memory unless their absence is proven;
- usable structured output;
- finite timeout and sanitized evidence.

SMOKE B — read-only fixture:

- one harmless file in a temporary isolated workspace;
- only proven read primitives;
- no write, shell, network, browser, MCP, plugins, or subagents;
- workspace digest unchanged;
- independent verification of the returned value.

Only if both smokes pass may one unchanged H03 API/interface-design cell be
attempted. H03 is REAL_EXECUTION quality evidence only when an independent
verifier confirms the DecisionRecord/artifact and acceptance criteria.

============================================================
6. SELECTED SKILLS AND LEARNING
============================================================

Canonical skill bodies remain in this repository. Resolve selected IDs by
source/ref/digest and load only those needed for execution. Do not duplicate
the 214-skill catalog into Hermes memory or native directories.

Hermes learned skills are not trusted core truth. Do not import or promote
external learned skills. Any observation may produce a proposal only; it
cannot modify routing policy, permissions, or canonical metadata silently.

============================================================
7. PERMISSIONS AND DATA BOUNDARY
============================================================

Effective authority is:

TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live Hermes restrictions

Model/provider profiles, skill metadata, MCP declarations, and plugins cannot
grant filesystem or network authority. Unknown permissions fail closed.

Persist only sanitized IDs, digests, byte counts, versioned provenance,
structured metrics, terminal outcomes, and artifact references. Never persist
credentials, auth headers, environment contents, raw prompts, stdout/stderr,
skill bodies, or session state.

============================================================
8. EVIDENCE AND DECISION
============================================================

Use strict evidence classes:

REAL_EXECUTION
HOST_MANAGED_FIXTURE
MOCK

Only REAL_EXECUTION may support runtime quality, reliability, latency, or
terminal-quality conclusions. Record unknown model calls, tokens, and cost
as null/UNKNOWN rather than inferring them from process launch.

Create:

- `docs/v3/evidence/MODEL_RUNTIME_EVAL_V7.md`;
- `docs/v3/evidence/PHASE3E_HERMES_DOGFOOD_ROUTE.md`;
- append-only sanitized records in the established live-runs directory.

Choose exactly one:

- `HERMES_SECOND_CANDIDATE_ESTABLISHED`: both smokes and independently
  verified H03 complete;
- `HERMES_RUNTIME_BLOCKED`: static boundary is valid but runtime/provider/
  headless execution blocks;
- `HERMES_CONTRACT_BLOCKED`: least-privilege/no-ASK boundary cannot be proven.

Do not call a Hermes result MODEL_EFFECT. At most, a completed Codex/Hermes
pair is a CONFIGURATION_EFFECT candidate.

============================================================
9. TESTS AND REVIEW
============================================================

Keep all existing tests green. Add only focused tests for installed-version
binding, zero-ASK behavior, selected-only loading, permission intersection,
credential sanitization, blocked-lane evidence, and Smoke A/B gating.

Use independent runtime-contract, security, simplification, and verification
review lanes. Run the OCR auth precheck once; if it is still HTTP 401, record
`OCR_NATIVE_DIFF = BLOCKED_BY_AUTH` without retrying.

If Hermes is blocked, stop this candidate investigation and report the exact
blocker and whether further Hermes work is lower value than a future,
explicitly approved runtime boundary. Do not automatically start another
adapter.
