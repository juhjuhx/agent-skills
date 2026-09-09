# Stage Router Evaluation v3

Status: **Phase 3A.2 routing-quality convergence evidence**. This report
replays the exact ten Phase 3A workloads after generated/curated metadata
separation, negative routing signals, role saturation, relationship
deduplication, and session-resident catalog snapshots. It does not change the
fixture file and does not implement model routing.

## Run identity and method

| Item | Value |
|---|---|
| Task | Agent Skills Matrix v3 Phase 3A.2 — Routing Quality Convergence |
| Start head | dfcf9f2e1e456c58e3471a9ac13b3367718b2a38 |
| Branch | feat/v3-routing-quality |
| Registry | .superpowers/SKILLS_INDEX.json; 214 records |
| Registry source commit | db3b67d5b051c4223da9146b2b836a9ed45e9bac |
| Fixture | fixtures/v3/router/routing-eval-v1.json |
| Fixture SHA-256 | 2fba30276affd2dc92fd0e46687924071c5d0841c424074abff5e83ccce2d264 |
| Compiled overlay | registry/v3/skill-routing-metadata.json |
| Overlay version | v3-routing-metadata-2 |
| Overlay digest | sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b |
| Snapshot | snapshot:2349a6fe70aaf346 |
| Router | tools/v3/stage_router.py |
| Runtime/model | Codex route consumer; model profile unselected |
| Normal ranking body reads | 0 |

V1 is the pre-overlay Stage Router baseline. V2 is the exact enriched replay
that exposed D/H/J review-role regressions. V3 keeps the workload definitions
unchanged and evaluates semantic requirements, not exact historical IDs. The
selected body byte value is a downstream context proxy; the router itself
loads metadata only.

## Evaluation rubric

Each fixture is judged independently on:

| Dimension | Requirement |
|---|---|
| Relevance | selected procedures match the task/stage objective |
| Required capability coverage | required process, domain, tool, review, or verification capability is present when requested |
| Role coverage | selected roles form a minimum sufficient complement |
| Redundancy | same-role selections need independent evidence or a relationship justification |
| Unnecessary context | optional additions justify their incremental instruction/tool cost |
| Safety | trust, negative signals, capability, and body-loading invariants remain intact |
| Verification coverage | required test/source/security/runtime evidence has a VERIFY path |

Historical routes are observations, not ground truth. No synthetic aggregate
quality score is used.

## Exact ten-fixture replay

Route labels use GATE, PROCESS, DOMAIN, REVIEW, and VERIFY suffixes. The
resident using-superpowers reference is not a normal candidate body.

| Fixture | V1 selected | V2 selected | V3 selected | V1 → V3 | V2 → V3 |
|---|---|---|---|---|---|
| A README typo | none; NO_SKILL_NEEDED | none; NO_SKILL_NEEDED | none; NO_SKILL_NEEDED | EQUIVALENT | EQUIVALENT |
| B ordinary bug | using-superpowers, diagnose, tdd, verification-before-completion | same | same | EQUIVALENT | EQUIVALENT |
| C API architecture | using-superpowers, grill-with-docs, improve-codebase-architecture, brooks-review, verification-before-completion | same | same | EQUIVALENT; exact API donor remains a gap | EQUIVALENT |
| D large frontend | using-superpowers, frontend-design, image-to-code, fixing-accessibility, baseline-ui, verification-before-completion | using-superpowers, frontend-design, image-to-code, baseline-ui, code-review-excellence, verification-before-completion | using-superpowers, frontend-design, image-to-code, fixing-accessibility, verification-before-completion | V3_BETTER: preserves frontend/accessibility/VERIFY intent without the V1 duplicate VERIFY role | V3_BETTER: removes redundant review selection |
| E security change | using-superpowers, safe-mode, permission-tuner, verification-before-completion | same | same | EQUIVALENT; proxy evidence remains explicit | EQUIVALENT |
| F source research | using-superpowers, wiki-research-loop, verification-before-completion | same | same | EQUIVALENT; exact source-driven donor remains a gap | EQUIVALENT |
| G visual design | using-superpowers, baoyu-slide-deck, design-taste-frontend | same | same | INCONCLUSIVE: semantic route is stable but context proxy remains high | INCONCLUSIVE |
| H repository audit | using-superpowers, codebase-inspection, logic-review, verification-before-completion | using-superpowers, codebase-inspection, brooks-debt, code-review-excellence, verification-before-completion | using-superpowers, codebase-inspection, logic-review, verification-before-completion | EQUIVALENT: returns to the V1 role complement | V3_BETTER: removes two unneeded review candidates |
| I product specification | using-superpowers, brainstorming, grill-with-docs, to-prd | same | using-superpowers, grill-with-docs, to-prd | EQUIVALENT: no premature implementation; less process redundancy | V3_BETTER on context while preserving semantic coverage |
| J release gate | using-superpowers, finishing-a-development-branch, brooks-test, logic-review, verification-before-completion | using-superpowers, finishing-a-development-branch, brooks-test, code-review-excellence, logic-review, verification-before-completion | using-superpowers, release, brooks-test, logic-review, verification-before-completion | EQUIVALENT: release process plus two evidence lanes and VERIFY | V3_BETTER: no third review pressure point |

