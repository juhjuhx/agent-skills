# Stage Router Evaluation v1

> Phase 3A evidence. This report records the first machine-executable
> stage-local routing run over the repository's current catalog. It records
> observable route data and evaluation judgments, not hidden model reasoning.

## Run identity

- **TASK:** Agent Skills Matrix v3 Phase 3A — Stage Router Intelligence MVP
- **START_HEAD:** 7ed948c18c4f69c2fcba34830ddf893e9932fb2b
- **BRANCH:** feat/v3-stage-router-mvp
- **REGISTRY:** .superpowers/SKILLS_INDEX.json
- **REGISTRY_EPOCH:** registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac
- **CATALOG:** 214 records; current registry source commit
  db3b67d5b051c4223da9146b2b836a9ed45e9bac
- **ROUTER:** tools/v3/stage_router.py; deterministic metadata-only baseline
- **RUNTIME:** Codex adapter as the route consumer
- **MODEL PROFILE:** unselected; Phase 3A does not route models

### TaskSpec summary

~~~yaml
task_id: T-v3-stage-router-mvp
task_type: implementation
complexity: COMPLEX
risk: MEDIUM
ambiguity: MEDIUM
architecture_impact: ARCHITECTURE-CHANGING
domains: [software-engineering, orchestration, testing]
required_capabilities: [needs_editing, needs_sandbox, needs_structured_output]
permission_level: workspace-write
context_budget: max_input_tokens=12000
objectives:
  - route each active stage independently
  - evaluate ten representative workloads
  - prove a StageRoute is consumable by CodexAdapter
~~~

### Deep Understanding

DEEP_UNDERSTANDING: USED_WITH_SAFE_FALLBACK.

The installed deep-understanding workflow was loaded/attempted because this
task defines durable cross-agent routing contracts and is
architecture-changing. Its external dependency was unavailable, so the
workflow's safe fallback was used and recorded in
[PHASE3A_DEEP_UNDERSTANDING.md](PHASE3A_DEEP_UNDERSTANDING.md). The repository
catalog has no deep-understanding record, so every complex route records
UNAVAILABLE rather than inventing a candidate. Simple/low-risk fixtures
record OFF.

## Dogfood stage routing

The resident using-superpowers authority created the following active
stages. Each stage was routed independently. In the table,
filtered_count means records with at least one rejection reason; the
resident gate is included in candidate_count but excluded from normal
candidate scoring.

| Stage | Route result | Selected skills (role) | Candidates / filtered / eligible | Role coverage | Duplicate-role pressure | Context estimate | Route latency |
|---|---|---|---:|---|---:|---:|---:|
| understand | SKILLS_SELECTED | using-superpowers (GATE); understand (PROCESS); brooks-audit (DOMAIN) | 214 / 207 / 6 | GATE, PROCESS, DOMAIN | 0 | 1,200 B | 3,627.308 ms |
| research | SKILLS_SELECTED | using-superpowers (GATE); wiki-builder (PROCESS); baoyu-url-to-markdown (TOOL) | 214 / 207 / 6 | GATE, PROCESS, TOOL | 0 | 936 B | 2,280.483 ms |
| design | SKILLS_SELECTED | using-superpowers (GATE); grill-with-docs (PROCESS); improve-codebase-architecture (DOMAIN); brooks-review (REVIEW); verification-before-completion (VERIFY) | 214 / 206 / 7 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 0 | 1,984 B | 2,475.479 ms |
| plan | SKILLS_SELECTED | using-superpowers (GATE); writing-plans (PROCESS) | 214 / 208 / 5 | GATE, PROCESS | 0 | 240 B | 1,020.044 ms |
| implement | SKILLS_SELECTED | using-superpowers (GATE); test-driven-development (PROCESS); verification-before-completion (VERIFY) | 214 / 204 / 9 | GATE, PROCESS, VERIFY | 0 | 404 B | 535.361 ms |
| review | SKILLS_SELECTED | using-superpowers (GATE); codebase-inspection (PROCESS); code-review-excellence (REVIEW); logic-review (REVIEW); verification-before-completion (VERIFY) | 214 / 192 / 21 | GATE, PROCESS, REVIEW, VERIFY | 1 | 964 B | 490.625 ms |
| verify | SKILLS_SELECTED | using-superpowers (GATE); verification-before-completion (VERIFY) | 214 / 209 / 4 | GATE, VERIFY | 0 | 300 B | 627.971 ms |
| harden | SKILLS_SELECTED | using-superpowers (GATE); safe-mode (PROCESS); code-review-excellence (REVIEW); verification-before-completion (VERIFY) | 214 / 202 / 11 | GATE, PROCESS, REVIEW, VERIFY | 0 | 700 B | 474.901 ms |
| handoff | SKILLS_SELECTED | using-superpowers (GATE); finishing-a-development-branch (PROCESS); verification-before-completion (VERIFY) | 214 / 202 / 11 | GATE, PROCESS, VERIFY | 0 | 564 B | 460.815 ms |

