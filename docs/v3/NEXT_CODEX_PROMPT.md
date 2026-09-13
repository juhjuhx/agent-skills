# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3P — EXECUTE EXACT CLAUDE REAL-HOME CANARY

Phase 3P stabilization 正在重新驗證 Phase 3O.1 的 canary package。舊 preview
識別碼只保留為 historical evidence，不能授權或重播任何 mutation；沒有任何
真實 HOME mutation。

不要執行本 prompt，除非使用者明確授權下方 exact package digest 與
confirmation digest。若 preview、destination、root identity、runtime fingerprint
或任何 stale input 改變，必須先重新 package。

Current state:

```yaml
CLAUDE_REAL_HOME_CANARY_READINESS: PENDING_STABILIZATION_REVALIDATION
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

Stabilization boundary:

```yaml
AUTONOMOUS_STABILIZATION: IN_PROGRESS
BETA_CANDIDATE_STABLE: PENDING_FINAL_DOUBLE_PASS
REAL_HOME_CANARY_EXECUTION: FORBIDDEN_IN_THIS_EPOCH
```

## Exact authorization handoff

```yaml
runtime: claude-code
runtime_version: 2.1.235
scope: USER
strategy: MANAGED_COPY
selected_skill: module-map
package_digest: NOT_YET_REFRESHED_AFTER_STABILIZATION
confirmation_digest: NOT_YET_REFRESHED_AFTER_STABILIZATION
preview_digest: NOT_YET_REFRESHED_AFTER_STABILIZATION
real_home_apply_authorized: false
consumable: false
```

Phase 3O.1 old non-authorizing identifiers (do not reuse):

```yaml
package_digest: sha256:a87e54bcbe516ded434feacf118daaba39fa2129434e6b1a5320e4671fb022de
confirmation_digest: sha256:9dceb3f9233adc712e26c3378278e6192963ebc0e0efc0a3f841617476e5f197
preview_digest: sha256:9174543748ac7451ea74ede04cdd68dbe88eca83cae2846d52dda96a5b1a080d
status: HISTORICAL_NON_AUTHORIZING
```

穩定化完成後必須重新 inventory、重新驗證 Claude fingerprint、ASM user-data
root、bundled collision 與所有 stale inputs，再產生新的 exact digests。

## Required authorization wording

使用者未來必須明確確認最終重新產生的 exact package digest 與 exact
confirmation digest，並明確允許 Claude Code 2.1.235、USER、MANAGED_COPY、
一個 `module-map` skill canary。只有該 exact confirmation 才能進入後續
execution gate；本 prompt 本身不是授權。若 digest 尚未刷新，不能執行。

## Constraints

下一階段仍只能執行 exact one-skill canary；不得擴展為 full catalog，不得執行
Claude inference、provider/auth、Codex/其他 runtime、Stage Router、
model/effort routing 或新增 bypass。Phase 3O.1 已 STOP，沒有任何 apply 發生。

References:

- [Phase 3O preview evidence](evidence/CLAUDE_REAL_HOME_CANARY_PREVIEW_V1.md)
- [Phase 3O.1 canary preview](evidence/CLAUDE_REAL_HOME_CANARY_PREVIEW_V2.md)
- [ASM user-data contract](evidence/ASM_USER_DATA_CONTRACT_V1.md)
- [Claude bundled collision evidence](evidence/CLAUDE_BUNDLED_COLLISION_V1.md)
- [Phase 3O route](evidence/PHASE3O_CANARY_PREP_ROUTE.md)
- [Clone-to-use guide](CLONE_TO_USE.md)
- [Current v3 contract index](CURRENT_V3_CONTRACT_INDEX.md)

STOP. DO NOT EXECUTE WITHOUT EXPLICIT USER AUTHORIZATION FOR THE EXACT DIGESTS
ABOVE. 本 prompt 本身不是授權。
