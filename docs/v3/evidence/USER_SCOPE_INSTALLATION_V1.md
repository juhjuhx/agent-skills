# Agent Skills Matrix v3 — USER Scope Installation Contract v1

本文件記錄 Phase 3K 的 USER-scope 契約與跨平台生命週期資格結果。這一階段只做
installed-version evidence、fixture-driven contract、symbolic preview 與 lifecycle
推演；不寫入真實 user home、不修改 runtime config、不呼叫 runtime 或 model。

## Decision summary

```text
USER_SCOPE_CONTRACT_READINESS = PREVIEW_ONLY_RECOMMENDED
PROJECT_INSTALLER_READINESS   = READY
USER apply                    = NOT AUTHORIZED IN PHASE 3K
GLOBAL apply                  = PREVIEW_ONLY / UNSUPPORTED
```

原因不是缺少 filesystem API，而是目前三個 runtime 的「user skill discovery path、
exact installed-version behavior、precedence、symlink follow semantics」沒有同時被
repository 的 pinned contract 完整證明。保守結果是可以產生可重現的 USER preview，
但不把 preview 升級成未來 apply 授權。

Machine-readable contract：
[`user-scope-contract-v1.json`](../../../fixtures/v3/productization/user-scope-contract-v1.json)

Machine-readable lifecycle fixture：
[`user-scope-lifecycle-v1.json`](../../../fixtures/v3/productization/user-scope-lifecycle-v1.json)

Implementation：[`user_scope.py`](../../../tools/v3/user_scope.py)

## Repo truth

| 欄位 | 值 |
|---|---|
| repository | `juhjuhx/agent-skills` |
| Phase 3K base | `feat/v3-safe-project-installer` |
| starting HEAD | `c638ba6faf855a7fb2231a22f2fe48624b8e3e69` |
| implementation branch | `feat/v3-user-scope-contract` |
| Stage Router | `STAGE_ROUTER_PRODUCTION_READY`，本 phase 未修改 |
| static productization | `STATIC_PRODUCTIZATION_READY`，本 phase 未改變 |
| project installer | `PROJECT_INSTALLER_READY`，本 phase 回歸保持 |
| Codex live | `CODEX_LIVE_TRANSPORT_BLOCKED`，本 phase 不重試 |
| intra-runtime effort | `NOT_READY` |
| cross-runtime routing | `NOT_READY` |
| routing metadata records | 214 |
| ranking body reads | 0 |

Phase 3J 已提供唯一可 APPLY 的 PROJECT host-managed staging。Phase 3K 沒有把
`scope=PROJECT` 換成 `scope=USER`，而是新增獨立的 user target/strategy model。

## Product boundary

```text
Canonical skills + RoutingCatalogSnapshot + installed runtime evidence
        ↓
UserScopeContract
        ↓
symbolic USER preview / lifecycle classification
        ↓
future apply design (not implemented here)
```

本 phase 的 `build_user_scope_preview()` 是 pure、deterministic、filesystem-free 的
contract planner。CLI 只讀 fixture、inventory 與 routing metadata；沒有 runtime
version probe、auth/status probe、model invocation 或 real-home inspection。

`apply --scope user` 在 CLI 解析完 scope 後立即回傳：

```text
USER_SCOPE_APPLY_NOT_AUTHORIZED
```

這個拒絕早於 project root、destination 或 runtime executable resolution；直接呼叫
既有 `apply_install_package()` 也有同一個 fail-closed guard。

## Installed-version evidence

Installed/runtime contract 是 authority；current first-party documentation 只是
supporting evidence：

