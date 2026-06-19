# State Transition Matrix

## Legal Transitions

| From → To | inbox | planning | planned | ready | claimed | running | review | done | blocked | failed | archived |
|-----------|-------|----------|---------|-------|---------|---------|--------|------|---------|--------|----------|
| inbox     | —     | ✅       |         |       |         |         |        |      | ✅      |        | ✅       |
| planning  |       | —        | ✅      |       |         |         |        |      | ✅      | ✅     | ✅       |
| planned   |       | ✅       | —       | ✅    |         |         |        |      | ✅      |        | ✅       |
| ready     |       |          |         | —     | ✅      |         |        |      | ✅      |        | ✅       |
| claimed   |       |          |         | ✅    | —       | ✅      |        |      | ✅      |        | ✅       |
| running   |       |          |         |       |         | —       | ✅     |      | ✅      | ✅     |          |
| review    |       |          |         |       |         | ✅      | —      | ✅   | ✅      | ✅     |          |
| blocked   | ✅    | ✅       | ✅      | ✅    | ✅      | ✅      |        |      | —       |        | ✅       |
| failed    | ✅    | ✅       |         | ✅    |         |         |        |      |         | —      | ✅       |
| done      |       |          |         |       |         |         |        | —    |         |        | ✅       |
| archived  | ✅    |          |         |       |         |         |        |      |         |        | —        |

## Rules

- **Same-state transitions**: Blocked (no-op)
- **Requires owner_agent**: claimed, running, review
- **Terminal states**: done, archived (no further transitions except unarchive)
- **Review loop**: review → running is allowed (reviewer requests changes)
- **Retry path**: failed → planning (re-plan, don't just re-run)
- **Unblock**: blocked can return to ANY active state
- **Atomic claim**: `UPDATE ... WHERE status='ready'` prevents double-claim
- **Version column**: Optimistic lock for read-modify-write races

## Stuck Detection

A task is "stuck" if:
- Status is non-terminal (not done/archived)
- `updated_at` is older than threshold (default 24h)

Recovery suggestions:
- blocked → "Review blockers, move to ready when resolved"
- failed → "Reassign or move to planning for re-plan"
- claimed/running stuck → "Check agent health, consider reassigning"
- review stuck → "Assign reviewer or mark done if reviewed externally"
