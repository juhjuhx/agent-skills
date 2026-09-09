# Model / Runtime Evaluation V1

Phase 3B is an evaluation harness, not a model-routing policy. It records
eligibility, reproducible execution configurations, evidence classes,
baselines, terminal outcomes, and multi-axis comparison without changing the
Stage Router or selecting a production model.

## Evaluation boundary

```text
Task / session       -> runtime / harness candidate
Eligible runtime     -> task, stage, or subagent model candidate
Individual call      -> design-only; not implemented
```

Changing `Codex` to `Claude Code` is an explicit `RuntimeHandoff`, not a hidden
StageRoute mutation. A model profile describes inference capability only. It
cannot grant filesystem, network, MCP, publish, delete, or sandbox authority.

## Source truth and candidates

The registry epoch for the Stage Router dogfood run is
`registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac`; the v3 catalog contains
214 canonical skill metadata records. Runtime and model candidate records are
validated against the new v3 schemas and keep support separate from
availability.

Runtime source evidence used in the fixture set:

- [Codex release `rust-v0.153.4`](https://github.com/openai/codex/releases/tag/rust-v0.153.4)
  and [Codex source](https://github.com/openai/codex).
- [Claude Code CLI documentation](https://docs.anthropic.com/en/docs/claude-code/cli-usage).
- [OpenCode Skills](https://opencode.ai/docs/skills), [Agents](https://opencode.ai/docs/agents/),
  and [Permissions](https://opencode.ai/v2/docs/permissions).
- [Hermes Agent source](https://github.com/NousResearch/hermes-agent).

Local probes found four installed executables: Codex `0.153.4`, Claude Code
`2.1.235`, OpenCode `1.18.25`, and Hermes `v0.20.0`. MiMo Code, ZCode, and
DeepSeek Harness have no verified executable discovery record. The static
runtime/model fixtures therefore establish compatibility only.

## Development and holdout data

The existing ten Stage Router workloads A–J are **DEVELOPMENT / REGRESSION**
fixtures. They are not unseen model-routing data and contain no expected
runtime/model identity labels.

The independent **HOLDOUT** set contains 12 explicit-acceptance workloads:

| IDs | Workloads |
|---|---|
| H01–H02 | bugfix; multi-file feature |
| H03–H04 | API design; architecture decision |
| H05–H06 | frontend; security |
| H07–H08 | deep source research; repository audit |
| H09–H10 | release verification; documentation |
| H11–H12 | visual design; tool/MCP integration |

No holdout fixture declares an expected runtime or model. Holdout data is not
used to tune weights. See [`development/index.json`](../../../fixtures/v3/model-routing/development/index.json)
and [`holdout/index.json`](../../../fixtures/v3/model-routing/holdout/index.json).

## Baselines

The harness implements deterministic, evaluation-only baselines:

| Baseline | Rule | Production policy? |
|---|---|---|
| `BASELINE_STRONGEST` | largest declared capability breadth among eligible candidates | No |
| `BASELINE_CHEAPEST` | lowest declared cost class/measurement | No |
| `BASELINE_DEFAULT` | caller-supplied configured default, if eligible | No |
| `BASELINE_HEURISTIC` | simple→cheapest, complex→broadest, standard→stable ID order | No |

These are compatibility baselines, not a claim that breadth predicts
agentic quality. A later router must beat or justify itself against these
baselines on held-out real evidence.

## Evidence status

| Evidence class | Count/status | What it can support |
|---|---:|---|
| `REAL_EXECUTION` | `n=0` task/model quality runs | quality, efficiency, reliability, security, portability when captured |
| `HOST_MANAGED_FIXTURE` | checked-in candidate/fixture validation | schema and compatibility conclusions only |
| `MOCK` | unit-test synthetic results | helper behavior only; excluded from quality ranking |
| unavailable runtime probes | 3 runtimes unresolved | availability gap, not quality |

The four local version probes are real compatibility evidence but are not
task/model executions. No provider endpoint, new runtime adapter, MCP server,
or model was installed or invoked by this phase. Consequently there are no
live terminal outcomes to compare and no stage-quality conclusions.

## Measurement contract

Every future `EvaluationRun` records fixture set, runtime/model references,
evidence class, execution mode, repetition, stage route references, and
append-only history. `EvaluationResult` keeps these axes independent:

- **Quality:** acceptance coverage, tests, artifact correctness, review
  findings, source accuracy, user correction.
- **Efficiency:** latency, wall time, calls, context/tokens, cost.
- **Reliability:** reroutes, failed calls, retries, invalid edits, recovery.
- **Security:** permission violations, unsafe proposals, secret exposure,
  sandbox mismatch.
- **Portability:** handoff artifact completeness, runtime leakage, lost
  capabilities.

Multi-stage tasks also require a terminal outcome: `VERIFIED_SUCCESS`,
`PARTIAL`, `FAILED`, or `BLOCKED`. A stage impression cannot replace the
terminal result.

## Pareto comparison

The helper returns a frontier over measured real results without collapsing
quality, cost, latency, and recovery into one score. The current unit tests use
synthetic `REAL_EXECUTION`-labeled records to prove the comparison contract;
that is not runtime/model performance evidence. With no live results, the
current empirical frontier is empty.

## Research lessons retained

The harness records only actionable design lessons from current research:

- [LLMRouterBench](https://arxiv.org/abs/2601.07206) and its
  [official repository](https://github.com/ynulihao/LLMRouterBench) motivate
  strong fixed baselines, latency-aware measurements, and recall/coverage
  diagnostics before claiming router gains.
- [Task- and Session-Level Model Routing](https://arxiv.org/abs/2608.14641)
  motivates separating task/session outcomes from stage impressions and
  reporting fixed-tier composition.
- [TwinRouterBench](https://arxiv.org/abs/2605.18859) and its
  [official repository](https://github.com/CommonstackAI/TwinRouterBench)
  motivate execution-verified labels and separate static/live tracks.
- [RouteLLM](https://arxiv.org/abs/2406.18665) and
  [FrugalGPT](https://arxiv.org/abs/2305.05176) motivate cost/quality
  comparisons, but not blind adoption of learned thresholds with this sample
  size.

No bandit, classifier, LLM judge, adaptive weight, or learned preference is
implemented. History can create a proposal-only record and cannot rewrite
`.superpowers/ROUTING_POLICY.yaml`.

## Review status

- Deterministic contract/code review: PASS; runtime and model identities are
  separate, and configuration construction rejects adapter/runtime mismatch.
- Security review: PASS for the Phase 3B boundary. Model records, MCP/plugin
  declarations, and candidate capability maps do not grant authority; the
  effective permission remains the existing intersection. Credentials are not
  serialized. The available security-patterns/manual lane was used because the
  exact `security-and-hardening` catalog entry was not installed in the local
  skill set.
- Simplification review: PASS; the implementation uses schemas and pure
  helpers only—no database, registry service, scheduler, or provider registry.
- Verification: PASS, 162 tests and `git diff --check`.
- Alibaba OpenCodeReview: `ocr` version `1.11.6`; the one `ocr llm test`
  precheck returned `401 Unauthorized`, so
  `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`. No native diff review is claimed and no
  delegate result is relabeled as native OCR.

## Current verdict

`INSUFFICIENT_LIVE_EVIDENCE`

The contracts, baselines, holdout separation, and comparison mechanics are
ready for bounded benchmark lanes. The repository does not yet have enough
real task executions to decide which runtime or model should own a workload.
