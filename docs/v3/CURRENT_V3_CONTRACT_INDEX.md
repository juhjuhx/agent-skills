# Agent Skills Matrix v3 — Current Contract Index

這是 Phase 3O 的 current index。它只列目前 authoritative implementation；較早
phase 的文件仍是不可改寫的 historical evidence。任何未明確列為 current 的
runtime/user claim，不得被當成 mutation authority。

## Status boundary

```yaml
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CLAUDE_USER_CONTRACT_READY: true
CLAUDE_USER_APPLY_AUTHORIZED: false
CLAUDE_USER_APPLY_ENGINE: VIRTUAL_HOME_ONLY
REAL_HOME_APPLY_AUTHORIZED: false
CLAUDE_REAL_HOME_CANARY_READINESS: CLAUDE_REAL_HOME_CANARY_BLOCKED
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Authoritative layers

| layer | current authoritative implementation | contract / fixture | consumer | scope and boundary |
|---|---|---|---|---|
| canonical skill source | repository root-level `<skill-id>/SKILL.md` plus `.superpowers/SKILLS_INDEX.json` | registry source records and canonical source digests | snapshot builder and offline validator | canonical only; generated copies never flow back |
| routing metadata | `tools/v3/routing_catalog.py` | `registry/v3/skill-routing-generated.json`, `skill-routing-curated.json`, `skill-routing-metadata.json` | Stage Router | 214 metadata records; ranking loads zero bodies |
| route selection | `tools/v3/stage_router.py` | `fixtures/v3/router/` and route records | bundle/compiler/adapters | `StageRoute` is intent; no runtime/config authority |
| execution bundle | `tools/v3/execution_bundle.py` | `schemas/v3/compiled-execution-bundle.schema.json` | runtime adapters | execution-local and ephemeral; never install |
| product status | `tools/v3/productization.py` status loaders | `schemas/v3/runtime-product-status.schema.json`, `fixtures/v3/productization/runtime-status-*.json` | report/plan/compiler | install, adapter, static, and live dimensions stay independent |
| canary/status façade | `tools/v3/claude_canary.py` and `installer.py` `status` / `canary-preview` commands | `fixtures/v3/productization/claude-real-home-canary-selection-v1.json`, Phase 3O evidence | read-only real-home inventory and non-authorizing preview | metadata-only; no real-home mutation or runtime invocation |
| static compiler | `tools/v3/productization.py` | `schemas/v3/generated-artifact.schema.json` | productization CLI and installer | pure/static; no runtime subprocess or global write |
| generated artifact | compiler output | `artifact-manifest.json`, `.asm-generated.json` | package builder | derived; owns exact generated paths only |
| plan | `build_installation_plan()` in `productization.py` | `schemas/v3/installation-plan.schema.json` | preview/package builder | immutable intent; `no_actual_writes=true`; `action` authoritative |
| package | `build_install_package()` and `build_user_install_package()` in `installer.py` | `schemas/v3/install-package.schema.json` | explicit PROJECT apply or Claude USER virtual apply; selected-only canary preview | one generic immutable candidate; USER is Claude/MANAGED_COPY/virtual-root only; Phase 3O preview package is non-authorizing |
| mutation result | `_result()` in `installer.py` | `schemas/v3/apply-result.schema.json` | apply/uninstall/revert | actual outcome, not plan or authorization |
| project ownership | marker validation in `installer.py` | `.asm-installed.json` under project staging | project transaction/lifecycle | exact artifacts only; no parent ownership |
| USER recovery journal | USER transaction helpers in `installer.py` | `schemas/v3/transaction-recovery.schema.json` | explicit recovery entrypoint | exact virtual-root/process-crash record; no credentials or body copies |
| generic USER contract | `tools/v3/user_scope.py` plus USER package fields in `installer.py` | `fixtures/v3/productization/user-scope-contract-v1.json`, lifecycle fixture | symbolic preview/migration | preview for other runtimes; Claude virtual apply only |
| Claude USER contract | `tools/v3/claude_user_scope.py` | Claude user-scope, strategy, lifecycle fixtures | Claude USER preview and virtual apply target | version-bound discovery/strategy evidence; narrows USER apply to MANAGED_COPY |
| live evaluation | `tools/v3/live_benchmark.py` and historical V1–V9 docs | `docs/v3/evidence/MODEL_RUNTIME_EVAL_V9.md` | benchmark reporting | orthogonal to filesystem productization |

## Shared semantics

### Installation actions

The normalized action set is:

```text
CREATE
UPDATE_MANAGED
NO_OP
SKIP_USER_OWNED
CONFLICT
WARN
SKIP_UNSUPPORTED
```

`InstallationPlan.operation` is retained as a descriptive compatibility field. The
authoritative mapping and validation live in `tools/v3/installer.py` as
`PLAN_OPERATION_ACTIONS`; `InstallPackage` contains `action` but no `operation`. The
executor therefore never infers mutation from `operation`, `conflict_outcome`, or
`overwrite_policy`.

### Lifecycle

```text
INSTALL_PERSISTENT / PROJECT_PERSISTENT
  → may enter a project InstallPackage after target filtering

