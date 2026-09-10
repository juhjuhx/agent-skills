# Model / Runtime Evaluation V9 — Phase 3G Codex Live Recovery

本文件記錄 Phase 3G 的新鮮 transport gate 結果。Phase 3F 的六筆 blocked
records 保留不變；本文件不把 provider 問題轉寫成 LOW/MEDIUM 品質結論。

## Decision

```yaml
decision: CODEX_LIVE_TRANSPORT_BLOCKED
inherited_experiment_status: CODEX_CONTROLLED_EXPERIMENT_BLOCKED
blocker: PROVIDER_UNREACHABLE
blocker_class: provider_reachability
transient_status: UNKNOWN
smoke_0: NOT_RUN
benchmark_cells: NOT_RUN
```

```yaml
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
MODEL_EFFECT: NOT_ATTEMPTED
```

## Repo truth

| 欄位 | 值 |
|---|---|
| starting HEAD | `d3af66ce4d9423ae7174effb3a798a1e61ecc3d6` |
| branch | `bench/v3-codex-effort-recovery` |
| base | `bench/v3-codex-effort-evaluation` |
| Stage Router weights | unchanged |
| new runtime/adapters | none |

## Installed Codex provenance

Fresh local checks on 2026-09-11:

| 項目 | 結果 |
|---|---|
| installed version | `codex-cli 0.153.4` |
| release/tag | `rust-v0.153.4` |
| release source commit | `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` |
| install class | standalone macOS arm64 runtime |
| verified headless surfaces | `exec`, `--model`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--sandbox`, `--json`, `--config` |
| unsupported assumption kept out | `--ask-for-approval` |

The installed help and pinned release source remain authoritative. The release page
identifies `rust-v0.153.4` at `3d2ee51`; the pinned CLI source exposes the headless
flags above, while the release config schema contains `approval_policy` and
`model_reasoning_effort`:

- https://github.com/openai/codex/releases/tag/rust-v0.153.4
- https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/cli.rs
- https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/lib.rs
- https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/config.schema.json

## Provider preflight

唯一一次 fresh preflight 使用：

```text
codex doctor --json --summary
```

只將非機密摘要保留在本文件；raw JSON、私有路徑、auth material 沒有寫入
repository。

| 檢查 | 結果 |
|---|---|
| Codex version | `0.153.4` |
| auth category/status | ChatGPT auth / `CONFIGURED` |
| provider | `openai` |
| configured model | `gpt-5.6-luna`（非機密識別值） |
| provider reachability | `PROVIDER_UNREACHABLE` |
| direct signal | required ChatGPT inference endpoint DNS/HTTP connect failure |
| overall doctor status | `fail` |

這是 provider transport 的直接證據，不是 task-quality evidence。由於 provider
已明確不可達，依 Phase 3G gate 不執行 Smoke 0，也不執行 H01/H03；不進行
相同失敗的重試。

## Smoke 0

`NOT_RUN`。原因是 provider preflight 已先阻塞。因而沒有：

- usable Codex JSONL；
- runtime 接受 explicit model 的執行證據；
- effective backend model identity；
- completed `turn.completed.usage` event。

這避免將 `-m gpt-5.6-luna` 的 request 誤標為
`EFFECTIVE_MODEL_VERIFIED`。

## Requested model / effective model

| 欄位 | 狀態 |
|---|---|
| requested model | `gpt-5.6-luna` |
| requested model status | `UNKNOWN`（沒有通過 Smoke 0 的 runtime acceptance） |
| effective model | `UNKNOWN` |
| effective model evidence | `UNOBSERVED` |
| model effect | `NOT_ATTEMPTED` |

Preflight 能安全確認設定中的 provider/model identifier，但不能證明一次
`codex exec` inference 已接受或實際使用該 model。

## Experiment controls

既有 Phase 3F harness 未修改，控制設計保持：

- 每個 workload 一次生成 immutable TaskSpec、StageRoute、selected skills 與
  CompiledExecutionBundle；
- LOW/MEDIUM 唯一預定變數是 `model_reasoning_effort`；
- explicit model、permission、sandbox、MCP、tool boundary、instruction/context
  digest 需固定；
- `--ephemeral`、`--ignore-user-config`、`--ignore-rules`、
  `approval_policy="never"`、finite timeout、isolated fixture、`shell=False`、
  `stdin=DEVNULL`；
- 不使用 `--ask-for-approval`、dangerous bypass、interactive approval 或高 effort。

由於 Smoke 0 沒有啟動，這些是待恢復時沿用的控制，不是本次新的 live quality
觀察。

## H01 / H03

| workload | LOW | MEDIUM | status |
|---|---:|---:|---|
| H01 | 0 次新執行 | 0 次新執行 | transport gate blocked |
| H03 | 0 次新執行 | 0 次新執行 | transport gate blocked |

H01 的 Phase 3F 六-cell 嘗試仍是歷史 `UNAVAILABLE/BLOCKED` evidence，不能
被補算成 repetition。H09 本 Phase 不執行。

## Metrics and effect boundary

本 Phase 沒有 task execution，因此不新增 latency、token、model-call、tool-call
或 cost 數據。只有 preflight status 可觀察：

| 軸 | 結果 |
|---|---|
| quality | `UNKNOWN` / no claim |
| efficiency | no benchmark metric |
| reliability | provider transport blocked before task |
| security | no model subprocess invoked |
| effort effect | `INCONCLUSIVE` |
| Pareto | no live configurations to compare |

不能從本次結果推導：

- `LOW` 或 `MEDIUM` 較好；
- model quality；
- runtime quality；
- `CONFIGURATION_EFFECT`；
- `MODEL_EFFECT`。

## RoutingPolicyProposal

本 Phase 沒有產生 LOW/MEDIUM recommendation。既有 evidence-only helper 仍保持：

```yaml
status: PROPOSAL_ONLY
active_policy_mutated: false
stage_router_weights_mutated: false
recommendation: NONE — restore provider transport before the exact missing cells
```

## Security / integrity

- 沒有安裝、重新 authentication、切換 provider/model 或新增 credential。
- 沒有啟動 Smoke 0，因此沒有可能的 model/tool authority widening。
- `codex doctor` 僅檢查本機狀態；本 repository 只保存摘要，不保存 raw diagnostics、
  token、header、auth file 內容、環境值或私有路徑。
- 沒有新增 runtime adapter、manager/service hierarchy 或 Stage Router 例外。
- 失敗的 transport preflight 不被轉寫為模型品質失敗。

## Reviews

| lane | result |
|---|---|
| experiment integrity | blocked before live cells; no quality claim made |
| security/control variables | no benchmark subprocess; existing controls unchanged |
| simplification | docs-only recovery branch; no speculative abstraction |
| verification | full test suite and repository checks run after evidence update |
| OpenCodeReview | `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH` (single precheck, HTTP 401) |

## Final gate

```yaml
CODEX_LIVE_TRANSPORT_BLOCKED: true
cause: PROVIDER_UNREACHABLE
cause_evidence: codex doctor required ChatGPT inference endpoint DNS/HTTP connect failure
Smoke_0: NOT_RUN
H01_H03: NOT_RUN
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```
