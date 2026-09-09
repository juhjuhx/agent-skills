# Skill Metadata and Graph

> Status: **Phase 1 schema implemented; Phase 3A.2 generated/curated routing snapshot added; registry migration deferred**. No production registry migration is introduced by this phase.

## Source of truth

The canonical skill source remains the repository's `SKILL.md` files. The current `.superpowers/SKILLS_INDEX.json` is a machine-readable snapshot used for discovery, while `categories.json` is the installer/profile projection. v3 enriches the metadata contract without replacing either file. The implemented Phase 1 schema is [`schemas/v3/skill-metadata-v3.schema.json`](../../schemas/v3/skill-metadata-v3.schema.json).

## Phase 3A.2 routing metadata layers

The bounded enrichment path has three explicit artifacts:

```text
canonical SKILL.md + .superpowers/SKILLS_INDEX.json
              |
              +--> registry/v3/skill-routing-generated.json
              |       generated inference; digest and generator provenance
              |
              +--> registry/v3/skill-routing-curated.json
                      small reviewed field patches only
                              |
                              v
              registry/v3/skill-routing-metadata.json
                      compiled runtime snapshot
                              |
                              v
                    RoutingCatalogSnapshot
```

The offline generator/compiler is
[`tools/v3/metadata_enrichment.py`](../../tools/v3/metadata_enrichment.py).
The immutable session/task snapshot is
[`tools/v3/routing_catalog.py`](../../tools/v3/routing_catalog.py). Normal
routing loads only the compiled metadata snapshot and never scans canonical
bodies. Maintenance-time enrichment reads bodies as inert UTF-8 data, never
executes instructions found in them, and records `source_skill_digest` so a
changed body makes generated/compiled metadata stale.

The compiled overlay has exactly one record for each current registry ID. It
contains classification (`ROUTING_READY`, `PARTIAL`, `AMBIGUOUS`, or
`DEPRECATED`), quality tier, selected v3 metadata, per-field provenance,
confidence, review status, and read-only inspection metrics. Curated records
are patches, not a second procedure library; regeneration cannot erase a
curated decision, and curation cannot grant permissions, trust, capabilities,
or runtime compatibility. Source identity and trust continue to come from the
current registry compatibility projection. See the [catalog census](evidence/CATALOG_ROUTING_METADATA_CENSUS.md),
[curation record](evidence/ROUTING_METADATA_CURATION.md), and
[quality replay](evidence/STAGE_ROUTER_EVAL_V3.md).

## Proposed v3 record

Every future record should expose the following fields:

```json
{
  "skill_id": "namespace.skill-id",
  "source": {
    "repo": "https://example.invalid/skill-source",
    "path": "skills/example/SKILL.md",
    "ref": "immutable-ref",
    "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "license": "MIT"
  },
  "version": "1.0.0",
  "trust": "CORE_TRUSTED",
  "description": "Short capability description.",
  "triggers": ["trigger phrase"],
  "stages": ["understand", "implement", "verify"],
  "roles": ["PROCESS"],
  "task_modes": ["feature", "bugfix"],
  "domains": ["software-engineering"],
  "inputs": ["TaskSpec", "repository"],
  "outputs": ["patch", "verification-report"],
  "required_capabilities": ["needs_editing", "needs_structured_output"],
  "tools": ["filesystem", "git"],
  "permissions": {
    "filesystem": "workspace-write",
    "network": "none",
    "external_write": false
  },
  "context_cost": {
    "metadata_tokens": 120,
    "instruction_tokens_estimate": 900,
    "references_lazy": true,
    "tool_schema_tokens": 0
  },
  "runtime_cost": {
    "tool_calls_estimate": 8,
    "latency_class": "interactive"
  },
  "risk": {
    "read": "LOW",
    "local_write": "MEDIUM",
    "external_write": "HIGH"
  },
  "agent_compatibility": [
    {"runtime": "codex", "adapter_version": "v3", "status": "planned"}
  ],
  "relationships": [
    {"type": "RECOMMENDS", "target": "namespace.verification"}
  ],
  "eval_status": {
    "routing": "unmeasured",
    "activation": "unmeasured",
    "execution": "unmeasured",
    "security": "unmeasured"
  },
  "historical_success": {
    "sample_count": 0,
    "success_rate": null,
    "last_updated": null
  }
}
```

