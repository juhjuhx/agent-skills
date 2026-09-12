# Agent Skills Matrix v3 — Integration Checkpoint V1

本文件是 Phase 3M 的目前契約稽核。它不實作 Claude USER apply，也沒有對真實
`HOME`、runtime、provider 或 model 做任何操作。歷史 evidence 維持原樣；本文件只
標示目前 authoritative contract 與後續必要的 contract delta。

## Decision

```yaml
USER_APPLY_ARCHITECTURE_READINESS: USER_APPLY_ARCHITECTURE_PARTIAL
CLAUDE_USER_APPLY_ELIGIBILITY: NEEDS_CONTRACT_CHANGE
STACK_INTEGRATION_STATUS: STACK_SAFE_TO_CONTINUE_TO_3N
STAGE_ROUTER_PRODUCTION_READY: true
STATIC_PRODUCTIZATION_READY: true
PROJECT_INSTALLER_READY: true
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
real_home_mutation: false
runtime_model_invocations: false
```

目前 stack 已能以一條一致的 static/project mutation path 運作，且本 checkpoint
修正了兩個實際的整合漂移：`operation/action` 矛盾不再被接受；package 的
`runtime_contract_digest` 必須同時符合 generated manifest 與 install target。可是
generic USER package builder/executor 仍刻意是 preview-only，Phase 3J 的 transaction
仍以 PROJECT root 為 apply 邊界，跨 process crash recovery 也只有 bounded manual
recovery。因此不能把 Phase 3L 的 `CLAUDE_USER_CONTRACT_READY` 當成 USER mutation
authorization。

## Repo truth

| 欄位 | 結果 |
|---|---|
| repository | `juhjuhx/agent-skills` |
| worktree | `<workspace>/agent-skills-v3-phase2` |
| starting branch | `feat/v3-claude-user-contract` |
| checkpoint branch | `chore/v3-integration-checkpoint` |
| expected starting HEAD | `d8d7248438f724e29c78998e1d66eb05193c93d5` |
| checkpoint base | `feat/v3-claude-user-contract` at `d8d7248438f724e29c78998e1d66eb05193c93d5` |
| local HEAD before checkpoint commit | `d8d7248438f724e29c78998e1d66eb05193c93d5` |
| Stage Router | `STAGE_ROUTER_PRODUCTION_READY`；本 phase 未修改 |
| canonical metadata | 214 records；ranking body reads = 0 |
| live tracks | Codex transport blocked；cross-runtime not ready；本 phase 未重試 |
| `git fetch origin` | 未完成：linked worktree 的 shared gitdir `FETCH_HEAD` 權限被環境拒絕；沒有改動 refs/history |

`git status`、branch、HEAD 與 stack ancestry 均以 local repository truth 核對。fetch
限制是工作環境限制，不是 productization 或 installer 的 runtime failure。

## Dogfood route

本 phase 是 contract review，不是 runtime dogfood。resident `using-superpowers`
仍是 authority；route 只載入本任務需要的程序，沒有重新選技能或執行任何
`SKILL.md` command。

```text
Understand  → SKILLS_SELECTED(using-superpowers)
Design      → SKILLS_SELECTED(Agent Development)
Implement   → SKILLS_SELECTED(addyosmani-test-driven-development)
Security    → SKILLS_SELECTED(codex-security:validation)
Review      → SKILLS_SELECTED(addyosmani-code-simplification)
Verify      → SKILLS_SELECTED(codex-engineering-guardrails:code-verification)
Live        → NO_SKILL_NEEDED(reason=Phase 3M forbids runtime/model invocation)
Handoff     → SKILLS_SELECTED(using-superpowers; verification)
```

Stage Router、routing weights、runtime adapters 與 model/effort policy 都沒有變更。
既有 route evidence 的歷史記錄見 [Phase 3L route](PHASE3L_CLAUDE_USER_ROUTE.md)。

## Stack map

