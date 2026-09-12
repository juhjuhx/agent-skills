# Agent Skills Matrix v3 — Claude USER Apply V1

Phase 3N closes the generic USER package and implements the first Claude Code
USER mutation boundary. It is deliberately limited to `claude-code` 2.1.235,
`MANAGED_COPY`, and an explicitly supplied virtual HOME. It does not authorize
real-home installation, runtime invocation, provider access, or model routing.

## Decision

```yaml
CLAUDE_USER_APPLY_ENGINE_STATUS: CLAUDE_USER_APPLY_ENGINE_READY
USER_APPLY_ARCHITECTURE_READINESS: USER_APPLY_ARCHITECTURE_READY
INSTALLER_IMPLEMENTED: true
VIRTUAL_HOME_VERIFIED: true
PROCESS_CRASH_RECOVERY_VERIFIED: true
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
REAL_HOME_APPLY_AUTHORIZED: false
CODEX_LIVE_TRANSPORT_STATUS: CODEX_LIVE_TRANSPORT_BLOCKED
INTRA_RUNTIME_EFFORT_ROUTING_READINESS: NOT_READY
CROSS_RUNTIME_ROUTING_READINESS: NOT_READY
```

## Boundary and contract composition

The mutation path is one generic contract path:

```text
canonical SKILL.md
  → RoutingCatalogSnapshot / StageRoute (execution intent only)
  → static/runtime-neutral artifacts
  → generic InstallPackage(scope=USER)
  → exact USER confirmation
  → Claude target binding
  → virtual-home transaction journal
  → ApplyResult
```

`InstallPackage` remains the only package type. USER packages bind the runtime
version/fingerprint, runtime and USER contract digests, `MANAGED_COPY`, path-free
virtual-root identities, source and artifact digests, collision observations,
exact managed paths, and transaction policy. `InstallationPlan` remains a
no-write intent; `ApplyResult` records actual execution. The package is never
mutated during apply.

The normalized mutation action is `CREATE`, `UPDATE_MANAGED`, `NO_OP`,
`REMOVE`, or `RESTORE` for USER execution, with conflict actions rejected before
mutation. `operation` remains a descriptive plan field only; the executor does
not infer mutation from it.

Execution-ephemeral objects such as `StageRoute`, `CompiledExecutionBundle`,
task-specific selected-skill state, and live records are rejected from a
persistent USER package.

## Claude target

The target is bound to the Phase 3L contract fixture:

| field | bound value |
|---|---|
| runtime | `claude-code` |
| qualified version | `2.1.235` |
| strategy | `MANAGED_COPY` |
| personal destination class | `${HOME}/.claude/skills` |
| stable derived source | `${ASM_USER_DATA}/v3/claude/skills` |
| ownership manifest | `${ASM_USER_DATA}/v3/claude/.asm-user-manifest.json` |
| config mutation | false |
| live/provider claim | none; live status remains blocked |

The ASM store is derived, non-canonical staging and recovery input. Destination
edits never flow back to the store or canonical source.

## Confirmation boundary

The CLI and API require a deterministic confirmation object bound to the exact
package digest, runtime, scope, strategy, virtual target identity, and managed
path count. CLI mutation additionally requires the caller to supply the exact
`--confirm-package-digest`. A changed package, root, collision observation,
source, ownership manifest, or runtime contract requires a new package and new
confirmation.

`CLAUDE_USER_CONTRACT_READY` is not authorization. `--apply` without the
virtual roots, package, strategy, and exact digest fails closed.

## Virtual HOME safety

USER apply requires two existing, absolute, non-symlink directories: a virtual
HOME and a separate ASM user-data root. The roots are rejected when they are
the real process HOME, an ancestor/descendant alias of it, a filesystem root,
a real runtime directory, or one another. No `expanduser`, implicit HOME,
environment-derived authorization, real-home bypass, `--force`, or adopt mode
exists.

