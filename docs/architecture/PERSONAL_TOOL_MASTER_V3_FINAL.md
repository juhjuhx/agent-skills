# Personal Tool Master V3：公開版架構與驗收摘要

本文件為公開安全摘要；不包含本機原始 logs、session IDs、HOME 絕對路徑、provider 設定或資料庫。私人完整證據留在原工作環境。

## 產品

using-superpowers 是單一母技能；輕量 helper 以 metadata 選候選／技能，形成 TASK、SKILLS、TOOLS、CONTEXT TO READ、WORKFLOW、DONE WHEN 封包。宿主工具執行及權限仍由宿主負責。無 daemon、policy server、SQLite、TaskLease／ActionGrant、TTL 或新的全域 tool gate。

```text
使用者 → using-superpowers → metadata / actual tools / project context
                         → compact RoutePacket → host-native execution
                         → verification → TASK / PLAN / STATE (long tasks)
故障 → 手動 metadata／一般小流程 → 宿主原生工具仍由原權限控制
```

最多20 candidates；guided／normal／high通常最多3／5／8 selected。候選名稱不是強制 workflow，僅載入相關正文。ToolMap 使用本次已暴露 names／description／schema；host hints 不等於 available 或授權。沒有網路工具就不假稱搜尋成功。

## 公開库分母與權利範圍

2026-10-11 使用者授權縮小公開範圍。此快照為14個一般 root-directory SKILL.md、14個metadata-ready records、14個分類可安裝目標。保留 V3 核心原創及固定 Superpowers MIT 技能；其他未核實授權內容與26外部symlink不打包。本機完整技能庫／active入口保持不動。逐檔来源见 docs/第三方來源與授權.json；排除只作用新版，不清除歷史。

## 宿主驗證範圍

| 宿主 | 本機既有證據 | 未證明 |
|---|---|---|
| OpenCode1.18.34 + oh-my-openagent5.1.19 | 歷史MiMo免費模型 research/debug/文件式新session續接；native skill/read/glob/bash completed；V3 gate無權威 | 所有版本／所有provider／每次autoload／穩定低token |
| Codex | 真實 exec_command/apply_patch/test 映射 | 第二個弱模型或所有Codex版本 |
| Claude Code | advisory格式／failure fallback contract tests；未自動裝hook | live E2E |
| Hermes／DSH | tool schema/hints與部分mapping測試 | live E2E／免費provider保證 |

純Skill入口適用於宿主能載入Skill且模型能tool-call的環境，不保證任何7B/9B/12B都成功。

## 歷史測試與誠實性能說明

本機前次完整Python242/242、Node21/21；入口收尾focused15/15、最後獨立5/5。這些是歷史驗收，不是公開隔離工作樹新鮮測試結果。新鮮公開結果另見發布驗收文件。

單fixture曾143423→38489→20075首輪input（metadata＋primary不同）；後一次input99272、cache-read16384，必要工具完成後180秒摘要timeout。不能宣稱固定86%節省、穩定host latency或8K上下文支援。packet1234characters/1832bytes與JSON4389bytes不是token counts；本機p50約63.42ms/p95約66.86ms只測offline route/render/serialize。

MiMo free曾真正websearch×2/webfetch×2、code修改／tests、新session讀STATE/PLAN；不是全宿主或任意大型repo整合保證。OCR曾因401 invalid x-api-key失敗，未當零問題PASS。

## 入口缺陷修正

最終advisory已修引用catalog誤改、session counter eviction ABA舊回應、tool.description引用誤縮。僅完整已識別原生metadata格式可縮，未知／混合文字保持；unique request identity不復用。tool.execute.before明確no-op；parameters/execute/permissions不改，錯誤或stale只降級。

## 使用／續接與邊界

先說 `using-superpowers：<任務>`，native Skill 或 READ 載入母技能；需要helper才執行route。重要長任務存TASK/PLAN/STATE，重啟讀現物再續接，不是自動Watchdog或模型調度器。

公開版只封裝既有V3與已核實來源技能。舊policy/enforcing不打包，不新造安全平台。Phase A只push/PR；merge/tag/Release由獨立Phase B進行。架構完成不等於正式release已發布。

上表與歷史測試不是本次14技能公開快照的新鮮模型E2E；本次release regression與安裝結果见 docs/發布驗收.md。
