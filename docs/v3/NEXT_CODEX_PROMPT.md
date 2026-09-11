# AGENT SKILLS MATRIX v3
# 下一步提案：STATIC PRODUCTIZATION PREP

Repository:
juhjuhx/agent-skills

Phase 3H result:
STAGE_ROUTER_PRODUCTION_READY

Independent live status:
CODEX_LIVE_TRANSPORT_BLOCKED

本文件只是下一步提案，不要在本 phase 執行。不要開始 Phase 4，不要做 model /
effort routing，不要重試 Codex transport，不要修改 Stage Router weights，也不
要追逐新的 runtime。

============================================================
0. PURPOSE
============================================================

Phase 3H 已以 recorded defect census、curated semantic patches、8 個 semantic
holdout near-miss、未變更的 A–J regression、snapshot reuse、zero body reads 與
deterministic replay 關閉反覆出現的 false-positive families。

剩餘的 `mathguard` 是一次、未載入 body、未執行 procedure 的 isolated backlog，
不得用 fixture-specific exclusion 過度修補。

Codex provider transport 仍為 `CODEX_LIVE_TRANSPORT_BLOCKED`，因此不能宣稱
effort/model policy readiness，也不能把 Stage Router READY 誤讀為 Phase 4 gate。

============================================================
1. SCOPE — STATIC ONLY
============================================================

下一步只做不依賴 live model 的 productization prep：

- 固化 `RoutingCatalogSnapshot` 的 load/validation/reuse contract；
- 將 `StageRoute`、selected skill IDs/digests、provenance、body-load evidence
  接到現有 runtime-neutral execution bundle 的靜態 conformance checks；
- 保持生成 metadata、curated patch、compiled snapshot 的來源邊界；
- 輸出 route explainability、determinism、stale-digest 與 zero-body-load checks；
- 維持 `NO_SKILL_NEEDED`、trust/quarantine、permission fail-closed 與 selected-only
  downstream loading。

不要加入 runtime adapter、model preference、effort policy、adaptive learning、
database、daemon、catalog manager 或背景服務。

============================================================
2. REQUIRED REGRESSION CONTRACT
============================================================

每次靜態 productization change 必須重跑：

- A–J unchanged Stage Router regression；
- 8-task semantic holdout（不調權重）；
- Phase 3H dogfood replay；
- curated override survives regeneration；
- stale canonical skill digest invalidates the snapshot；
- 214 metadata records / 0 SKILL.md body reads during ranking；
- deterministic route ID and selected skill digests；
- local schema, link, diff and secret/private-path checks。

`mathguard` 若再次出現，先累積 recorded evidence；只有形成重複且具 material
context/procedure cost 的 semantic family，才另提 bounded metadata cleanup。

============================================================
3. LIVE BOUNDARY
============================================================

不要執行 Codex、OpenCode、Claude 或 Hermes。

若未來 transport 在外部恢復，另行 resume 既有 Phase 3G controlled LOW/MEDIUM
experiment contract；不要重建 harness、不要重跑 Stage Router、不要在這個 static
prep branch 偷開 effort routing。

============================================================
4. ACCEPTANCE
============================================================

需要：

- `STAGE_ROUTER_PRODUCTION_READY` evidence 仍有效；
- 沒有 A–J material regression；
- semantic positive/near-miss coverage 保持；
- snapshot validation/reuse 可觀測且不讀 body；
- no authority widening；
- no model/runtime policy mutation；
- `CODEX_LIVE_TRANSPORT_BLOCKED` 原樣保留。

============================================================
5. FUTURE LIVE GATE
============================================================

這不是 Phase 4。只有既有 Phase 3G 的 Smoke 0、H01 LOW/MEDIUM paired repetition
與 H03 exploratory pair 在 provider transport 恢復後完成，才可重新評估
`INTRA_RUNTIME_EFFORT_ROUTING_READINESS`。

Cross-runtime readiness 仍為 `NOT_READY`，不可由 static adapter 或 blocked lane
推導出來。
