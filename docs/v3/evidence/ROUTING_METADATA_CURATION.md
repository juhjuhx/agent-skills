# Routing Metadata Curation

Status: **Phase 3A.2 quality-convergence evidence**. This report records
source-first curation and routing behavior; it is not a production registry
migration and it does not promote inferred metadata into policy.

## Source truth and artifacts

| Item | Observed value |
|---|---|
| Task | Agent Skills Matrix v3 Phase 3A.2 — Routing Quality Convergence |
| Start head | dfcf9f2e1e456c58e3471a9ac13b3367718b2a38 |
| Working branch | feat/v3-routing-quality |
| Canonical registry | .superpowers/SKILLS_INDEX.json |
| Registry source commit | db3b67d5b051c4223da9146b2b836a9ed45e9bac |
| Canonical records / bodies | 214 / 214 existing SKILL.md files |
| Generated overlay | [skill-routing-generated.json](../../../registry/v3/skill-routing-generated.json) |
| Curated patches | [skill-routing-curated.json](../../../registry/v3/skill-routing-curated.json) |
| Compiled runtime snapshot | [skill-routing-metadata.json](../../../registry/v3/skill-routing-metadata.json) |
| Generated digest | sha256:c47e2b526b104be10604c27563eb19b763410f89dde01626643260a059a1859b |
| Curated digest | sha256:c9f1177abbec0a565f7e9d3d2e56efeba6b408ae3108e148a97501979a2b37dc |
| Compiled digest | sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b |
| Compiled snapshot | snapshot:2349a6fe70aaf346 |

The canonical body remains the only procedure source. The generated overlay is
maintenance-time inference, the curated file is a small patch layer, and the
compiled overlay is the only runtime routing input. None of these artifacts
copies a second editable skill library.

## Catalog census and quality tiers

The exact catalog census remains in
[CATALOG_ROUTING_METADATA_CENSUS.md](CATALOG_ROUTING_METADATA_CENSUS.md).
The compiled snapshot contains:

| Classification | Records | Share |
|---|---:|---:|
| ROUTING_READY | 65 | 30.4% |
| PARTIAL | 131 | 61.2% |
| AMBIGUOUS | 16 | 7.5% |
| DEPRECATED | 2 | 0.9% |
| **Total** | **214** | **100.0%** |

The quality tiers are a prioritization aid, not a skill quota:

| Tier | Records | Routing-ready | Policy |
|---|---:|---:|---|
| TIER_1_CORE | 55 | 55 | strongest manual/source-first review |
| TIER_2_DOMAIN | 120 | 10 | domain review as evidence accumulates |
| TIER_3_SPECIALIZED | 37 | 0 | conservative inference only |
| TIER_4_DEPRECATED | 2 | 0 | retained for provenance; never executable |

All 55 Tier-1 records have a curated review record. Curated patch coverage is
65 roles, 65 stages, 64 task modes, 65 domains, 1 positive trigger patch, 11
negative-trigger patches, 42 output patches, and 9 sparse relationship edges.
Within Tier 1, the corresponding reviewed-field counts are 55, 55, 54, 55,
1, 10, 39, and the applicable relationship patches. Missing values remain
unknown rather than being filled for symmetry.

The generated-only layer is intentionally less confident: 178 PARTIAL, 34
AMBIGUOUS, and 2 DEPRECATED records. Compilation raises only records with
reviewed role/stage/domain coverage to ROUTING_READY; it does not turn every
generated value into reviewed truth.

## Generated versus curated policy

Generated inference may propose roles, stages, task modes, domains, outputs,
triggers, costs, and sparse relationship candidates. Each field carries
source_skill_digest, generator version, provenance, confidence, and review
status. It may not independently grant filesystem, network, secrets,
publish/delete, destructive, or runtime-compatibility authority.

Curated records are small field patches keyed by canonical skill_id and the
exact canonical body digest. Compilation applies them after generation. A
regeneration therefore preserves reviewed decisions, while a changed body
digest invalidates the patch rather than silently applying stale semantics.
Curated metadata is still routing data: it cannot widen TaskSpec permissions,
trust policy, adapter capabilities, or live sandbox authority.

The extraction process treats body text as untrusted data. It reads frontmatter
and UTF-8 text during explicit maintenance only; it does not run embedded shell,
MCP, URL, install, hook, or script instructions. Normal Stage Router ranking
reads zero canonical body files.

## Curated routing decisions

The curation pass corrected broad semantic assignments that caused the V2
regressions without adding fixture-specific branches:

- baseline-ui is a REVIEW-role UI/accessibility review procedure, not a
  generic VERIFY procedure. Its negative signals exclude repository audit,
  release gate, and security-change work.
- ckm:slides is a visual PROCESS procedure and ckm:design is a visual DOMAIN
  procedure. They are not general implementation reviewers.
- brooks-test is a review/test-evidence procedure with reviewed release/test
  triggers and REVIEW_WITH verification-before-completion.
- code-review-excellence, brooks-debt, logic-review, fixing-motion-performance,
  and visual/UI procedures have conservative negative triggers where their
  bodies explicitly do not fit source research, visual design, release, or
  security contexts.

