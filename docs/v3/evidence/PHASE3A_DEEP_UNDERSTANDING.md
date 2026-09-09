# Phase 3A Deep-Understanding Record

## Scope

This record covers the existing v3 contract, compatibility, and Codex execution
surfaces that the Stage Router MVP must consume. It is an observable design
artifact; it contains no private model reasoning.

## Repository and source truth

- Base branch: `fix/v3-runtime-contract-provenance`
- Implementation branch: `feat/v3-stage-router-mvp`
- Registry: `.superpowers/SKILLS_INDEX.json`
- Registry snapshot: 214 entries, source commit `db3b67d5b051c4223da9146b2b836a9ed45e9bac`
- `categories.json` remains an installer/profile projection, not routing metadata.
- The v2 routing policy remains unchanged and is evidence only for this phase.

## Existing data flow

1. `TaskSpec` is a versioned, validated record containing task type, complexity,
   risk, ambiguity, objectives, capabilities, permissions, budgets, and optional
   stage definitions.
2. `SkillMetadataV3` is the portable skill record. The schema already permits
   stage, role, task-mode, domain, capability, cost, trust, compatibility, and
   relationship fields, but most of those are optional.
3. `compatibility.import_skill_index_entry` projects one current registry entry
   into a valid minimal v3 metadata record. It copies identity, description,
   triggers, source reference/path, and digest; it explicitly marks missing
   provenance and routing fields unavailable instead of guessing them.
4. `StageRoute` is the stage boundary. It requires explicit status, selected
   skill records, role assignments, adapter/model references, granted
   capabilities, a permission level, route reasons, alternatives, and evidence
   requirements. `NO_SKILL_NEEDED` cannot contain selected skills.
5. `SkillResolver` consumes only the selected route entries. It validates
   metadata and trust, resolves paths below the repository root, verifies the
   canonical digest, and loads only selected `SKILL.md` files. The resident
   `using-superpowers` authority is represented without loading its body again.
6. `CodexAdapter` validates the TaskSpec, StageRoute, adapter manifest, model
   profile, permissions, capabilities, reasoning artifacts, selected-only
   resolution, and evidence. It then builds a portable
   `CompiledExecutionBundle` and projects it onto verified Codex surfaces.
   The adapter consumes a route; it does not select skills or call a router.
7. `AdapterResult.to_dict()` and projection/evidence records intentionally carry
   references, digests, roles, load state, and byte metrics, not raw skill bodies.

## Boundary that Phase 3A adds

The missing executable boundary is a pure stage-local route decision:

`TaskSpec + Stage + imported SkillMetadataV3 records + optional capabilities,
trust policy, and budgets -> validated StageRoute`.

The router must operate on metadata only. Body loading remains downstream in
`SkillResolver` and only after selection. The router must not choose a model or
runtime-specific configuration.

## Contract observations

- The current schema accepts richer metadata without requiring a registry
  migration. This allows a compatibility adapter to expose honest missing-field
  diagnostics while the MVP uses only available metadata and deterministic
  derived signals.
- `StageRoute.route_reasons` and `alternatives` are already portable but do not
  carry structured score components or filter metrics. The MVP therefore needs a
  small optional machine-readable routing evidence object on StageRoute so route
  explanations and evaluation measurements are not hidden in prose.
- `TaskSpec.task_type` has a deliberately small enum. Evaluation fixtures must
  use those current values; stage objectives/domains can carry more specific
  wording without changing the contract.
- Capability names are open for future extension, but an unknown capability may
  not be treated as executable or granted. The router will fail closed for an
  unknown required capability when an adapter envelope is supplied.
- Trust is a loading boundary. `QUARANTINE`, `COMMUNITY`, `LOCAL_GENERATED`, and
  `BLOCKED` records are not automatically executable by the current Codex
  resolver; the router must not let quarantine win ranking.
- Relationship cycles are not globally invalid. Dependency-like relationships
  such as `REQUIRES` constrain route expansion; positive relationships may be
  cyclic.
- `using-superpowers` is session/task authority and can appear as a GATE
  reference for traceability, but must not be treated as a normal candidate that
  reloads at every stage.

## Risks to control

- Sparse legacy metadata can create false confidence. Evaluation output must
  report fields that were unavailable and distinguish derived hints from source
  metadata.
- Keyword signals can over-select broad skills. Selection must use hard filters,
  role balancing, cost/budget checks, and a no-skill threshold before ranking.
- Relationships can introduce hidden selections or conflicts. Dependency
  expansion and conflict checks must be deterministic and explained.
- Historical dogfood routes are comparison evidence, not production weights or
  ground truth.
- Raw `SKILL.md` content must not enter route records or ranking telemetry.

## Implementation shape

Keep the MVP to data and pure functions: a stage router, transparent scoring
helpers, and a small relationship index if needed. Do not add a registry service,
database, scheduler, model router, or other orchestration framework. The output
must be consumable by the existing Codex adapter in an end-to-end test.

## Verification targets

- deterministic route for identical inputs;
- hard rejection of trust, capability, budget, conflict, superseded, and
  unsupported candidates;
- required dependencies and role coverage without a fixed skill quota;
- conditional security, MCP, verification, and Deep Understanding activation;
- explicit `NO_SKILL_NEEDED` for tiny corrections;
- metadata-only ranking with selected-only body loading;
- valid StageRoute output and Codex bundle/projection consumption;
- measured candidate/metadata/body counts and route latency.