| Phase / branch | immutable HEAD | base | current semantic role | mutation relevance |
|---|---|---|---|---|
| 3H / `fix/v3-stage-router-defect-closure` | `9e00d543dc312c6f9bd31c33d6a235cc4a58cd72` | prior routing/eval stack | Stage Router defect closure and production gate | required as snapshot/selection authority |
| 3I / `feat/v3-static-productization` | `109d78898916acb34607bc8905656fa4c2aa41a7` | 3H | deterministic compiler, generated manifests, InstallationPlan | required |
| 3J / `feat/v3-safe-project-installer` | `c638ba6faf855a7fb2231a22f2fe48624b8e3e69` | 3I | PROJECT InstallPackage, ownership, transaction, rollback | required; current transaction authority |
| 3K / `feat/v3-user-scope-contract` | `8ba23daed5e3ef13c6aceea218609c45518d88b7` | 3J | generic symbolic USER preview/lifecycle | required as generic USER vocabulary |
| 3L / `feat/v3-claude-user-contract` | `d8d7248438f724e29c78998e1d66eb05193c93d5` | 3K | Claude 2.1.235 discovery evidence and managed-copy preference | required as Claude specialization |
| 3M / `chore/v3-integration-checkpoint` | checkpoint worktree | 3L | contract composition, drift fixes, current index | required before a future 3N apply design |

No branch was merged or rebased. Phase 3C–3G runtime evidence remains historical
context only; it is not a USER-installation authority.

## Contract lineage

The current authoritative path is:

```text
root-level canonical <skill>/SKILL.md
  + .superpowers/SKILLS_INDEX.json
  + registry/v3/skill-routing-metadata.json
        ↓
RoutingCatalogSnapshot
        ↓
StageRoute
        ↓
CompiledExecutionBundle (runtime-neutral, execution-local)
        ↓
GeneratedArtifactManifest + runtime projection
        ↓
InstallationPlan (no writes; action-bearing intent)
        ↓
InstallPackage (persistent artifact candidate; project apply only today)
        ↓
ownership marker + bounded transaction
        ↓
ApplyResult / sanitized transaction record
```

| contract / artifact | introduced | current authority | current fixture/schema | future USER role |
|---|---|---|---|---|
| canonical skill source | pre-v3 | repository skill directory plus `.superpowers/SKILLS_INDEX.json` | registry source records with `relative_path`/digest | source of truth; never generated output |
| `RoutingCatalogSnapshot` | v3 routing | `tools/v3/routing_catalog.py` | routing registry + overlay | immutable snapshot input |
| `StageRoute` | v3 routing | `tools/v3/stage_router.py` | route fixtures / route records | intent only; no runtime path/permission grant |
| `CompiledExecutionBundle` | v3 execution | `tools/v3/execution_bundle.py` | `compiled-execution-bundle.schema.json` | execution-ephemeral; never install |
| generated distribution | 3I | `tools/v3/productization.py` | `generated-artifact.schema.json`, `.asm-generated.json` | source for persistent package filtering |
| `InstallationPlan` | 3I, normalized 3J | `tools/v3/productization.py`; validation in `tools/v3/installer.py` | `installation-plan.schema.json` | no authorization; future USER plan keeps `no_actual_writes=true` |
| `InstallPackage` | 3J | `tools/v3/installer.py` | `install-package.schema.json` | generic future USER package; current builder/executor rejects USER apply |
| generated ownership marker | 3I | productization output `.asm-generated.json` | generated-artifact ownership fields | owns generated output only |
| installed ownership marker | 3J | installer `.asm-installed.json` | marker validation in `installer.py` | future exact-scope ownership record |
| `ApplyResult` | 3J | installer `_result()` | `apply-result.schema.json` | actual outcome only |
| generic USER preview | 3K | `tools/v3/user_scope.py` | `user-scope-contract-v1.json` | target vocabulary and preview; not authorization |
| Claude USER specialization | 3L | `tools/v3/claude_user_scope.py` | three Claude user fixtures | binds version, collisions, strategy, and user contract |
| live evaluation | 3C–3G | `tools/v3/live_benchmark.py` + V1–V9 | `MODEL_RUNTIME_EVAL_V9.md` | orthogonal; cannot authorize filesystem mutation |

The repository's canonical layout is root-level skill directories rather than a
literal `skills/` wrapper. The semantic rule is unchanged: a generated runtime tree,
project package, or future user copy is derived and non-canonical.

## Current contract index

The compact index is maintained separately at
[`CURRENT_V3_CONTRACT_INDEX.md`](../CURRENT_V3_CONTRACT_INDEX.md). It intentionally
names one authority per semantic layer and marks historical compatibility readers.

## Superseded assumptions

