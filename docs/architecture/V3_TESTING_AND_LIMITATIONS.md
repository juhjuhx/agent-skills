# V3 測試與限制

本文件區分程式契約、候選驗收、歷史模型實測與尚未驗證項目。測試通過只證明其實際範圍；不能從 helper 或 fixture 推定所有宿主、provider、小模型、context window 或作業系統都成功。

## 測試來源與目前可核對內容

| 測試來源 | 實際檢查的行為 | 沒有證明的範圍 |
|---|---|---|
| [test_tool_master.py](../../runtime/skills-router/tests/test_tool_master.py) | 中英文 metadata 排序、PR 否定語句、產品／數字雜訊、selected digest、實際名稱描述 mapping、fallback、安全路徑、CLI、長任務提示與封包 fixture 大小 | 語意完整性、所有真實技能庫／工具、完整任務成功 |
| [test_claude_slim_hook.py](../../runtime/skills-router/tests/test_claude_slim_hook.py) | 缺少 router／錯誤 payload 不阻擋；成功只有 advisory additionalContext | 真實 Claude session、所有 hook 版本、runtime 逾時保證 |
| [test_v3_advisory.mjs](../../runtime/skills-router/tests/test_v3_advisory.mjs) | missing／throw／deny／stale／wrong-session／malformed、timeout、原生 args／schema 不變、已識別 catalog、未知混合文字、session 隔離及舊回應淘汰 | 真實 OpenCode provider 全程完成、所有 catalog 版本、SVG／介面效果 |
| [test_v3_install.py](../../tests/test_v3_install.py) | disposable HOME、profiles、dirty／ignored／wrong origin、nonmanaged 保留、optional adapter、storage failure 回復與 retry、stdin bootstrap | 真實 HOME 的任意狀態、並行／斷電、Windows symlink、網路 clone 的 transaction |
| [build_v3_catalog.py --check](../../scripts/build_v3_catalog.py) | index／lock 與當前來源的確切生成內容一致 | 授權／秘密／tracked 身分自動核查 |
| [CI workflow](../../.github/workflows/personal-tool-master-v3.yml) | Ubuntu 的 Python 3.12、Node 22、catalog／Python／Node／shell／diff checks | 只有 workflow 檔案不能宣稱該次 CI PASS |

Node 的 no-op hook 測試實際呼叫 7 類名稱的原生工具入口，核對呼叫資料沒有被修改；來源禁止語句掃描只是補充。Python 的 SQL fixture 明確確認 read-only SQL `execute` 不被誤認成 filesystem 或 shell 工具。這些具體行為是 advisory 邊界的證據，不是一般安全或權限實作的替代品。

## 2026-10-12 公開候選驗收紀錄

[發布驗收](../發布驗收.md) 保存了隔離公開快照的當時結果：router／Claude Python 29/29、installer 18/18、Node 15/15；catalog 為 14 physical／14 metadata-ready／14 installable。來源表核對 53 檔，14 個技能均有完整 MIT notice；另有 installer smoke、語法、format／lint 與 current-tree heuristic 掃描。

當時本機為 Python 3.14.5、Node 26.10.0、Ruff 0.15.16、macOS。它不是本次文件修改的新鮮執行結果，也不替代最終 commit 的 remote CI。原紀錄的獨立審查批准當時 Phase A 的 commit／push／PR；正式收束依 [發布與遷移](V3_RELEASE_AND_MIGRATION.md) 核對最新 PR checks、文件審查與發布物件。

沒有暴露 LSP diagnostics 工具時，不宣稱 LSP 通過。文件 grammar／相對連結檢查與 Mermaid 視覺 rendering 也應分開記錄。若只解析 Mermaid grammar，不把它寫成 SVG、DOM sanitizer 或畫面渲染驗證。

## 宿主與模型證據

| 類型 | 已有紀錄 | 正確解讀 |
|---|---|---|
| OpenCode 歷史 live | OpenCode 1.18.34／oh-my-openagent 5.1.19／`opencode/mimo-v2.6-flash-free`；研究中真正 search 2 次與 fetch 2 次、debug 修改與 tests、新 session 讀 STATE／PLAN 續接 | 歷史個人環境的部分成功，沒有重做本次公開 14 技能模型 E2E |
| Codex 歷史 live mapping | 真實 exec_command／apply_patch／test 映射 | 不代表所有 Codex 版本或全面弱模型測試 |
| Claude | 格式與失敗 fallback contract | live E2E 尚未完整驗證；hook 不預設安裝 |
| Hermes／DSH | 工具 mapping 知識與部分 fixture | live E2E 尚未完整驗證；沒有免費 provider 保證 |
| 小模型 | 7B／9B／12B 尚未全面驗證 | guided 是設計意圖，不是模型能力證明 |
| 舊 enforcing 故障 | 歷史 `SKILL_CATALOG_STALE` 曾阻擋 read／skill／bash／glob | 本輪未重演，不計入 fresh reproduction |

舊個人完整測試曾記錄 Python 242/242、Node 21/21、入口 focused 15/15 與最後獨立 5/5。這些使用不同範圍，不能加進公開 29＋18／15 的分母。外部審查 lane 的額度／provider 失敗亦不能計為完成；完整歷史細節留在當時 [驗收紀錄](../發布驗收.md) 與私人證據，不複製 raw logs 或憑證。

## 性能與 token 限制

歷史單一 fixture 的首輪 input 曾為 `143423 → 38489 → 20075`，其中 metadata 與 primary 條件不同。不能把約 86% 的一次縮減寫成固定節省、所有任務或免費模型的承諾。