Negative evidence now has three explicit forms:

| Signal | Match | Effect |
|---|---|---|
| negative_triggers | stage/task text contains the reviewed phrase | score penalty; optional activation is suppressed |
| stage_exclusions | current stage ID is listed | score penalty; optional activation is suppressed |
| domain_exclusions | requested task/stage domain is listed | score penalty; optional activation is suppressed |

A negative signal is not a hard permission policy. A required role may still
select a candidate, and a REQUIRES dependency is never suppressed by an
optional-routing negative signal. The route evidence records the matched signal
and the reason.

## Role saturation and relationship deduplication

The router first covers required role slots (GATE, PROCESS, DOMAIN, TOOL,
REVIEW, VERIFY) and then considers optional complements. It does not take a
fixed top-N list.

- One strong REVIEW candidate is normal.
- A second REVIEW candidate requires explicit independent/adversarial review
  evidence, multiple stage-local evidence lanes, or an explicit
  independent_review_count.
- A third reviewer requires an explicit count; it is never added for quota.
- A second PROCESS candidate is allowed when distinct plan/spec/test evidence
  justifies it.
- ALTERNATIVE_TO normally selects one; SUPERSEDES removes an available
  predecessor; positive REVIEW_WITH, VERIFY_WITH, and COMPLEMENTS edges can
  justify a contextual complement.

The compiled relationship graph has ten directed edges, including the
reciprocal TDD alternative, four verification relationships, two supersession
relationships, one MCP/context complement, and one release-test review
relationship. This is deliberately sparse. Cycles are rejected only for
REQUIRES; naturally reciprocal positive relationships remain legal.

Optional skills also pass a marginal context/tool-cost gate. A candidate with
high instruction bytes or tool cost must add an uncovered required role,
required evidence/output, or positive relationship benefit. The gate does not
remove required coverage merely to minimize context.

## Registry-gap disposition

The search used the actual 214-record registry and the installed local catalog.
Exact donor names were not silently aliased:

| Capability | Registry finding | Phase 3A.2 disposition |
|---|---|---|
| source-driven development | no exact canonical ID; installed donor exists outside registry | EXTERNAL_REFERENCE_ONLY |
| Deep Understanding | installed workflow exists, but no exact 214-record ID | EXTERNAL_REFERENCE_ONLY |
| security hardening | no exact donor ID; safe-mode and permission-tuner are conservative proxies | PROXY_SUFFICIENT for current fixtures; not an alias |
| API/interface design | no exact donor ID; architecture/decision methods are partial proxies | PROXY_SUFFICIENT for current fixtures; not an alias |
| MCP audit | exact mcp-audit record exists | direct canonical record; no import proposal |
| context engineering | exact context-engineering record exists | direct canonical record; no import proposal |

No external body was copied or imported in this phase. Future import proposals
must pass license/provenance, duplicate analysis, evaluation, security review,
and approval. The compiled route records Deep Understanding as UNAVAILABLE
when the exact record is absent; it does not invent it from the installed
workflow.

## Phase 3A.2 dogfood route

using-superpowers remained the resident task/session authority. It is shown as
a GATE reference for substantive routes, but its full body was not reloaded
for every stage. The dogfood TaskSpec was:

~~~yaml
task_id: T-phase3a2-routing-quality
task_type: implementation
complexity: COMPLEX
risk: HIGH
ambiguity: MEDIUM
architecture_impact: ARCHITECTURE-CHANGING
required_capabilities: [needs_editing, needs_structured_output]
permission_level: workspace-write
model_profile: unselected
~~~

Deep Understanding was USED_WITH_FALLBACK as an escalation check because the
task is architecture-changing and high risk. It was UNAVAILABLE in the
supplied registry, so the routes continued conservatively. The active stages
below each emitted and schema-validated a separate StageRoute; the router
inspected 214 metadata records and loaded zero bodies for every route.

| Stage | Objective | Selected skills by role | Route result | Evidence / operational note |
|---|---|---|---|---|
| UNDERSTAND | establish the routing-quality boundary | GATE using-superpowers; DOMAIN understand-diff | SKILLS_SELECTED | graph artifact absent; direct repository inspection was required |
| RESEARCH | inspect provenance, gaps, and replay evidence | PROCESS wiki-builder, PROCESS wiki-research-loop; VERIFY verification-before-completion | SKILLS_SELECTED | no wiki/MCP fetch was run; source material stayed local and cited |
| DESIGN | design curation, saturation, and snapshot behavior | PROCESS grill-with-docs; DOMAIN improve-codebase-architecture; REVIEW code-review-excellence; VERIFY verification-before-completion | SKILLS_SELECTED | decision and schema evidence required |
| PLAN | sequence implementation and replay | PROCESS writing-plans | SKILLS_SELECTED | no unrelated skill quota added |
| IMPLEMENT | implement the smallest quality changes | PROCESS executing-plans, test-driven-development; REVIEW code-review-excellence; VERIFY verification-before-completion | SKILLS_SELECTED | tests and diff evidence required |
| REVIEW | review relevance and evidence lanes | REVIEW brooks-test, code-review-excellence; VERIFY verification-before-completion | SKILLS_SELECTED | two review lanes justified by review/security evidence |
| VERIFY | run tests and unchanged fixtures | REVIEW brooks-test; VERIFY verification-before-completion | SKILLS_SELECTED | full suite and measurement evidence required |
| HARDEN | inspect trust, cost, and no-body-read safety | REVIEW code-review-excellence; VERIFY verification-before-completion | SKILLS_SELECTED | no permission grant is derived from metadata |
| HANDOFF | package evidence and readiness decision | PROCESS handoff; REVIEW code-review-excellence; VERIFY verification-before-completion | SKILLS_SELECTED | model routing remains unimplemented |