For every row:

- **OBJECTIVE:** the stage objective shown in the stage definition and
  summarized by the row.
- **SKILLS CONSIDERED:** all 214 metadata records; no body was read for
  ranking. The route's rejected_candidates contains machine-readable
  reasons for the first 32 rejected records.
- **AGENT/RUNTIME:** Codex.
- **MODEL PROFILE:** unselected; no model decision is made here.
- **TOOLS:** route-declared tool requirements were []; operational
  inspection used the repository filesystem, Git, rg, Python standard
  library, and test runner. No MCP server, browser, or subagent was loaded.
- **INPUT ARTIFACTS:** the TaskSpec above, the stage definition, the pinned
  registry epoch, and the read-only compatibility metadata view.
- **OUTPUT ARTIFACTS:** one validated StageRoute with selected references,
  role assignments, route reasons, alternatives, and routing_evidence.
- **EVIDENCE REQUIRED:** the stage-specific evidence listed below.
- **RESULT:** explicit SKILLS_SELECTED; no active dogfood stage needed a
  NO_SKILL_NEEDED result.

### Stage records

#### UNDERSTAND

- **OBJECTIVE:** Establish source truth, boundaries, and evaluation questions.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE / resident
  authority; understand / PROCESS / repository orientation; brooks-audit
  / DOMAIN / source and architecture audit.
- **SKILLS REJECTED / WHY:** broad legacy entries such as Agent Development,
  Command Development, Hook Development, MCP Integration, and Plugin Structure
  were rejected because their routing fields were not curated; Plugin Settings
  additionally lacked the requested repository/architecture domain. Deep
  Understanding was eligible by task signals but unavailable in the supplied
  registry.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; Git, rg, filesystem inspection.
- **INPUT ARTIFACTS:** TaskSpec, registry, v3 architecture docs.
- **OUTPUT ARTIFACTS:** TaskSpec classification, route
  route:T-v3-stage-router-mvp:understand:44f71c27be4cabdb.
- **EVIDENCE REQUIRED:** repository truth; classification.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 207 filtered, 3 selected,
  body files loaded 0.

#### RESEARCH

- **OBJECTIVE:** Inspect the actual catalog and existing evidence.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE / authority;
  wiki-builder / PROCESS / evidence synthesis; baoyu-url-to-markdown
  / TOOL / source/citation capture.
- **SKILLS REJECTED / WHY:** uncurated agent/plugin/hook entries were rejected
  for missing curated routing fields; frontend and security procedures were
  stage/domain mismatches; mcp-audit was not relevant without an MCP
  objective. No exact source-driven metadata record was available in the
  current registry.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; registry reader, rg, filesystem
  inspection. No MCP was loaded.
- **INPUT ARTIFACTS:** TaskSpec, current registry, historical dogfood traces.
- **OUTPUT ARTIFACTS:** catalog audit and route
  route:T-v3-stage-router-mvp:research:14bed530db70e606.
