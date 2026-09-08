# Phase 2.6 Runtime Contract Provenance Dogfood Route

This is an operational evidence record for the bounded provenance correction.
It records explicit artifacts and verdicts only; it does not record hidden
reasoning or private model traces.

## TaskSpec summary

- TASK: Agent Skills Matrix v3 Phase 2.6 — Runtime Contract Provenance
- START_HEAD: `e027b8a4c35b1e2aa5f79808e0dcee4a545b4438`
- BASE: `fix/v3-codex-adapter-conformance`
- BRANCH: `fix/v3-runtime-contract-provenance`
- TASK TYPE: bounded contract correction
- COMPLEXITY: STANDARD
- RISK: HIGH (native config provenance and permission-adjacent projection)
- AMBIGUITY: LOW after first-party source comparison
- REQUIRED OUTPUTS: runtime-bound contract metadata, source-preview fixture,
  focused tests, synchronized docs, provenance route
- STOP CONDITIONS: no Phase 3 adapter work; no runtime network lookup; no
  change to installer, general router, or production skill registry
- DEEP_UNDERSTANDING: NOT_USED — the change is bounded; exact release/source
  research plus independent validation resolved the relevant uncertainty

`using-superpowers` remained the task/session GATE authority. It is resident
for this run and was not reloaded as a full skill body at every stage.

## Stage routes

### UNDERSTAND

- ROUTE: `R-PHASE26-UNDERSTAND`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: establish repository baseline and identify the provenance drift.
- SKILLS CONSIDERED: `using-superpowers`,
  `verification-before-completion`, `codebase-inspection`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers` (resident authority);
  VERIFY=`verification-before-completion`
- WHY SELECTED: preserve stage routing and require fresh repository evidence.
- REJECTED: `codebase-inspection` — LOC metrics were unrelated to this bounded
  contract task.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: `git status`, branch/HEAD inspection, `git fetch origin`, `rg`, `sed`
- INPUT ARTIFACTS: Phase 2.5 implementation, v3 docs, existing fixtures/tests
- OUTPUT ARTIFACTS: clean baseline; identified `45305dd` vs installed-runtime
  claim as the correction target
- EVIDENCE REQUIRED: clean worktree, expected base HEAD, no unrelated edits
- RESULT: PASS; clean worktree at expected `e027b8a...` base

### RESEARCH

- ROUTE: `R-PHASE26-RESEARCH`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: bind the installed CLI version to first-party release/source
  evidence and compare only projected native fields.
- SKILLS CONSIDERED: `using-superpowers`,
  `addyosmani-source-driven-development`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  PROCESS=`addyosmani-source-driven-development`;
  VERIFY=`verification-before-completion`
- WHY SELECTED: release/tag resolution and exact source snapshots are the
  source of truth; no unversioned current-main assumption is acceptable.
- REJECTED: broader runtime adapter research — outside Phase 2.6 scope.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: `codex --version`, `git ls-remote`, official OpenAI GitHub sources,
  official Codex docs, local SHA-256 comparison
- INPUT ARTIFACTS: release schema at `3d2ee51...`, source schema at `45305dd...`,
  current docs snapshot `2026-09-08`
- OUTPUT ARTIFACTS: tag `rust-v0.153.4` → commit
  `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`; release digest
  `sha256:692da7699367f6f4fbbd46c0021278c1311440bcebf0bcb9b836690c05e56196`;
  source-snapshot commit `45305dd229c01e6cb6e122f6559e4f9b805bae6`; source
  digest `sha256:2e1fcf1cbb20f255c3baca2e174b4a3c954cef577a130587b8935e2d12c8ade6`
- EVIDENCE REQUIRED: first-party release/ref, immutable source commit, narrow
  field comparison, docs date
- RESULT: PASS; all six projected field shapes compare `IDENTICAL` after
  resolving relevant `$ref`/`allOf` shapes; full schema digests differ

### DESIGN

- ROUTE: `R-PHASE26-DESIGN`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: choose the smallest provenance model and fail-closed target rule.
- SKILLS CONSIDERED: `using-superpowers`,
  `addyosmani-api-and-interface-design`, `addyosmani-code-simplification`,
  `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  PROCESS=`addyosmani-api-and-interface-design`;
  REVIEW=`addyosmani-code-simplification`;
  VERIFY=`verification-before-completion`
- WHY SELECTED: add fields to the existing narrow contract, keep support and
  availability independent, and avoid a provenance framework.
- REJECTED: manager/registry/service abstractions — no real boundary in this
  patch.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: contract inspection, schema inspection, focused test design
- INPUT ARTIFACTS: `codex_native_contract.py`, projection schema, Phase 2.5 tests
- OUTPUT ARTIFACTS: `INSTALLED_RUNTIME` default; explicit `SOURCE_SNAPSHOT` /
  `UPSTREAM_ONLY` comparison target; `RUNTIME_CONTRACT_UNVERIFIED` verdict
