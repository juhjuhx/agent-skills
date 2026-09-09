# Phase 3B Model/Runtime Evaluation Dogfood Route

This is the first dogfood trace for the runtime/model evaluation harness. It
records explicit route artifacts and operational evidence only; it contains no
hidden chain-of-thought, private scratchpad, or model preference.

## TaskSpec summary

- TASK: Agent Skills Matrix v3 Phase 3B — Runtime and Model Routing Evaluation Harness
- START_HEAD: `bd5ecfdace6b78fe4b105020c19018d8c8280984`
- BRANCH: `feat/v3-model-routing-eval`
- TASK TYPE: `implementation`
- COMPLEXITY: `COMPLEX`
- RISK: `HIGH` — cross-runtime contract, permissions, evidence provenance
- AMBIGUITY: `MEDIUM` — local executable availability and native granularity require source checks
- REQUIRED OUTPUTS: evaluation schemas, pure eligibility/baseline helpers, development/holdout fixtures, evidence docs, tests
- STOP CONDITIONS: no Stage Router weight changes, no adaptive policy, no new adapter, no runtime/model installation, no MCP installation
- DEEP_UNDERSTANDING: `UNAVAILABLE` — no `deep-understanding` record exists in the supplied canonical registry; this was recorded as a capability gap rather than invented or silently substituted
- RESIDENT AUTHORITY: `using-superpowers` at task/session scope; its full body was not reloaded for each stage

## Stage routes

### UNDERSTAND

