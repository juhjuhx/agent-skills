# Runbook Template Outline

Use this as the section skeleton for an operational runbook page. Keep
each section short and scannable — a runbook is read under time pressure
during an incident, not studied like a design doc.

```
# <System/Service Name> Runbook

## Owner
- Team: <owning team>
- Primary contact: <name/role, or on-call rotation link>
- Last reviewed: <YYYY-MM-DD>   (add a "review-due" label with a date)

## Table of Contents
(use the native Confluence "Table of Contents" macro so it stays in
sync with headings automatically)

## Overview
One paragraph: what this system does and why it matters (impact if
it's down).

## Architecture / Dependencies
- Upstream dependencies: <services this depends on>
- Downstream consumers: <who/what depends on this>
- Link to architecture diagram page, if one exists.

## Common Operations
### <Operation 1, e.g. "Restart the service">
- Precondition/when to do this
- Exact command(s) or console steps
- How to verify it worked

### <Operation 2, e.g. "Scale up replicas">
...

## Alerts and What They Mean
| Alert name | Meaning | First response |
|---|---|---|
| <alert-name> | <what triggers it> | <first 2-3 steps> |

## Troubleshooting
### Symptom: <e.g. "elevated 5xx rate">
1. Check <dashboard link>.
2. Check <log query/link>.
3. Likely causes, in order of frequency, with next steps for each.

## Escalation
- Who to page if the above doesn't resolve it, and how (link to the
  on-call/paging tool, not just a name — names go stale).

## Related Pages / Tickets
- Link to the design doc, the incident postmortems that shaped this
  runbook, and any Jira component/epic it belongs to.
```

Notes:
- Add labels such as `runbook`, the service name, and the owning team so
  the page surfaces in space search and label-based indexes.
- Set a review cadence (e.g. every quarter) and track it via a label
  (`review-2026-q4`) or a recurring reminder — an unreviewed runbook is a
  liability during an incident, not a neutral artifact.
