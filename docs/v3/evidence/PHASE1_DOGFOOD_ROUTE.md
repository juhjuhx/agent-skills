# Phase 1 Dogfood Routing Trace

> This is an operational evidence record for the first v3 dogfood run. It records route decisions, artifacts, commands, and outcomes only; it does not record hidden chain-of-thought.

## Task

- `TASK`: Agent Skills Matrix v3 Phase 1 — machine-readable contracts
- `START_HEAD`: `e1c588c96f8b105d805b607a2e64678c3dc1ed36`
- `BRANCH`: `feat/v3-contract-schemas`
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not selected by the universal core; this run used local repository tools and explicit source artifacts
- `AUTHORITY`: `using-superpowers` at task/session scope

### TaskSpec summary

```yaml
task_id: T-v3-phase1-contracts-full
task_type: implementation
classification:
  complexity: COMPLEX
  risk: HIGH
  ambiguity: MEDIUM
  architecture_impact: ARCHITECTURE-CHANGING
required_capabilities:
  - needs_editing
  - needs_sandbox
  - needs_structured_output
permission_level: workspace-write
budget: balanced
stages: [understand, research, design, plan, implement, review, verify, harden, handoff]
```

### Deep Understanding

`DEEP_UNDERSTANDING: USED_WITH_SAFE_FALLBACK`

This task defines durable cross-agent contracts and therefore qualifies as `COMPLEX` and `ARCHITECTURE-CHANGING`. The installed `understand` capability was loaded and its deterministic `scan-project.mjs` workflow was invoked. The workflow was unavailable because the environment lacks `@understand-anything/core`; no graph was written. Per the v3 fallback rule, the enriched TaskSpec was completed from direct registry, policy, documentation, and file-tree evidence rather than inventing certainty.

## Contract consistency findings

- `BLOCKING`: none.
- `IMPORTANT`: the conceptual StageRoute example used `selected`/`route_epoch` while the Phase 1 contract requires `selected_skills`/`registry_epoch`; the canonical document was synchronized to the implemented names.
- `IMPORTANT`: the v3 documents named the adapter and profile surfaces but did not define serializable shapes; the five schemas now provide those boundaries.
- `IMPORTANT`: `using-superpowers` residency and unknown-capability behavior needed explicit contract language; both are now documented and tested.
- `MINOR`: current registry categories, installer categories, and v3 domains are different projections; compatibility docs now keep them separate.

`using-superpowers` was loaded once for the task. Its `GATE` reference is repeated below for each stage so every active stage has an observable route, but the full authority instructions were not reloaded at every stage.

## Stage routes

### 1. Understand

- `STAGE`: `understand`
- `OBJECTIVE`: establish repository truth, classify the task, and produce a portable TaskSpec.
- `SKILLS CONSIDERED`: `using-superpowers`, `understand`, `context-engineering`, `codebase-inspection`, `understand-domain`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — task/session orchestration authority.
  - `PROCESS`: `understand` — corresponding installed Deep Understanding capability for architecture-changing work.
  - `PROCESS`: `context-engineering` — progressive disclosure and artifact-sized context.
- `ROLE SLOT`: `GATE`, `PROCESS`
- `WHY SELECTED`: the task is durable, cross-agent, and requires explicit classification before implementation.
- `SKILLS REJECTED`:
  - `codebase-inspection` — LOC metrics are not needed to define these contracts.
  - `understand-domain` — this is an orchestration/schema task, not business-domain extraction.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `git`, `rg`, `jq`, `node`, repository file reads
- `INPUT ARTIFACTS`: user specification, `AGENTS.md`, v3 canonical docs, current registry, categories, v2 routing policy
- `OUTPUT ARTIFACTS`: TaskSpec summary, classification, contract consistency findings, Deep Understanding availability evidence
- `EVIDENCE REQUIRED`: current HEAD/branch, registry inspection, explicit fallback if Deep Understanding is unavailable
- `RESULT`: `SKILLS_SELECTED` — classification and conservative TaskSpec completed; Deep Understanding workflow failure preserved as evidence.

### 2. Research

