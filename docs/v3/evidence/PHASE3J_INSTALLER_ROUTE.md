# Phase 3J Installer Dogfood Route

本 route record 證明 installer 仍是 static/productization plane 的 route consumer，
不是新的 Stage Router，也不是 live execution path。

## Development route

```text
TaskSpec: safe project installer / generator MVP
  → using-superpowers resident authority
  → existing Stage Router / validated RoutingCatalogSnapshot
  → selected implementation and verification procedures only
  → Phase 3I DistributionCompiler
  → filtered InstallPackage
  → explicit PROJECT apply / ApplyResult
```

| Stage | Route emission | 本 phase scope |
|---|---|---|
| Understand | `SKILLS_SELECTED` | using-superpowers resident；讀 Phase 3I contracts/evidence |
| Design | `SKILLS_SELECTED` | Agent Development、Command Development、code-work |
| Plan | `SKILLS_SELECTED` | installation boundary、security validation、anti-bloat |
| Implement | `SKILLS_SELECTED` | installer module、contract schema、target fixture |
| Review | `SKILLS_SELECTED` | security validation、code simplification、ownership/transaction review |
| Verify | `SKILLS_SELECTED` | code-verification、focused/full regression |
| Live execution | `NO_SKILL_NEEDED(reason=live model execution is prohibited in Phase 3J)` | no runtime/model work |
| Handoff | `SKILLS_SELECTED` | evidence/docs、next prompt、draft PR |

實作使用現有 resident `using-superpowers` authority；沒有為了湊數載入完整 skill
catalog，也沒有在 ranking 階段讀取 214 個 `SKILL.md` body。Runtime/model choice
沒有改變 Stage Router ranking。

## Route invariants

- `RoutingCatalogSnapshot` 驗證一次並傳入 Phase 3I compiler；installer 不重跑 route。
- `StageRoute`、`CompiledExecutionBundle`、task-specific selected skill state 皆為
  `EXECUTION_EPHEMERAL`，不可進 persistent install package。
- `NO_SKILL_NEEDED` 保持 zero selected body / zero execution-specific skill artifact。
- installer 只投影既有 runtime static evidence；不選 model、effort、provider 或權限。
- 任何 runtime native path 若缺少 installed-version install proof，留在
  `PREVIEW_ONLY`；可 APPLY 的 target 是 explicit project-local host-managed staging。

## Observed installation route

對 no-route Codex static distribution：

```text
7 generated manifest artifacts
  ├─ 6 persistent package candidates
  └─ selected-skills.json = EXECUTION_EPHEMERAL → excluded

6 project-local destinations
  ├─ 2 INSTALL_PERSISTENT (adapter manifest / runtime contract)
  └─ 4 PROJECT_PERSISTENT (report / status / snapshot / projection)
```

空 project 的所有 destination 初始為 `ABSENT → CREATE`；apply 後相同 package 的
第二次 preview 是 `ASM_MANAGED → NO_OP`。若檔案沒有 valid ASM marker、被修改、是
symlink 或 preview 後 digest 改變，路由會停止於 `USER_OWNED` / `MODIFIED_MANAGED` /
`UNSAFE` / `STALE_PLAN`，不進入部分 apply。

## Runtime status route

| Runtime | Static route | Installer interpretation |
|---|---|---|
| Codex | `NATIVE_IMPLEMENTED / VERIFIED` | project staging 可 apply；live warning=`TRANSPORT_BLOCKED` |
| Claude Code | `READ_ONLY_IMPLEMENTED / VERIFIED` | project staging 可 apply；native `.claude` 只 preview；live=`RUNTIME_BLOCKED` |
| OpenCode | `READ_ONLY_IMPLEMENTED / VERIFIED` | project staging 可 apply；native `.opencode` 只 preview；live=`PROVIDER_BLOCKED` |
| Hermes | `NOT_IMPLEMENTED / PARTIAL` | status-only；沒有假 artifact、沒有 apply target |

這些是 product-status 維度，不是單一 `READY`。Installer 的成功不改變：

```text
CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS = NOT_READY
CROSS_RUNTIME_ROUTING_READINESS = NOT_READY
```

## Evidence references

- compiler compatibility: [`STATIC_PRODUCTIZATION_V1.md`](STATIC_PRODUCTIZATION_V1.md)
- target contract: [`install-targets-v1.json`](../../../fixtures/v3/productization/install-targets-v1.json)
- installer implementation: [`tools/v3/installer.py`](../../../tools/v3/installer.py)
- package contract: [`install-package.schema.json`](../../../schemas/v3/install-package.schema.json)
- result contract: [`apply-result.schema.json`](../../../schemas/v3/apply-result.schema.json)