- Codex pinned contract：`codex-cli 0.153.4`、`rust-v0.153.4`、source ref
  `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`。現有 pinned contract 是 config/effort
  subset，沒有 user skill-loader path，因此不能把 current main 的 path 當成
  0.153.4 的 release proof。Current loader source 可參考
  [OpenAI Codex skill loader](https://github.com/openai/codex/blob/main/codex-rs/core-skills/src/loader.rs)。
- Claude pinned runtime：`2.1.235`，installed contract 證明 Native Skills surface，
  但沒有 immutable release/source commit；personal path 以
  [Claude Agent Skills documentation](https://code.claude.com/docs/en/agent-sdk/skills)
  作 supporting evidence。
- OpenCode pinned runtime：`1.18.25`、tag `v1.18.25`、commit
  `cb7d8b2f5e44876ef98b661dc10590c915af3a9f`。installed contract 證明 native skill
  surface，但不包含完整 global discovery matrix；path 與目前 precedence 以
  [OpenCode Agent Skills documentation](https://opencode.ai/docs/skills) 作 supporting
  evidence。

因此「文件目前列出某個路徑」與「這個 pinned runtime 可安全 APPLY」被刻意分開。

## Per-runtime native destinations

| Runtime | observed version / ref | candidate user roots | evidence classification | Phase 3K verdict |
|---|---|---|---|---|
| Codex | 0.153.4 / rust-v0.153.4 / `3d2ee51c…` | `${HOME}/.agents/skills`; `${CODEX_HOME}/skills` | `UPSTREAM_ONLY`; `LEGACY`; loader path 未被 pinned config contract 證明 | `PREVIEW_ONLY` |
| Claude Code | 2.1.235 / no immutable source ref | `${HOME}/.claude/skills` | current first-party personal path；installed path/precedence/symlink lifecycle 未完整 pinned | `PREVIEW_ONLY` |
| OpenCode | 1.18.25 / `cb7d8b2f…` | `${XDG_CONFIG_HOME}/opencode/skills`; `${HOME}/.claude/skills`; `${HOME}/.agents/skills` | current docs candidate；1.18.25 narrow contract 未完整 pinned discovery matrix | `PREVIEW_ONLY` |
| Hermes | v0.20.0 / no adapter | none | adapter `NOT_IMPLEMENTED`; no fake user distribution | `NOT_IMPLEMENTED` |

`native_project_skill_roots` 也被記錄在 contract，但不能用 project path 的證據替代
user path 的證據。`RUNTIME_USER_CONFIG` 全部維持 out of scope，沒有為了 skill discovery
去改 TOML、JSON、JSONC、settings、CLAUDE.md、MCP 或 plugin config。

## Shared discovery analysis

`${HOME}/.agents/skills` 是 Codex/OpenCode 最有價值的 shared-tree candidate：current
Codex source 與 current OpenCode documentation 都能找到相容線索。但 Codex 0.153.4
的 pinned loader behavior 沒有在本 repository contract 中完成 release-level proof，
OpenCode 1.18.25 的 contract 也只 pin 了 benchmark 使用的 native skill surface。

所以 Phase 3K 的結論是：

```text
shared native directory = promising candidate
shared native directory = NOT verified for future apply
```

Claude 的 personal root 另列為 `${HOME}/.claude/skills`；沒有偷偷把 Claude 變成
`.agents/skills` 的 consumer，也沒有把三個 runtime 的 collision/precedence 混在一起。

## Distribution strategy matrix

| Strategy | Runtime evidence | Linux | macOS | Windows | lifecycle / failure boundary |
|---|---|---|---|---|---|
| `NATIVE_SHARED_DIRECTORY` | Codex/OpenCode candidate，未完成 installed proof | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | discovery/precedence 未證明即不可 apply |
| `MANAGED_COPY` | filesystem mechanics 可描述，native discovery 仍須 runtime proof | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | derived copy 綁 canonical digest；user collision 保留 |
| `DIRECTORY_SYMLINK` | runtime follow semantics 未證明 | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | `SUPPORTED_WITH_PRECONDITION` | target relocation、broken link、runtime follow 必須重驗 |
| `FILE_SYMLINK` | installed runtime path semantics 未證明 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | 不提供 optimistic fallback；目前 `UNVERIFIED` |
| `WINDOWS_JUNCTION` | 只屬平台候選，不是 runtime discovery proof | `UNSUPPORTED` | `UNSUPPORTED` | `SUPPORTED_WITH_PRECONDITION` | junction identity/escape/discovery 必須 separately prove |
| `CONFIG_REFERENCE` | 需要修改 user-authored runtime config | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | Phase 3K out of scope；不做 config merge |
| `UNSUPPORTED` | fail-closed sentinel | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | 不產生 distribution artifact |

這些結果分別表示「策略與 OS 的候選能力」，不是 apply 授權。Runtime-level support
仍取 intersection；目前 Codex、Claude、OpenCode target 都含 `strategy_support=UNKNOWN`
或 `PREVIEW_ONLY`，所以不會因 OS 可以建立 symlink 就變成可安裝。

重要 invariant：preview 選定 `DIRECTORY_SYMLINK` 時永遠顯示
`DIRECTORY_SYMLINK`；symlink 不可用不會靜默變成 `MANAGED_COPY`。反向亦同。

## Symbolic target and ownership model

Contract 只使用 `${HOME}`、`${ASM_USER_DATA}`、`${XDG_CONFIG_HOME}`、`${CODEX_HOME}`、
`${PROJECT}` 等 symbolic roots。USER preview 不保存真實 username、absolute home path、
credential、environment、auth store 或 runtime output。

未來 central manifest 的候選位置是：

```text
${ASM_USER_DATA}/v3/user-installations/manifest.json
```

它若日後實作，只能記錄 package/snapshot/runtime contract digest、strategy、exact
managed paths、source/content digest 與 transaction reference。它不擁有 `$HOME`、
`.agents`、`.claude`、`.config/opencode` 或其他 parent directory。Ownership 只綁定
marker 明列的 exact skill directory/file。

同名 path 的狀態分為：

```text
ABSENT → 可在 future apply preview 中列為 CREATE
ASM_MANAGED → 可進入 digest/ownership revalidation
USER_OWNED → CONFLICT；不覆寫、不 adopt、不 rename
AMBIGUOUS → CONFLICT / 保留
UNKNOWN → 未檢查 real home；不得假設安全
```

Phase 3K 的 preview 使用 `UNKNOWN` 作為預設 collision state，因為真實 user home
明確禁止被檢查。Lifecycle fixture 只使用 virtual-home examples。

## Upgrade, removal and revert model

`user-scope-lifecycle-v1.json` 固定了 snapshot A→B 的 bounded examples：

| Transition | Outcome |
|---|---|
| digest 相同 | `UNCHANGED` |
| canonical source digest 改變、仍是未修改 ASM artifact | `CONTENT_UPDATED` |
| 新增 canonical skill | `ADDED` |
| 新 snapshot 移除且 path 仍是未修改 ASM artifact | `REMOVED` candidate |
| user 修改 managed copy | `CONFLICT_USER_MODIFIED`；保留 |
| ownership marker 消失或 collision 不明 | `CONFLICT_OWNERSHIP_LOST` |
| runtime target 改變 | `RUNTIME_TARGET_CHANGED` |
| strategy 改變 | `STRATEGY_CHANGED` |
| 名稱相似但沒有 explicit provenance | 不推論 rename；拒絕 implicit rename |
| explicit rename provenance | `RENAMED` |

Removed skill 只有在 ownership、current digest、previous evidence 都相符時，才是
future deletion candidate；不做 recursive broad deletion。Revert 必須有 exact previous
bytes/link target 與可信 backup reference；缺少 backup 時是 `REVERT_UNAVAILABLE`，不
重建猜測內容。

Symlink lifecycle 額外追蹤 link path、target、target digest/version、target existence、
relative/absolute 形式、repository relocation/deletion 與 canonical mutation。直接
link 到 developer checkout 不能當成穩定 user product store；此風險是採用 link strategy
前的未決條件。

## PROJECT → USER and coexistence

PROJECT 與 USER 是兩個獨立 transaction：

```text
install USER (future, separately authorized)
        + optional uninstall PROJECT (separate explicit transaction)
```

USER 出現不會自動刪除 PROJECT。USER + PROJECT duplicate 是否是有意的 override，取決於
runtime 的已證明 precedence；目前不把 `UNKNOWN` precedence 變成自動 dedup 或覆寫。
這避免使用者原本的 project-specific skill 被 global distribution 偷換。

## Full catalog discovery vs execution materialization

USER discovery preview 可以列出完整 214 筆 canonical metadata/source digest，因為這
代表 runtime lazy discovery 的 derived entries；它不等於把 214 個 body preload 到每次
execution。

```text
USER DISCOVERY DISTRIBUTION
  214 metadata/source references
  body_materialized = false

EXECUTION MATERIALIZATION
  StageRoute selected-only
  NO_SKILL_NEEDED = zero selected body
```

Canonical source 永遠是 `skills/<skill>/SKILL.md`；user copy/tree 是
`DERIVED / MANAGED / REGENERABLE / NON_CANONICAL`。preview 只保存 source path/digest
與 symbolic destination，不保存 raw body。

## Preview package and CLI

例：

```text
python3 -m tools.v3.installer preview \
  --runtime claude-code \
  --scope user \
  --platform macos \
  --format json
```

Result 會帶有：

- `scope=USER`、`apply_allowed=false`、`no_actual_writes=true`、`authorization=PREVIEW_ONLY`；
- runtime/version、runtime contract digest、selected strategy、OS support；
- symbolic destination、user manifest symbolic path、source snapshot digest；
- planned managed path/source digest（214 entries，body 未 materialize）；
- collision inspection note（預設不讀 real home）；
- live/static status warning；
- project/user independent coexistence 與 selected-only lifecycle。

Hermes preview 只回傳 status-only target，不會合成假 adapter 或假 skill tree。

## Security review

| Invariant | Result |
|---|---|
| real user home writes | NONE |
| USER apply | fixed rejection `USER_SCOPE_APPLY_NOT_AUTHORIZED` |
| GLOBAL apply | unchanged preview-only/deferred |
| runtime/model/provider execution | NONE |
| auth/config/credential reads | NONE |
| MCP/plugin execution | NONE |
| SKILL.md body execution | NONE |
| raw skill body/prompt/output persistence | NONE |
| symbolic path traversal | rejected by contract validation |
| user-owned overwrite/adoption | not available |
| strategy fallback | prohibited and tested |
| execution-ephemeral persistence | not included in user discovery plan |
| Stage Router / weights | unchanged |

## Verification evidence

Focused USER contract tests cover 25 cases, including virtual-home lifecycle, path
ambiguity, strategy preservation, collision classification, explicit rename, migration,
CLI rejection and CLI preview. Phase 3J project transaction tests remain unchanged and are
run in the full suite.

The user-scope contract digest and lifecycle fixture digest are checked before use. Invalid
or stale contract data fails closed; no current-main runtime behavior is silently inherited.

## Per-runtime verdict

```text
CODEX_USER_SCOPE    = PREVIEW_ONLY
CLAUDE_USER_SCOPE   = PREVIEW_ONLY
OPENCODE_USER_SCOPE = PREVIEW_ONLY
HERMES_USER_SCOPE   = NOT_IMPLEMENTED
```

No runtime currently satisfies every Phase 3K `READY_FOR_FUTURE_APPLY` condition. In
particular, Codex path ambiguity and all three runtimes' exact installed discovery/lifecycle
proof remain bounded gaps. This is why the phase recommends preview-only rather than claiming
USER_SCOPE_CONTRACT_READY.

## Next bounded proposal

Do not implement automatically. If user-scope value justifies further work, propose a narrow
Phase 3L only after selecting a specific runtime and strategy whose installed-version path,
precedence, collision and lifecycle evidence is complete. A plausible first candidate is
Claude-only `MANAGED_COPY` under a separately proven `${HOME}/.claude/skills` contract; the
current evidence is not sufficient to authorize it yet. Codex/OpenCode shared discovery
should remain a research/contract question, not a silent fallback.

Live tracks stay unchanged:

```text
CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS = NOT_READY
CROSS_RUNTIME_ROUTING_READINESS = NOT_READY
```