- `STAGE`: `research`
- `OBJECTIVE`: verify the schema/skill-format foundations and inspect actual repository registry names.
- `SKILLS CONSIDERED`: `using-superpowers`, `addyosmani-source-driven-development`, `codebase-inspection`, `understand`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — preserves task authority.
  - `PROCESS`: `addyosmani-source-driven-development` — source-first implementation decisions and provenance.
- `ROLE SLOT`: `GATE`, `PROCESS`
- `WHY SELECTED`: JSON Schema and Agent Skills format details are externally specified and should not be reconstructed from memory.
- `SKILLS REJECTED`:
  - `codebase-inspection` — no LOC or language ratio decision affects the contract boundary.
  - `understand` — already used at the Understand stage; no second graph workflow is needed.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: official web sources, `jq`, `rg`
- `INPUT ARTIFACTS`: JSON Schema Draft 2020-12 specification, Agent Skills specification, current registry and policy
- `OUTPUT ARTIFACTS`: source references in `PHASE1_MACHINE_READABLE_CONTRACTS.md`, actual skill IDs and registry epoch
- `EVIDENCE REQUIRED`: official source links, no remembered or invented skill names
- `RESULT`: `SKILLS_SELECTED` — official sources and current registry evidence recorded.

### 3. Design

- `STAGE`: `design`
- `OBJECTIVE`: map the v3 architecture contracts to minimal data boundaries without creating a router.
- `SKILLS CONSIDERED`: `using-superpowers`, `addyosmani-api-and-interface-design`, `addyosmani-documentation-and-adrs`, `new-skill`, `plugin-structure`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — protects policy and stage boundaries.
  - `PROCESS`: `addyosmani-documentation-and-adrs` — records durable decisions and alternatives.
  - `DOMAIN`: `addyosmani-api-and-interface-design` — contract-first, boundary validation, additive evolution.
- `ROLE SLOT`: `GATE`, `PROCESS`, `DOMAIN`
- `WHY SELECTED`: the five schemas are public interfaces between future stages, runtimes, and providers.
- `SKILLS REJECTED`:
  - `new-skill` — no new executable skill is being authored.
  - `plugin-structure` — native plugins are Phase 2+ and not part of schema implementation.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `apply_patch`, JSON inspection
- `INPUT ARTIFACTS`: v3 ADRs, Stage Router contract, adapter/profile contracts, reasoning artifacts contract
- `OUTPUT ARTIFACTS`: schema field model, conditional StageRoute status rule, capability and relationship semantics
- `EVIDENCE REQUIRED`: agent/model separation, explicit route status, no permission grant by declaration
- `RESULT`: `SKILLS_SELECTED` — design stayed data/validation-focused; no framework hierarchy or runtime router introduced.

### 4. Plan

- `STAGE`: `plan`
- `OBJECTIVE`: sequence schema, validator, fixture, compatibility, documentation, and verification work.
- `SKILLS CONSIDERED`: `using-superpowers`, `writing-plans`, `plan`, `executing-plans`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — stage transition and stop-condition authority.
  - `PROCESS`: `writing-plans` — small files, exact paths, TDD checkpoints, and YAGNI.
- `ROLE SLOT`: `GATE`, `PROCESS`
- `WHY SELECTED`: the task spans five contracts and multiple fixtures but must remain a small Phase 1 slice.
- `SKILLS REJECTED`:
  - `plan` — its native `.hermes/plans` output is not the repository’s canonical v3 documentation surface.
  - `executing-plans` — no separate plan executor is needed in this single Codex session.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `apply_patch`, `python3 -m unittest`
- `INPUT ARTIFACTS`: TaskSpec, consistency findings, v3 migration plan
- `OUTPUT ARTIFACTS`: `PHASE1_IMPLEMENTATION_PLAN.md`, TDD red/green checkpoints
- `EVIDENCE REQUIRED`: failing test before validator implementation, then green contract tests
- `RESULT`: `SKILLS_SELECTED` — plan bounded the change to schemas, validation, fixtures, compatibility, and docs.

### 5. Implement

