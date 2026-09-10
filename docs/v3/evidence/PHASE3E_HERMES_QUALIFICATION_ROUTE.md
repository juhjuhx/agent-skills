# Phase 3E Hermes 資格閘門狗食化路由

本紀錄只保存可觀察的 StageRoute、技能載入狀態與作業證據；不保存
hidden chain-of-thought、原始 prompt、完整 runtime output、憑證或技能本文。

## 任務

| 欄位 | 值 |
|---|---|
| TASK | Qualification gate for the installed Hermes runtime |
| START_HEAD | `2f476371f139b050536c485a2ed13adaa59052ae` |
| BRANCH | `feat/v3-hermes-runtime-qualification` |
| TaskSpec | `phase3e-hermes-qualification` |
| TASK TYPE | `review` |
| COMPLEXITY / RISK / AMBIGUITY | `COMPLEX` / `HIGH` / `MEDIUM` |
| ARCHITECTURE IMPACT | `ARCHITECTURE-CHANGING` (qualification only; no adapter) |
| REGISTRY EPOCH | `registry:db3b67d5b051c4223da9146b2b836a9ed45e9bac` |
| METADATA RECORDS INSPECTED | `214` per route |
| SKILL BODIES READ DURING RANKING | `0` |
| DEEP UNDERSTANDING | `NOT_REQUIRED`: bounded qualification used source-driven, security and verification procedures; no full graph build was needed |

`using-superpowers` 是 task/session 層級的 resident authority。它只在需要的
StageRoute 中以 GATE 參照，不在每個 stage 重新載入完整本文。可執行的
`verification-before-completion` 本文已按 selected-only 規則載入並用於資格閘門；
`cost-tracker` 雖被 Router 選中，但目前找不到對應的已安裝或 repository
`SKILL.md`，所以沒有載入，也沒有執行其程序。

## StageRoute 記錄

### UNDERSTAND

| 欄位 | 證據 |
|---|---|
| OBJECTIVE | 建立 repository、分支與 Hermes 安裝來源真相 |
| ROUTE | `route:phase3e-hermes-qualification:understand:373d60fb711c43c0` |
| SKILLS CONSIDERED | `214` 筆 metadata；Router 顯示 Agent Development、Command Development、Hook Development 等不相容候選 |
| SKILLS SELECTED | `[]` |
| ROLE SLOT | `NO_SKILL_NEEDED` |
| WHY / REJECTED | 既有 repo truth 與安裝探針足以完成 bounded understanding；候選的 stage/task/domain metadata 不相容 |
| AGENT / RUNTIME | development host: Codex；candidate under test: Hermes（未啟動） |
| MODEL PROFILE | `unselected` |
| TOOLS | git、read-only local inspection |
| INPUT ARTIFACTS | AGENTS.md、Phase 3D evidence、current contracts |
| OUTPUT ARTIFACTS | installed-version/provenance notes |
| EVIDENCE REQUIRED | source provenance、version verification |
| RESULT | `NO_SKILL_NEEDED` |

### RESEARCH

| 欄位 | 證據 |
|---|---|
| OBJECTIVE | 驗證 approval、isolation、provider、tool 與 persistence semantics |
| ROUTE | `route:phase3e-hermes-qualification:research:fbe5c971b10b7dd2` |
| SKILLS CONSIDERED | `214` metadata；filtered `212`；eligible candidate set was narrow |
| SKILLS SELECTED | `using-superpowers` / `GATE`; `verification-before-completion` / `VERIFY` |
| WHY SELECTED | resident orchestration gate plus independent evidence-completion checks |
| REJECTED | MCP/plugin/command development candidates rejected for stage/domain mismatch; no unrelated body loaded |
| AGENT / RUNTIME | development host: Codex；Hermes runtime not invoked |
| MODEL PROFILE | `unselected` |
| TOOLS | local Hermes help/status/auth; official Hermes release/source pages |
| INPUT ARTIFACTS | installed help、installed source snapshot、official v2026.8.3 docs/source |
| OUTPUT ARTIFACTS | capability mapping、approval conclusion、provider status |
| EVIDENCE REQUIRED | official source、installed behavior、sanitized diagnostics |
| RESULT | `SKILLS_SELECTED`; research completed, provider gate blocked |

