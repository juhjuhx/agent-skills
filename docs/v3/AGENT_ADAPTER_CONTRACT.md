# Agent Adapter Contract

> Status: **runtime-neutral contract; Phase 1 manifests and the Phase 2.5 Codex vertical slice are implemented**. Other native adapters remain guides only.

## Purpose

An adapter makes one canonical skill source feel native in a specific agent runtime. It translates a portable `TaskSpec`, selected skill references, capabilities, permissions, model profile, and evidence requirements into native configuration and lifecycle calls.

Phase 1 represents the serializable portion as [`AgentAdapterManifest`](../../schemas/v3/agent-adapter-manifest.schema.json). The manifest advertises capabilities and native surfaces; it does not grant permissions, execute tools, or encode runtime-specific branches in the universal contract.

An adapter must describe, or explicitly mark unavailable:

- persistent instructions;
- native skill locations and lazy loading;
- commands;
- subagents;
- plugins;
- hooks;
- MCP/tool registration;
- permissions and sandbox;
- model selection and reasoning effort;
- parallelism;
- context strategy and token cost;
- native learning;
- structured output;
- generated configuration and provenance.

## Phase 2 two-layer boundary

The first adapter implementation keeps the portable record separate from the
Codex projection:

```text
TaskSpec + validated StageRoute + selected metadata
  -> CompiledExecutionBundle (portable)
  -> CodexNativeProjection (Codex-specific)
```

`CodexAdapter` consumes a route; it never invokes the general router. For a
`SKILLS_SELECTED` route it resolves only selected metadata, checks trust and
source digest, loads selected `SKILL.md` bodies on demand, and emits a bundle
and projection. For `NO_SKILL_NEEDED` it loads zero additional skills and
preserves `no_skill_reason`. The `using-superpowers` gate is a task/session
authority and may remain resident rather than reloading its full instructions
at every stage.

The portable bundle contains no Codex branch logic. The Codex projection emits
only researched native surfaces and labels static context, dynamic context,
tool-schema accounting, evidence gates, and native learning as host-managed or
unsupported where Codex has no equivalent. See the [Codex official capability
mapping](CODEX_OFFICIAL_CAPABILITY_MAPPING.md).

Permissions are calculated as a least-privilege intersection of TaskSpec,
policy, adapter declaration, route budget, and live runtime/sandbox state.
Model profiles, skill metadata, MCP declarations, and generated projections
cannot grant an operating-system permission.

The Codex slice applies an additional native-conformance gate before
projection: emitted config values must match the checked-in narrow contract
for the pinned Codex source revision. Unsupported native values and portable
permission levels fail closed; the adapter never substitutes a broader
sandbox mode. Full loaded `SKILL.md` bodies are ephemeral execution inputs,
not part of serialized adapter results or evidence by default. Serializable
skill records retain only references, provenance, role, load state, and byte
metrics.

## Proposed interface

```typescript
interface AgentAdapterContract {
  id: string;
  version: string;
  runtimeIdentity: string;
  capabilities(): AdapterCapabilities;
  inspect(): AdapterInventory;
  render(task: TaskSpec, stage: StageRoute): GeneratedConfiguration;
  loadSkills(selection: SkillSelection): LoadedSkillRefs;
  execute(envelope: TaskEnvelope): AsyncIterable<ArtifactEvent>;
  collectEvidence(envelope: VerificationEnvelope): Promise<EvidenceSet>;
  learn(input: LearningProposalInput): Promise<LearningProposal>;
}
```

The method names are illustrative. A native implementation may use a CLI, API, plugin hook, or process boundary, but must return equivalent artifacts.

## Configuration contract

```yaml
adapter:
  id: <runtime-id>
  version: <adapter-version>
  source_of_truth: canonical-skill-registry
  generated_config:
    digest: <digest>
    generated_at: <timestamp>
    inputs: [TaskSpec, StageRoute, ModelProfile, PermissionGrant]
  persistent_instructions:
    location: <native-location>
    purpose: [invariants, routing-bootstrap, context-policy]
  skill_loading:
    native_location: <native-skill-location>
    mode: lazy
    selected_refs_only: true
  commands: {supported: true, mapping: []}
  subagents: {supported: false, mapping: []}
  plugins: {supported: false, mapping: []}
  hooks: {supported: false, mapping: []}
  mcp: {supported: false, mapping: [], schema_cost: tracked}
  permissions: {sandbox: declared, external_write: policy-gated}
  model_selection: {profile_based: true, universal_model_ids: false}
  reasoning_effort: {native: true, artifact_contract: explicit}
  parallelism: {max: 0, write_set: required}
  context_strategy: {static_prefix: stable, dynamic_stage_context: lazy}
  learning: {native_support: unknown, promotion: core-policy-gated}
  structured_output: {supported: true, schema_refs: []}
```

## Invariants

1. The adapter cannot fork the canonical skill content.
2. Generated configuration is reproducible from declared inputs and records a digest.
3. Native instructions remain small enough to preserve lazy loading.
4. Permissions are narrowed at the adapter boundary; model choice cannot widen them.
5. Tool and MCP schemas count against the stage context budget.
6. Subagent or parallel execution requires an explicit disjoint write set or a read-only grant.
7. Native learning may propose artifacts, but promotion remains governed by the canonical learning policy.
8. Every execution produces portable status, artifact, evidence, and failure records.

## Capability negotiation

The adapter advertises facts, not aspirations. For example, `structured_output: false` must remain false even if a model profile claims to support JSON. The router intersects TaskSpec requirements, adapter capability, model profile capability, and policy grants. Any empty intersection becomes a blocked or degraded route with a reason.

See [Model Profile Contract](MODEL_PROFILE_CONTRACT.md) for the separate provider layer and the native guides under [`agents/`](agents/).