- **EVIDENCE REQUIRED:** registry inspection.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 207 filtered, 3 selected,
  body files loaded 0.

#### DESIGN

- **OBJECTIVE:** Define filters, scoring, role coverage, and graph behavior.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  grill-with-docs / PROCESS / decision and context record;
  improve-codebase-architecture / DOMAIN / architecture boundary;
  brooks-review / REVIEW / independent architecture quality;
  verification-before-completion / VERIFY / required evidence gate.
- **SKILLS REJECTED / WHY:** uncurated general plugin/hook entries were
  rejected; mcp-audit lacked MCP relevance; implementation-only test
  procedures did not match the design stage; Deep Understanding remained
  unavailable in the repository catalog.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; documentation editor, Python standard
  library, schema validator.
- **INPUT ARTIFACTS:** Phase 1 contracts, Codex bundle/adapter contracts,
  deep-understanding record.
- **OUTPUT ARTIFACTS:** router design, decision evidence, route
  route:T-v3-stage-router-mvp:design:1c10499cd7b24c5a.
- **EVIDENCE REQUIRED:** design review.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 206 filtered, 5 selected,
  body files loaded 0.

#### PLAN

- **OBJECTIVE:** Sequence the bounded MVP implementation.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  writing-plans / PROCESS / ordered implementation plan.
- **SKILLS REJECTED / WHY:** uncurated agent/plugin/hook entries were rejected;
  review, frontend, security, and MCP procedures were not required by this
  plan stage; no route quota was used to add them.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; repository inspection and plan editor.
- **INPUT ARTIFACTS:** design route and contract boundaries.
- **OUTPUT ARTIFACTS:** implementation plan, route
  route:T-v3-stage-router-mvp:plan:cb4452b94c54a1c8.
- **EVIDENCE REQUIRED:** plan evidence.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 208 filtered, 2 selected,
  body files loaded 0.

#### IMPLEMENT

- **OBJECTIVE:** Implement the router and read-only compatibility view.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  test-driven-development / PROCESS / executable regression loop;
  verification-before-completion / VERIFY / test/diff evidence.
- **SKILLS REJECTED / WHY:** architecture, frontend, security, and MCP
  procedures were rejected as non-required for this bounded implementation
  stage; broad legacy entries were rejected for missing curated fields.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; Python, unittest, filesystem, Git.
- **INPUT ARTIFACTS:** StageRoute schema, compatibility importer, design/plan
  artifacts.
- **OUTPUT ARTIFACTS:** router/scoring/graph implementation and route
  route:T-v3-stage-router-mvp:implement:305772f1a2df4e7d.
- **EVIDENCE REQUIRED:** tests; diff.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 204 filtered, 3 selected,
  body files loaded 0.

#### REVIEW

- **OBJECTIVE:** Independently review correctness and relevance.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  codebase-inspection / PROCESS / source inspection;
  code-review-excellence / REVIEW / API/code quality;
  logic-review / REVIEW / independent logic/routing review;
  verification-before-completion / VERIFY / evidence gate.
- **SKILLS REJECTED / WHY:** tdd and implementation-only skills were
  task-mode mismatches; frontend and MCP skills had no relevance; uncurated
  plugin/hook records were rejected for missing routing metadata.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; rg, Python, unittest, diff review.
- **INPUT ARTIFACTS:** implementation diff, StageRoute schema, routing fixtures.
- **OUTPUT ARTIFACTS:** review findings, route
  route:T-v3-stage-router-mvp:review:fc383c07e44a3d6d.
- **EVIDENCE REQUIRED:** code review; security review.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 192 filtered, 5 selected,
  body files loaded 0. Duplicate REVIEW pressure = 1 because two independent
  review outputs were required; this is recorded rather than hidden.

#### VERIFY

