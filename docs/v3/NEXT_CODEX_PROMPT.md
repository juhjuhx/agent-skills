# AGENT SKILLS MATRIX v3
# PHASE 3K — USER-SCOPE INSTALLATION & UPGRADE CONTRACT

這是 Phase 3J 成功後的下一階段提案；不要在 Phase 3J 執行。

Repository: `juhjuhx/agent-skills`

Current product state:

```yaml
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CODEX_LIVE_TRANSPORT_BLOCKED: true
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Mission

在 project-only installer contract 已穩定後，研究 user-scope installation、upgrade
與 cross-platform lifecycle。這不是 Phase 4，也不是 live model work。

不得：

- retry/debug Codex、Claude、OpenCode 或 Hermes live execution；
- 修改 Stage Router weights 或實作 model/effort/adaptive routing；
- 自動寫入 user/global runtime config；
- 引入 config merge engine、registry service、daemon 或 database；
- 把 project `InstallPackage` 直接重用為 global apply authorization。

## Required order

```text
repo truth
  → current project installer contract review
  → user destination provenance
  → cross-platform copy/symlink/reference contract
  → ownership and migration model
  → preview-only user plan
  → tests
  → explicit future apply gate
```

先研究，不要先寫 `~/.codex`、`~/.claude`、`~/.config/opencode` 或 Hermes config。

## Scope boundary

維持三個獨立 scope：

- `PROJECT`: Phase 3J 已通過的可 apply scope。
- `USER`: 本 phase 先做 detection/preview/contract only；若要 apply，必須有明確
  destination contract、user confirmation boundary、ownership migration 與回復策略。
- `GLOBAL`: 不應與 user scope 混稱；若無可靠 cross-platform contract，保持
  `PREVIEW_ONLY`。

Existing user-authored runtime config 仍然 out of scope。任何需修改 TOML、JSONC、
settings、permission、MCP、plugin、CLAUDE/AGENTS 檔案的整合都要另立設計與
fail-closed contract。

## Questions to answer

1. 各已驗證 runtime/version 是否真的支援 user-level skill/bootstrap destination？
2. copy、symlink、reference 的 discovery 與 lifecycle 是否分別可證明？
3. user-owned parent 與 ASM-managed exact artifact 如何區分？
4. managed project → user migration 是否需要新 transaction type？
5. upgrade、uninstall、revert 是否能保留既有 auth/permissions/config？
6. Windows、macOS、Linux 的 symlink failure 是否能在 apply 前完整預測？
7. 是否值得支援 user apply，還是長期保持 preview-only？

## Required invariants

- canonical `skills/<skill>/SKILL.md` remains source truth；generated copy 永不升格。
- `InstallationPlan.no_actual_writes` 永遠為 `true`；執行狀態只進 `ApplyResult`。
- `EXECUTION_EPHEMERAL` 永遠不能安裝成 user/global persistent state。
- ownership marker 只擁有 exact listed paths，不擁有 home、runtime parent 或 config。
- no `--force`、no adopt-existing、no recursive delete、no silent fallback between
  symlink/copy/reference。
- no credential/auth/provider/runtime/model invocation。
- Stage Router unchanged；214 metadata / zero ranking body reads / NO_SKILL_NEEDED 保持。

## Minimum proposed outputs

- user-scope target contract fixture with immutable runtime/version evidence；
- copy/symlink/reference capability matrix；
- preview-only user `InstallPackage` examples；
- migration/upgrade/revert state table；
- tests proving no global write and stale/ownership fail-closed；
- evidence doc and one dogfood route record。

Do not implement actual user/global apply until a later explicit gate says the contract
is safe and independently reviewed.

## Live track

Keep unchanged:

```text
CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS = NOT_READY
CROSS_RUNTIME_ROUTING_READINESS = NOT_READY
```

If Codex transport later recovers, resume the already-defined Phase 3G controlled effort
experiment separately. Do not mix it into user-scope installer work.

STOP. This file is a proposal only.
