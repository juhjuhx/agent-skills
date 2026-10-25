# Performance Measurement Pattern

When establishing performance baseline for IME or similar latency-sensitive systems:

## Phase 1 — Workspace Isolation

Create isolated M4 worktree from verified C4 baseline:

```bash
git worktree add .worktrees/m4-performance-baseline <c4-sha>
```

Verify:
- HEAD matches expected C4 SHA
- Working tree is clean
- Common repo is the canonical repository

## Phase 2 — Performance Inventory

Search for existing infrastructure:

```bash
# Search for benchmark modules
grep -r "benchmark\|macrobenchmark\|microbenchmark" --include="*.gradle" --include="*.gradle.kts"

# Search for JankStats
grep -r "JankStats\|FrameTimingMetric" --include="*.kt"

# Search for trace utilities
grep -r "TraceSection\|systemTracing\|compositionTracing" --include="*.kt"

# Check AndroidManifest for profileable
grep -i "profileable" app/src/main/AndroidManifest.xml
```

**Report absence explicitly** — do not assume infrastructure exists.

## Phase 3 — Define Three Measurement Layers

### A. Session / Decoder Latency

Measure per-command latency through the decoder path:

| Command | ChewingEngineSession | ZhuyinDictionarySession |
|---------|---------------------|------------------------|
| TapZhuyinKey | native JNI call | dictionary lookup |
| Space | engine.commitUpdate() | selectCandidate or clearComposing |
| Enter | engine.commitUpdate() | completeComposition() |
| SelectCandidate | engine.selectCandidateUpdate() | engine.selectCandidate() |

Metrics format (baseline only, no pass/fail yet):
```
Command: TapZhuyinKey
  Path: ChewingEngineSession
  Sample count: N
  p50: X μs
  p95: X μs
  max: X μs
```

**Implementation**: Add timing wrapper in test code only (no production changes).

### B. Real UI Frame Quality

Use Macrobenchmark + FrameTimingMetric:

```kotlin
@LargeTest
class FrameQualityBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun measureFrameTimingDuringTyping() {
        benchmarkRule.measureRepeated(
            metrics = listOf(FrameTimingMetric()),
            iterations = 5,
            setupBlock = { /* seed initial state */ }
        ) { /* scripted typing sequence */ }
    }
}
```

**Do NOT call decoder timing "end-to-end key latency"** — these are separate layers.

### C. Trace / Recomposition Diagnostics

Minimal trace points (only where they attribute measured issues):

| Trace Point | Purpose |
|-------------|---------|
| UI key callback entry | Boundary: Android framework → app |
| session.dispatch() | Decoder entry point |
| orderedCommits() completion | Result application |

**Do NOT instrument every composable** — only add Compose traces if frame quality issues detected.

## Primary Metrics (max 3)

1. **Session dispatch p95 latency** — decoder path speed
2. **Frame duration p95 during scripted typing** — real UI quality
3. **Recomposition count per keypress** — diagnostic (conditional)

## Guardrails

Existing gates must remain green:
- JVM tests (all @Test annotations)
- Python contracts
- assembleDebug build
- CI trigger on C4 push

**NO changes to:**
- Keyboard behavior
- Keyboard geometry
- Touch correction
- Candidate ranking
- libchewing semantics
- UI design
- Any arbitrary numeric targets

## Files to Create (M4-A1)

1. `app/src/androidTest/java/com/example/ime/benchmark/SessionLatencyBenchmark.kt`
2. `app/src/androidTest/java/com/example/ime/benchmark/FrameQualityBenchmark.kt`
3. `app/build.gradle.kts` additions (benchmark dependencies)
4. `app/src/androidTest/AndroidManifest.xml` additions (if needed)

## Measurement Risks

| Risk | Mitigation |
|------|------------|
| DEBUG_BUILD_BIAS | Profile with debug build first; note overhead |
| EMULATOR_BIAS | Document emulator vs device variance |
| WARMUP_EFFECT | Include warmup iterations before measurement window |
| TRACE_OVERHEAD | Use trace points sparingly; disable during final measurement |
