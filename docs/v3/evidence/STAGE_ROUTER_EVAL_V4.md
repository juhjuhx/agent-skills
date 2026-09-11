# Stage Router Evaluation v4

Status: Phase 3H defect-closure and production-readiness gate. The router
remains metadata-first; no runtime adapter, model/effort policy, or global
Stage Router weight was changed.

## Repo truth and method

| Item | Value |
|---|---|
| Branch | `fix/v3-stage-router-defect-closure` |
| Starting HEAD | `188269a70830a10c2cc360b01b57f291de0b6aa9` |
| Catalog | `.superpowers/SKILLS_INDEX.json`, 214 records |
| Snapshot | `snapshot:87dc6a8790b10450` |
| Compiled overlay digest | `sha256:be8eec30841c3ff8beddc13549f14ca3b77737aa39059191ab99d63bf2c8c1b2` |
| Semantic holdout | [`stage-router-semantic-holdout-v1.json`](../../../fixtures/v3/routing/stage-router-semantic-holdout-v1.json) |
| Defect census | [`stage-router-defect-census-v1.json`](../../../fixtures/v3/routing/stage-router-defect-census-v1.json) |
| Normal ranking body reads | 0 |

The unchanged A–J workloads are development/regression evidence. The eight
new holdout tasks are semantic near-miss pairs and were not used to tune
weights. Evaluation is rubric-based, not an exact expected-ID comparison.

## Semantic rubric

| Axis | Question |
|---|---|
| Relevance | Does each selected procedure match the requested semantics? |
| Required capability coverage | Are requested process/domain/review/verify capabilities present? |
| Role coverage | Is the selected complement sufficient without quota inflation? |
| Redundancy | Is same-role selection independently justified? |
| False positives | Did a specialized family activate without its semantic trigger? |
| Unnecessary context | Did the route add material context without marginal benefit? |
| Safety | Are trust, capability, permission, and body-load invariants intact? |
| Review/verify coverage | Are requested review and verification lanes retained? |
| NO_SKILL_NEEDED | Does a trivial/unrelated task stay empty? |

## A–J regression: base vs after closure

The “before” column is a fresh replay at the Phase 3H base snapshot. The
“after” column is the same TaskSpec/stage input on the closure snapshot.

| Fixture | Before selected | After selected | Result |
|---|---|---|---|
| A README typo | `NO_SKILL_NEEDED` | `NO_SKILL_NEEDED` | EQUIVALENT; required minimality preserved |
| B ordinary bug | `using-superpowers`, `diagnose`, `tdd`, `verification-before-completion` | same | EQUIVALENT |
| C API architecture | `using-superpowers`, `grill-with-docs`, `improve-codebase-architecture`, `brooks-review`, `verification-before-completion` | same | EQUIVALENT; exact API donor gap remains explicit |
| D large frontend | `using-superpowers`, `frontend-design`, `image-to-code`, `fixing-accessibility`, `verification-before-completion` | same | EQUIVALENT; no review regression |
| E security change | `using-superpowers`, `safe-mode`, `permission-tuner`, `verification-before-completion` | same | EQUIVALENT; permission-tuner remains available for true need |
| F deep source research | `using-superpowers`, `wiki-research-loop`, `verification-before-completion` | same | EQUIVALENT; source-driven donor gap remains explicit |
| G visual design | `using-superpowers`, `baoyu-slide-deck`, `design-taste-frontend` | same | EQUIVALENT; high context proxy remains visible |
| H repository audit | `using-superpowers`, `codebase-inspection`, `logic-review`, `verification-before-completion` | same | EQUIVALENT; unrelated reviewers do not reappear |
| I product specification | `using-superpowers`, `grill-with-docs`, `to-prd` | same | EQUIVALENT |
| J release gate | `using-superpowers`, `release`, `brooks-test`, `logic-review`, `verification-before-completion` | same | EQUIVALENT; release/review/verify coverage retained |

No material A–J regression was observed. The README typo remains the required
empty route. Role saturation was retained; no global `max_review=1` or
`max_verify=1` cap was introduced.

## New semantic holdout

| Task | Target family | Semantic expectation | After route observation |
|---|---|---|---|
| Brand style guide | `brandkit` | RELEVANT | selected; branding/visual identity signals present |
| API design-system near miss | `brandkit` | IRRELEVANT | absent; “design system” alone is insufficient |
| Skill-authoring verification | `writing-skills` | RELEVANT | selected; skill-lifecycle signals present |
| Release-verification near miss | `writing-skills` | IRRELEVANT | absent; generic verification is insufficient |
| Permission/sandbox audit | `permission-tuner` | RELEVANT | selected; access-boundary signals present |
| Generic code review near miss | `permission-tuner` | IRRELEVANT | absent; generic review is insufficient |
| Multi-model deliberation | `llm-council` | RELEVANT | selected; multi-model/deliberation signals present |
| Ordinary implementation planning near miss | `llm-council` | IRRELEVANT | absent; planning alone is insufficient and route is `NO_SKILL_NEEDED` |

