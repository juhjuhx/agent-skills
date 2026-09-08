# Agent Skills Matrix v3 Codex Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile validated portable v3 contracts into a selected-only, provenance-preserving Codex-native projection without implementing a general stage router or changing the canonical registry.

**Architecture:** Keep `CompiledExecutionBundle` runtime-neutral and immutable at the data boundary. A small resolver validates selected SkillMetadataV3 records, reads only their canonical `SKILL.md` files, and preserves digests. `CodexAdapter` intersects permissions and capabilities, compiles the portable bundle, and projects only source-verified Codex surfaces (`AGENTS.md`, Skills, MCP, subagents, plugins, hooks, `config.toml` fields, sandbox/approval settings, and reasoning effort).

**Tech Stack:** JSON Schema Draft 2020-12; Python 3 standard library; `unittest`; checked-in JSON fixtures and Markdown evidence. No runtime dependency or package manager is introduced.

---

## Contract consistency findings

- **BLOCKING:** None. Phase 1 already fixes `schema_version: "3.0"`, explicit StageRoute status, open capability declarations, trust states, safe relative paths, and runtime/provider separation.
- **IMPORTANT:** `StageRoute.stage` is lower-case while dogfood stage labels are human-facing upper-case; code and evidence will normalize to the schema values. `AgentAdapterManifest.permissions` advertises policy-gated scopes but cannot express an effective grant; the Phase 2 intersection therefore takes policy and live-runtime envelopes as explicit inputs. `context_behavior` is portable descriptive metadata, never a Codex config object. `using-superpowers` remains a session-level GATE reference and is not reloaded as an ordinary skill at every stage.
- **MINOR:** Phase 1 does not model unfamiliarity as a separate TaskSpec field, so the Phase 2 dogfood record will capture it as an explicit classification artifact and use the existing `COMPLEX`/`HIGH`/`ARCHITECTURE-CHANGING` signals. The current registry cannot provide license/import timestamps or stage/role metadata; the compatibility path will preserve those fields as unavailable rather than guessing.

## Task 1: Add failing vertical-slice tests

**Files:**
- Create: `tests/v3/test_codex_adapter.py`
- Modify: `tests/v3/test_contracts.py` only if the new public schemas need to be included in the existing schema-document loop.

- [ ] **Step 1: Write the first failing test**

Create a minimal test that imports `compile_execution_bundle`, supplies the existing Phase 1 TaskSpec, selected StageRoute, Codex fixture, model fixture, and selected metadata, then asserts a runtime-neutral bundle with a stable digest. Add tests for selected-only loading, no-skill loading, permission non-escalation, evidence failure, digest invalidation, and strict projection fields in the same focused test module.

- [ ] **Step 2: Run the focused test and verify the red state**

Run:

```bash
python3 -B -m unittest tests.v3.test_codex_adapter
```

Expected result: `ImportError` or `ModuleNotFoundError` because the Phase 2 adapter modules do not exist yet. Do not implement production code before observing this failure.

## Task 2: Add portable bundle and projection schemas

**Files:**
- Create: `schemas/v3/compiled-execution-bundle.schema.json`
- Create: `schemas/v3/codex-native-projection.schema.json`
- Modify: `tools/v3/contract_validation.py` to register the two public schemas and validate their capability declarations.
- Modify: `tests/v3/test_contracts.py` to load the two additional schema documents.

- [ ] **Step 1: Define the portable bundle schema**

Use Draft 2020-12, `schema_version: "3.0"`, `additionalProperties: false`, and only portable fields: bundle version, contract references, selected skill identity/ref/digest/role, effective capabilities, permission envelope, static/dynamic/tool-schema context envelope, reasoning artifact references, evidence requirements, registry epoch, provenance, status, and bundle digest. Do not add Codex-specific property names or runtime branch fields.

- [ ] **Step 2: Define the Codex projection schema**

Use a strict allowlist for a projection containing `runtime_id: "codex"`, the source bundle digest, support-level records, selected native skill paths, generated `config.toml` values whose keys are verified by the official Codex source, native instruction path references, MCP/subagent/plugin/hook references, and provenance. Unsupported or host-managed concepts must be represented by support metadata, not invented Codex configuration keys.

- [ ] **Step 3: Make the validator discover both schemas**

Extend `SCHEMA_FILES` with `CompiledExecutionBundle` and `CodexNativeProjection`. Keep the existing unknown-capability rule: unknown granted capabilities remain errors, while declarations may remain explicit warnings. Update the schema-document test tuple.

- [ ] **Step 4: Run schema and Phase 1 tests**

Run:

```bash
python3 -B -m unittest tests.v3.test_contracts tests.v3.test_codex_adapter
```

Expected result: the adapter test remains red while the public schema documents and existing Phase 1 tests pass.

- [ ] **Step 5: Commit**

