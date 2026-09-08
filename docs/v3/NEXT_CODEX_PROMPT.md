# Next Codex Prompt — Phase 3 Cross-Runtime Adapter Expansion

Copy the prompt below into the next Codex session. It is self-contained and must be executed only after the Phase 2 Codex vertical slice is available.

---

## Mission

Repository: juhjuhx/agent-skills

Implement AGENT SKILLS MATRIX v3 — PHASE 3: CROSS-RUNTIME ADAPTER EXPANSION. Expand the portable contracts to native adapter projections for Claude Code, OpenCode, Hermes, MiMo Code, ZCode, and DeepSeek Harness.

Do not redesign v3. Do not copy the Codex adapter six times. Each runtime requires fresh first-party source research and an adapter-specific projection that maps only real native surfaces. Keep one canonical skill library and keep agent runtime identity separate from model/provider identity.

## Start and source truth

Start by verifying, without resetting local work:

git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin

Base the implementation on the current Phase 2 branch/head and its stacked Phase 1 parent. Inspect the actual repository registry before selecting any skill ID:

- .superpowers/SKILLS_INDEX.json
- categories.json
- .superpowers/ROUTING_POLICY.yaml
- AGENTS.md

Machine-readable registry data wins over prose. Do not migrate or rewrite the production registry in this phase.

## Required reading

Read AGENTS.md, then the canonical v3 documents:

- docs/v3/README.md
- docs/v3/ARCHITECTURE.md
- docs/v3/USING_SUPERPOWERS.md
- docs/v3/STAGE_ROUTER.md
- docs/v3/SKILL_METADATA_AND_GRAPH.md
- docs/v3/AGENT_ADAPTER_CONTRACT.md
- docs/v3/MODEL_PROFILE_CONTRACT.md
- docs/v3/REASONING_ARTIFACTS.md
- docs/v3/LEARNING_AND_EVALS.md
- docs/v3/SECURITY_AND_PROVENANCE.md
- docs/v3/REVIEW_PIPELINE.md
- docs/v3/PHASE1_MACHINE_READABLE_CONTRACTS.md
- docs/v3/CODEX_OFFICIAL_CAPABILITY_MAPPING.md
- docs/v3/NEXT_CODEX_PROMPT.md (this file)

Inspect the implemented Phase 2 boundary before changing anything:

- schemas/v3/task-spec.schema.json
- schemas/v3/skill-metadata-v3.schema.json
- schemas/v3/agent-adapter-manifest.schema.json
- schemas/v3/model-profile.schema.json
- schemas/v3/stage-route.schema.json
- schemas/v3/compiled-execution-bundle.schema.json
- schemas/v3/codex-native-projection.schema.json
- tools/v3/contract_validation.py
- tools/v3/execution_bundle.py
- tools/v3/skill_resolver.py
- tools/v3/permission_intersection.py
- tools/v3/evidence_gate.py
- tools/v3/reasoning_artifacts.py
- tools/v3/codex_adapter.py
- tests/v3/test_contracts.py
- tests/v3/test_codex_adapter.py
- fixtures/v3/agents/
- fixtures/v3/models/
- fixtures/v3/routes/
- fixtures/v3/bundles/
- fixtures/v3/projections/
- docs/v3/evidence/PHASE2_CODEX_DOGFOOD_ROUTE.md

## Dogfood requirement

Use using-superpowers as the task/session authority again. Create active stages such as UNDERSTAND, RESEARCH, DESIGN, PLAN, IMPLEMENT, REVIEW, VERIFY, HARDEN, and HANDOFF. Re-run stage-local routing independently at every active stage and emit a StageRoute record with either SKILLS_SELECTED or an explicit NO_SKILL_NEEDED reason. Load only the selected installed SKILL.md files; do not load the whole catalog. Record the run under a concise docs/v3/evidence/PHASE3_CROSS_RUNTIME_DOGFOOD_ROUTE.md without hidden chain-of-thought.

Treat using-superpowers as resident task/session authority. A stage may list it in the GATE slot without reloading its full body.

## Fresh official-source research is mandatory

For each runtime, research current official documentation and current official source before implementing its projection. Record source URLs, revision/date, verified fields, and support level (NATIVE, EMULATED, HOST_MANAGED, or UNSUPPORTED) in a new canonical mapping document. Do not rely on memory, stale blog posts, or Codex assumptions. Do not put documentation URLs into runtime logic.

Research these native surfaces separately:

### Claude Code

Verify CLAUDE.md, Skills, Hooks, Subagents, Permissions, Plugins, commands, MCP, lazy loading, and model/reasoning controls. Preserve the separation:

- CLAUDE.md is persistent project context.
- Skills are reusable procedures.
- Hooks are deterministic lifecycle enforcement.
- Subagents are isolated/adversarial/parallel work.
- Permissions are capability boundaries.
- Plugins package extensions.

Do not turn every instruction into CLAUDE.md content.

### OpenCode

Verify AGENTS.md, the native skill tool, agents/subagents, model-per-agent configuration, permissions, commands, and MCP. Measure or account for MCP context cost. Keep OpenCode-specific model IDs inside the OpenCode projection/fixture only, never in universal routing logic.

### Hermes

