---
name: auto-learn
description: "從成功工作流程中自動學習並提煉可複用的 skills。Use when: 完成複雜任務、識別重複模式、創建工作流程模板。"
version: 1.0.0
author: Agnes + Hermes
license: MIT
tags: [learning, automation, workflow, skill-creation]
related_skills: [skill-authoring, find-skills, using-superpowers]
---

# Auto-Learn — 自動學習技能

從成功的工作流程中自動識別、提煉和創建可複用的 skills。

## 核心能力

1. **模式識別** — 從多次任務中識別重複模式
2. **提煉提問** — 詢問用戶確認是否要保存為 skill
3. **自動創建** — 使用 skill-authoring 規範創建新 skill
4. **版本管理** — 跟蹤 skill 的演進歷史

## 觸發條件

### 明確觸發
- 用戶說：「這是我們常做的」
- 用戶說：「保存這個流程」
- 用戶說：「創建 skill」
- 任務完成後，agent 主動提議

### 隱式觸發
- 使用 ≥ 3 個 skills 協作完成任務
- 任務執行時間 > 15 分鐘
- 涉及特定專案的獨特工作流程
- 遇到並解決了新的問題模式

## 工作流程

### Step 1: 任務完成後的自動檢查

```
1. 任務完成
2. 回顧本次使用的 skills
3. 檢查是否有以下模式：
   - 相同的 skills 組合？
   - 相同的問題和解決方案？
   - 特定的文件路徑或配置？
4. 如果命中 ≥ 2 個條件，主動提議：
   「我注意到這個任務使用了 [skills] 組合，且涉及 [模式]。
   是否要提煉為可複用的 skill？」
```

### Step 2: 與用戶確認

如果用戶同意，執行：

```
1. 收集必要資訊：
   - Skill 名稱
   - 描述（觸發條件）
   - 關鍵步驟
   - 注意事項和 pitfalls
   - 相關的 skills 組合

2. 使用 skill-authoring 創建：
   skill_manage(
     action='create',
     name='my-skill-name',
     content='... SKILL.md content ...'
   )

3. 驗證 skill 載入：
   skill_view(name='my-skill-name')
```

### Step 3: 記錄學習

在 memory 中記錄：

```
name: learned-workflow
content: |
  從 [任務描述] 中學習到 [skill 名稱]
  建立時間：[ISO timestamp]
  使用場景：[觸發條件]
  相關 skills：[組合]
```

## 示例場景

### 場景 1：劇場投影設計

```
任務：生成 1-1 場景的投影圖
使用的 skills：
- theater-projection-design
- baoyu-imagine
- agnes-vision
- html-canvas-to-video

模式識別：
- 每次都使用相同的 4 個 skills
- 有固定的工作流程（生成 → 分析 → 輸出）
- 涉及特定的文件路徑

提議：
「我注意到劇場投影設計專案總是使用這 4 個 skills。
是否要創建 'projection-design-pipeline' skill 整合這個流程？」
```

### 場景 2：語音轉文字 App

```
任務：構建 macOS 語音轉文字 App
使用的 skills：
- local-voice-to-text-app
- hermes-agent
- skill-authoring

模式識別：
- 遇到了特定的 Tauri + Python 架構問題
- 有固定的測試和構建流程
- 有特定的 pitfall 需要記住

提議：
「這個 App 開發涉及特定的架構模式和陷阱。
是否要更新 'local-voice-to-text-app' skill 以包含這些經驗？」
```

## Pitfalls

1. **不要過度抽象** — skill 應該聚焦於可複用的模式，不是通用知識
2. **保持用戶確認** — 創建 skill 前必須與用戶確認
3. **避免重複** — 檢查是否已有類似的 skill
4. **更新記憶體** — 創建 skill 後更新 memory 和相關文檔

## 相關 Skills

- `skill-authoring` — Skill 撰寫規範
- `find-skills` — 搜尋公開 skills
- `using-superpowers` — 自動掃描和匹配 skills

## Session Closing Hook

每次 session 結束時，自動執行檢查（見 `references/session-closing-hook.md`）：

1. 回顧本次使用的 skills
2. 檢查重複模式、新問題、新文件
3. 提議是否要保存為 skill
4. 如果用戶同意，立即創建或更新

## Pitfalls

1. **不要過度抽象** — skill 應該聚焦於可複用的模式，不是通用知識
2. **保持用戶確認** — 創建 skill 前必須與用戶確認
3. **避免重複** — 檢查是否已有類似的 skill
4. **更新記憶體** — 創建 skill 後更新 memory 和相關文檔
5. **不要過度干擾** — 只在確實有價值時提議

## 相關 Skills

- `skill-authoring` — Skill 撰寫規範
- `find-skills` — 搜尋公開 skills
- `using-superpowers` — 自動掃描和匹配 skills
- `curator` — Skills 庫管理

## 未來擴展

1. **自動頻率統計** — 記錄每個 skill 的使用頻率和成功/失敗率
2. **智能推薦** — 基於使用模式推薦 skill 組合
3. **版本控制** — 跟踪 skill 的演進歷史
4. **協作學習** — 在不同 session 之間共享學習成果

---

*此 skill 讓 Hermes 從「工具」进化為「伙伴」——理解你的工作方式，主動提供幫助。*