# Agent Skills Matrix v3

> Status: **proposed architecture; Phase 1 contracts and the Phase 2 Codex vertical slice implemented**. The slice compiles a portable execution bundle and a validated Codex projection; it does not implement the general stage router or install runtime configuration.

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
and portable/runtime separation. The projection records native support versus
host-managed metadata; it has no filesystem side effects and does not claim
that native Codex execution has already been wired.

### Native adapter guides

- [Codex](agents/CODEX.md)
- [Claude Code](agents/CLAUDE_CODE.md)
- [OpenCode](agents/OPENCODE.md)
- [Hermes](agents/HERMES.md)
- [MiMo Code](agents/MIMO_CODE.md)
- [ZCode](agents/ZCODE.md)
- [DeepSeek Harness](agents/DEEPSEEK_HARNESS.md)

## Non-goals for this proposal

This pass does not move or fork skills, rewrite `install.sh`, change `.superpowers/ROUTING_POLICY.yaml`, implement a runtime router, add a database or cloud service, install MCP servers, auto-import third-party skills, or add model names to universal policy. Those are follow-up phases and remain explicitly unimplemented.
