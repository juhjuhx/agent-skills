# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3O FOLLOW-UP — CLOSE CANARY PREPARATION BLOCKERS

Phase 3O 已完成唯讀 real-home inventory、bounded candidate selection、非授權
package/confirmation digest 與 clone-to-use façade；沒有任何真實 HOME mutation。

Current state:

```yaml
CLAUDE_REAL_HOME_CANARY_READINESS: CLAUDE_REAL_HOME_CANARY_BLOCKED
CLONE_TO_USE_UX_READINESS: CLONE_TO_USE_UX_READY
REAL_HOME_APPLY_AUTHORIZED: false
INSTALLER_IMPLEMENTED: true
VIRTUAL_HOME_VERIFIED: true
PROCESS_CRASH_RECOVERY_VERIFIED: true
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Exact blocker

不要執行 Phase 3P。要讓下一次 preview 能進入 authorization gate，必須先以
contract-only 變更補齊兩項證據：

1. 為 `${ASM_USER_DATA}/v3/claude` 綁定一個不含真實私人路徑、但能在未來
   transaction 中安全解析與 revalidate 的 user-data destination contract；
2. 提供與 Claude Code `2.1.235` 綁定的 bundled-skill collision inventory，或
   等價的 non-inference evidence，使 canary 候選不再是 `UNKNOWN`。

不能把本次 preview digest 視為授權，也不能用 CLI 參數宣稱 `bundled = none`。
補證後必須重新 inventory、重新 package、重新產生兩個 digest；舊 digest 不可重用。

## Constraints

只處理上述兩項 contract evidence 與驗證；不得執行 real-home apply、Claude
inference、provider/auth、Codex/其他 runtime、Stage Router、model/effort routing、
full-catalog rollout 或新增 bypass。

References:

- [Phase 3O preview evidence](evidence/CLAUDE_REAL_HOME_CANARY_PREVIEW_V1.md)
- [Phase 3O route](evidence/PHASE3O_CANARY_PREP_ROUTE.md)
- [Clone-to-use guide](CLONE_TO_USE.md)
- [Current v3 contract index](CURRENT_V3_CONTRACT_INDEX.md)

STOP. 只有 exact blockers 取得新證據後，才可重新 preview；本 prompt 不授權任何
real-home mutation。