- **OBJECTIVE:** Run fixtures, tests, and measurements.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  verification-before-completion / VERIFY / test and evidence completion.
- **SKILLS REJECTED / WHY:** process, domain, security, and MCP candidates
  lacked a required signal for this verification-only stage; no minimum quota
  added unrelated procedures.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; Python unittest, JSON/schema validation,
  timing and file-size measurement.
- **INPUT ARTIFACTS:** ten fixtures, router output, implementation diff.
- **OUTPUT ARTIFACTS:** verification report and route
  route:T-v3-stage-router-mvp:verify:df10f46207419358.
- **EVIDENCE REQUIRED:** tests; verification.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 209 filtered, 2 selected,
  body files loaded 0.

#### HARDEN

- **OBJECTIVE:** Check trust, capability, budget, and anti-bloat boundaries.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  safe-mode / PROCESS / conservative safety boundary;
  code-review-excellence / REVIEW / quality and permission review;
  verification-before-completion / VERIFY / hardening evidence.
- **SKILLS REJECTED / WHY:** mcp-audit had no MCP relevance; frontend and
  performance skills had no requested signal; uncurated plugin/hook records
  were rejected before scoring.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; source scan, tests, diff, metadata
  inspection. No new MCP/server/tool authority.
- **INPUT ARTIFACTS:** route evidence, trust/compatibility code, schema and
  security boundaries.
- **OUTPUT ARTIFACTS:** hardening findings and route
  route:T-v3-stage-router-mvp:harden:4bf75b6faa2b65eb.
- **EVIDENCE REQUIRED:** security review; anti-bloat.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 202 filtered, 4 selected,
  body files loaded 0.

#### HANDOFF

- **OBJECTIVE:** Package evidence, limitations, and the Phase 3B prompt.
- **SKILLS SELECTED / ROLE / WHY:** using-superpowers / GATE;
  finishing-a-development-branch / PROCESS / release/handoff checklist;
  verification-before-completion / VERIFY / final evidence.
- **SKILLS REJECTED / WHY:** unrelated implementation, frontend, MCP, and
  security procedures were rejected; release procedure alternatives were not
  selected because the selected handoff procedure covered the required output.
- **AGENT/RUNTIME:** Codex. **MODEL PROFILE:** unselected.
- **TOOLS:** route requirements []; Git status/diff, tests, documentation
  inspection.
- **INPUT ARTIFACTS:** all route/eval evidence, implementation commits,
  Phase 3B prompt.
- **OUTPUT ARTIFACTS:** handoff record and route
  route:T-v3-stage-router-mvp:handoff:17ad520fcbb180d1.
- **EVIDENCE REQUIRED:** handoff evidence.
- **RESULT:** SKILLS_SELECTED; 214 inspected, 202 filtered, 3 selected,
  body files loaded 0.

## Procedures actually used by the dogfood session

These are the installed workflows loaded and followed while performing the
work. They are separate from route ranking: the Phase 3A router intentionally
stops at metadata-only StageRoute; downstream body loading is still owned
by the resolver/adapter.

| Installed procedure | Use |
|---|---|
| using-superpowers | task/session authority, stage boundaries, evidence gate |
| deep-understanding | attempted escalation; dependency-unavailable safe fallback |
| addyosmani-source-driven-development | current source/registry inspection |
| addyosmani-api-and-interface-design | contract boundary review |
| addyosmani-planning-and-task-breakdown | bounded implementation plan |
| addyosmani-test-driven-development | regression-first test design |
| code-review-excellence | independent code/route review |
| addyosmani-code-simplification | anti-bloat review |
| addyosmani-security-and-hardening | trust/capability/security review |
| verification-before-completion | final validation and evidence gate |

The machine router selected only catalog IDs that exist in the current
registry. It did not claim that every selected ID above was body-loaded
during ranking; route output and execution loading are intentionally separate.

## Ten routing fixtures

