# Agent Skills Matrix v3 — Clone-to-Use

這是目前不需要理解 Phase 編號的最小使用流程。安裝預覽與實際執行分開；
Claude real-home canary 在取得 exact user authorization 前永遠是唯讀。

## 取得與查看狀態

```sh
git clone <repository>
cd agent-skills
python3 -m tools.v3.installer status
```

`status` 會分開顯示 Stage Router、static productization、project installer、
Claude USER engine、live execution 與 effort/cross-runtime routing 狀態。

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

## Claude personal canary 預覽

```sh
python3 -m tools.v3.installer canary-preview \
  --runtime claude-code \
  --skills module-map
```

這個 command 只讀取最小 personal-scope metadata，最多選 3 個 skill，並輸出
symbolic destination、collision、package digest 與 confirmation digest。它不會
建立 package file，也不會執行 apply；目前實際結果為 `CANARY_PREPARATION_BLOCKED`。

`apply --scope user` 沒有 hidden bypass。任何新 preview 都會生成新的 package
identity；舊 digest 不會跨 preview 或 target state 重用。

## 其他 lifecycle command

既有 `package`、`recover`、`uninstall` 與 `revert` 是 Phase 3N virtual-home
contract 的低階界面。它們不會使 Phase 3O 的 real-home preview 變成授權。Claude
USER 的下一個真實 mutation phase 必須重新 preview、明確確認 exact digest，並限於
1–3 個 managed-copy canary。

## 安全承諾

本流程不讀 auth/credential/config store、不啟動 runtime、不跑 model、不載入 MCP
或 plugin，也不默認安裝完整 214-skill catalog。
