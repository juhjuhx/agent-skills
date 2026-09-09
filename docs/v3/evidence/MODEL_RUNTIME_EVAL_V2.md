# Model / Runtime Evaluation V2 — bounded live benchmark

Phase 3C collected a deliberately small amount of live evidence. This remains
an evaluation harness, not a production model router. The Stage Router and its
weights were not changed.

## Evidence boundary

The unit of observation is an `ExecutionConfiguration`:

```text
runtime + model + effort + TaskSpec + StageRoute + skills + tools + permissions
```

Codex versus Claude is therefore a `CONFIGURATION_EFFECT` candidate, not a
model-effect experiment. No `MODEL_EFFECT` or reasoning-effort conclusion is
reported because no same-runtime controlled model/effort pair completed.

Evidence classes remain strict:

- `REAL_EXECUTION`: a verified live process produced a task result; eligible
  for task quality, reliability, and measured latency evidence.
- `HOST_MANAGED_FIXTURE`: static compatibility data only.
- `MOCK`: unit behavior only.
- `UNAVAILABLE`: a lane was not safely executable or produced no bounded result;
  it cannot support quality or ranking.

## Fresh runtime probes and provenance

Probe date: 2026-09-09 (Asia/Taipei). The version commands and help commands
were run locally. No executable was guessed or installed.

| Runtime | Observed version | Headless contract verified | Native controls observed | Phase 3C lane |
|---|---|---|---|---|
| Codex | `codex-cli 0.153.4` | `codex exec`; `--ephemeral`, `--sandbox`, `--cd`, `--json` | workspace sandbox, model flag, JSONL events | H01 completed once |
| Claude Code | `2.1.235 (Claude Code)` | `claude -p`; `--no-session-persistence`, `--output-format`, `--tools`, `--permission-mode`, `--max-budget-usd` | tool restriction, plan mode, effort/model flags, budget cap | H03 timed out; blocked |
| OpenCode | `1.18.25` | `opencode run --help` exposes `--format json`, `--pure`, `--dir`; safe least-privilege task invocation was not established | `--auto` is explicitly dangerous; no verified task-level deny surface was used | not activated; blocked by safety gate |
| Hermes | `Hermes Agent v0.20.0 (2026.8.3)` | `--oneshot` exists, but its help states approvals are auto-bypassed | model/reasoning/toolset flags exist, but no safe write boundary was verified | not activated; blocked by safety gate |
| MiMo Code | not observed | not probed; no verified executable | unknown | not run |
| ZCode | not observed | not probed; no verified executable | unknown | not run |
| DeepSeek Harness | not observed | not probed; no verified executable | unknown | not run |

