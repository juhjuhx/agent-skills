# Phase 3C.3 OpenCode Diagnostic Dogfood Route

This is the first Phase 3C.3 development trace. It records explicit
StageRoute outputs and operational evidence only; it does not record hidden
chain-of-thought, raw runtime output, prompts, credentials, or skill bodies.

## Task

| Field | Value |
|---|---|
| TASK | Diagnose the installed OpenCode provider/runtime blocker without changing the hardened read-only boundary |
| START_HEAD | `fb2d170795330eda3de07e25bd8b8d9ee383f86e` |
| BRANCH | `fix/v3-opencode-runtime-diagnostic` |
| TaskSpec | `T-phase3c3-opencode-runtime-diagnostic` |
| Complexity | `COMPLEX` |
| Ambiguity | `MEDIUM` |
| Risk | `HIGH` — provider diagnostics, configuration isolation, and evidence integrity |
| Scope | `tools/v3`, `schemas/v3`, `tests/v3`, `fixtures/v3`, `docs/v3` |
| Catalog snapshot | `snapshot:2349a6fe70aaf346` |
| Registry epoch | `registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac` |
| Metadata records inspected | 214 |
| Normal route body files loaded | 0 |

### TaskSpec summary

```yaml
task_id: T-phase3c3-opencode-runtime-diagnostic
task_type: bounded-runtime-diagnosis
objective: identify the OpenCode 1.18.25 blocker using one-variable probes
constraints: no-provider-change, no-credential-change, no-auto, no-permission-widening
required_outputs: sanitized-diagnostic-record, MODEL_RUNTIME_EVAL_V5, next-prompt
stop_conditions: [provider-failure, unsafe-ASK-path, unverified-runtime, successful-smoke]
```

`DEEP_UNDERSTANDING: NOT_USED` (`UNAVAILABLE`). The canonical catalog had no
exact installed `deep-understanding` record. The task was bounded by an
existing adapter contract, so source-driven checks, the direct provider probe,
and the existing permission/evidence gates supplied the required observable
artifacts. No substitute skill was invented.

`using-superpowers` remained the task/session orchestration authority. It was
loaded once at task start and was referenced as the resident GATE; its full
procedure was not reloaded as an ordinary candidate at every stage.

## Stage routes

Every active stage produced a route record. The router reused one immutable
214-record metadata snapshot and did not load `SKILL.md` bodies while ranking.

| Stage | Route ID | Objective | Skills considered | Skills selected / role slot | Result |
|---|---|---|---|---|---|
| UNDERSTAND | `route:T-phase3c3-opencode-runtime-diagnostic:understand:9bb0d34ce33cced4` | establish repo, runtime, and blocker boundary | 214 metadata records | `using-superpowers` / GATE; `understand-diff` / DOMAIN | `SKILLS_SELECTED` |
| RESEARCH | `route:T-phase3c3-opencode-runtime-diagnostic:research:b88ce03aacd0d42a` | verify installed OpenCode behavior and provider status | 214 metadata records | none | `NO_SKILL_NEEDED` |
| DESIGN | `route:T-phase3c3-opencode-runtime-diagnostic:design:6d4c421ddf1272b2` | define the smallest sanitized diagnostic contract | 214 metadata records | none | `NO_SKILL_NEEDED` |
| PLAN | `route:T-phase3c3-opencode-runtime-diagnostic:plan:d6706d5e45c94917` | sequence one-variable probes and stop gates | 214 metadata records | none | `NO_SKILL_NEEDED` |
| IMPLEMENT | `route:T-phase3c3-opencode-runtime-diagnostic:implement:db5f9e91a1c35035` | add explicit cause classification and safe record serialization | 214 metadata records | none | `NO_SKILL_NEEDED` |
| REVIEW | `route:T-phase3c3-opencode-runtime-diagnostic:review:413d76bf4777e8c4` | inspect provider diagnosis and secret boundary | 214 metadata records | none | `NO_SKILL_NEEDED` |
| VERIFY | `route:T-phase3c3-opencode-runtime-diagnostic:verify:4dbb7f8bd736375f` | validate schema, tests, and evidence record | 214 metadata records | `using-superpowers` / GATE; `writing-skills` / VERIFY | `SKILLS_SELECTED` |
| HARDEN | `route:T-phase3c3-opencode-runtime-diagnostic:harden:a6e7798942996d34` | ensure generic errors remain fail-closed | 214 metadata records | none | `NO_SKILL_NEEDED` |
| HANDOFF | `route:T-phase3c3-opencode-runtime-diagnostic:handoff:3a8f8f93849ce227` | publish blocker and next-runtime proposal | 214 metadata records | none | `NO_SKILL_NEEDED` |

