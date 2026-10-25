---
name: hermetic-tests
description: "Test passes locally but fails in CI: make it hermetic."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Testing, Hermetic, CI, Fixtures, unittest]
    related_skills: [tdd, verification-before-completion, code-quality, diagnose]
---

# Hermetic Tests

## When to Use

- A test is **green locally but red in CI / a clean checkout**.
- You are about to **add or review a test that reads repo data** (registry,
  catalog, gitignored layers, `~/.agents`, cached output).
- A gate spec requires a result to be **end-to-end**, and you are tempted to
  stand in a hermetic unit test for it.

The class of task: writing or reviewing tests that must run in a **clean
checkout / CI**, not just on the developer's machine. The failure mode this
skill prevents is the one that costs the most: a test that is *genuinely green
locally* and *red in CI*, because it depends on state that only exists on the
author's machine.

## The always-on rule

A test may only read inputs that **exist in every environment it will run in**.
Anything that is gitignored, private, a developer-machine path, or a
side-effect of a prior local run must be **synthesized into a fixture** —
never read from the real location.

If the real data is the thing under test, gate it behind an env flag and skip
in CI; but prefer the synthetic fixture, which is cheaper and covers the
empty/edge cases for free.

## Steps

1. **List what the test reads.** For each input, answer: "does this exist in a
clean checkout / CI?" Real registries, catalogs, gitignored private layers,
`~/.agents`, cached build output → no.
2. **Replace local-only inputs with a synthetic fixture** (in-memory object or
a `tempfile` dir you write the records into). Point the SUT at the fixture via
its `root`/`dir`/config argument.
3. **Prove hermeticity by hiding local state.** Run the test with an isolated
environment — empty `$HOME`, a scratch dir as the fixture root, or the env var
the loader honors set to nothing. Green there = hermetic. Green only when the
real data is present = not hermetic, fix step 2.
4. **For Python `unittest` fixtures, build them correctly** — see
`references/python-unittest-fixtures.md` for the two gotchas that turn a
correctly-designed fixture into a red test.

## Pitfalls (generalizable)

- **Never point a test at the repo's real registry/catalog/gitignored data
  layers.** They are absent in a clean checkout and the failure is *masked*
  locally because the local run really is green — you only see the red on CI.
- **Do not trust a green local run as evidence of CI-safety.** The local
  environment is the exact variable you are trying to hold constant; a green
  run *with* local state present proves nothing about a run *without* it.
- **Assert exact counts derived from the same code path the implementation
  uses, not an eyeballed total.** A hand-computed expected number is the first
  thing to go stale; a test that recomputes the total on its own then asserts
  a wrong literal fails on the first real run and wastes a debug cycle.
- **Do not use a unit test to impersonate an E2E** (or vice-versa). If a gate
  spec says a result must be end-to-end, a hermetic unit test passing does not
  satisfy it; run the real E2E and report that result separately.
- **Isolate REAL execution via state redirection, never by faking sources.**
  A "real" run of a pipeline whose state paths bind to env vars means: point
  every state/env var at a fresh `tempfile.mkdtemp` root and spawn the ACTUAL
  CLI/subprocess — real network, real fork, real log files. Never substitute
  an offline fixture for an upstream scan; a fixture-backed sweep must be
  labeled offline, not claimed as upstream discovery. Afterward clean up the
  temp roots and prove isolation: no new files under the live private layers.
  Record `exit code + last event-line + cursor/record count` as the evidence
  fields.
- **Atomicity boundary = the moment after the last I/O succeeds.** Design
  persistence as "do the I/O, then commit the marker" (stage the artifact to
  disk, THEN advance the cursor/ledger entry). A crash between the two must
  be resumable: re-running redoes the I/O cheaply and re-commits the marker
  (idempotent overwrite, not append). In tests, "crash before marker commit"
  is materialized by deleting the marker file by hand — mocking the commit
  function and asserting on it proves nothing about real FS durability and
  gives a false PASS.
- **Never write thread-based race tests** (`threading.Barrier` + N threads
  racing a write): the outcome depends on scheduling and the test is flaky —
  it passes on one run and fails on the next with zero signal about the
  SUT. Instead, materialize the stale-loser path on a **single
  connection**: fire the *same guarded UPDATE* back-to-back (first
  `rowcount==1`, second must be `rowcount==0`), or reopen the store on a
  second handle and assert takeover bumps a counter exactly once.
  Deterministic, hermetic, and it proves the guard works without
  depending on real parallelism.
- **JSONL ledgers stay pure**: every line of a `.jsonl` file must parse
  as JSON — no `# header` comment lines (the header belongs in a
  human-readable companion `.md`). Append entries with the patch tool,
  not a bash heredoc — CJK content in a heredoc can stall the terminal
  action on a 1-minute timeout and block the whole slice closeout.

## Verification

- [ ] Test reads no local-only state (step 1 audit)
- [ ] Fixture is synthetic (step 2)
- [ ] Test passes with local state hidden (step 3)
- [ ] Expected counts/strings are computed, not hardcoded (pitfall 3)
- [ ] Any E2E-gated requirement was actually run end-to-end, not by a unit test

## References

- `references/python-unittest-fixtures.md` — `TemporaryDirectory` lifetime in
  `setUpClass`, class-level function binding via the descriptor protocol,
  and exact-count assertion hygiene.
