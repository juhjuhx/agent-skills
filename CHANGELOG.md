# 變更紀錄

## v3.0.0 — Personal Tool Master

V3 程式與精簡封裝已由 [PR #27](https://github.com/juhjuhx/agent-skills/pull/27) 合併 main，merge commit 為 `a570dd639d06b8b7d164493bac98f01a55cdbc6f`。本次以獨立文件分支整理架構、測試限制與遷移；正式 annotated tag／GitHub Release 的實際狀態以 [發布與遷移](docs/architecture/V3_RELEASE_AND_MIGRATION.md) 與 [GitHub Releases](https://github.com/juhjuhx/agent-skills/releases) 核實，不預先宣稱建立。

- `using-superpowers` 單一母技能，metadata 先行選少量相關技能。
- Python 標準庫 helper，Compact RoutePacket 與當次工具名稱／描述能力映射。
- 由宿主執行並控制權限；路由故障使用 fallback，沒有全域 tool gate。
- 可選 OpenCode advisory／「工具大師V3」primary；不預設改宿主全域設定。
- TASK／PLAN／STATE 文件式長任務續接，由 Agent 自行保存及核對。
- installer 保護 dirty／ignored／既有插件與 nonmanaged 內容；檔案切換失敗回復。
- 公開快照 14 個固定來源與完整 MIT 通知核心技能，未核實材料與外部 symlink 不打包。
- 根 MIT 限定有權授權的 V3 原創範圍；Superpowers 保留 Jesse Vincent copyright。
- PowerPoint 等受限制材料只排除新版；不清除 Git 歷史內容或疑似憑證風險。
- 六份架構文件與十組 ASCII／Mermaid 對照圖；舊架構與發布入口導向完整文件。
- MiMo 免費模型的研究／debug／續接為歷史部分成功案例；公開 14 技能未重做模型 E2E，不保證 7B／9B／12B 或固定 86% token 節省。

[2026-10-12 候選驗收](docs/發布驗收.md) 保留原測試、日期與當時 Phase A 範圍；本次正式流程接續程式與文件合併後的 tag／Release。不補造 V1／V2 GitHub Releases。