All ten fixtures are in
[fixtures/v3/router/routing-eval-v1.json](../../../fixtures/v3/router/routing-eval-v1.json)
and use actual IDs from the current 214-record registry. The expected groups
are acceptance boundaries, not hard-coded router branches.

| Fixture | Machine route | Selected skills (role) | Evaluation judgment |
|---|---|---|---|
| A README typo | NO_SKILL_NEEDED | none | **PASS** — 214 considered, 0 selected, Deep Understanding OFF; no architecture/security/performance/MCP route |
| B ordinary bug | SKILLS_SELECTED | using-superpowers GATE; diagnose PROCESS; tdd PROCESS; verification-before-completion VERIFY | **PASS** — debugging, test, and verification coverage; one PROCESS duplicate is a useful procedure complement |
| C API architecture | SKILLS_SELECTED | using-superpowers GATE; grill-with-docs PROCESS; improve-codebase-architecture DOMAIN; brooks-review REVIEW; verification-before-completion VERIFY | **PASS WITH GAP** — all required role slots covered; API-specific metadata is sparse, so grill-with-docs is the evidence-oriented proxy |
| D large frontend | SKILLS_SELECTED | using-superpowers GATE; frontend-design PROCESS; image-to-code DOMAIN; fixing-accessibility REVIEW; baseline-ui VERIFY; verification-before-completion VERIFY | **PASS WITH PRESSURE** — frontend, implementation, accessibility, and verification; two VERIFY skills are retained for distinct UI/evidence outputs |
| E security-sensitive change | SKILLS_SELECTED | using-superpowers GATE; safe-mode PROCESS; permission-tuner REVIEW; verification-before-completion VERIFY | **PASS** — security skill activates conditionally; no MCP audit without MCP relevance |
| F deep source research | SKILLS_SELECTED | using-superpowers GATE; wiki-research-loop PROCESS; verification-before-completion VERIFY | **PASS WITH GAP** — research and verification are covered; exact source-driven metadata is absent and wiki-research-loop is the closest catalog signal |
| G visual design | SKILLS_SELECTED | using-superpowers GATE; baoyu-slide-deck PROCESS; design-taste-frontend DOMAIN | **PASS** — visual route stays out of generic coding/TDD/security paths |
| H GitHub repository audit | SKILLS_SELECTED | using-superpowers GATE; codebase-inspection PROCESS; logic-review REVIEW; verification-before-completion VERIFY | **PASS** — source inspection, review, and verification coverage |
| I product specification | SKILLS_SELECTED | using-superpowers GATE; brainstorming PROCESS; grill-with-docs PROCESS; to-prd DOMAIN | **PASS WITH PRESSURE** — discovery and product-spec coverage; two PROCESS skills have distinct requirements/decision outputs; no premature implementation |
| J release gate | SKILLS_SELECTED | using-superpowers GATE; finishing-a-development-branch PROCESS; brooks-test REVIEW; logic-review REVIEW; verification-before-completion VERIFY | **PASS WITH PRESSURE** — release, review, test, and verification; two REVIEW skills reflect separate review artifacts |

### Fixture metrics

| Fixture | Candidates | Filtered | Selected | Role coverage | Duplicate-role pressure | Context estimate | Tool requirements | Trust blocks | Body files loaded by router |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|
| A | 214 | 213 | 0 | — | 0 | 0 B | — | 0 | 0 |
| B | 214 | 206 | 4 | GATE, PROCESS, VERIFY | 1 | 732 B | — | 0 | 0 |
| C | 214 | 208 | 5 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 0 | 1,984 B | — | 0 | 0 |
| D | 214 | 207 | 6 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 1 | 1,316 B | — | 0 | 0 |
| E | 214 | 210 | 4 | GATE, PROCESS, REVIEW, VERIFY | 0 | 616 B | — | 0 | 0 |
| F | 214 | 208 | 3 | GATE, PROCESS, VERIFY | 0 | 912 B | — | 0 | 0 |
| G | 214 | 205 | 3 | GATE, PROCESS, DOMAIN | 0 | 448 B | — | 0 | 0 |
| H | 214 | 192 | 4 | GATE, PROCESS, REVIEW, VERIFY | 0 | 644 B | — | 0 | 0 |
| I | 214 | 206 | 4 | GATE, PROCESS, DOMAIN | 1 | 812 B | — | 0 | 0 |
| J | 214 | 202 | 5 | GATE, PROCESS, REVIEW, VERIFY | 1 | 1,988 B | — | 0 | 0 |