- `STAGE`: `implement`
- `OBJECTIVE`: implement five schemas, small validator, read-only compatibility projection, and fixtures.
- `SKILLS CONSIDERED`: `using-superpowers`, `test-driven-development`, `addyosmani-api-and-interface-design`, `incremental-implementation`, `verification-before-completion`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — stage gate and no-runtime-change invariant.
  - `PROCESS`: `test-driven-development` — failing test before implementation and incremental red/green cycles.
  - `DOMAIN`: `addyosmani-api-and-interface-design` — stable public contract and boundary validation.
  - `VERIFY`: `verification-before-completion` — fresh evidence before later claims.
- `ROLE SLOT`: `GATE`, `PROCESS`, `DOMAIN`, `VERIFY`
- `WHY SELECTED`: schemas are public interfaces; validator behavior must be proven through fixtures and negative cases.
- `SKILLS REJECTED`:
  - `incremental-implementation` — the TDD process and focused helpers were sufficient; no second implementation workflow was needed.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `apply_patch`, Python standard library, `unittest`, `jq`
- `INPUT ARTIFACTS`: schema design, implementation plan, current registry entry
- `OUTPUT ARTIFACTS`: `schemas/v3/`, `tools/v3/`, `fixtures/v3/`, `tests/v3/test_contracts.py`
- `EVIDENCE REQUIRED`: minimal/full TaskSpec, valid metadata, seven agent fixtures, five model fixtures, both route statuses, invalid cases, compatibility import
- `RESULT`: `SKILLS_SELECTED` — the first minimal test was observed failing on missing validator, then passed after the smallest validator/schema slice; final implementation tests cover 23 cases.

### 6. Review

- `STAGE`: `review`
- `OBJECTIVE`: independently inspect correctness, contract fit, and unnecessary abstraction.
- `SKILLS CONSIDERED`: `using-superpowers`, `code-review-excellence`, `addyosmani-code-simplification`, `official-code-review`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — preserves evidence-lane independence.
  - `REVIEW`: `code-review-excellence` — high-signal correctness, architecture, security, and test review.
  - `REVIEW`: `addyosmani-code-simplification` — anti-bloat and single-responsibility review.
- `ROLE SLOT`: `GATE`, `REVIEW`
- `WHY SELECTED`: the phase can fail through schema overreach, inconsistent field names, or unnecessary framework structure.
- `SKILLS REJECTED`:
  - `official-code-review` — its workflow targets a GitHub PR and agent delegation; this implementation review is local and independent of the draft PR.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `git diff`, `rg`, targeted file reads
- `INPUT ARTIFACTS`: implementation diff, tests, v3 canonical docs
- `OUTPUT ARTIFACTS`: independent review findings summarized below and in the final validation record
- `EVIDENCE REQUIRED`: no high-signal correctness issue, no schema/runtime boundary violation, no unnecessary manager/factory/service layer
- `RESULT`: `SKILLS_SELECTED` — two independent review passes completed without sharing conclusions before each pass. The correctness pass found and closed one invariant gap: `StageRoute.granted_capabilities` cannot opt out of unknown-capability rejection through a validator flag; the focused suite passed again after the fix. The simplification pass found no unnecessary Manager, Registry, Factory, Adapter, Service, or router layer.

### 7. Verify

- `STAGE`: `verify`
- `OBJECTIVE`: run the complete contract test suite and repository checks at the real boundary.
- `SKILLS CONSIDERED`: `using-superpowers`, `verification-before-completion`, `test-driven-development`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — completion remains evidence-gated.
  - `VERIFY`: `verification-before-completion` — fresh command output required before commit/push.
- `ROLE SLOT`: `GATE`, `VERIFY`
- `WHY SELECTED`: this is the stage where claims about schema validity, compatibility, and scope must be proven.
- `SKILLS REJECTED`:
  - `test-driven-development` — no new behavior is added during this verification pass.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `python3 -m unittest`, `git diff --check`, JSON/link/path scans
