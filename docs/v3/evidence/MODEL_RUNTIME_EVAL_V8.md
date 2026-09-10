# Model / Runtime Evaluation V8 — Phase 3F Codex Controlled Effort

Phase 3F 只測量已驗證的 Codex runtime 內，固定一個 explicit model 後改變
reasoning effort 的可能影響。沒有執行第二個 model、第二個 runtime、adaptive
routing 或 Stage Router 權重修改。

## Decision

```yaml
DECISION: CODEX_CONTROLLED_EXPERIMENT_BLOCKED
INTRA_RUNTIME_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
MODEL_EFFECT: NOT_ATTEMPTED
REASONING_EFFORT_EFFECT: INCONCLUSIVE
```

Codex 在修正後的六個 bounded cells 都沒有產生 usable model output。`codex doctor
--json --summary` 同時直接回報 ChatGPT provider reachability 失敗；這是重要的
環境線索，但由於 live records 只保存 sanitized digests，無法把 run-level cause
提升成 provider-specific 定論。因此本 Phase 的保守分類是 `RUNTIME_UNKNOWN`
（provider reachability failure 為 corroborating evidence），不是 LOW/MEDIUM、
model 或 Codex 品質失敗。

## Repo truth

| 欄位 | 值 |
|---|---|
| starting HEAD | `a414ff88adbd112e97e4fcc69ca8cf0c4f7399c6` |
| final branch | `bench/v3-codex-effort-evaluation` |
| base branch | `feat/v3-hermes-runtime-qualification` |
| Stage Router | unchanged |
| new runtime adapter | none |
| live invocation budget | maximum 6; all six scheduled cells attempted, no usable observation |

## Installed Codex provenance

Fresh local checks established:

| item | observed value |
|---|---|
| executable version | `codex-cli 0.153.4` |
| release/tag | `rust-v0.153.4` |
| release commit | `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` |
| local path class | user-local executable; private path not persisted |
| checked surfaces | `codex exec --help`, `codex doctor --json --summary` |
| model | `gpt-5.6-luna` requested explicitly; provider `openai` was visible as non-secret status |
| auth material | configured, values neither read into evidence nor persisted |

