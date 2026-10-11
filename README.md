# JUHJUHX AGENT-SKILLS
## Agent Skills v3.0.0 — Personal Tool Master（發布候選）

以 **using-superpowers** 為母技能的輕量跨 Agent 工作流程層：先理解任務，metadata-first 找相關技能，核對當次宿主工具，再形成小型工作封包、執行與驗證。長任務用 TASK／PLAN／STATE 接棒。不需要資料庫、daemon 或權限服務。

**Skills guide the agent. The host controls execution. Router failure must never disable native tools.**

```text
任務 → using-superpowers → 技能 metadata + 實際工具 + 專案上下文
                        → Compact RoutePacket → 宿主執行 → 驗證
長任務                  → TASK / PLAN / STATE → 下一工作階段
Router 故障             → 手動路由；原生工具由宿主權限控制
```

## 公開範圍

本候選打包 **14 個核心技能**（14 個一般 SKILL.md、14 個 metadata-ready records、14 個可安裝目標），以固定上游 Superpowers MIT 來源及 V3 母技能改寫為基礎。不是本機完整技能庫的 640／629，也不再宣稱 238 個公開技能。

使用者已決定先縮小公開範圍：其他未完成來源／授權／資產核查的材料，以及 26 個外部／失效 symlink，不納入本次快照；本次發布工作不更動你的原始本機庫；安裝器拒絕 dirty 工作樹。其他使用者若將乾淨舊版 checkout 明示更新到精簡版，Git 會移除排除的 tracked 檔案，應先阅读遷移說明。沒有把第三方內容改成 JuhJuhX 的 MIT。PowerPoint 受限制材料亦已排除。**Git 舊歷史仍保有既有內容，排除新版檔案不會清除歷史風險。** 詳見 [授權範圍](docs/授權範圍.md)、[第三方 notice](THIRD_PARTY_NOTICES.md) 及 [來源清單](docs/第三方來源與授權.json)。

## 開始使用

這是 release branch／PR 候選；`main` 及正式 v3.0.0 tag 必須在後續獨立驗收後才更新。

先用乾淨候選 clone 嘗試母技能與 helper，不更動既有安裝：

```sh
git clone --branch release/personal-tool-master-v3 https://github.com/juhjuhx/agent-skills.git agent-skills-v3
cd agent-skills-v3
python3 runtime/skills-router/tool_master.py route   '除錯：重現排序錯誤，最小修正並驗證' --root . --host generic --profile guided
```

在當前 Agent 載入 `using-superpowers/SKILL.md`，再說：

```text
using-superpowers：讀取這個專案的狀態，找出相關技能與實際工具，完成下一項工作並驗證。
```

正式合併後，乾淨 HOME 可執行 `bash install.sh --minimal`。已有 dirty checkout 會拒絕更新，以免覆蓋你的技能；請使用獨立 clone，詳見 [安裝與使用](docs/安裝與使用.md)。

- `--minimal`：3 個核心技能（母技能、systematic-debugging、verification-before-completion）。
- `--default`／`--all`：此精簡快照的全部 14 個技能；不會預載所有正文。
- `--category essential,coding`：沿用分類選擇介面；本版本只打包這兩類。
- `--opencode-advisory`：另行 opt-in adapter 與可選「工具大師V3」primary；不改全域 model／default-agent／permissions，不覆寫既有插件。

## 技能、工具與上下文

最多 20 個候選；guided／normal／high 通常最多選 3／5／8 個足夠技能，簡單任務可以更少。只讀當前需要的正文與 references。路由使用 metadata／詞彙啟發式，不保證所有自然語句都被分類正確；無匹配時沿用母技能與手動小流程。RoutePacket 包含 TASK／SKILLS／TOOLS／CONTEXT TO READ／WORKFLOW／DONE WHEN。

READ／SEARCH／PATCH／SHELL／TEST／WEB_SEARCH 等抽象能力，只映射到當次真的暴露的工具；示例名稱不是可用證明。專案知識使用既有檔案、AGENTS.md、README、source、tests、history。需要才用宿主現有 web／GitHub／MCP 搜尋，沒有網路工具就如實說明。V3 不額外提供搜尋引擎，也不攔截工具權限。

## 驗證範圍與限制

| 宿主 | 已有證據 | 限制 |
|---|---|---|
| OpenCode | 本機 MiMo free 曾完成研究、debug、文件式新 session 續接；advisory/native-tools 回歸 | 不保證每個版本或 provider；公開精簡技能集不是這些歷史模型測試的原始環境 |
| Codex | 本機 native exec／patch／test 映射 | 未完成全面弱模型測試 |
| Claude Code | advisory 格式與 failure fallback contract tests | live E2E 未完整驗證；不預設安裝 hook |
| Hermes／DSH | 工具名稱／能力 mapping 知識 | live E2E 未完整驗證 |

7B／9B／12B 尚未全面驗證。143423→20075 的首輪輸入縮減是歷史單 fixture；另一次輸入 99272，必要 native tools 完成但完整 model run timeout。**不承諾固定 86% token 節省。** 新鮮公開測試見 [發布驗收](docs/發布驗收.md)。完整本機資料與 provider 設定不打包。

## 開發與驗證

```sh
python3 scripts/build_v3_catalog.py --check
python3 -m unittest discover -s runtime/skills-router/tests -p 'test_*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test runtime/skills-router/tests/test_v3_advisory.mjs
```

[架構](docs/architecture/PERSONAL_TOOL_MASTER_V3_FINAL.md) · [遷移／回復](docs/發布與回復.md) · [變更紀錄](CHANGELOG.md)

## English quick start

Personal Tool Master is an advisory workflow layer, not another agent runtime. Load `using-superpowers`, discover relevant skills and actual host tools, gather context when needed, execute a compact plan, and verify. Long tasks resume from TASK / PLAN / STATE.

This release candidate bundles 14 verified-source core skills. Other unverified third-party materials are excluded from this snapshot, without changing existing local installations or rewriting history. The root MIT covers only the original V3 files listed in the license scope; Superpowers material retains Jesse Vincent's MIT notice.

Clone the release branch to try the helper. After independent merge verification, clean installations can use `bash install.sh --minimal`; the optional OpenCode advisory adapter requires `--opencode-advisory`. Dirty checkouts and existing plugins are preserved. Native skills work without the plugin. Windows, all hosts, and small local models are not universally qualified.