All eight tasks inspected 214 metadata records and loaded zero skill bodies
during ranking. The holdout contains no exact expected skill list.

## Defect delta and dispositions

The seven Phase 3H fixed-target families were absent in the final replay. The
eighth Phase 3H observation, `mathguard`, is intentionally reported as a
separate one-off backlog:

| Measure | Before | After | Interpretation |
|---|---:|---:|---|
| Phase 3H fixed-target-family false positives | 7 | 0 | Fixed by curated semantic boundaries |
| One-off unrelated selection | 0 | 1 (`mathguard`) | Confirmed but deferred; no body loaded/executed |
| Repeated defect families | 17 | 0 active repeated families | All have explicit `FIXED_METADATA` disposition |
| Relationship-rooted defects | 0 | 0 | No graph deletion justified |

The broader machine census contains 26 recorded occurrences and preserves
the full occurrence-level evidence in the [defect census](../../../fixtures/v3/routing/stage-router-defect-census-v1.json).
`mathguard` is not silently ignored: it is the only confirmed, non-repeated
backlog item and requires a future general mathematical/quantitative semantic
boundary if it recurs.

## Context cost

| Measure | Before closure | After closure | Delta |
|---|---:|---:|---:|
| Compiled metadata bytes | 754,619 | 762,895 | +8,276 (+1.10%) |
| A–J selected context proxy | unchanged per fixture | unchanged per fixture | 0 |
| Phase 3H dogfood selected context proxy | 170,540 B | 79,128 B | −91,412 B (−53.6%) |
| Normal-route body files | 0 | 0 | 0 |

The dogfood context decrease comes from removing broad specialized selections;
it is not a reason to suppress valid domain skills. The true brand,
permission, council, skill-authoring, diff, and invariant holdout cases still
activate their relevant family.

## Performance and snapshot reuse

The comparison used one immutable snapshot for the full A–J replay and 50
warm-route samples (five per fixture).

| Measurement | Before closure | After closure |
|---|---:|---:|
| Cold snapshot load | 494.717 ms | 472.542 ms |
| JSON parse | 8.009 ms | 7.852 ms |
| Schema/digest validation | 468.363 ms | 446.413 ms |
| Graph construction | 0.052 ms | 0.051 ms |
| Warm route median | 11.447 ms | 11.171 ms |
| Warm route min/max | 8.618 / 15.478 ms | 8.999 / 15.582 ms |
| Warm samples | 50 | 50 |

The cold validation pass remains the measurable bottleneck, while stage routes
reuse the snapshot. Warm routing remains in the same order of magnitude and
does not regress toward the Phase 3A.1 multi-second pattern.

## Remaining weak routes

- `G` is semantically stable but still has a large visual context proxy
  (108,128 B); cost/output curation is a future bounded improvement.
- Exact source-driven development, Deep Understanding, security-hardening,
  and API/interface-design donors remain registry gaps/proxy limitations.
- `mathguard` is one unexecuted, non-repeated false positive and remains a
  documented backlog item. No fixture-specific suppression was added.

## Acceptance gate

| Gate | Result |
|---|---|
| Repeated false-positive families have explicit dispositions | PASS |
| Positive near-miss counterparts preserved | PASS; 8/8 semantic holdout cases |
| A–J material regression | PASS; 0 |
| `NO_SKILL_NEEDED` behavior | PASS; A and holdout near miss remain empty where appropriate |
| Metadata-first / zero body reads | PASS |
| Deterministic output | PASS |
| Safety/trust boundaries | PASS; no authority fields added |
| Warm routing performance | PASS; 11.171 ms median, same order of magnitude |

**STAGE_ROUTER_PRODUCTION_READY** for the skill-routing layer. This does not
start Phase 4 and does not change the independent
`CODEX_LIVE_TRANSPORT_BLOCKED` status.

## Independent review and OCR

| Review lane | Result |
|---|---|
| Semantic routing correctness | PASS; recorded target families have explicit semantic boundaries; `mathguard` is visibly deferred |
| Required-skill/regression preservation | PASS; A–J unchanged and positive holdout counterparts remain relevant |
| Security/trust/permission behavior | PASS; no authority fields or runtime permissions were added |
| Performance/context | PASS; snapshot reuse and warm-route measurements remain in the prior order of magnitude |
| Simplification/anti-overfitting | PASS; no fixture-ID branch, global weight edit, manager, database, or runtime adapter |
| Verification | PASS; 278/278 repository tests, schema/digest validation, JSON validation, and diff check |
| OpenCodeReview native diff | `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH` |

The single OCR precheck returned HTTP `401 Unauthorized` with sanitized error
`invalid x-api-key`. No native OCR review is claimed; the deterministic review
lanes above remain separate evidence.
