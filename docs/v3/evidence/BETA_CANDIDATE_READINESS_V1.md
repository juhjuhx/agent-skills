# Agent Skills Matrix v3 — Beta Candidate Readiness

## Candidate status

```yaml
candidate: v3-beta-candidate
publication: NOT_PUBLISHED
real_home_mutation: NOT_AUTHORIZED
live_model_execution: NOT_RUN_IN_EPOCH
```

The candidate is a local, fresh-clone-testable static/productization build. A
final `BETA_CANDIDATE_STABLE=true` claim requires two consecutive integrated
verification passes on the same final HEAD with no code changes between them.

## Product gates

| gate | status | boundary |
|---|---|---|
| Stage Router | READY | metadata-first, deterministic, 0 ranking body reads |
| static productization | READY | deterministic projections and no-write plan |
| PROJECT installer | READY | explicit project root, managed artifacts, rollback/revert |
| Claude virtual USER installer | READY | Claude `2.1.235`, `MANAGED_COPY`, virtual roots only |
| process-crash recovery | VERIFIED | `PROCESS_CRASH_RECOVERABLE`, not power-loss atomicity |
| clone-to-use UX | READY | status/doctor/preview/package/apply/recovery lifecycle |
| real-home canary | PENDING STABILIZATION REFRESH | exact package/confirmation only; no mutation in Phase 3P |
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

## Release posture

Release publication, package registry publication, stack merge and real-user
installation are separate authority gates. This document is a readiness report,
not a release or installation command.
