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

公開技能庫分兩層（M4-P8 起）：

- **14 個核心技能**：根目錄 `<skill>/SKILL.md`，來源為固定 Superpowers MIT 上游（commit `8ca22dba…`）與有權授權的 V3 原創，metadata-ready、可獨立安裝。
- **450 個補充可攜技能包**：`skills/<slug>/SKILL.md`，從本機技能庫通過授權與安全 gate 後打包，附帶 `NOTICE`／`LICENSE`、必要 `scripts/` `references/` `assets/`。
- **合計 464 個技能套件**（14 核心＋450 補充），**依名稱可安裝 461 個**：`requesting-code-review`、`systematic-debugging`、`test-driven-development` 三個補充 slug 與根目錄核心同名，根目錄版本優先解析；三者全部 464 份 SKILL.md 都在盤上，只是這 3 個補充版不該被獨立安裝為技能。

機器可讀清單：[`catalog.json`](catalog.json) ＋ [`catalog.lock.json`](catalog.lock.json)（每個 slug 的 SHA-256 鎖）；人類摘要見 [Skills Catalog](docs/SKILLS_CATALOG.md)。

未核實授權（LICENSE_UNKNOWN）、copyleft（GPL/AGPL）未獲明確授權、以及含真實憑證或私人資料的技能，**不**進入公開 repo，只在本地 excluded manifest 追蹤（見 [Skill Provenance](docs/SKILL_PROVENANCE.md)）。乾淨舊版 checkout 明示更新到新版時，Git 不會移除這些未發布材料；更新前請自行保存要保留的內容。

根 MIT 只涵蓋 [授權範圍](docs/授權範圍.md) 明列的 V3 原創檔案與新寫文件；Superpowers 保留 Jesse Vincent 的完整 MIT notice。見 [第三方通知](THIRD_PARTY_NOTICES.md) 與 [逐檔來源](docs/第三方來源與授權.json)。Git 歷史中既有受限制內容與疑似憑證風險不因本次發布清除，也沒有重寫歷史或代為撤銷憑證。

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
bash install.sh --minimal                 # 3 個母技能
bash install.sh --all --host hermes       # 全部 464 個套件（461 個依名稱可安裝）
bash install.sh --list                    # 列出 catalog 全部技能
```

- `--minimal`：母技能、systematic-debugging、verification-before-completion，共 3 個。
- `--default`：essential + coding 分類（14 核心技能）。
- `--all`：全部公開技能（464 套件、依名稱 461 個可安裝，見上方衝突說明）；`--host hermes|dsh|opencode|claude|codex|gemini` 指定宿主，或預設 `--host auto` 依既有目錄自適應。
- `--category essential,coding,published-extra`：使用目前打包的分類。
- `--skill name1,name2`：依 catalog slug 安裝特定技能（可與上述合併）。
- `--dry-run`：解析安裝意圖、只輸出會做什麼；`--rollback`：還原到前一次 backup。
- `--verify`：驗證已安裝技能 symlink 是否全部解析到 SKILL.md。
- `--update`：ff-only 更新既有乾淨 checkout。
- `--repo-local <path>`：以本機 checkout 替代遠端 clone（clean-room 測試 / 發布前驗證）。
- `--opencode-advisory`：另行 opt-in plugin 與可選「工具大師V3」primary；不改全域 model、default agent、permissions。

跨宿主安裝：

| Host | 命令 | 行為 |
|---|---|---|
| Hermes | `bash install.sh --all --host hermes` | 選擇性 per-skill symlink 到 `~/.hermes/skills/`，**不覆寫**既有技能（461 個名稱級） |
| DSH | `bash install.sh --all --host dsh` | top-level 直接子目錄 symlink，讓 DSH 非遞迴掃描能發現 |
| OpenCode | `bash install.sh --all --host opencode` | `~/.config/opencode/skills/` 整目錄 symlink 到 `~/.agents/skills-enabled` |
| Claude | `bash install.sh --all --host claude` | `~/.claude/skills/` 整目錄 symlink |
| Codex | `bash install.sh --all --host codex` | `~/.codex/skills/` 整目錄 symlink |
| Gemini CLI | `bash install.sh --all --host gemini` | `~/.gemini/skills/` 整目錄 symlink |

既有 dirty／untracked checkout 與非 managed 入口會拒絕更新；既有宿主目錄與 plugin 不覆寫。已有乾淨 checkout 預設不 pull，明示 `--update` 才在額外條件下 ff-only 更新。完整操作與回復邊界見 [安裝與使用](docs/安裝與使用.md)、[Install Hermes](docs/INSTALL_HERMES.md)、[Install DSH](docs/INSTALL_DSH.md) 與 [發布與遷移](docs/architecture/V3_RELEASE_AND_MIGRATION.md)。

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

## 實作狀態（Registry / Scout / Forge / V3 composer）

| 層 | 狀態 | 說明 |
|---|---|---|
| P0 Catalog | PASS | 640 筆 = 492 現役 + 148 私人恢復，零重疊，digest 全對 |
| P1 Registry | PASS | public / private / history 三層；provenance 錨定、license gate、symlink 阻擋、雙側路徑 redaction、rollback |
| **P2 Scout** | **PARTIAL** | 已實測：GitHub Discovery、Metadata、Candidate Staging、有界 403/429 重試（普通 403 不重試）、fail-open。**未實作且未啟用：完整 commit-SHA 捕捉、深度逐檔安全掃描、自動升級信任名單** —— 因此 Scout 不得宣稱完整自動安裝或深度安全審查 |
| P3 Forge | PASS | 遞迴界（per-parent generation、MAX_DEPTH=2、fan-out 3）、lineage cycle 阻擋、regression gate、rollback |
| V3 skill-composer | PASS | BM25 組合 + advisory fallback；不 import、不改動 `tool_master.py`；14 核心 digest 不變；advisory 非阻擋、legacy enforcing 不重部署、router fallback 保持 |

公開 repo 只含 public 層與白名單代碼／測試；**private registry、history layer 與 forge-workspace 全數 gitignored 且不進入 Git**。Scout 的 candidate staging 在本機私人區完成，第三方技能不會自動啟用。

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
