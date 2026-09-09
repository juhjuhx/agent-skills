# Next Codex Prompt — Phase 3B Model / Agent Routing Evaluation

Copy this prompt into the next Codex session. It defines the next bounded
evaluation task. Do not execute Phase 3B during Phase 3A.2.

---

## Mission

Repository: `juhjuhx/agent-skills`

Implement **Agent Skills Matrix v3 — Phase 3B: Model / Agent Routing
Evaluation** from the verified and quality-converged Phase 3A.2 Stage Router
MVP. Do not redesign v3, clone the Codex adapter, or implement the six
remaining native adapters in this phase.

The question is:

```text
For the same TaskSpec and stage route, what evidence supports a choice of
agent runtime + model profile for this stage?
```

Choices must emerge from measured fixtures. Never hard-code rules such as
`Claude for architecture`, `Codex for implementation`, `if agent == codex`, or
`if model == glm`.

## Start and source truth

Verify without resetting local work:

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
```

Start from the current Phase 3A.2 branch or its merged base. Read the actual
repository registry before selecting any skill ID. At the time this prompt is
generated, the source truth is 214 canonical records at registry commit
`db3b67d5b051c4223da9146b2b836a9ed45e9bac`, plus the checked-in routing
overlay and its digest-bound source metadata:

- `registry/v3/skill-routing-metadata.json`
- generated overlay: `registry/v3/skill-routing-generated.json`
- curated patch layer: `registry/v3/skill-routing-curated.json`
- compiled overlay version `v3-routing-metadata-2`
- compiled overlay digest `sha256:482720a45d8b74f5e9cda4eddc283993611510ba31403d991c4f297605f66f4b`
- session-resident snapshot: `snapshot:2349a6fe70aaf346`
- [`CATALOG_ROUTING_METADATA_CENSUS.md`](evidence/CATALOG_ROUTING_METADATA_CENSUS.md)
- [`STAGE_ROUTER_EVAL_V2.md`](evidence/STAGE_ROUTER_EVAL_V2.md)
- [`STAGE_ROUTER_EVAL_V3.md`](evidence/STAGE_ROUTER_EVAL_V3.md)
- [`ROUTING_METADATA_CURATION.md`](evidence/ROUTING_METADATA_CURATION.md)

Use the overlay as the metadata-first routing input. Do not read all 214
procedure bodies during normal route or model evaluation; load only bodies
selected by a validated route. The overlay is not a second skill library and
its inferred fields are not author-declared truth.

Read:

- `.superpowers/SKILLS_INDEX.json`
- `categories.json`
- `.superpowers/ROUTING_POLICY.yaml`
- `AGENTS.md`
- `schemas/v3/`
- `tools/v3/stage_router.py`
- `tools/v3/codex_adapter.py`
- `tools/v3/execution_bundle.py`
- `tools/v3/skill_resolver.py`
- `fixtures/v3/router/routing-eval-v1.json`
- `docs/v3/evidence/STAGE_ROUTER_EVAL_V1.md`
- `docs/v3/evidence/STAGE_ROUTER_EVAL_V2.md`
- `docs/v3/evidence/CATALOG_ROUTING_METADATA_CENSUS.md`
- `docs/v3/evidence/STAGE_ROUTER_EVAL_V3.md`
- `docs/v3/evidence/ROUTING_METADATA_CURATION.md`

Machine-readable registry data wins over stale prose. Keep the production
registry, installer, and v2 policy unchanged.

## Preserve the Phase 3A boundary

The current route flow is:

```text
TaskSpec + Stage + SkillMetadataV3 catalog
  -> StageRouter
  -> StageRoute
  -> agent adapter
  -> execution/evidence artifacts
```

Phase 3B may use `ModelProfile` and `AgentAdapterManifest` as capability and
measurement records, but it must not move model choice into the skill router.
The Stage Router still selects skills; this phase evaluates the next boundary:

```text
validated StageRoute + runtime capability envelope + ModelProfile
  -> candidate execution configurations
  -> comparable evidence