```bash
git add schemas/v3 tools/v3/contract_validation.py tests/v3/test_contracts.py
git commit -m "feat(v3): add portable execution bundle"
```

## Task 3: Implement selected-only skill resolution and permission intersection

**Files:**
- Create: `tools/v3/skill_resolver.py`
- Create: `tools/v3/permission_intersection.py`
- Create: `tools/v3/reasoning_artifacts.py`

- [ ] **Step 1: Resolve only route-selected metadata**

Implement a small `SkillResolver` that receives a repository root, canonical registry path, and selected SkillMetadataV3 records. For each selected route entry, require an exact metadata record, reject `QUARANTINE` and `BLOCKED`, reject missing records with an explicit blocked result, ensure the relative source path stays inside the repository, hash the canonical `SKILL.md`, and reject a digest mismatch. Return loaded instruction bodies only for selected skills; the generated bundle and projection contain refs/digests and never skill bodies.

- [ ] **Step 2: Intersect permissions without granting authority**

Implement `intersect_permission_envelopes(task, policy, adapter, live_runtime)` with the explicit order `TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime`. Treat model profiles, skills, MCP declarations, and generated projection fields as non-authorizing inputs. Return an effective least-privilege envelope or an explicit blocked reason when a required level/scope cannot fit.

- [ ] **Step 3: Keep reasoning artifacts observable**

Implement a sanitizer/validator for allowed artifact references (`TaskSpec`, assumptions, unknowns, decision record, stage plan, alternatives, evidence, risk, verification, learning proposal). Reject keys named `chain_of_thought`, `private_reasoning`, `scratchpad`, or `hidden_reasoning` recursively.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
python3 -B -m unittest tests.v3.test_codex_adapter
```

Expected result: resolver, permission, and artifact tests pass or expose only the remaining missing adapter/compiler behavior.

## Task 4: Implement the Codex adapter and deterministic compilation

**Files:**
- Create: `tools/v3/execution_bundle.py`
- Create: `tools/v3/codex_adapter.py`
- Modify: `tools/v3/__init__.py` only if an existing package initializer exports public helpers.

- [ ] **Step 1: Add immutable canonical serialization helpers**

Use frozen dataclasses or immutable mappings at the public boundary, canonical JSON (`sort_keys=True`, compact separators), and SHA-256 over the bundle payload excluding its digest. Identical inputs must produce identical bundle and projection output; no timestamps, process IDs, or local absolute paths may enter either digest.

- [ ] **Step 2: Compile a validated StageRoute without routing**

Make `CodexAdapter.compile(route, ...)` consume a validated route and never call a router. `SKILLS_SELECTED` resolves and loads exactly the selected skill files. `NO_SKILL_NEEDED` loads zero additional skill files, preserves `no_skill_reason`, and still returns a bundle/evidence artifact. Capability mismatch, missing skill, trust rejection, or digest mismatch must return an explicit blocked/degraded result rather than silently falling back.

- [ ] **Step 3: Project only source-verified Codex surfaces**

Emit project `AGENTS.md` as a persistent instruction reference, selected canonical skill paths using Codex progressive disclosure, optional lazy MCP references, optional subagent role references only when the route requires them, plugin/hook references only when declared, and only source-verified config keys such as `model`, `model_provider`, `model_reasoning_effort`, `approval_policy`, `sandbox_mode`, and `agents.*` when present in the input. Keep native config values separate from the portable bundle. Mark static/dynamic context and evidence handling as host-managed where Codex has no equivalent field.

- [ ] **Step 4: Add an evidence gate**

Compare required evidence names with observed evidence records. Passing evidence permits a ready result; missing evidence returns a blocked result plus an observable reroute/degradation artifact. Never mark completion merely because a projection was generated.

- [ ] **Step 5: Run focused and full tests**

Run:

```bash
python3 -B -m unittest tests.v3.test_codex_adapter tests.v3.test_contracts
```

Expected result: all Phase 1 tests and the new adapter boundary tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/v3
git commit -m "feat(v3): add Codex native adapter projection"
```

## Task 5: Add fixtures and compatibility coverage

**Files:**
- Create: `fixtures/v3/bundles/selected.json`, `fixtures/v3/bundles/no-skill.json`, and `fixtures/v3/bundles/blocked-digest.json`.
- Create: `fixtures/v3/projections/codex-selected.json` and `fixtures/v3/projections/codex-no-skill.json`.
- Create: `fixtures/v3/evidence/evidence-failed.json`.
- Modify: `tests/v3/test_codex_adapter.py` and `tests/v3/test_contracts.py`.

- [ ] **Step 1: Add Codex bundle/projection fixtures**

Use the existing Codex and model fixtures, an existing current-registry compatibility projection for selected skills, and a selected-only route. Keep no model/provider fields in the portable bundle beyond a reference; keep no full skill body in generated output.

