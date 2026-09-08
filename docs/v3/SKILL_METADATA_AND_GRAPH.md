# Skill Metadata and Graph

> Status: **future schema design**. No schema migration is introduced by this PR.

## Source of truth

The canonical skill source remains the repository's `SKILL.md` files. The current `.superpowers/SKILLS_INDEX.json` is a machine-readable snapshot used for discovery, while `categories.json` is the installer/profile projection. v3 enriches the metadata contract without replacing either file in this documentation pass.

## Proposed v3 record

Every future record should expose the following fields:

```json
{
  "id": "namespace.skill-id",
  "source": {
    "repository": "https://example.invalid/skill-source",
    "path": "skills/example/SKILL.md",
    "ref": "immutable-ref",
    "digest": "sha256:..."
  },
  "version": "1.0.0",
  "license": "MIT",
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
    "read": "low",
    "local_write": "medium",
    "external_write": "high"
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

The current registry may be projected into this schema with inferred fields marked `unmeasured`, `inferred`, or `planned`. No migration, mass frontmatter rewrite, generated index rewrite, or runtime consumer is part of v3 documentation. Phase 1 of the [Migration Plan](MIGRATION_PLAN.md) defines the future schema work.
