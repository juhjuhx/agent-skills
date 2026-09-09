# v3 Stage Router

> Status: **Phase 3A.2 quality convergence implemented**. This document
> describes the small, deterministic, metadata-first selector in `tools/v3/`.
> It does not implement a general stage planner, model router, persistence
> layer, or additional native adapters.

## Boundary

The MVP turns one task, one stage, and one metadata catalog into one validated
`StageRoute`:

```text
TaskSpec + Stage + generated/curated metadata
    -> compiled routing snapshot
    -> hard filters
    -> transparent scoring
    -> role-balanced selection
    -> StageRoute
```

The router consumes a stage. It does not decide the whole task plan, choose a
model, invoke tools, load `SKILL.md` bodies, or silently call another router.
The existing Codex adapter remains the first route consumer:

```text
StageRoute -> SkillResolver -> CompiledExecutionBundle -> CodexNativeProjection
```

Implementation boundaries are intentionally small:

- [`stage_router.py`](../../tools/v3/stage_router.py) owns one-stage filtering,
  selection, and route evidence.
- [`skill_scoring.py`](../../tools/v3/skill_scoring.py) owns deterministic
  text/metadata scoring, negative routing signals, and escalation signals.
- [`skill_graph.py`](../../tools/v3/skill_graph.py) owns in-memory relationship
  lookups and dependency expansion for a snapshot.
- [`routing_catalog.py`](../../tools/v3/routing_catalog.py) validates and
  compiles one immutable metadata/relationship snapshot for reuse across
  stages.
- [`CodexAdapter`](../../tools/v3/codex_adapter.py) consumes a validated route;
  it does not choose skills.

## Route contract

Every active stage produces exactly one explicit result:

- `SKILLS_SELECTED` with selected skill references and role assignments; or
- `NO_SKILL_NEEDED` with a non-empty `no_skill_reason` and no selected skills.

The optional `routing_evidence` object records candidate, filter, selection,
role, cost, trust, relationship, and Deep Understanding metrics. It contains
metadata references and concise reason codes, never hidden chain-of-thought or
raw skill bodies.

`using-superpowers` is different from an ordinary candidate. It is the
task/session-level orchestration authority and is represented as a resident
`GATE` reference when a substantive route exists. Its full instruction file is
not reloaded at every stage.

## Inputs

The stage object may provide:

```yaml
id: understand | research | design | plan | implement | review | verify | harden | handoff | learn
objective: observable stage outcome
task_type: implementation | bugfix | research | design | review | documentation | handoff | other
domains: [software-engineering]
required_outputs: [patch]
evidence_required: [tests]
required_roles: [PROCESS, VERIFY]
required_capabilities: [needs_editing]
required_tools: [browser]
```

`TaskSpec` supplies task classification, domains, capabilities, permissions,
budgets, artifact requirements, and acceptance context. The catalog is a
`SkillMetadataV3` list or a read-only compatibility projection of the current
`.superpowers/SKILLS_INDEX.json`. The offline maintenance path keeps generated
inference and curated field patches separate:

```text
canonical SKILL.md + current registry
        -> skill-routing-generated.json
        + skill-routing-curated.json
        -> skill-routing-metadata.json
        -> RoutingCatalogSnapshot
```

The router's default loader consumes only the compiled
[`registry/v3/skill-routing-metadata.json`](../../registry/v3/skill-routing-metadata.json)
snapshot. It does not read canonical bodies during normal ranking. The
generation and compilation boundary is implemented in
[`metadata_enrichment.py`](../../tools/v3/metadata_enrichment.py), and the
session-resident snapshot in [`routing_catalog.py`](../../tools/v3/routing_catalog.py).

### Routing metadata provenance

The overlay is generated offline by
[`tools/v3/metadata_enrichment.py`](../../tools/v3/metadata_enrichment.py).
It reads canonical bodies only as maintenance-time input and stores no raw
body text. Every derived field carries one of these provenance levels:

| Provenance | Router treatment |
|---|---|
| `AUTHOR_DECLARED` / `CURATED` | full routing weight and eligible for field enforcement |
| `INFERRED_HIGH_CONFIDENCE` | eligible with a modest confidence penalty |
| `INFERRED` | contextual score only; never a permission grant or hard semantic assertion |
| `UNKNOWN` | conservative absence; cannot satisfy a hard semantic requirement |

Each layer records the canonical body digest, generator/compiler version,
review status, confidence, and read-only body policy. A stale body digest is a
maintenance validation failure. Curated records are small field patches and
cannot replace the generated source record or grant permissions, capabilities,
trust, or runtime compatibility. `trust` and canonical source identity remain
inherited from the current registry compatibility projection. Unknown
permissions remain unknown/conservative. `QUARANTINE` and `BLOCKED` records
cannot become executable through a metadata score.

## Hard filters before ranking

Candidates are rejected before scoring when the supplied metadata establishes:

1. disallowed trust or deprecated status;
2. Deep Understanding is requested while its escalation gate is off;
3. incompatible stage, task mode, or domain;
4. unavailable required capability or tool;
5. a skill permission declaration beyond the TaskSpec permission envelope;
6. runtime incompatibility;
7. impossible context/tool budget;
8. no executable role slot;
9. a superseded record, missing `REQUIRES` dependency, or invalid dependency
   cycle;
10. a reviewed stage/domain exclusion or negative trigger when the candidate
    is only an optional complement.

Unknown required capabilities fail closed. A quarantined or blocked record
cannot become executable through scoring. The router never treats a candidate
as safe merely because its description contains a matching keyword.