- [ ] **Step 2: Add boundary tests**

Cover deterministic compilation/projection, selected-only and no-skill loading, unrelated skill exclusion, digest preservation/invalidation, quarantine/missing/capability failures, permission intersection, model/MCP non-escalation, artifact sanitization, strict projection allowlist, bounded `AGENTS.md`, and compatibility projection status (`DIRECT`, `DERIVED`, `UNAVAILABLE`, `DEPRECATED`). Permit relationship cycles only where Phase 1 semantics permit them.

- [ ] **Step 3: Commit**

```bash
git add fixtures/v3 tests/v3
git commit -m "test(v3): verify Codex adapter boundaries"
```

## Task 6: Synchronize documentation and evidence

**Files:**
- Create: `docs/v3/CODEX_OFFICIAL_CAPABILITY_MAPPING.md`
- Create: `docs/v3/evidence/PHASE2_CODEX_DOGFOOD_ROUTE.md`
- Modify: `docs/v3/README.md`, `docs/v3/AGENT_ADAPTER_CONTRACT.md`, `docs/v3/PHASE1_MACHINE_READABLE_CONTRACTS.md`, and `docs/v3/NEXT_CODEX_PROMPT.md`.

- [ ] **Step 1: Record official capability evidence**

Link official OpenAI/Codex docs and the current `openai/codex` source revision used for research. Map each portable concept to an actual Codex surface and one of `NATIVE`, `EMULATED`, `HOST_MANAGED`, or `UNSUPPORTED`. State explicitly that runtime paths/config syntax are not universal schema fields and that plugin/hook support is source-versioned.

- [ ] **Step 2: Record every dogfood stage route**

Document TaskSpec summary, complexity/risk/ambiguity classification, Deep Understanding fallback or use, and one StageRoute record per active stage. Show selected skills by role, rejected skills and reasons, tools/input/output artifacts, evidence requirements, Codex runtime/model profile, and results. Mention `using-superpowers` residency without duplicating its full instructions. Do not record hidden reasoning.

- [ ] **Step 3: Write the Phase 3 handoff prompt**

Replace `docs/v3/NEXT_CODEX_PROMPT.md` with a self-contained Phase 3 prompt requiring fresh official-source research for Claude Code, OpenCode, Hermes, MiMo Code, ZCode, and DeepSeek Harness. Require reuse of the Phase 2 portable schemas and explicit independent projections; do not ask the next worker to copy the Codex adapter.

- [ ] **Step 4: Commit documentation and evidence**

```bash
git add docs/v3
git commit -m "docs(v3): record Codex adapter dogfood evidence"
```

## Task 7: Review, harden, measure, publish

**Files:**
- Modify only files identified by concrete review findings.

- [ ] **Step 1: Run independent review lanes**

Read the diff independently with `code-review-excellence`, `addyosmani-code-simplification`, `addyosmani-security-and-hardening`, and `verification-before-completion`. Run the required OCR probes once. If native OCR authentication returns 401, record `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`; never relabel delegate review as native OCR.

- [ ] **Step 2: Run context/performance measurement**

Measure a hypothetical all-catalog metadata count versus selected-only metadata records inspected, selected `SKILL.md` files loaded, loaded bytes/approximate tokens, and bundle/projection generation latency. Report observed values, not unmeasured token-savings claims.

- [ ] **Step 3: Perform anti-bloat and secret/path audit**

Search new files for speculative Manager/Registry/Service/Factory/Coordinator/Gateway hierarchies, absolute user paths, tokens, API keys, secret config, and invented Codex keys. Remove speculative abstractions and fix concrete findings only.

- [ ] **Step 4: Run final validation**

Run:

```bash
git diff --check
python3 -B -m unittest discover -s tests -p 'test*.py'
```

Also run a Markdown link checker if available and a fresh `AGENTS.md` size check. Confirm no runtime router, installer rewrite, registry migration, MCP install, or other adapter is present.

- [ ] **Step 5: Push and create the stacked draft PR**

```bash
git push -u origin feat/v3-codex-adapter
gh pr create --draft --base feat/v3-contract-schemas --head feat/v3-codex-adapter \
  --title "feat: add Codex native adapter vertical slice" \
  --body-file <temporary-pr-body-file>
```

The PR body must state the portable bundle, Codex projection, selected-only discovery, permission intersection, observable artifacts/evidence gates, tests, and explicit non-goals. Do not merge.

## Self-review coverage

This plan covers the Phase 2 schema, adapter, resolver, projection, selected-only loading, permission intersection, evidence failure, source-driven Codex mapping, fixtures, compatibility path, tests, reviews, context measurement, dogfood trace, and Phase 3 handoff. It intentionally does not implement the universal stage router, another runtime adapter, an installer/generator, a database, cloud orchestration, or automatic skill import.
