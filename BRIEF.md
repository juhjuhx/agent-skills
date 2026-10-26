# BRIEF — Phase 8+ README & 架構圖形化（Q1 定案後）

**Goal**: 重構 README 為「5 分鐘上車」首頁（這是什麼 → 多少 Skills → 支援哪些 Agent → 怎麼裝 → 怎麼驗證），並建立明確的 TUI/ASCII 架構圖；不實作第二分發面。

## Q1 決定（2026-10-25，user）

| 選項 | 決定 |
|---|---|
| A — Git + Bash + Python installer 為唯一正式分發 | **本階段實作**：重構 README、簡化安裝入口 |
| B — GitHub Pages 靜態技能探索介面（catalog.json 唯一資料源；分類/搜尋/篩選/詳情，零 backend） | **第二階段 Roadmap** |
| C — NPX CLI 包裝 | **暫緩**（不建第二套安裝/更新邏輯） |

## 必修問題（user 核實於 origin main = `3d55520`，tree 464 SKILL.md）

1. README 多處寫「461 個名稱級可安裝」，與 catalog.json `installable_by_unique_name = 464` 矛盾 → 以 catalog 為準。
2. 英文 Quick Start 仍寫「public edition includes 14 verified-source core skills」→ 464（14 core + 450 extra）。
3. README 標題與驗收文字偏早期 V3 精簡版 → 更新為 P8 後的真實狀態。
4. 安裝教學入口太深（授權說明壓在 Quick Start 前）→ 首頁前置。

## 首頁必須呈現

464 真實數量（由 catalog.json / Git tree 驗證，不許手寫矛盾數字）；Hermes/DSH/OpenCode/Codex/Claude/Gemini 支援狀態表（未跑過 E2E 的 host 不得宣稱已實機驗證）；完整安裝與驗證命令；分類索引入口；一張完整架構圖；License/Security 摘要；詳細文件入口。目標 80–120 行，可讀性與準確性優先。舊版架構/長篇限制/測試細節移 `docs/`，保留精簡授權與安全警告並鏈接詳情。

## Scope IN

- README.md 重構；docs/ 新增一張 ASCII 架構總圖 + router 流程圖 + P0–P8 roadmap；BRIEF/ADR 決策紀錄；`install.sh` flag 存在性與 help 文案校對；CI 綠。

## Scope OUT（min 2）

- 不修改 450+14 個既有 skill 內容（除確切問題另行審核）。
- 不破壞 `install.sh` / `install_v3.py` 現有行為與相容性。
- 不新增 npm/Node 依賴；不動 P5 未提交工作樹（main-repo 的 scout/scheduler 3 檔）。
- 不實作 B（GH Pages）與 C（NPX）；保留 lock SHA-256、授權 gate、fail-open router 不變。

## Constraints

- 數字一律由 catalog.json / git ls-tree 生成或校對。
- 只提交本輪相關檔案；ff-push only。

## Exit Criteria

- [ ] README 首頁五段（是什麼/數量/Agent/安裝/驗證）全數可獨立閱讀
- [ ] README 中每個數字可溯源到 catalog.json 或 git tree（人工校對紀錄在 docs/）
- [ ] `bash install.sh --all --host hermes --dry-run` 與 `--all --host dsh --dry-run` 實際執行通過
- [ ] 架構圖至少 2 張（系統總覽 + router 請求流程），ASCII 在 80 欄可讀
- [ ] 獨立審查 + CI 通過後 ff-push

## Risk Flags

- 未實機 E2E 的 host（Claude/Hermes/DSH live）若被誤宣稱已驗證 → 表格須標「flag 存在 / 未實機驗證」。
- README 重寫時誤刪授權与安全警告 → 只做精簡 + 鏈接，不刪段落。

## Contraindication

- 若 464 數字與 git tree 再次不符（例如 P5 污染進 worktree），先對帳再寫文件，不硬調數字。

## Q2 決定（2026-10-25，user）

- **Q2.1 交付形式 = A（純靜態）**：Unicode box-drawing ASCII（`┌─┐ │ └`），放 markdown code block。
  不建互動 TUI、不新增 `curses`/readline 導覽入口、不建第二份 `architecture.json` 資料源。
  - 圖的數量與位置：**待 Q2.3**（初案：README 1 張系統總覽 + docs/ 2 張 router 請求流程 & P0–P8 roadmap）。
  - box 內一律**英文標籤**（CJK 全形字撐歪方框是 terminal 圖經典坑）；中文說明放 box 外。
  - 80 欄可讀、GitHub 直接渲染、零依賴——與 Q1-A「單一分發面、不新增 runtime」同構。
  - **後果記錄**：原始指令「用 TUI 寫得明確」收斂為「靜態 ASCII 高可讀化」；互動導航價值讓給 Q1-B（GH Pages 探索介面，roadmap 第二階段）。
- **Q2.2 記號系統 = A（最小記號集）**：box-drawing 結構符＋`→` 流向＋狀態記號 `PASS ✓`／`PARTIAL ◐`／`BLOCKED ✗`；實線框=本 repo、虛線框／`(external)`=宿主側。無 emoji、無配色代碼（emoji 跨 terminal/GitHub 顯示成方塊是已知坑）。
  - 欄寬：**80 欄硬限**（跨 terminal/GitHub 最穩；user 原話「80 欄可讀」）。
- **Q2.3 圖清單**：初案 README 1 張系統總覽＋docs/ 2 張（router 請求流程、P0–P8 roadmap）；節點清單於 build 階段落定、完成後由 user 審圖。

## Status

WORKING — Q1=A、Q2.1=A、Q2.2=A 定案；剩 Q2.3 節點清單（build 階段落定）。實作未開始。所有 skill 數字仍以 catalog.json / git tree 為準。
