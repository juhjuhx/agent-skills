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
| O — Beta candidate | PENDING FINAL DOUBLE PASS | local candidate only; no publication |

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
No product code was changed for that parsing mistake.

## Measured product operations

Measurements are host-local filesystem/product metrics, not runtime inference:

| operation | measured result |
|---|---:|
| warm route, 3 samples | 12.756–15.190 ms; 0 body reads |
| snapshot load | 495.848 ms |
| static distribution compile | 606.813 ms |
| PROJECT package | 14.974 ms |
| PROJECT apply | 18.290 ms |
| full virtual USER package, 214 skills / 428 artifacts | 310.062 ms |
| full virtual USER apply | 6633.802 ms |
| virtual USER uninstall package | 298.299 ms |
| virtual USER uninstall apply | 6435.237 ms |

The 214-skill catalog is allowed for virtual discovery validation only. It is not
a real-user rollout authorization and does not preload 214 bodies into execution.

## Catalog health

The offline scan found 214/214 canonical source files with matching digests, no
missing sources, no oversized `SKILL.md` bodies over 1 MiB, no case-fold or NFC
slug collisions, and zero body reads during metadata snapshot construction. Two
symlinked supporting directories and 47 executable supporting files remain
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
preparation remains a separate exact-digest authority gate; it must be freshly
revalidated after stabilization and must stop before mutation.

