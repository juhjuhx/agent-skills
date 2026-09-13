# Agent Skills Matrix v3 — Beta Candidate Readiness

## Candidate status

```yaml
candidate: v3-beta-candidate
publication: NOT_PUBLISHED
real_home_mutation: NOT_AUTHORIZED
live_model_execution: NOT_RUN_IN_EPOCH
beta_candidate_stable: true
final_canary_status: READY_FOR_EXACT_USER_AUTH
```

The candidate is a local, fresh-clone-testable static/productization build.
Two consecutive integrated verification passes completed on the same final HEAD
with no code changes between them. No real-home mutation or release publication
was performed.

## Product gates

| gate | status | boundary |
|---|---|---|
| Stage Router | READY | metadata-first, deterministic, 0 ranking body reads |
| static productization | READY | deterministic projections and no-write plan |
| PROJECT installer | READY | explicit project root, managed artifacts, rollback/revert |
| Claude virtual USER installer | READY | Claude `2.1.235`, `MANAGED_COPY`, virtual roots only |
| process-crash recovery | VERIFIED | `PROCESS_CRASH_RECOVERABLE`, not power-loss atomicity |
| clone-to-use UX | READY | status/doctor/preview/package/apply/recovery lifecycle |
| real-home canary | READY_FOR_EXACT_USER_AUTH | one-skill `module-map` preview; exact package/confirmation only; no mutation in Phase 3P |
| full-catalog real USER | NOT READY | explicitly not authorized |
| Codex live effort evidence | BLOCKED | transport remains blocked |

## Known limitations

- Codex live transport and intra/cross-runtime effort routing remain NOT_READY.
- Claude `2.1.235` is the qualified USER contract; another installed version
  requires requalification for new mutation.
- USER real-home canary is not executed or considered verified.
- Hermes has no adapter and receives status-only treatment.
- Linux/Windows filesystem contracts retain explicit preconditions/unknowns where
  runtime or host capability evidence is not pinned.
- The legacy `install.sh` remains compatibility tooling, not the v3 authority.
- The fresh canary preview is bound to Claude Code `2.1.235`, `MANAGED_COPY`,
  zero observed collisions, and a virtual/ephemeral ASM user-data contract;
  the package is non-authorizing until the exact user gate is crossed.

## Release posture

Release publication, package registry publication, stack merge and real-user
installation are separate authority gates. This document is a readiness report,
not a release or installation command.

## Final verification dimensions

```yaml
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