V2 previously reported seven equivalent and three historical-better
comparisons. That result is retained as historical evidence of the regression;
V3 is the first replay that removes the D/H/J regression without fixture ID
exceptions.

## Route metrics

| Fixture | V1 filtered / context B | V2 filtered / eligible / context B | V3 filtered / eligible / context B | V3 selected | roles | duplicate pressure |
|---|---:|---:|---:|---:|---|---:|
| A | 213 / 0 | 194 / 19 / 0 | 194 / 19 / 0 | 0 | — | 0 |
| B | 206 / 732 | 201 / 13 / 15,668 | 201 / 13 / 15,668 | 4 | GATE, PROCESS, VERIFY | 1 |
| C | 208 / 1,984 | 192 / 21 / 14,704 | 196 / 17 / 14,704 | 5 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 0 |
| D | 207 / 1,316 | 173 / 40 / 56,568 | 176 / 37 / 48,932 | 5 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 0 |
| E | 210 / 616 | 209 / 4 / 13,448 | 209 / 4 / 13,448 | 4 | GATE, PROCESS, REVIEW, VERIFY | 0 |
| F | 208 / 912 | 187 / 26 / 9,632 | 187 / 26 / 9,632 | 3 | GATE, PROCESS, VERIFY | 0 |
| G | 205 / 448 | 165 / 48 / 108,128 | 166 / 47 / 108,128 | 3 | GATE, PROCESS, DOMAIN | 0 |
| H | 192 / 644 | 167 / 46 / 18,424 | 173 / 42 / 21,156 | 4 | GATE, PROCESS, REVIEW, VERIFY | 0 |
| I | 206 / 812 | 204 / 9 / 17,408 | 204 / 9 / 6,756 | 3 | GATE, PROCESS, DOMAIN | 0 |
| J | 202 / 1,988 | 168 / 45 / 35,276 | 169 / 45 / 21,644 | 5 | GATE, PROCESS, REVIEW, VERIFY | 1 |

Every V3 route inspected all 214 metadata records and loaded zero SKILL.md
bodies. B's one duplicate PROCESS is the two complementary TDD procedures
with an explicit alternative/verification relationship; J's one duplicate
REVIEW is justified by the fixture's explicit review/security/tests evidence
and the two-review saturation limit. No unrelated skill was added to meet a
quota.

## Semantic quality findings

| Fixture | Relevance | Capability/role coverage | Redundancy/context | Verification | Verdict |
|---|---|---|---|---|---|
| A | precise no-skill | no procedure required | zero context | not requested | PASS |
| B | debugging and test discipline | PROCESS plus VERIFY | one related PROCESS pair | present | PASS |
| C | architecture/decision coverage | all requested roles | no duplicate role | present | PARTIAL: API donor gap |
| D | frontend and accessibility coverage | frontend/domain/review/VERIFY | no duplicate role; 48,932 B proxy | present | PASS |
| E | security proxies selected only for security task | security PROCESS/REVIEW/VERIFY | no duplicate role | present | PASS with proxy gap |
| F | evidence-oriented research plus VERIFY | PROCESS/VERIFY | no coding skills | present | PARTIAL: source-driven gap |
| G | visual process/domain | visual roles | stable but 108,128 B proxy | no extra verification requested | PARTIAL: context weak |
| H | source inspection, review, VERIFY | all required roles | no duplicate role | present | PASS |
| I | specification/clarification | PROCESS/DOMAIN | 6,756 B proxy; no implementation | not yet required | PASS |
| J | release, test/review, VERIFY | process, two independent review lanes, VERIFY | 21,644 B proxy; pressure 1 | present | PASS |

The weak routes are visible rather than patched with fixture-specific
exceptions: G needs better visual skill cost/output metadata, C/F need exact
donor provenance, and the current catalog has no exact Deep Understanding
record.

## Historical dogfood replay

Earlier Phase 1, 2, 2.5, and 2.6 traces were replayed as comparison evidence.
They are not labels for correctness:

| Historical phase | Comparison with V3 | Classification | Reason |
|---|---|---|---|
| Phase 1 | intent preserved through current canonical IDs/proxies | AMBIGUOUS | exact source-driven/API/security donors were unavailable in the 214 registry |
| Phase 2 | Codex-focused implementation, provenance, review, and verification remain represented | EQUIVALENT / AMBIGUOUS | adapter execution intent is not a skill-route oracle |
| Phase 2.5 | safety and review boundaries remain conservative | EQUIVALENT | native conformance work is downstream of the skill router |
| Phase 2.6 | source/release provenance remains explicit | EQUIVALENT | runtime-contract evidence is independent of route quality |
| Phase 3A | same ten workloads, with stronger curation/snapshot evidence | MACHINE_BETTER for transparency; AMBIGUOUS for procedure quality | evidence is more explicit, but historical manual selections are not truth |