Verify the current Hermes source for persistent learned skills, /learn-style distillation, MCP, cross-agent import, and long-running coordination. Preserve the learning donor boundary:

OBSERVE -> DISTILL -> CANDIDATE -> DUPLICATE CHECK -> PROVENANCE -> EVAL -> REVIEW -> PROMOTION

Do not duplicate Hermes memory or auto-promote unknown external skills.

### MiMo Code

Verify Agent Skills, on-demand loading, primary agents, subagents, permissions, MCP, commands, and Compose workflow. Keep MiMo Code as the runtime and MiMo models as model profiles. Compare Compose with using-superpowers stage routing; do not replace Superpowers with Compose.

### ZCode

Verify AGENTS.md, skills, commands, subagents, plugins, MCP, per-subagent model, thinking effort, and tool permissions. Keep ZCode as runtime and GLM as model profile. Treat a ZCode plugin that bundles Skill, Command, Subagent, and MCP as a native packaging target.

### DeepSeek Harness

Verify the harness as a full plugin-based agent runtime, not merely a DeepSeek model client. Research system-prompt assembly, ordered prompt sections, runtime context, prompt variables, tool schemas, agent-scoped overrides, tool ordering, context/token cost, and KV-cache stability. Extend the portable adapter contract only where the evidence supports it; do not copy the implementation directly.

## Implementation boundary

Use the existing runtime-neutral CompiledExecutionBundle as the input to each adapter. Each adapter must consume a validated StageRoute; it must not call a general router or select skills. For every runtime, implement only the smallest useful data/projection boundary:

canonical SkillMetadataV3
  -> validated StageRoute
  -> CompiledExecutionBundle
  -> runtime-specific NativeProjection
  -> native surface references/config data
  -> explicit artifacts and evidence

Selected-only loading, trust checks, source/ref/digest provenance, and the resident using-superpowers rule must remain intact. NO_SKILL_NEEDED must load zero additional skills and preserve its reason. A changed canonical digest must invalidate the derived projection.

Effective permission remains the least-privilege intersection of TaskSpec, policy, adapter manifest, route budget, and live runtime/sandbox restrictions. Model profiles, skills, MCP declarations, plugins, and generated projections cannot grant OS permissions.

The portable bundle must remain free of runtime-specific branch logic. Runtime identity belongs in the adapter projection only. Model profiles must remain separate records for OpenAI-compatible, Anthropic-compatible, DeepSeek, GLM, MiMo, and future providers.

## Fixtures and tests

Add capability fixtures for all six runtimes and separate representative model fixtures. These are not production integrations. Add native projection schemas or a small shared projection contract only when justified by the existing boundary; do not create a framework hierarchy.

Tests must keep all Phase 1 and Phase 2 tests green and cover, for every adapter:

- valid manifest and native projection;
- runtime/model separation;
- deterministic projection for identical inputs;
- selected-only skill loading and no-skill loading;
- digest/provenance preservation and invalidation;
- trust/quarantine/missing-skill blocking;
- capability negotiation and unknown capability handling;
- permission intersection and non-escalation;
- MCP/tool-schema context cost and lazy activation;
- explicit observable reasoning artifacts with no hidden-CoT fields;
- evidence gate pass/failure and reroute/degradation artifact;
- unsupported native concepts are explicitly classified, never invented;
- no universal branch on agent == ... or model == ...;
- no unrelated skill body appears in a generated projection.

Add cross-agent fixtures/tests demonstrating the same portable bundle can be projected differently without forking canonical skills. Add regression, security, context-efficiency, and cross-agent handoff cases where evidence supports them.

## Review and security gates

Use actual installed review/security/simplification/verification skills in independent lanes. Inspect every new Manager, Registry, Service, Factory, Coordinator, Gateway, or framework abstraction and remove speculative layers. Schemas, data validation, small helpers, and thin projections are preferred.

Audit untrusted metadata, plugin/MCP declarations, scripts/hooks, external commands, network permissions, path traversal, prompt injection, tool-schema cost, and generated configuration. Schemas describe permissions; they never grant them. Unknown external skills/plugins/MCP remain quarantined until provenance, license, evaluation, security review, and human/policy approval.

Run Alibaba OpenCodeReview checks once:

which ocr
ocr version
ocr llm test

If native authentication returns 401, record OCR_NATIVE_DIFF = BLOCKED_BY_AUTH; do not fake a pass or relabel delegate review as native OCR.

## Non-goals

Do not move or fork the existing skills. Do not rewrite install.sh or .superpowers/ROUTING_POLICY.yaml. Do not implement the general Stage Router, database, cloud orchestration, MCP installation, automatic external import, or universal model list. Do not replace using-superpowers with a runtime's workflow feature. Do not execute Phase 4 eval-driven routing.

## Deliverables and handoff

Create a stacked branch from the current Phase 2 implementation. Keep commits small and semantic. Update canonical docs/v3/ only where implementation makes a contract precise. Create a new next prompt for Phase 4 only after verification. Do not merge the PR.

The final response must report repository truth, dogfood stages and selected skills, each runtime's official mapping and source evidence, tests, performance or context evidence, security/OCR/independent reviews, anti-bloat audit, files, commits, draft PR, next prompt path, and remaining blockers.
