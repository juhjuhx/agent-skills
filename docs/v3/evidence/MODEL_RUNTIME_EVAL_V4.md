# Model / Runtime Evaluation V4 — OpenCode read-only boundary

Phase 3C.2 is a bounded native-boundary pass. It does not implement Phase 4,
adaptive routing, Stage Router changes, or another runtime adapter.

## Decision

**OPENCODE_RUNTIME_BLOCKED**

The portable bundle and OpenCode projection pass the static contract, schema,
permission, selected-only, and serialization gates. A bounded contract smoke
then reached installed OpenCode '1.18.25', but returned a structured
'UnknownError' without an actionable cause. Because the smoke did not produce a
usable response, the unchanged H03 workload was not started and no second
runtime quality configuration was established.

This is not a claim that OpenCode or its model is worse than Codex. No quality,
model-effect, or Pareto conclusion is drawn from the blocked smoke.

## Repo truth

| Field | Value |
|---|---|
| Starting base | 'feat/v3-live-routing-evidence-2' |
| Starting HEAD | '20401eeea8eb60bdd87081d923f9cb78fb5eb049' |
| Implementation branch | 'feat/v3-opencode-readonly-adapter' |
| Stage Router | unchanged |
| H03 fixture | unchanged; smoke gate failed before H03 |
| Evidence class | 'UNAVAILABLE' for the smoke; no quality evidence |

## Installed OpenCode provenance

Fresh local probes reported:

~~~
opencode --version  -> 1.18.25
opencode --help     -> run, --pure, --format, --agent, --model, --auto
opencode run --help -> noninteractive run, --pure, --format json, --agent, --dir
opencode agent --help / opencode mcp --help -> inspected
~~~

First-party release resolution:

| Field | Verified value |
|---|---|
| runtime_id | 'opencode' |
| observed_version | '1.18.25' |
| release/tag | 'v1.18.25' |
| release commit | 'cb7d8b2f5e44876ef98b661dc10590c915af3a9f' |
| release date | '2026-08-28' |
| contract target | 'INSTALLED_RUNTIME' |
| native contract revision | 'opencode-v1-config-permission-run@cb7d8b2f5e44876ef98b661dc10590c915af3a9f' |
| contract digest | 'sha256:3e4147fcd2a6edb726aec76ed2782343d92df9593cfcf49e8685f21bfc129853' |
| source files | packages/opencode/src/config/config.ts; packages/opencode/src/cli/cmd/run.ts |
| verification | local version/help, official tag resolution, exact-release source, current permission/config/skill docs |

