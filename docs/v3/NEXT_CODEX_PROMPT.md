# Next Codex Prompt — Phase 3C.1 targeted live evidence collection

## Current state

Repository: `juhjuhx/agent-skills`

The current branch contains the bounded Phase 3C harness and the first live
records. Read these files before acting:

- `tools/v3/live_benchmark.py`
- `schemas/v3/live-execution-record.schema.json`
- `fixtures/v3/model-routing/evidence-v2.json`
- `fixtures/v3/model-routing/runs/phase3c/`
- `docs/v3/evidence/MODEL_RUNTIME_EVAL_V2.md`
- `docs/v3/evidence/PHASE3C_LIVE_BENCHMARK_DOGFOOD_ROUTE.md`

Current verdict: `INSUFFICIENT_LIVE_EVIDENCE`.

Observed evidence is one `REAL_EXECUTION` Codex H01 success at `n=1`, plus a
Claude H03 bounded timeout recorded as `UNAVAILABLE`. No model or reasoning
effect is established. Do not call Codex versus Claude a model comparison.

## Mission

Collect only the missing, safe repetitions and task classes needed to improve
the evidence floor. Do not build a router or change routing policy.

Do not modify Stage Router weights, the holdout acceptance criteria, the
canonical skill catalog, or runtime adapters. Do not install software,
credentials, models, MCP servers, or dependencies. Do not run a benchmark in a
user project; use isolated temporary fixtures only.

## Dogfood and controls

Use resident `using-superpowers`, the existing Stage Router, and selected skill
bodies only. Emit a StageRoute for every active development stage. Keep
`NO_SKILL_NEEDED` routes intact and do not let runtime/model choice alter skill
selection.

For every cell preserve the existing control variables:

```text
TaskSpec digest, fixture digest, START_SHA, StageRoute digest,
selected skill IDs/digests, permission envelope, runtime/version,
model/effort, tools, MCP state, instruction digests
```

Use `run_headless_command` with an explicit argv, `shell=False`, isolated cwd,
short timeout, and no environment serialization. Build a
`LiveExecutionRecord`; persist only digests, metrics, artifacts, and concise
evidence. Never persist prompts, raw stdout/stderr, tool payloads, session IDs,
credentials, auth headers, or skill bodies.

## Targeted cells

Run only these holdout workloads, without adding runtime/model labels:

1. Codex H01: two additional repetitions if the measured account budget and
   observed input-token volume are explicitly acceptable. The existing first
   success is `n=1`; the cell must remain exploratory until repetitions are
   complete.
2. Codex H03: one read-only API design execution using the same route/control
   recording. This adds a second task class, not a model comparison.
3. Codex H09: one read-only release-verification execution using a temporary
   fixture and explicit artifact checks. This adds a third task class only if
   the acceptance evidence is independently verified.
4. Claude H03: do not retry blindly. First determine why the verified `claude
   -p` invocation timed out despite tools being disabled, using help/config
   facts only. Retry at most once with a bounded budget and timeout if that
   diagnosis establishes a safe contract; otherwise retain `LIVE_LANE_BLOCKED`.
5. OpenCode and Hermes: do not activate until their installed-version
   permission boundary is demonstrably safe for the chosen task. Hermes
   `--oneshot` currently reports approval bypass and must not be used for
   write-capable work.

Do not run H06 security or H07 network/source research until the lane can
record permission and source provenance without unresolved integrity gaps.

## Comparison rules

- `n=1` is `EXPLORATORY_ONLY`; never derive a preference from it.
- Codex versus Claude is `CONFIGURATION_EFFECT` evidence only, and only when
  both actually complete comparable work.
- Emit `MODEL_EFFECT` only for same runtime, task, route, skills, tools,
  permissions, and effort with model as the only changed variable. If model ID
  is not exposed, the result is `INCONCLUSIVE`.
- Keep reasoning-effort changes separate from model changes.
- Run only actually available evaluation baselines. Unknown cost stays
  `UNKNOWN`; it is not zero.
- Only `REAL_EXECUTION` records may enter quality/reliability/Pareto analysis.

## Acceptance gate

Update `MODEL_RUNTIME_EVAL_V2.md` and append-only machine records. Report
success count, n, latency variance, tool/context metrics, cost status,
terminal/stage evidence, confounders, security, and blocked lanes. The next
state can become `ROUTING_EVIDENCE_READY` only if there are at least two
completed configurations, three materially distinct task classes, repetition
beyond n=1, no measurement-integrity blocker, and a meaningful live baseline
comparison. Otherwise keep `INSUFFICIENT_LIVE_EVIDENCE` and list the exact
remaining cell.

Do not implement Phase 4 or adaptive/per-call model routing.
