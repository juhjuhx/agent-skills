# Agent Skills Matrix v3 — ASM User-Data Contract v1

## 結論

Phase 3O.1 建立的是通用、與 runtime 無關的 `ASM_USER_DATA_ROOT` contract。
它是 Agent Skills Matrix 的 derived / managed / non-canonical 儲存根，不是
`.claude`、`.codex`、OpenCode 或 Hermes 的 runtime-owned config 目錄。

目前 canary 平台為 macOS，解析規則為：

```text
${ASM_USER_DATA}
  = ${HOME}/Library/Application Support/Agent Skills Matrix
```

本次實際解析只存在於本機程序記憶體，沒有建立目錄，也沒有將真實絕對路徑
寫入 repository evidence。公共 contract 使用 `asm-user-data-contract-v1.json`，
contract digest 為：

```text
sha256:b158ae49df8674d3b87c6434083c8915b6ebe8d1a78c50456a9d6004ca0b204d
```

## 平台矩陣

| 平台 | 解析規則 | Phase 3O.1 狀態 |
|---|---|---|
| macOS | `${HOME}/Library/Application Support/Agent Skills Matrix` | `READY_FOR_VERSION_INDEPENDENT_RESOLUTION` |
| Linux | `${XDG_DATA_HOME}/agent-skills-matrix`，否則 `${HOME}/.local/share/agent-skills-matrix` | `SUPPORTED_WITH_PRECONDITION` |
| Windows | `${LOCALAPPDATA}/Agent Skills Matrix`，否則 `${HOME}/AppData/Local/Agent Skills Matrix` | `SUPPORTED_WITH_PRECONDITION` |

Linux 的 `XDG_DATA_HOME` 與 Windows 的 `LOCALAPPDATA` 若提供，必須是絕對路徑；
任何 symlink component、runtime-owned path、repository path、filesystem root、
或過寬的 HOME 本身都 fail closed。

## 本次 macOS 解析結果

| 欄位 | 結果 |
|---|---|
| root state | `EXPECTED_ABSENT` |
| managed Claude subroot | `${ASM_USER_DATA}/v3/claude`，`EXPECTED_ABSENT` |
| root writes | `0` |
| parent/root identity | 只在 ephemeral process state 內用於 revalidation |
| public absolute path | 不保存 |
| contract revision | `1.0` |

即使 root 尚不存在，resolver 仍會檢查可見 parent chain、symlink、目錄型別與
parent identity。後續 package 必須綁定 root identity、parent identity、expected
state、platform 與 contract digest；若 root 出現、消失、變成 symlink、parent
identity 改變或 contract revision 改變，便是 stale state，不能在原 package 上
繼續 mutation。

## 目前實作邊界

- `tools/v3/asm_user_data.py` 是唯一 generic resolver authority。
- resolver 純 read-only，不建立 root、不讀 config/auth、不執行 runtime。
- `observe_asm_user_data_path()` 對 `${ASM_USER_DATA}/v3/claude` 再做 exact
  subpath confinement，避免 managed path 透過 symlink escape。
- Phase 3O.1 只產生 preview/package evidence；沒有 real ASM data write。
- `v3/claude` 是目前 Claude USER package 的 bounded subroot，不是另一個
  Claude-specific user-data resolver。
