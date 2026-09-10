# Phase 3C.2 OpenCode Dogfood Route

This trace records the first Phase 3C.2 development run through the
repository's current v3 Stage Router. It contains explicit route outputs and
operational evidence only; it does not contain hidden model reasoning.

## Task

- **TASK:** build and verify a benchmark-safe, read-only OpenCode 1.18.25
  projection for the existing StageRoute and gated H03 smoke
- **START_HEAD:** `20401eeea8eb60bdd87081d923f9cb78fb5eb049`
- **WORKING_BRANCH:** `feat/v3-opencode-readonly-adapter`
- **Task mode:** bounded native adapter / execution-boundary verification
- **Risk:** high for permission and evidence integrity; no production write,
  deployment, credential, MCP, plugin, or global-config mutation
- **Catalog snapshot:** `registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac`
- **Metadata records:** 214
- **Normal route body files loaded:** 0
- **using-superpowers:** resident task/session authority; its full body was
  not reloaded as an ordinary skill on every stage

## TaskSpec summary

```yaml
task_id: T-v3-phase3c2-opencode-dogfood
objective: consume validated StageRoute through a narrow OpenCode read-only boundary
scope: tools/v3, schemas/v3, fixtures/v3, tests/v3, docs/v3
complexity: COMPLEX
risk: HIGH
ambiguity: MEDIUM
permission: read-only isolated fixture; no network; no external write; no secrets
required_capabilities: [needs_sandbox, needs_structured_output]
stop_conditions: [no --auto, no global config mutation, no H03 after failed smoke]
```

`DEEP_UNDERSTANDING: NOT_USED` — no installed skill with the exact
`deep-understanding` identity was present in the canonical registry. The task
was bounded to an already-defined adapter contract, so uncertainty was
handled by first-party source checks, explicit no-ASK validation, and a gated
runtime smoke rather than by inventing a substitute capability.

## Stage routes

Each stage was routed independently. `SKILLS_CONSIDERED` means metadata
records considered by the current router; it does not mean that all skill
bodies were read.

### UNDERSTAND

- **OBJECTIVE:** establish the installed runtime, branch boundary, and exact
  least-privilege problem.
- **SKILLS_CONSIDERED:** 214 records; 213 filtered; 0 executable candidates.
- **SKILLS_SELECTED:** `NO_SKILL_NEEDED`.
- **ROLE SLOT:** none.
- **WHY_SELECTED:** the repository truth and phase boundary were explicit;
  another procedure would add no required evidence.
- **SKILLS_REJECTED:** all candidates failed the stage relevance/capability
  gate; Deep Understanding was not available as an installed exact skill.
- **AGENT/RUNTIME:** Codex host; OpenCode target not yet invoked.
- **MODEL PROFILE:** unselected by the Stage Router.
- **TOOLS:** `git`, local CLI help, repository reads.
- **INPUT ARTIFACTS:** Phase 3C.1 evidence and current contracts.
- **OUTPUT ARTIFACTS:** source-truth checklist and TaskSpec summary.
- **EVIDENCE REQUIRED:** branch/head/version facts.
- **RESULT:** `NO_SKILL_NEEDED`; source truth established.

### RESEARCH

- **OBJECTIVE:** verify OpenCode 1.18.25 CLI, permission, config, run, skill,
  plugin, and MCP surfaces from installed help and first-party source.
- **SKILLS_CONSIDERED:** 214 records; 212 filtered; 1 eligible candidate.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident),
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** the gate supplied task authority and verification supplied
  the source/version evidence discipline.
- **SKILLS_REJECTED:** unrelated domain and implementation procedures were
  filtered by stage or missing capability; no body was loaded for ranking.
- **AGENT/RUNTIME:** Codex host; OpenCode 1.18.25 research target.
- **MODEL PROFILE:** unselected.
- **TOOLS:** `opencode --version`, `--help`, `run --help`, `agent --help`,
  `mcp --help`, official release/source/docs.
- **INPUT ARTIFACTS:** local CLI output and official OpenCode sources.
- **OUTPUT ARTIFACTS:** pinned native contract and support/availability map.
- **EVIDENCE REQUIRED:** installed version, release commit, exact projected
  fields, no current-main-only assumptions.
- **RESULT:** `SKILLS_SELECTED`; contract revision and permission actions
  recorded.

### DESIGN

- **OBJECTIVE:** design the smallest portable-to-native projection and
  zero-ASK proof.
- **SKILLS_CONSIDERED:** 214 records; 212 filtered; 1 eligible candidate.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident),
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** the change is a boundary contract; explicit evidence and
  deterministic data flow are more relevant than a broad architecture method.
- **SKILLS_REJECTED:** managers, registries, services, schedulers, and generic
  model-routing procedures were not eligible or were outside scope.
- **AGENT/RUNTIME:** Codex host; OpenCode projection target.
- **MODEL PROFILE:** unselected.
- **TOOLS:** existing bundle/permission/evidence modules, schema inspection.
- **INPUT ARTIFACTS:** TaskSpec, StageRoute, AgentAdapterManifest,
  ModelProfile, Codex bundle pattern.
