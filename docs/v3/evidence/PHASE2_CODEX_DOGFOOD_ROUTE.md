# Phase 2 Codex Dogfood Routing Trace

> Evidence artifact for the first Phase 2 run. This records observable route
> decisions and operational evidence only; it does not record hidden
> chain-of-thought, private reasoning, or scratchpads.

## Task

- TASK: Agent Skills Matrix v3 Phase 2 — Codex native adapter vertical slice
- START_HEAD: fb46e564c084e0b04526a782b0d07d91c5a952a4
- BRANCH: feat/v3-codex-adapter
- AGENT/RUNTIME: Codex
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0
- REGISTRY EPOCH: registry:42c3d5c
- TASKSPEC SUMMARY: implement portable execution bundle, selected-only canonical skill resolution, Codex-native projection, evidence gate, fixtures, tests, and synchronized contracts
- CLASSIFICATION: COMPLEX / HIGH risk / MEDIUM ambiguity / ARCHITECTURE-CHANGING
- REQUIRED CAPABILITIES: editing, sandbox, structured_output
- PERMISSION TARGET: workspace-write; network none for implementation
- NON-GOALS: general Stage Router, other adapters, install.sh, registry migration, MCP installation, runtime side effects
- DEEP_UNDERSTANDING: FALLBACK
- DEEP_UNDERSTANDING REASON: the installed understand workflow was selected and attempted, but its package dependency under the local skill installation was unavailable. No package was installed; bounded repository inspection, current contracts, and official Codex source evidence were used instead.

## Skill discovery and loading

The route used the current repository registry rather than remembered names. The
selected procedures were read from their canonical SKILL.md files before the
corresponding work. using-superpowers was loaded once as the task/session
authority and is resident across stages.

| Skill ID | Canonical path | SHA-256 body digest | Residency |
|---|---|---|---|
| using-superpowers | using-superpowers/SKILL.md | 1adce90aedd8b1362381f8bf8a7346966612cbde3591f74ab7e55e539fa1209a | resident GATE |
| understand | understand/SKILL.md | e82730b349a1a6a51dab7f3e9b8e19a47da3d46682c122999d3392a905c3a28a | selected; fallback recorded |
| context-engineering | pro-context-engineering/SKILL.md | f6963d98e6a9244138bc41bfe1fb0516a5d20853422830f6fe235f102f0f3ec6 | selected on demand |
| codebase-inspection | codebase-inspection/SKILL.md | 87ddc0578d9bcbc80addb34ca045e4263689873ce02b1b73e3d57275ec6315c6 | selected on demand |
| improve-codebase-architecture | improve-codebase-architecture/SKILL.md | ac2befcd188bf45bc82ab3463abb626c153fc25c382eb2f33dbcdd9964211776 | selected on demand |
| writing-plans | writing-plans/SKILL.md | ff07e2f04c08f316b2f9823000ac8f95d5584a65229d00a1a6911ff3af6ed11c | selected on demand |
| test-driven-development | test-driven-development/SKILL.md | 7dee67b4af6bdccc7a914ca34533184d64592d0f5b23aeae631538168db14994 | selected on demand |
| code-review-excellence | code-review-skill-main/SKILL.md | 0a17fe3afac4b34d823e582aee0bfebb6430246fa78d06704b1aa94eef6e4b35 | selected on demand |
| verification-before-completion | verification-before-completion/SKILL.md | ea52d15aabaf72bc6b558efe2c126f161b53961090ddcd712000273bfe8c7b6c | selected on demand |
| mcp-audit | pro-mcp-audit/SKILL.md | a7a8973d7bc50258e642ba09226c8129da945f7dc890117e57fe9411146f8932 | selected on demand |

## Stage routes

Every active stage emitted a StageRoute-shaped record. All records use the
Codex adapter and the same fixture model profile, but the skill selection is
rerun per stage. Route IDs are evidence IDs, not a router implementation.

### UNDERSTAND