```

`using-superpowers` remains the task/session orchestration authority and is not
a repeatedly loaded candidate skill. All active dogfood stages must emit a
valid `StageRoute` with `SKILLS_SELECTED` or `NO_SKILL_NEEDED`.

## Dogfood and stage-local routing

Use the actual installed `using-superpowers` workflow as resident authority.
Create only relevant stages, for example `UNDERSTAND`, `RESEARCH`, `DESIGN`,
`PLAN`, `IMPLEMENT`, `REVIEW`, `VERIFY`, `HARDEN`, and `HANDOFF`. Re-run the
Phase 3A Stage Router independently at each active stage. Load only selected
`SKILL.md` bodies downstream; do not load the whole catalog. Record the run in
a concise `docs/v3/evidence/PHASE3B_MODEL_AGENT_DOGFOOD_ROUTE.md` artifact
without hidden chain-of-thought.

## Research and provenance lanes

Before comparing runtimes or model profiles, perform fresh source-driven
research. For every runtime under test record, when available:

- observed installed version;
- latest stable release/tag and resolved immutable commit;
- official source/release ref used for the contract;
- current upstream source snapshot;
- documentation snapshot date/ref;
- native support (`NATIVE`, `EMULATED`, `HOST_MANAGED`, `UNSUPPORTED`);
- availability (`INSTALLED`, `RELEASE_SUPPORTED`, `UPSTREAM_ONLY`, `UNKNOWN`).

Keep support and availability separate. Do not claim installed conformance from
unversioned current documentation. Do not put provider-specific model IDs or
documentation URLs into universal routing logic.

Research the runtime layer separately from the model layer:

- runtimes: Codex, Claude Code, OpenCode, Hermes, MiMo Code, ZCode, DeepSeek
  Harness;
- model/provider profiles: OpenAI-compatible, Anthropic-compatible, DeepSeek,
  GLM, MiMo, plus future profiles.

If only the Codex adapter is executable in the current repository, use native
Codex execution plus explicit host-managed/mock projections for other runtimes.
Do not pretend a fixture is a production adapter.

## Evaluation matrix

Build a matrix of real task fixtures × active stages × compatible agent/model
configurations. Reuse the ten Phase 3A workloads and add representative
multi-stage workloads only when needed:

- coding and bugfix;
- API/architecture design;
- frontend/browser-visible work;
- source research;
- security-sensitive change;
- repository audit;
- release/handoff.

For each cell capture:

```text
task_id
stage
agent_runtime
model_profile
selected_skills
adapter_capabilities
permission envelope
context bytes/tokens
tool schemas and tool calls
duration/latency class
reroutes
files changed
tests
verification evidence
user correction
completion result
security findings
```

Use independent evidence classes. A model's self-report is not equivalent to
test evidence, runtime evidence, or a native security scan.

## Comparison metrics

Report separate, interpretable measures rather than one synthetic quality
number:

- route compatibility and capability coverage;
- task completion and acceptance-criteria coverage;
- evidence quality and verification pass rate;
- near-miss activation and over/under-routing;
- context/token and tool-schema cost;
- tool-call count and latency/duration;
- reroute count and recovery quality;
- user corrections and regression rate;
- security/provenance failures;
- cross-agent artifact portability.

Unknown or missing measurements stay explicit. Historical observations may
generate a proposal, but they must not silently rewrite routing policy or
model-selection policy.

## Capability negotiation and permissions

Use `TaskSpec.required_capabilities` and the adapter manifest to negotiate
capabilities. Model profiles describe inference capabilities and limits only;
they never grant filesystem, network, MCP, sandbox, publishing, or deletion
authority. The effective permission remains the least-privilege intersection
of TaskSpec, policy, adapter, route, and live runtime restrictions.

Test that:

- an unknown runtime/model capability fails closed or is marked unavailable;
- a model profile cannot widen OS permissions;
- a skill, MCP declaration, plugin, or generated output cannot widen them;
- incompatible runtime/model combinations are not executable;
- host-managed or unsupported surfaces are not emitted as fake native fields.

## Tests

Keep all Phase 1, Codex, and Phase 3A tests green. Add focused tests for:

- deterministic candidate matrices and repeated measurements;
- agent/model identifier separation;
- same TaskSpec producing comparable but runtime-specific projections;
- no provider hard-coding in universal routing decisions;
- capability and permission negotiation;
- near-miss fixture triggering;
- cross-agent artifact/evidence comparison;
- context/tool cost accounting;
- regression detection and proposal-only history;
- security and provenance failures;
- `NO_SKILL_NEEDED` remaining free of model selection side effects.

No external runtime side effect is required unless a verified installed runtime
is available. Do not install MCP servers or new dependencies merely to create a
matrix cell.

## Reviews and anti-bloat

Use independent installed skills for architecture/code review, simplification,
security/hardening, doubt-driven evaluation, and verification. Do not hand one
reviewer's conclusion to the next reviewer before independent analysis.

Run the Alibaba OpenCodeReview precheck once. If native authentication returns
401, record `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH`; do not relabel delegate review
as native OCR.

Keep implementation to data, measurement, validators, and small comparison
helpers. Do not add a database, event bus, worker pool, provider registry,
general scheduler, cloud orchestrator, or new adapter framework without a
demonstrated boundary requirement.

## Non-goals

Do not implement Phase 3 cross-runtime adapters, rewrite `install.sh` or
`.superpowers/ROUTING_POLICY.yaml`, migrate the production registry, install
MCP servers, auto-import external skills, expose hidden chain-of-thought, or
silently change policy from evaluation history. Do not execute a later phase in
this task.

## Deliverables

Keep commits small and semantic. Produce:

- source/provenance notes for every researched runtime/model lane;
- comparison fixtures and machine-readable measurements;
- focused validation and compatibility tests;
- concise dogfood and evaluation evidence under `docs/v3/evidence/`;
- canonical documentation updates only where the measured contract becomes
  more precise;
- a Draft stacked PR with explicit limitations and failed/blocked lanes.

The result must make a measured recommendation—or explicitly conclude that the
evidence is insufficient—without hard-coded runtime/model preferences.