Sources: [OpenCode v1.18.25 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.25),
[exact-release config source](https://raw.githubusercontent.com/anomalyco/opencode/cb7d8b2f5e44876ef98b661dc10590c915af3a9f/packages/opencode/src/config/config.ts),
[exact-release run source](https://raw.githubusercontent.com/anomalyco/opencode/cb7d8b2f5e44876ef98b661dc10590c915af3a9f/packages/opencode/src/cli/cmd/run.ts),
[permissions](https://opencode.ai/docs/permissions/),
[configuration](https://opencode.ai/docs/config/), and
[skills](https://opencode.ai/docs/skills).

## Native support and availability

Support and runtime availability are separate dimensions.

| Portable concept | Native surface | Support | Availability | Phase 3C.2 treatment |
|---|---|---|---|---|
| Project invariants | AGENTS.md | NATIVE | INSTALLED | small persistent context only |
| Skill discovery | native skill tool | NATIVE | INSTALLED | selected-only host resolution |
| Skill body delivery | host-loaded canonical SKILL.md | HOST_MANAGED | INSTALLED | never copied as a second library |
| Runtime config | OPENCODE_CONFIG_CONTENT | NATIVE_EXACT | INSTALLED | inline per-run config |
| Permission rules | v1 permission allow/ask/deny | NATIVE_EXACT | INSTALLED | explicit no-ASK map |
| Headless run | opencode run | NATIVE_EXACT | INSTALLED | --pure --format json --agent plan --dir |
| Plugins | --pure / plugin | NATIVE_EXACT | INSTALLED | disabled for H03 |
| MCP | mcp config | NATIVE_EXACT | INSTALLED | empty and denied for H03 |
| Static/dynamic context accounting | portable host envelope | HOST_MANAGED | INSTALLED | metadata only |
| Evidence gate | portable host verifier | HOST_MANAGED | INSTALLED | smoke cannot self-certify H03 |

## No-ASK permission proof

The generated H03 projection is intentionally narrower than the portable
contract. It contains every known OpenCode permission class and the top-level
wildcard:

- read, list, glob, and grep: wildcard deny, then allow only the isolated fixture;
- .env, .env.*, credential, and key patterns: explicit final deny rules;
- edit, bash, task, external_directory, webfetch, websearch, repo_clone,
  repo_overview, lsp, doom_loop, question, todowrite, and skill: explicit deny;
- plugin: [] and mcp: {};
- no ask action is emitted anywhere;
- --auto and extra CLI arguments are rejected;
- OPENCODE_DISABLE_PROJECT_CONFIG=true is set after removing inherited
  OpenCode config selectors;
- shell=False, stdin=DEVNULL, isolated cwd, and finite timeout are
  host-enforced.

OpenCode applies the last matching permission rule. The renderer preserves
rule order so the isolated allow precedes the final secret denials. This is a
static proof of the generated config, not a claim that a failed runtime
response completed H03.

Portable authority remains:

~~~
TaskSpec ∩ policy ∩ AgentAdapterManifest ∩ live runtime restrictions
~~~

No skill, ModelProfile, MCP declaration, plugin declaration, or generated
projection widens that intersection. Unknown portable permission and unknown
native config fields fail closed.

## StageRoute and selected-only projection

The current Stage Router was not modified and the adapter does not import or
invoke it. The adapter consumed two already-built routes:

| Route | Status | Body behavior | Result |
|---|---|---|---|
| contract smoke | NO_SKILL_NEEDED | 0 selected; 0 bodies | bundle/projection compiled successfully |
| H03 design | SKILLS_SELECTED | 4 selected refs; 3 bodies execution-local | compiled only; not executed after smoke gate failed |

The H03 selected IDs were using-superpowers,
test-driven-development, code-review-excellence, and
verification-before-completion. Public projection/evidence retained only ID,
source/ref, digest, role, trust, load state, and byte metrics. Raw SKILL.md
contents never enter the projection or serializable adapter result.

The resident using-superpowers authority is not reloaded as a normal skill on
each stage. The development trace is in
[PHASE3C2_OPENCODE_DOGFOOD_ROUTE.md](PHASE3C2_OPENCODE_DOGFOOD_ROUTE.md).

## Contract smoke

The bounded smoke used a temporary fixture containing one harmless marker and
the exact projected command:

~~~
opencode run --pure --format json --agent plan --dir <isolated-fixture> <prompt>
shell=False; stdin=DEVNULL; timeout=30s; --auto absent
~~~

Observed result:

| Field | Evidence |
|---|---|
| process | launched |
| exit | non-zero (1) |
| duration | 1607.6 ms |
| stdout | JSON, 218 bytes, digest-only in record |
| stderr | 0 bytes |
| structured result | type=error, UnknownError; no actionable cause |
| workspace | unchanged before/after |
| model/call/tool/token/cost | unknown; not exposed by the response |
| terminal | BLOCKED |
| evidence class | UNAVAILABLE |

The second same-boundary diagnostic produced the same structured error class;
its sanitized diagnostic was used only to classify the blocker. No raw output,
prompt, path, environment, credentials, or session value was persisted. The
append-only record is
[live-opencode-contract-smoke-001.json](../../../fixtures/v3/model-routing/runs/phase3c/live-opencode-contract-smoke-001.json).

## H03 gate

The unchanged H03 API/interface-design workload was **not run**. The two-step
gate requires the contract smoke to complete safely before H03. The previous
historical blocked record remains untouched and is not counted as a completed
OpenCode configuration. Consequently:

- H03 terminal outcome: NOT_RUN_AFTER_SMOKE_BLOCK;
- H03 quality: no values;
- CONFIGURATION_EFFECT: not established by this phase;
- MODEL_EFFECT: INCONCLUSIVE / not attempted;
- reasoning-effort effect: not attempted;
- Pareto inclusion: none for OpenCode.

## Metric semantics

The public smoke record uses the Phase 3C.1 metric policy:

| Metric | Value | Semantics |
|---|---:|---|
| wall/runtime time | 1607.6 ms | observed PER_RUN host timer |
| model calls | null | UNKNOWN; process launch is not a call count |
| tool calls | null | UNKNOWN |
| input/output/tokens total | null | OpenCode response did not prove aggregation |
| actual cost | null | UNKNOWN |

The record retains source field, aggregation, confidence, and status for each
metric. It is EXPLORATORY_ONLY and cannot influence model/runtime preference.

## Security review

Static checks passed for:

- zero unresolved ASK paths in the generated projection;
- fail-closed write, shell, task, web, external-directory, secret, plugin, and
  MCP rules;
- no inherited OpenCode config selector that could reintroduce a broader
  project config;
- no --auto, shell execution, inherited interactive stdin, or unbounded
  timeout;
- no model or skill metadata authority grant;
- selected-only body loading and no raw body/prompt/output/credential
  serialization;
- temporary fixture isolation and unchanged file digest.

The runtime error prevented end-to-end proof of provider/runtime behavior. The
record therefore keeps quality and metric claims unknown rather than inferring
safety or success from process launch.

## Review lanes

- **OpenCode contract/API:** PASS for the narrow pinned config/run fields and
  projection schema.
- **Permission/secret safety:** PASS for static no-ASK, fail-closed, and
  serialization tests; runtime behavior remains blocked/unknown after the
  structured error.
- **Simplification:** PASS; no manager, registry, service, scheduler, database,
  or plugin framework was added.
- **Evidence classification:** PASS; the smoke is UNAVAILABLE, not quality
  failure or model evidence; H03 was gated.
- **OCR:** OCR_NATIVE_DIFF = BLOCKED_BY_AUTH after one precheck. The installed
  open-code-review v1.11.7 returned HTTP 401; no retry or delegate relabeling
  was performed.

## Files and tests

Implementation files:

- [tools/v3/opencode_adapter.py](../../../tools/v3/opencode_adapter.py)
- [tools/v3/opencode_native_contract.py](../../../tools/v3/opencode_native_contract.py)
- [schemas/v3/opencode-native-contract.schema.json](../../../schemas/v3/opencode-native-contract.schema.json)
- [schemas/v3/opencode-native-projection.schema.json](../../../schemas/v3/opencode-native-projection.schema.json)
- [fixtures/v3/opencode/opencode-native-contract-1.18.25.json](../../../fixtures/v3/opencode/opencode-native-contract-1.18.25.json)

Verification command:

~~~
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
~~~

The focused adapter/live tests passed after adding the permission-order and
inherited-config-selector regressions. The full repository suite passed with
**223 tests in 36.656 seconds**; the checked-in smoke record also validates
against the public LiveExecutionRecord schema.

## Next decision

This phase does not establish a second completed execution configuration. The
next proposal is blocker-specific: diagnose the installed OpenCode
UnknownError / provider or headless lifecycle boundary without changing
permissions, enabling --auto, installing tools, running H03, or starting
Phase 4. See [NEXT_CODEX_PROMPT.md](../NEXT_CODEX_PROMPT.md).
