# Phase 3C.1 Dogfood Route

This is the first live-evidence run routed through the repository's existing
v3 Stage Router. It is an operational trace, not a record of hidden model
reasoning.

## Task

- **TASK:** measurement integrity plus targeted live evidence for the Codex,
  Claude Code, and OpenCode lanes
- **START_HEAD:** `cbb81593cf85fa8e013371880ab17b29eef7971c`
- **TASKSPEC:** `T-phase3c1-live-evidence`
- **Task mode:** bounded benchmark / evidence maintenance
- **Risk:** medium; no production deployment, credentials, installer, or
  routing-policy changes
- **Catalog snapshot:** `snapshot:2349a6fe70aaf346`
- **Metadata records inspected:** 214
- **Normal-route SKILL.md bodies loaded:** 0
- **DEEP_UNDERSTANDING:** `NOT_USED` — the phase is explicitly bounded,
  existing contracts are fixed, and the remaining uncertainty is measured by
  safe runtime probes rather than an architecture redesign.

`using-superpowers` is the resident task/session authority. Each route below
references it as the `GATE` authority; its full instructions were not reloaded
as a fresh ordinary candidate at every stage.

## Stage routes

| Stage | Route | Status | Selected role slots | Why selected | Rejected / not executed | Result |
|---|---|---|---|---|---|---|
| UNDERSTAND | `route:T-phase3c1-live-evidence:understand:d0027ad18b926a5b` | `NO_SKILL_NEEDED` | — | The bounded phase, fixed contracts, and safety scope were already explicit; no additional procedure was needed to classify the work. | Deep Understanding was not invoked: this was a constrained evidence correction, not an architecture-changing task. | Route emitted; source truth and safety scope established. |
| RESEARCH | `route:T-phase3c1-live-evidence:research:cce73a73070c2dd1` | `SKILLS_SELECTED` | GATE `using-superpowers`; PROCESS `knowledge-consolidation`; DOMAIN `mcp-audit`; VERIFY `verification-before-completion` | Inspect first-party Codex JSONL semantics, installed CLI help, and secondary-lane controls. | Other research candidates were rejected by stage fit; only selected bodies were loaded and no embedded command, URL, or script was executed. | Codex release semantics and lane contracts recorded. |
| DESIGN | `route:T-phase3c1-live-evidence:design:b6f6f74dd95bce5a` | `SKILLS_SELECTED` | GATE `using-superpowers`; PROCESS `brooks-harness`; DOMAIN `improve-codebase-architecture`; VERIFY `verification-before-completion` | Design explicit metric provenance, blocked-lane records, and the small evidence gate. | No telemetry framework, database, adaptive router, or new adapter hierarchy. | Data boundary remained digest/metadata-only. |
| PLAN | `route:T-phase3c1-live-evidence:plan:b5a0d995804cbe7b` | `SKILLS_SELECTED` | GATE `using-superpowers`; DOMAIN `teams-meeting-pipeline` | Sequence measurement fix, Codex replicates, secondary probes, review, and evidence publication. | `teams-meeting-pipeline` was a semantically unrelated router result; its body was read for audit only and no meeting workflow was executed. No model preference, effort experiment, or Phase 4 work. | Bounded sequence followed; router quality issue retained as evidence. |
| IMPLEMENT | `route:T-phase3c1-live-evidence:implement:37f456eb61e57ef0` | `SKILLS_SELECTED` | GATE `using-superpowers`; PROCESS `executing-plans`, `test-driven-development`; REVIEW `official-code-review`; VERIFY `verification-before-completion` | Implement metric semantics, smoke classification, read-only eligibility, and focused tests. | No changes to Stage Router weights, install.sh, runtime adapters, or production registry. | Tests and record builder updated; no raw output persisted. |
| REVIEW | `route:T-phase3c1-live-evidence:review:af32605fd6bbef09` | `SKILLS_SELECTED` | GATE `using-superpowers`; DOMAIN `improve-codebase-architecture`; REVIEW `logic-diff`; VERIFY `verification-before-completion` | Inspect changed boundaries, record schema, and prohibited-scope files. | No first-review conclusion was supplied to the independent security/simplification passes. | Review lanes remained independent. |
| VERIFY | `route:T-phase3c1-live-evidence:verify:c652300bd9d6dcc9` | `SKILLS_SELECTED` | GATE `using-superpowers`; REVIEW `brooks-test`; VERIFY `verification-before-completion` | Run schema validation, full unit tests, fixture validation, and diff checks. | No success was inferred from runtime self-report; tests and isolated workspace state were authoritative. | Verification evidence collected. |
| HARDEN | `route:T-phase3c1-live-evidence:harden:05f8c78fb14c326d` | `SKILLS_SELECTED` | GATE `using-superpowers`; PROCESS `safe-mode`; VERIFY `verification-before-completion` | Check credential nonserialization, fail-closed lane handling, and metric ambiguity. | `brandkit` was an irrelevant metadata selection; its body was read for route audit only. No permission widening, retry loop, or unsafe `--auto` invocation. | Blockers retained explicitly. |
| HANDOFF | `route:T-phase3c1-live-evidence:handoff:4f8549a39c9baaeb` | `SKILLS_SELECTED` | GATE `using-superpowers`; PROCESS `finishing-a-development-branch`; REVIEW `brooks-harness`, `brooks-review`; VERIFY `verification-before-completion` | Produce append-only evidence, next prompt, and PR handoff. | No external posting or release action; the route did not execute unrelated publication skills. | Evidence and next-phase proposal prepared locally only. |

The route IDs above are the exact deterministic IDs emitted by the rerun of the
current catalog snapshot. `using-superpowers` is resident authority, not a
full instruction body to reload as an ordinary candidate at every stage.

## Stage operational contract

- **Inputs:** v3 TaskSpec, current StageRoute outputs, installed CLI help,
  first-party source snapshots, historical live records, and isolated fixture
  repositories.
- **Tools:** local `git`, Python unittest, schema validator, Codex CLI,
  Claude/OpenCode help and bounded probes, and one OCR precheck.
- **Outputs:** metric-provenance code, append-only sanitized records, evidence
  report, tests, and a Phase 3C.2 proposal.
- **Evidence gate:** every runtime result is classified as
  `REAL_EXECUTION`, `UNAVAILABLE`, or blocked; no mock or self-reported result
  is used as quality evidence.
- **No-skill behavior:** the route system was allowed to select no additional
  skill when no stage evidence justified one; no quota was imposed.
