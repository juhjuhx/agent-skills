# Phase 2.5 Codex Conformance Dogfood Routing Trace

> Phase 2.6 provenance correction: this historical record describes the
> `45305dd` source snapshot used at the time. Its mention of local
> `codex-cli 0.153.4` is not installed-runtime conformance evidence. The
> current executable target and the explicit source-preview classification are
> recorded in [`CODEX_OFFICIAL_CAPABILITY_MAPPING.md`](../CODEX_OFFICIAL_CAPABILITY_MAPPING.md)
> and [`PHASE26_RUNTIME_PROVENANCE_ROUTE.md`](PHASE26_RUNTIME_PROVENANCE_ROUTE.md).

This evidence artifact records the first Phase 2.5 conformance and hardening
run. It records explicit route decisions, source evidence, test results, and
operational artifacts only. It does not record hidden chain-of-thought,
private reasoning, or scratchpads.

## Task

- TASK: Agent Skills Matrix v3 Phase 2.5 — Codex adapter conformance and hardening
- START_HEAD: 5e18083eb149378e6208f6f55b5ec069002b9ed3
- BRANCH: fix/v3-codex-adapter-conformance
- AGENT/RUNTIME: Codex
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0
- REGISTRY EPOCH: registry:42c3d5c
- TASKSPEC SUMMARY: verify pinned Codex approval/config behavior, fail closed on unrepresentable permissions, keep loaded skill bodies execution-local, add regression tests, and synchronize canonical evidence
- TASK TYPE: bounded conformance and security hardening
- CLASSIFICATION: STANDARD implementation scope / HIGH risk boundary / LOW ambiguity / MEDIUM unfamiliarity / LOW architecture impact
- REQUIRED CAPABILITIES: editing, sandbox, structured_output
- PERMISSION TARGET: workspace-write; network read-only for source verification; no new MCP installation
- NON-GOALS: Phase 3, other adapters, general Stage Router, installer changes, runtime side effects, registry migration
- DEEP_UNDERSTANDING: NOT_REQUIRED
- DEEP_UNDERSTANDING REASON: the bounded risk questions were resolved by pinned first-party Codex source comparison, existing Phase 2 contracts, focused red tests, and independent security review; invoking a broader understanding workflow would not add evidence.

## Skill discovery and loading

The repository registry was inspected before selecting names. Selected procedures
were loaded from the canonical installed SKILL.md files only when their stage
needed them. using-superpowers was loaded as resident task/session authority;
listing it in each GATE slot does not require a full instruction reload.

Selected installed skills used in this run:

| Skill ID | Role use | Residency |
|---|---|---|
| using-superpowers | GATE | resident task/session authority |
| codebase-inspection | DOMAIN/TOOL | stage-local |
| context-engineering | PROCESS/TOOL | stage-local |
| addyosmani-source-driven-development | PROCESS | stage-local |
| addyosmani-api-and-interface-design | DOMAIN | stage-local |
| writing-plans | PROCESS | stage-local |
| executing-plans | PROCESS | stage-local |
| test-driven-development | PROCESS | stage-local |
| code-review-excellence | REVIEW | stage-local |
| mcp-audit | TOOL | stage-local |
| addyosmani-security-and-hardening | REVIEW | stage-local |
| addyosmani-code-simplification | REVIEW | stage-local |
| verification-before-completion | VERIFY | stage-local |

## Findings before fix

| Finding | Requirement/risk | Observable evidence | Verdict before fix |
|---|---|---|---|
| Approval policy drift | Native projection must match pinned AskForApproval | Pinned schema exposes on-request, never, or a full granular object; old adapter accepted untrusted and on-failure | BLOCKING |
| Native config contract | v3 shortString validation is not evidence that Codex accepts a value | No pinned subset validator existed; unknown values could pass the projection schema | BLOCKING |
| Permission projection | Portable permissions must never become broader Codex authority | Old mapping sent permissions beyond workspace-write toward danger-full-access | BLOCKING |
| Loaded-body boundary | Serializable evidence must not expose full private/licensed skill bodies | AdapterResult carried loaded content risk through the result boundary | BLOCKING |
| Revision provenance | Native evidence must be reproducible and invalidated when the source contract changes | No checked-in narrow contract revision was recorded | IMPORTANT |
| Documentation precision | Canonical docs must agree on portable permission vocabulary | USING_SUPERPOWERS used local-write while schemas use workspace-write | IMPORTANT |

