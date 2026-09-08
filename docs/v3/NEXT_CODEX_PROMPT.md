# Next Codex Prompt — Phase 3 Cross-Runtime Adapter Expansion

Copy the prompt below into the next Codex session. It is a planning and
implementation prompt for Phase 3 only. Do not execute it during Phase 2.5.

---

## Mission

Repository: juhjuhx/agent-skills

Implement Agent Skills Matrix v3 — Phase 3: Cross-Runtime Adapter Expansion
from the hardened Phase 2.5 Codex adapter branch (or its merged base). Extend the portable contracts
to native projections for Claude Code, DeepSeek Harness, OpenCode, MiMo Code,
ZCode, and Hermes.

Do not redesign v3. Keep one canonical skill library and keep agent runtime
identity separate from model/provider identity. Do not copy the Codex adapter
six times. Every runtime requires fresh official-source research and a
runtime-specific projection that emits only verified native surfaces.

## Start and source truth

Verify without resetting local work:

    git status --short
    git branch --show-current
    git rev-parse HEAD
    git fetch origin

Start from the current hardened Phase 2 adapter branch and its stacked Phase 1
parent. Inspect the actual registry before selecting any skill ID:

- .superpowers/SKILLS_INDEX.json
- categories.json
- .superpowers/ROUTING_POLICY.yaml
- AGENTS.md

Machine-readable registry data wins over prose. Do not migrate or rewrite the
production registry, installer, or general Stage Router.

## Required contract boundary

Read the canonical v3 documents and the implemented Phase 1/2 contracts,
including:

- schemas/v3/
- tools/v3/contract_validation.py
- tools/v3/execution_bundle.py
- tools/v3/skill_resolver.py
- tools/v3/permission_intersection.py
- tools/v3/evidence_gate.py
- tools/v3/reasoning_artifacts.py
- tools/v3/codex_adapter.py
- tools/v3/codex_native_contract.py
- fixtures/v3/
- tests/v3/
- docs/v3/CODEX_OFFICIAL_CAPABILITY_MAPPING.md
- docs/v3/evidence/PHASE2_CODEX_DOGFOOD_ROUTE.md

The Codex slice establishes the two-layer boundary:

    canonical metadata + validated StageRoute
            -> CompiledExecutionBundle (portable)
            -> runtime-specific NativeProjection
            -> native surfaces + explicit artifacts/evidence

The portable bundle must remain free of runtime-specific branch logic. The
Codex adapter consumes routes; it does not choose skills or call a general
router. Preserve selected-only skill loading, provenance/digest checks,
quarantine blocking, explicit evidence gates, the resident
using-superpowers authority, and the serializable boundary that excludes raw
SKILL.md bodies.

Effective permission remains the least-privilege intersection of TaskSpec,
policy, adapter manifest, route budget, and live runtime restrictions. Models,
skills, MCP, plugins, and generated projections cannot grant OS authority.

## Dogfood requirement

Use using-superpowers as task/session authority. Run active stages such as
UNDERSTAND, RESEARCH, DESIGN, PLAN, IMPLEMENT, REVIEW, VERIFY, HARDEN, and
HANDOFF. Re-run stage-local routing independently for every active stage and
emit a StageRoute with either SKILLS_SELECTED or an explicit NO_SKILL_NEEDED
reason. Load only selected installed SKILL.md files and record the run under a
concise docs/v3/evidence/PHASE3_CROSS_RUNTIME_DOGFOOD_ROUTE.md; never record
hidden chain-of-thought. using-superpowers is resident task/session authority
and does not require full instruction reload at every stage.

## Research all six before implementation

First research all six runtimes and record official URLs, source revision/date,
verified fields, and support level (NATIVE, EMULATED, HOST_MANAGED, or
UNSUPPORTED) in a canonical mapping document. Prefer current first-party
documentation and source. Do not put documentation URLs or provider-specific
IDs into universal routing logic.

Verify separately:

- Claude Code: CLAUDE.md, Skills, Hooks, Subagents, Permissions, Plugins,
  commands, MCP, lazy loading, and model/reasoning controls. Keep persistent
  context, reusable procedures, deterministic hooks, isolated subagents,
  capability boundaries, and packaged plugins separate.
