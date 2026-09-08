# Next Codex Prompt — Phase 2 Codex Native Adapter Vertical Slice

Copy the prompt below into the next Codex session. It is intentionally self-contained and must be executed only after Phase 1 is available on the branch being used.

---

## Project

Repository: `juhjuhx/agent-skills`

This is **AGENT SKILLS MATRIX v3 — PHASE 2: CODEX NATIVE ADAPTER VERTICAL SLICE**.

Phase 1 added machine-readable contracts, validation, fixtures, and a read-only compatibility projection. Do not redesign v3 and do not begin the Claude/OpenCode/Hermes/MiMo/ZCode/DeepSeek adapters.

## Required reading

Read the repository `AGENTS.md`, then:

- `docs/v3/README.md`
- `docs/v3/ARCHITECTURE.md`
- `docs/v3/USING_SUPERPOWERS.md`
- `docs/v3/STAGE_ROUTER.md`
- `docs/v3/AGENT_ADAPTER_CONTRACT.md`
- `docs/v3/MODEL_PROFILE_CONTRACT.md`
- `docs/v3/REASONING_ARTIFACTS.md`
- `docs/v3/PHASE1_MACHINE_READABLE_CONTRACTS.md`
- `docs/v3/evidence/PHASE1_DOGFOOD_ROUTE.md`
- `schemas/v3/task-spec.schema.json`
- `schemas/v3/skill-metadata-v3.schema.json`
- `schemas/v3/agent-adapter-manifest.schema.json`
- `schemas/v3/model-profile.schema.json`
- `schemas/v3/stage-route.schema.json`
- `tools/v3/contract_validation.py`
- `tools/v3/compatibility.py`

Inspect actual source truth before choosing skill IDs:

- `.superpowers/SKILLS_INDEX.json` (`skill_count: 214`, source commit `db3b67d5b051c4223da9146b2b836a9ed45e9bac` at the Phase 1 baseline)
- `categories.json` (installer projection, not v3 domains)
- `.superpowers/ROUTING_POLICY.yaml` (current v2 policy; do not rewrite it)
- `fixtures/v3/agents/codex.json`
- `fixtures/v3/models/openai-compatible.json`
- `fixtures/v3/routes/skills-selected.json`

## Scope

Implement one small Codex adapter vertical slice using the Phase 1 contracts:

```text
canonical SkillMetadataV3
  -> Codex native adapter manifest
  -> generated native configuration
  -> canonical skill discovery
  -> lazy selected-SKILL.md loading
  -> StageRoute consumption
  -> explicit reasoning artifacts
  -> evidence gate
```

The adapter must make the canonical skill source feel native to Codex while keeping one source of truth. It must not fork skill content, copy hundreds of workflows into `AGENTS.md`, or add universal model/provider branch logic.

## Constraints

- Use `using-superpowers` as task/session orchestration authority.
- Decompose the work into active v3 stages and emit a route record for every active stage.
- Re-run stage-local routing at each active stage; use actual registry/installed skill names only.
- Keep `AGENTS.md` limited to invariants, routing bootstrap, and context-loading policy.
- Use Codex-native concepts: `AGENTS.md`, Skills, Plugins, Subagents, MCP, config/permission profiles, and reasoning effort.
- Model runtime and provider/model profile remain separate. Do not write `if model == codex` and do not encode today's model IDs in universal policy.
- The adapter advertises capabilities; it does not grant permissions. Effective permissions are the intersection of TaskSpec, policy, adapter, and model profile.
- MCP/tool schema cost, static prompt prefix, dynamic context, tool ordering, and cache stability must be represented in the generated configuration or evidence.
- `using-superpowers` may be referenced as the route `GATE`; do not reload its full instruction file as an ordinary skill at every stage.
- Do not modify `install.sh`, move skills, migrate `.superpowers/SKILLS_INDEX.json`, rewrite `.superpowers/ROUTING_POLICY.yaml`, add a database, or install MCP servers.
- Do not implement a general Stage Router. Consume an existing validated `StageRoute` only.

## Required implementation

1. Add a Codex adapter module that consumes a validated `TaskSpec`, `StageRoute`, `SkillMetadataV3` records, the Codex `AgentAdapterManifest`, and a compatible `ModelProfile`.
2. Implement canonical metadata lookup and selected-only lazy loading of the referenced `SKILL.md` files.
3. Generate a deterministic Codex-native configuration artifact with:
   - small `AGENTS.md` bootstrap reference;
   - native skill location and selected refs;
   - model profile reference and reasoning effort;
   - permission/sandbox envelope;
   - optional plugins, subagents, MCP, and parallelism declarations;
   - static prefix/dynamic context/tool-schema budget/order/cache fields;
   - source refs, digests, and generated-config digest.
4. Consume `StageRoute.status` correctly:
   - `SKILLS_SELECTED` loads only selected refs and their required resources;
   - `NO_SKILL_NEEDED` loads no additional skill and preserves `no_skill_reason`.
5. Emit portable reasoning artifacts: TaskSpec reference, assumptions, unknowns, decision record, stage plan, evidence, risk, verification, and optional learning proposal. Never emit private hidden chain-of-thought.
6. Implement an evidence gate that blocks completion without required evidence and returns an observable reroute/degradation reason. It must not widen permissions.

## Required tests

Add tests for:

- Codex manifest validates against `AgentAdapterManifest`.
- A route generated from `fixtures/v3/routes/skills-selected.json` consumes the Codex fixture and OpenAI-compatible profile.
- A `NO_SKILL_NEEDED` route does not load a skill.
- Only selected canonical refs are loaded; unrelated `SKILL.md` content is not copied into configuration.
- Generated configuration is deterministic for identical inputs and includes provenance/digest.
- A changed registry digest invalidates or regenerates configuration rather than silently reusing it.
- Missing or quarantined skill metadata cannot be loaded as trusted core.
- Unsupported adapter/model capabilities produce an explicit blocked/degraded artifact.
- A permission declaration cannot escalate the TaskSpec or policy grant.
- Reasoning artifacts are portable and contain no hidden-chain-of-thought field.
- Evidence failure blocks completion and records a reroute trigger.
- No universal routing code branches on provider/model or runtime identity.

Run the full Phase 1 suite plus the new adapter tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Deliverables

- Codex adapter implementation and focused tests.
- Generated configuration fixture and provenance evidence.
- Canonical v3 doc synchronization only where the adapter makes the contract more precise.
- A concise Phase 2 routing/evidence trace under `docs/v3/evidence/`.
- No Claude/OpenCode/Hermes/MiMo/ZCode/DeepSeek implementation.

Stop after verification and open a separate stacked PR based on the Phase 1 branch. Do not merge.