The focused tests cover implicit HOME, real HOME, tilde expansion, relative
aliases, symlink roots, and parent escapes. All mutation tests use temporary
fixture roots.

## Ownership and collisions

Ownership is exact-path and digest-bound through one central ASM manifest. A
parent such as `.claude`, `.claude/skills`, the ASM store, or HOME is never
owned merely because a child was created.

The engine preserves user-owned, modified-managed, ambiguous, unknown, unsafe,
synced, bundled, and project-duplicate collisions. `CLAUDE_SYNCED` and bundled
collisions are blocked; no user-owned content is adopted or overwritten. An
unexpected file inside a managed skill directory makes uninstall/update a
conflict rather than triggering recursive deletion.

## Transaction and recovery

The USER transaction reuses the Phase 3J shape and adds a small write-ahead
journal under the ASM virtual store:

```text
PREPARED
  → STAGED
  → MUTATING(active operation)
  → OWNERSHIP_COMMITTED
  → VERIFIED
  → COMPLETE
```

An interrupted transaction is represented as `RECOVERY_REQUIRED` until a fresh
recovery process deterministically resumes, completes verification, or reports
manual conflict. The journal binds transaction ID, package/root identities,
immutable operation/path/digest records, staged references, backups, manifest
state, active/completed indexes, and created-directory metadata. The ownership
manifest is committed last. Journal, stage, backup, and operation paths are
confined and schema/digest validated; tampering is `RECOVERY_BLOCKED`.

The demonstrated guarantee is `PROCESS_CRASH_RECOVERABLE` for the supported
virtual-home model. The implementation does not claim power-loss durability;
atomic replacement, content fsync, and directory-entry durability are not
equated with a stronger cross-platform guarantee.

## Lifecycle evidence

The focused virtual-home suite covers:

- single-skill create, same-package idempotent `NO_OP`, uninstall, and reapply;
- managed update with exact backup and revert;
- three-skill mixed lifecycle with independent `CREATE`, `NO_OP`, and
  `UPDATE_MANAGED` actions in one package;
- manual destination modification and unexpected child-file conflicts;
- user-owned and synced-skill collisions;
- all persisted interruption boundaries, including marker-last recovery;
- recovery after the first managed update and after an atomic replacement;
- interruption after an atomic replacement but before its journal completion;
- deterministic rollback after an injected destination failure;
- exact package confirmation and CLI package/apply boundaries;
- full current discovery catalog apply into virtual HOME and ASM store without
  execution-context materialization.

The full catalog is a filesystem validation only. It does not make
`FULL_CATALOG_USER_READY` true and does not load all skill bodies into an
execution bundle.

Uninstall and revert use only ASM evidence and do not require Claude to be
installed, authenticated, or live. Runtime version/fingerprint drift blocks
new apply/update with `RUNTIME_REQUALIFICATION_REQUIRED` while exact managed
cleanup remains evidence-based.

## Security review

Verified properties:

- no Claude/Codex/OpenCode/Hermes process or model inference;
- no auth, keychain, settings, MCP, plugin, hook, or environment-secret read;
- no real HOME or global runtime write;
- no config mutation, force/adopt, silent strategy fallback, or recursive
  deletion;
- no user-owned, synced, bundled, ambiguous, or modified-managed overwrite;
- no raw prompt, output, skill body, credential, or private real path in
  serialized evidence;
- all mutation inputs are host-created and digest-bound; skill instructions
  cannot grant installer authority.

## Authoritative artifacts

- [`tools/v3/installer.py`](../../../tools/v3/installer.py)
- [`schemas/v3/install-package.schema.json`](../../../schemas/v3/install-package.schema.json)
- [`schemas/v3/transaction-recovery.schema.json`](../../../schemas/v3/transaction-recovery.schema.json)
- [`CURRENT_V3_CONTRACT_INDEX.md`](../CURRENT_V3_CONTRACT_INDEX.md)
- [`PHASE3N_USER_APPLY_ROUTE.md`](PHASE3N_USER_APPLY_ROUTE.md)