For each row, `SKILLS_CONSIDERED` was the 214-record compiled metadata
snapshot; no procedure bodies were considered by the ranker. The common
`AGENT/RUNTIME` was the Codex route consumer, `MODEL PROFILE` was unselected,
`TOOLS` were local repository inspection, patching, and test execution, and
the `INPUT ARTIFACTS` were the TaskSpec, stage definition, and snapshot. Each
stage emitted a `StageRoute` as the `OUTPUT ARTIFACT`, with selected skill
references, role assignments, routing evidence, and the stage's evidence
requirements. The following ledger preserves the route IDs and the concise
rejection evidence without recording private reasoning:

| Stage | Route ID | Skills rejected / reason summary | Evidence required |
|---|---|---|---|
| UNDERSTAND | `route:T-phase3a2-routing-quality:understand:9568a004dc7271e6` | stage/task/domain mismatch; `understand-diff` graph precondition absent | repository boundary and assumptions |
| RESEARCH | `route:T-phase3a2-routing-quality:research:ea6bff17285f5b3f` | implementation, visual, security, and MCP candidates lacked research relevance | source/provenance and gap findings |
| DESIGN | `route:T-phase3a2-routing-quality:design:d07efdf6f5c49236` | unrelated implementation, release, and MCP candidates filtered or cost/saturation-rejected | decision, schema, and architecture evidence |
| PLAN | `route:T-phase3a2-routing-quality:plan:72e2609f6935f624` | unrelated domain/review/security candidates; no quota selection | plan artifact and acceptance criteria |
| IMPLEMENT | `route:T-phase3a2-routing-quality:implement:64731522a985ad9e` | visual, security, MCP, and unrelated domain candidates lacked stage fit or budget value | tests, diff, and verification evidence |
| REVIEW | `route:T-phase3a2-routing-quality:review:ae68cf987a2a861a` | non-review candidates and redundant same-role candidates saturated without extra evidence | independent review evidence |
| VERIFY | `route:T-phase3a2-routing-quality:verify:6494df047e9d6e40` | non-verification candidates rejected; no minimum quota | full tests and measurement evidence |
| HARDEN | `route:T-phase3a2-routing-quality:harden:91f211caacbe99d6` | non-security/MCP/visual candidates lacked hardening relevance; review saturation applied | trust, cost, and body-read safety |
| HANDOFF | `route:T-phase3a2-routing-quality:handoff:ae59a020f2e81166` | candidates without handoff/release/review relevance rejected; no quota | evidence package and readiness decision |

The resident gate, stage routes, selected body references, reasons, and
rejected-candidate summaries are observable route artifacts only. No hidden
chain-of-thought, scratchpad, or private reasoning was recorded. The
understand-diff procedure could not use its optional knowledge graph because
.understand-anything/knowledge-graph.json is absent; this is recorded as a
runtime/documentation gap rather than a successful graph-backed analysis.

## Module map and data flow

The pro-module-map and architecture review identified these actual seams:

~~~text
SKILL_INDEX + canonical bodies
        -> metadata_enrichment.py
             -> generated / curated / compiled overlay
        -> routing_catalog.py
             -> immutable RoutingCatalogSnapshot + SkillGraph
        -> stage_router.py
             -> skill_scoring.py + skill_graph.py
             -> StageRoute + routing evidence
        -> Codex adapter (existing downstream consumer)
~~~

The real boundaries are data validation, metadata compilation, graph reuse,
stage selection, and evidence. No Manager, registry service, database,
factory hierarchy, worker pool, or general orchestration engine was added.
pro-auto-setup found a pure Python repository without a package manifest;
available local tooling was inspected without writing user settings or
installing dependencies.

## Future learning and research boundary

Future Hermes-style learning may emit a MetadataProposal:

~~~text
experience -> MetadataProposal -> eval -> review -> promotion
~~~

The proposal cannot silently edit either curated truth or routing weights. The
same separation matters for future adaptive model routing. Primary research
shows that cost/quality routing needs preference or task-outcome evidence and,
for adaptive budgeted policies, bandit feedback—not a hand-tuned preference
such as “use model X for architecture.” See [RouteLLM](https://arxiv.org/abs/2406.18665),
[Adaptive LLM Routing under Budget Constraints](https://arxiv.org/abs/2508.21141),
and [FrugalGPT](https://arxiv.org/abs/2305.05176). Model routing remains a
later phase.
