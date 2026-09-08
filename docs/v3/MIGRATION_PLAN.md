# Migration Plan

> Status: **proposal**. This PR is Phase 0 documentation/contracts only.

## Guardrails

The migration must preserve one canonical skill source, avoid hundreds of per-agent forks, keep `using-superpowers` as orchestration authority, and make every generated adapter traceable to a source ref/digest. A phase may ship only when its contracts have independent eval and security evidence.

## Phases

### Phase 0 — Documentation and contracts (this PR)

- Document the v3 architecture and ADRs.
- Define TaskSpec, stage routes, observable reasoning artifacts, skill metadata, graph relationships, adapter contract, and model profile contract.
- Document native adapters, learning/eval, security/provenance, and independent review lanes.
- Refresh README and the compact AGENTS bootstrap from machine-readable current truth.

This phase does not change skills, installer, runtime router, routing YAML, registry schema, database, cloud orchestration, MCP installation, or model catalog.

### Phase 1 — Schemas and fixtures

- Add versioned schemas for TaskSpec, StageRoute, artifacts, metadata, adapter capabilities, model profiles, trust, and evidence.
- Build fixture workloads and near-miss cases.
- Add deterministic validation without changing runtime routing.

### Phase 2 — Codex adapter

- Generate a small `AGENTS.md` bootstrap and native skill references.
- Map Codex Skills, Plugins, Subagents, MCP, config/permission profiles, and reasoning effort.
- Prove capability negotiation and artifact handoff against the fixture suite.

### Phase 3 — Claude Code, OpenCode, Hermes, MiMo Code, ZCode, and DeepSeek Harness adapters

- Implement native separation for persistent instructions, skills, commands, subagents, plugins, hooks, MCP, permissions, model selection, and context strategy.
- Preserve Hermes learning strengths without duplicating its memory.
- Treat DeepSeek Harness as a full harness and MiMo Code/ZCode as runtimes, not model aliases.

### Phase 4 — Eval-driven stage-local routing

- Implement stage planner, role-slot balancing, capability negotiation, evidence gates, and boundary reroutes.
- Measure routing, activation, near-miss, completion, evidence, cost, cross-agent, regression, security, and learning suites.
- Let history produce proposals only; require review/promotion for policy changes.

### Phase 5 — Installer and adapter generator

- Generate native bundles from the canonical source and approved metadata.
- Extend installation only after permissions, trust, provenance, rollback, and compatibility are tested.
- Keep `install.sh` as a compatibility surface until a reviewed replacement is ready.

## Explicitly deferred

No phase in this documentation PR moves 400+ skills, forks skills by agent, rewrites `install.sh`, rewrites `.superpowers/ROUTING_POLICY.yaml`, introduces a database, implements cloud orchestration, installs MCP servers, auto-imports external skills, or hard-codes new model names.