## Stage routes

Every active stage below emitted a StageRoute-shaped record with status
SKILLS_SELECTED. Skill selection was rerun independently per stage. The
resident GATE reference is not a repeated full context load.

### UNDERSTAND

- STAGE: UNDERSTAND
- OBJECTIVE: establish the exact hardening scope, source truth, and pre-fix risks.
- SKILLS CONSIDERED: using-superpowers, codebase-inspection, context-engineering, verification-before-completion, brainstorming.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - DOMAIN: codebase-inspection
  - PROCESS: context-engineering
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; DOMAIN codebase-inspection; PROCESS context-engineering; VERIFY verification-before-completion.
- WHY SELECTED: task authority, bounded repository inspection, context control, and evidence-first acceptance criteria.
- SKILLS REJECTED: brainstorming.
- WHY REJECTED: the hardening requirements and protected scope were already explicit; ideation would not resolve a source or safety uncertainty.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: git status, branch/rev-parse, git fetch, rg, sed, registry inspection.
- INPUT ARTIFACTS: AGENTS.md, Phase 2 adapter files, Phase 2 tests, v3 contracts, current registry.
- OUTPUT ARTIFACTS: TaskSpec summary, classification, findings-before-fix matrix.
- EVIDENCE REQUIRED: current branch/head, protected scope, actual installed skill IDs, explicit risk classification.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-understand; task_id T-v3-phase25-codex; stage understand; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. Scope remained bounded to conformance, permissions, serialization, tests, and docs.

### RESEARCH

- STAGE: RESEARCH
- OBJECTIVE: verify the pinned Codex native contract and current first-party surface mapping.
- SKILLS CONSIDERED: using-superpowers, addyosmani-source-driven-development, codebase-inspection, context-engineering, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - PROCESS: addyosmani-source-driven-development
  - DOMAIN: codebase-inspection
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; PROCESS source-driven-development; DOMAIN codebase-inspection; VERIFY verification-before-completion.
- WHY SELECTED: first-party evidence is authoritative for native values, while repository inspection ties the source revision to emitted fields.
- SKILLS REJECTED: context-engineering.
- WHY REJECTED: the source set was already limited to the pinned schema, official docs, and current adapter files; an additional context pass was unnecessary.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: official OpenAI docs, pinned openai/codex source, curl, codex version, rg, python3.
- INPUT ARTIFACTS: Codex config schema revision 45305dd229c01e6cb6e122f6559e4f9b805bae6, local Codex CLI 0.153.4, Phase 2 mapping.
- OUTPUT ARTIFACTS: verified approval/sandbox findings, narrow native contract fixture design, refreshed mapping evidence.
- EVIDENCE REQUIRED: exact AskForApproval forms, SandboxMode values, emitted-field allowlist, source and contract revisions.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-research; task_id T-v3-phase25-codex; stage research; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. The pinned schema is authoritative: scalar on-request and never are valid; granular is an object form; untrusted and on-failure are not valid in this snapshot.

### DESIGN

- STAGE: DESIGN
- OBJECTIVE: choose the smallest conformance and fail-closed boundaries without introducing an engine hierarchy.
- SKILLS CONSIDERED: using-superpowers, addyosmani-api-and-interface-design, context-engineering, addyosmani-code-simplification, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - DOMAIN: addyosmani-api-and-interface-design
  - PROCESS: context-engineering
  - REVIEW: addyosmani-code-simplification
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; DOMAIN API/interface design; PROCESS context-engineering; REVIEW code simplification; VERIFY verification-before-completion.
- WHY SELECTED: preserve the portable/native boundary, keep body loading ephemeral, and prefer pure data/validator helpers.
- SKILLS REJECTED: improve-codebase-architecture.
- WHY REJECTED: the existing Phase 2 boundary already has the required ownership; adding another architecture framework would expand scope.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: rg, sed, existing schemas, adapter diff inspection.
- INPUT ARTIFACTS: Phase 1 schemas, Codex projection schema, AdapterResult, permission intersection, source findings.
- OUTPUT ARTIFACTS: design for a narrow pinned validator, permission classification matrix, execution-local body boundary.
- EVIDENCE REQUIRED: no broad fallback, no unsupported native fields, no raw body in serializable output, no manager/registry/service layer.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-design; task_id T-v3-phase25-codex; stage design; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. The design uses a checked-in subset validator, pure mapping data, and an explicit ephemeral execution field.

