# Session Closing Hook — Auto-Learn Trigger

這個 hook 在每次 session 結束時自動執行，檢查是否可以學習新的 skill。

## 執行時機
- Session 結束前
- 用戶說「結束」、「 bye 」、「下次再說」等
- 或者超過 30 分鐘沒有活動

## 檢查流程

```
1. 回顧本次 session 使用的 skills
2. 檢查是否有以下模式：
   a. 重複使用了相同的 skill 組合 ≥ 2 次
   b. 遇到了並解決了新的問題模式
   c. 創建了新的文件/配置/腳本
   d. 用戶明確表示這是「常做的」或「重要的」

3. 如果命中任意條件，執行提議：
   - 列出發現的模式
   - 詢問是否要保存為 skill
   - 如果用戶同意，立即創建
```

## 示例輸出

```
=== Session Closing: Auto-Learn Check ===

發現的模式：
1. 使用了 theater-projection-design + baoyu-imagine 組合 3 次
2. 解決了 Agnes Vision SSL 問題（已記錄在 pitfall）
3. 創建了 scene_1_1.json 模板

建議：
- 更新 theater-projection-design 的 pitfalls 章節
- 創建「agen-vision-ssl-fix」作為獨立 skill

是否要保存？ (y/n)
```

## 注意事項
- 不要過度干擾 — 只在確實有價值時提議
- 優先考慮用戶的明確指示
- 保存後更新相關 skill 的 references
