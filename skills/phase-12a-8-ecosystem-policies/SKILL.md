---
name: phase-12a-8-ecosystem-policies
description: "Use when recording Phase 12A.8 ecosystem policy decisions B47-B58 (plugin, release, license, governance). Captures the decision delta recording workflow for non-implementation architecture decisions."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Phase-12, Decision, Architecture, Policy, B-Series]
    related_skills: [phase-12-stage-0-workflow, phase-11-completion-workflow, skill-authoring]
---

# Phase 12A.8 Ecosystem Policies (B47-B58)

## When to Use

- Recording B47-B58 decision deltas
- Creating policy-only spec documents (no implementation)
- Updating canonical docs after design decisions
- Finalizing license policy (B58)

---

## Decision Categories

### Plugin Ecosystem (B47-B50)

| ID | Topic | Status | Doc |
|----|-------|--------|-----|
| B47 | Plugin Dependency Resolution | APPROVED / DESIGN_ONLY | PLUGIN_DEPENDENCY_RESOLUTION_SPEC.md |
| B48 | Plugin Publisher Identity | APPROVED | PLUGIN_PUBLISHER_IDENTITY_SPEC.md |
| B49 | Registry Conflict Resolution | APPROVED | FEDERATED_PLUGIN_REGISTRY_PROTOCOL.md |
| B50 | Plugin Revocation | APPROVED | PLUGIN_REVOCATION_POLICY.md |

### Application Lifecycle (B51-B55)

| ID | Topic | Status | Doc |
|----|-------|--------|-----|
| B51 | Application Release Channels | APPROVED / CONTRACT_ONLY | APPLICATION_RELEASE_CHANNELS.md |
| B52 | Application Update Policy | APPROVED | APPLICATION_UPDATE_POLICY.md |
| B53 | Snapshot-Like Rollback | APPROVED | APPLICATION_ROLLBACK_ARCHITECTURE.md |
| B54 | Forward/Backward Compatibility | APPROVED | PROJECT_COMPATIBILITY_POLICY.md |
| B55 | Opaque Extension Data | APPROVED | OPAQUE_EXTENSION_DATA_SPEC.md |

### Governance & Policy (B56-B58)

| ID | Topic | Status | Doc |
|----|-------|--------|-----|
| B56 | Public Community Telemetry | APPROVED / WITH_PRIVACY_BOUNDARY | PUBLIC_TELEMETRY_DATASET_POLICY.md |
| B57 | Contributor Governance | APPROVED | CONTRIBUTING.md |
| B58 | Ecosystem License Policy | APPROVED — GPL-3.0 FOSS-COPYLEFT | LICENSE_STRATEGY_DECISION_B58.md |

---

## B58 Final Decision (2026-09-06)

**Policy: GPL-3.0 FOSS-COPYLEFT**

- LSS Core: GPL-3.0
- Official plugins: GPL-3.0 or GPL-compatible OSI-approved
- Commercial use: Legally permitted
- Copyleft: Preserved

Do NOT describe GPL-3.0 as non-commercial.

---

## Document Creation Pattern

Each B-decision creates one spec:

```
docs/architecture/BXX_<POLICY_NAME>.md
```

Required sections:
1. Header with Phase reference, Decision ID, Status
2. Policy statement
3. Schema/Format (if applicable)
4. Rules/Constraints
5. Status

---

## Canonical Doc Updates

After recording decisions:

1. `docs/architecture/DECISION_LEDGER_CURRENT.md` — Add B47-B58 rows
2. `docs/architecture/DECISION_LEDGER_12A8_UPDATE.md` — Add summary
3. `CANONICAL_DOC_INDEX.md` — Add new sections
4. `DECISIONS.md` — Add B47-B58 section
5. `docs/research/LICENSE_PROVENANCE_CURRENT.md` — Update with B58
6. `AGENTS.md` — Update license reference
7. `READ_FIRST.md` — Update decision summary

---

## Verification

```bash
./test.sh all
```

Expected: Python 743+, Frontend 129+, Rust 4+

---

## Key Pitfalls

1. B47-B58 are DESIGN_ONLY — do not implement
2. B58 requires explicit user choice — was PENDING_USER_FINAL_CHOICE
3. License policy conflicts: "open source" ≠ "non-commercial"
4. macOS file descriptor limit ~256 — batch write_file calls
5. Don't let ecosystem work displace critical path (EditorialTimeline wiring, Tauri integration)
6. v0.5.0-alpha.1 remains BLOCKED on D-068 regardless of B47-B58

---

## Critical Path Reminder

B47-B58 are future ecosystem work. Current path:

1. EditorTimeline wiring (Phase 12A.8 ✅)
2. Frontend Tauri integration (Phase 12A.9 ⏳)
3. Real artifact E2E test (Phase 12A.9 ⏳)
4. Performance verification (Future)
5. Full-source OpenCodeReview (Future)
6. v0.5.0-alpha.1 gate (BLOCKED on D-068)
