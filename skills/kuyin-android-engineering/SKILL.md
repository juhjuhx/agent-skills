---
name: kuyin-android-engineering
description: "KU-Yin Android IME workflow. Use for KU-Yin keyboard repo."
tags: [android, ime, keyboard, forensics, performance]
related_skills: [phase-11-completion-workflow, phase-12-stage-0-workflow]
version: 1.0.0
author: agnes
license: MIT
---

# KU-Yin Android Engineering Workflow

## When to Use

- Working in ~/KU-Yin_keyboardforandroid or its .worktrees/
- Dirty-work forensics (comparing a dirty worktree against a reference branch)
- Doc-source reconciliation (aligning docs with production code)
- Performance measurement baseline (session latency, frame quality)
- Tasks that require structured PASS/FAIL/BLOCKED report blocks

Project: ~/KU-Yin_keyboardforandroid (Android IME, Compose mainline, JNI libchewing).
Working language of reports: English structured blocks; user's chat language: Traditional Chinese.

## Standing Report Format (mandatory)

User tasks for this project specify an EXACT return template (sections like MODE_RESTORATION / ENTER_CONTRACT / GUARDRAILS with PASS/FAIL/BLOCKED/NOT_MEASURED values). Reproduce the requested section list VERBATIM in order. Do not add prose commentary around it; put detail under each section. When a value cannot be measured, write NOT_MEASURED / BLOCKED with the reason — never invent numbers.

## Environment Setup (every session, in every worktree)

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
```

Pitfalls:
- A freshly created `git worktree` has NO `local.properties` → any Gradle task fails with "SDK location not found". Fix: `cp ~/KU-Yin_keyboardforandroid/local.properties <worktree>/local.properties` before first Gradle invocation in that worktree.
- Native prebuilt deps are git-ignored: `assembleDebug` fails at `configureCMakeDebug` (all 4 ABIs) until `bash scripts/bootstrap_native_deps.sh` has been run in that worktree. Run it after any fresh worktree creation, before the APK gate.
- Never run two Gradle invocations in parallel on this machine.

## Verification Gates (run for any code/doc change)

```bash
./gradlew :app:testDebugUnitTest            # JVM suite
for f in scripts/check_*.py; do python3 "$f"; done   # ~7 python contracts
./gradlew :app:assembleDebug               # needs bootstrap_native_deps.sh first
```

Do not run `./gradlew lintDebug` (times out). Do not claim runtime readiness from static/build evidence.

## Dirty-Work Forensics Pattern

When a worktree is dirty (modified + untracked files) and must be classified against a reference branch:
1. Preserve the dirty worktree untouched as evidence; all new work happens in a SEPARATE worktree: `git worktree add .worktrees/<name> <sha>`.
2. Three-way compare each target file: worktree HEAD (`git show HEAD:path`), dirty working tree (read the file on disk), and reference branch (`git show origin/<branch>:path`). `git diff HEAD -- <file>` gives the dirty delta directly.
3. For untracked test files: read the test, identify the intended behavior, then grep the reference branch's tests for equivalent coverage before ruling. Rulings use explicit classes: BEHAVIOR_ALREADY_COVERED, DUPLICATE_STATE_OWNER, REGRESSION, etc. Judge against the branch's CONTRACT TESTS (they define intended semantics), not against the dirty implementation.
4. Classify state ownership before preserving code: a field that duplicates a service-level owner is DUPLICATE_STATE_OWNER — reject it even if the behavior is correct.
5. Output only the requested report block; end with FINAL_PRESERVE_SET / FINAL_SUPERSEDED_SET / SAFE_TO_MOVE_TO_CLEAN_C4_BASELINE / NEXT.

## Doc-Source Reconciliation Pattern

- Verify every doc claim against production source before editing; count test figures by scanning `@Test` annotations in source rather than trusting stale numbers.
- Stale claims: correct in place; historical claims: mark historical, don't delete context.
- Minimal edits; never redesign architecture or touch production code during a doc pass.
- After edits, re-read changed sections and confirm AGENTS.md, docs/CURRENT_STATE.md, docs/ARCHITECTURE.md, and source no longer contradict each other.

## Performance Measurement Conventions (M4+)

- Session/decoder latency harnesses live in `app/src/androidTest/java/com/example/ime/benchmark/`.
- Rules: `System.nanoTime()` monotonic clock; preparation/reset/composition setup OUTSIDE the timed interval; fixed warm-up samples (5) then measured samples (20); report sample count / p50 / p95 / max in µs; no pass/fail thresholds — descriptive baseline only.
- Native-path baselines MUST use the real engine (LibChewingDataInstaller.ensureInstalled → AndroidChewingEngine → init(DACHEN)); never substitute a fake ChewingEngine for native numbers. If the runtime can't start the native engine, report NATIVE_BASELINE = BLOCKED.
- Disable personalized learning on BOTH paths (native: `setPersonalizedLearningEnabled(false)`; fallback: EditorPolicy `allowPersonalizedLearning=false`) so repeated selection can't mutate ranking mid-measurement.
- Key contract: `ChewingEngineSession.TapZhuyinKey` expects the Zhuyin LABEL (session maps label→ASCII code internally); both sessions take the same label form.
- Semantic checks: assert composition is active (preedit non-empty) and candidates exist before measuring Space/Enter/SelectCandidate — a measurement that didn't exercise the intended path is invalid.
- Output: one machine-readable line per decoder×command: `KUYIN_PERF_SESSION` header + `decoder=,command=,samples=,p50_us=,p95_us=,max_us=`.
- Without a device/emulator: compile the androidTest artifact, run the static gates, and report runtime as NOT MEASURED. Never invent timings.
- Frame-quality work uses Macrobenchmark + FrameTimingMetric; do not conflate decoder dispatch latency with end-to-end key latency.
- Macrobenchmark module layout: keep frame benchmarks in `:app`'s own `src/androidTest/.../benchmark/` plus a dedicated non-minified, debuggable app build type for installation — a separate `com.android.test` module is unnecessary here (AGP plugin classpath conflicts, no access to app manifests) and the target app is a single APK that IS the IME.
- Exact imports that resolved in this toolchain: `androidx.benchmark.macro.FrameTimingMetric` lives in `androidx.benchmark.macro`, but `MacrobenchmarkRule` lives in `androidx.benchmark.macro.junit4` (junit4 subpackage, separate artifact `benchmark-macro-junit4`). Check the actual jar in the Gradle cache (`jar tf <artifact>.jar | grep <class>`) when an import is unresolved — the package split between the core and junit4 artifacts is not guessable from the artifact name alone.
- `UiDevice` exposes no `launchActivity` API: launch the target Activity via `androidx.test.core.app.ActivityScenario` and drive the editor with `UiDevice`/`UiSelector`.
- Shell-command helpers for instrumentation: `InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(cmd)` returns a `ParcelFileDescriptor` (NOT `java.io.ParcelFileDescriptor` — it is `android.os.ParcelFileDescriptor`).
- Before measuring frames, assert IME state in order: installed (`ime list -s` contains pkg) → enabled → selected (`settings get secure default_input_method` contains pkg + service class) → visible (`dumpsys input_method` shows mShown=true for pkg). Auto-fix each missing state, then fail loudly with a descriptive AssertionError on timeout (~5s poll @200ms). Prevents silently benchmarking a fallback keyboard.

## Scope Discipline

Forensic/doc/baseline turns are explicitly read-only-or-test-only: do not modify product code, tests, or UI unless the task says so. Preserved evidence worktrees are never touched.
