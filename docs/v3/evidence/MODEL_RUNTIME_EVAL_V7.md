# Model / Runtime Evaluation V7 — Hermes Runtime Qualification

Phase 3E 只做既有 Hermes runtime 的資格查核。它沒有修改 Stage Router、
沒有啟動 Phase 4，也沒有在資格閘門之前建立 Hermes adapter。

## Decision

**HERMES_RUNTIME_BLOCKED**

本機確實安裝 Hermes Agent `v0.20.0 (2026.8.3)`，但直接查得
`custom:agnes-ai: logged out`。因此 provider gate 未通過，沒有執行任何
model inference、Smoke A、Smoke B 或 H03。這是 provider/runtime 可用性證據，
不是 Hermes、模型或其他 runtime 的品質比較。

另外，Hermes 的主要 scripted `--oneshot/-z` 路徑在安裝版 help 與對應版本
source 中明確會自動繞過 approvals；這條路徑不符合本專案的 zero-ASK、
no-bypass benchmark contract。這個 contract 限制被保留為獨立的安全發現，
但本階段的最終分類依 provider gate 規則為 `HERMES_RUNTIME_BLOCKED`。

## Repo truth

| 欄位 | 值 |
|---|---|
| Starting HEAD | `2f476371f139b050536c485a2ed13adaa59052ae` |
| Base branch | `feat/v3-claude-readonly-adapter` |
| Working branch | `feat/v3-hermes-runtime-qualification` |
| Stage Router | unchanged |
| Adapter | `NOT_BUILT` |
| Model invocation | `NOT_PERFORMED` |
| Final decision | `HERMES_RUNTIME_BLOCKED` |
| Quality evidence | none |

本次 qualification-only 的 machine record 是
[`hermes-qualification-001.json`](../../../fixtures/v3/model-routing/qualification/hermes-qualification-001.json)。
它不是 `LiveExecutionRecord`，也不是 REAL_EXECUTION quality run；真正的 live
run directory 沒有新增假 run。

## Hermes installed version / provenance

Fresh local probes：

| 欄位 | 值 | 分類 |
|---|---|---|
| runtime_id | `hermes` | installed |
| observed version | `0.20.0` | installed |
| release label | `2026.8.3` | installed |
| release tag | `v2026.8.3` | official release |
| official tag commit | `3c27eb6234bf91b8ceee9e9071591b31e9b148cb` | source provenance |
| installed source HEAD | `48e2dcd7a0118834ca994f1285f047b313879a63` | installed source snapshot |
| upstream source revision | `9098f6777b93b7881216a9b7d8fb402899f62400` | installed update reference |
| install method | `git` | installed |
| install path class | `user_local` | exact private path not persisted |
| Python | `3.11.15` | installed |
| source relation | version label matches release label, source HEAD differs | not release-identical |
| contract target | `INSTALLED_SOURCE_SNAPSHOT` | fail-closed |

