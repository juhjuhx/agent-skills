# Safe Project Installer V1 — Phase 3J

本文件記錄 v3 第一個可實際 APPLY、但仍然只限 project scope 的 installer
vertical slice。它把 Phase 3I 的 deterministic compiler 產物轉成可重驗證、可
回滾的 `InstallPackage`；它不執行 runtime、model、provider、MCP 或 plugin。

## Decision

```yaml
PROJECT_INSTALLER_READINESS: PROJECT_INSTALLER_READY
STATIC_PRODUCTIZATION_READINESS: STATIC_PRODUCTIZATION_READY
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
stage_router_weights_mutated: false
runtime_model_invocations: false
global_runtime_writes: false
user_scope_apply: false
```

這個 decision 只表示 project-local filesystem installer contract 已通過；不表示
任何 runtime 的 live provider 可用，也不表示 Phase 4 或 model/effort routing 已就緒。

## Repo truth

| 欄位 | 值 |
|---|---|
| repository | `juhjuhx/agent-skills` |
| base branch | `feat/v3-static-productization` |
| expected base HEAD | `109d78898916acb34607bc8905656fa4c2aa41a7` |
| implementation branch | `feat/v3-safe-project-installer` |
| routing baseline | `STAGE_ROUTER_PRODUCTION_READY` |
| canonical metadata records | 214 |
| ranking body reads | 0 |
| live execution | not run by Phase 3J policy |

`git fetch origin` 在這個 linked-worktree 環境因 `.agents/skills/.git/worktrees` 的
`FETCH_HEAD` 權限限制失敗；目前 branch、HEAD 與 working tree 狀態仍以 local repo
truth 核對，這不是 installer implementation failure。

## Phase 3I compatibility

Phase 3I 的 compiler 仍是唯一 static source of generated artifacts。Phase 3J 只
增加 mutation boundary：

```text
canonical SKILL.md
  → RoutingCatalogSnapshot
  → DistributionCompiler / immutable InstallationPlan
  → filtered InstallPackage
  → explicit project apply
  → ApplyResult + exact ownership marker
```

沒有新增 skill library、runtime registry、config merge engine 或 live execution
service。既有 `RoutingCatalogSnapshot`、`StageRoute`、`CompiledExecutionBundle`、
adapter manifest 與 runtime status contract 沒有被重新路由。

## Operation semantics normalization

`InstallationPlan` 現在同時保留兩層資訊，但 executor 只使用 authoritative
`action`：

| 欄位 | 用途 |
|---|---|
| `operation` | Phase 3I 的 artifact intent / reporting 相容欄位，例如 `CREATE_GENERATED_FILE` |
| `action` | 唯一可執行語意：`CREATE`, `UPDATE_MANAGED`, `NO_OP`, `SKIP_USER_OWNED`, `CONFLICT`, `WARN`, `SKIP_UNSUPPORTED` |
| `conflict_outcome` | dry-run 狀態摘要，不可被 executor 當成 mutation instruction |

這避免 executor 從 `operation + conflict_outcome + overwrite_policy` 猜測真正的
filesystem mutation。

## Artifact lifecycle

所有 generated artifact 都有 lifecycle：

| Lifecycle | 本 phase 是否可 APPLY | 例子 |
|---|---:|---|
| `INSTALL_PERSISTENT` | 是 | adapter manifest、runtime contract |
| `PROJECT_PERSISTENT` | 是 | runtime status、snapshot reference、static projection |
| `EXECUTION_EPHEMERAL` | 否 | StageRoute、CompiledExecutionBundle、selected-skills state、selected `SKILL.md` body |

即使 compiler 產生了 route-aware output，installer 也會將 execution-ephemeral
artifact 放入 `excluded_artifacts`，不會把一次任務的 route 或 skill body 變成
persistent runtime installation state。

## Runtime capability and install-target matrix

Install target inventory 是 checked-in、版本綁定的 fixture：
[`install-targets-v1.json`](../../../fixtures/v3/productization/install-targets-v1.json)。
它只允許 `PROJECT` scope、`COPY`、`config_mutation_required: false`，並把目標鎖在
project-local host-managed staging：

```text
<explicit-project-root>/.agent-skills-matrix/<runtime-id>/
```