The current 214-record registry predates v3 routing fields. The compatibility
view therefore distinguishes explicit fields, the generated inference layer,
and curated field patches. With the Phase 3A.2 compiled snapshot, curated and
high-confidence inferred routing fields are available to the MVP while their
provenance remains visible in route evidence. A legacy record whose roles,
stages, and domains are only broad inference is filtered with
`legacy metadata lacks curated routing fields`, rather than being allowed to
win on an over-broad keyword match. This is an MVP compatibility boundary, not
a registry migration.

## Role-slot selection

The selector covers required role slots first:

`GATE`, `PROCESS`, `DOMAIN`, `TOOL`, `REVIEW`, `VERIFY`.

It then adds an optional candidate only when it is a strong fit and either:

- covers an explicitly required role not yet covered;
- supplies a required artifact/evidence output; or
- has a declared positive graph relationship to an already selected skill.

There is no fixed primary/optional quota and no minimum skill quota. A tiny
correction may produce no skill; a complex stage may use several roles. Role
saturation is a marginal-value control, not a global maximum: the first strong
`REVIEW` candidate has normal value, a second is allowed only when the stage
requests independent/adversarial review evidence, and an explicit
`independent_review_count` may justify a third. `PROCESS` can similarly have a
second candidate when the stage requires distinct plan/spec/test evidence.
`ALTERNATIVE_TO` and `SUPERSEDES` reduce duplicate selection, while
`REVIEW_WITH`/`VERIFY_WITH` and `COMPLEMENTS` add contextual value. Role
diversity is preferred to the top N semantic scores.

Optional additions also pass a marginal context/tool-cost gate. Required role
coverage is not removed for cost alone, but an optional high-cost candidate
must add relevance, evidence, or a relationship signal that justifies its
incremental context.

## Transparent baseline score

For each eligible role assignment, the score records these components:

```text
task_relevance
stage_relevance
domain_match
role_need
trigger_match
required_output_match
relationship_bonus
capability_fit
trust
context_cost_penalty
historical_evidence = 0
```

The score is deterministic and tie-broken by role order and skill ID. Historical
success is observation-only in this phase; it cannot alter production weights
or policy. Score components and selected/rejected reason codes are persisted in
`routing_evidence` for review.

## Graph behavior

The in-memory graph supports the v3 relationship vocabulary:

- `REQUIRES`: add an eligible transitive dependency;
- `CONFLICTS`: never co-select;
- `SUPERSEDES`: prefer the available successor;
- `ALTERNATIVE_TO`: normally choose one;
- `RECOMMENDS`, `COMPLEMENTS`, `REVIEW_WITH`, `VERIFY_WITH`: positive contextual
  signals without a quota.

`RoutingCatalogSnapshot` builds the graph once after validation and reuses it
across stage routes. It has no database, background state, or mutable manager.
Positive relationship cycles are allowed; only dependency traversal detects a
`REQUIRES` cycle.

## Deep Understanding gate

Deep Understanding is an escalation policy, not a normal high-score candidate:

| Signals | Gate |
|---|---|
| simple/low-risk/low-ambiguity | `OFF` |
| standard with ordinary uncertainty | usually `OFF` |
| complex, high ambiguity, high/critical risk, architecture-changing, unfamiliar, or contradictory evidence | `ELIGIBLE` |

If the supplied catalog has no `deep-understanding` record, the route records
`UNAVAILABLE` and continues with the conservative metadata route. The installed
local workflow and the repository's 214-record registry are separate evidence
sources; an installed workflow is not silently invented into the registry.

## No-skill behavior

The router can return `NO_SKILL_NEEDED` for a simple, low-risk, low-ambiguity
correction when the stage has no required role or evidence obligation. This is
an intentional result, not a failed route. It prevents unrelated architecture,
security, performance, MCP, or Deep Understanding skills from being loaded just
to satisfy an example count.

## Lazy loading and Codex consumption

Ranking inspects metadata only. It reports `body_files_loaded: 0` and does not
read any `SKILL.md`. After selection, the downstream resolver loads only the
selected canonical files, verifies their source digest/trust, and preserves
provenance. `NO_SKILL_NEEDED` loads zero additional skills. This keeps one
canonical skill source and leaves native projection to the adapter.

Phase 3A.2 measures the distinction explicitly: offline enrichment inspected
all 214 bodies to create generated inference, while normal Stage Router
invocations inspect 214 metadata records and load zero bodies. The immutable
snapshot amortizes JSON/schema/digest validation and graph construction across
stages. The selected body byte estimate is route evidence for downstream
execution; it is not a claim that the router loaded those bodies.

## Current limits and evidence

The MVP does not yet provide a general stage planner, model/provider routing,
reroute executor, historical-weight learning, or Claude/OpenCode/Hermes/MiMo/
ZCode/DeepSeek adapters. The v2 policy and production registry remain
unchanged. The ten-workload baseline, enriched replay, and quality-convergence
replay are recorded in [`STAGE_ROUTER_EVAL_V1.md`](evidence/STAGE_ROUTER_EVAL_V1.md),
[`STAGE_ROUTER_EVAL_V2.md`](evidence/STAGE_ROUTER_EVAL_V2.md), and
[`STAGE_ROUTER_EVAL_V3.md`](evidence/STAGE_ROUTER_EVAL_V3.md). The curation
policy, registry gaps, and this phase's dogfood routes are in
[`ROUTING_METADATA_CURATION.md`](evidence/ROUTING_METADATA_CURATION.md) and
[`CATALOG_ROUTING_METADATA_CENSUS.md`](evidence/CATALOG_ROUTING_METADATA_CENSUS.md).