### PLAN

- STAGE: PLAN
- OBJECTIVE: order focused RED/GREEN changes and define verification gates.
- SKILLS CONSIDERED: using-superpowers, writing-plans, executing-plans, addyosmani-api-and-interface-design, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - PROCESS: writing-plans
  - PROCESS: executing-plans
  - DOMAIN: addyosmani-api-and-interface-design
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; PROCESS planning/execution; DOMAIN API/interface design; VERIFY verification-before-completion.
- WHY SELECTED: make the hardening sequence explicit, preserve small commits, and keep each change tied to a regression.
- SKILLS REJECTED: addyosmani-planning-and-task-breakdown as a duplicate of the selected writing-plans procedure.
- WHY REJECTED: one planning discipline was sufficient for this bounded pass.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: writing plan, rg, sed, apply_patch.
- INPUT ARTIFACTS: findings matrix, Phase 2 tests, source mapping, protected non-goals.
- OUTPUT ARTIFACTS: docs/superpowers/plans/2026-09-08-v3-codex-conformance.md.
- EVIDENCE REQUIRED: plan before implementation, test-first targets, explicit stop conditions.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-plan; task_id T-v3-phase25-codex; stage plan; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. The plan separated native contract, permission, serialization, regression tests, and docs/evidence work.

### IMPLEMENT

- STAGE: IMPLEMENT
- OBJECTIVE: implement pinned native validation, current approval mapping, fail-closed permission projection, and body-safe AdapterResult serialization.
- SKILLS CONSIDERED: using-superpowers, test-driven-development, addyosmani-api-and-interface-design, context-engineering, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - PROCESS: test-driven-development
  - DOMAIN: addyosmani-api-and-interface-design
  - TOOL: context-engineering
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; PROCESS test-driven-development; DOMAIN API/interface design; TOOL context-engineering; VERIFY verification-before-completion.
- WHY SELECTED: focused red tests exposed drift first; implementation stayed at data/validation/pure helper boundaries; selected-only loading remained intact.
- SKILLS REJECTED: addyosmani-code-simplification.
- WHY REJECTED: simplification was reserved for an independent review lane after behavior was green.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: apply_patch, python3 -B -m unittest, rg, json validation.
- INPUT ARTIFACTS: adapter, projection schema, permission intersection, skill resolver, native source findings.
- OUTPUT ARTIFACTS: codex-native-config-contract.json, codex_native_contract.py, adapter/schema/test/fixture changes.
- EVIDENCE REQUIRED: valid current approval values, obsolete rejection, native invalid-value rejection, permission non-widening, no serialized raw body, digest/trust preservation.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-implement; task_id T-v3-phase25-codex; stage implement; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. Focused tests and the full suite reached 66 passing tests.

### REVIEW

- STAGE: REVIEW
- OBJECTIVE: independently review correctness, API boundaries, context leakage, and unsupported native claims.
- SKILLS CONSIDERED: using-superpowers, code-review-excellence, addyosmani-code-simplification, addyosmani-api-and-interface-design, mcp-audit, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - REVIEW: code-review-excellence
  - REVIEW: addyosmani-code-simplification
  - DOMAIN: addyosmani-api-and-interface-design
  - TOOL: mcp-audit
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; REVIEW code-review-excellence and code simplification; DOMAIN API/interface design; TOOL mcp-audit; VERIFY verification-before-completion.
- WHY SELECTED: independent quality and simplification lanes inspect different failure classes; MCP audit checks declared tool/config surfaces.
- SKILLS REJECTED: test-driven-development.
- WHY REJECTED: review stage needed independent inspection, not another implementation loop.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: git diff, rg, Python tests, project MCP/config scan, review checklists.
- INPUT ARTIFACTS: implementation diff, native contract fixture, tests, fixtures, mapping docs.
- OUTPUT ARTIFACTS: review findings and hardening confirmations.
- EVIDENCE REQUIRED: no unsupported projection fields, no permission widening, no raw body serialization, no speculative abstraction.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-review; task_id T-v3-phase25-codex; stage review; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. No additional blocking code or architecture finding remained after the focused fixes.

### VERIFY