- EVIDENCE REQUIRED: source snapshot cannot satisfy installed-runtime validation
- RESULT: PASS; design stayed additive and target-specific

### IMPLEMENT

- ROUTE: `R-PHASE26-IMPLEMENT`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: implement metadata validation, projection provenance, fixture, and
  regression coverage without changing the runtime router.
- SKILLS CONSIDERED: `using-superpowers`,
  `addyosmani-api-and-interface-design`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  PROCESS=`addyosmani-api-and-interface-design`;
  VERIFY=`verification-before-completion`
- WHY SELECTED: maintain the portable/native boundary and verify each edit with
  executable tests.
- REJECTED: Phase 3 adapter skills — explicitly out of scope.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: `apply_patch`, Python unittest
- INPUT ARTIFACTS: portable v3 contracts, Codex projection, checked-in fixtures
- OUTPUT ARTIFACTS: provenance-bound validator, installed/source fixtures,
  projection metadata, focused compatibility tests
- EVIDENCE REQUIRED: default installed target; explicit mismatch/unknown tests;
  no network code path
- RESULT: PASS; implementation completed with no installer/router/registry changes

### REVIEW

- ROUTE: `R-PHASE26-REVIEW`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: independently inspect spec fidelity, source binding, compatibility,
  security, and abstraction size.
- SKILLS CONSIDERED: `using-superpowers`, `code-review-excellence`,
  `addyosmani-code-simplification`, `addyosmani-security-and-hardening`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  REVIEW=`code-review-excellence`, `addyosmani-code-simplification`;
  VERIFY=`addyosmani-security-and-hardening`
- WHY SELECTED: check fail-closed provenance, metadata-as-evidence (not grant),
  and absence of speculative managers.
- REJECTED: generic provider/runtime redesign — unrelated to the patch.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: diff inspection, source scans, OCR auth precheck
- INPUT ARTIFACTS: implementation diff, official-source mapping, tests
- OUTPUT ARTIFACTS: independent review findings; permission/provenance threat
  checks; OCR status
- EVIDENCE REQUIRED: no permission widening, no secret/path leakage, no
  unsupported native field, no broad abstraction
- RESULT: PASS with OCR native diff blocked by authentication (`401`); no
  actionable code finding identified

### VERIFY

- ROUTE: `R-PHASE26-VERIFY`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: run the full regression suite and final repository hygiene checks.
- SKILLS CONSIDERED: `using-superpowers`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  VERIFY=`verification-before-completion`
- WHY SELECTED: completion claims require fresh command evidence.
- REJECTED: performance optimization — projection remains a small local data
  validation path and no regression signal was observed.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: unittest discovery, `git diff --check`, JSON/schema fixture validation,
  secret/private-path scans
- INPUT ARTIFACTS: all changed code, fixtures, schemas, docs
- OUTPUT ARTIFACTS: 75 passing tests; clean diff check
- EVIDENCE REQUIRED: no failing tests, no whitespace errors, no secrets or
  private local paths, no Phase 3 implementation
- RESULT: PASS

### HANDOFF

- ROUTE: `R-PHASE26-HANDOFF`; STATUS: `SKILLS_SELECTED`
- OBJECTIVE: synchronize canonical docs and update the next-task prompt without
  executing Phase 3.
- SKILLS CONSIDERED: `using-superpowers`, `verification-before-completion`
- SKILLS SELECTED / ROLE: GATE=`using-superpowers`;
  VERIFY=`verification-before-completion`
- WHY SELECTED: preserve the resident authority and hand off only verified
  provenance requirements.
- REJECTED: all Phase 3 implementation work — explicit stop condition.
- AGENT/RUNTIME: Codex / `codex-cli 0.153.4`; MODEL PROFILE: not recorded
- TOOLS: canonical Markdown edits and link review
- INPUT ARTIFACTS: updated Codex mapping, contract fixtures, test results
- OUTPUT ARTIFACTS: synchronized v3 docs and `NEXT_CODEX_PROMPT.md`
- EVIDENCE REQUIRED: every future runtime lane records installed version,
  release/tag→commit, source snapshot, docs snapshot, support, availability
- RESULT: PASS; Phase 3 prompt updated only, not executed

## Contract consistency and source findings

- BLOCKING: none after source verification.
- IMPORTANT: Phase 2.5 conflated installed `codex-cli 0.153.4` with the
  `45305dd` source snapshot. The full schemas differ even though the six
  projected field shapes are identical.
- MINOR: current documentation pages can mention historical/alternate values;
  the immutable release schema remains authoritative for executable projection.

## Provenance verdict

| Check | Verdict |
|---|---|
| Installed runtime → official release commit | `VERIFIED` |
| Installed release narrow contract | `INSTALLED_RUNTIME` |
| `45305dd` source snapshot | `SOURCE_SNAPSHOT / UPSTREAM_ONLY` |
| Support vs availability | separate fields |
| Unknown runtime or revision | `RUNTIME_CONTRACT_UNVERIFIED` |
| Runtime network lookup | none |
| Phase 3 started | no |