filtered is a rejection count, not a claim that every omitted legacy record
is intrinsically bad. The large value is primarily a metadata quality signal.

## Historical dogfood comparison

Historical traces are loaded from
[fixtures/v3/router/historical-dogfood-v1.json](../../../fixtures/v3/router/historical-dogfood-v1.json)
and the Phase 1/2/2.5/2.6 evidence files. They were human/model-selected
StageRoute-shaped traces without labeled ground truth.

| Historical phase | Comparison | Evidence |
|---|---|---|
| Phase 1 | **AMBIGUOUS; ROUTER_BETTER on stage locality, DOGFOOD_BETTER on explicit source/design/security procedure intent** | Manual route selected a broad contract/review set; the MVP adds per-stage filtering and explicit no-quota role coverage |
| Phase 2 | **AMBIGUOUS; EQUIVALENT for TDD/verification overlap, ROUTER_BETTER on conditional routing, DOGFOOD_BETTER where sparse metadata hides MCP/source intent** | Both expose test/verification; Phase 2 manually named mcp-audit and source-driven work that current legacy metadata cannot always recover |
| Phase 2.5 | **AMBIGUOUS; EQUIVALENT for conformance/review/verification intent, DOGFOOD_BETTER for source/security detail** | Manual review emphasized source, API, security, simplification; MVP reports gaps instead of inferring all of them |
| Phase 2.6 | **AMBIGUOUS; ROUTER_BETTER for deterministic stage records and no fixed quota, DOGFOOD_BETTER for explicit provenance research** | Runtime-provenance trace was manually staged; Phase 3A remains model-agnostic and records the missing metadata |

These labels are comparison judgments, not training labels. Historical success is
not a production score and does not change routing policy.

## Over-routing findings

1. **Initial legacy inference was too broad.** Before the curated-field
   eligibility boundary was added, generic legacy descriptions could produce
   candidates such as brooks-harness, plugin, and hook procedures from keyword
   overlap alone. The current route rejects records whose roles, stages, and
   domains are only uncurated inference with reason
   legacy metadata lacks curated routing fields.
2. **Review-stage duplicate pressure = 1.** code-review-excellence and
   logic-review both cover requested review outputs. The duplication is
   visible and justified for independent review evidence, not a fixed quota.
3. **Frontend duplicate VERIFY pressure = 1.** baseline-ui and
   verification-before-completion cover different UI and general evidence
   obligations. This is a candidate for a future relationship/metadata
   refinement, not a fixture-specific exception.
4. **Product-spec duplicate PROCESS pressure = 1.** brainstorming and
   grill-with-docs represent discovery and decision/context work. The report
   keeps the pressure observable.

## Under-routing findings

1. The current registry has no deep-understanding record even though the
   installed local workflow exists. Complex routes therefore record
   UNAVAILABLE, a safe limitation rather than a hidden activation.
2. No exact source-driven/API-specific metadata exists for all relevant
   concepts. Research and API fixtures use the closest actual catalog
   procedures and are marked PASS WITH GAP.
3. MCP is conditional by design, but the old registry does not expose rich
   MCP/tool-schema requirements for most skills. No MCP audit is selected
   without an explicit MCP domain/capability signal.
4. Model profiles and runtime-specific capabilities are intentionally not
   scored in Phase 3A. Cross-agent/model evidence belongs to Phase 3B.

## Metadata gaps

The 214 current records contain the v1 identity/description/trigger/category
shape rather than complete v3 routing metadata. The compatibility view records
missing fields instead of pretending they were source-authored:

- no canonical roles, stages, task modes, domains, capability requirements,
  costs, relationships, or routing eval status for most records;
- provenance fields such as license/import date remain unavailable;
- a small, auditable compatibility hint map exists only to expose high-signal
  current procedures and is marked as a derived view;
- inferred fields are never treated as strong enough when all core routing fields
  are uncurated;
- the production registry and v2 ROUTING_POLICY.yaml were not migrated or
  changed.

The next metadata work should add curated records and relationships, then
replace compatibility hints with source-authored data. It should not patch
individual fixtures with task-name exceptions.

## Context and performance evidence

Measurements used the current 214-record registry and the ten routing fixtures:

- metadata records inspected per route: **214**;
- SKILL.md files loaded by the router: **0**;
- hypothetical all-catalog canonical body bytes (file-size proxy):
  **2,155,285 B across 214 files**;
- selected-only body bytes if the downstream resolver executes each fixture
  route (resident using-superpowers excluded):
  **0, 15,662, 14,697, 52,431, 13,445, 9,626, 108,127, 21,151, 17,402,
  26,422 B** for fixtures A–J respectively;
- average selected-only body bytes: **27,896 B**, approximately **1.29%** of
  the all-catalog body-byte proxy per fixture. This is a byte-size estimate,
  not a token-savings claim;
- route context estimate from selected metadata: **0, 732, 1,984, 1,316, 616,
  912, 448, 644, 812, 1,988 B** for fixtures A–J;
- warm ten-fixture routing benchmark: mean **488.394 ms**, median **437.071 ms**,
  minimum **377.242 ms**, maximum **876.429 ms** in one local run;
- the first dogfood process included cold schema/file effects and ranged from
  **460.815 ms to 3,627.308 ms**. This did not justify a performance framework.

The router does not load the all-catalog hypothetical body set. The selected
body sizes are a separate downstream-resolution estimate measured with file
metadata, preserving the metadata-first boundary.

## Codex end-to-end integration

Test:
CodexEndToEndRouterTests.test_router_output_is_consumable_by_codex_adapter.

The path is:

~~~text
TaskSpec
  -> StageRouter (using-superpowers resident GATE + selected metadata)
  -> validated StageRoute
  -> CodexAdapter
  -> CompiledExecutionBundle
  -> CodexNativeProjection
~~~

The test uses actual registry IDs using-superpowers, tdd, and
verification-before-completion, validates the route, resolves selected
metadata, and compiles the portable bundle/native projection without external
runtime side effects. No other runtime adapter or model router was implemented.

## Review and verification status

- **Tests:** focused Stage Router/evaluation suite passed 21/21 and the full
  repository suite passed 96/96. Ruff lint and format checks passed; final
  JSON/link/diff scans are recorded in the PR validation.
- **Independent review lanes:** codebase inspection/code review, simplification,
  security/hardening, and verification were run independently. Findings are
  represented above; no reviewer conclusion was used as hidden router input.
- **OpenCodeReview:** one CLI precheck reported open-code-review v1.11.6, but
  the configured provider endpoint was unreachable by DNS. No native diff
  review was claimed: OCR_NATIVE_DIFF = BLOCKED_BY_NETWORK. A delegate result,
  if any, would be kept under OCR_DELEGATE and never relabeled native OCR.
- **Anti-bloat:** implementation remains three small modules plus tests and
  schema evidence. No RouterManager, RoutingService, GraphManager, database,
  scheduler, worker pool, plugin framework, or model router was added.

## Limitations

Phase 3A proves deterministic skill selection over a sparse compatibility view;
it does not prove that every route is semantically optimal. The documented
metadata gaps, duplicate-role pressure, Deep Understanding unavailability,
and research proxy are deliberate evaluation findings. Phase 3B should measure
runtime/model choices from these route artifacts rather than hide the failures
with fixture-specific branches.
