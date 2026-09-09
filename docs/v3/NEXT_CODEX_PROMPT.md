# NEXT CODEX PROMPT
# PHASE 3C.2 — OPENCODE BENCHMARK-SAFE READ-ONLY ADAPTER BOUNDARY

Repository:
juhjuhx/agent-skills

Current evidence decision:
RUNTIME_CAPABILITY_GAPS

This is a narrowly scoped follow-up to Phase 3C.1. Do not start Phase 4.
Do not implement model routing, adaptive routing, Stage Router weight changes,
or any runtime adapter other than the demonstrated OpenCode boundary below.

============================================================
0. MISSION
============================================================

Close only the missing execution boundary identified by the live evidence:

validated StageRoute
    → runtime-neutral execution contract
    → OpenCode 1.18.25 native read-only projection
    → bounded headless H03 execution
    → sanitized execution evidence

The goal is to determine whether the installed OpenCode runtime can consume a
portable route under a proved least-privilege configuration. This is not a
quality claim against Codex or any model. A completed cross-runtime cell would
be a CONFIGURATION_EFFECT candidate only.

============================================================
1. READ CURRENT SOURCE TRUTH
============================================================

Before editing, verify:

git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin

Read the current Phase 3C.1 evidence and implementation:

tools/v3/live_benchmark.py
tools/v3/runtime_model_evaluation.py
schemas/v3/live-execution-record.schema.json
tools/v3/stage_router.py
docs/v3/evidence/MODEL_RUNTIME_EVAL_V3.md
fixtures/v3/model-routing/runs/phase3c/

Freshly inspect the installed OpenCode 1.18.25 contract:

opencode --version
opencode --help
opencode run --help
opencode agent --help
opencode mcp --help

Use current first-party OpenCode documentation/source as supporting evidence,
but installed-version help and behavior win for executable claims. Do not
encode documentation URLs into runtime logic.

============================================================
2. SCOPE AND SAFETY
============================================================

Do not install OpenCode, models, plugins, MCP servers, dependencies, or
credentials. Do not change the canonical skill bodies, registry policy, or
Stage Router weights. Do not use --auto or another broad permission bypass.

The adapter must consume a validated StageRoute. It must not call the general
router, choose skills, or widen the TaskSpec permission envelope.

The target workload is read-only H03 API/interface design. Execute only in a
temporary fixture repository or isolated worktree. Do not touch a user
project, publish, deploy, or mutate an external repository.

============================================================
3. RESEARCH THE INSTALLED PERMISSION BOUNDARY
============================================================

Establish an evidence table for the installed release:

portable control
→ exact OpenCode 1.18.25 surface/configuration
→ support: NATIVE / HOST_MANAGED / UNSUPPORTED
→ availability: INSTALLED / UNKNOWN
→ verification evidence

The minimum read-only contract must prove, at runtime or through the exact
installed configuration contract:

- deny by default;
- allow read/list/glob/grep only inside the isolated fixture;
- deny edit/write;
- deny bash/shell and task/subagent execution;
- deny external directories;
- deny web/network tools;
- deny .env, credential, and secret paths;
- no plugin or MCP auto-installation;
- bounded noninteractive output;
- explicit timeout and no inherited interactive stdin.

If the installed contract cannot prove least privilege, record
LIVE_LANE_BLOCKED and stop without broadening permissions.

============================================================
4. IMPLEMENT ONLY THE SMALLEST BOUNDARY
============================================================

Prefer small data objects and pure functions. Do not add a manager, registry,
service, database, plugin framework, scheduler, or model router.

The boundary may include only what is needed for:

- OpenCode runtime provenance and installed-contract evidence;
- a runtime-neutral execution request/reference;
- an OpenCode-native permission/config projection;
- selected-only skill references and digests;
- bounded headless invocation;
- LiveExecutionRecord generation and sanitization.

The universal bundle must remain runtime-neutral. OpenCode-specific keys may
appear only in the OpenCode projection layer and only when verified by the
installed contract. Unknown native values fail closed.

============================================================
5. STAGEROUTE AND SKILL BOUNDARY
============================================================

The flow must remain:

TaskSpec
→ existing Stage Router
→ StageRoute
→ OpenCode adapter