- OBJECTIVE: establish source truth, scope, risks, and the smallest Phase 2 boundary.
- SKILLS CONSIDERED: using-superpowers, understand, codebase-inspection, context-engineering, verification-before-completion, brainstorming.
- SKILLS SELECTED:
  - GATE: using-superpowers — task/session authority; resident, no full reload.
  - PROCESS: understand — requested by the complexity policy; its scanner was attempted and fell back.
  - DOMAIN: codebase-inspection — inspect registry, contracts, fixtures, and branch state.
  - TOOL: context-engineering — keep the context bounded to current contracts and selected files.
  - VERIFY: verification-before-completion — define evidence before implementation.
- SKILLS REJECTED: brainstorming — the user supplied a fixed implementation scope; open-ended ideation would add no evidence.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: git status/branch/rev-parse, rg, sed, python3, understand scan attempt.
- INPUT ARTIFACTS: AGENTS.md, v3 docs, current registry, v2 policy, Phase 1 fixtures and schemas.
- OUTPUT ARTIFACTS: TaskSpec summary, classification, contract consistency findings, bounded implementation plan.
- EVIDENCE REQUIRED: source truth command output, current registry counts, explicit non-goals.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-understand
  - task_id: T-v3-phase2-codex
  - stage: understand
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), understand(PROCESS), codebase-inspection(DOMAIN), context-engineering(TOOL), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: repository truth, TaskSpec, consistency findings
- RESULT: PASS with DEEP_UNDERSTANDING FALLBACK; no source files were overwritten.

### RESEARCH

- OBJECTIVE: verify current first-party Codex surfaces before defining the native projection.
- SKILLS CONSIDERED: using-superpowers, context-engineering, codebase-inspection, verification-before-completion, mcp-audit.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident orchestration authority.
  - PROCESS: context-engineering — separate stable documentation evidence from dynamic local state.
  - DOMAIN: codebase-inspection — inspect current fixture shape and Phase 1 compatibility.
  - VERIFY: verification-before-completion — record source revision and command evidence.
- SKILLS REJECTED:
  - mcp-audit — MCP security review belongs in HARDEN after the projection exists.
  - understand — fallback already established; no second unavailable scan was useful.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: codex --version, codex --help, git ls-remote, official OpenAI documentation/source, rg, python3.
- INPUT ARTIFACTS: Phase 1 manifests, Codex fixture, local Codex CLI, current openai/codex main source.
- OUTPUT ARTIFACTS: CODEX_OFFICIAL_CAPABILITY_MAPPING.md, source revision 45305dd229c01e6cb6e122f6559e4f9b805bae6.
- EVIDENCE REQUIRED: AGENTS.md, Skills, MCP, Subagents, Plugins, Hooks, config, sandbox, approvals, reasoning effort mapped to NATIVE/HOST_MANAGED/UNSUPPORTED.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-research
  - task_id: T-v3-phase2-codex
  - stage: research
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), context-engineering(PROCESS), codebase-inspection(DOMAIN), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: first-party source links, source revision, support-level table
- RESULT: PASS; native fields were limited to researched surfaces and internal context/evidence fields were marked HOST_MANAGED.

### DESIGN

- OBJECTIVE: design the two-layer portable bundle and Codex projection without runtime-specific universal logic.
- SKILLS CONSIDERED: using-superpowers, context-engineering, improve-codebase-architecture, codebase-inspection, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - PROCESS: context-engineering — keep portable and native concerns separate.
  - DOMAIN: improve-codebase-architecture — enforce a thin data/validation boundary.
  - VERIFY: verification-before-completion — define deterministic digest and evidence invariants.
- SKILLS REJECTED:
  - codebase-inspection — prior repository survey was sufficient for this design decision.
  - extra adapter/framework skills — Phase 2 has one runtime and no general adapter framework.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: rg, sed, apply_patch, python3 schema checks.