## Over-routing and under-routing

Over-routing observed or eliminated:

- V2 D selected baseline-ui and code-review-excellence as redundant REVIEW
  candidates. V3 assigns baseline-ui its reviewed UI-review semantics and
  saturates the role after fixing-accessibility.
- V2 H selected brooks-debt and code-review-excellence in addition to the
  needed repository review. V3 returns to codebase-inspection, logic-review,
  and verification.
- V2 J selected three REVIEW procedures. V3 retains two because the stage
  explicitly asks for review, security, tests, and verification evidence.
- G remains a high downstream context proxy. The router did not load the
  108,128 bytes; curation should improve marginal output/cost evidence before
  adding more visual skills.

Under-routing or metadata gaps:

- There is no exact canonical source-driven development, Deep Understanding,
  security-hardening, or API/interface-design record. Proxies remain labeled
  as proxies.
- The dogfood UNDERSTAND route can select understand-diff, but the optional
  knowledge-graph artifact is absent in this repository. That is a runtime
  precondition gap, not proof of successful graph-backed analysis.
- A route operates on metadata only. It cannot infer whether a selected
  procedure's external tool or wiki dependency is available without an
  adapter/capability boundary.
- Agent compatibility and permission fields remain intentionally undeclared
  in the compiled routing metadata; this is conservative but limits future
  capability negotiation.

## Deep Understanding gate

The gate is explicit and fixture-sensitive through task signals, not skill-ID
branches:

| Workload class | V3 gate |
|---|---|
| A simple typo | OFF |
| B ordinary bug | OFF |
| C, D, E, F, H, J complex/high-risk/ambiguous work | ELIGIBLE when the task signals require escalation, but UNAVAILABLE because no exact catalog record exists |
| G standard visual design | OFF |
| I complex product specification | ELIGIBLE by complexity, but UNAVAILABLE in the supplied registry |

No Deep Understanding body is automatically loaded. The installed workflow
outside the repository and the canonical 214-record registry remain separate
evidence sources.

## Context and latency profile

### Snapshot load

The immutable RoutingCatalogSnapshot was loaded once for the replay:

| Component | Median/latest observed ms |
|---|---:|
| JSON parse | 5.767 |
| schema and digest validation | 447.224 |
| metadata compilation in runtime | 0.000 |
| graph construction | 0.066 |
| total cold snapshot load | 472.658 |
| canonical bodies loaded | 0 |

Schema/digest validation remains the cold-load bottleneck. It is not repeated
for each stage route in the same task/session.

### Warm routing

| Measurement | Result |
|---|---:|
| V1 warm-route median baseline | approximately 437.071 ms |
| V2 ten-route median mean | approximately 1,244.79 ms |
| V3 outer warm-route median | 23.714 ms |
| V3 outer warm-route mean | 23.427 ms |
| V3 fixture-median mean | 22.821 ms |
| V3 exact-ten-fixture sum of medians | 228.205 ms |
| V3 nine-active-stage batch median | 216.806 ms |
| V3 nine-active-stage batch mean | 227.231 ms |
| V3 normal route body files | 0 |

The measurements show snapshot reuse materially below the Phase 3A.1 warm
baseline while keeping validation in the one-time load path. They are local
Python wall-clock measurements, not a model-token billing claim. Selected
body byte estimates remain downstream context evidence.

## Acceptance gate

| Gate | Result |
|---|---|
| simple README typo remains NO_SKILL_NEEDED | PASS |
| D/H/J are no worse than V1 | PASS; D and H improve redundancy, J matches the two-review evidence need |
| no new fixture materially worse | PASS, with G explicitly weak/inconclusive rather than hidden |
| Tier-1 metadata is reviewable and provenance-safe | PASS, 55/55 curated |
| normal route body reads remain zero | PASS |
| route output is deterministic | PASS |
| safety invariants remain green | PASS |

**Model-router readiness: READY for a separate evaluation phase.** This means
the Stage Router quality gate passed; it does not mean model routing has been
implemented or that any runtime/model preference has been established.

## Independent review evidence

| Lane | Result | Finding |
|---|---|---|
| routing relevance | PASS with weak-route follow-up | D/H/J regression removed; G and exact donor gaps remain visible |
| architecture/simplification | PASS | generated/curated/snapshot data seams are sufficient; no manager/service hierarchy |
| security/hardening | PASS | trust, negative signals, body-read, and metadata-authority boundaries remain conservative |
| verification | PASS | full unittest suite, schema checks, digest checks, and deterministic replay passed |
| Alibaba OpenCodeReview native diff | OCR_NATIVE_DIFF = BLOCKED_BY_AUTH | one precheck returned HTTP 401; no native OCR pass is claimed |

No external skill body, MCP server, or dependency was executed during metadata
enrichment or normal ranking.
