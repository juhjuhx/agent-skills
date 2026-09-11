# AGENT SKILLS MATRIX v3
# PHASE 3J — SAFE INSTALLER / GENERATOR MVP

Repository:
juhjuhx/agent-skills

Current base:
feat/v3-static-productization

Current static decision:
STATIC_PRODUCTIZATION_READY

Current live state:
CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS = NOT_READY
CROSS_RUNTIME_ROUTING_READINESS = NOT_READY

這是下一階段提案，不要在本 phase 執行。不要開始 Phase 4，不要重試 live
model execution，不要修改 Stage Router weights，不要做 adaptive routing，也
不要新增 runtime adapter。

============================================================
0. MISSION
============================================================

在 Phase 3I 已驗證的 static compiler 之上，建立最小、明確授權、可 preview 的
installer/generator MVP。它可以偵測實際 runtime、解析安全安裝目的地、產生
preview、在明確 apply 後只更新 Agent Skills Matrix 管理的檔案，並能對 managed
artifact 做可逆的 uninstall/revert。

Productization plane 仍與 execution plane 分離：

  compiler / plan / preview / apply
             不得
  invoke runtime / model / provider / MCP / plugin

============================================================
1. PRESERVE PHASE 3I CONTRACT
============================================================

沿用而不重建：

- canonical `skills/<skill>/SKILL.md` source truth；
- validated immutable `RoutingCatalogSnapshot`；
- generated + curated metadata provenance；
- `RuntimeProductStatus` 四個獨立維度；
- `InstallationPlan` 與 `GeneratedArtifactManifest`；
- `.asm-generated.json` ownership marker；
- selected-only materialization 與 `NO_SKILL_NEEDED`；
- stale digest fail-closed；
- Hermes `NOT_IMPLEMENTED` 不得產生假 adapter tree；
- `STAGE_ROUTER_PRODUCTION_READY` 不等於 live routing ready。

不要將 installer 變成 CatalogManager、RuntimeManager、Service、daemon、database
或 plugin framework。

============================================================
2. REPO TRUTH FIRST
============================================================

先核對 branch、HEAD、status 與 Phase 3I evidence：

- `docs/v3/evidence/STATIC_PRODUCTIZATION_V1.md`
- `docs/v3/evidence/PHASE3I_PRODUCTIZATION_ROUTE.md`
- `tools/v3/productization.py`
- `schemas/v3/runtime-product-status.schema.json`
- `schemas/v3/installation-plan.schema.json`
- `schemas/v3/generated-artifact.schema.json`

不要依賴 developer machine 的 executable 狀態作為 static tests 的輸入。

============================================================
3. ACTUAL DETECTION — EXPLICIT ACTION ONLY
============================================================

新增 runtime detection 只能在使用者明確執行 installer 的時候發生；不能在
import、plan、compile、validate 或 tests 中自動呼叫 runtime。

安全記錄：

- runtime ID；
- executable availability；
- observed version；
- release/source provenance；
- adapter/static/live status。

不得讀取、輸出或序列化 credentials、auth store、environment secrets、headers
或 session tokens。Unknown version 或 contract 必須 fail closed。

============================================================
4. DESTINATION DISCOVERY
============================================================

只解析與目前 runtime contract 相符的 destination class。每個 destination 必須
明確標記：

- absent；
- ASM-managed；
- user-owned；
- unknown；
- symlinked / unsafe。

拒絕：

- home root；
- 未經明確確認的 global runtime config；
- arbitrary symlink escape；
- user-owned 檔案的 force overwrite；
- 以 filename 猜測 ownership。

Installer 的預設操作仍是 preview；`apply` 必須是明確、單次、可觀測的使用者
動作。不要提供 `--force` 來繞過 ownership 或 contract checks。

============================================================
5. APPLY BOUNDARY
============================================================

只允許執行 `InstallationPlan` 已列出的、非 destructive、managed-safe operation：

- create absent generated file；
- update ASM-managed file；
- create required generated directory；
- preserve canonical skill reference；
- skip user-owned / unsupported runtime；
- warn live-blocked。

Apply 前重新驗證 snapshot、runtime contract、artifact manifest、ownership marker
與 destination state，避免 TOCTOU 式 stale output。權限、model、effort、MCP、
plugin、provider 設定不是 installer 可授予的 authority。

============================================================
6. UNINSTALL / REVERT
============================================================

只處理 marker 明確列出的 managed paths，並在刪除前要求：

- marker generator/schema/runtime/snapshot digest 相符；
- destination 仍是原 managed content；
- 沒有 user-owned 取代或衍生變更。

若任何條件不明確，改為 `CONFLICT` / `SKIP`，不要刪除。保留 preview 與 audit
summary；不要建立資料庫。

============================================================
7. TESTS
============================================================

保持既有 300 tests 綠燈，增加 focused tests：

- detection 不在 import/plan/compile 時執行；
- explicit apply 才能寫入；
- no global runtime write；
- user-owned / unknown / symlink destination fail closed；
- managed update 只更新 marker 允許的檔案；
- stale snapshot / skill / runtime contract 在 apply 前失效；
- uninstall 不刪 user-owned 或被修改的檔案；
- Hermes 不產生假輸出；
- `NO_SKILL_NEEDED` 與 selected-only materialization 不變；
- raw credentials、prompts、skill bodies、runtime output 不進 installer log；
- plan 與 preview deterministic / idempotent。

不要為了 installer 測試啟動 Codex、Claude、OpenCode、Hermes 或任何模型。

============================================================
8. LIVE TRACK STATUS
============================================================

原樣保留：

CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS = NOT_READY
CROSS_RUNTIME_ROUTING_READINESS = NOT_READY

若未來 transport 在外部恢復，另行 resume 已定義的 Phase 3G controlled effort
experiment；不要讓 installer 偷開 live benchmark 或 model policy。

============================================================
9. ACCEPTANCE
============================================================

Phase 3J 只能在下列條件全部成立時通過：

- preview 與 apply 邊界清楚；
- apply 需要明確使用者動作；
- managed ownership / conflict / revert 可驗證；
- canonical/generated boundary 未改變；
- 沒有 global config 或 credentials side effect；
- status 維度沒有被壓成單一 READY；
- static compiler 的 deterministic/stale/no-body-load tests 仍通過；
- Stage Router 與 runtime adapter 行為未被重寫。

完成後才評估是否進入真正的安裝 productization；Phase 4 仍需要獨立的 live
effort evidence，不能由 installer 結果推導。

============================================================
10. OUTPUT
============================================================

建議只新增必要的：

- safe installer/generator command；
- destination/ownership apply tests；
- preview/apply/revert evidence；
- `docs/v3/evidence/SAFE_INSTALLER_V1.md`；
- 本 prompt 對應的 route/evidence record。

不要新增另一套 skill library、runtime registry service、background process 或
model router。

STOP：本文件只描述 Phase 3J，現在不要執行它。
