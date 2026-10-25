---
name: skills-curator-cron
description: "Weekly cron job to audit and optimize skills library. Run automatically to check skills integrity."
version: 1.0.0
author: Agnes + Hermes
license: MIT
tags: [automation, cron, skills, maintenance]
related_skills: [skill-optimizer, auto-learn, skill-authoring]
---

# Skills Curator Cron Job

每週自動檢查和優化 skills 庫。

## 功能

1. **完整性檢查** — 統計 skills 數量
2. **描述長度檢查** — 識別過長或過短的描述
3. **結構檢查** — 檢查是否有 related_skills、When to Use 等
4. **生成報告** — 保存到 ~/.hermes/logs/curator/

## 執行方式

```bash
~/.local/bin/skills-curator audit
```

## 定時設定

每週一凌晨 2:00 自動執行。

## 輸出位置

- 日誌：`~/.hermes/logs/curator/YYYYMMDD-HHMMSS.log`
- 報告：`~/.hermes/logs/curator/report-YYYYMMDD.md`

## 與 Auto-Learn 協同

當 curator 發現問題時，可以：
1. 自動建議優化（使用 skill-optimizer）
2. 記錄到 auto-learn 的學習日誌
3. 在下個 session 中主動提醒用戶

## 注意事項

- 此 cron job 是 local-only，不會主動通知用戶
- 如需通知，可設置 deliver='telegram' 或 deliver='all'
- 報告會保存到日誌目錄，可隨時查看
