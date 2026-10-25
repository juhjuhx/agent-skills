---
name: self-audit
description: "Self-audit: verify your own prior claims before a gate."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Audit, Verification, Evidence, Phase-Gate, Self-Audit, Truthful-Reporting]
    related_skills: [full-audit, code-quality, forensic-workspace-audit, session-checkpoint]
---

# Self-Audit — Verify Your Own Claims Before the Gate

Before advancing a phase gate (or shipping), re-prove the claims made in PRIOR turns against live evidence. A gate closed on remembered claims is invalid: the danger is not a wrong method, it is a stale or un-located artifact being reported as done.

## Dominant Variable
**Gate-label integrity** — `PASS / PARTIAL / FAIL / NOT_VERIFIED / BLOCKED` (or `WORKING / PARTIAL / BROKEN`) is only as true as the FRESHEST evidence behind each individual claim. One un-re-checked claim can silently flip a `PASS` into a `PARTIAL`.

## Trigger
- "self-audit", "did I actually finish", "verify my prior claims", "pre-gate / pre-push check", "re-verify the last phase before we continue"
- An autonomous multi-phase run is about to mark a phase PASS or push, and the completion evidence comes from earlier turns ("we wrote the second suite", "all 16 green", "reviewer passed").

## When to Use

- The user says "self-audit", "did I actually finish", "verify my prior claims", "pre-gate / pre-push check", or "re-verify the last phase before we continue".
- An autonomous multi-phase run is about to mark a phase PASS or push, and the completion evidence comes from earlier turns ("we wrote the second suite", "all 16 green", "reviewer passed").

## Discard If
- The claim is about a code AREA that needs exhaustive coverage (counts, dead links, index-vs-reality) → `full-audit`
- You are packaging/auditing ANOTHER party's tree read-only → `forensic-workspace-audit`
- Nothing was actually claimed as done (a fresh task with no prior assertions to check) → no audit needed

## Always-On Rules

1. **Re-execute, don't remember.** Every number or status the agent asserted earlier — a test count, a "wrote the second test file", a "review passed", a phase PASS — must be RE-PRODUCED by a command run THIS session. Report the value read from live output. If you cannot re-run it this session, label it `NOT RUN` / `NOT VERIFIED`; never restate the remembered value as current.
   - WHY: "all green" carries no date — the tree, the suites, and the environment moved since the claim was made. A re-run is the only thing that can back a PASS.
2. **Located-or-not-done.** A claimed artifact (file, suite, config) you cannot locate with `read_file` / `search_files` right now — or that is truncated / half-written / duplicated from a bad write — is NOT done. Finish it this session or mark the phase incomplete. "I said I made it earlier" is not a deliverable; only a present, complete, parseable file on disk counts. Spot-check the tail / byte-count of any file that survived a long write or a context-compaction boundary.
3. **Salvage dead reviewers, label the review PARTIAL.** A parallel/background reviewer that died (rate-limit 429, timeout, non-zero exit) has NOT delivered its verdict. Read its live transcript / last-emitted findings, extract ONLY findings that carry a concrete citation (command + file:line), and re-verify each one locally before counting it. The whole second-eyes review is then `PARTIAL` (incomplete coverage), never `PASS` — a check that didn't finish is not a passing check. Re-dispatch a fresh reviewer only if the gate actually demands a complete pass. See `references/dead-reviewer-salvage.md`.
4. **One claim, one fresh citation.** No line in the gate report may read `PASS`/`done` without a live evidence anchor: a command + exit code, or an artifact path you just read. The report shape is: per-claim table (claim | evidence (cmd+exit or path) | status) + an explicit remaining-gaps list. An empty gaps list deserves suspicion.
5. **Blind re-review + parallel self-evidence.** When re-dispatching an independent reviewer for a release gate, give it the INVARIANTS/requirements and the code — NOT your prior findings — so it derives independently and cannot rubber-stamp your own conclusions. While the (often background) reviewer runs, generate the gate's own evidence in PARALLEL: a secret/leak scan against the remote baseline, a digest-vs-remote check on protected files, the exact git staging manifest, a full re-sweep of every test suite with real exit codes, and confirmation that any not-yet-implemented features are genuinely disabled/absent. WHY: the gate stops being serial-blocked on one reviewer, and its verdict is cross-checked against evidence you produced independently. A `PARTIAL` phase may ship its implemented subset ONLY when that subset passes review + tests AND is explicitly labeled PARTIAL; never upgrade it to a full-capability claim.
5. **Do not widen.** The audit verifies the CLAIMS and their supporting evidence; it does not redo the whole build or re-open settled scope. Scope = what was asserted done, plus the evidence that asserts it. New defects found → fix only if they block this phase's gate; otherwise record as follow-up.

## Pitfalls

- **"The subagent said it finished"** — subagent self-reports are not verified facts. For any external side-effect (a file written, a commit pushed, a publish), require a handle you can re-check (path, commit SHA, URL) and confirm it yourself with `read_file` / terminal. A dead subagent's partial transcript is salvageable ONLY where it cites a checkable artifact.
- **Reusing a stale pass to save time** — the whole point is to catch exactly the claims that went stale. Skipping the re-run because "it passed before" defeats the audit.
- **Treating a truncation as a clean write** — a long `write_file` / split write that hit a stream cutoff leaves a half file that still parses or still "looks" complete. Confirm the expected ending marker / last line exists, and that no function or test class is duplicated from a re-appended tail.
- **Calling a partial review a pass** — see Rule 3. If coverage is incomplete, say `PARTIAL` and name what wasn't covered; do not upgrade it to `PASS` because the *parts that ran* were green.

## Output

```
SELF-AUDIT — <phase>
| # | Claim (from prior turn) | Evidence (cmd + exit / path) | Status |
Gate label: WORKING | PARTIAL | BROKEN
Remaining gaps: <explicit list, or 'none'>
Dead/partial reviews: <reviewer id, what was salvaged, re-verified?>
```

Final label is one of `WORKING / PARTIAL / BROKEN` (or the user's `PASS / PARTIAL / FAIL / NOT_VERIFIED / BLOCKED`). Any item that could not be re-verified this session is `NOT VERIFIED` and names the missing evidence.
