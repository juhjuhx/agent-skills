# Agent Skills Matrix v3

> Status: **proposed architecture; Phase 1 contracts, the Phase 2.6 provenance-hardened Codex vertical slice, the Phase 3A.2 deterministic Stage Router quality pass, and the Phase 3B runtime/model evaluation contracts implemented**. The router is metadata-first and stage-local; the evaluation harness records candidates and evidence but does not activate adaptive model routing or implement the other native adapters.

## Why v3

Agent Skills Matrix v3 keeps one canonical skill library and gives each agent runtime a generated/native adapter. A user can experience Codex, Claude Code, OpenCode, Hermes, MiMo Code, ZCode, or DeepSeek Harness as a native integration without maintaining a separate copy of every skill.

```text
canonical SKILL.md + registry metadata
              |
              v
       capability-based core
              |
              +--> Codex adapter
              +--> Claude Code adapter
              +--> OpenCode adapter
              +--> Hermes adapter
              +--> MiMo Code adapter
              +--> ZCode adapter
              +--> DeepSeek Harness adapter
```

The core owns task contracts, stage-local routing, evidence gates, trust, and learning policy. Adapters own native packaging, lifecycle, tool, permission, context, and model-selection details. Skills are not forked by agent.

## Current evidence baseline

Counts below are derived from machine-readable files at the v3 proposal baseline (`origin/main` at `42c3d5c`):

| Source | Result | Meaning |
|---|---:|---|
| `.superpowers/SKILLS_INDEX.json` → `skill_count` | 214 | indexed canonical skills |
| `.superpowers/SKILLS_INDEX.json` → unique `categories[]` tags | 9 | registry taxonomy tags |
| `categories.json` → `.categories` length | 10 | installer/profile categories |
| README prose before this proposal | 238 / 11 | stale historical claim |

The registry is authoritative for indexed skills. Installer categories and registry taxonomy are different projections and must not be silently conflated. The often-repeated 423/14 figure is not present in the checked machine-readable baseline, so v3 does not claim it.

## Lifecycle

```text
Task Intake
  -> Risk / Complexity / Ambiguity
  -> TaskSpec
  -> Stage Planner
  -> Stage-local Skill Router
  -> Agent Adapter
  -> Model Profile
  -> Execution
  -> Evidence Gate
  -> Reroute / Next Stage
```

The normal stages are:

1. Understand
2. Research
3. Design
4. Plan
5. Implement
6. Review
7. Verify
8. Harden
9. Handoff / Learn

Each stage can independently select and reroute skills. A typical stage uses 3–7 relevant skills; a complex stage may use 5–10. A complex project may therefore produce 30–50+ activations across the workflow. These are guidance ranges, not quotas: unrelated skills must never be loaded merely to reach a number, and reuse across stages is expected.

## Contracts

- [Architecture and ADRs](ARCHITECTURE.md) — frozen v3 decisions and boundaries.
- [Using-Superpowers v3](USING_SUPERPOWERS.md) — orchestration authority and lifecycle.
- [Stage Router](STAGE_ROUTER.md) — role slots, capability negotiation, and rerouting.
- [Skill Metadata and Graph](SKILL_METADATA_AND_GRAPH.md) — future registry schema and relationships.
- [Agent Adapter Contract](AGENT_ADAPTER_CONTRACT.md) — runtime-neutral adapter surface.
- [Model Profile Contract](MODEL_PROFILE_CONTRACT.md) — provider/model separation.
- [Reasoning Artifacts](REASONING_ARTIFACTS.md) — observable handoff contract, not hidden chain-of-thought.
- [Learning and Evals](LEARNING_AND_EVALS.md) — proposal-based learning and evaluation suites.
- [Security and Provenance](SECURITY_AND_PROVENANCE.md) — trust states and supply-chain evidence.
- [Review Pipeline](REVIEW_PIPELINE.md) — independent OCR, agent, security, performance, test, and runtime evidence.
- [Plugin, MCP, and CLI Matrix](PLUGIN_MCP_CLI_MATRIX.md) — native capability mapping.
- [Migration Plan](MIGRATION_PLAN.md) — documentation-first implementation sequence.
- [Donor Research Notes](DONOR_RESEARCH_NOTES.md) — provenance and adopted patterns.
- [Phase 1 Machine-Readable Contracts](PHASE1_MACHINE_READABLE_CONTRACTS.md) — schemas, validation, fixtures, and compatibility projection.
- [Codex Official Capability Mapping](CODEX_OFFICIAL_CAPABILITY_MAPPING.md) — first-party surface evidence and support levels for the Phase 2 adapter.
- [Phase 2.6 Runtime Provenance Evidence](evidence/PHASE26_RUNTIME_PROVENANCE_ROUTE.md) — installed-release binding and source-snapshot distinction.
- [Runtime Capability Matrix](evidence/RUNTIME_CAPABILITY_MATRIX.md) — observed local runtimes, provenance, capability granularity, and availability.
- [Model/Runtime Evaluation V1](evidence/MODEL_RUNTIME_EVAL_V1.md) — development/holdout design, baselines, evidence classes, and current verdict.
- [Phase 3B dogfood route](evidence/PHASE3B_MODEL_RUNTIME_DOGFOOD_ROUTE.md) — the first task-level use of the evaluation contracts.

