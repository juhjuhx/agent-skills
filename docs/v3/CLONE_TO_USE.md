# Agent Skills Matrix v3 — Clone-to-Use

這是目前不需要理解 Phase 編號的最小使用流程。安裝預覽與實際執行分開；
Claude real-home canary 在取得 exact user authorization 前永遠是唯讀。

## 取得與查看狀態

```sh
git clone <repository>
cd agent-skills
python3 -m tools.v3.installer status
python3 -m tools.v3.installer doctor
```

`status` 會分開顯示 Stage Router、static productization、project installer、
Claude USER engine、live execution 與 effort/cross-runtime routing 狀態。
`doctor` 只驗證 repository 內的 snapshot、schema、runtime fixture 與 zero-body-load
invariant；它不探測 runtime executable、不讀設定、不啟動模型。

需要查看同一份狀態的機器可讀解釋時使用：

```sh
python3 -m tools.v3.installer explain --format json
```

## Project-local 使用

```sh
python3 -m tools.v3.installer preview \
  --runtime claude-code \
  --scope project \
  --project "$PWD"

python3 -m tools.v3.installer apply \
  --runtime claude-code \
  --scope project \
  --project "$PWD"
```

Project installer 仍是現階段唯一不需 real-home canary 的 apply 路徑。

## Claude USER 虛擬 HOME 測試

USER apply 目前只允許明確提供的虛擬 HOME 與虛擬 ASM user-data root；不能省略
任何 root，也不會從 `$HOME` 偷偷取得授權。下面的流程會把 package 與所有檔案
留在暫存目錄：

```sh
work="$(mktemp -d)"
mkdir -p "$work/home" "$work/asm"
python3 -m tools.v3.installer package \
  --runtime claude-code --scope user --strategy managed-copy \
  --home-root "$work/home" --asm-user-data-root "$work/asm" \
  --output "$work/package.json"
```

接著以 package 內的 exact digest 做 apply（不是泛用的 `yes`）：

```sh
package_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["package_digest"])' "$work/package.json")"
python3 -m tools.v3.installer apply \
  --runtime claude-code --scope user --strategy managed-copy \
  --home-root "$work/home" --asm-user-data-root "$work/asm" \
  --package "$work/package.json" \
  --confirm-package-digest "$package_digest"
```

同一 package 再套用會是 `NO_OP`。`uninstall`、`revert` 與 `recover` 也必須帶
`--strategy managed-copy`，並只接受同一個虛擬 root；它們不需要 Claude executable
或 provider。這條路徑是測試與開發用的 virtual USER engine，不是 real-home 授權。

## Claude personal canary 預覽

```sh
python3 -m tools.v3.installer canary-preview \
  --runtime claude-code \
  --skills module-map
```

這個 command 只讀取最小 personal-scope metadata，最多選 3 個 skill，並輸出
symbolic destination、collision、package digest 與 confirmation digest。它不會
建立 package file，也不會執行 apply。Phase 3O.1 的 ready 結果是 historical
preview；目前 stabilization 已完成一次新的只讀 revalidation，新的 package
仍須是
`apply_allowed=false`、`consumable=false`。

`apply --scope user` 沒有 hidden bypass。任何新 preview 都會生成新的 package
identity；舊 digest 不會跨 preview 或 target state 重用。

`doctor`／`explain` 是產品 façade；`package`、`apply`、`recover`、`uninstall`、
`revert` 是目前保留的明確 lifecycle verbs。阻擋時 JSON 會包含穩定的
`error_code`、`safe_state` 與 `next_action`，不回傳私人絕對路徑。

目前 final canary 是一個 `module-map`、零碰撞的 exact preview；要進入未來
real-home execution，仍必須由使用者明確確認該次 preview 所列的 package digest
與 confirmation digest。穩定化 epoch 不會自動消費這份確認。

## 其他 lifecycle command

既有 `package`、`recover`、`uninstall` 與 `revert` 是 Phase 3N virtual-home
contract 的低階界面。它們不會使 Phase 3O 的 real-home preview 變成授權。Claude
USER 的下一個真實 mutation phase 必須重新 preview、明確確認 exact digest，並限於
1–3 個 managed-copy canary。

## 安全承諾

本流程不讀 auth/credential/config store、不啟動 runtime、不跑 model、不載入 MCP
或 plugin，也不默認安裝完整 214-skill catalog。