SKILLS_SELECTED resolves only the selected SkillMetadataV3 records and
loads a selected body only when execution requires it. NO_SKILL_NEEDED loads
zero additional skill bodies. No full catalog or unrelated SKILL.md may
enter the OpenCode projection.

Preserve skill ID, source/ref, digest, role, trust, and load-state provenance.
Do not serialize raw skill bodies, prompts, stdout/stderr, credentials, auth
headers, session identifiers, or MCP secrets.

============================================================
6. PERMISSION INTERSECTION
============================================================

Effective authority remains:

TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime restrictions

The OpenCode projection may be narrower than requested and report
DEGRADED/HOST_MANAGED explicitly. It may never be broader. A skill, MCP
declaration, model profile, plugin, or generated config cannot grant
authority.

Add negative tests for:

- portable write/edit request cannot become OpenCode allow;
- external path request cannot become an allowed external directory;
- unknown permission fails closed;
- .env and secret patterns remain denied;
- --auto or equivalent broad bypass is rejected;
- task/subagent, bash, web, and plugin/MCP loading are denied for H03.

============================================================
7. EVIDENCE AND METRICS
============================================================

Record a fresh append-only run under:

fixtures/v3/model-routing/runs/phase3c/

Use the existing LiveExecutionRecord contract. Preserve metric semantics:

- process launch is not model_calls = 1;
- token values remain UNKNOWN unless the installed OpenCode output contract
  proves their aggregation;
- actual cost remains UNKNOWN when not exposed;
- every metric retains source field, aggregation, confidence, and status;
- raw output remains digest/byte metadata only.

Capture start/end SHA, changed files, diff digest, tests, route/task/skill
digests, permission envelope, runtime version, model/effort if observable,
tool/MCP state, and all confounders. A smoke/configuration result is not
quality evidence unless H03 produces a verifiable DecisionRecord.

============================================================
8. TESTS
============================================================

Keep all existing tests green. Add focused tests for:

- installed OpenCode provenance and contract revision;
- deterministic projection for identical inputs;
- projection contains no unsupported invented fields;
- deny-by-default read-only projection;
- permission intersection never widens authority;
- unknown native/portable permissions fail closed;
- selected-only skill resolution and zero-body NO_SKILL_NEEDED behavior;
- raw skill bodies/prompts/stdout/stderr/credentials are not serialized;
- timeout/noninteractive stdin behavior;
- blocked lane produces no quality claim;
- successful H03 result is classified as REAL_EXECUTION only after
  independent acceptance verification;
- cross-runtime result remains CONFIGURATION_EFFECT, never MODEL_EFFECT.

Run:

PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
git diff --check

============================================================
9. REVIEWS
============================================================

Use the resident using-superpowers authority and existing Stage Router for
the implementation work. Emit a StageRoute for each active stage and load
only selected skill bodies.

Run independent review lanes for:

- OpenCode contract/API correctness;
- permission and secret safety;
- simplification/anti-bloat;
- verification and evidence classification.

Run the OCR auth precheck once. If it returns 401, record
OCR_NATIVE_DIFF = BLOCKED_BY_AUTH; do not retry repeatedly or relabel
delegate review as native OCR.

============================================================
10. STOP CONDITIONS
============================================================

Stop and report the exact blocker if:

- OpenCode 1.18.25 cannot express or prove the least-privilege boundary;
- model/provider identity or permissions cannot be recorded safely;
- the run requires interactive approval or an unsafe bypass;
- output cannot be sanitized;
- the result would need a new universal routing abstraction.

Do not turn a blocked lane into a preference or claim that Phase 4 is ready.

============================================================
11. HANDOFF
============================================================

Update docs/v3/evidence/MODEL_RUNTIME_EVAL_V4.md without overwriting V3.
Report:

- installed OpenCode provenance and exact contract;
- support/availability mapping;
- permission projection and negative evidence;
- StageRoute and selected skill provenance;
- live result, terminal/stage outcomes, metrics, and confounders;
- security and serialization review;
- whether a second completed execution configuration now exists.

If OpenCode completes safely, the next proposal may evaluate a bounded
configuration comparison. If it remains blocked, propose only the smallest
missing OpenCode or Claude execution boundary. Do not implement Phase 4,
adaptive routing, or additional adapters in this task.
