# Phase 1 Machine-Readable Contracts

> Status: **implemented contract artifacts**. Phase 1 adds schemas, fixtures, validation, and compatibility projection. It does not implement the stage router, generated native adapters, installer changes, or registry migration.

## Contract files

The public contract names map to these JSON Schema Draft 2020-12 documents:

| Contract | Schema |
|---|---|
| `TaskSpec` | [`schemas/v3/task-spec.schema.json`](../../schemas/v3/task-spec.schema.json) |
| `SkillMetadataV3` | [`schemas/v3/skill-metadata-v3.schema.json`](../../schemas/v3/skill-metadata-v3.schema.json) |
| `AgentAdapterManifest` | [`schemas/v3/agent-adapter-manifest.schema.json`](../../schemas/v3/agent-adapter-manifest.schema.json) |
| `ModelProfile` | [`schemas/v3/model-profile.schema.json`](../../schemas/v3/model-profile.schema.json) |
| `StageRoute` | [`schemas/v3/stage-route.schema.json`](../../schemas/v3/stage-route.schema.json) |
| Shared definitions | [`schemas/v3/common.schema.json`](../../schemas/v3/common.schema.json) |

Every v3 record declares `schema_version: "3.0"`. Unsupported versions fail validation rather than being silently coerced.

## Validation surface

The read-only validator is [`tools/v3/contract_validation.py`](../../tools/v3/contract_validation.py). It intentionally stays small and uses the Python standard library. It validates the JSON Schema vocabulary used by these documents and adds only the cross-record rules that belong at this boundary:

- `TaskSpec` has a minimal required shape while detailed budgets, artifacts, assumptions, unknowns, and acceptance criteria remain optional.
- `SkillMetadataV3` accepts missing measurements and unavailable legacy provenance; historical success is never a required core field.
- `AgentAdapterManifest` describes runtime surfaces and boolean capabilities. It cannot contain provider/model identity.
- `ModelProfile` describes provider/model capability, limits, reasoning effort, measurements, cost class, and data policy. It cannot contain runtime identity.
- `StageRoute` always requires an explicit `SKILLS_SELECTED` or `NO_SKILL_NEEDED` status. The latter requires `no_skill_reason` and cannot carry selected skills or role assignments.

Run the contract tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Capability resolution

Capability names are open for future extensions. A requirement or adapter advertisement that is not in the Phase 1 known set is reported as `unknown_capabilities` and remains unresolved; `x-` and `custom:` names are explicit extension namespaces. An unknown capability on `StageRoute.granted_capabilities` is an error. A declaration describes a need or an advertisement—it never grants a permission.

## Using-Superpowers residency

`using-superpowers` is the task/session-level orchestration authority. A route may reference it in the `GATE` slot, but Phase 1 does not require reloading its full `SKILL.md` at every stage. The route record preserves the authority reference and the stage-local selection while keeping the authority's instructions resident at the task boundary.

## Current registry compatibility

The compatibility helper reads the existing registry without changing it:

| Current source | v3 mapping | Classification |
|---|---|---|
| `SKILLS_INDEX.json.id`, `name`, `description`, `triggers` | `skill_id`, `name`, `description`, `triggers` | `DIRECT` |
| registry `source`, `source_ref`, `relative_path` | `source.repo`, `source.ref`, `source.path` | `DIRECT` |
| entry `sha256` | `source.digest` with an explicit `sha256:` prefix | `DERIVED` |
| canonical repository origin | `trust: CORE_TRUSTED` | `DERIVED` policy projection |
| `categories[]` | `extensions.compatibility.current_categories` | `DIRECT`, not a v3 domain/stage |
| license, import date, stages, roles, task modes, domains | omitted and listed as unavailable | `UNAVAILABLE` |
| a legacy description beginning `[Deprecated:` | `extensions.compatibility.legacy_status` | `DEPRECATED` |

`categories.json` remains an installer/profile projection. Its categories are not silently converted into v3 domains. `.superpowers/ROUTING_POLICY.yaml` remains the current v2 policy; its required gate, role names, registry epoch, and budget values are compatibility evidence, not a Phase 1 runtime migration. OpenCode-specific model IDs are not copied into universal schema logic.

The compatibility fixture is [`fixtures/v3/compatibility/current-skill-index-entry.json`](../../fixtures/v3/compatibility/current-skill-index-entry.json), and tests also read the actual `.superpowers/SKILLS_INDEX.json`.

## Security boundary

Schema fields describe declared permissions, paths, commands, hooks, plugins, and MCP surfaces. They do not grant any of them. Phase 1 rejects absolute or traversal paths in native/config references, rejects unknown granted capabilities, keeps third-party trust states explicit, and leaves actual policy enforcement to `using-superpowers` and the native adapter.

## Source references

The contract format follows the [JSON Schema Draft 2020-12 specification](https://json-schema.org/draft/2020-12) and preserves the portable `SKILL.md` plus progressive-disclosure model in the [Agent Skills specification](https://agentskills.io/specification). The v3 adapter boundary also follows the public Codex [`AGENTS.md` guidance](https://github.com/openai/codex/blob/main/docs/agents_md.md) without importing runtime-specific configuration into the universal schemas.

## Explicit non-goals

This phase does not provide a router, route scoring, agent execution, generated configuration, automatic registry import, schema migration, database, MCP installation, or native adapter behavior. Those remain follow-up work described in [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).
