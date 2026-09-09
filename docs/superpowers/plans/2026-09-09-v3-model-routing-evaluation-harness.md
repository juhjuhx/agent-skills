# Runtime and Model Routing Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, evidence-preserving harness that evaluates runtime and model candidates without changing production Stage Router policy.

**Architecture:** Keep runtime eligibility, model eligibility, execution configuration, handoff, evidence classification, baselines, and Pareto comparison as plain validated records and pure functions. Reuse existing TaskSpec, StageRoute, AgentAdapterManifest, ModelProfile, permission intersection, and Codex adapter contracts; never let model or fixture metadata grant authority.

**Tech Stack:** JSON Schema, the repository's dependency-free Python validator, Python `unittest`, deterministic JSON fixtures, Markdown evidence.

---

### Task 1: Add public evaluation contracts

**Files:**
- Create: `schemas/v3/runtime-candidate.schema.json`
- Create: `schemas/v3/model-candidate.schema.json`
- Create: `schemas/v3/execution-configuration.schema.json`
- Create: `schemas/v3/evaluation-run.schema.json`
- Create: `schemas/v3/evaluation-result.schema.json`
- Create: `schemas/v3/runtime-handoff.schema.json`
- Modify: `tools/v3/contract_validation.py`
- Test: `tests/v3/test_runtime_model_evaluation.py`

- [ ] Write failing tests for valid minimal records, invalid evidence/identity/authority fields, and every new contract name.
- [ ] Run the focused unittest module and observe failures caused by missing schemas and helpers.
- [ ] Add only the fields required for candidate eligibility, execution configuration, explicit handoff, separate evidence axes, and terminal outcomes.
- [ ] Register schemas in `contract_validation.py` and apply strict unknown-capability checks to runtime candidate grants and execution envelopes.
- [ ] Re-run the focused tests and retain the smallest passing contract surface.

### Task 2: Implement pure eligibility and comparison helpers

**Files:**
- Create: `tools/v3/runtime_model_evaluation.py`
- Modify: `tools/v3/contract_validation.py` if cross-record checks need a public entry point
- Test: `tests/v3/test_runtime_model_evaluation.py`

- [ ] Add tests first for runtime availability/capability eligibility, model eligibility, task-pinned behavior, permission intersection, evidence classification, deterministic configuration digests, handoff records, baselines, Pareto frontiers, terminal outcomes, and proposal-only history.
- [ ] Implement pure functions only: no subprocess discovery inside routing, no policy mutation, no model preference table, no adaptive loop.
- [ ] Use existing `intersect_permissions` and reject any model, skill, MCP, or generated declaration as an authority source.
- [ ] Ensure mock and host-managed evidence cannot rank quality; only real execution can make quality evidence eligible.
- [ ] Run focused tests, then the full suite.

### Task 3: Add candidate discovery and development/holdout fixtures

**Files:**
- Create: `fixtures/v3/model-routing/runtime-candidates.json`
- Create: `fixtures/v3/model-routing/model-candidates.json`
- Create: `fixtures/v3/model-routing/development/index.json`
- Create: `fixtures/v3/model-routing/holdout/index.json`
- Test: `tests/v3/test_runtime_model_evaluation.py`

- [ ] Add tests proving development references A–J without changing them and holdout has no expected runtime/model identity.
- [ ] Record only observed local version probes for installed runtimes; unknown executables remain unknown and no installation occurs.
- [ ] Keep model candidates separate from runtime candidates and classify static candidates as host-managed fixture evidence.
- [ ] Add twelve holdout workloads with explicit acceptance/evidence criteria and no routing identity labels.
- [ ] Validate all fixture records through the public contracts.

### Task 4: Record dogfood and research evidence

**Files:**
- Create: `docs/v3/evidence/PHASE3B_MODEL_RUNTIME_DOGFOOD_ROUTE.md`
- Create: `docs/v3/evidence/RUNTIME_CAPABILITY_MATRIX.md`
- Create: `docs/v3/evidence/MODEL_RUNTIME_EVAL_V1.md`
- Modify: `docs/v3/README.md`
- Modify: `docs/v3/ARCHITECTURE.md`
- Modify: `docs/v3/MODEL_PROFILE_CONTRACT.md`
- Modify: `docs/v3/LEARNING_AND_EVALS.md`

- [ ] Record every active dogfood stage route, selected role slots, body-loading boundary, and explicit Deep Understanding status without hidden reasoning.
- [ ] Document first-party runtime/version evidence and research lessons, separating compatibility evidence from quality evidence.
- [ ] Report baselines, live-run absence, terminal/stage evidence, independent axes, and Pareto behavior without an opaque score.
- [ ] Synchronize canonical docs to state that this is an evaluation harness, not production model routing.

### Task 5: Verify, review, and hand off

**Files:**
- Replace: `docs/v3/NEXT_CODEX_PROMPT.md`
- Modify: `docs/v3/evidence/MODEL_RUNTIME_EVAL_V1.md`

- [ ] Run the complete unittest command, `git diff --check`, fixture validation, secret/path scans, and one OCR precheck.
- [ ] Perform independent code, security, simplification, and verification reviews; record blockers honestly.
- [ ] Classify the outcome as `INSUFFICIENT_LIVE_EVIDENCE`, `ROUTING_EVIDENCE_READY`, or `RUNTIME_CAPABILITY_GAPS` from measured evidence.
- [ ] Generate a self-contained next prompt without starting the next phase.
- [ ] Commit in small semantic slices, push the stacked branch, and create a draft PR only after fresh verification.
