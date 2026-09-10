# AGENT SKILLS MATRIX v3
# 下一步提案：TARGETED CODEX EFFORT EVIDENCE RECOVERY

Repository:
juhjuhx/agent-skills

Current phase result:
CODEX_CONTROLLED_EXPERIMENT_BLOCKED

本文件只是下一步提案，不要在 Phase 3F 內執行。不要開始 Phase 4，不要修改
Stage Router weights，不要做 model-effect experiment，不要追逐新的 runtime，
也不要安裝或重新 authentication 任何 runtime/model/provider/MCP/dependency。

============================================================
0. PURPOSE
============================================================

Phase 3F 已完成 controlled-effort harness、route/bundle reuse、sanitized
LiveExecutionRecord 與安全檢查，但第一個 H01 cell 在 model output 前因
provider transport 不可達而阻塞。這不是 effort 品質結論。

下一次只恢復已授權的 Codex provider transport，然後補跑精確缺少的 cells；
不要重做 architecture。

============================================================
1. FIRST CHECK — PROVIDER RECOVERY ONLY
============================================================

先重新確認：

- `codex --version` 仍為 `codex-cli 0.153.4`；
- release contract 仍為 `rust-v0.153.4@3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`；
- 已授權 explicit model `gpt-5.6-luna` 仍可安全 pin；
- `codex doctor --json --summary` provider reachability 已恢復。

不可：購買 credits、改 provider、登入新帳號、加入 credentials、放寬 sandbox、
使用 interactive approval 或 dangerous bypass。若 provider 仍不可達，停止並
保留 `CODEX_CONTROLLED_EXPERIMENT_BLOCKED`；不要建立 3F.1 diagnostic rabbit hole。

============================================================
2. PRESERVE CONTROLS
============================================================

沿用 Phase 3F 已驗證的：

- 一個 immutable H01 route/bundle 與一個 immutable H03 route/bundle；
- explicit model、effort only as changed variable；
- selected skill IDs/digests、TaskSpec/fixture/permission/instruction digests；
- `--ephemeral`、`--ignore-user-config`、`--ignore-rules`、`--config approval_policy=never`；
- same sandbox/tool/MCP boundary；
- shell=False、stdin=DEVNULL、finite timeout、fresh isolated fixture。

Stage Router 不得因 LOW/MEDIUM 分別重跑而改變 selected skills。Router defects
（例如 maps/brandkit/permission-tuner）另記 backlog，不在 recovery task 修正。

============================================================
3. ONLY MISSING CELLS
============================================================

恢復後使用原 schedule 的未完成部分；這個新的 recovery task 最多六次 live invocation；
已失敗的 provider probe 不得被冒充為 repetition：

- H01 LOW：補足至 n=2；
- H01 MEDIUM：補足至 n=2；
- H03 LOW：n=1；
- H03 MEDIUM：n=1；
- 不跑 H09；
- 不跑 HIGH/XHIGH；
- 不跑第二個 model。

仍使用 interleaved order，並記錄實際 n、執行順序與 confounders。若 provider、
measurement integrity、fixture isolation 或 quota 任何一項再次失敗，立即停止。

============================================================
4. EFFECT BOUNDARY
============================================================

只有同一 Codex runtime、同一 explicit model、同一 task/fixture/route/skills/
permissions/tools/context，且只改 `model_reasoning_effort`，才可分類
`REASONING_EFFORT_EFFECT`。不執行 `MODEL_EFFECT`；跨 runtime 只能是歷史上的
configuration context。

LOW/MEDIUM 結果只可產生 evidence-only `RoutingPolicyProposal`，不能修改 active
policy、Stage Router weights 或 runtime config。

============================================================
5. ACCEPTANCE
============================================================

需要：

- H01 LOW/MEDIUM 各至少 n=2；
- H03 LOW/MEDIUM 各至少 n=1；
- token/model-call/tool-call/cost 只在 installed semantics 證實時填值；
- terminal outcome 由 tests/artifact/acceptance evidence 獨立判定；
- security、permission、skill、route digest 控制無 material confounder；
- readiness 分開回報 intra-runtime / cross-runtime。

若 H01 與 H03 仍無法完成 paired observations，回報
`CODEX_CONTROLLED_EXPERIMENT_INCONCLUSIVE` 或 `CODEX_CONTROLLED_EXPERIMENT_BLOCKED`
並停止；不要把啟動成功當 model quality。

============================================================
6. NEXT DECISION
============================================================

若 controlled effort evidence 成立且 intra-runtime gate READY，才可另提
`PHASE 4A — CODEX CONSERVATIVE EFFORT ROUTER MVP`。該 phase 仍須 deterministic、
measured、保守 escalation、無 adaptive learning。Cross-runtime readiness 仍須
另外取得真實 runtime evidence。
