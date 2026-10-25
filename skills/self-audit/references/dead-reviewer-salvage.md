# Salvaging a Dead Parallel/Background Reviewer

Applies when a reviewer (subagent, spawned fan-out unit, external review job) dies before finishing: rate-limit 429, timeout, crash, non-zero exit. Its absence is NOT a pass, and its last lines are NOT a verdict.

## Steps

1. **Confirm the death.** Read the run status / final line: `status=failed`, a rate-limit/timeout message, or a partial summary. Record the reviewer id and failure cause.
2. **Read its live transcript**, not just the (missing) final summary. The transcript is append-only and holds every tool call + output that DID run. Look for: `terminal` results, grep/read outputs, and any findings already emitted with a `file:line` citation.
3. **Filter to citation-backed findings only.** A usable salvaged finding names a command + its output or a file:line anchor. A finding that exists only in the reviewer's unverified prose ("I think X is broken") is discarded — it was never confirmed and cannot be credited to the review.
4. **Re-verify each salvaged finding locally yourself**, with the same command class the reviewer used. You are now the reviewer-of-record for those lines; the dead agent carries no authority. If a salvaged finding does not reproduce, drop it and say so.
5. **Label the review PARTIAL**, naming exactly what was not covered (the phases/questions the dead reviewer never reached). Do NOT let the green parts upgrade the label to PASS. A second-eyes check that didn't finish is not a passing second-eyes check.
6. **Re-dispatch only when the gate demands it.** If the decision is blocked on a complete independent review, spawn a FRESH reviewer with the same scope (a restarted one with lost context is not a completion of the old one). If the gate can proceed on the salvaged+re-verified findings, record the gap and move on — do not over-audit.

## Anti-patterns
- Treating a dead reviewer's partial "looks fine so far" as an all-clear. (Missing verdict ≠ verdict.)
- Inheriting un-cited conclusions because "it's easier than re-running". (No re-verification = not verified.)
- Looping: restart the same dead run in hopes it finishes. (Restart ≠ completion; dispatch fresh or accept PARTIAL.)
- Labeling the salvage `PASS` because every salvaged finding that WAS checked held. (Coverage is the unit of truth, not the per-check result.)

## Report line
`Dead/partial review: <id> died at <cause>. Salvaged N findings (all citation-backed, re-verified locally), M questions never reached. Review status = PARTIAL (not a complete second-eyes pass).`
