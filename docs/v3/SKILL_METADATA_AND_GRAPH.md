# Skill Metadata and Graph

> Status: **Phase 1 schema implemented; Phase 3A read-only routing consumer added; registry migration deferred**. No production registry migration is introduced by this phase.

## Source of truth

The canonical skill source remains the repository's `SKILL.md` files. The current `.superpowers/SKILLS_INDEX.json` is a machine-readable snapshot used for discovery, while `categories.json` is the installer/profile projection. v3 enriches the metadata contract without replacing either file. The implemented Phase 1 schema is [`schemas/v3/skill-metadata-v3.schema.json`](../../schemas/v3/skill-metadata-v3.schema.json).

## Phase 3A.1 routing overlay

The first bounded enrichment layer is the checked-in
[`registry/v3/skill-routing-metadata.json`](../../registry/v3/skill-routing-metadata.json)
overlay. It has exactly one record for each current registry ID and keeps the
canonical body in place. The offline generator is
[`tools/v3/metadata_enrichment.py`](../../tools/v3/metadata_enrichment.py).
Normal routing reads this overlay as metadata; it does not scan all bodies.
The generator reads bodies only during maintenance-time enrichment, never
executes instructions found in them, and records `source_skill_digest` so a
changed body makes the overlay stale.

The overlay is deliberately additive rather than a schema migration. Its
record contains classification (`ROUTING_READY`, `PARTIAL`, `AMBIGUOUS`, or
`DEPRECATED`), quality tier, selected v3 metadata, per-field provenance,
confidence, review status, and read-only inspection metrics. Source identity
and trust continue to come from the current registry compatibility projection;
agent compatibility, permissions, and unavailable provenance are not invented.
See the [catalog census](evidence/CATALOG_ROUTING_METADATA_CENSUS.md) for the
214-record field counts and the [enriched router replay](evidence/STAGE_ROUTER_EVAL_V2.md)
for behavior.

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

Relationships are directed and versioned. A `CONFLICTS` edge is not a security deny by itself; policy still decides whether a combination is forbidden. A `SUPERSEDES` edge must preserve the old record for pinned tasks and migration history.

## Graph behavior

1. Hard constraints remove candidates before semantic ranking.
2. `REQUIRES` edges pull dependencies only when the stage and permissions allow them.
3. `RECOMMENDS`, `COMPLEMENTS`, `REVIEW_WITH`, and `VERIFY_WITH` improve coverage without creating a quota.
4. `CONFLICTS` and incompatible permissions prevent a combination.
5. Near-duplicate detection produces a proposal; it does not delete or silently merge source skills.
6. Historical success is a weighted signal, never an override of trust, capability, or policy.
7. A registry snapshot pins the exact record, source ref, digest, and relationship view used for a stage.

## Compatibility and migration

The current registry may be projected into this schema with inferred fields
marked `inferred`, unavailable provenance left absent, and curated compatibility
hints marked separately. Phase 3A uses that read-only projection as an
in-memory router view. Records whose roles, stages, and domains are only broad
inference are not executable candidates; this prevents legacy descriptions from
creating false routing confidence. The compatibility view never reads skill
bodies and never changes `.superpowers/SKILLS_INDEX.json`.

Phase 3A.1 refines this compatibility path without changing its source of
truth. `AUTHOR_DECLARED` and `CURATED` fields have full routing weight;
`INFERRED_HIGH_CONFIDENCE` fields are eligible with a confidence penalty;
`INFERRED` fields are contextual only; and `UNKNOWN` remains conservative.
The router does not infer permissions from a body and does not treat a
metadata proposal as promoted truth.

No migration, mass frontmatter rewrite, generated index rewrite, persistent
graph database, or learned-weight update is part of Phase 3A. The in-memory
relationship graph supports dependency expansion, conflict/alternative checks,
and positive contextual signals only for the current route invocation.
Historical success remains observation-only. Phase 1 of the [Migration Plan](MIGRATION_PLAN.md)
defines the future schema work, and the [Stage Router evaluation](evidence/STAGE_ROUTER_EVAL_V1.md)
records the pre-overlay metadata gaps. The Phase 3A.1 census and V2 replay
record which gaps remain after enrichment; future Hermes-style learning may
produce a `MetadataProposal`, but promotion still requires evaluation and
review.
