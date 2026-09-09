# Using-Superpowers v3

> Status: **proposed orchestration contract**. `.superpowers/ROUTING_POLICY.yaml` remains unchanged in this PR.

## Authority

`using-superpowers` is the orchestration authority. It establishes the routing bootstrap, turns a request into a portable `TaskSpec`, owns stage transitions, and requires an evidence gate before completion. A skill may advise the core; it may not redefine the core's permissions, deny list, budget, or completion criteria. In Phase 3A, the resident authority delegates one validated stage at a time to the deterministic Stage Router; it remains the policy owner.

### Session-level residency

`using-superpowers` is a task/session-level authority, not an ordinary procedure that must reload its full instruction file at every stage. A stage route may reference it in the `GATE` slot so the authority is observable, while the runtime keeps the authority context resident at the task boundary. The Phase 3A router records this residency explicitly and does not score or reload it as a normal candidate.

The current v2 policy is predominantly task-level: it pins a registry snapshot and selects a bounded set of primary/optional skills once. That is useful baseline behavior, but it cannot adapt cleanly when later stages reveal new domain, review, or verification needs. v3 adds stage-local routing as a design target without changing v2 at runtime.

## v3 flow

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

The router creates a new route record at each stage. A route change is allowed only at a declared stage boundary or after an evidence gate reports that the current stage cannot satisfy its acceptance criteria. Every reroute records its reason, candidates considered, skills selected, capabilities negotiated, and budget impact.

Phase 1 makes the route record machine-readable. Phase 3A makes the stage-local selection step executable: every active stage still emits an explicit `SKILLS_SELECTED` or `NO_SKILL_NEEDED` status, while the validator and router reject a silent or contradictory route.

## Task classification

| Class | Default behavior | Deep Understanding |
|---|---|---|
| `SIMPLE` | Normal router; minimal sufficient artifacts | No |
| `STANDARD` | Feature extraction, normal stage plan | Optional when uncertainty remains |
| `COMPLEX` | Multi-stage plan, explicit alternatives and evidence | Yes |
| `AMBIGUOUS` | Resolve the highest-impact unknown; conservative permissions | Yes |
| `UNFAMILIAR` | Enrich domain and source context before implementation | Yes |
| `HIGH-RISK` | Stronger trust, permission, review, and verification gates | Yes |
| `ARCHITECTURE-CHANGING` | ADR and migration evidence required | Yes |

Deep Understanding is an escalation layer, not a mandatory preamble. If it is unavailable, the safe fallback is a bounded conservative `TaskSpec`, not an invented certainty.

## Stage model

The default stage planner may emit:

1. **Understand** — clarify goal, scope, constraints, assumptions, and unknowns.
2. **Research** — obtain current or authoritative evidence when freshness or unfamiliarity requires it.
3. **Design** — define interfaces, alternatives, risks, and decision records.
4. **Plan** — produce ordered work items, acceptance criteria, and stop conditions.
5. **Implement** — make the smallest authorized change and record files/artifacts.
6. **Review** — inspect quality, security, performance, architecture, and independent evidence lanes.
7. **Verify** — execute tests, checks, and acceptance evidence at the real boundary.
8. **Harden** — address confirmed findings, permissions, provenance, and recovery paths.
9. **Handoff / Learn** — package observable artifacts and propose, never silently promote, learnings.

Not every request needs every stage. The planner may skip irrelevant stages, but a skipped stage and its reason are observable.

## Skill activation policy

Stage-local guidance:

- Typical stage: 3–7 relevant skills.
- Complex stage: 5–10 relevant skills.
- Complex project: 30–50+ activations across all stages may be natural.
- There is no minimum skill quota.
- Do not call unrelated skills to satisfy a count.
- Reusing one skill in multiple stages is expected when its role remains relevant.
- Context loading is lazy: select metadata first, then load only selected `SKILL.md` files and required references.

The goal is the smallest sufficient set that covers the stage's roles, capabilities, permissions, and evidence—not the largest set that can be made to sound related. The Phase 3A baseline uses deterministic metadata scoring, hard filters, relationship checks, and role coverage; selected bodies remain a downstream adapter/resolver concern.

## Portable TaskSpec

```yaml
task_id: T-<stable-id>
goal: <observable outcome>
task_mode: [design, implement, review]
classification: STANDARD
stages: [understand, design, plan, implement, review, verify, handoff]
domains: [software-engineering]
inputs: [repository, user-requirements]
outputs: [patch, decision-record, verification-report]
constraints:
  needs_editing: true
  needs_browser: false
  needs_subagents: false
  needs_sandbox: true
  needs_MCP: false
  needs_structured_output: true
  needs_long_context: false
  needs_multimodal: false
  permission_level: workspace-write
  budget: balanced
risk:
  level: medium
  reasons: [public-documentation, external-publish]
assumptions: []
unknowns: []
acceptance_criteria: []
stop_conditions: []
```

The fields describe requirements and capabilities, not a particular model. Adapters advertise capabilities; the router negotiates them. Identity-specific branching is confined to the adapter.

## Stage records and evidence

Each stage produces a portable record containing:

```text
stage_id
stage_kind
input_artifact_refs
selected_skill_refs
role_assignments
adapter_id
model_profile_ref
budget_snapshot
route_reasons
execution_artifact_refs
evidence_refs
status: planned | running | review | verified | reroute | blocked
```

The evidence gate may advance, reroute, degrade to a plan/summary, or block. It cannot mark a task complete without acceptance evidence. Completion and learning handoff are separate events.

## Policy ownership and non-goals

This document does not change the current routing YAML, implement a general stage planner, create a database, install a model/provider, or replace Compose with Superpowers. Phase 3A implements only a small stage-local selector; model selection, runtime expansion, and historical-weight learning remain future work. Historical v2 material remains available in [the v2 architecture document](../using-superpowers-v2-extensible-architecture.md).