EXECUTION_EPHEMERAL
  → StageRoute, CompiledExecutionBundle, selected-skills state, selected body
  → must be excluded from persistent installation
```

### Ownership

Ownership is exact-path and digest-bound. `.asm-generated.json` describes compiler output;
`.asm-installed.json` records the current PROJECT transaction. Neither marker owns its
parent runtime directory or a user home. A future Claude USER manifest should use the
same exact-path principle in `${ASM_USER_DATA}/v3/...`; it must not be a second ownership
model.

### Transaction

The current transaction authority is the Phase 3J flow plus its Phase 3N virtual-USER
specialization in `installer.py`:

```text
all-target preflight
→ same-filesystem staging
→ destination revalidation
→ atomic replacement
→ ownership state last
→ digest verification
→ bounded rollback or deterministic process-crash recovery
```

PROJECT semantics remain unchanged. Claude USER mutation is enabled only for an
explicit existing virtual HOME and `MANAGED_COPY`; real HOME authorization remains
false. The USER journal is process-crash recoverable for the supported virtual model,
but the implementation does not claim power-loss durability.

## USER / Claude composition

| concept | current authority | current status |
|---|---|---|
| generic USER scope | `user_scope.py` plus generic USER package fields in `installer.py` | preview for other runtimes; Claude virtual apply only |
| Claude version/fingerprint/path evidence | `claude_user_scope.py` + Claude fixtures | `CLAUDE_USER_CONTRACT_READY` |
| preferred distribution | Claude strategy fixture | `MANAGED_COPY_PREFERRED` |
| generic USER package | `build_user_install_package()` / `install-package.schema.json` | immutable, digest-bound USER candidate; only virtual Claude apply is enabled |
| Claude USER apply | `apply_user_install_package()` / `recover_user_transaction()` | virtual HOME only; exact confirmation; no real-home authorization |

The future package should remain generic. Its USER target contract must bind scope,
Claude runtime fingerprint/contract digest, managed-copy strategy, symbolic root,
collision observations, expected destination states, and exact managed paths. A Claude
specific package class is prohibited.

## Historical versus current evidence

| historical item | current interpretation |
|---|---|
| Phase 3I native runtime destinations | static/preview evidence unless target contract says otherwise |
| Phase 3K generic Claude target record | generic preview baseline; Phase 3L Claude fixture is the specialized current evidence |
| Phase 3L `CLAUDE_USER_CONTRACT_READY` | permits a later Claude-only apply design; does not set `apply_allowed=true` |
| Phase 3C–3G live statuses | remain unchanged and orthogonal; no live runtime is called in productization/checkpoint |
| `INSTALL_USER_SEPARATELY` | descriptive independent-migration record, not an installer action |

## Canonical references

- [Phase 3I productization route](evidence/PHASE3I_PRODUCTIZATION_ROUTE.md)
- [Phase 3J installer evidence](evidence/SAFE_PROJECT_INSTALLER_V1.md)
- [Phase 3K USER contract](evidence/USER_SCOPE_INSTALLATION_V1.md)
- [Phase 3L Claude contract](evidence/CLAUDE_USER_SCOPE_V1.md)
- [Phase 3M integration checkpoint](evidence/INTEGRATION_CHECKPOINT_V1.md)
- [`tools/v3/productization.py`](../../tools/v3/productization.py)
- [`tools/v3/installer.py`](../../tools/v3/installer.py)
- [`tools/v3/claude_canary.py`](../../tools/v3/claude_canary.py)
- [`tools/v3/user_scope.py`](../../tools/v3/user_scope.py)
- [`tools/v3/claude_user_scope.py`](../../tools/v3/claude_user_scope.py)
- [`schemas/v3/installation-plan.schema.json`](../../schemas/v3/installation-plan.schema.json)
- [`schemas/v3/install-package.schema.json`](../../schemas/v3/install-package.schema.json)
- [`schemas/v3/apply-result.schema.json`](../../schemas/v3/apply-result.schema.json)
- [`schemas/v3/transaction-recovery.schema.json`](../../schemas/v3/transaction-recovery.schema.json)

## Next boundary

Phase 3O completed its preview-only boundary but is blocked from issuing a consumable
authorization. The next work is limited to the two exact evidence gaps: bind a safe
`${ASM_USER_DATA}/v3/claude` destination contract, and provide version-bound bundled
skill collision evidence for Claude Code `2.1.235`. After those are proven, a fresh
preview may be considered. No current document authorizes real USER mutation. Codex
live transport and all runtime-routing readiness states remain unchanged.
