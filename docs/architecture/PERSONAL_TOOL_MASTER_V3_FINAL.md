# Personal Tool Master V3：架構入口

此舊入口保留，完整架構已整理為以下六份文件。V3 為已完成的 advisory 工作流程層：母技能與 helper 提供建議，宿主控制工具執行與權限；故障使用 metadata fallback 或手動流程。

| 文件 | 內容 |
|---|---|
| [系統架構](V3_SYSTEM_ARCHITECTURE.md) | 需求、演化、整體與請求流程 |
| [元件參考](V3_COMPONENT_REFERENCE.md) | 實際路徑、metadata 分數、profile、digest |
| [工作流程與工具映射](V3_WORKFLOW_AND_TOOL_MAPPING.md) | 宿主差異、真實 schema、adapter、fallback |
| [儲存與狀態](V3_STORAGE_AND_STATE.md) | JSON、TASK／PLAN／STATE、暫存與私人 legacy DB |
| [測試與限制](V3_TESTING_AND_LIMITATIONS.md) | 歷史證據、公開測試、大小／時間上限與未測能力 |
| [發布與遷移](V3_RELEASE_AND_MIGRATION.md) | 公開 14 技能、權利分界、Git 與正式發布、回復 |

程式 [PR #27](https://github.com/juhjuhx/agent-skills/pull/27) 已合併；文件 PR、最終 tag 與 Release 的身分以發布文件與外部 GitHub 物件核實，不能由「FINAL」檔名推定完成。

歷史完整個人驗收、token／latency 案例與未測宿主的安全摘要移至 [測試與限制](V3_TESTING_AND_LIMITATIONS.md)；[2026-10-12 公開候選驗收](../發布驗收.md) 保留原日期與範圍。私人 raw logs、session、provider 設定與資料庫不打包。