原生 runtime 位置的 current documentation 只作 supporting evidence；在目前已驗證
contract 尚不足以保證每個 historical installed version 的 discovery behavior，
所以原生位置保持 `PREVIEW_ONLY`，不由 installer 自動採用。

| Runtime | Adapter/static status | Project apply | Native destination | Live status |
|---|---|---:|---|---|
| Codex 0.153.4 | `NATIVE_IMPLEMENTED` / `VERIFIED` | `HOST_MANAGED` | `PREVIEW_ONLY`; 不寫 `.codex/config.toml` | `TRANSPORT_BLOCKED` |
| Claude Code 2.1.235 | `READ_ONLY_IMPLEMENTED` / `VERIFIED` | `HOST_MANAGED` | `PREVIEW_ONLY`; 不寫 `.claude/settings*.json` | `RUNTIME_BLOCKED` |
| OpenCode 1.18.25 | `READ_ONLY_IMPLEMENTED` / `VERIFIED` | `HOST_MANAGED` | `PREVIEW_ONLY`; 不寫 `opencode.json` | `PROVIDER_BLOCKED` |
| Hermes v0.20.0 | `NOT_IMPLEMENTED` / `PARTIAL` | status only | none | `PROVIDER_BLOCKED` |

Hermes 不會產生假 distribution；CLI 只輸出 status-only package，`artifacts=[]`、
`installable=false`。

## Runtime detection

Runtime detection 不在 module import、schema validation、static compile 或普通
tests 發生。明確執行 `detect` 時，才可使用：

```text
<runtime> --version
```

process envelope 是 explicit argv、`shell=False`、`stdin=DEVNULL`、capture-only、
短 timeout；不執行 no-args、doctor、auth、login、provider、model invocation。只保留
runtime ID、executable availability、observed version 與 contract match；raw stdout/
stderr 不進結果。

本 phase 的已安裝 Codex version probe 與 static status 都不能解除
`CODEX_LIVE_TRANSPORT_BLOCKED`。

## InstallPackage

`tools/v3/installer.py` 的 `build_install_package()` 只接受已驗證的 generated
`artifact-manifest.json`、Phase 3I `InstallationPlan` 與 version-matched target
contract。Package 會保存：

- plan、snapshot、runtime contract、target contract、source manifest digest；
- project root 的不可逆 reference/identity digest，而不是完整 project tree；
- exact source/destination relative paths、content/source digest、lifecycle、預期
  destination state 與 authoritative action；
- excluded ephemeral artifacts 與原因；
- `apply_allowed` / `installable`，不壓成一個 runtime `READY`。

No-route Codex package 的觀察結果是 6 個可 persistent 的 metadata/projection
artifacts，`codex/selected-skills.json` 以 `EXECUTION_EPHEMERAL` 被排除。任何
package 若包含 ephemeral artifact，validation 會 fail closed。

## Project scope and user/global scope

`PROJECT` 是唯一可 APPLY scope，而且必須傳入明確、已存在、非 symlink 的 project
root；home root、runtime global directory、symlink parent、外部 path 都拒絕。

`USER` / `GLOBAL` 只允許 preview。Phase 3J 不會寫入：

```text
~/.codex/                 ~/.claude/
~/.config/opencode/       ~/.hermes/
project .codex/config.toml
project .claude/settings*.json
project opencode.json / .opencode/opencode.json
```

也沒有 `--force`、adopt-existing、rename collision 或任何 TOML/JSONC/config
merge engine。

## Preview

預設操作是 preview；只有 `apply` verb 具 mutation authority：

```text
python3 tools/v3/installer.py preview \
  --runtime codex --scope project --project /explicit/project

python3 tools/v3/installer.py apply \
  --runtime codex --scope project --project /explicit/project
```

Preview 顯示 runtime/version、install contract、scope、exact target、action、
ownership state、conflict 與 live warning，並明確輸出 `No changes were made.`。
Phase 3J 測試的 preview 對空 project 產生 6 個 `CREATE`，對已安裝內容產生全數
`NO_OP`。

## Pre-apply revalidation

`apply` 不信任 stale preview。寫入前重新驗證：

1. explicit project root reference/identity；
2. target contract/version/digest；
3. source artifact manifest 與 snapshot digest；
4. package self-digest；
5. ownership marker digest；
6. 每個 destination 的 symlink、state、expected digest；
7. source bytes 的 content digest。

