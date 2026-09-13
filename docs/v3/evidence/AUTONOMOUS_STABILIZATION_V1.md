# Agent Skills Matrix v3 — Autonomous Stabilization

這份文件是 Phase 3P 的可審計穩定化紀錄。它描述 repository 內可重播的
static/productization 產品路徑，不授權 real HOME、release、merge 或 live
model/provider 執行。

## Epoch boundary

```yaml
epoch_id: v3-autonomous-product-stabilization-2026-09-13
starting_head: 975a8b443fcc3da6c39ebf0f7a6b748f296f54c7
branch: fix/v3-claude-canary-authorization-closure
real_home_apply_authorized: false
real_home_canary_verified: false
full_catalog_user_ready: false
claude_real_home_canary_readiness: CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH
beta_candidate_stable: true
codex_live_transport: CODEX_LIVE_TRANSPORT_BLOCKED
intra_runtime_effort_routing: NOT_READY
cross_runtime_routing: NOT_READY
```

## Completed stabilization work

| milestone | result | evidence |
|---|---|---|
| A — contract stabilization | PASS | [`CURRENT_V3_CONTRACT_INDEX.md`](../CURRENT_V3_CONTRACT_INDEX.md), normalized `InstallationPlan.action`, immutable package/result split |
| B — fresh clone | PASS | current HEAD disposable clone replay; status/doctor/project/virtual USER lifecycle |
| C — CLI consolidation | PASS | `status`, `doctor`, `explain`, `preview`, `package`, `apply`, `recover`, `uninstall`, `revert` |
| D — error UX | PASS | stable error code, safe-state and next-action fields; private path redaction |
| E — recovery/security hardening | PASS | Phase 3J/3N fault and journal tests plus real ASM-root overlap guard |
| F — portability | PASS WITH BOUNDED UNKNOWN | macOS/Linux/Windows symbolic user-data fixtures; symlink-parent rejection |
| G — security review | PASS | no runtime/model/config/auth surface in productization path; exact-path and digest guards |
| H — product performance | PASS | warm route and virtual filesystem measurements recorded below |
| I — catalog health | PASS WITH REVIEWED SUPPORTING FILES | 214 source digests, slug/case/Unicode checks, executable/symlink inventory |
| J/K — routing and installer regression | PASS | v3 suite and focused lifecycle matrix |
| L — onboarding | PASS | [`CLONE_TO_USE.md`](../CLONE_TO_USE.md), current v3 README sections |
| M — CI | PASS LOCALLY | repository workflow added; remote CI remains an external check |
| N — independent review | PASS WITH NO OPEN HIGH/CRITICAL | architecture, security, lifecycle, router, UX and anti-bloat lanes |
| O — Beta candidate | PASS | final two-pass integrated verification completed on the final HEAD; local candidate only; no publication |

## Fresh-clone replay

The flow was executed from a disposable clone of the current repository. It used
only temporary project, virtual HOME and virtual ASM roots:

```text
status READY/READY
doctor PASS, ranking_body_reads=0
PROJECT preview → apply → uninstall
USER package → apply → repeat NO_OP → recover COMPLETE_VERIFICATION
      → revert → reapply → uninstall
remaining virtual Claude skill files: 0
```

The initial replay exposed a package-output parsing assumption in the test command;
the second clean clone used the authoritative InstallPackage root and completed.
No product code was changed for that parsing mistake. The corrected replay also
proved repeat-apply converges to `NO_OP`, recovery reaches `COMPLETE`, and the
virtual USER uninstall leaves zero managed skill files.

## Measured product operations

Measurements are host-local filesystem/product metrics, not runtime inference:

| operation | measured result |
|---|---:|
| warm route, 3 samples | 12.756–15.190 ms; 0 body reads |
| snapshot load | 533.489 ms |
| static distribution compile | 699.982 ms |
| PROJECT package | 19.304 ms |
| PROJECT apply | 23.455 ms |
| full virtual USER package, 214 skills / 428 artifacts | 337.796 ms |
| full virtual USER apply | 7289.962 ms |
| virtual USER uninstall package | 298.299 ms |
| virtual USER uninstall apply | 6435.237 ms |

The 214-skill catalog is allowed for virtual discovery validation only. It is not
a real-user rollout authorization and does not preload 214 bodies into execution.

