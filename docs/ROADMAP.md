# Project Roadmap

Status table for the M4 agent-skills roadmap. Two independent numbering
systems are shown: the **registry layers** (P0-P3, historical) and the
**M4 phases** (P1-P8+, independent). They are **not** the same sequence and
must not be merged.

All status markers reflect the checkpoint / git evidence at the time this
document was written, **not** the act of writing this document. No deployment
or completion is implied by a doc edit.

## Roadmap

```
+----------------------------------------------+
| REGISTRY LAYERS (HISTORICAL NUMBERING P0-P3) |
| P0 Catalog   PASS                            |
| P1 Registry  PASS                            |
| P2 Scout     PARTIAL                         |
| P3 Forge     PASS                            |
|                                              |
|                                              |
| do not merge with M4 phases                  |
+==============================================+

M4 roadmap (independent numbering P1-P8+)
M4 P1  baseline / dual-repo contract   DONE      PASS
M4 P2  composer fixes                  DONE      PASS
M4 P3  closeout (CI green)             DONE      PASS
M4 P4  scout hardening                  DONE      PASS
M4 P5  scheduler                         IN_PROGRESS  PARTIAL
M4 P6  forge loop                         NOT_STARTED
M4 P7  six E2E                            NOT_STARTED
M4 P8  public 464 skill packages          PUBLISHED  PASS
M4 P8+ README / docs / workflow           THIS RELEASE

+-----------------------------------+
| FUTURE (ROADMAP, NOT IMPLEMENTED) |
| GitHub Pages static explorer      |
| NPX CLI (deferred)                |
+===================================+
P5/P6/P7 markers reflect checkpoint state, not document edits;
no deployment is claimed from this documentation release.
```

## Registry layers (historical, P0-P3)

| Layer | Status | Note |
|---|---|---|
| P0 Catalog | PASS | 640 records = 492 active + 148 private recovery, zero overlap |
| P1 Registry | PASS | public / private / history; provenance, license gate, rollback |
| P2 Scout | **PARTIAL** | discovery + staging + bounded retry; deep security scan NOT implemented |
| P3 Forge | PASS | recursion bounds, lineage cycle block, regression gate |

## M4 phases (independent numbering)

| Phase | Status | Evidence |
|---|---|---|
| P1 Baseline | DONE | initial M4 baseline commit |
| P2 Composer fixes | DONE | pushed, CI green |
| P3 Dual-repo contract closeout | DONE | pushed, CI green, closeout re-verified |
| P4 Scout hardening | DONE | pushed, CI green |
| P5 Scheduler | **IN_PROGRESS** | U1-U3 done; hermetic suite pending; NOT_DEPLOYED, NOT_RELEASED |
| P6 Forge loop | NOT_STARTED | P5.5 launchd deploy prerequisite |
| P7 Six E2E | NOT_STARTED | pending P6 |
| P8 Public 464 skill packages | **PUBLISHED** | `3d55520` on main, CI run `40197122208` green |
| P8+ README / docs / workflow | THIS RELEASE | the document you are reading |

## Future (ROADMAP, not implemented)

- GitHub Pages static catalog explorer (Q1-B) — catalog.json as single source,
  zero backend.
- NPX CLI wrapper (Q1-C) — deferred; no second install path.

## Invariants

- P5/P6/P7 markers above reflect checkpoint state; they do not change because
  this document was written.
- No force push. P5 worktree (`scout/scout.py`, `scheduler/`,
  `tests/test_scheduler_suite.py`) is uncommitted and not touched by this release.
- The 464 skill bodies are unchanged in this release.

## Related

- [ADR-0001 distribution architecture](../adr/0001-distribution-architecture.md)
- [Release Verification](../RELEASE_VERIFICATION.md)
- [Checkpoint](state/M4-P8-CHECKPOINT.json) (local, not in git)
