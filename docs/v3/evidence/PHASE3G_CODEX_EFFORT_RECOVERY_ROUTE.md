# Phase 3G Codex Effort Recovery — Dogfood Route

本文件只保存可觀測的 orchestration artifacts，不保存 hidden chain-of-thought。
`using-superpowers` 是 resident task/session authority；Stage Router 只選 skill，
不選 model、provider 或 reasoning effort。

## Repo truth

| 欄位 | 值 |
|---|---|
| starting HEAD | `d3af66ce4d9423ae7174effb3a798a1e61ecc3d6` |
| branch | `bench/v3-codex-effort-recovery` |
| task | Phase 3G Codex transport qualification and controlled-effort recovery |
| Stage Router | unchanged |
| benchmark cells | not started after transport gate |

## Active StageRoutes

本次只啟用實際需要的四個 stage。每個 stage 都先通過既有 metadata-first
Stage Router，再只解析該 route 選中的 skill metadata；下游需要 procedure 時
才載入 selected body。`using-superpowers` 保持 resident，不在每個 stage 重載。

| stage | result | route id | selected skills | non-resident body files loaded |
|---|---|---|---|---:|
| UNDERSTAND | `SKILLS_SELECTED` | `route:holdout:H03:understand:af21d9f248ec71e4` | `using-superpowers`, `understand`, `understand-chat` | 2 |
| DESIGN | `SKILLS_SELECTED` | `route:holdout:H03:design:2f93c6c1fcc33791` | `using-superpowers`, `verification-before-completion` | 1 |
| VERIFY | `SKILLS_SELECTED` | `route:holdout:H03:verify:1ef3eeb124ecc680` | `using-superpowers`, `writing-skills` | 1 |
| HANDOFF | `SKILLS_SELECTED` | `route:holdout:H03:handoff:539c966d1bd3af84` | `using-superpowers`, `finishing-a-development-branch`, `wiki-viewer`, `official-code-review`, `verification-before-completion` | 4 |

本次沒有把整個 catalog 或所有 `SKILL.md` body 放進 stage context。實際遵循的
流程能力包括 resident orchestration、source-driven verification、security
hardening、planning 與 verification；selected body 只在對應工作需要時使用。

## Routing defects observed

本次 dogfood 沿用 Stage Router，沒有修權重。下列選擇記為 backlog，不影響
transport verdict：

| stage | skill | observation | body/procedure |
|---|---|---|---|
| VERIFY | `writing-skills` | verify evidence task 與 writing skill 語義不完全相符 | body loaded; not used as authority |
| HANDOFF | `wiki-viewer` | handoff evidence 不需要 wiki viewing | body loaded; not used |
| UNDERSTAND | `understand-chat` | generic understanding variant may be broader than source-truth need | body loaded; not independently executed |

這些是 Stage Router metadata debt，不能在本 branch 以 fixture-specific rule 修復。

## Transport gate

執行唯一一次：

```text
codex doctor --json --summary
```

fresh installed facts：`codex-cli 0.153.4`、`rust-v0.153.4`、release source commit
`3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`。Doctor 摘要顯示 auth 已配置、provider
為 `openai`、configured model 為 `gpt-5.6-luna`，但 required ChatGPT inference
endpoint 的 DNS/HTTP connect failure 使 reachability = `PROVIDER_UNREACHABLE`。

依 gate：

```yaml
provider_preflight: PROVIDER_UNREACHABLE
Smoke_0: NOT_RUN
H01_LOW: NOT_RUN
H01_MEDIUM: NOT_RUN
H03_LOW: NOT_RUN
H03_MEDIUM: NOT_RUN
H09: NOT_RUN
```

這裡的 `NOT_RUN` 是刻意的安全結果，不是漏測。沒有為 provider failure 重試
相同命令，也沒有改 sandbox、approval、model 或 effort 來取得輸出。

## Recovery schedule proposal

只在 provider transport 已恢復且 Smoke 0 PASS 後，沿用 Phase 3F 的 immutable
route/bundle，按下列順序補跑；不是本 Phase 的執行結果：

```text
1 H01 LOW    #1
2 H01 MEDIUM #1
3 H01 MEDIUM #2
4 H01 LOW    #2
5 H03 LOW    #1
6 H03 MEDIUM #1
```

若再次出現 provider instability、quota warning、measurement integrity 或 fixture
isolation 問題，停止剩餘 cells。不要跑 H09、HIGH/XHIGH 或第二個 model。

## Evidence boundary

本次沒有 REAL_EXECUTION task observation。`gpt-5.6-luna` 只是在 doctor 的 non-secret
configuration summary 中可見，不能標為 runtime-accepted 或 effective model observed。
沒有新增 token、model-call、tool-call、cost 或 effort-quality evidence。

下一步只允許恢復 provider transport 後再執行 Smoke 0；若仍不可達，保持
`CODEX_LIVE_TRANSPORT_BLOCKED`，不要建立新的 runtime diagnostic phase。