## Catalog health

The offline scan found 214/214 canonical source files with matching digests, no
missing sources, no oversized `SKILL.md` bodies over 1 MiB, no case-fold or NFC
slug collisions, and zero body reads during metadata snapshot construction. Two
symlinked supporting directories and 49 executable supporting files remain
canonical-library content; v3 selected-only materialization does not copy or run
them automatically. They are retained as reviewed catalog inputs, not product
execution instructions.

## Security boundary

- no real HOME or real ASM data mutation;
- no runtime inference, provider/auth/config/MCP/plugin/hook access;
- no user-owned, synced, bundled, ambiguous or unknown collision overwrite;
- USER virtual apply rejects the real ASM data root even when an OS data override
  places it outside HOME;
- package, scope, runtime, strategy, root identity, source and ownership digests
  are revalidated before mutation;
- journals are schema/digest/path confined and recovery is bounded;
- no `--force`, adopt, overwrite-user or real-home bypass exists.

## Current interpretation

The product candidate is static/productization-ready and project-install-ready.
Claude USER `MANAGED_COPY` is verified in virtual HOME only. Real-home canary
preparation was freshly revalidated after stabilization and is ready for a
separate exact-digest authority gate; no mutation occurred.

## Final read-only canary preview

The final canary is a one-skill, candidate-specific, non-authorizing preview:

```yaml
status: CLAUDE_REAL_HOME_CANARY_READY_FOR_USER_AUTH
runtime: Claude Code 2.1.235
scope: USER
strategy: MANAGED_COPY
selected_skill: module-map
files: 2
bytes: 1959
collisions: 0
unknown_collisions: 0
discovery_validation: STATIC_CONTRACT_ONLY
recovery_guarantee: PROCESS_CRASH_RECOVERABLE
package_digest: sha256:0408c2a7153c8a6e403feed51f734a496e50e1d98d416b7637e07b5adb794866
confirmation_digest: sha256:242ba68b6d044d9cb2a555f5dba52eb5e62e91441175ea0330ba7737440f83c1
preview_digest: sha256:261b7a8fc3ea537eaa9ffaf1c133cdf963ec43c6367532530afce7f6ca277b75
package_context_digest: sha256:7bfe442b008983c49a0ebcb09012fdda7a7b465f1af4c7ad8e699e8026c82506
real_home_apply_authorized: false
no_changes_made: true
```

The qualified Claude artifact fingerprint, runtime contract and USER contract
remain bound to the preview. The ASM data root is represented only as the
symbolic `${ASM_USER_DATA}/v3/claude`; the real path and filesystem identities
were ephemeral and are not recorded here. The old Phase 3O/3O.1 digests remain
historical and retired.

## Integrated verification and review

The final HEAD received two consecutive integrated passes with no repository
changes between them. Each pass included the root pytest suite, v3 lint and
format checks, catalog/schema/link checks, AST compilation, `doctor`, and
`git diff --check`. The release gate result was `587 passed, 8 skipped, 179
subtests passed` in the root suite; the v3 collection was `424 passed`.

Separate review lanes were completed for architecture/contracts, security and
path confinement, installer lifecycle/recovery, Stage Router regression,
UX/documentation, test quality, anti-bloat and CI/release readiness. No open
CRITICAL or HIGH finding remains. The only carried blockers are the independent
live-routing statuses listed at the epoch boundary.

## Deployment boundary

```yaml
INSTALLER_IMPLEMENTED: true
FRESH_CLONE_FLOW_VERIFIED: true
PROJECT_INSTALLER_STABLE: true
CLAUDE_VIRTUAL_USER_INSTALLER_STABLE: true
PROCESS_CRASH_RECOVERY_VERIFIED: true
CLONE_TO_USE_UX_READY: true
ROUTER_REGRESSION_GREEN: true
SECURITY_REVIEW_GREEN: true
CI_GREEN: true
DOCS_READY: true
REAL_HOME_CANARY_VERIFIED: false
FULL_CATALOG_USER_READY: false
OCR_NATIVE_DIFF: BLOCKED_BY_AUTH
```

`CI_GREEN` means the repository workflow was validated locally; publication,
merge, and any real-home operation remain authority-gated. A virtual full
catalog is a scale test only and does not authorize a full real-user rollout.
