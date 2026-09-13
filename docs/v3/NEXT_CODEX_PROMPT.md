# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3P — EXECUTE EXACT CLAUDE REAL-HOME CANARY

Phase 3P stabilization 已完成。下方是最後一次只讀 real-home inventory 後產生的
fresh canary package；舊 preview 識別碼只保留為 historical evidence，不能授權
或重播任何 mutation。整個 epoch 沒有真實 HOME mutation。

不要執行本 prompt，除非使用者明確授權下方 exact package digest 與
confirmation digest。若 preview、destination、root identity、runtime fingerprint
或任何 stale input 改變，必須先重新 package。

Current state:

```yaml
CLAUDE_REAL_HOME_CANARY_READINESS: CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH
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
AUTONOMOUS_STABILIZATION: COMPLETE
BETA_CANDIDATE_STABLE: true
REAL_HOME_CANARY_EXECUTION: FORBIDDEN_IN_THIS_EPOCH
```

## Exact authorization handoff

```yaml
runtime: claude-code
runtime_version: 2.1.235
scope: USER
strategy: MANAGED_COPY
selected_skill: module-map
files: 2
bytes: 1959
collisions: 0
package_digest: sha256:0408c2a7153c8a6e403feed51f734a496e50e1d98d416b7637e07b5adb794866
confirmation_digest: sha256:242ba68b6d044d9cb2a555f5dba52eb5e62e91441175ea0330ba7737440f83c1
preview_digest: sha256:261b7a8fc3ea537eaa9ffaf1c133cdf963ec43c6367532530afce7f6ca277b75
package_context_digest: sha256:7bfe442b008983c49a0ebcb09012fdda7a7b465f1af4c7ad8e699e8026c82506
recovery_guarantee: PROCESS_CRASH_RECOVERABLE
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

這組 digest 綁定 Claude Code 2.1.235、`MANAGED_COPY`、`module-map`、符號化
`${HOME}/.claude/skills` 與 `${ASM_USER_DATA}/v3/claude`，以及當次 zero-collision
inventory。任何 source、destination、ASM root、runtime fingerprint、contract 或
collision state 變化都會使它失效，必須重新 preview/package/confirm。

## Required authorization wording

使用者未來若要進入後續 execution gate，必須明確確認以下 exact package digest
與 exact confirmation digest，並明確允許 Claude Code 2.1.235、USER、
`MANAGED_COPY`、一個 `module-map` skill canary。只有該 exact confirmation 才能
進入後續 gate；本 prompt 本身不是授權。若任何 digest 已失效，不能執行。

## Exact authorization request

```text
請明確授權只執行以下 exact canary：
runtime: Claude Code 2.1.235
scope: USER
strategy: MANAGED_COPY
skill: module-map
package_digest: sha256:0408c2a7153c8a6e403feed51f734a496e50e1d98d416b7637e07b5adb794866
confirmation_digest: sha256:242ba68b6d044d9cb2a555f5dba52eb5e62e91441175ea0330ba7737440f83c1

只有這兩個 digest 完全相符時才可進入未來的 Phase 3P canary executor。
本文件與本 prompt 不會自動授權；目前仍未執行任何真實 HOME mutation。
```

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
