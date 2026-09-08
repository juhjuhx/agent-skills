# Reasoning Artifacts

> Status: **observable handoff contract**. v3 does not attempt to expose or standardize private hidden chain-of-thought.

## Principle

Each agent and model may reason in its native way. Cross-agent coordination depends on explicit, reviewable artifacts rather than hidden internal traces. An artifact should be sufficient for the next stage to act, challenge, or verify without requiring access to private reasoning.

## Required artifact vocabulary

| Artifact | Purpose | Minimum content |
|---|---|---|
| `TaskSpec` | Shared task definition | goal, scope, modes, capabilities, risk, budget, acceptance criteria |
| `Assumptions` | Make inferred premises visible | statement, source, confidence, invalidation signal |
| `Unknowns` | Prevent invented certainty | question, impact, owner, resolution state |
| `Decision Record` | Preserve why a choice was made | context, decision, alternatives, consequences, evidence |
| `Stage Plan` | Make the next stage executable | stage, work items, selected roles, dependencies, stop conditions |
| `Alternatives` | Keep material options comparable | option, fit, cost, risk, rejected/selected reason |
| `Evidence` | Support claims and completion | source, command/tool, result, digest, timestamp, scope |
| `Risk` | Identify failure and side-effect paths | likelihood, impact, mitigation, residual state |
| `Verification` | Decide whether acceptance is met | criterion, check, result, failure, environment |
| `Learning Proposal` | Suggest a reusable improvement | observation, distilled rule, provenance, eval, approval state |

## Handoff envelope

```yaml
handoff:
  task_id: T-<id>
  stage: review
  summary: <short observable outcome>
  task_spec_ref: <artifact-ref>
  assumptions_ref: <artifact-ref>
  unknowns_ref: <artifact-ref>
  decisions: [<decision-ref>]
  stage_plan_ref: <artifact-ref>
  alternatives_ref: <artifact-ref>
  evidence: [<evidence-ref>]
  risks: [<risk-ref>]
  verification_ref: <artifact-ref>
  learning_proposal_ref: <optional-artifact-ref>
  files_changed: []
  permissions_used: []
  model_profile_ref: <profile-ref>
  adapter_ref: <adapter-ref>
```

References should prefer stable paths, IDs, digests, and concise summaries over pasting a whole repository or private transcript. Sensitive input must be redacted according to policy; redaction itself is observable.

## Artifact quality gate

An artifact is acceptable when it is:

- specific enough to be checked;
- linked to evidence or explicitly marked as an assumption;
- scoped to the current stage;
- small enough for the next consumer's context budget;
- independent of a provider/model name;
- safe to share across the selected adapters.

An artifact is not a transcript dump, a claim of hidden thought, or a substitute for execution evidence. The evidence gate may request a missing artifact, reroute to a review/verify role, or block completion.
