# Phase 3F Codex Effort Evaluation — Dogfood Route

本文件只記錄本次 task/session 的可觀測 orchestration artifacts，不記錄
hidden chain-of-thought。`using-superpowers` 仍是 resident task/session
authority；Stage Router 只負責選 skill，不負責選 model 或 reasoning effort。

## Repo truth

| 欄位 | 值 |
|---|---|
| starting HEAD | `a414ff88adbd112e97e4fcc69ca8cf0c4f7399c6` |
| working branch | `bench/v3-codex-effort-evaluation` |
| task | Phase 3F controlled Codex reasoning-effort evaluation |
| catalog snapshot | `registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac` |
| overlay digest | `sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b` |
| Stage Router weights | unchanged |
| model routing | not implemented |

## Active StageRoutes

每個 active stage 都有一個獨立 route 結果。`NO_SKILL_NEEDED` 是有效結果，
不是缺漏；selected body 只在下游執行需要時載入。

| stage | result | route id | selected skills | body files loaded |
|---|---|---|---|---:|
| understand | `NO_SKILL_NEEDED` | `route:T-v3-phase3f-dogfood-understand:understand:0e1ca9f0a89a3b08` | — | 0 |
| design | `SKILLS_SELECTED` | `route:T-v3-phase3f-dogfood-understand:design:212c97377aa9abda` | `using-superpowers`, `verification-before-completion` | 1 |
| plan | `NO_SKILL_NEEDED` | `route:T-v3-phase3f-dogfood-understand:plan:8e671bd607d6cdc3` | — | 0 |
| implement | `SKILLS_SELECTED` | `route:T-v3-phase3f-dogfood-understand:implement:4cef935f9e626537` | `using-superpowers`, `executing-plans`, `maps`, `official-code-review`, `verification-before-completion` | 4 |
| review | `SKILLS_SELECTED` | `route:T-v3-phase3f-dogfood-understand:review:00a9999b749b0476` | `using-superpowers`, `brandkit`, `permission-tuner`, `verification-before-completion` | 3 |
| verify | `SKILLS_SELECTED` | `route:T-v3-phase3f-dogfood-understand:verify:34f8e7495061174d` | `using-superpowers`, `verification-before-completion` | 1 |

實際遵循的程序包含 resident orchestration、source-driven development、
security/hardening、planning 與 verification。選出的 `maps`、`brandkit`、
`permission-tuner` 與本 task 語義不符，記入 `ROUTING_DEFECT` backlog；本分支
沒有執行其程序，也沒有修改 Stage Router 權重或加入 fixture-specific exception。

## Compiled route reuse

正式 benchmark workload 只在每個 workload 編譯一次：

```text
TaskSpec → StageRouter → StageRoute → CodexAdapter → CompiledExecutionBundle
```

| workload | route status | selected IDs | router body loads | compile body loads |
|---|---|---|---:|---:|
| H01 | `SKILLS_SELECTED` | `tdd`, `using-superpowers`, `verification-before-completion` | 0 | 2 |
| H03 | `SKILLS_SELECTED` | `using-superpowers`, `verification-before-completion` | 0 | 1 |

`using-superpowers` 的 resident body 不在每個 stage 重載。實驗 cells 只重用
同一份 immutable workload route/bundle metadata；effort level 不會觸發重新路由。
計時欄位不再進入 stable route digest，避免 route identity 隨 wall-clock 改變。

## Bounded execution schedule

目標 schedule 是六個 cell，採 interleaved 順序以降低時間因素混淆：

```text
1  H01 LOW    #1
2  H01 MEDIUM #1
3  H01 MEDIUM #2
4  H01 LOW    #2
5  H03 LOW    #1
6  H03 MEDIUM #1
```

修正後的 invocation contract 已執行六個排程 cell；每個 process 都 exit 1 且
沒有 usable stdout。執行當下的舊分類邏輯沒有在第一個空輸出失敗處停止，這個
measurement-integrity defect 隨後已修正為 fail-closed，並將六筆結果全部正規化
為 `UNAVAILABLE/BLOCKED`。它們沒有被當成 H01 的成功 repetition，也沒有產生
任何 effort 品質結論；達到硬上限後不再執行 live cell。

## Authority and evidence boundary

- Codex command 使用 explicit model、explicit effort、`--ephemeral`、
  `--ignore-user-config`、`--ignore-rules`、`--config approval_policy=never`、
  sandbox 與 JSONL output。
- wrapper 使用 `shell=False`、`stdin=DEVNULL`、isolated temporary fixture、
  finite timeout。
- ranking 讀 metadata；只有 selected skills 在 bundle compile 時進入 execution-local
  context；raw prompt、stdout、stderr、skill body、credential 不寫入 evidence。
- `NO_SKILL_NEEDED` workload 會載入零個額外 skill body。
- blocked process 不產生 quality、token、model-call 或 cost 結論。

## Routing defects observed

| stage | skill | defect | body/procedure |
|---|---|---|---|
| implement | `maps` | 未見 graph/maps 語義需求 | body loaded by dogfood route; not executed |
| review | `brandkit` | 非 branding task | body loaded by dogfood route; not executed |
| review | `permission-tuner` | 非 permission-tuning task | body loaded by dogfood route; not executed |

這些是下一個 metadata/routing cleanup 的觀察，不是本 Phase 3F 的實驗變數；
paired effort comparison 若能執行，會固定同一份 route 以避免 selection drift。

## Gate result

```yaml
dogfood_routes: emitted
selected_only_loading: preserved
stage_router_modified: false
controlled_live_schedule_started: true
controlled_live_schedule_completed: false
scheduled_cells_attempted: 6
usable_quality_observations: 0
stop_reason: no usable runtime output; hard live-run cap reached
```
