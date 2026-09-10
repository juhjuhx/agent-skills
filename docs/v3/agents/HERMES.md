# Hermes Native Adapter

> Status: **qualification blocked (Phase 3E)**. The installed runtime is recorded as a candidate only; no Hermes adapter was built before the qualification gate.

## Native strengths to preserve

Hermes is an agent runtime, not a model provider. The adapter should preserve:

- persistent learned skills;
- `/learn`-style distillation;
- MCP integration;
- cross-agent import;
- long-running coordination.

These features produce learning artifacts and coordination events. They do not get a second copy of canonical skill policy.

## Learning boundary

```text
Hermes observation / session result
  -> OBSERVE
  -> DISTILL
  -> CANDIDATE
  -> DUPLICATE CHECK
  -> PROVENANCE
  -> EVAL
  -> REVIEW
  -> PROMOTION
```

Persistent memory may retain an approved learning proposal or a reference to a canonical skill. It must not silently rewrite routing rules, trust, permissions, required skills, or deny lists. Cross-agent import carries source refs, digest, license, eval status, and approval state.

## Long-running coordination

Long-running Hermes work maps to stage records and handoff artifacts. The adapter reports active stage, budget, last artifact, pending evidence, cancellation state, and next route. A resumed run uses the pinned task/stage context and records any legal boundary reroute.

## Deferred implementation

The qualification gate must pass before an adapter or memory bridge is designed. The
current installed `--oneshot` path auto-bypasses approvals and the configured
`custom:agnes-ai` provider is logged out, so Phase 3E stops before adapter work.
Any future adapter must reuse Hermes native memory rather than introduce a duplicate
learning store, while still enforcing the canonical [Learning and Evaluation](../LEARNING_AND_EVALS.md)
promotion chain. The immediate next proposal is a controlled Codex model/reasoning
experiment, not another runtime adapter.