- **OUTPUT ARTIFACTS:** `OpenCodeNativeProjection`, narrow contract fixture,
  no-ASK permission map.
- **EVIDENCE REQUIRED:** runtime-neutral bundle remains free of OpenCode
  branch logic; native values are checked against the pinned contract.
- **RESULT:** `SKILLS_SELECTED`; design remained data plus pure validators.

### PLAN

- **OBJECTIVE:** sequence unit tests, contract smoke, H03 gate, evidence
  recording, and independent review.
- **SKILLS_CONSIDERED:** 214 records; 213 filtered; 0 executable candidates.
- **SKILLS_SELECTED:** `NO_SKILL_NEEDED`.
- **ROLE SLOT:** none.
- **WHY_SELECTED:** the user-supplied two-step smoke-before-H03 gate was
  already a complete plan and did not need another planning procedure.
- **SKILLS_REJECTED:** planning candidates did not clear stage relevance;
  no minimum activation quota was applied.
- **AGENT/RUNTIME:** Codex host; OpenCode target remains gated.
- **MODEL PROFILE:** unselected.
- **TOOLS:** unittest, schema validator, bounded subprocess runner.
- **INPUT ARTIFACTS:** design outputs and safety stop conditions.
- **OUTPUT ARTIFACTS:** test/verification order and live-lane decision gate.
- **EVIDENCE REQUIRED:** no H03 invocation unless smoke has no unresolved
  ASK path and completes.
- **RESULT:** `NO_SKILL_NEEDED`; bounded plan followed.

### IMPLEMENT

- **OBJECTIVE:** implement contract validation, read-only projection,
  selected-only references, bounded invocation, and tests.
- **SKILLS_CONSIDERED:** 214 records; 210 filtered; 3 eligible candidates.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident),
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** implementation was constrained by the existing contracts;
  verification was needed to prevent unsupported native fields and permission
  widening.
- **SKILLS_REJECTED:** broad adapter frameworks and unrelated runtime adapter
  procedures were outside the vertical slice; no Stage Router was imported.
- **AGENT/RUNTIME:** Codex host; OpenCode 1.18.25 projection.
- **MODEL PROFILE:** fixture profile used only for contract separation tests;
  no live model selection.
- **TOOLS:** `apply_patch`, Python unittest, contract validator.
- **INPUT ARTIFACTS:** existing bundle, permission intersection, resolver,
  LiveExecutionRecord schema.
- **OUTPUT ARTIFACTS:** `opencode_adapter.py`, native contract/projection
  schemas and fixture, focused tests.
- **EVIDENCE REQUIRED:** deterministic projection, explicit denials, no raw
  body/prompt serialization, `shell=False`, `stdin=DEVNULL`.
- **RESULT:** `SKILLS_SELECTED`; static boundary tests passed after the
  permission-order and inherited-config-selector hardening.

### REVIEW

- **OBJECTIVE:** independently inspect config conformance, permission
  intersection, serialization, and prohibited-scope changes.
- **SKILLS_CONSIDERED:** 214 records; 210 filtered; 3 eligible candidates.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident), `brandkit`
  **PROCESS**, `permission-tuner` **REVIEW**,
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** the router associated permission review and verification
  with the stage.
- **SKILLS_REJECTED:** the selected `brandkit` procedure is an image/brand-kit
  workflow and is semantically unrelated to this code review.
- **AGENT/RUNTIME:** Codex host; OpenCode target.
- **MODEL PROFILE:** unselected.
- **TOOLS:** source inspection, focused tests, diff review.
- **INPUT ARTIFACTS:** adapter/projection diff and no-ASK proof.
- **OUTPUT ARTIFACTS:** review findings and a routing-defect record.
- **EVIDENCE REQUIRED:** no `ask`, no permission widening, no raw body leak.
- **RESULT:** `SKILLS_SELECTED`; static security boundary passed. The
  `brandkit` selection is recorded as `ROUTING_DEFECT`, not executed.

### VERIFY

- **OBJECTIVE:** validate schemas, selected-only behavior, evidence handling,
  and the gated OpenCode smoke.
