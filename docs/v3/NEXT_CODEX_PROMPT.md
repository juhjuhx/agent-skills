# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3N — CLAUDE USER-SCOPE APPLY MVP
# CONTRACT-CLOSURE GATE

本提案承接 Phase 3M integration checkpoint。Phase 3M 已確認 static/productization/
project transaction 與 Claude user discovery contract 可以組合，但尚未授權任何
USER mutation。

Current state:

```yaml
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CLAUDE_USER_CONTRACT_READY: true
CLAUDE_DISTRIBUTION_STRATEGY: MANAGED_COPY_PREFERRED
USER_APPLY_ARCHITECTURE_READINESS: USER_APPLY_ARCHITECTURE_PARTIAL
CLAUDE_USER_APPLY_ELIGIBILITY: NEEDS_CONTRACT_CHANGE
STACK_INTEGRATION_STATUS: STACK_SAFE_TO_CONTINUE_TO_3N
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Required contract closure before mutation

Phase 3N 只能在 virtual HOME 先完成以下 gate，不能把 Phase 3L 的 READY 當成
authorization：

1. 將 generic `InstallPackage`/target contract 擴充為可驗證的 `scope=USER`，保留
   一般 package，不建立 `ClaudeInstallPackage`；
2. package 必須綁定 Claude 2.1.235 fingerprint/contract digest、
   `MANAGED_COPY`、symbolic USER root、collision observations、exact managed paths
   與每個 destination 的 expected state；
3. 重用 Phase 3J 的 all-target preflight、stage、revalidate、marker-last、digest
   verify、bounded rollback，不建立第二個 transaction engine；
4. 對 process death / partial state 提供 bounded recovery marker 或明確的
   fail-closed/manual-recovery protocol；
5. `CLAUDE_SYNCED`、user-owned、ambiguous、unknown、bundled collision 不得被
   adopt/overwrite；bundled collision 在沒有窄化 confirmation contract 前直接
   BLOCK；
6. runtime version 變動時新 apply/update 必須 `RUNTIME_REQUALIFICATION_REQUIRED`，
   但 exact managed cleanup 不得依賴 runtime inference；
7. `USER_SCOPE_APPLY_AUTHORIZED` 在本 gate 完成前維持 false。

## Authorized future scope

只有上述 contract closure 通過後，才可實作：

- Claude Code only；
- USER scope only；
- `MANAGED_COPY` only；
- explicit preview → exact confirmation → apply；
- virtual HOME first；
- exact-path ownership、uninstall、revert；
- no real-home canary unless a later task explicitly requests it after preview,
  zero-collision check, bounded subset, and rollback validation。

仍禁止 Codex/OpenCode/Hermes USER apply、runtime config mutation、provider/auth/model
work、symlink fallback、force/adopt、recursive delete、Stage Router 變更與 Phase 4。

## Live tracks

不要重試 Codex、Claude、OpenCode 或 Hermes live execution。若 Codex transport 在別的
環境獨立恢復，回到既有 Phase 3G contract；不要在 3N 重建 benchmark harness。

## References

- [Phase 3M integration checkpoint](evidence/INTEGRATION_CHECKPOINT_V1.md)
- [Current v3 contract index](CURRENT_V3_CONTRACT_INDEX.md)
- [Claude user-scope contract](evidence/CLAUDE_USER_SCOPE_V1.md)

STOP. 本文件是下一階段提案，不要在 Phase 3M 執行 USER apply。
