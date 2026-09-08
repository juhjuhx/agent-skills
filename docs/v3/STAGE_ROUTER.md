# Stage-Local Skill Router

> Status: **design contract**. This is not an implementation of the current router.

## Inputs and outputs

The router accepts a `TaskSpec`, the current stage, the canonical registry snapshot, adapter capabilities, model profiles, policy grants, and the remaining budget. It returns a stage route plus explicit reasons.

```yaml
StageRoute:
  schema_version: "3.0"
  route_id: <route-id>
  task_id: <task-id>
  stage: implement
  status: SKILLS_SELECTED
  selected_skills:
    - skill_id: using-superpowers
      role: GATE
      reason: orchestration authority
    - skill_id: incremental-implementation
      role: PROCESS
      reason: smallest authorized slice
  role_assignments:
    - skill_id: using-superpowers
      role: GATE
    - skill_id: incremental-implementation
      role: PROCESS
  adapter: codex
  model_profile: <profile-ref>
  granted_capabilities: [editing, structured_output]
  budget_envelope:
    permission_level: workspace-write
  alternatives: []
  evidence_required: [diff, tests, verification]
  registry_epoch: <registry-epoch>
```

The router never needs private model reasoning. It needs the TaskSpec, metadata, capabilities, policy, and observable stage artifacts.

The Phase 1 [`StageRoute` schema](../../schemas/v3/stage-route.schema.json) uses `selected_skills`, `role_assignments`, `registry_epoch`, and an explicit route `status`. The YAML above is a conceptual example; no router implementation is introduced here.

## Role slots

Every stage may use the following slots:

| Slot | Purpose | Typical cardinality |
|---|---|---:|
| `GATE` | Policy and orchestration entry point | 0–1 |
| `PROCESS` | Procedure for how to do the stage | 0–2 |
| `DOMAIN` | Subject-matter method or discipline | 0–3 |
| `TOOL` | Tool/MCP/CLI capability | 0–3 |
| `REVIEW` | Quality, risk, architecture, security, or adversarial review | 0–2 |
| `VERIFY` | Completion evidence and acceptance checks | 0–2 |

The slots are a diversity constraint, not a quota. Five skills that all perform the same review role are worse than two skills covering distinct risks. The router should prefer complementary roles, reuse a skill when it remains the best fit, and leave a slot empty when it is irrelevant.

### Implementation example

```text
GATE
  using-superpowers

PROCESS
  test-driven-development
  incremental-implementation

DOMAIN
  tauri-development
  rust-engineering

REVIEW
  code-review-and-quality

VERIFY
  verification-before-completion
```

The two domain IDs are illustrative adapter/registry candidates; their appearance here does not claim that this baseline registry already contains them.

## Routing sequence

1. Load registry metadata and pin the current epoch for the stage.
2. Apply hard filters: stage, task mode, domain, required inputs/outputs, trust, permissions, tools, budget, and adapter compatibility.
3. Group surviving candidates by role slot.
4. Select the smallest sufficient complementary set.
5. Negotiate TaskSpec capabilities with the adapter.
6. Select a compatible model profile separately from the runtime.
7. Reserve stage budget and context budget.
8. Load selected `SKILL.md` files on demand; load references or scripts only when their contract requires them.
9. Execute and collect artifacts.
10. Run the stage evidence gate.
11. Advance, reroute, degrade, or block with an explicit reason.

## Capability negotiation

Task requirements are capability declarations, for example:

```yaml
needs_editing: true
needs_browser: false
needs_subagents: true
needs_sandbox: true
needs_MCP: false
needs_structured_output: true
needs_long_context: false
needs_multimodal: false
permission_level: workspace-write
budget: balanced
```

An adapter advertises capabilities such as editing, browser, subagents, sandbox, MCP, structured output, multimodal input, long context, permissions, parallelism, and native learning. The router intersects requirements with advertised capabilities. It does not choose because a runtime or model has a particular name.

## Reroute triggers

Reroute only when one of these observable events occurs:

- a stage boundary is reached;
- a required capability is unavailable or withdrawn;
- a selected skill is unhealthy, quarantined, or blocked;
- an evidence gate fails and identifies a missing role or capability;
- a user changes a material constraint;
- budget or context limits require a declared degradation;
- a review lane finds a new risk that changes the next stage.

Rerouting must preserve prior artifacts and must not erase a failed route. A route decision records the old route, new route, trigger, and evidence.

## Context and cost discipline

- Metadata and role selection precede full instruction loading.
- Only selected skills enter the stage context.
- Tool schemas are lazy and domain-scoped; MCP context cost is part of the budget.
- Large logs become artifacts with summaries and digests, not repeated prompt text.
- Fixed adapter instructions should stay stable for cache reuse; dynamic TaskSpec and stage artifacts follow them.
- A budget failure may reduce optional skills or context, but never relax permissions or acceptance criteria.

## Reference pseudocode

```text
route(TaskSpec task, Stage stage, Registry registry, Adapter adapter):
  candidates = registry.skills
    .filter(metadata_matches(task, stage))
    .filter(permission_and_trust_fit(task))
    .filter(capability_requirements_fit(task, adapter))
    .filter(cost_fits(task.budget))

  grouped = group_by_role(candidates)
  selected = minimum_sufficient_complement(grouped, task.acceptance_criteria)
  negotiated = adapter.negotiate(task.capabilities, selected)
  model = choose_model_profile(task, negotiated)
  return StageRoute(stage, selected, adapter.id, model, negotiated, reasons)
```

The placeholder functions are contracts for future tests, not runtime code. A model/provider name must not appear in the universal branch conditions.
