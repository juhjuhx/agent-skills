# Debug & Independent Review Workflow

Formal maintenance document for the `agent-skills` repository. It records the
engineering disciplines that already exist for this codebase — debugging,
verification, independent review, and the release gate. It does **not** add
new tooling; it pins the discipline so each cycle is auditable.

> Scope rule: organize what already exists. Do not build a new debug framework.
> Do not use LLM self-review as a substitute for an independent reviewer.

## 1. Debugging

Deterministic, minimal, evidenced. One issue at a time.

```
Reproduce  ->  Minimize  ->  Root cause  ->  Failing test  ->  Minimal fix  ->  Regression
```

| Step | Requirement |
|---|---|
| Reproduce | Record the exact failing command + exit code + input. No "should fail." |
| Minimize | Reduce to the smallest input that still fails. Drop unrelated state. |
| Root cause | Name the mechanism (type error, race, missing file, stale cache), not just the symptom. |
| Failing test | A test that fails before the fix and is meaningful (not just "row exists"). |
| Minimal fix | One change per cause. No drive-by refactors into unrelated files. |
| Regression | Rerun the focused test + the suite that owns the module. Record exit code. |

Rules:

- No `git reset --hard`, `git clean`, force push, or blanket `git stash`.
- Never edit a live scheduler or another worktree to debug; copy out or work in
  the isolated `publish-worktree-*`.
- Distinguish **pre-existing failure** from **this-change regression** before
  claiming anything — run the suite on the baseline commit and diff the results.

## 2. Engineering Verification

Focused first, then broad. Each gate leaves `COMMAND / EXIT_CODE / RESULT`.

1. **Focused tests** — the test files that own the changed module.
2. **Full tests** — `python3 -m unittest discover` (both suites) + the Node
   advisory test.
3. **Catalog / lock verification** — `python3 scripts/build_v3_catalog.py --check`
   and `install_v3.py --verify` against an isolated HOME; counts must match
   `catalog.json` / `catalog.lock.json` exactly.
4. **Installer smoke** — `--dry-run` per host into a throwaway HOME, then a real
   `--all` into an isolated HOME and `--verify` on it. Do **not** install into the
   real `~/.hermes/skills` user layer just to test.

A passing local test does not equal a passing GitHub CI. The release gate below
runs the real CI on the pushed commit.

## 3. Independent Review

A fresh-context reviewer who was **not** the implementer.

```
Fresh-context reviewer  ->  Findings (Critical/High/Med/Low)  ->  Remediation  ->  Re-review
```

| Rule | Why |
|---|---|
| Reviewer reads the **final** diff, docs, tests and verification evidence | Self-check is not independent review |
| Every Critical/High finding is fixed and **re-reviewed** | A patch without re-verification is not closed |
| If no valid independent reviewer is available, set `RELEASE_GATE = REVIEW_BLOCKED` | Do not fake completion; record the blocker + recovery path |

Priority: use whatever fresh-context reviewer is actually available. If the
OpenCode/OCR path is down (e.g. provider rate limit), do **not** burn retries —
switch to another genuine fresh-context reviewer. If none is reachable, hold the
release and report `REVIEW_BLOCKED` with the unreviewed diff path.

## 4. Release Gate

Ordered. A release happens only when every line is PASS.

```
Security  ->  License  ->  Compatibility  ->  CI green  ->  Fast-forward push  ->  Remote verification
```

- **Security**: no new secret-bearing or private data in the diff; private
  registry / history / forge workspaces stay out of git.
- **License**: every published skill has an approved license or notice; the
  excluded manifest covers the rest; no copyleft leaked in.
- **Compatibility**: installer flags still work; no npm/Node dependency added;
  skill bodies untouched (unless separately reviewed); P5 worktree untouched.
- **CI green**: the pushed commit's GitHub Actions run is `completed / success`.
  A push whose CI fails is `PUSHED_BUT_CI_FAILED`, not shipped.
- **Fast-forward push**: no force push. If remote moved, rebase the doc-only
  changes onto it and re-verify before pushing.
- **Remote verification**: confirm remote HEAD == pushed SHA, read the rendered
  README diagrams/links, and confirm a fresh install command pulls the new version.

### Not-done = not-shipped

Never hide a failing test or an incomplete item. If the gate cannot fully pass,
record the real blocker, save all work, and stop — the status is the blocker,
not "shipped."

## Quick reference: the three failure-to-flag mappings

| You might be tempted to say | Correct recorded status |
|---|---|
| "Review skipped because provider was down" | `REVIEW_BLOCKED` (+ recovery path) |
| "CI was red but the push went out" | `PUSHED_BUT_CI_FAILED` |
| "Local tests passed, so it's shipped" | not shipped until CI + remote verify |
