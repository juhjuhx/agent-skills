# AGENT SKILLS MATRIX v3
# 下一步提案：CODEX CONTROLLED MODEL / REASONING EXPERIMENT

Repository:
juhjuhx/agent-skills

Current proposal base:
feat/v3-hermes-runtime-qualification

Current evidence decision:
HERMES_RUNTIME_BLOCKED

這是提案，不要在 Phase 3E 執行。不要開始 Phase 4，不要修改 Stage Router
weights，不要安裝 runtime/model/provider/MCP/plugin/dependency/credential，
也不要實作新的 runtime adapter。

============================================================
0. PURPOSE
============================================================

Hermes 已是目前 second-runtime search 的最後候選，但 provider/auth gate
未通過，且 `--oneshot` 會 bypass approvals。不要再建立 OpenCode、Claude 或
其他 runtime adapter。

下一個 bounded task 只研究已驗證的 Codex CLI `0.153.4`，把：

runtime + task + StageRoute + skills + tools + permissions + context

固定後，分開測量：

1. CONTROLLED MODEL EFFECT（只有 model 改變）；或
2. CONTROLLED REASONING-EFFORT EFFECT（只有 effort 改變）。

如果無法取得兩個已授權、可識別的 model，不能製造 MODEL_EFFECT；可以只
評估 reasoning effort，或明確回報 evidence 不足。

============================================================
1. PRESERVE CURRENT CONTRACTS
============================================================

沿用既有：

TaskSpec
StageRoute
CompiledExecutionBundle
CodexAdapter
CodexNativeProjection
LiveExecutionRecord
live benchmark metric provenance

Stage Router 只選 skills，不選 model。不要把 model preference 寫回
StageRoute、ROUTING_POLICY.yaml 或 metadata overlay。runtime switch 仍是
explicit handoff，不是隱式 stage mutation。

============================================================
2. DOGFOOD
============================================================

使用 `using-superpowers` 作為 resident task/session authority，使用既有
Stage Router，不重載整個 catalog。每一個 active development stage 都必須
產生 StageRoute 或：

NO_SKILL_NEEDED(reason)

只載入 selected SKILL.md bodies。若出現 brandkit、llm-council、cost-tracker
等語義不相關或不可載入的 selection，記為 ROUTING_DEFECT，不在本 task 修
Stage Router。

============================================================
3. FRESH CODEX SOURCE TRUTH
============================================================

先記錄：

- git status / branch / HEAD / origin fetch;
- installed `codex --version` and exact `codex exec --help`;
- installed Codex contract target and provenance;
- available model selection and reasoning-effort surfaces;
- current TaskSpec/StageRoute/skill digests.

Installed behavior wins over current-main docs。不要把不存在的 model、flag 或
usage field 寫進實驗。

============================================================
4. CONTROLLED MODEL EFFECT
============================================================

只有在 Codex installed runtime 支援 model selection，且現有 account 已授權
至少兩個可辨識 model 時才能跑：

same runtime
same task
same fixture/repository
same StageRoute digest
same selected skill IDs/digests
same permission envelope
same tool/MCP availability
same project/system instruction digest
same reasoning effort

只改：

MODEL

若任何控制變數不能固定，放入 `CONFOUNDERS`，並將結果分類為
`MODEL_EFFECT = INCONCLUSIVE`，不可改名成 configuration preference。

不要自動切換 provider、不要登入、不要購買 credits、不要建立新 credentials。

============================================================
5. CONTROLLED REASONING-EFFORT EFFECT
============================================================

這是與 model effect 分離的實驗。固定 runtime、model、task、route、skills、
tools、permissions、context，只改 installed Codex 支援的 effort level。

不要同時改 model + effort。分別記錄：

- terminal success;
- acceptance coverage;
- latency / wall time;
- observable model/tool calls;
- tokens / cost only with verified semantics;
- retries, reroutes, failures;
- verification artifacts。

