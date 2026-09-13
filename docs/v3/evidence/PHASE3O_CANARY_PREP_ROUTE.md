# Phase 3O — Canary Preparation Route

## Route

```text
Phase 3N virtual-home evidence
        ↓
read-only HOME / Claude personal-root inventory
        ↓
metadata-only candidate selection (≤ 3)
        ↓
canonical digest/size check for selected body only
        ↓
generic USER package in disposable scratch roots
        ↓
path-free real target identity binding
        ↓
zero-collision + ASM-store + stale-input gate
        ↓
non-consumable preview / exact digest request
```

## Gate result

`CANARY_PREPARATION_BLOCKED`。

`module-map` 的 personal、synced、project exact path 都是 `ABSENT`，但 bundled
collision 沒有 version-bound inventory，且 `${ASM_USER_DATA}/v3/claude` 仍只有
symbolic contract。依 Phase 3O 的 zero-collision 與 real-store safety rule，
不能發出可消費的 authorization。

## Implementation boundary

- `tools/v3/claude_canary.py`：唯讀 inventory、bounded selection、非授權 package
  preview、status/preview rendering。
- `tools/v3/installer.py`：新增 status/canary-preview façade；既有 project/virtual
  USER transaction 不改變。
- `build_user_install_package(..., skill_ids=...)`：只增加 selected-only package
  input，預設完整 catalog 行為不變；selected package 不會默認 prune 未選 skill。
- 沒有新增 runtime adapter、model/effort routing、Stage Router weight 或 live
  execution path。

## Exact handoff rule

本 phase 的 `package_digest` 與 `confirmation_digest` 是 preview identity，
且 `consumable = false`。只有後續 phase 在重新 inventory、重新 package 並由
使用者明確核准同一組 digest 後，才可考慮 Phase 3P；本次阻斷時不提出 Phase 3P
執行授權。

## Verification lanes

- canary API/CLI tests：read-only、path redaction、≤3、unknown collision、status；
- existing Phase 3N USER/project tests：package/apply/recovery regression；
- static security checks：no subprocess/model/auth access in canary preview；
- no real-home apply path is reachable from the new façade。
