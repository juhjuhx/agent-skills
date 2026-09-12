# AGENT SKILLS MATRIX v3 — NEXT PROPOSAL
# PHASE 3M — CLAUDE USER-SCOPE APPLY MVP

本提案承接 Phase 3L：Claude Code `2.1.235` 的 user-scope discovery contract 已
完成資格化，但本文件不授權現在 apply，也不代表 Claude live execution 已恢復。

Current state:

```yaml
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CLAUDE_USER_CONTRACT_READY: true
CLAUDE_DISTRIBUTION_STRATEGY: MANAGED_COPY_PREFERRED
CLAUDE_USER_APPLY_AUTHORIZED: false
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Scope

若要繼續，只能做 Claude-only 的 `PHASE 3M — CLAUDE USER-SCOPE APPLY MVP`：

- 只支援 `scope=USER` 的 `MANAGED_COPY`；
- 先 preview，再由明確 apply action 授權；
- 所有測試使用 virtual HOME，不碰真實 `~/.claude`；
- 不修改 `settings.json`、`CLAUDE.md`、MCP、plugin、hook、permission、provider、auth；
- 重用 Phase 3J 的 InstallPackage、ownership、stale-plan、atomic staging、rollback、
  uninstall/revert 契約；
- exact-path ownership、source/installed digest、user collision、synced/bundled collision
  必須在 mutation 前完整 revalidate；
- 不新增 Codex/OpenCode/Hermes user apply，不做 model/effort/adaptive routing，不進 Phase 4。

## Gate

先確認：

```text
USER_SCOPE_APPLY_AUTHORIZED = explicitly granted by a future task
real-home protection = proven by virtual-home tests
managed-copy target = unchanged and version-bound
no config mutation = proven
rollback/uninstall/revert = exact-state only
```

若任何一項無法證明，維持 `CLAUDE_USER_PREVIEW_ONLY`，不要擴大權限或加入
symlink fallback。Claude 的 `RUNTIME_BLOCKED` 與這個靜態 installer contract 保持
正交。

## Live tracks

不要在 3M 重試 Codex、Claude、OpenCode 或 Hermes live execution。若 Codex transport
另行恢復，回到既有 Phase 3G controlled effort cells；不要重建 harness。

STOP. 本文件是下一階段提案，不要在 Phase 3L 執行。
