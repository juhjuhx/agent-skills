# NEXT CODEX PROMPT
# PHASE 3C.3 — OPENCODE RUNTIME BLOCKER DIAGNOSTIC

Repository:
juhjuhx/agent-skills

Current implementation branch:
feat/v3-opencode-readonly-adapter

Current decision:
OPENCODE_RUNTIME_BLOCKED

This is a blocker-specific follow-up. Do not start Phase 4.
Do not modify Stage Router weights.
Do not implement Claude, Hermes, MiMo, ZCode, or DeepSeek adapters.
Do not broaden permissions, use --auto, install tools, install models,
change credentials, or run the unchanged H03 workload before the contract
smoke passes.

============================================================
0. MISSION
============================================================

Diagnose only the installed OpenCode 1.18.25 bounded smoke failure:

structured JSON error
type = error
name = UnknownError
no actionable cause
exit = 1
no stderr
workspace unchanged

The Phase 3C.2 projection and no-ASK static contract already pass. Determine
whether the remaining blocker is a provider/model availability issue, an
installed-runtime lifecycle/config issue, an output-contract issue, or
UNKNOWN. Do not infer a cause from a generic error.

Success means a trustworthy contract smoke can complete under the existing
read-only boundary. It does not yet establish OpenCode H03 quality or model
superiority.

============================================================
1. PRESERVE THE HARDENED BOUNDARY
============================================================

Use the existing:

TaskSpec
StageRoute
CompiledExecutionBundle
OpenCodeAdapter
OpenCodeNativeProjection
LiveExecutionRecord

Do not add a RuntimeManager, ProviderRegistry, ExecutionService, scheduler,
database, or generic diagnostic framework.

Keep:

- explicit no-ASK permission entries;
- isolated fixture read/list/glob/grep only;
- edit/write, bash, task, external directory, web, secrets, plugin, and MCP
  denied;
- no --auto and no extra CLI arguments;
- shell=False;
- stdin=DEVNULL;
- finite timeout;
- OPENCODE_CONFIG_CONTENT;
- OPENCODE_DISABLE_PROJECT_CONFIG=true;
- inherited OpenCode config selectors removed;
- no global OpenCode configuration mutation;
- raw prompt/output/stderr/credentials/session data out of evidence.

============================================================
2. FRESH SOURCE AND RUNTIME TRUTH
============================================================

Read the current Phase 3C.2 files and evidence:

tools/v3/opencode_adapter.py
tools/v3/opencode_native_contract.py
schemas/v3/opencode-native-contract.schema.json
schemas/v3/opencode-native-projection.schema.json
tools/v3/live_benchmark.py
docs/v3/evidence/MODEL_RUNTIME_EVAL_V4.md
fixtures/v3/model-routing/runs/phase3c/live-opencode-contract-smoke-001.json

Verify locally:

opencode --version
opencode --help
opencode run --help
opencode agent --help
opencode mcp --help

Use the pinned release:

v1.18.25
cb7d8b2f5e44876ef98b661dc10590c915af3a9f

Do not silently substitute current upstream behavior.

============================================================
3. DIAGNOSTIC HYPOTHESES

============================================================

Test hypotheses in this order, using the smallest safe observation:

A. PROVIDER / MODEL
Can the installed runtime identify or reach an already-configured provider
without exposing credentials? Record only provider/model identifiers or
redacted availability status. Never print environment contents or auth
headers.

B. CONFIG / LIFECYCLE
Does the exact inline config plus --pure/--dir/--agent contract start
correctly? Inspect only sanitized local metadata/log structure. Do not persist
raw logs.

C. OUTPUT
Does the installed runtime's --format json contract produce a usable
success shape for a harmless read-only prompt? Do not change to a broader or
interactive mode merely to get output.

D. PERMISSION
Revalidate the existing projection. If any class resolves to ASK or a
managed/global setting can be shown to override the explicit boundary,
classify OPENCODE_CONTRACT_BLOCKED. Do not compensate with a broad allow.

E. UNKNOWN
If the runtime returns only a generic UnknownError and no safe evidence
distinguishes A-D, preserve OPENCODE_RUNTIME_BLOCKED with cause UNKNOWN.

Do not run all hypotheses repeatedly. One additional bounded probe is allowed
only when it answers a newly identified hypothesis.

============================================================
4. TWO-STEP EXECUTION GATE

============================================================

STEP A — SMOKE

Use one temporary fixture with one harmless file. Reuse the same no-skill
StageRoute and hardened projection. Record:

runtime version
projection digest
permission proof
argv summary
timeout
process status
sanitized error class
workspace before/after digest

Do not persist raw stdout/stderr.

STEP B — H03

Run the existing unchanged H03 only if STEP A completes with:

no unresolved ASK
exit success
usable structured output
independent workspace safety check

If STEP A remains blocked, do not run H03.

============================================================
5. EVIDENCE CLASSIFICATION

============================================================

Maintain:

RUNTIME_CONTRACT_EVIDENCE
LIVE_LANE_BLOCKED
UNAVAILABLE
UNKNOWN

A successful smoke is compatibility evidence only. H03 is quality evidence
only after an independent verifier confirms the DecisionRecord and acceptance
criteria.

Do not label any result MODEL_EFFECT. Codex/OpenCode remains a
CONFIGURATION_EFFECT comparison at most, and only after a completed OpenCode
H03 cell.

============================================================
6. TESTS

============================================================

Keep all existing tests green. Add only focused regressions for any proven
diagnostic behavior:

- generic structured UnknownError remains sanitized;
- provider/model cause is not inferred without evidence;
- no raw local logs or credentials enter records;
- no-ASK projection remains unchanged;
- unknown cause remains UNKNOWN;
- a successful smoke gates H03;
- blocked smoke prevents H03;
- unknown cost/model-call/tool-call/token semantics remain null/UNKNOWN.

Run:

PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
git diff --check

============================================================
7. DOGFOOD AND REVIEW

============================================================

Use using-superpowers as resident task/session authority and the existing
Stage Router. Emit a StageRoute for every active stage. Do not load the full
catalog. Record any unrelated selection as ROUTING_DEFECT; do not fix router
weights here.

Use independent lanes for:

- runtime/source diagnosis;
- permission/security review;
- serialization/evidence review;
- simplification;
- verification.

Run the OCR auth precheck once. If it returns 401, record
OCR_NATIVE_DIFF = BLOCKED_BY_AUTH and do not retry.

============================================================
8. OUTPUT

============================================================

Append a concise record under:

fixtures/v3/model-routing/runs/phase3c/

Update, without overwriting prior evidence:

docs/v3/evidence/MODEL_RUNTIME_EVAL_V5.md

Record:

- exact hypothesis tested;
- sanitized observation;
- cause classification;
- whether a safe smoke completed;
- whether H03 was gated or run;
- permission/no-ASK proof;
- metrics and unknowns;
- security result;
- confounders.

============================================================
9. STOP DECISION

============================================================

Choose exactly one:

OPENCODE_RUNTIME_RECOVERED
  Smoke completes safely; H03 may be proposed as a later bounded cell.

OPENCODE_RUNTIME_BLOCKED
  Projection is valid but provider/runtime/lifecycle remains unavailable or
  generically unknown.

OPENCODE_CONTRACT_BLOCKED
  Least-privilege native behavior cannot be proven.

Do not start Phase 4 in any outcome.
