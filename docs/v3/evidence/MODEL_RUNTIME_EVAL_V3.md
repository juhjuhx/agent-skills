# Model / Runtime Evaluation V3 — measurement integrity and targeted live evidence

Phase 3C.1 is a bounded evidence correction and live-evidence collection
pass. It does not implement model routing, adaptive routing, Stage Router
weight changes, or additional runtime adapters.

## Decision

**`RUNTIME_CAPABILITY_GAPS`**

The measurement-integrity issue is resolved for the Codex fields that have a
verified release interpretation. Codex now has repeated H01 evidence and two
additional task classes, but only one runtime-backed execution configuration
completed. Claude Code and OpenCode could not produce a trustworthy second
quality configuration under their verified safety boundaries. This is a
runtime/adapter boundary gap, not evidence that either runtime or its model is
inferior.

The decision is not `ROUTING_EVIDENCE_READY`: the second completed
configuration requirement remains unmet, and no isolated model or reasoning
effect was measured.

## Scope and evidence classes

The observation unit remains:

```text
runtime + model + effort + TaskSpec + StageRoute + skills + tools + permissions
```

`REAL_EXECUTION` can support task-quality, reliability, and live-latency
observations. `UNAVAILABLE` records preserve compatibility/safety attempts but
cannot enter quality or Pareto conclusions. No `MOCK` record is promoted to
live evidence.

The development work itself was routed through the existing Stage Router;
the exact stage trace is in
[`PHASE3C1_DOGFOOD_ROUTE.md`](PHASE3C1_DOGFOOD_ROUTE.md). The resident
`using-superpowers` authority was not reloaded as an ordinary skill body at
every stage, and runtime/model choice did not change Stage Router selection.

## Measurement-integrity findings

The previous interpretation made two unsafe assumptions:

1. The last observed `input_tokens`/`output_tokens` value was a generic total.
2. A launched agent process represented one model call.

Both assumptions are removed. Every efficiency metric now carries a compact
provenance record: runtime, runtime version, source field, value, unit,
aggregation semantics, source, confidence, and status. A process launch alone
does not set `model_calls` to one; the value is `null` with `UNKNOWN` semantics
when the runtime does not expose a count.

The historical H01 value `145919` remains in its append-only record, but it is
now classified as the Codex release's cumulative session usage field rather
than an unqualified `TOTAL_INPUT_TOKENS` claim. The record's overall
`measurement_status` remains `PARTIAL` because model-call count, tool-call
count, and actual cost were not exposed.

### Codex token interpretation

The installed runtime is `codex-cli 0.153.4`. Its release source stores the
latest total token notification and uses that total when emitting
`turn.completed` JSONL usage. The protocol shape contains both `last` and
`total`, while the captured exec event exposes the total-derived usage. The
first-party source and issue evidence therefore support:

| Observed field | Interpretation | Status |
|---|---|---|
| `turn.completed.usage.input_tokens` | `CUMULATIVE_TOTAL` for the execution/session | `VERIFIED` for the pinned release |
| `turn.completed.usage.output_tokens` | `CUMULATIVE_TOTAL` for the execution/session | `VERIFIED` for the pinned release |
| `turn.completed.usage.total_tokens` | total usage associated with the emitted event | `VERIFIED` for the pinned release |
| generic `usage.*` without verified runtime identity | aggregation unknown | `UNKNOWN` |
| model-call count | not exposed by captured JSONL | `UNKNOWN` |
| tool-call count | not exposed as a trustworthy total | `UNKNOWN` |
| actual cost | not exposed | `UNKNOWN` |

