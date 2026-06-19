# Architectural Risks & Mitigations

## R-001 架構複雜度（Adapter 維護成本）
6 個 Adapter 需解析不同 CLI 輸出格式。先做 dry-run adapter（只產 brief + command），驗證格式穩定後再上 subprocess.

## R-002 狀態機不嚴謹
子任務部分成功、review 後回退、重複 claim、卡住的任務。**緩解**：完整轉移矩陣 + stuck detection + recovery suggestions.

## R-003 Planner 輸出格式不穩定
Codex 是對話式 Agent，無法保證 YAML schema 符合。**緩解**：Plan Validator + 4-level degradation pipeline.

## R-004 Resource Manager 即時性
quota 可能在任務執行中耗盡。**緩解**：subprocess 監控 thread，即時更新 agent 狀態.

## R-005 長期記憶分界模糊
Markdown vs SQLite 邊界不清。**緩解**：統一存 SQLite，Markdown 僅匯出.

## R-006 Artifact 傳遞缺失
depends_on 只表達依賴，不確保 artifact 傳遞。**緩解**：tiered injection (summary/excerpt/path).

## R-007 GUI 過早
GUI 在 Adapter 之前只能看靜態資料。**緩解**：GUI 延後到 Adapter + Planner 驗證後.

## R-008 遷移策略不足
agents ID → SQLite 無具體遷移步驟。**緩解**：增加 migrate 指令.

## R-009 測試策略缺失
無測試覆蓋定義。**緩解**：每個 MVP 必須附帶 smoke test + mock agent 測試.

## R-010 效能瓶頸（串行調度）
所有 subtask 串行。**緩解**：parallel_group 機制.
