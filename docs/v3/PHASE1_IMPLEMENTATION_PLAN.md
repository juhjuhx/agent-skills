# Agent Skills Matrix v3 Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the existing v3 routing authority and test-driven development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned, validated machine-readable contracts for TaskSpec, skills, agent runtimes, model profiles, and stage routes without implementing the stage router.

**Architecture:** JSON Schema documents define the portable data boundary. A small Python standard-library validator adds conditional route rules, capability resolution, relationship semantics, and read-only compatibility projection. Fixtures keep agent runtimes separate from model/provider profiles.

**Tech Stack:** JSON Schema Draft 2020-12, Python 3 standard library, `unittest`, JSON fixtures.

---

### Task 1: Define the five contract schemas

**Files:**
- Create: `schemas/v3/common.schema.json`
- Create: `schemas/v3/task-spec.schema.json`
- Create: `schemas/v3/skill-metadata-v3.schema.json`
- Create: `schemas/v3/agent-adapter-manifest.schema.json`
- Create: `schemas/v3/model-profile.schema.json`
- Create: `schemas/v3/stage-route.schema.json`

- [x] Add `schema_version: "3.0"` and portable field boundaries.
- [x] Keep runtime identity and provider/model identity in separate schemas.
- [x] Make `StageRoute.status` explicit and conditional on selected versus no-skill routes.

### Task 2: Implement validation and compatibility projection

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/v3/__init__.py`
- Create: `tools/v3/contract_validation.py`
- Create: `tools/v3/compatibility.py`

- [x] Validate the checked-in schema subset without adding a runtime dependency.
- [x] Treat unknown requirements as unresolved warnings and unknown grants as errors.
- [x] Reject unsafe absolute/traversal paths and forbidden relationship cycles.
- [x] Project current registry records without inventing unavailable provenance.

### Task 3: Add fixtures and compatibility tests

**Files:**
- Create: `fixtures/v3/taskspec/`
- Create: `fixtures/v3/skills/`
- Create: `fixtures/v3/agents/`
- Create: `fixtures/v3/models/`
- Create: `fixtures/v3/routes/`
- Create: `fixtures/v3/compatibility/`
- Create: `tests/v3/test_contracts.py`

- [x] Cover minimal/full TaskSpec and all seven runtime fixtures.
- [x] Cover OpenAI-compatible, Anthropic-compatible, DeepSeek, GLM, and MiMo profiles.
- [x] Cover selected/no-skill route status and invalid silent routes.
- [x] Cover schema versions, trust, permissions, roles, relationships, cycles, capabilities, paths, and current registry import.

### Task 4: Synchronize canonical documentation and evidence

**Files:**
- Modify: `docs/v3/README.md`
- Modify: `docs/v3/USING_SUPERPOWERS.md`
- Modify: `docs/v3/STAGE_ROUTER.md`
- Modify: `docs/v3/SKILL_METADATA_AND_GRAPH.md`
- Modify: `docs/v3/AGENT_ADAPTER_CONTRACT.md`
- Modify: `docs/v3/MODEL_PROFILE_CONTRACT.md`
- Create: `docs/v3/PHASE1_MACHINE_READABLE_CONTRACTS.md`
- Create: `docs/v3/evidence/PHASE1_DOGFOOD_ROUTE.md`
- Create: `docs/v3/NEXT_CODEX_PROMPT.md`

- [x] Record the first stage-local routing trace without hidden reasoning.
- [x] Document `using-superpowers` session-level residency.
- [x] Link implementation artifacts while keeping runtime router work deferred.

### Task 5: Verify and hand off

**Files:**
- Test: `tests/v3/test_contracts.py`

- [x] Run `python3 -m unittest discover -s tests -p 'test_*.py' -v`.
- [x] Run `git diff --check` and the security/provenance scans.
- [x] Do not begin the Codex adapter vertical slice in this phase.