- `INPUT ARTIFACTS`: all schemas, fixtures, tests, and docs
- `OUTPUT ARTIFACTS`: test output, diff-check output, validation summary
- `EVIDENCE REQUIRED`: zero test failures, clean diff check, no secrets/private paths, no forbidden runtime files changed
- `RESULT`: `SKILLS_SELECTED` — the required `python3 -B -m unittest discover -s tests -p 'test_*.py' -v` passed all 24 tests; `git diff --check` passed; 24 schema/fixture JSON documents parsed; 48 relative Markdown links resolved; secret/private-path scans returned no matches. A simple 5,000-record validation benchmark completed with zero failures at 1.93 ms/record; no performance architecture was introduced. Generated bytecode was excluded from the change set.

### 8. Harden

- `STAGE`: `harden`
- `OBJECTIVE`: check untrusted metadata, permission declarations, path/script surfaces, MCP cost, and native OCR availability.
- `SKILLS CONSIDERED`: `using-superpowers`, `addyosmani-security-and-hardening`, `mcp-audit`, `permission-tuner`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — declarations cannot override policy.
  - `REVIEW`: `addyosmani-security-and-hardening` — threat model for untrusted metadata and model output.
  - `TOOL`: `mcp-audit` — inspect MCP context/security overhead without changing configuration.
- `ROLE SLOT`: `GATE`, `REVIEW`, `TOOL`
- `WHY SELECTED`: manifests describe permissions, paths, hooks, plugins, commands, and MCP surfaces that future adapters may consume.
- `SKILLS REJECTED`:
  - `permission-tuner` — no permission-denial history exists for this documentation/contract branch.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `rg`, `jq`, `which`, `ocr` checks, targeted config inspection
- `INPUT ARTIFACTS`: schemas, fixtures, security contract, MCP matrix, implementation diff
- `OUTPUT ARTIFACTS`: path restrictions, unknown-grant rule, threat review, OCR result
- `EVIDENCE REQUIRED`: no secret exposure, no arbitrary absolute/traversal paths, unknown grants rejected, OCR status honest
- `RESULT`: `SKILLS_SELECTED` — security review completed. The validator rejects absolute/traversal paths and unknown granted capabilities; declarations remain non-authorizing. `which ocr` and `ocr version` succeeded (`open-code-review v1.11.5`); `ocr llm test` returned HTTP 401 Unauthorized during provider authentication. Therefore `OCR_NATIVE_DIFF: BLOCKED_BY_AUTH`; no native diff PASS is claimed. `OCR_NATIVE_FULL_SOURCE: NOT_RUN_AFTER_AUTH_PRECHECK`; `OCR_DELEGATE: NOT_USED`. `ocr review --preview` was used only to inspect the candidate file set.

### 9. Handoff / Learn

- `STAGE`: `handoff / learn`
- `OBJECTIVE`: package portable artifacts, record the route, and generate the next-phase prompt without promoting learning or starting Phase 2.
- `SKILLS CONSIDERED`: `using-superpowers`, `addyosmani-documentation-and-adrs`, `verification-before-completion`, `handoff`
- `SKILLS SELECTED`:
  - `GATE`: `using-superpowers` — final handoff and learning authority.
  - `PROCESS`: `addyosmani-documentation-and-adrs` — preserve implementation rationale and future boundaries.
  - `VERIFY`: `verification-before-completion` — ensure the prompt and evidence paths exist and are linked.
- `ROLE SLOT`: `GATE`, `PROCESS`, `VERIFY`
- `WHY SELECTED`: cross-agent handoff depends on explicit artifacts, and learning must remain proposal/eval/promotion based.
- `SKILLS REJECTED`:
  - `handoff` — the v3-specific handoff is represented by the canonical reasoning/artifact contract and this trace; a second handoff format would duplicate it.
- `AGENT/RUNTIME`: Codex
- `MODEL PROFILE`: not applicable
- `TOOLS`: `apply_patch`, `git`, link/path scans
- `INPUT ARTIFACTS`: TaskSpec, stage routes, tests, review/security findings
- `OUTPUT ARTIFACTS`: this trace, `NEXT_CODEX_PROMPT.md`, Phase 1 implementation docs
- `EVIDENCE REQUIRED`: no hidden reasoning, no Phase 2 execution, portable file references, promotion remains pending
- `RESULT`: `SKILLS_SELECTED` — handoff artifacts prepared; Phase 2 was not executed.