因此不能把本機 source 當作官方 tag 的 byte-identical build，也不能用
current main 代替它。使用的第一方資料包括官方
[v2026.8.3 release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.3)、
[同版本 CLI reference](https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.8.3/website/docs/reference/cli-commands.md)、
[同版本 one-shot source](https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.8.3/hermes_cli/oneshot.py)、
[同版本 security guide](https://raw.githubusercontent.com/NousResearch/hermes-agent/v2026.8.3/website/docs/user-guide/security.md)
與本機安裝 source 的直接檢查。

## Historical `--oneshot` claim

歷史上曾把 `--oneshot` 描述為「非互動但安全」。Phase 3E 重新核對後，
結論如下：

| 問題 | 證據 | 結論 |
|---|---|---|
| 是否 noninteractive | installed help、CLI reference | 是 |
| 是否只輸出 final response | installed help | 是，但不代表安全 |
| 是否自動 bypass approval | installed help、tagged `oneshot.py`、local source | 是 |
| 是否載入 tools/config/rules/AGENTS | help、source | 是 |
| 是否會接受 hooks | tagged/local source sets the per-call acceptance environment | 是 |
| `--yolo` 是否使用 | 本階段命令未使用 | 否 |

```yaml
ONESHOT_APPROVAL_SEMANTICS: BYPASS
HERMES_YOLO_MODE_FLAG_DIRECTLY_PASSED: false
HERMES_YOLO_MODE_INTERNAL_ON_ONESHOT: true
BENCHMARK_ELIGIBLE: false
```

這不是將 `--yolo` 當作 CLI flag 使用；而是指出 `--oneshot` 自己會建立
等價的 per-call bypass 狀態，所以不能用於本資格閘門。

## Noninteractive and isolation contract

| Surface | Support | Availability | Phase 3E interpretation |
|---|---|---|---|
| `hermes -z/--oneshot` | `NATIVE` | `INSTALLED` | `UNSAFE_BYPASS`; not used |
| `hermes chat -q/--query` | `NATIVE` | `INSTALLED` | noninteractive query surface observed |
| `--safe-mode` | `NATIVE` | `INSTALLED` | disables user config/rules, plugins, MCP and customization; may remove custom provider config |
| `--ignore-user-config` | `NATIVE` | `INSTALLED` | not sufficient to preserve the configured custom provider |
| `--ignore-rules` | `NATIVE` | `INSTALLED` | not a complete tool/approval boundary |
| `--toolsets` | `NATIVE` | `INSTALLED` | `context_engine` resolves zero tool schemas in local source; full authenticated path not proven |
| `--max-turns` | `NATIVE` | `INSTALLED` for `chat` | available but no model run was authorized |
| `--provider`, `--model` | `NATIVE` | `INSTALLED` | no automatic substitution or new provider setup |
| `--reasoning` | `NATIVE` | `INSTALLED` | not varied |
| `--usage-file` | `NATIVE` | `INSTALLED` for `-z` | not produced because no inference ran |
| no-session-persistence switch | `UNSUPPORTED` | `UNKNOWN` | no equivalent flag exposed; session persistence was not proven suppressible |
| `--accept-hooks` / `--yolo` | `NATIVE` | `INSTALLED` | dangerous surfaces; never used |

`context_engine` 的 source-level schema count 為 zero，是一項
`HOST_MANAGED_FIXTURE` 相容性觀察，不是已完成 live zero-tool proof。安全
authenticated invocation 還受到 provider 狀態與 config/auth 分離問題阻擋。

## Authentication and provider health

只保存非秘密的身份與狀態：

| 欄位 | 值 |
|---|---|
| auth category | `API_KEY` (category only) |
| provider_id | `agnes-ai` |
| provider status | `PROVIDER_BLOCKED` |
| auth status | `LOGGED_OUT` |
| configured model_id | `agnes-2.0-flash` |
| model status | `CONFIGURED_BUT_UNVERIFIED` |
| provider health | `PROVIDER_BLOCKED` |
| credential values read | `false` |
| credential values persisted | `false` |

`hermes status --all` 只用來取得 provider/model 的非秘密 metadata；
`hermes auth status agnes-ai` 回報 logged out。沒有執行 setup、login、update、
model wizard，也沒有自動改選另一個 provider/model。因此依 mission 的
provider health gate，這裡必須停止。

## Qualification order and smoke gates

```text
installed truth       PASS
approval review       PASS — oneshot is BYPASS
provider/auth gate    BLOCKED — custom:agnes-ai logged out
tool/read proof       NOT_REACHED
Smoke A                NOT_RUN
adapter                NOT_BUILT
Smoke B                NOT_ELIGIBLE
H03                    NOT_ELIGIBLE
```

Smoke A 沒有因為「取得一筆結果」而被強行執行。沒有 raw prompt、stdout、
stderr、session state 或 provider response 被寫入 evidence；也沒有任何
model-call、工具呼叫或 workspace mutation。

## Hermes adapter / skill delivery

**Hermes adapter：`NOT_BUILT`。** 依資格優先規則，provider block 發生在
adapter 實作之前。

**Skill delivery：`NOT_APPLICABLE`。** canonical `SKILL.md` 沒有搬移、複製或
匯入 Hermes native skill store。若未來資格通過，StageRoute 仍是 selected-only
authority；Hermes learned skills 只能成為 proposal/eval 輸入，不能升格成
canonical routing truth。

## Learning / persistence exposure

| 項目 | 結果 |
|---|---|
| persistent learning mutation | `NOT_RUN` |
| canonical metadata mutation | `false` |
| routing weight mutation | `false` |
| memory/rules injection proof | `NOT_QUALIFIED` |
| session persistence suppression | `NOT_PROVEN` |

一方面，safe-mode 能關閉部分 customization；另一方面，它會忽略 user config，
而現有 provider 是 custom provider。`chat -q` 也沒有被證實能關閉 session
persistence。這使得安全、authenticated、無 uncontrolled learning 的完整
執行路徑尚未成立。

## Usage and cost semantics

本階段沒有 inference，因此沒有 live usage record：

| Metric | Value | Semantics |
|---|---:|---|
| model calls | `null` | `UNKNOWN`; no process was used for inference |
| tool calls | `null` | `UNKNOWN` |
| tokens | `null` | `UNKNOWN` |
| cost | `null` | `UNKNOWN`; no `--usage-file` output |
| terminal quality | not measured | no Smoke/H03 |

不能把 CLI process launch 算成 model call，也不能把 public pricing 當成 actual
billing cost。

## Dogfood routing

所有實際啟用的 development stages 都重新產生 StageRoute，完整記錄在
[`PHASE3E_HERMES_QUALIFICATION_ROUTE.md`](PHASE3E_HERMES_QUALIFICATION_ROUTE.md)。
Router 只讀 `214` 筆 metadata；正常 ranking 載入 `0` 個 `SKILL.md` body。

已載入並遵循的技能程序：

- `using-superpowers`：resident task/session GATE，整個 session 載入一次；不在每個 stage 重載。
- `verification-before-completion`：RESEARCH/HANDOFF 的 VERIFY 程序。
- `addyosmani-source-driven-development`、`addyosmani-security-and-hardening`：source/security research 與 review 程序。

Router 在 VERIFY stage 選出 `cost-tracker`，但 repository 與已安裝 catalog 都找不到
可載入的同名 `SKILL.md`；body 沒有載入、程序沒有執行。這被記為
`ROUTING_DEFECT`，沒有在本分支修改權重或加例外。

## Security review

- `--yolo`、`--accept-hooks`、approval auto-bypass invocation：未使用；`--oneshot` 因內部 bypass 被排除。
- 沒有啟動 model、shell、MCP、plugin、browser 或 filesystem tool。
- 沒有修改 global Hermes configuration，也沒有 setup/login/update。
- 沒有讀取或保存 API key、OAuth token、auth header、環境內容或 session secret。
- 沒有保存 raw prompt、stdout、stderr、skill body 或 session state。
- 沒有建立 adapter、沒有改 canonical skills、routing metadata 或 policy。
- future execution 仍須維持 `shell=False`、`stdin=DEVNULL`、isolated cwd、finite timeout、zero-ASK；本階段未以未證實的 live process 假冒完成這些 gate。

## Review status

| Lane | 結果 |
|---|---|
| source / qualification | PASS for installed facts; provider gate explicitly blocked |
| security / hardening | PASS for no-bypass/no-secret actions; complete live contract unqualified |
| simplification | PASS; no Hermes adapter、manager、registry、service 或 framework added |
| verification | docs/record validation and repository tests pending final run |
| OCR native diff | `BLOCKED_BY_AUTH` — single precheck returned HTTP 401; no retry |

## Final decision and next proposal

```yaml
DECISION: HERMES_RUNTIME_BLOCKED
HERMES_ADAPTER: NOT_BUILT
SMOKE_A: NOT_RUN
SMOKE_B: NOT_ELIGIBLE
H03: NOT_ELIGIBLE
CONFIGURATION_EFFECT: NONE
MODEL_EFFECT: NONE
```

Hermes 是目前 second-runtime search 的最後候選；不再建立 3E.1/3E.2，也不
自動轉向 MiMo、ZCode 或 DeepSeek Harness。下一步只提議既有 Codex runtime
的 controlled model/reasoning experiment；詳見 [`NEXT_CODEX_PROMPT.md`](../NEXT_CODEX_PROMPT.md)。
