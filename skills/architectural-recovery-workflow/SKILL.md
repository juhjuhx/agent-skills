---
name: architectural-recovery-workflow
description: "Use when resuming architectural work after session loss."
version: 1.0.0
author: Agnes + Hermes
license: MIT
tags: [recovery, architecture, phase-12]
related_skills: [phase-12-stage-0-workflow]
---

# Architectural Recovery Workflow

Resuming architectural work after context loss requires establishing TRUTH before proceeding.

## When to Use

- Session lost API connectivity mid-task
- Context compaction removed critical state
- User reports "where were we?" or "resume from earlier"
- Starting new session on incomplete Phase 12/13 task

## Recovery Phases

### Phase 1: Establish Repository Truth

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git describe --tags --always
```

Output:
```text
ACTUAL_HEAD: <sha>
ACTUAL_BRANCH: <branch>
WORKTREE_STATUS: <clean|dirty>
```

**PITFALL**: Never trust reported HEAD from conversation history. Always verify fresh.

### Phase 2: Locate Canonical Documents

Search priority:
1. `READ_FIRST.md`
2. `STATE_MANIFEST.json`
3. `CANONICAL_DOC_INDEX.md`
4. `DECISION_LEDGER_CURRENT.md`
5. `DECISIONS.md`
6. `PROJECT_STATE.md`

**PITFALL**: Docs may be in `handoff/chatgpt-current/`.

### Phase 3: Read Canonical Truth

Read only (do NOT load 158K tokens):
- `READ_FIRST.md` (if exists)
- `DECISIONS.md` (full)
- `PROJECT_STATE.md` (first 100 lines)

### Phase 4: Scan Production Code

```bash
find python -name "*.py" -type f | wc -l
find frontend/js -name "*.js" -type f | wc -l
```

**PITFALL**: Docs may describe unimplemented features.

### Phase 5: Create Evidence Documents

1. `docs/research/PHASE_XX_RECOVERY_STATUS_REPORT.md`
2. `docs/research/CURRENT_AUTHORITY_MAP_FROM_CODE.md`
3. `docs/research/COUPLING_AUDIT_CURRENT.md`

### Phase 6: Update Canonicals

- `DECISIONS.md` — Mark decisions
- `READ_FIRST.md` — Create if missing

### Phase 7: Identify Grill Questions

```
GRILL Q<n>: <topic>
- Option A/B/C: <descriptions>
- RECOMMENDATION: <X>
```

### Phase 8: Return Status Report

Use `references/recovery-report-template.md`.

## Donor Graft Analysis

### Classification

| Classification | When |
|---------------|------|
| COPY_WITH_NOTICE | Small utility, direct copy |
| ADAPT | Pattern needs restructuring |
| REIMPLEMENT_PATTERN | Large system with conflicts |
| REFERENCE_ONLY | Ideas only |
| REJECT | Authority/license conflicts |

### Stop Conditions (GRILL_REQUIRED)

Stop if donor would change:
- EditorialTimeline authority (D-046)
- EditIntent authority (D-009)
- Project ownership
- ASR workflow
- Transcript delete semantics
- Persistence source
- GPL strategy
- Frontend freeze

## C4 Baseline Correction Pattern

When reviewing dirty worktree changes against C4 reference:

### Step 1: Verify C4 Baseline First

Before judging dirty changes, confirm what C4 already implements:

```bash
# Check expected C4 SHA matches actual
git rev-parse origin/c4-branch
# Verify against documented expected SHA

# Read C4 reference versions of files under review
git show origin/c4-branch:path/to/file.kt
```

### Step 2: Classify Dirty Changes

| Classification | Criteria | Action |
|---------------|----------|--------|
| `DUPLICATE_STATE_OWNER` | Dirty adds state that C4 already manages at service level | Reject — do not merge |
| `BEHAVIOR_ALREADY_COVERED` | Dirty test covers same behavior as existing C4 test | Reject — existing test is sufficient |
| `GAP_FILLED` | Dirty adds genuinely new behavior not in C4 | Accept — cherry-pick into clean baseline |
| `DESIGN_CONFLICT` | Dirty contradicts established C4 contract | Reject — preserve C4 design |

### Step 3: State Ownership Rule

**Service-level state ≠ Engine-level state:**
- Mode restoration lives in `KuYinInputMethodService.userPreferredMode`
- Computed via `EffectiveModePolicy.effectiveMode()`
- KuYinEngine must NOT duplicate this as `_userMode`
- Engine owns composition state, not policy evaluation

### Step 4: Test Hierarchy

Pure logic tests > Fixture-heavy tests:
- `EffectiveModePolicyTest` (pure JUnit, no Robolectric) is canonical
- `EditorForcedModeRestorationTest` (Robolectric + Context) is redundant if same behaviors covered
- When in doubt, prefer the test without Android fixture overhead

### Step 5: Establish Clean Workspace

```bash
# Preserve dirty worktree as forensic evidence
git worktree add <clean-path> <c4-sha>

# Verify clean workspace
git -C <clean-path> status --short  # should be empty
git -C <clean-path> rev-parse HEAD   # must match expected C4 SHA
```

**Rule**: Never modify the forensic worktree. All engineering happens in the clean workspace.

### Step 6: D3 Component Verification

When establishing baseline, verify these components exist:
- `NativeChewingEngineOwner` — JNI engine lifecycle
- `NativeStartupGate` — one-time native initialization
- `NativeLearningPolicy` — personalized learning control
- `ProductionDecoderResolver` — decoder selection
- `EffectiveModePolicy` — mode restoration logic

## Key Pitfalls

1. Don't assume reported state is true — verify HEAD fresh
2. Don't read 158K tokens — use canonical compression
3. Don't implement during recovery — discovery only
4. macOS file descriptor limit ~256 — batch write_file calls
5. **Don't merge duplicate state owners** — service-level state trumps engine-level state
6. **Preserve forensic worktrees** — never modify dirty evidence, work in clean clone
7. **Verify C4 before judging dirty** — baseline may already be correct
8. **Verify docs against production source** — stale claims in ARCHITECTURE.md/CURRENT_STATE.md can mislead future sessions
9. **Measure before optimizing** — establish baseline metrics before any performance work
10. **Don't conflate layers** — decoder latency ≠ UI frame time ≠ end-to-end latency

## References

- `references/recovery-report-template.md`
- `references/donor-graft-checklist.md`