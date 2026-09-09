# Next Codex Prompt — Phase 3C Bounded Live Benchmark Lanes

Copy this prompt into the next Codex session. It is the next bounded task
after Phase 3B. Do not execute it during Phase 3B.

## Mission

Repository: `juhjuhx/agent-skills`

Run a small, safe, evidence-producing benchmark of runtime/model execution
configurations using the Phase 3B contracts. The current verdict is
`INSUFFICIENT_LIVE_EVIDENCE`; the purpose of Phase 3C is to collect bounded
`REAL_EXECUTION` evidence, not to activate adaptive routing.

Do not redesign v3. Do not modify Stage Router weights. Do not implement
per-call routing, a learned router, bandits, model preferences, or the other
native adapters. Do not install runtimes, models, MCP servers, dependencies,
or credentials.

## Start and source truth

Verify without resetting local work:

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
```

Read the current contracts and implementations:

- `schemas/v3/runtime-candidate.schema.json`
- `schemas/v3/model-candidate.schema.json`
- `schemas/v3/execution-configuration.schema.json`
- `schemas/v3/evaluation-run.schema.json`
- `schemas/v3/evaluation-result.schema.json`
- `schemas/v3/runtime-handoff.schema.json`
- `tools/v3/runtime_model_evaluation.py`
- `tools/v3/stage_router.py`
- `tools/v3/codex_adapter.py`
- `fixtures/v3/model-routing/`
- `docs/v3/evidence/MODEL_RUNTIME_EVAL_V1.md`
- `docs/v3/evidence/RUNTIME_CAPABILITY_MATRIX.md`

Machine-readable registry data wins over prose. Keep the canonical skill
library, installer, Stage Router, and `.superpowers/ROUTING_POLICY.yaml`
unchanged.

## Dogfood and routing

Use `using-superpowers` as resident task/session authority. For each active
stage, invoke the existing Stage Router and emit a StageRoute with
`SKILLS_SELECTED` or `NO_SKILL_NEEDED`. Load only selected skill bodies after
route selection. Do not reload the resident `using-superpowers` body at every
stage and do not use model choice to alter skill ranking.

## Fresh provenance before live work

For every runtime/model actually exercised, record:

- observed installed version and executable probe;
- latest stable release/tag and resolved immutable source commit when
  available;
- exact official source/release reference used for the native contract;
- current upstream source/documentation snapshot and snapshot date;
- native support: `NATIVE`, `EMULATED`, `HOST_MANAGED`, or `UNSUPPORTED`;
- availability: `INSTALLED`, `RELEASE_SUPPORTED`, `UPSTREAM_ONLY`, or
  `UNKNOWN`;
- model selection granularity actually supported by that runtime.

Do not treat current-main documentation as installed-release proof. Do not
encode provider-specific IDs or URLs in universal routing code.

## Safe benchmark lanes

Use isolated temporary worktrees or fixture repositories. A lane may run only
when the executable is installed, its existing credentials/configuration are
already available, the task is safe, and cost is bounded. Never print or
serialize credentials. If a runtime/model is not available, record a missing
lane; do not substitute a mock and call it live evidence.

Start with a small, representative subset of the holdout set, for example:

- H01 bugfix;
- H02 multi-file feature;
- H03 API design;
- H06 security task;
- H07 deep source research;
- H09 release verification;
- H12 tool/MCP integration.

Keep A–J as development/regression data. Do not tune routing weights on the
holdout tasks. Record repetition `n` for every workload/configuration cell;
do not claim broad superiority from `n=1`.

## Runtime/model boundary

Evaluate runtime/harness compatibility at task/session scope. Within an
eligible runtime, evaluate a model at task, stage, or subagent scope only when
the runtime candidate advertises that granularity. If the runtime pins one
model, record `TASK_PINNED`; do not simulate stage switching. Per-inference
call routing remains design-only.

Changing runtimes is an explicit `RuntimeHandoff` containing source and
destination, reason, portable artifacts, working-tree state, permission
envelope, lost capabilities, and handoff cost. Do not make automatic handoff.

Effective authority remains:

```text
TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime restrictions
```

ModelCandidate, skill metadata, MCP declarations, plugins, and generated
configuration cannot widen it.

## Evidence records

For each run create an `EvaluationRun` and `EvaluationResult` with:

- evidence class and execution mode;
- runtime/model/configuration refs;
- selected skills and StageRoute refs;
- stage outcomes and one terminal task outcome;
- separate quality, efficiency, reliability, security, and portability axes;
- context/tokens, tool calls, latency, wall time, cost, reroutes, retries,
  files changed, tests, verification, and user correction;
- immutable input/artifact digests and source provenance.

Only `REAL_EXECUTION` may support quality/ranking conclusions.
`HOST_MANAGED_FIXTURE` supports compatibility only. `MOCK` supports unit
behavior only. Keep unknown measurements as `null` or an explicit
missing-evidence record.

## Baselines and comparison

Run every live lane against the existing evaluation-only baselines where
eligible:

- `BASELINE_STRONGEST`
- `BASELINE_CHEAPEST`
- `BASELINE_DEFAULT`
- `BASELINE_HEURISTIC`

Do not assume a baseline is good; measure it. Compare quality, cost, latency,
reliability, security, and portability separately. Produce Pareto frontiers
without a universal scalar score. A future recommendation must identify the
data and repetition supporting it, and remains a proposal until policy review.

## Tests and safety gates

Keep all current tests green. Add tests for live-run record shape, artifact
digests, task/stage model scope, terminal result capture, missing evidence,
runtime handoff, and no credential serialization. Verify that:

- a `NO_SKILL_NEEDED` route does no model-routing work;
- unsupported runtime switching is `TASK_PINNED` or explicitly unavailable;
- mock/fixture results never enter quality ranking;
- permissions never widen during configuration or handoff;
- no live run reads unrelated skill bodies;
- history remains append-only and proposal-only.

Run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Run the Alibaba OpenCodeReview auth/network precheck once. If native auth is
still `401`, record `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`; do not relabel a
delegate review as native OCR.

## Output

Create concise append-only evidence, for example:

- `docs/v3/evidence/MODEL_RUNTIME_EVAL_V2.md`
- `fixtures/v3/model-routing/runs/` or the repository's established evidence
  location

Report live lane count and `n`, missing lanes, terminal outcomes, stage
outcomes, quality/efficiency/reliability/security/portability evidence,
baseline comparisons, Pareto results, and provenance. Do not hide failures or
turn absent data into a preference.

## Decision at the end

Choose exactly one next state from evidence:

- `INSUFFICIENT_LIVE_EVIDENCE` — collect more safe repetitions or lanes;
- `ROUTING_EVIDENCE_READY` — a conservative Model Router MVP may be designed,
  still without adaptive policy activation;
- `RUNTIME_CAPABILITY_GAPS` — implement only the adapter/capability boundary
  required by a demonstrated live gap.

Generate a follow-up prompt from the observed state. Do not execute the
follow-up phase or merge any PR.
