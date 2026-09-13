# Agent Skills Matrix v3 — Claude Real-Home Canary Preview v2

## Gate result

```yaml
CLAUDE_REAL_HOME_CANARY_READINESS: CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH
REAL_HOME_APPLY_AUTHORIZED: false
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
```

Phase 3O.1 只完成 blocker closure 與新 preview。沒有 real HOME、`.claude` 或
ASM user-data mutation，沒有 Claude inference，也沒有任何 provider/auth/config
讀取。

## Fresh read-only inventory

| 欄位 | 結果 |
|---|---|
| Claude personal root | `${HOME}/.claude/skills`，一般 directory |
| direct child count | `287`；child names 未保存 |
| `module-map` personal target | `ABSENT` |
| `module-map` synced target | `ABSENT` |
| `module-map` project duplicate | `ABSENT` |
| bundled collision | `NONE_VERIFIED`，candidate-specific calibrated artifact proof |
| unknown collisions | `0` |
| user-owned/synced/ambiguous/bundled conflicts | `0` |
| inventory body reads | `0` |
| actual mutation | `0` |

## Selected canary

| skill | source digest | size | support files | selection reason |
|---|---|---:|---:|---|
| `module-map` | `sha256:12b79ba718e4e85e21ca862808f5fe61647b59c59675fa78e45c272ecb34c4df` | `1959` bytes | `0` | 唯讀、單一 `SKILL.md`、無 MCP/plugin/config 需求、適合檢驗 managed-copy lifecycle |

只讀取該 selected canonical body 做 digest/size verification；preview 沒有保存
raw body。這是 1-skill bounded canary，不代表 full catalog authorization。

## ASM user-data preview

```text
root: ${ASM_USER_DATA}
resolution: ${HOME}/Library/Application Support/Agent Skills Matrix
state: EXPECTED_ABSENT
managed subroot: ${ASM_USER_DATA}/v3/claude
managed subroot state: EXPECTED_ABSENT
ownership marker: ${ASM_USER_DATA}/v3/claude/.asm-user-manifest.json
journal: ${ASM_USER_DATA}/v3/claude/.transactions/<id>.json
writes: 0
```

Root/parent/device identity 只在 ephemeral preview package 內使用，不寫入本文件；
package digest 仍會綁定它們，未來 apply 需重新 revalidate。

## Fresh non-authorizing package

| 欄位 | 結果 |
|---|---|
| package version | `canary 1.1` |
| runtime | Claude Code `2.1.235` |
| strategy | `MANAGED_COPY` |
| scope | `USER` |
| selected skills | `1` |
| planned files | `2`（ASM derived source + Claude personal destination） |
| bytes | `1959` |
| CREATE | `2` |
| UPDATE / NO_OP / BLOCK | `0 / 0 / 0` |
| `installable` | `false` |
| `apply_allowed` | `false` |
| `consumable` | `false` |
| recovery guarantee | `PROCESS_CRASH_RECOVERABLE` |
| discovery validation | `STATIC_CONTRACT_ONLY` |

Exact fresh preview identifiers：

```text
package_digest: sha256:a87e54bcbe516ded434feacf118daaba39fa2129434e6b1a5320e4671fb022de
confirmation_digest: sha256:9dceb3f9233adc712e26c3378278e6192963ebc0e0efc0a3f841617476e5f197
preview_digest: sha256:9174543748ac7451ea74ede04cdd68dbe88eca83cae2846d52dda96a5b1a080d
```

這三個 digest 是 Phase 3O.1 fresh preview identity；Phase 3O 的舊 package、
confirmation、preview digest 全部 retired，不可重用。即使本 preview READY，
它也不會自動變成 mutation authorization。

## Authorization boundary

```yaml
authorization_status: PENDING_EXPLICIT_USER_AUTHORIZATION
real_home_apply_authorized: false
revalidation_required_before_apply: true
no_changes_made: true
```

未來執行必須重新驗證 runtime fingerprint、ASM root/parent/subroot identity、
candidate collision、canonical/source snapshot 與 exact package/confirmation
digest；任一項變更都要重新 preview/package/confirmation。Phase 3O.1 不提供
real-home apply path。

## Security

- 未寫入真實 `${HOME}`、`${HOME}/.claude` 或 real ASM data root。
- 未讀 settings、auth、credential、history、session、MCP、plugin、hook 或 provider。
- 未執行 Claude inference；bundled proof 是 bounded static inspection。
- 未覆寫 user-owned、synced 或 bundled path；沒有 force/adopt/fallback。
- evidence 只使用 symbolic paths；沒有 private absolute path 或 raw artifact/body。
