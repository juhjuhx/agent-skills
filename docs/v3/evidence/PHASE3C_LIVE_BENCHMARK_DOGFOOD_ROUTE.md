# Phase 3C live benchmark dogfood route

This is the first dogfood trace for the bounded live-execution benchmark.
`using-superpowers` remained the task/session authority. It was represented as
the resident `GATE` in routes and was not reloaded as a normal candidate body at
each stage. The machine router used the current 214-record metadata snapshot;
normal ranking reported zero `SKILL.md` body reads.

## TaskSpec summary

- Task: implement a bounded live benchmark runner and publish evidence.
- Complexity: `COMPLEX`; risk: `HIGH`; ambiguity: `MEDIUM`; architecture impact:
  `LOCAL`.
- Required capabilities: editing, sandbox, structured output.
- Permission envelope: workspace-write, network none, no secrets, publish, or
  delete authority.
- Stop conditions: no adaptive model routing, no Stage Router weight changes,
  no new runtime adapters, no installations, and no external-project changes.
- Deep Understanding: `NOT_USED`. The gate was evaluated, but the current
  catalog has no exact Deep Understanding record and the task proceeded through
  the normal metadata router with that limitation recorded.

## Active StageRoutes

| Stage | Route status / route ID | Selected skills and role slots | Why / evidence result |
|---|---|---|---|
| UNDERSTAND | `NO_SKILL_NEEDED` / `route:T-phase3c-live-benchmark-dogfood:understand:a1db3e85fa451759` | none | No candidate met the relevance, trust, capability, role, and budget gates; TaskSpec and source truth were established directly. |
| RESEARCH | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:research:0a6933561b7410b0` | `using-superpowers` (GATE); `verification-before-completion` (VERIFY) | Runtime help and first-party references needed verification; selected body was loaded on demand. |
| DESIGN | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:design:79fc859f04c032ec` | `using-superpowers` (GATE); `verification-before-completion` (VERIFY) | The route selected a verification discipline but no distinct design/domain skill; this metadata gap is evidence, not silently repaired. |
| PLAN | `NO_SKILL_NEEDED` / `route:T-phase3c-live-benchmark-dogfood:plan:bec6e9df3e278b22` | none | No candidate passed the stage gates; the bounded plan was kept in explicit artifacts. |
| IMPLEMENT | `NO_SKILL_NEEDED` / `route:T-phase3c-live-benchmark-dogfood:implement:cdb693ece8b8a188` | none | No candidate passed the stage gates for this task-shaped input; implementation proceeded only after the route record was emitted. |
| REVIEW | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:review:cddff3429f6cb6fa` | `using-superpowers` (GATE); `brooks-review` (REVIEW); `pr-review-toolkit` (REVIEW); `brooks-harness` (VERIFY) | Review and verification evidence were required. `brooks-harness` was read for its applicability boundary and not run as a brooks-lint maintenance pipeline because its own trigger excludes other repositories. |
| VERIFY | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:verify:f68d600d3cb32059` | `using-superpowers` (GATE); `writing-skills` (VERIFY) | A verification route was emitted; `writing-skills` was inspected but its skill-authoring workflow was not applicable to this Python/evidence change. |
| HARDEN | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:harden:1f57df202877991c` | `using-superpowers` (GATE); `brooks-review` (REVIEW); `verification-before-completion` (VERIFY) | Credential, serialization, permission, and live-lane failure boundaries required independent hardening evidence. |
| HANDOFF | `SKILLS_SELECTED` / `route:T-phase3c-live-benchmark-dogfood:handoff:df97c19268b95224` | `using-superpowers` (GATE); `handoff` (PROCESS); `verification-before-completion` (VERIFY) | Record the evidence-bounded verdict and next prompt; no Phase 4 work started. |

## Operational artifacts

- Input artifacts: current v3 contracts, Stage Router snapshot, holdout index,
  local runtime help, and isolated fixture repositories.
- Output artifacts: `tools/v3/live_benchmark.py`,
  `schemas/v3/live-execution-record.schema.json`, validated run records, and
  `MODEL_RUNTIME_EVAL_V2.md`.
- Evidence gate: every active stage has a route; live quality is accepted only
  for a process that actually produced a result; blocked/timeout lanes are
  `UNAVAILABLE` and cannot enter quality or Pareto comparisons.
- No hidden chain-of-thought, raw `SKILL.md` body, stdout, stderr, prompt,
  environment, credential, or auth header is persisted.