| earlier assumption | current interpretation | evidence / action |
|---|---|---|
| `operation` alone described the filesystem mutation | `action` is the only normalized mutation semantic; `operation` is descriptive compatibility data and must map consistently | Phase 3M adds `PLAN_OPERATION_ACTIONS` validation and a regression test |
| `conflict_outcome` or `overwrite_policy` could drive apply | they are plan/report preconditions; executor consumes package `action` | preserved; no second action vocabulary |
| any generated artifact could be installed | only `INSTALL_PERSISTENT`/`PROJECT_PERSISTENT` survive package filtering; `EXECUTION_EPHEMERAL` is rejected | 3I/3J lifecycle tests |
| a native runtime destination was an install target | current verified project targets are host-managed staging; native destinations remain preview-only unless version-bound | `install-targets-v1.json` |
| `scope=USER` in a schema meant USER apply was available | schema reserves the scope; current builder emits preview/non-installable state and apply fails closed | `USER_SCOPE_APPLY_NOT_AUTHORIZED` |
| `CLAUDE_USER_CONTRACT_READY` meant package authorization | it means discovery/strategy evidence is sufficient for a later Claude-only contract phase | Phase 3L and Claude fixture `apply_allowed=false` |
| `INSTALL_USER_SEPARATELY` was an executor operation | it is a descriptive two-transaction migration record from 3K | no installer consumes it as action |
| `actions_attempted`/`actions_completed` were action enum names | public `ApplyResult` records exact relative paths; action enum is stored in package/marker | schema and implementation agree on path-list semantics |
| release/current-doc path evidence proved all Claude behavior | personal root is artifact-bound, while precedence/symlink/bundled behavior retains weaker evidence classes | Phase 3L claim table |
| old Phase3L NEXT prompt remained current | handoff now describes Phase 3N only after this checkpoint's contract delta | updated in this phase |

Historical documents retain their original terminology. The table above is the current
interpretation, not a rewrite of earlier evidence.

## Operation semantics

`InstallationPlan` still exposes both `operation` and `action` because the earlier
reporting field is part of the current public plan schema. They now have an explicit
relationship:

| descriptive `operation` | permitted authoritative `action` |
|---|---|
| `CREATE_DIRECTORY` | `CREATE`, `UPDATE_MANAGED` |
| `CREATE_GENERATED_FILE` | `CREATE`, `UPDATE_MANAGED` |
| `LINK_OR_REFERENCE_CANONICAL_SKILL` | `CREATE`, `UPDATE_MANAGED` |
| `WRITE_PROJECT_CONFIG` | none; config mutation is not a valid installer action |
| `SKIP_UNSUPPORTED_RUNTIME` | `SKIP_UNSUPPORTED` |
| `SKIP_USER_OWNED` | `SKIP_USER_OWNED` |
| `CONFLICT` | `CONFLICT` |
| `NO_OP` | `NO_OP` |
| `WARN_LIVE_BLOCKED` | `WARN` |

`tools/v3/installer.py` validates this table before building a package. The apply
subset (`CREATE`, `UPDATE_MANAGED`, `NO_OP`) and conflict subset are implementation
filters, not a competing vocabulary. `InstallPackage` has no `operation` field, so
the executor cannot accidentally interpret the descriptive field.

## Ownership and transaction composition

The one ownership principle is exact-path, digest-bound, fail-closed ownership:

```text
canonical source digest + snapshot digest
  → generated marker owns generated output paths only
  → installed marker/manifest owns listed destination paths only
```

- A marker never owns `$HOME`, `.claude`, `.agent-skills-matrix`, or another runtime
  parent directory merely because ASM created a child.
- A missing/invalid marker means no adoption. Existing content is user-owned or
  ambiguous, never an automatic update target.
- A changed managed copy is `MODIFIED_MANAGED` and becomes a conflict.
- `CLAUDE_SYNCED` is Claude-owned and is never adopted, overwritten, backed up for
  overwrite, or deleted by ASM.
- `BUNDLED_COLLISION`, `PROJECT_DUPLICATE`, and `CLAUDE_SYNCED` extend the collision
  vocabulary; they do not grant a mutation exception.
- Canonical source remains authoritative. User edits to a derived destination never
  flow back into the canonical skill library.

Phase 3J already provides the transaction shape a future USER apply should reuse:

```text
validate package → preflight every destination → stage bytes
→ revalidate → bounded atomic replacement → ownership state last
→ verify digests → complete audit record → bounded rollback
```

The current implementation is PROJECT-only by design (`_safe_project_root`, project
target inventory, and the explicit USER guard). A future 3N change may parameterize
the root/target/manifest contract, but must not create a second USER transaction
engine.