- STAGE: VERIFY
- OBJECTIVE: verify all tests, schema fixtures, source revisions, diffs, links, protected files, and secret/path boundaries.
- SKILLS CONSIDERED: using-superpowers, verification-before-completion, codebase-inspection, context-engineering.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - VERIFY: verification-before-completion
  - TOOL: codebase-inspection
  - PROCESS: context-engineering
- ROLE SLOT: GATE using-superpowers; VERIFY verification-before-completion; TOOL codebase-inspection; PROCESS context-engineering.
- WHY SELECTED: fresh commands and scoped inspection provide completion evidence without loading unrelated repository content.
- SKILLS REJECTED: test-driven-development.
- WHY REJECTED: implementation regressions were already covered; this stage is independent confirmation.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p test_*.py -v, git diff --check, JSON validation, Markdown link checks, rg secret/path checks.
- INPUT ARTIFACTS: all changed code, schemas, fixtures, docs, and evidence.
- OUTPUT ARTIFACTS: 66-test report, diff-check report, link/path/secret scan.
- EVIDENCE REQUIRED: all tests pass, no protected-scope changes, no secrets or private paths.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-verify; task_id T-v3-phase25-codex; stage verify; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS after the final command set; detailed results are recorded in the final handoff section.

### HARDEN

- STAGE: HARDEN
- OBJECTIVE: confirm security posture, fail-closed behavior, MCP/tool declarations, and anti-bloat constraints.
- SKILLS CONSIDERED: using-superpowers, addyosmani-security-and-hardening, mcp-audit, addyosmani-code-simplification, code-review-excellence, verification-before-completion.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - REVIEW: addyosmani-security-and-hardening
  - TOOL: mcp-audit
  - REVIEW: addyosmani-code-simplification
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; REVIEW security and simplification; TOOL mcp-audit; VERIFY verification-before-completion.
- WHY SELECTED: inspect metadata/path/config injection, permission boundaries, body leakage, external declarations, and unnecessary layers.
- SKILLS REJECTED: executing-plans.
- WHY REJECTED: no new implementation plan was needed after the focused fixes; hardening validates the resulting boundary.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: rg, project config scan, security tests, diff audit, which ocr, ocr version, ocr llm test.
- INPUT ARTIFACTS: hardened diff, native contract, permission tests, serialization tests, project MCP/config state.
- OUTPUT ARTIFACTS: security verdict, OCR status, anti-bloat audit, protected-scope scan.
- EVIDENCE REQUIRED: unknown values block, authority never widens, body remains ephemeral, no unsafe generated config, OCR status is honest.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-harden; task_id T-v3-phase25-codex; stage harden; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS for code/security/anti-bloat review; native OCR was run once and is recorded as authentication-blocked below.

### HANDOFF

- STAGE: HANDOFF
- OBJECTIVE: synchronize canonical docs, update the Phase 3 strategy prompt, commit, push, and create a stacked Draft PR without merging.
- SKILLS CONSIDERED: using-superpowers, writing-plans, verification-before-completion, code-review-excellence.
- SKILLS SELECTED:
  - GATE: using-superpowers
  - PROCESS: writing-plans
  - VERIFY: verification-before-completion
- ROLE SLOT: GATE using-superpowers; PROCESS writing-plans; VERIFY verification-before-completion.
- WHY SELECTED: preserve task authority, make the next phase self-contained, and verify publication state without executing Phase 3.
- SKILLS REJECTED: code-review-excellence.
- WHY REJECTED: independent review conclusions are recorded in REVIEW/HARDEN; handoff only packages verified artifacts.
- AGENT/RUNTIME: Codex.
- MODEL PROFILE: openai/gpt-compatible-fixture@fixture-1.0.
- TOOLS: apply_patch, git diff/status/log, git add/commit, git push, gh pr create/view.
- INPUT ARTIFACTS: passing tests, refreshed canonical docs, Phase 2.5 trace, Phase 3 prompt.
- OUTPUT ARTIFACTS: semantic commits, remote branch, stacked Draft PR, final repository truth.
- EVIDENCE REQUIRED: branch based on feat/v3-codex-adapter, clean publish, Draft PR base/head, no merge, Phase 3 not executed.
- ROUTE RECORD: route_id R-T-v3-phase25-codex-handoff; task_id T-v3-phase25-codex; stage handoff; registry_epoch registry:42c3d5c; status SKILLS_SELECTED.
- RESULT: PASS. Three semantic commits were pushed to the stacked branch and Draft PR #4 was verified open against feat/v3-codex-adapter; no merge was performed.

