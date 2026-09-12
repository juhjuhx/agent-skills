# Phase 3M Integration Checkpoint Route

## Route record

| 欄位 | 值 |
|---|---|
| phase | `3M` |
| branch | `chore/v3-integration-checkpoint` |
| base | `feat/v3-claude-user-contract` |
| starting HEAD | `d8d7248438f724e29c78998e1d66eb05193c93d5` |
| task | audit the combined static/productization/project/USER/Claude contract path |
| runtime/model execution | `NOT_RUN` by policy |
| real HOME mutation | `NOT_RUN` and forbidden |
| Stage Router | unchanged; `STAGE_ROUTER_PRODUCTION_READY` carried forward |
| final checkpoint result | `USER_APPLY_ARCHITECTURE_PARTIAL` |

## Scope boundary

```text
RoutingCatalogSnapshot
  → StageRoute
  → CompiledExecutionBundle
  → static distribution
  → InstallationPlan
  → InstallPackage
  → project ownership/transaction contracts
  → generic USER preview
  → Claude user preview
```

Only contract composition and virtual/static evidence were exercised. No Claude,
Codex, OpenCode, Hermes, provider, auth, MCP, plugin, or model invocation was allowed.
The current `CODEX_LIVE_TRANSPORT_BLOCKED`, `INTRA_RUNTIME_EFFORT_ROUTING_READINESS=
NOT_READY`, and `CROSS_RUNTIME_ROUTING_READINESS=NOT_READY` statuses were not changed.

## Stage emissions

```text
Understand
  SKILLS_SELECTED: using-superpowers

Design
  SKILLS_SELECTED: Agent Development

Implement
  SKILLS_SELECTED: addyosmani-test-driven-development

Security / Review
  SKILLS_SELECTED: codex-security:validation
  SKILLS_SELECTED: addyosmani-code-simplification

Verify
  SKILLS_SELECTED: codex-engineering-guardrails:code-verification

Live execution
  NO_SKILL_NEEDED(reason=Phase 3M forbids runtime/model invocation)

Handoff
  SKILLS_SELECTED: using-superpowers; verification
```

The resident authority remained `using-superpowers`. Ranking did not load canonical
skill bodies; the snapshot contract remains 214 metadata records and zero ranking body
reads.

## TDD finding and fix

The new integration tests were added before the implementation change. The initial
focused run was deliberately red:

```text
8 tests: 6 passed, 2 failed
```

The two failures were direct contract findings:

1. a valid-schema plan could pair `operation=CONFLICT` with `action=CREATE`;
2. a package could carry a tampered runtime-contract digest without the revalidator
   comparing it to the generated manifest and target.

The bounded fix is in [`tools/v3/installer.py`](../../../tools/v3/installer.py):

- `PLAN_OPERATION_ACTIONS` validates descriptive operation/authoritative action pairs;
- `_revalidate_package()` checks package runtime contract against both generated
  manifest and install target.

The green focused run is recorded as `8/8 PASS`. No schema version or universal
abstraction was added.

## Contract lineage replay

The route replay uses a fixture `NO_SKILL_NEEDED` `StageRoute` and the Codex static
status only. It demonstrates:

| boundary | assertion |
|---|---|
| snapshot → route | route remains bound to snapshot registry epoch |
| route → projection | runtime projection carries the route digest |
| projection → plan | generated artifact manifest and plan share snapshot/content bindings |
| plan → package | only persistent lifecycles enter package; ephemeral route/bundle/skill state is excluded |
| package → result | `ApplyResult` is a separate outcome contract; package has no `operation` field |
| no-skill branch | zero `SKILL.md` body files and no persistent skill-body artifact |

The existing productization and installer tests provide the A–J/route replay coverage;
the new tests bind those observations together without rerunning Stage Router per
runtime or per scope.

## USER / Claude composition replay

The generic USER preview and Claude specialization were built independently from the
same snapshot and Claude runtime status:

```text
generic UserScopeContract
  → symbolic USER preview, apply_allowed=false

Claude 2.1.235 UserContract
  → Claude-specific personal/synced/bundled/strategy preview, apply_allowed=false
```

Neither preview is an `InstallPackage`; neither carries an authorization token. The
generic migration descriptor remains two independent transactions with
`shared_transaction=false` and no automatic project deletion.

The managed-copy lifecycle is represented in virtual fixtures only. It preserves
canonical source authority, exact ownership, user/synced collision protection, manual
modification conflict, exact backup/revert, and independent project/user scope. Actual
USER mutation is still absent.

## Transaction and crash review

Phase 3J's project transaction remains the only mutation algorithm:

```text
all-target preflight
→ stage
→ revalidate
→ atomic/bounded replace
→ ownership marker last
→ digest verification
→ transaction record
→ bounded rollback
```

Virtual fault injection confirms the in-process rollback path. The crash review finds a
bounded limitation: a process dying after a destination write but before ownership
state/transaction completion can leave partial state that needs manual, digest-based
recovery. There is no second persistent journal in the current code. Therefore the
crash classification is `BOUNDED_MANUAL_RECOVERY`, not `DETERMINISTIC`, and this is one
reason USER apply remains partial.

## Stale-state review

The current project chain is now:

```text
source → snapshot → generated manifest → plan → package
       → runtime contract + target → destination state → ownership marker
```

The new package revalidation test confirms that a runtime-contract digest tamper stops
before any virtual project write. A future Claude USER package must append the Claude
user-contract digest/fingerprint, managed-copy strategy, collision observations, and
symbolic USER target digest. It must not recompile inside apply.

## Runtime lifecycle review

New Claude versions require `RUNTIME_REQUALIFICATION_REQUIRED` for new USER apply/update;
Phase 3L evidence is not automatically portable. Cleanup should remain possible from
recorded exact ownership when the Claude executable is absent, without provider/auth
access. Current PROJECT uninstall already does not probe the runtime; a future USER
cleanup path must retain this property.

## Security review

```text
real HOME write                         NO
runtime/config/auth read                NO
runtime/model/provider invocation       NO
MCP/plugin/hook execution               NO
credential/raw prompt/output storage   NO
Stage Router/routing weight mutation   NO
USER apply authorization                NO
```

The single OCR precheck returned 401; the retained classification is
`OCR_NATIVE_DIFF=BLOCKED_BY_AUTH`. No retry was performed.

## Verification sequence

```text
focused integration tests  → PASS (8/8)
full repository tests       → PASS (371/371)
schema validation           → PASS through repository contract tests and explicit fixture checks
diff check / links / scan   → PASS; private-path/secret scan recorded in checkpoint handoff
runtime/model invocation    → NOT RUN
real HOME mutation          → NOT RUN
```

Static/integration timing was measured over three virtual no-skill runs (median):

```text
snapshot load/validation          732.37 ms
static compile                    932.51 ms
package build                      21.74 ms
generated distribution validation 468.22 ms
end-to-end                       2,153.14 ms
```

These figures are local static measurements, not runtime/model latency or cost.

See the full checkpoint assessment in
[`INTEGRATION_CHECKPOINT_V1.md`](INTEGRATION_CHECKPOINT_V1.md) and the current
authoritative index in [`CURRENT_V3_CONTRACT_INDEX.md`](../CURRENT_V3_CONTRACT_INDEX.md).

## Handoff

The stack is safe to continue to a bounded Phase 3N contract-closure/apply design, but
not to skip the gate. Phase 3N must be Claude-only, `MANAGED_COPY` only, virtual-home
first, and must first make USER package/target composition and cross-process recovery
explicit. No Codex/OpenCode/Hermes USER apply and no Phase 4 work are implied.