The crash/interruption classification is `BOUNDED_MANUAL_RECOVERY`, not fully
deterministic. An in-process failure rolls back known previous bytes, but a process
death after the first destination replace and before the ownership marker can leave
partial bytes without a committed transaction record. A process death after the
marker and before final verification can leave marker/content state requiring digest
inspection. A future USER apply must add a bounded recoverable pre-commit state or
fail closed on detectable staging/partial state; it cannot assume `finally` runs after
process death.

## InstallationPlan / InstallPackage boundary

| layer | current meaning |
|---|---|
| `InstallationPlan` | immutable intended operations; `no_actual_writes=true`; snapshot/runtime/artifact references |
| `InstallPackage` | immutable filtered persistent-artifact candidate bound to exact state; not authorization itself |
| `ApplyResult` | actual explicit apply/uninstall/revert outcome and sanitized transaction identity |

The `InstallPackage` schema can represent `PROJECT`, `USER`, and `GLOBAL`, but the
current builder excludes USER artifacts and sets `apply_allowed=false` outside PROJECT;
`apply_install_package()` rejects USER before filesystem resolution. This is a reserved,
fail-closed shape, not an implicit USER implementation.

A future generic USER package needs a versioned USER target binding containing the Claude
fingerprint/contract revision, `MANAGED_COPY`, symbolic/virtual root identity, collision
observations, exact managed paths, and expected destination states. The existing
`install_target_digest` and `runtime_contract_digest` can remain generic fields after
the USER target is accepted by builder/revalidator. Current project-root fields and
project-only target inventory are not enough by themselves. No `ClaudeInstallPackage`
should be created.

## Claude composition and managed-copy lifecycle

The composition is intentionally one-way:

```text
generic USER contract (preview-only)
  + Claude 2.1.235 discovery contract
  + MANAGED_COPY strategy evidence
  → Claude-specific preview (still apply_allowed=false)
```

The future lifecycle is modeled only in virtual fixtures:

```text
canonical <skill>/SKILL.md
  → ${ASM_USER_DATA}/v3/claude (stable derived store)
  → ${HOME}/.claude/skills/<slug>/SKILL.md (future explicit apply)
  → exact-path ownership manifest
  → upgrade / manual-modification conflict / removal / exact revert
```

It proves no generated copy becomes canonical, no manual destination edit flows back,
no user-owned or synced skill is adopted, and no bundled collision is silently
overridden. `PROJECT` and future `USER` operations remain independent. The actual USER
transaction is intentionally absent from this phase.

`KEEP_TWO_LEVEL_STORE` is the current recommendation. The ASM-owned derived store
provides stable staging, source provenance, backup/revert, and repository-relocation
independence; the Claude personal directory remains the native managed copy. The byte
duplication is an explicit lifecycle tradeoff, not a reason to link directly into a
moving checkout.

For USER ownership, a central manifest under `${ASM_USER_DATA}/v3/...` should be the
authoritative future record with exact paths. Do not put an arbitrary marker inside a
Claude skill directory unless a version-bound discovery contract requires it. The
current `.asm-generated.json` owns compiler output and `.asm-installed.json` owns the
current PROJECT target only.

## Collision and coexistence contract

| state | future behavior |
|---|---|
| `CLAUDE_SYNCED` | Claude-owned; never owned, overwritten, backed up for overwrite, or removed |
| `BUNDLED_COLLISION` | current Phase 3L policy is explicit confirmation; because generic package has no bounded confirmation token, 3N should initially block |
| `PROJECT_DUPLICATE` | preserve both scopes; show precedence warning; never mutate the other scope |
| `USER_OWNED` / `AMBIGUOUS` / `UNKNOWN` | conflict; no adoption, rename, force, or silent strategy fallback |

Project→User migration means “install USER separately, optionally uninstall PROJECT
separately”; it never means move or implicit project deletion. Runtime precedence is a
warning until installed-version behavior is stronger than the Phase 3L current-doc
evidence.

## Stale-state chain and runtime lifecycle

```text
canonical skill digest
  → snapshot/source-index digest
  → StageRoute digest
  → generated content/manifest digest
  → InstallationPlan digest
  → InstallPackage digest
  → runtime contract + install-target digest
  → expected destination state/digest
  → ownership marker/manifest digest
```

The current project revalidator now checks package runtime-contract digest against both
generated manifest and install target; the new regression test proves tampering aborts
before mutation. Future Claude USER apply must append the Claude user-contract revision,
fingerprint, strategy, collision observations, and symbolic user-target digest. Any
stale input stops the entire apply; no partial recompile is permitted.