First-party references: [Codex rust-v0.153.4 release](https://github.com/openai/codex/releases/tag/rust-v0.153.4),
[Codex CLI reference](https://developers.openai.com/codex/cli/reference),
[pinned CLI source](https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/cli.rs),
[pinned exec source](https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/lib.rs)，
與 [pinned config schema](https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/config.schema.json)。
Installed help/source 是本次 invocation contract 的優先證據，沒有用 current-main
欄位冒充 installed support。

特別注意：installed `codex exec --help` 與 release `exec/src/cli.rs` 沒有
`--ask-for-approval` flag；release `exec/src/lib.rs` 對 headless exec 設定
`approval_policy = Never`。因此 runner 使用已證實可解析的
`--config approval_policy="never"`，沒有保留不存在的 CLI flag。

## Pinned model and effort levels

| item | value | evidence status |
|---|---|---|
| requested model ID | `gpt-5.6-luna` | `CLI_CONFIRMED` request; non-secret local config/doctor identity |
| effective model ID | unknown | no completed JSONL event |
| pin status for quality evidence | `UNVERIFIED` | no provider result; not eligible for effect conclusion |
| lower effort | `low` | accepted by checked-in Codex profile/command contract |
| higher effort | `medium` | accepted by checked-in Codex profile/command contract |
| high / xhigh | not attempted | explicitly out of initial budget |

The experiment command would change only:
`-c model_reasoning_effort="low|medium"`. No model-effect comparison was run.
`CLI_CONFIRMED` here means the explicit request was constructed/accepted by the
local command contract; it does not mean a server response confirmed effective model
identity.

## Experiment controls

For each workload the route and bundle were compiled once and intended for reuse:

- TaskSpec digest, fixture digest and start SHA;
- StageRoute identity/digest and selected skill IDs/digests;
- permission envelope, sandbox, approval policy, tool/MCP availability;
- project/system instruction digests;
- Codex version, explicit model and effort;
- fresh ephemeral fixture, no session resume, finite timeout.

H01’s attempted record used:

```yaml
task_spec_digest: sha256:f8dcba3ce56461173e3b02eba92a0518be765e1e0a63a52b5487df62e9a05c48
fixture_digest: sha256:3765dfa4870081ce23c74ab8ae07b00b834e26664ca5c1fff80ac9ac6c7df0bd
permission_envelope_digest: sha256:a09a39d930ed2dcf4fcd330b38566fe1cd1bf64701e343fc9688ace5e1729866
selected_skills: [tdd, using-superpowers, verification-before-completion]
sandbox: workspace-write
approval: never
mcp: NOT_USED
```

Route timing observations are excluded from the stable route digest. This correction
was made before any paired comparison; no blocked cell is used as an effort pair.

## Schedule and live result

Target schedule:

| sequence | workload | effort | repetition | result |
|---:|---|---|---:|---|
| 1 | H01 | LOW | 1 | `BLOCKED`, no usable output |
| 2 | H01 | MEDIUM | 1 | `BLOCKED`, no usable output |
| 3 | H01 | MEDIUM | 2 | `BLOCKED`, no usable output |
| 4 | H01 | LOW | 2 | `BLOCKED`, no usable output |
| 5 | H03 | LOW | 1 | `BLOCKED`, no usable output |
| 6 | H03 | MEDIUM | 1 | `BLOCKED`, no usable output |

Append-only sanitized records:
[`live-codex-effort-h01-low-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h01-low-001.json)、
[`live-codex-effort-h01-medium-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h01-medium-001.json)、
[`live-codex-effort-h01-medium-002.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h01-medium-002.json)、
[`live-codex-effort-h01-low-002.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h01-low-002.json)、
[`live-codex-effort-h03-low-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h03-low-001.json)、
[`live-codex-effort-h03-medium-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-codex-effort-h03-medium-001.json)。

Observed record:

| field | value |
|---|---|
| evidence class | `UNAVAILABLE` for all six |
| status | `LIVE_LANE_BLOCKED` for all six |
| terminal outcome | `BLOCKED` for all six |
| process stdout | 0 bytes for all six; raw output not persisted |
| process stderr | 199 bytes for all six; digest only |
| host wall time | 22.18–94.90 ms, `PER_RUN`, verified |
| changed files | none |
| model/tool calls | `null`, `UNKNOWN` |
| input/output/total tokens | `null`, `UNKNOWN` |
| cost | `null`, `UNKNOWN` |

Two earlier parser-level probes used the pre-conformance unsupported approval flag and
are excluded from benchmark evidence. The corrected contract then attempted exactly
the six scheduled cells; none reached a completed model event. H01 has two attempts
per effort but zero usable repetitions, H03 has one attempt per effort, and H09 was not
run.

## Provider blocker

Direct local diagnostic evidence from `codex doctor --json --summary` showed the
configured ChatGPT provider could not reach its endpoint in this environment. The six
corrected bounded runner cells produced no usable JSONL result. Because the public
record does not retain raw stderr, the run-level cause remains conservative:

```yaml
cause: RUNTIME_UNKNOWN
corroborating_signal: provider reachability failure from codex doctor
quality_claim: NONE
model_quality_claim: NONE
effort_quality_claim: NONE
```

The cause is not classified as model unavailable, effort unsupported, timeout quality
failure, or authentication failure because those were not directly established.

## Metric semantics

For Codex `0.153.4`, only a completed `turn.completed.usage` event may establish the
release-specific cumulative usage interpretation used by the existing measurement
policy. Since none of the six cells had such an event:

| metric | value | status |
|---|---:|---|
| `latency_ms` / `wall_time_ms` | 22.18–94.90 | observed host `PER_RUN` |
| `input_tokens` | null | `UNKNOWN`, no usage event |
| `output_tokens` | null | `UNKNOWN`, no usage event |
| `tokens_total` | null | `UNKNOWN`, no usage event |
| `model_calls` | null | `UNKNOWN`; process launch is not a call |
| `tool_calls` | null | `UNKNOWN` |
| billing cost | null | `UNKNOWN` |

No historical unpinned run is eligible for the controlled pair. No token total is
claimed from the previously observed single numeric value.

## Quality, variance and effects

There are zero completed REAL_EXECUTION quality observations in this phase:

| workload | LOW | MEDIUM | effect classification |
|---|---|---|---|
| H01 | 0 usable / 2 attempted | 0 usable / 2 attempted | `INCONCLUSIVE` because no runtime output |
| H03 | 0 usable / 1 attempted | 0 usable / 1 attempted | `INCONCLUSIVE` |

Thus there is no success rate, acceptance comparison, test comparison, artifact
variance, latency variance, token variance, or terminal-quality comparison between
effort arms. `HIGHER_EFFORT_MATERIALLY_BETTER`, `LOWER_EFFORT_EQUIVALENT`,
`LOWER_EFFORT_BETTER`, and `TRADEOFF` are all unsupported by this run.

`MODEL_EFFECT: NOT_ATTEMPTED`. A Codex-vs-other-runtime comparison is historical
configuration context only and is not part of this effect calculation.

## Non-production RoutingPolicyProposal

The code contains an evidence-only proposal helper. It deep-copies the active policy,
does not mutate routing configuration, and has no call site that activates a policy.
Because no effort result exists, this phase produces no substantive LOW/MEDIUM
recommendation:

```yaml
status: PROPOSAL_ONLY
active_policy_mutated: false
recommendation: NONE — collect the missing controlled cells after provider recovery
```

## Readiness split

| dimension | result | reason |
|---|---|---|
| intra-runtime routing | `NOT_READY` | no paired H01 repetitions and no paired H03 observations |
| cross-runtime routing | `NOT_READY` | OpenCode provider-blocked, Claude timeout-blocked, Hermes provider/contract-blocked |

This keeps Codex-local effort work conceptually independent from cross-runtime work,
but neither readiness gate is promoted without evidence.

## Dogfood and routing defects

All active development stages emitted StageRoutes; the detailed trace is in
[`PHASE3F_CODEX_EFFORT_ROUTE.md`](PHASE3F_CODEX_EFFORT_ROUTE.md)。Current router
defects observed during dogfood include `maps` in implementation and `brandkit` /
`permission-tuner` in review. They were not repaired in this branch, and they did not
become effort-specific variables.

## Security review

- No approval bypass or dangerous sandbox flag was used.
- Commands were explicit, `shell=False`, `stdin=DEVNULL`, isolated, ephemeral and finite.
- Model/effort settings did not grant filesystem, network, MCP, external-path,
  publish or delete authority.
- No raw prompt, stdout, stderr, skill body, environment value, credential, token or
  auth header was persisted.
- The temporary fixture remained unchanged; no unrelated repository was touched.
- Blocked evidence cannot enter quality/Pareto conclusions.

## Reviews

| lane | result |
|---|---|
| experiment integrity | PASS after correcting fail-closed empty-output classification; no pair formed |
| quality evidence | PASS for refusing self-report/blocked quality claims |
| security/control equality | PASS for static boundary; no live pair to compare |
| simplification | PASS; no manager/registry/service/router or adapter hierarchy added |
| verification | PASS: 269 repository tests; six LiveExecutionRecords; diff, links and scans clean |
| OCR native diff | `BLOCKED_BY_AUTH` if the single precheck remains HTTP 401 |

## Phase conclusion

This phase establishes the measurement harness and six sanitized runtime-blocked
records, but not a reasoning-effort effect. The only valid next step is a targeted
recovery of the already-authorized Codex provider transport followed by the exact
missing cells; see
[`NEXT_CODEX_PROMPT.md`](../NEXT_CODEX_PROMPT.md)。不要開始 Phase 4，也不要進行
model-effect 或另一個 runtime 的追逐。