### VERIFY

| 欄位 | 證據 |
|---|---|
| OBJECTIVE | 確認 provider block 後不啟動模型，且保留 fail-closed 決策 |
| ROUTE | `route:phase3e-hermes-qualification:verify:1dc15a2ba62b1767` |
| SKILLS CONSIDERED | `214` metadata；filtered `212` |
| SKILLS SELECTED | `using-superpowers` / `GATE`; `cost-tracker` / `VERIFY`（unavailable body） |
| WHY SELECTED | resident gate；Router 將 cost/usage verification 候選置於 VERIFY |
| REJECTED | 其餘候選因 stage/task/domain mismatch 被拒；`cost-tracker` 因無可發現 `SKILL.md` 形成 ROUTING_DEFECT |
| AGENT / RUNTIME | development host: Codex；Hermes 未啟動 |
| MODEL PROFILE | `unselected` |
| TOOLS | sanitized evidence validation、status cross-check |
| INPUT ARTIFACTS | provider auth status、qualification record、官方 semantics |
| OUTPUT ARTIFACTS | `HERMES_RUNTIME_BLOCKED` 決策 |
| EVIDENCE REQUIRED | provider status、no model invocation、no credential persistence |
| RESULT | `SKILLS_SELECTED`; verification gate confirms Smoke A/H03 ineligible |

### HARDEN

| 欄位 | 證據 |
|---|---|
| OBJECTIVE | 審查 approval bypass、憑證邊界、學習 persistence 與 evidence serialization |
| ROUTE | `route:phase3e-hermes-qualification:harden:90623fc108bec4a3` |
| SKILLS CONSIDERED | `214` metadata；候選均未達 stage/security/domain gate |
| SKILLS SELECTED | `[]` |
| ROLE SLOT | `NO_SKILL_NEEDED` |
| WHY / REJECTED | 沒有新增 runtime code；security review 以已載入的 security/hardening 程序與直接 source evidence 完成，避免無關技能載入 |
| AGENT / RUNTIME | development host: Codex；Hermes 未啟動 |
| MODEL PROFILE | `unselected` |
| TOOLS | read-only diff/evidence/security scan |
| INPUT ARTIFACTS | qualification probe results |
| OUTPUT ARTIFACTS | security assertions、blocked-lane boundary |
| EVIDENCE REQUIRED | no bypass、no credential/raw-output persistence |
| RESULT | `NO_SKILL_NEEDED` |

### HANDOFF

| 欄位 | 證據 |
|---|---|
| OBJECTIVE | 交付 bounded 結果並提出受控 Codex model/effort experiment |
| ROUTE | `route:phase3e-hermes-qualification:handoff:3428f2a2f8f66e58` |
| SKILLS CONSIDERED | `214` metadata；filtered `212` |
| SKILLS SELECTED | `using-superpowers` / `GATE`; `verification-before-completion` / `VERIFY` |
| WHY SELECTED | preserve session authority and verify handoff artifacts |
| REJECTED | plugin/command/skill development candidates因 handoff task/domain不相容而拒絕 |
| AGENT / RUNTIME | development host: Codex；Hermes candidate blocked |
| MODEL PROFILE | `unselected` |
| TOOLS | evidence/documentation only |
| INPUT ARTIFACTS | V7 evidence、sanitized qualification record |
| OUTPUT ARTIFACTS | `NEXT_CODEX_PROMPT.md` |
| EVIDENCE REQUIRED | decision record、next prompt |
| RESULT | `SKILLS_SELECTED` |

## Qualification gate outcome

```yaml
DEEP_UNDERSTANDING: NOT_REQUIRED
HERMES_ADAPTER: NOT_BUILT
SMOKE_A: NOT_RUN
SMOKE_B: NOT_ELIGIBLE
H03: NOT_ELIGIBLE
FINAL_DECISION: HERMES_RUNTIME_BLOCKED
```

## Routing defect

```yaml
- stage: verify
  skill_id: cost-tracker
  selected: true
  metadata_reason: role=VERIFY; cost/usage-oriented candidate
  body_loaded: false
  procedure_executed: false
  defect: no matching installed/repository SKILL.md was discoverable
```

這個 defect 只記錄，不在本分支調整 Stage Router 權重或加入 fixture-specific
例外。
