# Learning and Evaluation

> Status: **future control-plane design**. No automatic import, database, or self-modifying router is introduced by this PR.

## Hermes-inspired learning loop

Hermes is the primary donor for the learning system. Preserve its strengths—persistent learned skills, `/learn`-style distillation, MCP, cross-agent import, and long-running coordination—but place every promotion behind canonical policy.

The minimum proposal chain is:

```text
OBSERVE
  -> DISTILL
  -> CANDIDATE
  -> DUPLICATE CHECK
  -> PROVENANCE
  -> EVAL
  -> REVIEW
  -> PROMOTION
```

The full intake path for unknown material is:

```text
Discover
  -> Quarantine
  -> Inspect source
  -> License / provenance
  -> Distill
  -> Duplicate / overlap analysis
  -> Candidate
  -> Routing eval
  -> Execution eval
  -> Security review
  -> Human/policy approval
  -> Promotion
```

Unknown external skills, plugins, and MCP servers must never be automatically promoted into the trusted core. A failed or incomplete step leaves the item quarantined or blocked.

## Learning proposal

```yaml
learning_proposal:
  id: LP-<stable-id>
  observation: <what happened>
  distilled_rule: <small reusable procedure or metadata change>
  source_refs: [<artifact-or-repository-ref>]
  source_ref: <immutable-ref>
  license: <declared-or-unknown>
  digest: <digest>
  duplicate_analysis: <result>
  routing_eval: <result>
  execution_eval: <result>
  security_review: <result>
  affected_skills: []
  proposed_change: <content | metadata | adapter | policy>
  approval: pending
  promotion_target: <quarantine | curated | core>
```

Distillation must preserve provenance and avoid copying upstream prose without license tracking. Promotion changes a versioned artifact or metadata record; it does not mutate an agent's hidden memory into policy.

## Evaluation suites

The future eval system should include independent suites for:

- routing;
- activation;
- near-miss triggering;
- task completion;
- evidence quality;
- context/token efficiency;
- cross-agent handoff;
- regression;
- security;
- skill-learning.

Fixtures should represent real workloads across coding, bugfix, architecture, web research, design, frontend, image workflow, security, performance, documentation, content creation, and handoff.

Each fixture should declare its expected stage, role coverage, permission envelope, acceptance criteria, and independent evidence. Near-miss fixtures are required so a broad trigger does not look good only because it activates on obvious examples.

## Evaluation record

```yaml
eval_run:
  task: <task-id>
  stage: <stage>
  agent: <runtime-id>
  model: <model-profile-ref>
  skills: [<skill-ref>]
  context: {input_tokens: 0, artifact_tokens: 0, tool_schema_tokens: 0}
  tool_calls: 0
  duration_ms: 0
  reroutes: []
  files_changed: []
  tests: []
  verification: []
  user_correction: null
  outcome: pass | partial | fail | blocked
```

History may generate a routing proposal, an eval fixture, or a compatibility warning. It may not silently rewrite routing policy, required/deny lists, trust state, permissions, or acceptance criteria. A promotion must have provenance, evaluation evidence, security review, and human/policy approval.

## Cost and independence

Evaluation tracks context, tool-schema budget, duration, reroutes, and correction—not only final success. Routing and execution evaluation should avoid using the exact same generated judgment as both selector and grader. Independent review lanes remain independent; see [Review Pipeline](REVIEW_PIPELINE.md).