- INPUT ARTIFACTS: Phase 1 schemas, AGENT_ADAPTER_CONTRACT.md, Model Profile and Reasoning Artifact contracts, official Codex mapping.
- OUTPUT ARTIFACTS: design in docs/superpowers/plans/2026-09-08-v3-codex-adapter.md; bundle/projection schema boundary.
- EVIDENCE REQUIRED: no Codex-specific fields in portable bundle; native support level for every projection surface.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-design
  - task_id: T-v3-phase2-codex
  - stage: design
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), context-engineering(PROCESS), improve-codebase-architecture(DOMAIN), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: boundary design, no speculative hierarchy
- RESULT: PASS; portable compilation, selected-only resolution, permission intersection, evidence gate, and thin projection were chosen.

### PLAN

- OBJECTIVE: turn the design into ordered implementation tasks with tests and explicit stop conditions.
- SKILLS CONSIDERED: using-superpowers, writing-plans, improve-codebase-architecture, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - PROCESS: writing-plans — exact paths, TDD order, and verification commands.
  - DOMAIN: improve-codebase-architecture — keep the implementation data-oriented.
  - VERIFY: verification-before-completion — define final proof commands.
- SKILLS REJECTED: context-engineering — the plan already fixes context boundaries and selected files.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: sed, rg, apply_patch.
- INPUT ARTIFACTS: design findings, Phase 1 tests, official mapping requirements.
- OUTPUT ARTIFACTS: docs/superpowers/plans/2026-09-08-v3-codex-adapter.md.
- EVIDENCE REQUIRED: failing test first, exact file list, no runtime router/installer work.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-plan
  - task_id: T-v3-phase2-codex
  - stage: plan
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), writing-plans(PROCESS), improve-codebase-architecture(DOMAIN), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: plan file and initial red test
- RESULT: PASS; the plan was written before production modules and the initial adapter test was observed failing with ModuleNotFoundError.

### IMPLEMENT

- OBJECTIVE: implement bundle schemas, selected-only resolver, permission/evidence/artifact helpers, and Codex projection.
- SKILLS CONSIDERED: using-superpowers, test-driven-development, context-engineering, code-review-excellence, verification-before-completion, improve-codebase-architecture.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - PROCESS: test-driven-development — failing test first, then smallest implementation.
  - TOOL: context-engineering — load only selected metadata and selected SKILL.md bodies.
  - REVIEW: code-review-excellence — keep review concerns in the implementation boundary.
  - VERIFY: verification-before-completion — run fresh tests and inspect generated artifacts.
- SKILLS REJECTED: improve-codebase-architecture — design boundary was already settled; using it as a second implementation framework would add no code value.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: apply_patch, python3 -B -m unittest, rg, git diff.
- INPUT ARTIFACTS: TaskSpec, StageRoute, Codex manifest, OpenAI-compatible model fixture, selected current registry metadata.
- OUTPUT ARTIFACTS: schemas/v3/compiled-execution-bundle.schema.json; schemas/v3/codex-native-projection.schema.json; tools/v3/execution_bundle.py; tools/v3/skill_resolver.py; tools/v3/permission_intersection.py; tools/v3/evidence_gate.py; tools/v3/reasoning_artifacts.py; tools/v3/codex_adapter.py; tests and fixtures.
- EVIDENCE REQUIRED: selected-only load metrics, digest/trust/capability/permission/evidence tests, deterministic bundle/projection.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-implement
  - task_id: T-v3-phase2-codex
  - stage: implement
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), test-driven-development(PROCESS), context-engineering(TOOL), code-review-excellence(REVIEW), verification-before-completion(VERIFY)
  - granted_capabilities: editing, sandbox, structured_output
  - evidence_required: tests, schema validation, diff, security review
- RESULT: PASS; selected route compiled with four metadata records, three loaded SKILL.md bodies, and one resident authority.

### REVIEW

- OBJECTIVE: independently inspect correctness, portability, trust/permission boundaries, and architecture size.
- SKILLS CONSIDERED: using-superpowers, code-review-excellence, improve-codebase-architecture, mcp-audit, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - DOMAIN: improve-codebase-architecture — inspect portable/native boundary and references.
  - REVIEW: code-review-excellence — independent code quality review.
  - TOOL: mcp-audit — inspect MCP/tool declarations and permission surfaces.
  - VERIFY: verification-before-completion — demand reproducible results.
