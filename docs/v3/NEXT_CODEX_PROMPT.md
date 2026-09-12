# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3O — CLAUDE REAL-HOME CANARY & CLONE-TO-USE UX
# EXPLICIT DEPLOYMENT GATE

本提案承接 Phase 3N。Phase 3N 已在 virtual HOME 完成 Claude Code
`MANAGED_COPY` 的 package、exact confirmation、交易 journal、process-crash
recovery、single/mixed/full-catalog lifecycle、upgrade、uninstall 與 revert。
本文件不授權真實 HOME mutation。

Current state:

```yaml
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CLAUDE_USER_CONTRACT_READY: true
CLAUDE_USER_APPLY_ENGINE: VIRTUAL_HOME_ONLY
USER_APPLY_ARCHITECTURE_READINESS: USER_APPLY_ARCHITECTURE_READY
CLAUDE_USER_APPLY_AUTHORIZED: false
INSTALLER_IMPLEMENTED: true
VIRTUAL_HOME_VERIFIED: true
PROCESS_CRASH_RECOVERY_VERIFIED: true
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Required Phase 3O boundary

Phase 3O 只能處理 Claude Code、USER scope、`MANAGED_COPY`。必須先做 preview，
再由使用者明確授權 exact package digest；不得新增 `--force`、real-home bypass、
config merge 或其他 runtime apply。

第一個 real-home canary 必須：

1. 明確由使用者請求；
2. 使用目前 package/confirmation/transaction contract；
3. 只包含 1–3 個 bounded skills；
4. zero collision、zero synced/bundled conflict、zero user-owned overwrite；
5. 完成 post-install digest/ownership validation；
6. 驗證 uninstall/reinstall/revert；
7. 失敗時保留 exact transaction evidence，不能猜測或 recursive cleanup。

只有 bounded canary 成功後，才可另行評估 `FULL_CATALOG_USER_READY`。Phase 3O
不得默認寫入 214 個 skill，也不得把 virtual-home success 宣稱為 real-home
success。

## Explicitly out of scope

Codex/OpenCode/Hermes USER apply、runtime config、provider/auth/model work、live
benchmark、Stage Router weights、model/effort routing、adaptive learning、plugin、
MCP、Claude settings、CLAUDE.md、hooks、permissions、Phase 4 都不在本 prompt。

Codex live transport 仍為 blocked；若它在其他環境獨立恢復，只能回到既有
Phase 3G contract，不能在 Phase 3O 順便重跑或改 benchmark harness。

## Required evidence

保留 virtual-home regression，並新增 real-home canary 的明確 audit boundary、
preview transcript 的 sanitized metadata、post-install/revert evidence 與
rollback result。不得保存 credentials、environment、raw prompt、skill body、
runtime output 或私人絕對路徑。

## References

- [Phase 3N Claude USER apply evidence](evidence/CLAUDE_USER_APPLY_V1.md)
- [Phase 3N route](evidence/PHASE3N_USER_APPLY_ROUTE.md)
- [Current v3 contract index](CURRENT_V3_CONTRACT_INDEX.md)
- [Phase 3M integration checkpoint](evidence/INTEGRATION_CHECKPOINT_V1.md)

STOP. 本文件只提出 Phase 3O；除非使用者另行明確授權，不得執行 real-home
canary，也不得將任何 live-routing readiness 升級。
