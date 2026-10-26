# ADR-0001 — Phase 8+ 分發架構定位

**Status**: Accepted (2026-10-25, user)

## Context

M4-P8 已將 464 個 skill（14 core + 450 extra）發布至 `juhjuhx/agent-skills` main（`3d55520`），
提供 `install.sh`（curl bootstrap）→ `install_v3.py` 跨 6 host 安裝器 + `catalog.lock.json` SHA-256 鎖 +
V3 advisory router（fail-open）。開源對標研究顯示生態有三種分發形態：
NPX CLI（agent-skills-hub）、team sync hooks（skillcrew）、gh skill + pin（JPeetz）。

## Decision

- **A（本階段）**：唯一正式分發面 = git clone + bash install.sh + Python installer。
  本階段只做 README 重構（5 分鐘上車首頁）+ ASCII/TUI 架構圖 + debug/review 流程。
- **B（roadmap 第二階段）**：GitHub Pages 靜態探索介面，`catalog.json` 為唯一資料源，
  分類/搜尋/篩選/詳情，零 backend。
- **C（暫緩）**：NPX CLI 不引入；不建立第二套安裝與更新邏輯；repo 不新增 npm/Node 依賴。

## Consequences

- 維護面單一，數字真相來源固定為 catalog.json + git tree。
- 代價：沒有 web 發現層（由 B 補）；`gh skill install` 不原生支援（可 later，非本階段）。
- README 中所有 skill 數字必須可溯源；未跑 E2E 的 host 不得宣稱已實機驗證。
- 保留：lock SHA-256、授權 gate、fail-open router、既有 install 相容性。

## Invariants（本階段）

1. 不修改 464 個 skill 內容（除確切問題另行審核）。
2. 不破壞 `install.sh` / `install_v3.py` 行為。
3. 不碰 P5 未提交工作樹（main-repo 的 scout/scheduler/tests 3 檔）。
4. 最終 = 測試 + 獨立審查 + CI 綠 + ff-push。
