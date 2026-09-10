# Claude Read-Only Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest provenance-bound Claude Code 2.1.235 read-only projection that consumes an existing StageRoute and preserves the v3 evidence boundary.

**Architecture:** Keep TaskSpec, StageRoute, CompiledExecutionBundle, AgentAdapterManifest, ModelProfile, SkillResolver, and LiveExecutionRecord unchanged. Add a narrow installed-runtime contract validator and a Claude adapter whose projection emits only verified CLI surfaces; skill bodies remain execution-local.

**Tech Stack:** Python 3 standard library, repository JSON-schema validator, unittest, `claude -p`.

---

### Task 1: Define the failing adapter boundary tests

**Files:**
- Create: `tests/v3/test_claude_adapter.py`

- [x] **Step 1: Write the failing tests**

The tests cover contract provenance, deterministic compilation, selected-only loading, zero-ASK read-only projection, permission non-escalation, serialization, and bounded invocation.

- [x] **Step 2: Run the focused test file**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.v3.test_claude_adapter -v`

Expected: import failure because the Claude adapter has not been implemented.

### Task 2: Add the installed Claude native contract

**Files:**
- Create: `schemas/v3/claude-native-contract.schema.json`
- Create: `fixtures/v3/claude/claude-native-contract-2.1.235.json`
- Create: `tools/v3/claude_native_contract.py`
- Modify: `tools/v3/contract_validation.py`

- [ ] **Step 1: Implement contract shape and digest validation**

Bind executable validation to observed version `2.1.235`, the checked-in CLI-help contract revision, and `INSTALLED_RUNTIME`; retain null release/source commits because this installed proprietary CLI does not expose an immutable source commit.

- [ ] **Step 2: Run contract tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.v3.test_claude_adapter.ClaudeNativeContractTests -v`

Expected: PASS.

### Task 3: Implement the Claude adapter projection and invocation

**Files:**
- Create: `schemas/v3/claude-native-projection.schema.json`
- Create: `tools/v3/claude_adapter.py`

- [ ] **Step 1: Implement pure projection and fail-closed validation**

Use `--safe-mode`, `--permission-mode dontAsk`, `--tools Read,Glob,Grep`, JSON output, no session persistence, no Chrome, strict empty MCP, and finite max turns/budget. Do not emit model-selection flags or raw skill bodies.

- [ ] **Step 2: Implement execution-local skill delivery**

Pass selected procedure text only through the ephemeral `--append-system-prompt` argument when execution needs it; public results contain references, digests, load state, and byte counts only.

- [ ] **Step 3: Run focused adapter tests**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.v3.test_claude_adapter -v`

Expected: PASS.

### Task 4: Verify runtime gates and publish evidence

**Files:**
- Create: `fixtures/v3/model-routing/runs/phase3c/claude-phase3d-smoke-a-001.json`
- Create: `fixtures/v3/model-routing/runs/phase3c/claude-phase3d-smoke-b-001.json`
- Create: `docs/v3/evidence/PHASE3D_CLAUDE_DOGFOOD_ROUTE.md`
- Create: `docs/v3/evidence/MODEL_RUNTIME_EVAL_V6.md`

- [ ] **Step 1: Run Smoke A**

Use a temporary isolated directory and a bounded `claude -p` invocation with tools overridden to empty. Persist only sanitized status, digests, and metrics.

- [ ] **Step 2: Run Smoke B only after Smoke A passes**

Use a harmless fixture file and the read-only tool allowlist. Confirm the fixture digest is unchanged.

- [ ] **Step 3: Run H03 only after both smoke gates pass**

Independently verify the DecisionRecord artifact before assigning a terminal outcome.

- [ ] **Step 4: Run repository validation**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v`, `git diff --check`, schema/link/secret scans.

- [ ] **Step 5: Commit the bounded changes**

Use semantic commits and create a stacked Draft PR; do not merge.