### Route decisions and skill execution

- `UNDERSTAND`: `understand-diff` was read for applicability. It supplied no
  runtime-diagnostic procedure and was not executed as a code-change recipe.
- `VERIFY`: `writing-skills` was read for trigger verification only. It is a
  skill-authoring workflow and was not executed; this is recorded as a
  `ROUTING_DEFECT`, not treated as verification evidence.
- The resident `using-superpowers` authority governed the stage sequence and
  was not repeatedly full-loaded.
- All other active stages returned `NO_SKILL_NEEDED` because the existing
  contract, one-variable diagnostic order, and user-specified stop rules were
  sufficient. No quota was applied.

The router defect was not patched in this branch:

```yaml
ROUTING_DEFECT:
  stage: VERIFY
  selected_skill: writing-skills
  role: VERIFY
  body_loaded: true
  procedure_executed: false
  reason: skill authorship is unrelated to runtime/evidence verification
  follow_up: routing-quality backlog; no Stage Router weight change here
```

## Diagnostic route

The operational sequence was deliberately short:

1. Verify local OpenCode version/help and the pinned release.
2. Inspect provider/model identity without reading auth material.
3. Stop before agent/lifecycle/output probes when the provider probe directly
   reported that the configured provider was not found.
4. Do not substitute an already-listed Xiaomi model and do not rerun the
   failed contract smoke.

The direct probe was:

```text
opencode models anthropic --pure
```

It used the existing bounded subprocess boundary: explicit argv,
`shell=False`, `stdin=DEVNULL`, isolated temporary cwd, finite timeout, and
digest-only persistence. The sanitized observation was exit 1, zero stdout
bytes, 50 stderr bytes, and a direct `Provider not found: anthropic` result.

The configured primary model was safely observed as
`anthropic/claude-sonnet-4-5` in sanitized resolved-config evidence. The
installed model listing exposed Xiaomi providers only. Auth inspection exposed
provider identifiers/status only; no credential contents were read or saved.

## Stage artifact contract

| Stage | Inputs | Outputs | Evidence required | Result |
|---|---|---|---|---|
| UNDERSTAND | Phase 3C.2 evidence, current branch | TaskSpec summary, source checklist | version/head/branch | established |
| RESEARCH | installed help, release tag, provider listing | provenance facts, provider diagnosis | direct installed-version evidence | blocked at provider resolution |
| DESIGN | existing adapter, schemas, Phase 3C.1 metric rules | allowlisted diagnostic fields | no raw details, no authority grant | completed |
| PLAN | diagnostic priority and stop rule | one-variable probe plan | no random retries/fallback model | completed |
| IMPLEMENT | observation + explicit probe status | classifier, schema field, focused tests | generic UnknownError remains unknown | completed |
| REVIEW | diff, tests, provider record | security/evidence findings | no credential/log leakage | static pass |
| VERIFY | focused tests, record validator | sanitized append-only record | schema-valid record | completed |
| HARDEN | fail-closed requirements | no additional probe after blocker | no permission widening | completed |
| HANDOFF | V5 evidence and final cause | next-runtime proposal | no Phase 4 execution | ready |

## Result

The route ended with `OPENCODE_RUNTIME_BLOCKED`, cause
`PROVIDER_NOT_CONFIGURED`, evidence status `DIRECT_PROBE`. The diagnosis is
specific to the current configured provider resolution; a generic structured
`UnknownError` by itself remains `RUNTIME_UNKNOWN` under the classifier.

The hardened contract smoke did not pass, so H03 was not run. No agent
resolution probe, explicit-model probe, lifecycle probe, or output-contract
probe was justified after the first-priority provider failure. The append-only
sanitized record is
[`live-opencode-provider-probe-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-opencode-provider-probe-001.json).