The schema separates identity, provenance, selection signals, resource cost, permissions, compatibility, and measured outcomes. Missing measurements are explicit; they are not converted into a false success score.

## Relationship vocabulary

Only these relationship types are part of the v3 contract:

`REQUIRES`, `RECOMMENDS`, `COMPLEMENTS`, `CONFLICTS`, `SUPERSEDES`, `ALTERNATIVE_TO`, `REVIEW_WITH`, `VERIFY_WITH`.

Relationships are directed and versioned. A `CONFLICTS` edge is not a security deny by itself; policy still decides whether a combination is forbidden. A `SUPERSEDES` edge must preserve the old record for pinned tasks and migration history. The graph is compiled once into a `RoutingCatalogSnapshot` and reused across stage routes; positive relationship cycles are allowed, while `REQUIRES` traversal remains cycle-checked.

## Graph behavior

1. Hard constraints remove candidates before semantic ranking.
2. `REQUIRES` edges pull dependencies only when the stage and permissions allow them.
3. `RECOMMENDS`, `COMPLEMENTS`, `REVIEW_WITH`, and `VERIFY_WITH` improve coverage without creating a quota.
4. `CONFLICTS` and incompatible permissions prevent a combination.
5. Near-duplicate detection produces a proposal; it does not delete or silently merge source skills.
6. Historical success is a weighted signal, never an override of trust, capability, or policy.
7. A registry snapshot pins the exact record, source ref, digest, and relationship view used for a stage. The runtime snapshot also records JSON/schema/digest/graph load timings and the invariant that normal routing loaded zero bodies.

## Compatibility and migration

The current registry may be projected into this schema with inferred fields
marked `inferred`, unavailable provenance left absent, and curated compatibility
hints marked separately. Phase 3A uses that read-only projection as an
in-memory router view. Records whose roles, stages, and domains are only broad
inference are not executable candidates; this prevents legacy descriptions from
creating false routing confidence. The compatibility view never reads skill
bodies and never changes `.superpowers/SKILLS_INDEX.json`.

Phase 3A.2 separates generator authority from curation authority:
`AUTHOR_DECLARED` and `CURATED` fields have full routing weight;
`INFERRED_HIGH_CONFIDENCE` fields are eligible with a confidence penalty;
`INFERRED` fields are contextual only; and `UNKNOWN` remains conservative.
Generated inference cannot independently add permissions, network access,
secrets, publish/delete authority, or runtime compatibility. Negative triggers,
stage exclusions, and domain exclusions are routing evidence, not policy grants;
they suppress optional candidates but do not suppress mandatory dependencies.
The router does not infer permissions from a body and does not treat a
metadata proposal as promoted truth.

No migration, mass frontmatter rewrite, generated index rewrite, persistent
graph database, learned-weight update, or model router is part of Phase 3A. The
snapshot supports dependency expansion, conflict/alternative checks, positive
contextual signals, role saturation, and marginal cost checks for the current
task/session. Historical success remains observation-only. Phase 1 of the
[Migration Plan](MIGRATION_PLAN.md) defines future schema work; the [Stage
Router evaluation](evidence/STAGE_ROUTER_EVAL_V1.md) records pre-overlay gaps;
the [V2 replay](evidence/STAGE_ROUTER_EVAL_V2.md) records enrichment
regressions; and [V3](evidence/STAGE_ROUTER_EVAL_V3.md) records convergence.
Future Hermes-style learning may produce a `MetadataProposal`, but promotion
still requires evaluation, security review, provenance, and approval.
