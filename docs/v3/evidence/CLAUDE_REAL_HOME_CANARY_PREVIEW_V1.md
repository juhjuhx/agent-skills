# Agent Skills Matrix v3 — Claude Real-Home Canary Preview v1

本文件記錄 Phase 3O 的唯讀準備結果。它沒有執行 Claude inference，也沒有
在真實 HOME、`~/.claude` 或 ASM user-data 位置建立、更新、刪除、卸載、回復
或 recovery 任何檔案。

## 結論

`CLAUDE_REAL_HOME_CANARY_READINESS = CLAUDE_REAL_HOME_CANARY_BLOCKED`

阻斷是刻意 fail-closed：

- 目前 Claude 2.1.235 的 checked-in USER contract 沒有把
  `${ASM_USER_DATA}` 映射成可供 real-home package 使用的實際安全位置；
- Phase 3L evidence 沒有 version-bound bundled-skill 名單，因此即使
  `module-map` 的個人目標目前為 `ABSENT`，bundled collision 仍是 `UNKNOWN`；
- Phase 3O 要求第一個 canary 的 unknown、user-owned、synced、bundled、ambiguous
  collision 全部為零，不能以目前文件猜測補齊。

## 唯讀 real-home inventory

此次本機 inventory 僅查看：HOME/Claude personal skill root 的 directory
metadata、root 是否為 symlink、direct-child count，以及 `module-map` 的
精確候選路徑、synced 候選路徑與 repository project 候選路徑。沒有讀取任意
skill body、settings、auth、history、session、plugin、hook、MCP 或 provider
資料。

| 欄位 | 結果 |
|---|---|
| Claude personal root | `${HOME}/.claude/skills`，現存且為一般 directory |
| direct-child count | `287`；child names 沒有寫入 evidence |
| `module-map` personal target | `ABSENT` |
| `module-map` synced target | `ABSENT` |
| `module-map` project duplicate | `ABSENT` |
| bundled collision | `UNKNOWN`；沒有版本綁定名單 |
| raw skill bodies | `0`（inventory）；選定候選只做 canonical digest/size verification |
| mutation | `0` |

真實 root 的 owner/mode 與 device/inode 只在程序記憶體中用於 safety identity
digest；不保存私人絕對路徑。

## Canary candidate

只選一個 bounded candidate：

| skill | source digest | size | support files | 選擇原因 |
|---|---|---:|---:|---|
| `module-map` | `sha256:12b79ba718e4e85e21ca862808f5fe61647b59c59675fa78e45c272ecb34c4df` | 1959 bytes | 0 | 唯讀、零工具、單一 `SKILL.md`、不需 MCP/plugin/config |

這不是 popularity 選擇，也不是執行效果測試。完整 sanitized candidate input
見 [`claude-real-home-canary-selection-v1.json`](../../../fixtures/v3/productization/claude-real-home-canary-selection-v1.json)。

## Preview package

Package 在 disposable scratch roots 中由既有 generic USER package builder
建立，再以 path-free digest 綁定 real target identity；它只存在於記憶體，
不會寫成可執行 package。它保留：

- `scope = USER`；
- `runtime = claude-code`、Claude Code `2.1.235`；
- `strategy = MANAGED_COPY`；
- canonical snapshot、runtime contract、Claude USER contract、selected skill
  source digests；
- exact symbolic paths：`${ASM_USER_DATA}/v3/claude/skills/module-map/SKILL.md`
  與 `${HOME}/.claude/skills/module-map/SKILL.md`；
- `PROCESS_CRASH_RECOVERABLE` 作為既有 virtual-home transaction guarantee，
  不宣稱 power-loss atomicity。

Preview summary：

| 欄位 | 結果 |
|---|---|
| selected skills | `1` |
| planned files | `2`（ASM derived source + Claude destination） |
| managed-copy bytes | `1959` |
| collision count | `1`（`UNKNOWN` bundled evidence） |
| installable | `false` |
| real-home apply authorized | `false` |
| discovery validation | `STATIC_CONTRACT_ONLY` |
| ASM store | `${ASM_USER_DATA}/v3/claude`，symbolic-only unresolved |

最新唯讀 preview 的非消費性摘要：

```text
status: CANARY_PREPARATION_BLOCKED
package_digest: sha256:c0c03a6b2a77e8c3bda0185e3a383e3d3dedb01ebbc087f3d342b5b5ebf7d763
confirmation_digest: sha256:6a2a29bbc55f38a0a4ebb8228ae48296a7b1a4d0980282a9c5e7f3a3f6cfd308
consumable: false
no_changes_made: true
```

這兩個 digest 只能識別本次被阻斷的 preview；不是 user authorization，不能
傳給任何 apply path。

## Clone-to-use façade

目前最小流程是：

```sh
git clone <repository>
cd agent-skills
python3 -m tools.v3.installer status
python3 -m tools.v3.installer preview --runtime claude-code --scope project --project "$PWD"
python3 -m tools.v3.installer canary-preview --runtime claude-code --skills module-map
```

`status`、project `preview/apply` 與既有 `recover/uninstall/revert` 仍使用
原本 installer contracts。`canary-preview` 只產生真實 personal scope 的
最小唯讀 inventory 與 package/confirmation digest；沒有 Phase 3P 的 apply
verb。`status` 將尚未完成本次 bounded preview 的狀態顯示為
`PENDING_READ_ONLY_PREVIEW`；實際 preview 結果另行顯示
`CANARY_PREPARATION_BLOCKED`。任何 `apply --scope user` 仍 fail closed。

## Future verification plan

只有後續 phase 取得新的 exact authorization，才可按下列順序執行：

1. revalidate runtime fingerprint、Claude USER contract、snapshot、package、
   target identity、collision state 與 destination state；
2. apply 1–3 個 exact managed-copy files，ownership marker 最後寫入；
3. verify destination/source digests、journal `COMPLETE`、zero unrelated changes；
4. preview and perform exact-path uninstall/reinstall/revert checks；
5. 若任何 concurrent change 出現，回傳 `STALE_PACKAGE` 或 `MANUAL_CONFLICT`，
   不自動修復。

## Privacy and security

本次檢查確認：

- 沒有真實 HOME mutation、config mutation、auth read 或 runtime/model invocation；
- 沒有讀取 credentials、settings、history、sessions、MCP、plugins 或 hooks；
- 沒有輸出 raw skill body、raw runtime output、environment 或私人絕對路徑；
- 沒有 overwrite user-owned、synced 或 bundled content；
- 沒有 `--force`、`--adopt`、silent strategy fallback 或 recursive deletion；
- `real_home_apply_authorized = false` 在整個 Phase 3O 保持不變。

## Status carry-forward

`INSTALLER_IMPLEMENTED = true`、`VIRTUAL_HOME_VERIFIED = true`、
`PROCESS_CRASH_RECOVERY_VERIFIED = true`；
`REAL_HOME_CANARY_VERIFIED = false`、`FULL_CATALOG_USER_READY = false`。

下一步不是 Phase 3P，因為本次 canary 沒有取得可授權 package。需先補上：
version-bound bundled-name evidence 與不含 real-home write 的 ASM user-data
destination contract；補齊後重新 preview，不能沿用上述 digest。
