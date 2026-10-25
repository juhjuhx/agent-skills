# Postmortem: <incident title>

- **Incident ID:** <e.g. INC-2026-0728-01>
- **Date/time (UTC):** <start> – <end>
- **Authors:** <names>
- **Status:** Draft / In review / Final
- **Severity:** <Sev1/Sev2/... — see incident-response-and-on-call-management>

## Summary

Two to three sentences: what broke, what the user-visible impact was, and
how it was resolved. Written so someone who wasn't involved understands
the shape of the incident from this paragraph alone.

## Impact

- Who/what was affected (which users, which region, which % of traffic).
- Duration of customer-visible impact (distinct from total incident
  duration).
- Quantified impact where possible: error budget consumed, requests
  failed, revenue/SLA impact, support tickets filed.

## Timeline (all timestamps UTC)

| Time | Event |
|---|---|
| 14:02 | Deploy of `payments-api` v2.14.0 begins |
| 14:05 | Checkout error rate begins climbing |
| 14:07 | Fast-burn SLO alert pages primary on-call |
| 14:12 | Incident declared Sev1, IC assigned |
| 14:22 | Rollback to v2.13.2 completed |
| 14:40 | Error rate confirmed back within SLO; stand-down declared |

## Root cause

The proximate technical cause of the incident, stated precisely (not "a
bad deploy" — what specifically was wrong in the deploy/config/code).

## Contributing factors

List *all* the independent conditions that had to be true for this
incident to happen and to reach the impact it did — avoid stopping at a
single "root cause." Typically includes a mix of:

- A proximate trigger (e.g. a config value outside its valid range).
- A detection gap (e.g. no validation caught it in CI/staging).
- A latent condition (e.g. staging traffic volume too low to trigger the
  bug; no canary stage in the deploy pipeline).
- A response factor (e.g. the alert that should have fired sooner didn't
  have a short-window burn-rate rule).

## What went well

- Concrete things that worked and should be reinforced (fast detection,
  a clean rollback path, good cross-team comms).

## What went poorly

- Concrete things that slowed detection or recovery, described in system
  terms, not blaming an individual (e.g. "the deploy pipeline allowed an
  unvalidated config change to reach 100% of production traffic with no
  canary stage" — not "X forgot to check the config").

## Where we got lucky

- Anything that could have made this worse but happened not to (e.g. the
  incident occurred during business hours when the full team was
  online) — these are often the most important findings, since luck is
  not a mitigation.

## Action items

| Action item | Owner | Ticket | Due date | Category |
|---|---|---|---|---|
| Add config schema validation to CI | @owner | JIRA-1234 | 2026-08-15 | Prevent recurrence |
| Add canary stage to payments-api pipeline | @owner | JIRA-1235 | 2026-08-30 | Reduce blast radius |
| Add short-window burn-rate alert for checkout SLI | @owner | JIRA-1236 | 2026-08-10 | Detect faster |

Every action item must have exactly one owner, a tracked ticket, and a
due date — an item with none of these will not get done.

## Lessons / follow-up

Broader takeaways worth sharing beyond this specific incident (patterns
that may recur elsewhere in the system).