Evidence: [Codex `rust-v0.153.4` release](https://github.com/openai/codex/releases/tag/rust-v0.153.4),
[release event processor](https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/event_processor_with_jsonl_output.rs),
[release protocol schema](https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server-protocol/schema/json/v2/ThreadTokenUsageUpdatedNotification.json),
and first-party discussions of [cumulative total usage](https://github.com/openai/codex/issues/22354)
and [exec JSONL usage semantics](https://github.com/openai/codex/issues/17539).

## Live runtime lanes

Fresh local version/help probes were performed on 2026-09-09. No runtime,
model, MCP server, dependency, account, or credential was installed.

| Runtime | Observed version | Lane result | Evidence boundary |
|---|---|---|---|
| Codex | `codex-cli 0.153.4` | `REAL_EXECUTION` | `codex exec --ephemeral --sandbox ... --json`; adapter implemented; release tag resolves to `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` |
| Claude Code | `2.1.235 (Claude Code)` | `LIVE_LANE_BLOCKED` | bounded `claude -p` smoke timed out with no output; no H03 retry was run |
| OpenCode | `1.18.25` | `LIVE_LANE_BLOCKED` | explicit deny-by-default read-only config was attempted, but the bounded run produced no usable response; adapter remains guide-only |
| Hermes | `Hermes Agent v0.20.0 (2026.8.3)` | `LIVE_LANE_BLOCKED` | `--oneshot` help states approvals are auto-bypassed; no write benchmark was attempted |
| MiMo Code | `mimo 0.1.0`; `mimocode 0.36.4` | `LIVE_LANE_BLOCKED` | executables were observed, but no safe deny-by-default headless execution boundary was verified |
| ZCode | not observed | unavailable | no verified executable |
| DeepSeek Harness | not observed | unavailable | no verified executable |

Installed-version evidence wins over current-main documentation. Claude's
installed help did not expose every option shown in current documentation, so
the probe used only options verified locally. The relevant first-party
references are the [Claude CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage),
[OpenCode permissions](https://opencode.ai/docs/permissions/),
[OpenCode agents](https://opencode.ai/docs/agents), and
[OpenCode skills](https://opencode.ai/docs/skills).

## Codex H01 repetitions

The controlled successful H01 cell reached three real executions. Each record
is individually `n=1` and `EXPLORATORY_ONLY`; the table is the cell aggregate,
not a claim of statistical superiority. The historical temporary fixture was
not retained, so two later runs reconstructed the semantic acceptance criteria
and explicitly record a fixture/start-SHA confounder.

| Run | Terminal outcome | Latency | Cumulative input | Cumulative output | Tests |
|---|---|---:|---:|---:|---|
| `live-codex-h01-001` | `VERIFIED_SUCCESS` | 42,831.7 ms | 145,919 | 1,725 | 2/2 passed |
| `live-codex-h01-002` | `VERIFIED_SUCCESS` | 76,529.4 ms | 202,896 | 3,562 | 2/2 passed |
| `live-codex-h01-003` | `VERIFIED_SUCCESS` | 63,032.5 ms | 200,476 | 2,572 | 2/2 passed |

Aggregate: **3/3 verified success**; latency median **63,032.5 ms**, range
**42,831.7–76,529.4 ms**. The input/output columns are per-run cumulative
observations and must not be summed as per-call usage. `model_calls`,
`tool_calls`, and cost remain `UNKNOWN`.

The preliminary `live-codex-h01-000` default-sandbox attempt is retained as a
blocked append-only record and excluded from the successful H01 cell.

## Codex H03

`live-codex-h03-001` completed as `VERIFIED_SUCCESS` in **32,734.3 ms** using
Codex read-only execution. The local API/interface design acceptance artifact
was complete and source-accuracy checks passed against the bounded fixture
constraints. This is exploratory `n=1` evidence; the reconstructed fixture
and absence of external production API research remain confounders.

## Codex H09

`live-codex-h09-001` completed as `PARTIAL` in **132,205.7 ms**. Independent
tests passed and no release input was mutated or published, but the required
handoff artifact was incomplete. This is a real terminal outcome, not a hidden
success; it supplies a third task class without being a verified-success
claim.

## Claude smoke probe and H03

The diagnostic command was bounded, noninteractive, tools-disabled, plan-mode,
no-session-persistence, JSON output, and a small budget cap. It launched but
timed out after **60,021.3 ms** with no stdout or stderr. The evidence permits
classification as:

```text
LIVE_LANE_BLOCKED
failure_class = TIMEOUT
cause = UNKNOWN
```

The timeout cause was not inferred. It may not be relabeled as AUTH,
startup, model availability, or runtime quality failure. Since the smoke
contract did not produce a response, no Claude H03 quality retry was run.
The historical Claude H03 blocked record remains separate and is not counted
as a completed configuration.

## OpenCode safety contract and H03

Installed SDK types and first-party permissions documentation support an
allow/ask/deny permission model. A temporary configuration attempted:

```text
deny by default
allow read/list/glob/grep only inside the isolated fixture
deny edit, bash, task, external directories, web, LSP, question, and secrets
deny plugins; selected skill permissions were explicit
```

The `opencode run --pure --dir <isolated-fixture> --format json --agent plan`
attempt left the workspace unchanged but exited without a usable bounded
response or design artifact. It is recorded as `LIVE_LANE_BLOCKED` with no
quality values. The attempt demonstrates a safety configuration, not a
completed OpenCode execution configuration. `--auto` was not used.

## Other blocked lanes

- **Hermes:** no write-capable benchmark because the installed `--oneshot`
  contract auto-bypasses approvals. A future read-only lane requires a
  separately verified invocation.
- **MiMo Code:** local executables were observed, but `mimo run` exposed only a
  dangerous permission bypass rather than a verified deny-by-default boundary;
  `mimocode chat` is interactive. No quality run was attempted.
- **ZCode / DeepSeek Harness:** no executable was verified.

These are exact blockers for the current evidence run; none justify weakening
permissions or fabricating a result.

## Terminal and stage outcomes

| Cell | Terminal outcome | Stage evidence |
|---|---|---|
| Codex H01, three runs | `VERIFIED_SUCCESS` (3/3) | understand, implement, and verify passed; isolated parser tests passed |
| Codex H03 | `VERIFIED_SUCCESS` | understand, research, design, and read-only review passed |
| Codex H09 | `PARTIAL` | review and verify passed; handoff incomplete |
| Claude smoke | `BLOCKED` | compatibility-only probe timed out before output |
| OpenCode H03 | `BLOCKED` | explicit deny controls preserved the workspace; no response artifact |

Completed task-class count is **3**: `bugfix`, `api/interface design`, and
`release verification`. Completed runtime-backed configuration count is **1**:
Codex 0.153.4. Repeating or changing the workload inside Codex does not create
a second runtime/model configuration.

## Effects and baselines

### Configuration effect

No completed cross-runtime pair exists. The OpenCode record retains
`CONFIGURATION_EFFECT` as the prospective comparison class, but its
`UNAVAILABLE` evidence class makes it ineligible for a quality comparison.
Codex versus Claude/OpenCode must not be described as a model comparison.

### Model effect

None. The captured Codex events did not expose a model identifier and no
same-runtime alternate-model pair was available and controlled.

### Reasoning-effort effect

None. No bounded effort comparison was run.

### Baseline and Pareto status

The existing `BASELINE_STRONGEST`, `BASELINE_CHEAPEST`, `BASELINE_DEFAULT`, and
`BASELINE_HEURISTIC` helpers remain evaluation-only. No eligible live baseline
cell was available, so no live baseline relationship or meaningful Pareto
frontier was established. Unknown cost is not treated as zero. A single
Codex-backed configuration family cannot support a routing preference.

## Variance and efficiency

The H01 cell records success count and latency variance explicitly:

```text
n = 3
success_count = 3
success_rate = 1.0
latency median = 63,032.5 ms
latency min/max = 42,831.7 / 76,529.4 ms
input/output = verified cumulative per-run observations only
model_calls = UNKNOWN
tool_calls = UNKNOWN
cost = UNKNOWN
```

H03 and H09 remain `n=1`, `EXPLORATORY_ONLY`. Their input/output values are
also verified cumulative Codex observations, while call counts and cost are
unknown. The run records retain byte counts and digests rather than raw output.

## Security and measurement review

Independent review checked:

- `run_headless_command` uses an explicit argv with `shell=False`, isolated
  cwd, bounded timeout, and `DEVNULL` stdin when no input is supplied;
- prompts, stdout/stderr, environment values, credentials, and session values
  are not serialized; records keep only digests, byte counts, and sanitized
  metadata;
- successful Codex work was isolated and had no observed permission violation;
  H09 performed no publish/deploy action;
- the OpenCode attempt used deny-by-default controls and left its workspace
  unchanged; it did not use `--auto`;
- metric provenance prevents a token field or process launch from becoming a
  false total/call claim;
- unavailable or timeout lanes cannot carry quality evidence into comparisons.

The simplification review found no database, manager hierarchy, telemetry
service, adaptive router, or new adapter implementation. The change remains
small data/provenance helpers, validation, tests, append-only records, and
evidence documentation.

## Append-only records

Machine records are under
[`fixtures/v3/model-routing/runs/phase3c/`](../../../fixtures/v3/model-routing/runs/phase3c/).
Historical V2 evidence was not overwritten. New records include:

- two additional Codex H01 repetitions;
- Codex H03 and H09 cells;
- preliminary blocked Codex H01 attempt;
- Claude smoke result;
- OpenCode read-only safety attempt.

No raw process output, prompt, skill body, API key, OAuth token, auth header,
or session credential is committed.

## OCR

The one permitted precheck found `open-code-review v1.11.6`; `ocr llm test`
returned HTTP **401 Unauthorized**. Therefore:

```text
OCR_NATIVE_DIFF = BLOCKED_BY_AUTH
```

No repeated auth attempt was made and no delegate result was relabeled as
native OCR.

## Next-state rationale

The next task must address only the demonstrated missing boundary: a
benchmark-safe, native OpenCode read-only adapter/projection that consumes a
validated StageRoute, preserves selected-only skill loading and permission
intersection, and emits a usable bounded result. It must not implement Phase 4
or broaden into other adapters. The proposed prompt is in
[`NEXT_CODEX_PROMPT.md`](../NEXT_CODEX_PROMPT.md).