任何一項變動都返回 `STALE_PLAN` 或 conflict，並在任何 mutation 前停止。

## Transaction model and ApplyResult

Apply 先對所有 target 做 preflight，再在同一 project filesystem 建立 temporary
stage/backup，最後以 `os.replace` 類 atomic replacement 寫入。ownership marker 在
managed files 之後才寫；每個檔案與 marker 都做 digest verification。中途 fault
會停止，對已知 previous bytes 做 bounded rollback；不能安全 rollback 時返回
`PARTIAL`，不假裝成功。

`InstallationPlan.no_actual_writes` 永遠保持 `true`。執行結果另存為
`ApplyResult`，包含 transaction ID、attempted/completed paths、conflicts、warning、
rollback status 與 `sensitive_data_serialized: false`。

完整 transaction record 只落在明確 project 的
`.agent-skills-matrix/<runtime>/.transactions/<id>.json`，只保存 digest/action
metadata，不保存 prompt、runtime output、skill body、credential 或 environment。

## Ownership, managed update, uninstall and revert

`.asm-installed.json` 只擁有 marker 明列的 exact managed artifact paths，不擁有
`.agent-skills-matrix`、runtime directory 或 project root 本身。marker 綁定：

```text
generator/schema/runtime/scope
package/plan/snapshot/runtime-contract/target/source-manifest digest
artifact source path + source/content digest + lifecycle + origin
transaction ID
```

碰到沒有有效 ASM marker 的現有檔案，一律 `USER_OWNED`；不覆寫。ASM-managed copy
被使用者修改後會是 `MODIFIED_MANAGED`，後續 update/uninstall/revert fail closed。

- `CREATED_BY_ASM`：只有 current content 仍等於 installed digest 才能 uninstall。
- `UPDATED_ASM_MANAGED`：update 前保存 exact previous bytes；uninstall 不假裝可刪，
  revert 只使用 verified backup。
- backup 遺失、digest 不符、current state 改變：`REVERT_UNAVAILABLE` 或 `CONFLICT`，
  不猜測、不重建 previous content。
- uninstall 不做 recursive delete；只刪 marker exact 列出的 unchanged created file，
  並在目錄仍為空且確實由 ASM 建立時才可清理目錄。

## Security review

Phase 3J security checks confirmed:

- no model/runtime/provider/MCP/plugin invocation from compiler/package path；
- no `shell=True`；runtime detection only explicit version probe；
- detection subprocess uses `stdin=DEVNULL` and finite timeout；
- no credential/auth-store/environment read or serialization；
- no raw prompts/stdout/stderr/skill bodies in InstallPackage、ApplyResult 或 audit；
- no existing user runtime config mutation；
- no write through target/parent symlink；
- no permission/model/provider/effort grant from generated metadata；
- user/global apply rejected；Hermes status-only；
- selected-only/NO_SKILL_NEEDED and 214 metadata / zero ranking body reads preserved。

## Regression and verification

| Check | Result |
|---|---|
| full repository tests | PASS — 318/318 |
| Phase 3I productization/schema compatibility | PASS |
| deterministic package/plan | PASS |
| clean apply + repeat apply | PASS; second apply `NO_OP` |
| managed upgrade + exact backup/revert | PASS |
| user-owned/modified/symlink/stale target | PASS; fail closed |
| injected mid-transaction replacement failure | PASS; bounded rollback detected |
| Hermes no-adapter status-only | PASS |
| global runtime config writes | NONE |
| live model execution | NOT RUN by policy |
| `git diff --check` / Python compile / ruff | PASS |
| OCR native diff | `BLOCKED_BY_AUTH`; one precheck returned HTTP 401 `invalid x-api-key` |

## Routing status carried forward

Stage Router remains `STAGE_ROUTER_PRODUCTION_READY`; no score/weight or routing
metadata was changed. Productization consumes the existing immutable snapshot and does
not choose model, effort, provider or runtime. Live statuses remain:

```yaml
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

The next proposed phase is **Phase 3K — User-Scope Installation & Upgrade Contract**.
It must first investigate user destinations, copy/symlink policy and managed upgrade
migration; it must not silently turn this project-only MVP into a global installer.