### Phase 2 implementation slice

The first executable boundary is intentionally small:

```text
validated TaskSpec + StageRoute + manifests
  -> selected-only SkillResolver
  -> CompiledExecutionBundle
  -> CodexNativeProjection
  -> evidence gate
```

The public schemas are [`CompiledExecutionBundle`](../../schemas/v3/compiled-execution-bundle.schema.json)
and [`CodexNativeProjection`](../../schemas/v3/codex-native-projection.schema.json).
The standard-library implementation lives in
[`tools/v3/execution_bundle.py`](../../tools/v3/execution_bundle.py),
[`tools/v3/skill_resolver.py`](../../tools/v3/skill_resolver.py), and
[`tools/v3/codex_adapter.py`](../../tools/v3/codex_adapter.py), with explicit
permission and evidence helpers. This is a route consumer, not a router:
selected skills are verified by source digest and trust before on-demand
loading, and a resident `using-superpowers` reference is not reloaded in full
for every stage.

Fixtures and boundary tests cover selected-only and no-skill routes,
permission non-escalation, provenance, digest invalidation, evidence failure,
and portable/runtime separation. Phase 2.5 additionally checked emitted config
values against a pinned narrow Codex contract; Phase 2.6 binds the executable
default to the observed installed release and retains the former source
snapshot only as explicit upstream-preview evidence. The adapter fails closed
on unrepresentable permissions and keeps raw skill bodies out of serializable
results. The projection records native support versus host-managed metadata;
it has no filesystem side effects and does not claim that native Codex
execution has already been wired.

### Native adapter guides

- [Codex](agents/CODEX.md)
- [Claude Code](agents/CLAUDE_CODE.md)
- [OpenCode](agents/OPENCODE.md)
- [Hermes](agents/HERMES.md)
- [MiMo Code](agents/MIMO_CODE.md)
- [ZCode](agents/ZCODE.md)
- [DeepSeek Harness](agents/DEEPSEEK_HARNESS.md)

### Phase 3A Stage Router and quality convergence

The first machine-executable routing boundary is implemented in
[`STAGE_ROUTER.md`](STAGE_ROUTER.md):

```text
TaskSpec + Stage + generated/curated metadata snapshot
  -> hard filters -> transparent score -> role complement
  -> StageRoute (SKILLS_SELECTED | NO_SKILL_NEEDED)
```

The implementation inspects the current 214-record registry as metadata and
loads zero `SKILL.md` bodies while ranking. Phase 3A.2 separates generated
inference from small curated field patches, compiles an immutable
`RoutingCatalogSnapshot`, adds semantic negative signals and role saturation,
and keeps optional context cost visible. It does not migrate or rewrite the
production registry. The router does not select a model, run a general
planner, or load unrelated skills. It emits route evidence for ten unchanged
workload fixtures and its output remains consumable by the existing Codex
adapter in an end-to-end test. See the [`V1 baseline`](evidence/STAGE_ROUTER_EVAL_V1.md),
[`V2 enriched replay`](evidence/STAGE_ROUTER_EVAL_V2.md), and
[`V3 quality replay`](evidence/STAGE_ROUTER_EVAL_V3.md).

### Phase 3A.1 Catalog Intelligence

The routing bottleneck was sparse legacy metadata, so Phase 3A.1 adds a
bounded, offline overlay at
[`registry/v3/skill-routing-metadata.json`](../../registry/v3/skill-routing-metadata.json).
The overlay is keyed by the 214 IDs in
`.superpowers/SKILLS_INDEX.json`; it is not a second skill library and does not
copy procedure bodies. The canonical `SKILL.md` remains the procedure source.

[`metadata_enrichment.py`](../../tools/v3/metadata_enrichment.py) reads bodies
as data only during maintenance-time enrichment, records each source digest,
and emits provenance for derived routing fields. Normal catalog loading reads
the overlay and registry metadata only. Selected skill bodies remain a
downstream, selected-only resolver concern.

