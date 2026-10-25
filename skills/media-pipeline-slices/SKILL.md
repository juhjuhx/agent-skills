---
name: media-pipeline-slices
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when TDD-building FFmpeg/FFprobe media pipeline slices."
---

# Media Pipeline Slices (FFmpeg/FFprobe) + Slice Closure Discipline

## When to Use

Any media-pipeline vertical slice in this user's autonomous engineering runs: FFprobe-based probes, proxy/transcode generators, receipt-gated artifact publishing — and the closure discipline (regression → state files → independent review → commit → push) that wraps every slice.

For this user's autonomous engineering runs: each slice ships as
spec-first → TDD vertical slices → full regression → state-file
closure → independent review → standalone commit → push. Media
classes of work additionally require real-toolchain verification with
synthetic fixtures and honest degradation.

## 1. Slice procedure (every slice, in this order)

1. Spec first (`writing-plans`): a test-matrix spec in the repo's spec
   location BEFORE any code. List every scenario with expected
   behavior; untestable-on-this-host items are marked UNVERIFIED in
   the spec, not discovered later.
2. TDD vertical slices: one red test → minimal green, repeated. Batch
   a spec's matrix into one test file, but run after each fix batch
   and record which bugs the red runs caught (that record is part of
   the slice evidence).
3. Full regression before ANY commit: targeted suite + full suite +
   linter, all green. Never commit on partial results.
4. State files update with the slice (STATE/EVIDENCE/PLAN/CHANGELOG +
   append-only JSONL ledger). Append ledger lines via targeted patch,
   never shell heredoc: CJK terminal heredoc is error-prone, and the
   patch gives a reviewable diff. Validate the JSONL stays pure
   (every line a json.loads) after appending.
5. Independent review BEFORE commit: dispatch a fresh-context reviewer
   (subagent) that must read the diff/files, run the regression
   itself, and report per-item PASS/FAIL with file:line evidence.
   Address its flags in the same slice (or add explicit errata) so the
   review is part of the commit, not after it.
6. Standalone commit per slice, then push to the research branch.
   Keep slices disjoint: stage only that slice's files; later
   slices' files stay out.

## 2. Consents on irreversible steps

A commit is local and reversible; a push is not. When a consent gate
   stops a command, do not retry it in rephrased form and do not
   complete the outcome via another path. Stage and commit if that is
   already consented and reversible, then report state and wait for
   direction on the irreversible step. This generalizes: uploads,
   publications, external writes all need the same gate.

## 3. Synthetic fixtures, never real media

Generate fixtures in the test's temp dir with ffmpeg lavfi sources
(testsrc/sine/color); each generated file must be asserted
non-empty. Real camera cards, real NAS, and real user media are
never touched by tests. Hardware-dependent verification stays
BLOCKED with an explicit contract marker — never simulated data
presented as a hardware pass.

## 4. Build capability gates every codec claim

Query the local build first (`ffmpeg -encoders` / `-h encoder=X`);
only claim what is present. Missing encoder → honest degradation
(path still works, flagged as degraded), never a fake claim of the
target codec. Verify with ffprobe read-back: the artifact's actual
codec must match what the result reports. Encoder option sets
differ per build — a flag that is valid elsewhere may be rejected
here; when an encode fails on an option, isolate the option before
assuming the codec is unsupported.

## 5. Subprocess + URL safety

- Safe argv: list form, shell=False, a timeout, a stdout size cap,
  and the trimmed stderr carried into any error so failures are
  diagnosable without rerunning.
- URL/network input: check the original string on scheme markers
  (both a `://` anywhere and scheme prefixes after lowercasing)
  BEFORE path normalization: `Path('http://x')` collapses to
  `'http:/x'` and hides the scheme from a later check. A spy that
  asserts zero subprocess calls proves the refusal happened early.
- Empty input: reject before invoking the tool at all.

## 6. Receipt-gated atomic publishing (staging → verify → receipt → rename)

Encoded/transcoded artifacts land in a hidden staging area keyed by
job id. The verify gate reads the staged artifact back through
ffprobe (decodable, duration within tolerance, stream counts match
the source mapping); any miss discards the staging file and raises.
On success: write the receipt JSON FIRST (job id, lease token, both
sha256 fingerprints, tool version, argv), then an atomic same-dir
rename into the public location. No receipt = not committed. This
makes stolen-lease or interrupted writer outputs attributable and
discardable; a DB-layer fence alone does not cover external file
writes.

## 7. FFprobe data quirks (cost hours in a real run)

- ffprobe JSON fields that look numeric can be strings: cast before
  comparing (sample rates etc.).
- Frame PTS extraction requires both frame-show and the entries
  flag with JSON output; a csv/entries-only invocation may yield
  nothing usable — check what a real invocation prints before
  writing the parser.
- Build-dependent muxing: some builds silently drop display-matrix
  rotation and HDR color transfer when muxing to MP4; if a synthetic
  clip cannot carry that metadata, verify the parsing path against
  crafted ffprobe JSON and say so in the test, instead of faking
  samples.
- Keep a public read-only JSON-parse helper on the probe module for
  the verify gate; re-export it rather than re-implementing the
  subprocess dance in each consumer.