- SKILLS REJECTED: official-code-review — it is a PR-oriented workflow and was not needed before the native CLI check; native OCR was handled separately.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: git diff, rg, python3 tests, schema validation, review checklist.
- INPUT ARTIFACTS: implementation diff, schemas, fixtures, official mapping, plan.
- OUTPUT ARTIFACTS: review findings, hardening list, independent review notes.
- EVIDENCE REQUIRED: two independent review lanes, no unsupported projection keys, no universal runtime/model branch, no speculative abstractions.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-review
  - task_id: T-v3-phase2-codex
  - stage: review
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), improve-codebase-architecture(DOMAIN), code-review-excellence(REVIEW), mcp-audit(TOOL), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: code review, security review, simplification review
- RESULT: PASS with no blocking correctness finding before final verification.

### VERIFY

- OBJECTIVE: run the full contract/adapter suite and validate generated fixtures, digests, links, and repository cleanliness.
- SKILLS CONSIDERED: using-superpowers, verification-before-completion, codebase-inspection, context-engineering.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - PROCESS: context-engineering — keep verification context scoped to changed files.
  - TOOL: codebase-inspection — inspect files changed and protected non-goals.
  - VERIFY: verification-before-completion — fresh command evidence before completion.
- SKILLS REJECTED: test-driven-development — implementation tests were already added; this stage is independent confirmation.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: python3 -B -m unittest discover -s tests -p test_*.py -v, git diff --check, Markdown link checks where available, rg secret/path scans.
- INPUT ARTIFACTS: all implementation/tests/docs/fixtures.
- OUTPUT ARTIFACTS: test report, diff-check report, link-check result, clean tree evidence.
- EVIDENCE REQUIRED: all tests pass; no changed protected files; no secrets/private paths.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-verify
  - task_id: T-v3-phase2-codex
  - stage: verify
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), context-engineering(PROCESS), codebase-inspection(TOOL), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: full suite, diff check, link/path scan
- RESULT: PASS for implementation verification; final publication state is
  recorded in the handoff after push.

### HARDEN

- OBJECTIVE: test security non-escalation, provenance/trust, untrusted declarations, and anti-bloat constraints.
- SKILLS CONSIDERED: using-superpowers, mcp-audit, code-review-excellence, improve-codebase-architecture, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - TOOL: mcp-audit — audit stage-local MCP, hooks, plugins, commands, and schema cost.
  - REVIEW: code-review-excellence — inspect untrusted paths and generated configuration.
  - DOMAIN: improve-codebase-architecture — remove speculative managers/services/factories.
  - VERIFY: verification-before-completion — rerun evidence after hardening.
- SKILLS REJECTED: test-driven-development — no new behavior was intended; existing boundary tests cover the hardening cases.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: rg, python3 security tests, diff inspection, which ocr, ocr version, ocr llm test.
- INPUT ARTIFACTS: diff, permission tests, trust tests, Codex mapping, projection fixtures.
- OUTPUT ARTIFACTS: hardening review, OCR result, anti-bloat audit.
- EVIDENCE REQUIRED: permission intersection, quarantine block, path/digest checks, OCR status, no speculative hierarchy.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-harden
  - task_id: T-v3-phase2-codex
  - stage: harden
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), mcp-audit(TOOL), improve-codebase-architecture(DOMAIN), code-review-excellence(REVIEW), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: security review, OCR, anti-bloat
- RESULT: PASS; native OCR is explicitly blocked by authentication and no
  false native review result is claimed.

### HANDOFF

- OBJECTIVE: package the portable/native artifacts, document limitations, and prepare a stacked Draft PR without merging.
- SKILLS CONSIDERED: using-superpowers, writing-plans, verification-before-completion, code-review-excellence.
- SKILLS SELECTED:
  - GATE: using-superpowers — resident authority.
  - PROCESS: writing-plans — produce a self-contained Phase 3 handoff prompt.
  - VERIFY: verification-before-completion — confirm final head, files, commits, and PR state.
