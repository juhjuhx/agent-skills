# Model / Runtime Evaluation V5 — OpenCode blocker diagnosis

Phase 3C.3 is the final dedicated OpenCode diagnostic pass before an explicit
cost/benefit decision about another runtime. It does not implement Phase 4,
adaptive routing, Stage Router changes, provider setup, credential changes, or
another runtime adapter.

## Decision

**OPENCODE_RUNTIME_BLOCKED**

The Phase 3C.2 native projection remains statically valid and preserves the
zero-ASK, read-only boundary. A fresh installed-version provider probe showed
that the configured `anthropic` provider is not found by OpenCode 1.18.25.
This is direct evidence for the current provider-resolution blocker. No
provider, model, credential, permission, or global configuration was changed.

The diagnostic does **not** claim that OpenCode, Anthropic, or any model is
inferior to Codex. No OpenCode H03 quality cell completed, so there is no
configuration-effect result and no model-effect result.

## Repo truth

| Field | Value |
|---|---|
| Starting base | `feat/v3-opencode-readonly-adapter` |
| Starting HEAD | `fb2d170795330eda3de07e25bd8b8d9ee383f86e` |
| Branch | `fix/v3-opencode-runtime-diagnostic` |
| Stage Router | unchanged |
| Phase 3C.2 decision | `OPENCODE_RUNTIME_BLOCKED` |
| Phase 3C.3 decision | `OPENCODE_RUNTIME_BLOCKED` |
| H03 | not run after provider blocker |
| Evidence class | diagnostic compatibility evidence; no quality claim |

## Installed runtime provenance

Fresh local checks returned:

```text
opencode --version  -> 1.18.25
opencode run --help -> --pure, --format, --agent, --model, --dir, --auto, noninteractive run
opencode agent --help -> agent list/create, --pure
opencode models --help -> provider listing surface, --pure
```

The installed executable path was observed locally but is intentionally not
persisted in evidence. First-party release resolution is:

| Field | Verified value |
|---|---|
| runtime_id | `opencode` |
| observed_version | `1.18.25` |
| release/tag | `v1.18.25` |
| release_commit | `cb7d8b2f5e44876ef98b661dc10590c915af3a9f` |
| contract_target | `INSTALLED_RUNTIME` |
| native contract revision | `opencode-v1-config-permission-run@cb7d8b2f5e44876ef98b661dc10590c915af3a9f` |
| contract digest | `sha256:3e4147fcd2a6edb726aec76ed2782343d92df9593cfcf49e8685f21bfc129853` |
| verification | local version/help, exact tag resolution, pinned contract, first-party docs/source |