`Claude 2.1.235 → another version` is `RUNTIME_REQUALIFICATION_REQUIRED` for new
USER apply/update. Existing exact managed artifacts should remain previewable for
cleanup even when the Claude executable is absent; cleanup must use recorded safe paths
and ownership evidence rather than requiring inference or the current runtime binary.

## Failure injection and verification scope

Existing Phase 3J virtual-project tests cover stale destinations, symlink parents,
marker tampering, managed-upgrade backups, and deterministic replacement failure with
successful rollback. Phase 3M adds 8 focused tests covering:

| case | result |
|---|---|
| contradictory `operation/action` | rejected before package construction |
| tampered runtime-contract digest | `STALE_PLAN` before mutation |
| `NO_SKILL_NEEDED` | zero body files and no persistent skill body |
| generic vs Claude USER preview | both remain preview-only; no package authorization |
| project/user migration | `shared_transaction=false` |
| cleanup without runtime probe | project uninstall remains independent of runtime executable |
| route→projection→plan→package | snapshot/route/lifecycle bindings retained |
| package/result roles | schema layers remain distinct |

No real HOME, runtime, provider, model, config, auth, MCP, plugin, or hook was
accessed. USER fault injection remains a future 3N gate, not a hidden apply.

## Static/integration performance

Three local virtual-project runs measured the existing no-skill path (snapshot load,
static compile, package build, and distribution validation). Median wall times were:

| segment | median |
|---|---:|
| snapshot validation/load | 732.37 ms |
| static compile | 932.51 ms |
| package build | 21.74 ms |
| generated distribution validation | 468.22 ms |
| end-to-end local checkpoint path | 2,153.14 ms |

These are static filesystem measurements only; they are not runtime latency, model
latency, token usage, or cost evidence. No daemon/cache or second transaction engine
was introduced.

## Schema consistency and dead code

The schemas use one digest shape and one scope enum. `operation` is a descriptive
InstallationPlan field; `action` is authoritative; package artifacts intentionally
contain only `action`. `no_actual_writes` belongs to plan/preview, while
`apply_allowed` belongs to the package/preview gate. Backup records are internal marker
state; transaction IDs are result/audit identities. These are different layers, not
conflicting meanings. No schema version bump was necessary.

The old `operation` field, 3K migration descriptor, generic USER preview, Claude
specialization, and Hermes status-only package are retained as historical/current
compatibility surfaces. No unreachable implementation was removed. A second USER
transaction engine was deliberately not created.

## Security review

- No real HOME or runtime config write; no runtime/model/provider/auth/MCP/plugin call.
- No credential, environment, prompt, skill body, raw output, or session persistence.
- No force, adoption, recursive deletion, silent copy/symlink fallback, or bundled
  override.
- Exact-path ownership only; user/synced/ambiguous content is preserved.
- Package, target, manifest, source, destination, marker, and runtime-contract digests
  are revalidated before project mutation.
- No Stage Router weights, runtime adapter, live benchmark, or permission boundary
  changed.

The one OCR precheck returned HTTP 401 (`invalid x-api-key`). Only the sanitized
classification is retained: `OCR_NATIVE_DIFF=BLOCKED_BY_AUTH`; no retry was made.

## Gate interpretation

`USER_APPLY_ARCHITECTURE_PARTIAL` is the precise result: plan/action, ownership, and
transaction shape are coherent; Claude USER composition and managed-copy lifecycle are
well-defined as preview contracts; but USER package/apply acceptance and cross-process
crash recovery are not complete. The stack is `STACK_SAFE_TO_CONTINUE_TO_3N` because
the discovered current-code drift was fixed locally and no history rewrite is needed.

## Next proposal

```text
PHASE 3N — CLAUDE USER-SCOPE APPLY MVP (CONTRACT-CLOSURE GATE)
```

Before any mutation, 3N must first make the generic InstallPackage/target contract
represent a version-bound USER root, Claude user-contract digest, `MANAGED_COPY`, exact
collision/expected-state preconditions, and bounded crash recovery. Only then may it
implement Claude-only USER preview → explicit confirmation → apply, using virtual HOME
first. No Codex/OpenCode/Hermes USER apply, config mutation, provider work, or Phase 4.

The handoff is maintained in [`NEXT_CODEX_PROMPT.md`](../NEXT_CODEX_PROMPT.md).