- SKILLS REJECTED:
  - code-review-excellence — review conclusions belong in the review/harden records and should not be duplicated in handoff.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: apply_patch, git status/log/diff, git push, gh pr create/view.
- INPUT ARTIFACTS: verified tests, official mapping, route trace, Phase 3 prompt, clean branch.
- OUTPUT ARTIFACTS: stacked branch, Draft PR, final repository truth.
- EVIDENCE REQUIRED: clean push, PR base feat/v3-contract-schemas, draft state, no merge.
- ROUTE RECORD:
  - route_id: R-T-v3-phase2-codex-handoff
  - task_id: T-v3-phase2-codex
  - stage: handoff
  - registry_epoch: registry:42c3d5c
  - status: SKILLS_SELECTED
  - selected_skills: using-superpowers(GATE), writing-plans(PROCESS), verification-before-completion(VERIFY)
  - granted_capabilities: sandbox, structured_output
  - evidence_required: final git/PR evidence
- RESULT: PASS after the stacked branch and Draft PR are created; no merge is
  permitted in this phase.

## Context and performance evidence

The measurement used the current 214-record registry and the selected route
from this task. It did not load every body; the all-catalog body count below is
a hypothetical byte total obtained from file metadata, while the selected
figures are actual adapter measurements.

| Measurement | Result |
|---|---:|
| Registry records | 214 |
| Hypothetical all-catalog SKILL.md files present | 214 |
| Hypothetical all-catalog body bytes | 2,155,285 |
| Hypothetical all-catalog estimate at 4 bytes/token | 538,821 tokens |
| Selected metadata records inspected | 4 |
| Selected source files verified | 4 |
| Selected SKILL.md bodies loaded | 3 |
| Selected body bytes loaded | 22,911 |
| Selected estimate at 4 bytes/token | 5,728 tokens |
| First compile + projection latency | 20.766 ms |
| Median of 25 compile + projection runs | 19.557 ms |
| 25-run range | 19.333–20.766 ms |

The byte/token ratio is an estimate, not a tokenizer measurement. The result
supports selected-only loading and provenance checks; it does not claim a
production token-saving percentage.

## Independent review lanes

- ARCHITECTURE/API REVIEW: PASS — portable compilation has no Codex branch;
  CodexAdapter consumes a validated route; projection keys are allowlisted by
  the strict schema; no general router was added.
- SIMPLIFICATION REVIEW: PASS — the implementation uses data records, pure
  helpers, one resolver, one adapter, one projection function, and one evidence
  gate. No Manager, Registry, Service, Factory, Coordinator, Gateway, event
  bus, database, worker pool, or universal scheduler was added.
- SECURITY REVIEW: PASS after hardening — source paths are repository-bound,
  digests are checked, QUARANTINE is blocked, MCP/skill/model declarations do
  not grant permission, and Codex sandbox projection is capped by the
  effective filesystem envelope.
- VERIFICATION REVIEW: PENDING until the final full suite, diff check, link
  scan, and clean-tree check.

## Alibaba OpenCodeReview

- which ocr: /opt/homebrew/bin/ocr
- ocr version: open-code-review v1.11.6 (04284b5dc), darwin/arm64
- ocr llm test: authentication failed with HTTP 401 Unauthorized.
- OCR_NATIVE_DIFF: BLOCKED_BY_AUTH

No native diff pass is claimed. Delegate review, if used later, must remain a
separate OCR_DELEGATE evidence class.

## Protected-scope and secret checks

The implementation diff changes no install.sh, no
.superpowers/ROUTING_POLICY.yaml, no .superpowers/SKILLS_INDEX.json, no
categories.json, and no root AGENTS.md or README.md. No API keys, tokens,
secret configuration, or user-home paths are included in the Phase 2 artifacts.