若 effort surface 或 quota 不可安全控制，`EFFORT_EFFECT = INCONCLUSIVE`。

============================================================
6. INITIAL WORKLOADS
============================================================

優先使用已存在、未修改的 holdout fixture：

- H03 API/interface design;
- H09 release verification;
- 另一個已證明 bounded 且 non-destructive 的 task（若現有資料足夠）。

不要用同一個 Codex configuration 的 repetitions 當作不同 configurations。
H01/H03/H09 的 acceptance criteria 不得為了實驗改寫。

cheap cell target `n >= 2`；若只能 `n = 1`，標示 `EXPLORATORY_ONLY`，不產生
preference。開發用 A–J fixture 不可當 unseen model holdout。

============================================================
7. EXECUTION AND SECURITY
============================================================

coding/editing 只可在 temporary fixture repo 或 isolated worktree。每次 run
記錄 START_SHA、END_SHA、changed files、tests、diff digest、workspace digest。

維持既有 Codex permission intersection，不得由 model/profile/skill/MCP
宣告取得 OS authority。subprocess 必須 shell=False、stdin=DEVNULL、finite
timeout；不要保存 raw prompt/stdout/stderr、credential、auth header、環境
內容或 session state。

不使用 broad bypass、interactive approval、未驗證的 model alias 或未授權
provider。不能證明安全就 `BLOCKED`，不要為了取得結果放寬權限。

============================================================
8. EVIDENCE CONTRACT
============================================================

所有結果使用 strict evidence class：

REAL_EXECUTION
HOST_MANAGED_FIXTURE
MOCK

只有 REAL_EXECUTION 可以支持 live quality/reliability/latency/terminal
結論。每個 metric 保存 source field、aggregation、unit、status、confidence。

不要把 process launch 算成 `model_calls = 1`。unknown token/cost/model-call
使用 null/UNKNOWN。不要從 public pricing 推算 actual billing cost。

每個 task 產生一個 terminal outcome：

VERIFIED_SUCCESS | PARTIAL | FAILED | BLOCKED

並保留 stage outcomes 與 independent verification。不要以 model 自評當成功證據。

============================================================
9. OUTPUTS
============================================================

建立：

- `docs/v3/evidence/MODEL_RUNTIME_EVAL_V8.md`
- `docs/v3/evidence/PHASE3F_CODEX_CONTROLLED_EXPERIMENT_ROUTE.md`
- append-only sanitized records in `fixtures/v3/model-routing/runs/phase3c/`

報告需分開：

- MODEL_EFFECT;
- REASONING_EFFORT_EFFECT;
- CONFIGURATION_EFFECT（只用於真正不同 runtime/configuration）；
- quality / efficiency / reliability / security；
- variance、confounders、baseline relationship；
- whether evidence is sufficient for a later conservative router。

不要在這一步啟動 production policy、adaptive learning、bandits、per-call
model switching 或 agent-as-router。

============================================================
10. TESTS AND REVIEWS
============================================================

保留全 repository tests。新增 focused tests：

- model/effort variable isolation;
- same StageRoute and skill digests;
- n=1 exploratory classification;
- unknown metric semantics;
- credential sanitization;
- permission preservation;
- REAL_EXECUTION-only quality inclusion;
- terminal evidence and append-only records。

用獨立 lanes 做 execution correctness、security、simplification、verification
review。OCR auth precheck 只做一次；401 時記錄
`OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`。

============================================================
11. DECISION
============================================================

不要預設成功。根據實測結果選一個：

- `CODEX_CONTROLLED_MODEL_EFFECT_EVIDENCE`
- `CODEX_CONTROLLED_EFFORT_EFFECT_EVIDENCE`
- `CODEX_CONTROLLED_EXPERIMENT_INCONCLUSIVE`
- `INSUFFICIENT_LIVE_EVIDENCE`

即使 evidence 成功，也只提出下一階段 Conservative Model Router MVP；不在
本 task 啟動 production routing。
