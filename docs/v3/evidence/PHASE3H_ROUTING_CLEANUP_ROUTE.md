# Phase 3H Routing Cleanup Dogfood Route

This is the orchestration record for the bounded Phase 3H work. It records
the same task and stages before and after metadata cleanup. It does not record
hidden reasoning or raw skill bodies.

## Repo truth

| Item | Value |
|---|---|
| Branch | `fix/v3-stage-router-defect-closure` |
| Starting HEAD | `188269a70830a10c2cc360b01b57f291de0b6aa9` |
| Task fixture | [`phase3h-dogfood-v1.json`](../../../fixtures/v3/routing/phase3h-dogfood-v1.json) |
| Catalog | 214 metadata records |
| Resident authority | `using-superpowers` (GATE; not reloaded as a normal candidate) |
| Stage Router | unchanged globally; no weight edit |
| Runtime/model work | not executed; Codex transport remains blocked |

The task intentionally used seven active stages rather than forcing all nine:
understand, research, plan, implement, review, verify, and handoff.

## Routing contract used

```text
TaskSpec + Stage + compiled routing snapshot
    → metadata-only StageRoute
    → selected skill IDs/roles
    → selected-only downstream loading if execution requires a body
```

Every stage emitted either `SKILLS_SELECTED` or `NO_SKILL_NEEDED`. The router
inspected 214 metadata records and reported zero body files loaded in both
replays. The resident orchestration authority was not converted into a
repeated per-stage body load.

## Dogfood routes before

This is the base-state replay captured before the Phase 3H closure patches.

| Stage | Result | Route suffix | Selected skills | Context proxy |
|---|---|---|---|---:|
| understand | `SKILLS_SELECTED` | `understand:abb812ae2a038a9b` | `using-superpowers`, `understand`, `understand-chat` | 50,652 B |
| research | `SKILLS_SELECTED` | `research:bd5b502b7448c250` | `using-superpowers`, `understand`, `understand-chat`, `verification-before-completion` | 54,856 B |
| plan | `SKILLS_SELECTED` | `plan:33389c5360803152` | `using-superpowers`, `writing-plans`, `logic-explain`, `llm-council` | 13,100 B |
| implement | `SKILLS_SELECTED` | `implement:65fccaabc4022c05` | `using-superpowers`, `executing-plans`, `test-driven-development`, `logic-explain`, `code-review-excellence`, `verification-before-completion` | 28,568 B |
| review | `SKILLS_SELECTED` | `review:998bdeb04b079226` | `using-superpowers`, `module-map`, `brooks-audit`, `pr-review-toolkit`, `verification-before-completion` | 9,188 B |
| verify | `SKILLS_SELECTED` | `verify:77b741d5298bd4c5` | `using-superpowers`, `brooks-harness`, `llm-council`, `brooks-test`, `verification-before-completion` | 17,164 B |
| handoff | `SKILLS_SELECTED` | `handoff:d7d54be1774e8266` | `using-superpowers`, `finishing-a-development-branch`, `brooks-harness`, `full-output-enforcement` | 17,012 B |

Observed false-positive families in the base route included broad knowledge
graph/chat helpers, council, and Brooks harness. Those occurrences are also
preserved in the [defect census](../../../fixtures/v3/routing/stage-router-defect-census-v1.json).

## Dogfood routes after

The final replay used the same TaskSpec and stage definitions after compiling
the generated overlay with the curated semantic patches.

| Stage | Result | Route suffix | Selected skills | Context proxy | Assessment |
|---|---|---|---|---:|---|
| understand | `NO_SKILL_NEEDED` | `understand:a33b0cf3c4517875` | none | 0 B | generic repository evidence no longer activates a knowledge-graph family |
| research | `SKILLS_SELECTED` | `research:d48395b5db209b1c` | `using-superpowers`, `orchestrate`, `mathguard`, `verification-before-completion` | 24,232 B | `mathguard` is a one-off false positive; deferred explicitly |
| plan | `SKILLS_SELECTED` | `plan:6f7c95bacbf81778` | `using-superpowers`, `writing-plans`, `logic-explain` | 9,316 B | council removed without losing planning |
| implement | `SKILLS_SELECTED` | `implement:65fccaabc4022c05` | `using-superpowers`, `executing-plans`, `test-driven-development`, `logic-explain`, `code-review-excellence`, `verification-before-completion` | 28,568 B | required process/review/verify complement preserved |
| review | `SKILLS_SELECTED` | `review:998bdeb04b079226` | `using-superpowers`, `module-map`, `brooks-audit`, `pr-review-toolkit`, `verification-before-completion` | 9,188 B | stable review route |
| verify | `SKILLS_SELECTED` | `verify:dd1ae274faa93d1d` | `using-superpowers`, `brooks-test`, `verification-before-completion` | 6,044 B | harness/council false positives removed |
| handoff | `SKILLS_SELECTED` | `handoff:a41be18a7d2cefc7` | `using-superpowers`, `finishing-a-development-branch`, `session-handoff`, `full-output-enforcement` | 11,780 B | explicit handoff procedure remains relevant |

`orchestrate` is not a defect here because the task explicitly coordinates
multiple stages. `session-handoff` is not a defect because the final stage
explicitly publishes a handoff. Neither was suppressed by a fixture rule.

## Fix disposition for Phase 3H observations

| Observation | Final disposition | Evidence |
|---|---|---|
| `understand-dashboard` in generic understand | `FIXED_METADATA` | requires explicit graph dashboard/visualization signal |
| `understand-domain` in generic understand | `FIXED_METADATA` | requires business-domain/process-flow signal |
| `MCP Integration` in generic research | `FIXED_METADATA` | requires MCP/Model Context Protocol signal |
| `survey-generator` in generic research | `FIXED_METADATA` | requires survey/literature/bibliography/deep-dive signal |
| `understand-diff` in generic understand | `FIXED_METADATA` | requires diff/PR/change-impact signal; positive counterpart selects it |
| `invariant-guard` in generic research | `FIXED_METADATA` | requires algorithm/invariant/postcondition signal; positive counterpart selects it |
| `redesign-existing-projects` in generic research | `FIXED_METADATA` | requires existing-site/UI redesign signal |
| `mathguard` in generic research | `FALSE_POSITIVE_CONFIRMED_BUT_DEFERRED` | one occurrence, body not loaded/executed; no evidence for a safe broad exclusion yet |

The changes are local curated field patches and a provenance-gated semantic
activation filter. No relationship was deleted, no role was globally capped,
and no fixture ID is mentioned in routing logic.

## Selected-only and safety observations

- Ranking body files loaded: `0` before and `0` after.
- The router did not execute shell commands, MCP instructions, URLs, or skill
  scripts while inspecting catalog bodies offline.
- Only selected skill IDs are eligible for downstream body loading; the
  deferred `mathguard` body was not loaded or executed.
- Curated metadata contains no permission grant. Trust, runtime capability,
  and permission policy remain governed by the existing contracts.
- The only unresolved routing backlog is the isolated `mathguard` selection;
  it does not meet the Phase 3H rule for a repeated, material defect family.

## Handoff

Stage Router production readiness is evaluated separately in
[`STAGE_ROUTER_EVAL_V4.md`](STAGE_ROUTER_EVAL_V4.md). Codex live transport is
carried forward as `CODEX_LIVE_TRANSPORT_BLOCKED`; this phase did not retry or
reinterpret it.

