# Phase 3D Claude Read-only Adapter Dogfood Route

This trace records the first Phase 3D development run. It contains explicit
StageRoute outputs and operational evidence only; it does not contain hidden
chain-of-thought, raw prompts, raw runtime output, credentials, or skill
bodies.

## Task

| Field | Value |
|---|---|
| TASK | Establish the smallest benchmark-safe Claude Code read-only boundary |
| START_HEAD | `6988c778d634630df2cabf236ab14fc6ca74689f` |
| BASE | `fix/v3-opencode-runtime-diagnostic` |
| BRANCH | `feat/v3-claude-readonly-adapter` |
| TaskSpec | `T-phase3d-claude-readonly-adapter` |
| Complexity | `COMPLEX` |
| Risk | `HIGH` |
| Ambiguity | `HIGH` — installed Claude flags, auth category, and headless behavior required fresh verification |
| Architecture impact | adapter vertical slice; no Stage Router or universal-contract redesign |
| Registry snapshot | `snapshot:2349a6fe70aaf346` |
| Registry epoch | `registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac` |
| Metadata records inspected while routing | `214` |
| SKILL.md bodies read while ranking | `0` |

### TaskSpec summary

```yaml
task_id: T-phase3d-claude-readonly-adapter
task_type: implementation
objective: establish a Claude Code 2.1.235 read-only execution boundary
constraints:
  - no Stage Router changes
  - no other runtime adapters
  - no installations or credential changes
  - no permission widening
required_capabilities: [needs_editing, needs_sandbox, needs_structured_output]
permission_intent: workspace-write for the repository implementation; read-only for the live H03 lane
evidence: projection tests, contract validation, bounded smoke, sanitized record
```

`using-superpowers` was the resident task/session authority. It was loaded
once for orchestration and referenced as the GATE; it was not reloaded as a
normal candidate at every stage.

`DEEP_UNDERSTANDING: NOT_USED`. No exact installed `deep-understanding`
record was available in the repository catalog. The router surfaced
`understand`/`understand-chat`, but their knowledge-graph procedure was not
applicable to this bounded adapter task and was not executed. The fallback
was source-driven installed-help/documentation research plus existing
contract inspection; no substitute skill was invented.

## Stage routes

Every active stage emitted a route. The router reused the immutable metadata
snapshot and loaded no skill body during ranking.

| Stage | Route ID | Skills selected / role slots | Why selected | Result |
|---|---|---|---|---|
| UNDERSTAND | `route:T-phase3d-claude-readonly-adapter:understand:f17b75f8131595a4` | `using-superpowers` / GATE; `understand` / PROCESS; `understand-chat` / DOMAIN | Task/session authority, repository understanding, and task framing | `SKILLS_SELECTED` |
| RESEARCH | `route:T-phase3d-claude-readonly-adapter:research:2a14b115ffa25637` | `using-superpowers` / GATE; `verification-before-completion` / VERIFY | First-party CLI/auth/permission evidence and freshness gate | `SKILLS_SELECTED` |
| DESIGN | `route:T-phase3d-claude-readonly-adapter:design:f3fc5d65a99277d7` | `using-superpowers` / GATE; `brandkit` / PROCESS; `verification-before-completion` / VERIFY | Router output; `brandkit` was not semantically relevant to runtime-contract design | `SKILLS_SELECTED` |
| PLAN | `route:T-phase3d-claude-readonly-adapter:plan:e8baf54a1d8bee7f` | `using-superpowers` / GATE; `executing-plans` / PROCESS; `writing-plans` / PROCESS; `llm-council` / VERIFY | Small implementation sequence and verification gate; `llm-council` was not relevant | `SKILLS_SELECTED` |
| IMPLEMENT | `route:T-phase3d-claude-readonly-adapter:implement:e80be8d05763df0b` | `using-superpowers` / GATE; `executing-plans`, `test-driven-development` / PROCESS; `invariant-guard` / DOMAIN; `code-review-excellence` / REVIEW; `verification-before-completion` / VERIFY | Test-first projection, permission invariants, review, and evidence | `SKILLS_SELECTED` |
| REVIEW | `route:T-phase3d-claude-readonly-adapter:review:e0c01076336664f2` | `using-superpowers` / GATE; `code-review-excellence`, `logic-logic-diff` / REVIEW; `verification-before-completion` / VERIFY | Independent code/diff review and completion evidence | `SKILLS_SELECTED` |
| VERIFY | `route:T-phase3d-claude-readonly-adapter:verify:c0e0bbd6827556da` | `using-superpowers` / GATE; `verification-before-completion` / VERIFY | Contract/schema/full-suite verification | `SKILLS_SELECTED` |
| HARDEN | `route:T-phase3d-claude-readonly-adapter:harden:fe1865b94950e47b` | `using-superpowers` / GATE; `pro-safe-mode` / REVIEW; `verification-before-completion` / VERIFY | Review safe-mode/config isolation and final evidence | `SKILLS_SELECTED` |
| HANDOFF | `route:T-phase3d-claude-readonly-adapter:handoff:00bd67308a6a330d` | `using-superpowers` / GATE; `handoff` / PROCESS; `verification-before-completion` / VERIFY | Preserve evidence boundary and hand off the blocked lane | `SKILLS_SELECTED` |

The selected procedure bodies used during implementation/review were loaded
progressively from the canonical catalog, including the test-first,
planning, invariant, code-review, security/hardening, simplification,
source-driven, and verification procedures. The router itself inspected
metadata only. Unrelated selections were not executed merely to satisfy a
quota.

## Routing defects observed

These were recorded and deliberately not fixed in this adapter branch:

```yaml
- stage: UNDERSTAND
  skill: understand / understand-chat
  issue: knowledge-graph-oriented procedure was not needed for this bounded task
  body_loaded: false
  procedure_executed: false
- stage: DESIGN
  skill: brandkit
  issue: visual-brand semantics do not match runtime-contract design
  body_loaded: false
  procedure_executed: false
- stage: PLAN
  skill: llm-council
  issue: multi-model deliberation is unrelated to the bounded implementation plan
  body_loaded: false
  procedure_executed: false
```

No Stage Router weights or fixture-specific exceptions were changed.

## Route-to-execution gates

1. Fresh installed Claude version/help and safe auth-category probe.
2. Test-first native contract and projection validation.
3. Smoke A: no tools, bounded `claude -p`, JSON output.
4. Smoke B: selected read-only file access only if Smoke A passes.
5. H03 only if both smokes pass, followed by independent artifact review.

Smoke A reached its finite timeout with no stdout/stderr. Therefore Smoke B
and H03 were not run. This is a runtime compatibility blocker, not a model
quality result.

## Snapshot evidence

| Metric | Result |
|---|---:|
| metadata records inspected | `214` |
| normal-route SKILL.md body reads | `0` |
| overlay digest | `sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b` |
| snapshot reused | `true` |
| warm route generation | approximately 11–19 ms per stage in this run |

No raw skill body or runtime output was put in this trace.