First-party references used for runtime provenance: [Codex release
`rust-v0.153.4`](https://github.com/openai/codex/releases/tag/rust-v0.153.4),
[Codex docs](https://developers.openai.com/codex/), [Claude Code CLI
usage](https://docs.anthropic.com/en/docs/claude-code/cli-usage), [OpenCode
run/skills documentation](https://opencode.ai/docs/skills), and [Hermes
source](https://github.com/NousResearch/hermes-agent). The Codex release is
already bound to immutable source commit
`3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`; the other installed tools have no
resolved immutable release commit in this run and are not represented as such.
An initial Codex probe using `--approve-for-me` together with `--sandbox` was
rejected by the installed CLI's option contract; it was not counted as a live
cell. The successful H01 invocation used the compatible sandboxed form above.

## Workload cells

Only the requested initial holdout subset was considered. Acceptance criteria
and holdout labels were not changed, and no runtime/model identity was added.

| Holdout | Configuration | n | Result | Quality evidence |
|---|---|---:|---|---|
| H01 bounded bugfix | Codex 0.153.4, workspace-write sandbox, network-none TaskSpec | 1 | `VERIFIED_SUCCESS` | 2/2 isolated unittest cases passed; only `parser.py` changed |
| H03 API/interface design | Claude Code 2.1.235, tools disabled, plan mode, 0.10 budget cap | 1 | `BLOCKED` | no response before 60-second timeout; no quality evidence |
| H06 security-sensitive task | no live cell | 0 | not run | deferred until a trustworthy lane and cost bound are established |
| H07 deep source research | no live cell | 0 | not run | deferred because network/source correctness was not safely bounded |
| H09 release verification | no live cell | 0 | not run | deferred after the first lane-integrity pass |

`n=1` is `EXPLORATORY_ONLY`; it is not sufficient to derive a preference.
The append-only machine records are under
[`fixtures/v3/model-routing/runs/phase3c/`](../../../fixtures/v3/model-routing/runs/phase3c/).

## Terminal and stage evidence

Codex H01:

- `UNDERSTAND`: holdout, TaskSpec, route, and permission digests fixed.
- `IMPLEMENT`: `parser.py` preserved content after the first delimiter and
  raised `ValueError` for a missing delimiter.
- `VERIFY`: `python3 -B -m unittest discover -s . -p 'test_*.py'` passed 2/2.
- Terminal: `VERIFIED_SUCCESS`.

Claude H03:

- `DESIGN`: process launched with tools disabled and plan permission, but no
  bounded result arrived.
- Terminal: `BLOCKED`; output was empty and quality fields remain null.

## Efficiency and variance

The Codex H01 process reported 42,831.7 ms wall time, 145,919 input tokens,
1,725 output tokens, and unknown actual cost. Tool-call count and model ID were
not reliably exposed by the captured JSONL event summary. Its stdout/stderr are
represented only by digests and byte counts; raw output is not committed.

Claude H03 reached the 60,036.1 ms timeout with no output and no usable usage
metrics. There is no repeated cell, so no median-over-repetitions or variance
claim is made. The runner and record schema retain success count, latency range,
tool-call range, context range, reroutes, and failure modes for future n>1
cells.

## Configuration, model, and reasoning effects

- `CONFIGURATION_EFFECT`: no paired completed result exists. Codex and Claude
  changed runtime, model/provider, and runtime system behavior together; they
  must not be interpreted as a model comparison.
- `MODEL_EFFECT`: none. The Codex model was not exposed and no same-runtime
  model pair was run.
- `REASONING_EFFORT_EFFECT`: none. No effort variable pair was run.
- Confounders: model identity, provider cost, runtime skill injection, tool
  traces, and context composition were not all observable. These remain in the
  individual records rather than being silently normalized.

## Baselines and Pareto

The existing `BASELINE_STRONGEST`, `BASELINE_CHEAPEST`,
`BASELINE_DEFAULT`, and `BASELINE_HEURISTIC` helpers remain evaluation-only.
No live baseline cell was eligible and run in this bounded slice. The measured
Pareto frontier is therefore empty: one exploratory success cannot establish a
quality/cost/latency/reliability frontier, and unknown cost is never treated as
zero.

## Security and portability

- Coding work ran in a temporary isolated Git fixture; the repository HEAD
  remained the same and the uncommitted diff was captured by digest.
- The Codex TaskSpec requested workspace-write, network none, no secrets, no
  publish, and no delete. No permission violation or sandbox mismatch was
  observed; unexpected network usage was not independently observable and is
  recorded as unknown in the machine record.
- Claude used `--tools=` and plan mode; it timed out without a response.
- The runner invokes an explicit argv with `shell=False`, never serializes the
  inherited environment, and stores only output digests/metrics. Credential-like
  text is redacted in diagnostic helpers. No API key, OAuth token, auth header,
  prompt, raw output, or session credential is in the committed records.
- Portable artifacts are represented separately from runtime-specific JSONL
  event metadata. No RuntimeHandoff was executed.

## Verification and review

- Contract tests validate both checked-in live records against
  `LiveExecutionRecord`.
- Unit tests cover effect separation, effort isolation, exploratory n=1,
  variance, timeout/unavailable lanes, output sanitization, no credential
  serialization, unknown cost, and real-record boundaries.
- Independent review lanes: runtime/evaluation correctness, security boundary,
  simplification, and final verification. The selected `brooks-review` and
  `pr-review-toolkit` procedures were read; the brooks-lint-specific harness
  was not executed against this repository because its own trigger boundary
  excludes that use.
- Alibaba OpenCodeReview precheck: `ocr` 1.11.6; `ocr llm test` returned
  `401 Unauthorized`, so `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`; no delegate result
  is relabeled as native OCR.

## Decision gate

`INSUFFICIENT_LIVE_EVIDENCE`

The run produced the first trustworthy real task result, but not the minimum
for a routing decision: only one completed configuration, one task class with a
quality result, no repetition beyond n=1, no model/effort controlled pair, and
no live baseline comparison. H06/H07/H09 remain unrun holdout cells; their
absence is explicit rather than filled with mock evidence.