- **SKILLS_CONSIDERED:** 214 records; 204 filtered; 9 eligible candidates.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident),
  `brooks-harness` **PROCESS**, `llm-council` **DOMAIN**, `brooks-test`
  **REVIEW**, `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** the router supplied test-quality and evidence checks for
  the implementation boundary.
- **SKILLS_REJECTED:** `brooks-harness` explicitly targets maintenance of its
  own brooks-lint plugin, and `llm-council` would require an external
  multi-provider deliberation that is not needed or authorized here; both were
  read for trigger audit only. `brooks-test` was used as a test-suite review
  lens, not as a request to rewrite tests.
- **AGENT/RUNTIME:** Codex host; OpenCode smoke target.
- **MODEL PROFILE:** unselected for routing; fixture profile only in unit tests.
- **TOOLS:** unittest discovery, JSON Schema validation, isolated subprocess.
- **INPUT ARTIFACTS:** all changed schemas/code and smoke record builder.
- **OUTPUT ARTIFACTS:** test results, sanitized smoke record, evidence report.
- **EVIDENCE REQUIRED:** process result must not self-certify H03 success;
  raw output must remain digest/byte metadata.
- **RESULT:** `SKILLS_SELECTED`; static tests passed and smoke was executed
  only after the no-ASK projection gate.

### HARDEN

- **OBJECTIVE:** close permission-rule ordering, inherited config overrides,
  secret/path boundaries, and fail-closed runtime errors.
- **SKILLS_CONSIDERED:** 214 records; 209 filtered; 4 eligible candidates.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident), `safe-mode`
  **PROCESS**, `brandkit` **DOMAIN**, `permission-tuner` **REVIEW**,
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** `safe-mode` provided the non-destructive operating rule;
  permission review and verification covered the security boundary.
- **SKILLS_REJECTED:** `brandkit` is not a security or runtime-domain skill;
  its selection is a second `ROUTING_DEFECT`. No image procedure was executed.
- **AGENT/RUNTIME:** Codex host; OpenCode child process in a temporary fixture.
- **MODEL PROFILE:** unselected.
- **TOOLS:** permission-order regression, environment-selector regression,
  OCR precheck, sanitized runtime diagnostic.
- **INPUT ARTIFACTS:** generated config and process observation.
- **OUTPUT ARTIFACTS:** explicit no-ASK proof, blocked structured-error
  classification, security findings.
- **EVIDENCE REQUIRED:** wildcard deny, ordered secret denies, no `--auto`,
  no global config mutation, no credential serialization.
- **RESULT:** `SKILLS_SELECTED`; safety controls passed statically; runtime
  smoke remained blocked by an unclassified structured error.

### HANDOFF

- **OBJECTIVE:** publish the narrow boundary, append evidence, and prepare a
  blocker-specific next prompt without starting Phase 4.
- **SKILLS_CONSIDERED:** 214 records; 209 filtered; 4 eligible candidates.
- **SKILLS_SELECTED:** `using-superpowers` **GATE** (resident),
  `verification-before-completion` **VERIFY**.
- **WHY_SELECTED:** the handoff contains verified artifacts and an explicit
  stop decision; no unrelated release or adapter workflow is required.
- **SKILLS_REJECTED:** publication/release and other-runtime procedures were
  outside this stacked branch; no merge or runtime installation occurred.
- **AGENT/RUNTIME:** Codex host; OpenCode result handoff.
- **MODEL PROFILE:** unselected.
- **TOOLS:** diff check, full tests, docs/link scan, Git/GitHub handoff.
- **INPUT ARTIFACTS:** tests, smoke record, source provenance, review notes.
- **OUTPUT ARTIFACTS:** `MODEL_RUNTIME_EVAL_V4.md`, this trace, OpenCode guide,
  and updated `NEXT_CODEX_PROMPT.md`.
- **EVIDENCE REQUIRED:** exact blocker and no quality claim from smoke.
- **RESULT:** `SKILLS_SELECTED`; decision is `OPENCODE_RUNTIME_BLOCKED`.

## Selected body use and routing defects

- `using-superpowers` was read once as the resident authority and not treated
  as a per-stage reload.
- `verification-before-completion`, `permission-tuner`, `safe-mode`, and the
  test-review references were read and applied to the relevant checks.
- `brandkit`, `brooks-harness`, and `llm-council` were read only to audit the
  router's result. Their procedures were not executed because their trigger
  contracts do not match this repository task.
- **ROUTING_DEFECT 1:** `REVIEW` selected `brandkit` as `PROCESS`.
- **ROUTING_DEFECT 2:** `HARDEN` selected `brandkit` as `DOMAIN`.
- **ROUTING_DEFECT 3:** `VERIFY` selected `llm-council` and
  `brooks-harness`; both are trigger-mismatched for this bounded local review.

These defects did not alter Stage Router weights and did not enter the
OpenCode projection. They remain a separate routing-quality backlog item.

## OpenCode execution gate

The adapter compiled both a no-skill smoke route and a selected H03 route.
The no-skill projection inspected no skill bodies; the selected H03 compile
resolved only four selected metadata records and loaded three bodies into
execution-local memory, while its projection contained references/digests only.

The bounded smoke used:

```text
opencode run --pure --format json --agent plan --dir <isolated-fixture> <prompt>
shell=False, stdin=DEVNULL, timeout=30s, OPENCODE_CONFIG_CONTENT, no --auto
```

The generated config had zero `ask` actions and explicit ALLOW/DENY results
for all known permission classes. OpenCode returned a structured
`UnknownError` with no actionable cause, so H03 was not started. The append-only
record is [`live-opencode-contract-smoke-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-opencode-contract-smoke-001.json).
