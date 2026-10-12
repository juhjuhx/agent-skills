# JUHJUHX AGENT-SKILLS

## Agent Skills v3.0.0 — Personal Tool Master

以 **using-superpowers** 為母技能的跨 Agent 工作流程層：先理解任務，metadata 先行找相關技能，核對當次宿主工具，再安排小流程、執行並驗證。重要長任務以 TASK／PLAN／STATE 續接。

V3 程式與精簡封裝已由 [PR #27](https://github.com/juhjuhx/agent-skills/pull/27) 合併 main，merge commit 為 `a570dd639d06b8b7d164493bac98f01a55cdbc6f`。本次架構文件與正式 tag／GitHub Release 依 [發布與遷移](docs/architecture/V3_RELEASE_AND_MIGRATION.md) 的收束流程核實；實際發布狀態以 GitHub Release 與遠端 tag 身分為準，不從版本標題推定已發布。

**技能引導 Agent；宿主控制執行與權限。Router 故障不禁用原生工具。**

```text
任務 → 母技能 → metadata／實際工具／需要的專案 context
              → RoutePacket 建議 → 宿主執行 → 成果驗證
重要長任務    → Agent 保存 TASK／PLAN／STATE → 新 session 核對後續接
路由故障      → metadata fallback 或手動小流程 → 宿主權限仍有效
```

## 公開範圍與授權

公開快照打包 **14 個核心技能**：14 個普通根目錄 SKILL.md、14 個 metadata-ready record、14 個分類可安裝目標。`full` 是此快照的全部 14 個；個人完整技能庫的分母由本機盤點，與公開範圍不同。

來源為固定 Superpowers MIT 上游及有權授權的 V3 原創；未核實來源／授權／資產材料與 26 個既有外部／失效 links 不納入快照。原個人庫、dirty 工作、legacy DB 與私人封存保持原位。乾淨舊版 checkout 明示更新到精簡版時，Git 會移除新版排除的 tracked 材料，更新前需保存要保留且可合法使用的內容。

根 MIT 只涵蓋 [授權範圍](docs/授權範圍.md) 明列的 V3 原創檔案與新寫文件；Superpowers 保留 Jesse Vincent 的完整 MIT notice。見 [第三方通知](THIRD_PARTY_NOTICES.md) 與 [逐檔來源](docs/第三方來源與授權.json)。新版排除 PowerPoint 等受限制材料不會清除 Git 歷史；歷史受限制內容與疑似憑證風險仍需個別處理，沒有重寫歷史或撤銷憑證。

## 開始使用

先在獨立乾淨路徑取得公開 repo，不覆寫個人 dirty 技能庫：

```sh
git clone https://github.com/juhjuhx/agent-skills.git agent-skills-v3
cd agent-skills-v3
python3 runtime/skills-router/tool_master.py route \
  '除錯：重現排序錯誤，最小修正並驗證' --root . --host generic --profile guided
```

載入 `using-superpowers/SKILL.md`，再給出任務：

```text
using-superpowers：讀取這個專案的狀態，找出相關技能與實際工具，完成下一項工作並驗證。
```

需要建立宿主入口時，乾淨 HOME 可執行：

```sh
bash install.sh --minimal
```

- `--minimal`：母技能、systematic-debugging、verification-before-completion，共 3 個。
- `--default`／`--all`：此公開快照全部 14 個；正文仍按需載入。
- `--category essential,coding`：使用目前打包的兩類。
- `--opencode-advisory`：另行 opt-in plugin 與可選「工具大師V3」primary；不改全域 model、default agent、permissions。

既有 dirty／untracked checkout 與非 managed 入口會拒絕更新；既有宿主目錄與 plugin 不覆寫。已有乾淨 checkout 預設不 pull，明示 `--update` 才在額外條件下 ff-only 更新。完整操作與回復邊界見 [安裝與使用](docs/安裝與使用.md) 與 [發布與遷移](docs/architecture/V3_RELEASE_AND_MIGRATION.md)。

## 技能、工具與上下文

helper 使用 metadata 詞彙分數與排序修正，最多 20 候選；guided／normal／high 最多選 3／5／8 個正分技能，簡單任務至多 3 個，也可以零個。只檢查 selected 正文 digest，不預載全庫。它不提供 embedding、模型 reranker、web 搜尋引擎、daemon、資料庫或新的 tool gate。

能力映射只根據本次傳入的工具名稱與描述；參數、可用性與權限仍需核對當次 schema。OpenCode adapter 預設只傳 task 給 helper，工具名稱提示不等於已發現工具。helper 不執行工具，也不自動寫入 TASK／PLAN／STATE。

## 架構文件

| 文件 | 內容 |
|---|---|
| [系統架構](docs/architecture/V3_SYSTEM_ARCHITECTURE.md) | 原始需求、技能庫到 advisory 的演化、整體與請求流程 |
| [元件參考](docs/architecture/V3_COMPONENT_REFERENCE.md) | 確切檔案、helper 介面、metadata 排序與 digest |
| [工作流程與工具映射](docs/architecture/V3_WORKFLOW_AND_TOOL_MAPPING.md) | 模式、宿主、真實工具、adapter 與故障降級 |
| [儲存與狀態](docs/architecture/V3_STORAGE_AND_STATE.md) | JSON、task 狀態、記憶體 cache、legacy SQLite 與私人證據 |
| [測試與限制](docs/architecture/V3_TESTING_AND_LIMITATIONS.md) | 契約測試、歷史模型案例、數值上限與未驗證項目 |
| [發布與遷移](docs/architecture/V3_RELEASE_AND_MIGRATION.md) | 公開／個人分界、Git 隔離、正式收束與備份回復 |

## 驗證範圍

OpenCode 的歷史 MiMo 免費模型研究、debug 與文件式新 session 續接曾完成；Codex 有真實 exec／patch／test 映射。Claude、Hermes、DSH 的 live E2E 尚未完整驗證，本次公開 14 技能也未重做模型 E2E。7B／9B／12B 未全面測量。

歷史單 fixture 的 token 縮減不保證固定 86% 節省；另一次必要 native tools 完成後，整段模型摘要在 180 秒 timeout。公開候選的 29／18 Python 與 15 Node 測試、來源／安裝結果保留在 [2026-10-12 驗收紀錄](docs/發布驗收.md)。最終文件、CI、tag／Release 查驗與上述歷史結果分開。

## 維護命令

```sh
python3 scripts/build_v3_catalog.py --check
python3 -m unittest discover -s runtime/skills-router/tests -p 'test_*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test runtime/skills-router/tests/test_v3_advisory.mjs
```

[發布與回復入口](docs/發布與回復.md) · [變更紀錄](CHANGELOG.md) · [GitHub Releases](https://github.com/juhjuhx/agent-skills/releases)

## English quick start

Personal Tool Master V3 is a lightweight advisory skill and workflow layer. Load `using-superpowers`, discover a small set of relevant skills and actual host tools, gather project or web context when useful, execute, and verify. Long tasks resume from TASK / PLAN / STATE files maintained by the agent.

The public edition includes 14 verified-source core skills. Clone this repository into a clean directory, then use `bash install.sh --minimal`; add `--opencode-advisory` only if you want the optional OpenCode adapter. Dirty installations and existing plugins are preserved. Native skills work without that adapter. The host controls execution and permissions; router failure cannot disable native tools.

Support is evidence-based: historical OpenCode/MiMo tasks and Codex tool mapping were demonstrated, while Claude/Hermes/DSH live E2E, all small local models, Windows, and stable token savings remain unqualified. Third-party MIT notices remain intact; removing restricted content from this snapshot does not remove historical risks. See the architecture, installation and licensing documents above.