The current overlay census is recorded in
[`CATALOG_ROUTING_METADATA_CENSUS.md`](evidence/CATALOG_ROUTING_METADATA_CENSUS.md)
and the exact unchanged ten-fixture quality replay is in
[`STAGE_ROUTER_EVAL_V3.md`](evidence/STAGE_ROUTER_EVAL_V3.md). The compiled
snapshot has 65 `ROUTING_READY`, 131 `PARTIAL`, 16 `AMBIGUOUS`, and 2
`DEPRECATED` records; these are measured quality classifications, not a claim
that all metadata is author-declared. The curation and registry-gap decisions
are recorded in [`ROUTING_METADATA_CURATION.md`](evidence/ROUTING_METADATA_CURATION.md).
Phase 3A.2 does not migrate the production registry, silently promote inferred
metadata, implement a model router, or add another runtime adapter.

### Phase 3B Runtime and Model Evaluation Harness

Phase 3B adds runtime-neutral records for runtime candidates, model
candidates, execution configurations, evaluation runs/results, and explicit
runtime handoffs. Runtime selection is task/session-level; model selection is
limited to task, stage, or subagent boundaries advertised by the runtime; per
inference-call routing remains design-only. `ModelProfile` and
`ModelCandidate` describe inference capability and measurement only: they
cannot grant filesystem, network, MCP, publish, delete, or sandbox authority.

The harness provides four deterministic evaluation baselines and a separate
Pareto comparison over quality, cost, latency, and recovery. It keeps the
existing A–J Stage Router fixtures as development/regression data and adds a
12-workload holdout set without expected runtime/model identities. Static
fixtures prove contract compatibility only; quality conclusions require
`REAL_EXECUTION`. No live task/model quality runs are claimed in this phase,
so the current verdict is `INSUFFICIENT_LIVE_EVIDENCE`.

### Phase 3I Static Distribution Compiler

Phase 3I productizes the stable routing plane without entering the execution
plane. [`tools/v3/productization.py`](../../tools/v3/productization.py) consumes
one validated `RoutingCatalogSnapshot`, existing adapter manifests, and a
fixture-driven runtime capability inventory to produce a no-write
`InstallationPlan`, runtime capability report, and deterministic derived output
tree. It supports plan/compile/validate/explain operations but never probes a
runtime, invokes a model, reads credentials, or writes global runtime
configuration.

The canonical source remains `skills/<skill>/SKILL.md`; generated runtime files
carry source/snapshot/content digests and are never a second skill library.
Codex, Claude Code, and OpenCode have meaningful static projections; Hermes is
reported honestly as `NOT_IMPLEMENTED` without a fake distribution. Runtime
status keeps install availability, adapter support, static contract, and live
execution independent, so `CODEX_LIVE_TRANSPORT_BLOCKED` is preserved rather
than turned into a false product-ready signal. See the
[`static productization evidence`](evidence/STATIC_PRODUCTIZATION_V1.md),
[`Phase 3I route`](evidence/PHASE3I_PRODUCTIZATION_ROUTE.md), and
[`machine-readable conformance record`](../../fixtures/v3/productization/static-conformance-v1.json).

### Phase 3J Safe Project Installer

Phase 3J adds the first mutation boundary on top of the static compiler in
[`tools/v3/installer.py`](../../tools/v3/installer.py). It normalizes the existing
`InstallationPlan` with an authoritative `action` field, makes artifact lifecycle
explicit (`INSTALL_PERSISTENT`, `PROJECT_PERSISTENT`, `EXECUTION_EPHEMERAL`), and
filters only persistent artifacts into an `InstallPackage`.

Only an explicitly supplied `PROJECT` root can be applied. The MVP writes to a
project-local `.agent-skills-matrix/<runtime>/` host-managed staging tree and does not
edit `.codex`, `.claude`, OpenCode, Hermes, provider, authentication or global config
files. User/global scope is preview-only. Apply performs complete preflight, stale
revalidation, atomic staging, ownership-marker commit, digest verification and bounded
rollback; `ApplyResult` is separate from the immutable no-write plan.

Codex, Claude Code and OpenCode retain honest static support with live blockers;
Hermes is status-only because no adapter exists. The installer cannot upgrade live or
effort-routing readiness. See the [`safe installer evidence`](evidence/SAFE_PROJECT_INSTALLER_V1.md),
[`Phase 3J route`](evidence/PHASE3J_INSTALLER_ROUTE.md),
[`InstallPackage schema`](../../schemas/v3/install-package.schema.json), and
[`ApplyResult schema`](../../schemas/v3/apply-result.schema.json).

## Non-goals for this proposal

This pass does not move or fork skills, rewrite `install.sh`, change `.superpowers/ROUTING_POLICY.yaml`, implement a general stage planner or model router, add a database or cloud service, install MCP servers, auto-import third-party skills, or implement non-Codex adapters. Those are follow-up phases and remain explicitly unimplemented.