- DeepSeek Harness: plugin architecture, ordered system-prompt assembly,
  runtime context, prompt variables, tool schemas, agent-scoped overrides,
  tool ordering, context/token cost, and KV-cache stability. Treat it as a
  full harness, not merely a DeepSeek model client; do not copy its
  implementation.
- OpenCode: AGENTS.md, native skill tool, agents/subagents, model-per-agent
  configuration, permissions, commands, and MCP. Account for MCP context cost
  and keep OpenCode model IDs inside its projection/fixture.
- MiMo Code: Agent Skills, on-demand loading, primary agents, subagents,
  permissions, MCP, commands, and Compose. Compare Compose with v3 stage
  routing; do not replace using-superpowers with Compose.
- ZCode: AGENTS.md, skills, commands, subagents, plugins, MCP, per-subagent
  model, thinking effort, and tool permissions. Treat ZCode as the runtime and
  GLM as a model profile; use its plugin bundle shape only as a native packaging
  target when first-party evidence supports it.
- Hermes: persistent learned skills, /learn-style distillation, MCP,
  cross-agent import, and long-running coordination. Preserve the governed
  learning path OBSERVE -> DISTILL -> CANDIDATE -> DUPLICATE CHECK ->
  PROVENANCE -> EVAL -> REVIEW -> PROMOTION; never auto-promote unknown
  external content.

## Diversity-driven implementation waves

Do not implement all six in one undifferentiated batch. After researching all
six, use the evidence to confirm or change this default order:

1. Wave 1 — Claude Code + DeepSeek Harness. Claude exercises a conventional
   native coding-agent separation; DeepSeek Harness exercises a substantially
   different plugin and prompt-assembly architecture. Together they test
   whether the universal contract is genuinely portable.
2. Wave 2 — OpenCode + MiMo Code + ZCode. Implement only after Wave 1 exposes
   and resolves contract gaps; preserve each runtime's model, permissions, MCP,
   commands, and context distinctions.
3. Wave 3 — Hermes learning integration. Integrate its learning strengths last
   unless fresh source research demonstrates a safer ordering.

Changing the order requires an explicit decision record tied to research
evidence. The strategy is diversity-driven, not clone Codex six times.

## Adapter implementation and tests

Each adapter should consume a validated StageRoute and the existing
CompiledExecutionBundle, then produce the smallest useful native projection.
It must not implement the general router, a universal subagent scheduler, a
database, or a plugin framework. Keep helpers/data models thin.

For each runtime, test:

- valid manifest and native projection;
- runtime/model separation and no universal if agent equals or if model equals
  routing branch;
- deterministic projection for identical inputs;
- selected-only lazy loading and zero loading for NO_SKILL_NEEDED;
- digest/provenance preservation and invalidation;
- trust, quarantine, missing-skill, and capability mismatch blocking;
- permission intersection and no widening by models, skills, MCP, plugins, or
  generated output;
- MCP/tool-schema cost and lazy activation;
- observable reasoning artifacts without hidden-CoT fields;
- evidence pass/failure and explicit reroute/degradation artifacts;
- unsupported native concepts classified rather than invented;
- no unrelated skill body in generated projections;
- cross-agent projections of the same portable bundle without forking skills.

Use actual installed skills in independent architecture/code, simplification,
security, and verification lanes. Run the Alibaba OpenCodeReview precheck once.
If native authentication returns 401, record OCR_NATIVE_DIFF =
BLOCKED_BY_AUTH; do not fake a pass or relabel delegate review as native OCR.

## Non-goals

Do not move or fork existing skills. Do not rewrite install.sh or
.superpowers/ROUTING_POLICY.yaml. Do not install MCP servers, auto-import
external skills, add cloud orchestration, implement Phase 4 eval-driven
routing, or merge the PR. Do not execute Phase 3 until this prompt is the
active task.

## Deliverables

Keep commits small and semantic. Update canonical docs/v3/ only where the
implementation makes a contract precise. Produce source mapping, capability
fixtures, native projections, focused tests, dogfood evidence,
security/provenance review, context-cost evidence, and a Draft stacked PR.

At the end, generate a self-contained Phase 4 prompt only after verification.