Sources: [OpenCode v1.18.25 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.25),
[exact-release CLI source](https://github.com/anomalyco/opencode/tree/cb7d8b2f5e44876ef98b661dc10590c915af3a9f/packages/opencode/src/cli/cmd),
[OpenCode CLI](https://opencode.ai/docs/cli/),
[permissions](https://opencode.ai/docs/permissions/), and
[configuration](https://opencode.ai/docs/config/).

## Diagnostic hypotheses

The probes changed one variable at a time and stopped at the first direct
blocker.

| Hypothesis | Probe / changed variable | Sanitized observation | Verdict |
|---|---|---|---|
| configured provider/model is unavailable | `opencode models anthropic --pure`; provider-resolution observation only | exit 1; installed listing reports provider not found; no stdout; 50 stderr bytes | `SUPPORTED` — `PROVIDER_NOT_CONFIGURED` |
| generic UnknownError itself identifies provider/model | classifier test with only historical structured `UnknownError` | no direct provider/model status | `REJECTED` — remains `RUNTIME_UNKNOWN` |
| `--agent plan` is the cause | no execution probe after provider failure | provider priority failed first; agent not independently tested | `INCONCLUSIVE / NOT_RUN` |
| config/lifecycle merge is the cause | no additional runtime probe | current projection still uses isolated inline config; provider failure already observed | `INCONCLUSIVE / NOT_RUN` |
| JSON output contract is the cause | no additional runtime probe | output contract not reached after provider probe | `INCONCLUSIVE / NOT_RUN` |

No explicit-model probe was run: the currently configured Anthropic provider
was not found and the existing Xiaomi models were not a permitted automatic
substitution. No agent-resolution probe was run for the same reason.

## Provider status

| Evidence | Result |
|---|---|
| sanitized resolved-config primary model | `anthropic/claude-sonnet-4-5` |
| config source category | `GLOBAL_CONFIG` |
| `opencode models anthropic --pure` | `NOT_CONFIGURED / provider not found` |
| `opencode models xiaomi` | listed already-configured Xiaomi model IDs; not selected |
| auth status | provider identifiers/status only; credential contents not read |
| direct probe record | [`live-opencode-provider-probe-001.json`](../../../fixtures/v3/model-routing/runs/phase3c/live-opencode-provider-probe-001.json) |

This supports `PROVIDER_NOT_CONFIGURED` as the current environment blocker.
It does not prove that the historical Phase 3C.2 generic `UnknownError` had a
unique cause beyond the now-observed provider-resolution failure; the generic
error alone remains deliberately non-diagnostic.

## Model and agent resolution

Model identity was observable from sanitized resolved configuration, but model
availability was not treated as independently healthy because its provider
was not found. The model is therefore `BLOCKED_BY_PROVIDER`, not a model
quality observation.

`plan` appeared in installed help as an available agent-selection surface, but
no agent execution probe was run. Agent result: `NOT_TESTED_AFTER_PROVIDER_FAILURE`.

## Config / lifecycle

The Phase 3C.2 configuration isolation remains unchanged:

- `--pure` and an execution-local inline config are used;
- inherited OpenCode selector variables are removed;
- project config is disabled for the benchmark process;
- no global OpenCode config is mutated;
- provider connection configuration is not fabricated or imported from auth
  files;
- authority config remains the explicit no-ASK projection.

OpenCode configuration is merged across sources, so global/project/inline
configuration must not be conflated. The current blocker cannot be removed
without provider configuration or credentials, both outside this phase. The
safe result is to stop, not to load arbitrary global configuration wholesale.

## Output contract

No output-contract probe was performed after the direct provider failure. The
previous smoke's structured `UnknownError` remains historical evidence of a
failed run, not proof of a JSON-format defect. No raw output or diagnostic log
was persisted.

## Permission revalidation

The existing static boundary remained green:

| Surface | Effective result |
|---|---|
| read/list/glob/grep inside isolated fixture | allow only where explicitly scoped |
| edit/write | deny |
| bash/shell | deny |
| task/subagent | deny |
| web/network | deny |
| external directories | deny |
| `.env`, credentials, keys | deny |
| plugins | deny / empty |
| MCP | deny / empty |
| unresolved ASK | zero |
| `--auto` | rejected / absent |

The direct provider listing used the existing bounded subprocess helper:
explicit argv, `shell=False`, `stdin=DEVNULL`, finite timeout, and isolated
cwd. A provider/model selector changes runtime resolution only; it does not
grant OS/tool authority.

## Contract smoke and H03

The hardened Phase 3C.2 smoke was not rerun after the blocker was identified;
the user-specified rule forbids identical retries without a supported fix.

| Cell | Result |
|---|---|
| contract smoke | `BLOCKED`; previous structured `UnknownError`, workspace unchanged |
| provider-resolution probe | `BLOCKED`; direct `PROVIDER_NOT_CONFIGURED` evidence |
| H03 API/interface design | `NOT_ELIGIBLE`; smoke/provider gate did not pass |
| independent H03 verification | not applicable |
| second configuration | not established |

## Metrics

The provider probe is `n=1`, `EXPLORATORY_ONLY`, and is not quality evidence.

| Metric | Value | Semantics |
|---|---:|---|
| process wall time | 3413.1739 ms | observed `PER_RUN` host timer |
| model calls | null | `UNKNOWN`; process launch is not a call count |
| tool calls | null | `UNKNOWN`; no model run |
| input/output/tokens | null | no verified OpenCode aggregation semantics |
| actual cost | null | `UNKNOWN`; no account spend exposed |
| stdout/stderr | 0 / 50 bytes | byte counts only; raw data not persisted |

The append-only record retains digests, byte counts, and metric provenance;
it contains no prompt, stdout, stderr, credential, or raw config content.

## Configuration/model effects and Pareto

- `CONFIGURATION_EFFECT`: **not established**; OpenCode H03 did not complete.
- `MODEL_EFFECT`: **not attempted / inconclusive**; runtime and model were not
  controlled in a completed comparison.
- reasoning effect: **not attempted**.
- Pareto: OpenCode is **excluded** because there is no real quality result;
  the provider probe is compatibility/blocker evidence only.

## Security and confounders

Static and record-boundary checks cover:

- no permission widening, no unresolved ASK, no `--auto`;
- no global config mutation or provider fallback;
- no shell injection, shell-enabled subprocess, or inherited interactive stdin;
- finite timeout and isolated cwd;
- no environment dump, credential/auth serialization, raw diagnostic logs,
  prompt, or runtime session state;
- no plugin/MCP installation or loading;
- historical generic error and current direct provider probe are kept as
  separate evidence sources.

Confounders:

- the provider identity came from sanitized resolved-config evidence;
- provider listing is a no-model-invocation diagnostic;
- no H03 artifact exists for this phase;
- local global configuration may contain the model selection, but its auth
  material was not imported or serialized;
- OpenCode was not compared against a completed Codex cell in this phase.

## Final cause and next decision

```yaml
final_cause: PROVIDER_NOT_CONFIGURED
evidence_status: DIRECT_PROBE
decision: OPENCODE_RUNTIME_BLOCKED
contract_status: valid_static_boundary
quality_status: no_quality_claim
```

This is the final dedicated OpenCode diagnostic stop. The next value-bearing
path is a fresh Claude read-only boundary research/probe, not another
OpenCode diagnostic subphase. A future phase may revisit OpenCode only when a
user-provided/pre-existing provider configuration can be safely verified; it
must not auto-authenticate, choose another model, or broaden permissions.

## Review status

- runtime/source diagnosis: direct installed provider evidence recorded;
  generic errors remain fail-closed;
- permission/security: static no-ASK and serialization boundary preserved;
- evidence classification: diagnostic probe has no quality claim;
- simplification: no provider registry, runtime manager, retry loop, or new
  orchestration framework added;
- verification: focused schema/classifier tests pass; full-suite result is
  recorded with this change.

OCR status is recorded in the delivery summary. If native authentication is
unavailable, no delegate/static review is relabeled as native OCR.
