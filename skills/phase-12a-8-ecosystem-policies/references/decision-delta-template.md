# Decision Delta Recording Template

> For recording B-series decision deltas (B47-B58)

---

## Template

```markdown
# Decision Delta — B{START} TO B{END}

========================================================
Record the following decisions in the canonical decision ledger.
========================================================

## Decision Recording

| ID | Topic | Status | Doc |
|----|-------|--------|-----|
| B{X} | {Topic} | {Status} | {Doc} |
| ... |

## Document Creation

Create: docs/architecture/{DOC_NAME}.md

## Canonical Updates

- docs/architecture/DECISION_LEDGER_CURRENT.md
- docs/architecture/DECISION_LEDGER_12A8_UPDATE.md
- CANONICAL_DOC_INDEX.md
- DECISIONS.md
- docs/research/LICENSE_PROVENANCE_CURRENT.md (if B58)
- AGENTS.md
- READ_FIRST.md

## Verification

./test.sh all

Expected: Python 743+, Frontend 129+, Rust 4+

## Critical Path Reminder

B{X}-B{Y} are future ecosystem work. Current path:
1. EditorialTimeline wiring
2. Frontend Tauri integration
3. Real artifact E2E
4. Performance verification
5. v0.5.0-alpha.1 gate (BLOCKED on D-068)
```

---

## Status Codes

| Status | Meaning |
|--------|---------|
| APPROVED | Design complete |
| APPROVED / DESIGN_ONLY | No implementation |
| APPROVED / CONTRACT_ONLY | Contract defined only |
| APPROVED / WITH_PRIVACY_BOUNDARY | Privacy constraints apply |
| APPROVED — GPL-3.0 FOSS-COPYLEFT | License policy finalized |
| PENDING_USER_FINAL_CHOICE | Requires user decision |
| IMPLEMENTED | Code implemented |

---

## License Policy Decision

If B58 is included:

**Must resolve to one of:**
- Option A: FOSS-COPYLEFT (GPL-3.0, commercial permitted)
- Option B: SOURCE-AVAILABLE-NONCOMMERCIAL (prohibited)

Do NOT leave B58 as PENDING indefinitely.
Do NOT describe GPL-3.0 as non-commercial.