另一次歷史 input 為 99272、cache-read 16384；必要 native tools 已完成，但整段模型摘要在 180 秒 timeout。因此「工具成功」與「整段 model run 完成」需分開。歷史 packet 1234 characters／1832 bytes、JSON 4389 bytes 不是 token counts；offline route／render／serialize 的 p50 約 63.42 ms／p95 約 66.86 ms 不包含 host／provider latency。費用與全任務 token 未全面測量；沒有 8K 上下文保證。

## 從實碼讀出的限制

下表以 [helper](../../runtime/skills-router/tool_master.py)、[OpenCode adapter](../../runtime/skills-router/adapters/opencode/skills-router.js) 與 [Claude hook](../../runtime/skills-router/adapters/claude/skills-router-hook.py) 為準。Python 的字元長度、JavaScript 的字串長度與 bytes 分開；它們都不是 token 預算。

| 層次 | 現有數值 | 實際效果 |
|---|---|---|
| catalog 檔案 | 最大 16 MiB | 超過則 metadata fallback；不是總記憶體上限 |
| fallback roots | 最多前 64 根 | 缺少設定採 `.`；不遍歷任意 HOME |
| fallback 訪問計數 | 設定夾在 1～4096，預設 4096 | 直接子項訪問上限；各根先建立排序列表，因此不是硬性總 I/O／wall-clock 限制 |
| frontmatter | 設定夾在 1～65536 bytes，預設 65536 | bounded header；需完整 closing marker，不讀全庫正文 |
| selected 正文 | 每份最大 4 MiB | 超過／不可用只標 BODY_UNAVAILABLE；其他工具不被禁用 |
| 候選 | 至多 20 | 排名後截取；不要求至少 10 個 |
| selected | guided 3／normal 5／high 8；simple 至多 3 | 只取正分；可以更少或零個；不保證涵蓋所有領域角色 |
| task 摘要 | 超過 2400 字元，保留前 1800＋後 500＋摘要提示 | 原始需求仍以訊息／TASK 為準；丟失的中段不能被當成已理解 |
| task 中檔案片段 | 取前 6 個，再去重 | `context_to_read` 的建議；沒有讀取檔案或完整中文路徑辨識保證 |
| tool inventory | 前 512 項 | 名稱／描述啟發式；後續工具需 Agent 回到真實 inventory 查閱 |
| 每種能力呈現 | 前 8 個 available，另記 additional_count | 不把較後的同能力工具視為被禁用 |
| 文字診斷 | render 顯示前 10 筆 | JSON 保留 diagnostics；不是總輸出大小限制 |
| OpenCode task 文字 | LIMIT 16000；前 256 parts | 只保留 text parts；JavaScript 字串長度單位，不是 UTF-8 bytes |
| OpenCode session ID | 非空字串，長度至多 256 | 無效 ID 不處理建議，不能據此推定工具受阻 |
| OpenCode helper stdout | 至多 32768 bytes | 超限 kill child 並 fallback |
| OpenCode 建議文字 | packet JSON 截至 16000 字串單位，另有前綴 | 是注入文字，不是可重新解析的完整 JSON 保證 |
| OpenCode child timer | 2000 ms | 預設 helper child 逾時 kill／fallback |
| OpenCode outer timer | 預設 2200 ms | 等待 routePreflight 的 timeout；不保證任意注入 callback 會被取消 |
| OpenCode Map | pending／revisions 各最多 100 筆 | 淘汰建議 cache；unique Symbol 避免被淘汰舊回應覆寫新建議 |
| Claude input | `read(32769)`，超過 32768 字元則空結果 | 文字長度，不是 byte bound；仍需 stdin 完成讀取 |
| Claude context | 前 12000 字元 | 成功注入的上下文上限，不是完整任務／token 保證 |
| Claude／helper CLI timeout | 沒有內建總執行 timeout | 測試 harness 的 10 秒等設定不能代替 runtime 限制 |

CLI 直接讀 stdin 與 `--tools-json` 檔案沒有總大小限制；catalog metadata 內容可以很長。helper 會對有效 metadata 排序，並非只先讀 20 個 record。因此「少量封包」是實作策略與 fixture 測試結果，不是任意輸入下的固定 latency、記憶體或輸出上限。

## 安裝、授權與平台限制

installer 的檔案切換失敗回復與正常重選備份已由 disposable fixture 驗證；clone／pull 不在 transaction 中，沒有並行鎖、停電恢復或任意外部修改保證。八個宿主目錄的 link 支援也不代表八個宿主都做了 live E2E。Windows symlink、所有 Linux 版本與其他 host catalog 格式未全面驗證。

current-tree heuristic 掃描的零發現不是完整 secret 或法律保證。排除新版的受限制內容不會清除 Git 歷史，未使用、驗證或撤銷歷史疑似 credentials。來源與權利邊界見 [授權範圍](../授權範圍.md)、[第三方通知](../../THIRD_PARTY_NOTICES.md) 與 [發布與遷移](V3_RELEASE_AND_MIGRATION.md)。

## 可重跑的公開契約命令

請在乾淨的隔離公開 checkout 執行；installer 測試僅使用 disposable HOME。這些命令不證明模型 live E2E，也不構成正式發布。

```sh
python3 scripts/build_v3_catalog.py --check
python3 -m unittest discover -s runtime/skills-router/tests -p 'test_*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test runtime/skills-router/tests/test_v3_advisory.mjs
bash -n install.sh
sh -n runtime/skills-router/adapters/claude/claude-user-prompt.sh
git diff --check
```

正式收束另核對 fresh CI、文件相對連結、來源／通知、最終 commit 與 tag／Release 身分；實際結果與待完成欄保存在 [發布與遷移](V3_RELEASE_AND_MIGRATION.md)。不為了顯示完成而刪除失敗或換掉驗收分母。
