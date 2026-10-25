# Postmortem Template Outline

Blameless by default: describe what the system and process did, not who
made a mistake. Publish even when the root cause is mundane — the value
is in the timeline and the follow-up actions, not in the drama.

```
# Postmortem: <Incident Title> (<YYYY-MM-DD>)

## Status
Draft | In Review | Final — (Final means action items are tracked and
this page is the closed record.)

## Summary
2-3 sentences: what happened, user/business impact, duration.

## Impact
- Who/what was affected (users, regions, internal systems).
- Quantified impact where possible (error rate, revenue, SLA breach).
- Duration: start/end timestamps (UTC) and detection lag.

## Timeline
| Time (UTC) | Event |
|---|---|
| 14:02 | Alert fired: elevated 5xx on checkout-api |
| 14:05 | On-call acknowledged |
| 14:18 | Root cause identified: bad config pushed at 13:55 |
| 14:22 | Rollback deployed |
| 14:30 | Error rate back to baseline |

## Root Cause
What actually caused it, at the level of "this specific change/condition
triggered this specific failure mode" — not just "human error."

## Detection
How was this detected (alert, customer report, internal QA)? How long
between the change/onset and detection? Was detection fast enough, and
if not, what would have caught it sooner?

## What Went Well
- Things that worked as intended (fast rollback, alert fired correctly,
  runbook was accurate).

## What Went Wrong / Contributing Factors
- Gaps that let this happen or slowed the response — process gaps, not
  individual blame.

## Action Items
| Action | Owner | Ticket | Due |
|---|---|---|---|
| Add config validation to CI | <owner> | <JIRA-KEY> | <date> |
| Update runbook alert section | <owner> | <JIRA-KEY> | <date> |

Every action item should link to a real Jira ticket — an action item
that only lives on this page with no ticket tends to never get done.

## Related Pages
- Link to the runbook this incident should update, and any prior related
  postmortems (if this is a recurrence, that itself is a finding).
```

Notes:
- Label the page `postmortem` plus the affected service/team so it is
  discoverable from a space-wide postmortem index page — link every new
  postmortem from that index at creation time so it is never orphaned.
- Do not let "Draft" postmortems linger indefinitely; a stale draft with
  no owner is worse than a short, finished one.