## Results and evidence

- PINNED_CODEX_SOURCE_REVISION: 45305dd229c01e6cb6e122f6559e4f9b805bae6
- NATIVE_CONTRACT_REVISION: codex-rs/core/config.schema.json@45305dd229c01e6cb6e122f6559e4f9b805bae6
- APPROVAL_POLICY: on-request and never are emitted; full granular object is validated as native shape but blocked as unsupported by this adapter; untrusted and on-failure are rejected.
- PERMISSION_POLICY: read and workspace-write are exact; workspace-read is host-managed and blocked without proved path enforcement; none, external-write, destructive, and unknown values are blocked.
- SERIALIZATION_POLICY: projection and AdapterResult.to_dict contain references/digests/roles/load-state/bytes only; full skill bodies remain in execution_skills.
- DEEP_UNDERSTANDING: NOT_REQUIRED for this bounded evidence-driven hardening pass.
- PHASE3: NOT_EXECUTED.
- DRAFT_PR: #4 https://github.com/juhjuhx/agent-skills/pull/4; base feat/v3-codex-adapter; head fix/v3-codex-adapter-conformance; state OPEN; draft true.

## Verification results

- TESTS: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v` — 68 tests passed.
- DIFF_CHECK: `git diff --check` — PASS.
- JSON_CHECK: modified schemas and fixtures parse successfully — PASS.
- MARKDOWN_RELATIVE_LINKS: 39 repository-relative links checked — PASS.
- SECRET_AND_PRIVATE_PATH_SCAN: no API keys, tokens, secret config, user-home paths, or private local paths found in changed scope — PASS.
- PROTECTED_SCOPE: no install.sh, production registry, categories.json, routing policy, root AGENTS.md, or root README.md changes — PASS.

## Context and serialization measurement

The measurement used the current 214-record registry and the selected route.
All-catalog body bytes are a hypothetical file-metadata total; selected values
are actual adapter measurements. The byte/token relationship is not a token
count and no production token-savings claim is made.

| Measurement | Result |
|---|---:|
| Registry records | 214 |
| Hypothetical all-catalog SKILL.md files present | 214 |
| Hypothetical all-catalog body bytes | 2,155,285 |
| Selected metadata records inspected | 4 |
| Selected source files verified | 4 |
| Selected SKILL.md bodies loaded | 3 |
| Selected/execution-local body bytes | 22,911 |
| Serialized AdapterResult bytes | 7,822 |
| Codex projection bytes | 3,048 |
| Ten-run projection latency minimum | 20.827 ms |
| Ten-run projection latency average | 21.413 ms |

The result demonstrates selected-only loading and a body-free serializable
boundary; no new optimization architecture was introduced.

## Independent review results

- ARCHITECTURE/API REVIEW: PASS — portable bundle remains runtime-neutral;
  CodexAdapter consumes a validated route; native field validation is isolated
  in a narrow pinned helper.
- CODE REVIEW: PASS — current approval forms are preserved, unsupported forms
  fail closed, revision mismatch blocks projection, and result serialization
  retains provenance without raw bodies.
- SIMPLIFICATION REVIEW: PASS — no NativeConfigManager, PermissionManager,
  SerializationManager, ProviderRegistry, database, event bus, worker pool,
  scheduler, or general runtime engine was added.
- SECURITY REVIEW: PASS — path and digest checks remain repository-bound;
  quarantine is blocked; model, skill, MCP, hook, and projection declarations
  cannot grant OS authority; unrepresentable sandbox levels do not fall back
  to danger-full-access.
- VERIFICATION REVIEW: PASS — full suite, diff, JSON, link, secret/path, and
  protected-scope checks passed.
- MCP AUDIT: PASS — no project-level MCP configuration or server installation
  was added; the existing OpenCode JSON is a capability fixture only and its
  MCP declaration remains policy-gated and lazy.

## Alibaba OpenCodeReview

- WHICH_OCR: `/opt/homebrew/bin/ocr`
- OCR_VERSION: open-code-review v1.11.6 (04284b5dc), darwin/arm64
- OCR_LLM_TEST: HTTP 401 Unauthorized from the configured provider.
- OCR_NATIVE_DIFF: BLOCKED_BY_AUTH

No native diff pass is claimed. Delegate review, if used later, must remain a
separate OCR_DELEGATE evidence class.