- STAGE: `understand`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: establish source truth and preserve the runtime/model boundary.
- SKILLS CONSIDERED: `using-superpowers`, `module-map`, `brooks-audit`, `improve-codebase-architecture`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers` (resident); PROCESS=`module-map`; DOMAIN=`brooks-audit`; REVIEW=`improve-codebase-architecture`
- WHY SELECTED: repository map, architecture boundary, and current evidence are required before adding contracts.
- SKILLS REJECTED: `verification-before-completion` — reserved for final command evidence in this stage set.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: git status/branch/HEAD/fetch, `rg`, `sed`
- INPUT ARTIFACTS: Phase 3A.2 branch, existing v3 schemas, Stage Router, Codex adapter
- OUTPUT ARTIFACTS: repository truth, implementation boundary, plan
- EVIDENCE REQUIRED: expected base HEAD; no unrelated dirty work; no Stage Router edits
- RESULT: PASS

### RESEARCH

- STAGE: `research`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: verify installed runtime discovery and primary-source evaluation lessons.
- SKILLS CONSIDERED: `using-superpowers`, `wiki-research-loop`, `wiki-builder`, `llm-council`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; PROCESS=`wiki-research-loop`; DOMAIN=`wiki-builder`; REVIEW=`llm-council`; VERIFY=`verification-before-completion`
- WHY SELECTED: official runtime docs and routing research must remain separate from fixture assumptions.
- SKILLS REJECTED: broad adapter implementation skills — no other runtime adapter is in scope.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: official OpenAI/Anthropic/OpenCode/Hermes sources, safe `command -v` and version probes, source review
- INPUT ARTIFACTS: runtime guides, ModelProfile contract, research papers/repos
- OUTPUT ARTIFACTS: runtime matrix, evidence taxonomy, baseline/holdout design
- EVIDENCE REQUIRED: first-party links; exact local version outputs; no live quality claim from static fixtures
- RESULT: PASS; four runtimes installed, three unresolved; quality evidence remains absent

### DESIGN

- STAGE: `design`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: define the smallest separate runtime/model evaluation records.
- SKILLS CONSIDERED: `using-superpowers`, `grill-with-docs`, `ckm:design-system`, `improve-codebase-architecture`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; PROCESS=`grill-with-docs`; DOMAIN=`ckm:design-system`; REVIEW=`improve-codebase-architecture`; VERIFY=`verification-before-completion`
- WHY SELECTED: contracts need explicit boundaries, reproducible envelopes, and evidence provenance.
- SKILLS REJECTED: model-router implementation — this phase is evaluation-only.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: schema inspection, test-first contract design, apply_patch
- INPUT ARTIFACTS: TaskSpec, StageRoute, AgentAdapterManifest, ModelProfile, permission intersection
- OUTPUT ARTIFACTS: six evaluation schemas plus runtime-neutral helper design
- EVIDENCE REQUIRED: model records cannot declare runtime authority; handoffs are explicit; history is append-only
- RESULT: PASS

### PLAN

- STAGE: `plan`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: sequence implementation, fixture separation, tests, evidence, and PR work.
- SKILLS CONSIDERED: `using-superpowers`, `writing-plans`, `invariant-guard`, `logic-explain`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; PROCESS=`writing-plans`; DOMAIN=`invariant-guard`; REVIEW=`logic-explain`
- WHY SELECTED: keep the patch small and preserve the 129-test baseline plus explicit security invariants.
- SKILLS REJECTED: parallel implementation orchestration — no independent large workstream was needed.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: plan artifact, existing test/schema inventory
- INPUT ARTIFACTS: implementation task, current contract files, source findings
- OUTPUT ARTIFACTS: `docs/superpowers/plans/2026-09-09-v3-model-routing-evaluation-harness.md`
- EVIDENCE REQUIRED: no adaptive routing, no runtime side effects, development/holdout split
- RESULT: PASS

### IMPLEMENT

- STAGE: `implement`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: implement schemas, validators, pure evaluation helpers, and fixtures.
- SKILLS CONSIDERED: `using-superpowers`, `tdd`, `addyosmani-api-and-interface-design`, `addyosmani-incremental-implementation`, `code-review-excellence`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; PROCESS=`tdd`, `addyosmani-incremental-implementation`; DOMAIN=`addyosmani-api-and-interface-design`; REVIEW=`code-review-excellence`; VERIFY=`verification-before-completion`
- WHY SELECTED: contract-first slices, no authority leakage, and executable regression coverage.
- SKILLS REJECTED: runtime adapter skills — current Codex adapter remains the only execution target; no new adapter is implemented.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: `apply_patch`, Python unittest, JSON fixture validation
- INPUT ARTIFACTS: existing v3 schemas/helpers, runtime probes, source mapping
- OUTPUT ARTIFACTS: six schemas, validator registrations, evaluation helper, 7 runtime and 5 model fixtures, development/holdout indices, 27 focused tests
- EVIDENCE REQUIRED: deterministic records; permission intersection; mock/fixture quality exclusion; no credential serialization
- RESULT: PASS; focused suite 27/27

### REVIEW

- STAGE: `review`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: independently inspect architecture, security, evidence classes, and anti-bloat.
- SKILLS CONSIDERED: `using-superpowers`, `code-review-excellence`, `addyosmani-code-simplification`, `security-patterns`, `doubt-driven-development`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; REVIEW=`code-review-excellence`, `doubt-driven-development`; VERIFY=`security-patterns`; PROCESS=`addyosmani-code-simplification`
- WHY SELECTED: challenge unsupported runtime/model claims, authority boundaries, and speculative abstractions.
- SKILLS REJECTED: unavailable `security-and-hardening` exact catalog entry — used available security-patterns/manual security review fallback.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: diff inspection, targeted secret/path scan, official-source comparison, OCR precheck
- INPUT ARTIFACTS: new schemas/helper/tests/fixtures and source notes
- OUTPUT ARTIFACTS: review findings, security checklist, OCR status
- EVIDENCE REQUIRED: model cannot grant authority; mock cannot rank quality; no unsupported switching; no credentials in records
- RESULT: PASS pending final full-suite verification; no live quality result inferred

### VERIFY

- STAGE: `verify`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: run all tests, schema checks, link checks, and repository hygiene checks.
- SKILLS CONSIDERED: `using-superpowers`, `verification-before-completion`, `codex-engineering-guardrails:code-verification`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; VERIFY=`verification-before-completion`, `codex-engineering-guardrails:code-verification`
- WHY SELECTED: completion requires fresh command output and explicit negative checks.
- SKILLS REJECTED: performance optimization — no live execution path or measured regression requires it.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: unittest discovery, `git diff --check`, JSON/schema validation, link/path/secret scans
- INPUT ARTIFACTS: all changed implementation, fixtures, docs
- OUTPUT ARTIFACTS: full test result, diff check, changed-file boundary, live-evidence verdict
- EVIDENCE REQUIRED: existing 129 tests remain green; no router/install changes; no live superiority claim
- RESULT: PASS; final full regression recorded 162/162 tests; no Stage Router or runtime adapter changes

### HANDOFF

- STAGE: `handoff`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: publish a stacked Draft PR and hand off the next evidence-gathering phase.
- SKILLS CONSIDERED: `using-superpowers`, `handoff`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`; PROCESS=`handoff`; VERIFY=`verification-before-completion`
- WHY SELECTED: preserve append-only evidence and stop before adaptive policy or Phase 3C implementation.
- SKILLS REJECTED: model-router implementation and other native adapters — explicit phase boundary.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not selected
- TOOLS: canonical docs, PR metadata, final verification output
- INPUT ARTIFACTS: schemas, fixtures, evaluation evidence, review findings
- OUTPUT ARTIFACTS: Draft stacked PR and updated `NEXT_CODEX_PROMPT.md`
- EVIDENCE REQUIRED: verdict must be one of the specified next-state values; no merge
- RESULT: PASS; evidence and next prompt prepared; publication remains a Draft PR and no merge is performed

## Cross-stage evidence

- Stage Router dogfood used the immutable snapshot `snapshot:2349a6fe70aaf346`.
- Snapshot facts: 214 metadata records; overlay digest
  `sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b`;
  normal ranking body files loaded `0`.
- The current Stage Router emits `model_profile: unselected`; this Phase 3B
  harness records model candidates without changing that route contract.
- No live model quality execution was performed. Static candidate fixtures and
  synthetic unit-test results are not superiority evidence.
