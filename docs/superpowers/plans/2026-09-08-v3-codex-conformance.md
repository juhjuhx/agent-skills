# Codex Adapter Conformance and Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the Phase 2 Codex projection against pinned native-config drift, permission widening, and raw skill-body leakage without starting the general stage router or Phase 3 adapters.

**Architecture:** Keep `CompiledExecutionBundle` portable and keep Codex-specific validation in a small pinned native-contract module. The adapter consumes a validated route, intersects permissions before projection, resolves only selected skills, and returns metadata references while retaining loaded bodies only in an execution-local field.

**Tech Stack:** Python 3 standard library, checked-in JSON schemas/fixtures, `unittest`, Markdown evidence.

---

### Task 1: Pin and validate the researched Codex config subset

**Files:**
- Create: `tools/v3/codex_native_contract.py`
- Create: `fixtures/v3/codex/codex-native-config-contract.json`
- Modify: `tools/v3/codex_adapter.py`
- Modify: `schemas/v3/codex-native-projection.schema.json`
- Test: `tests/v3/test_codex_adapter.py`

- [x] **Step 1: Write failing tests** for `on-request`, `never`, full granular object validation, obsolete approval rejection, unknown native keys/values, and native-contract revision mismatch.
- [x] **Step 2: Run the focused tests** and confirm the old adapter either accepts obsolete approval values, drops `never`, or has no native-contract validator.
- [x] **Step 3: Add the narrow pinned fixture** for the exact fields emitted by the adapter: model/provider strings, non-empty reasoning effort, `approval_policy` one-of, sandbox enum, and the verified `agents` subset.
- [x] **Step 4: Implement a pure validator** that checks the fixture revision before validating values; it must not fetch upstream at runtime. Reject the obsolete string forms and reject partial granular syntax.
- [x] **Step 5: Call the validator before returning a Codex projection** and add the exact approval enum/object shape to the projection schema.
- [x] **Step 6: Run the focused tests** and confirm current values pass while invalid native values fail explicitly.

### Task 2: Make filesystem projection fail closed

**Files:**
- Modify: `tools/v3/codex_adapter.py`
- Modify: `tests/v3/test_codex_adapter.py`
- Modify: `schemas/v3/codex-native-projection.schema.json`
- Modify: `fixtures/v3/projections/codex-selected.json`
- Modify: `fixtures/v3/projections/codex-no-skill.json`

- [x] **Step 1: Write failing tests** for `none`, `read`, `workspace-read`, `workspace-write`, `external-write`, `destructive`, and an unknown future filesystem value.
- [x] **Step 2: Run those tests** and capture the old broad `danger-full-access` behavior for unsupported levels.
- [x] **Step 3: Implement one pure mapping table** with `NATIVE_EXACT`, `NATIVE_CONSERVATIVE`, `HOST_MANAGED`, and `BLOCKED`; map only exact `read-only`/`workspace-write` cases, classify `workspace-read` as `HOST_MANAGED`, and block it unless a proved host path boundary exists.
- [x] **Step 4: Include the permission projection classification in the Codex projection** and propagate any future conservative mapping to bundle/result `DEGRADED` status; current host-managed and unrepresentable mappings fail closed.
- [x] **Step 5: Run permission and regression tests** and confirm no projection can widen the effective envelope.

### Task 3: Separate ephemeral skill bodies from serializable results

**Files:**
- Modify: `tools/v3/codex_adapter.py`
- Modify: `tests/v3/test_codex_adapter.py`

- [x] **Step 1: Write failing tests** proving `AdapterResult.to_dict()` currently exposes a loaded body while execution still needs access to it.
- [x] **Step 2: Run the serialization tests** and confirm the raw body is present in the old result.
- [x] **Step 3: Keep `LoadedSkill` objects in an execution-local field** and expose only ID/path/ref/digest/role/load-state/bytes in `loaded_skills` and `to_dict()`.
- [x] **Step 4: Run serialization, selected-only, and no-skill tests** and confirm selected bodies remain available only through the execution-local field.

### Task 4: Independent review and verification

**Files:**
- Modify: `docs/v3/CODEX_OFFICIAL_CAPABILITY_MAPPING.md`
- Modify: `docs/v3/agents/CODEX.md`
- Create: `docs/v3/evidence/PHASE25_CODEX_CONFORMANCE_ROUTE.md`
- Modify: `docs/v3/NEXT_CODEX_PROMPT.md`
- Modify: `docs/v3/USING_SUPERPOWERS.md`

- [x] **Step 1: Re-read the changed code with code-review and simplification checklists**; remove speculative managers, registries, services, or factories.
- [x] **Step 2: Run the MCP audit without changing configuration** and run the OCR auth precheck once; record an authentication block rather than substituting delegate review.
- [x] **Step 3: Run the full unittest command, `git diff --check`, JSON fixture validation, changed-file secret/path scans, and a small selected-only serialization measurement.
- [x] **Step 4: Update canonical docs** with pinned source revision, approval/permission support classifications, serialization boundary, and no-runtime-fetch process.
- [x] **Step 5: Record every active dogfood stage as a route** with selected real skills, reasons, evidence, and final result; do not record hidden reasoning.
- [x] **Step 6: Update `NEXT_CODEX_PROMPT.md`** with the diversity-driven Phase 3 research/wave strategy, but do not execute Phase 3.
- [x] **Step 7: Commit each semantic group, push the stacked branch, and create a draft PR against `feat/v3-codex-adapter` only after fresh verification passes.
