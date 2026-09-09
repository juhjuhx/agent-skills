# Stage Router Evaluation V2 — Enriched Catalog

Status: **Phase 3A.1 replay evidence**. This report re-runs the exact
Phase 3A ten-fixture suite after adding the offline routing metadata overlay.
The fixture file was not edited to improve the result.

## Method and inputs

| Item | Value |
|---|---|
| Baseline | [`STAGE_ROUTER_EVAL_V1.md`](STAGE_ROUTER_EVAL_V1.md) |
| Fixture file | [`routing-eval-v1.json`](../../../fixtures/v3/router/routing-eval-v1.json) |
| Fixture content | unchanged; SHA-256 `2fba30276affd2dc92fd0e46687924071c5d0841c424074abff5e83ccce2d264` |
| Registry | 214 records from `.superpowers/SKILLS_INDEX.json` |
| Overlay | [`skill-routing-metadata.json`](../../../registry/v3/skill-routing-metadata.json) |
| Overlay digest | `sha256:13896c8ded17a16129f2092b2e83d1bbe6465055867f3f948897e78d42a5dcc5` |
| Model routing | not implemented or evaluated |
| Body loading during ranking | 0 for every fixture |

Both runs use metadata-first routing. V2's context estimate is an offline
selected-body byte proxy carried by metadata; it is not a token-billing claim.
The overlay generator, unlike normal routing, inspected all 214 bodies once as
read-only maintenance input.

## Ten-fixture comparison

The selection strings include role assignments. `filtered` counts hard-filtered
records; `eligible` is the remaining executable candidate count before role
selection. A judgment of `HISTORICAL_BETTER` means the V1 route was less
redundant or more semantically precise for this fixture, not that V1's sparse
metadata is preferred globally.

| Fixture | V1 selected | V2 selected | V1 filtered / ctx B | V2 filtered / eligible / ctx B | Role pressure | Judgment |
|---|---|---|---|---|---:|---|
| A README typo | none (`NO_SKILL_NEEDED`) | none (`NO_SKILL_NEEDED`) | 213 / 0 | 194 / 19 / 0 | 0 | `EQUIVALENT` |
| B ordinary bug | `using-superpowers[GATE]`, `diagnose[PROCESS]`, `tdd[PROCESS]`, `verification-before-completion[VERIFY]` | same | 206 / 732 | 201 / 13 / 15,668 | 1 | `EQUIVALENT` — alternative relation is now explicit |
| C API architecture | `using-superpowers[GATE]`, `grill-with-docs[PROCESS]`, `improve-codebase-architecture[DOMAIN]`, `brooks-review[REVIEW]`, `verification-before-completion[VERIFY]` | same | 208 / 1,984 | 192 / 21 / 14,704 | 0 | `EQUIVALENT` — exact API donor remains a gap |
| D large frontend | `using-superpowers[GATE]`, `frontend-design[PROCESS]`, `image-to-code[DOMAIN]`, `fixing-accessibility[REVIEW]`, `baseline-ui[VERIFY]`, `verification-before-completion[VERIFY]` | `using-superpowers[GATE]`, `frontend-design[PROCESS]`, `image-to-code[DOMAIN]`, `baseline-ui[REVIEW]`, `code-review-excellence[REVIEW]`, `verification-before-completion[VERIFY]` | 207 / 1,316 | 173 / 40 / 56,568 | 1 | `HISTORICAL_BETTER` — V2 adds review redundancy and changes `baseline-ui`'s slot |
| E security change | `using-superpowers[GATE]`, `safe-mode[PROCESS]`, `permission-tuner[REVIEW]`, `verification-before-completion[VERIFY]` | same | 210 / 616 | 209 / 4 / 13,448 | 0 | `EQUIVALENT` — exact hardening donor remains a gap |
| F source research | `using-superpowers[GATE]`, `wiki-research-loop[PROCESS]`, `verification-before-completion[VERIFY]` | same | 208 / 912 | 187 / 26 / 9,632 | 0 | `EQUIVALENT` — wiki procedure is a proxy, not source-driven donor |
| G visual design | `using-superpowers[GATE]`, `baoyu-slide-deck[PROCESS]`, `design-taste-frontend[DOMAIN]` | same | 205 / 448 | 165 / 48 / 108,128 | 0 | `EQUIVALENT` — high selected-body cost needs curation |
| H repository audit | `using-superpowers[GATE]`, `codebase-inspection[PROCESS]`, `logic-review[REVIEW]`, `verification-before-completion[VERIFY]` | `using-superpowers[GATE]`, `codebase-inspection[PROCESS]`, `brooks-debt[REVIEW]`, `code-review-excellence[REVIEW]`, `verification-before-completion[VERIFY]` | 192 / 644 | 167 / 46 / 18,424 | 1 | `HISTORICAL_BETTER` — V2 adds two review signals without enough evidence |
| I product specification | `using-superpowers[GATE]`, `brainstorming[PROCESS]`, `grill-with-docs[PROCESS]`, `to-prd[DOMAIN]` | same | 206 / 812 | 204 / 9 / 17,408 | 1 | `EQUIVALENT` — no premature implementation activation |
| J release gate | `using-superpowers[GATE]`, `finishing-a-development-branch[PROCESS]`, `brooks-test[REVIEW]`, `logic-review[REVIEW]`, `verification-before-completion[VERIFY]` | `using-superpowers[GATE]`, `finishing-a-development-branch[PROCESS]`, `brooks-test[REVIEW]`, `code-review-excellence[REVIEW]`, `logic-review[REVIEW]`, `verification-before-completion[VERIFY]` | 202 / 1,988 | 168 / 45 / 35,276 | 2 | `HISTORICAL_BETTER` — V2 adds a third review pressure point |

V2 preserves the important safety outcomes: A remains no-skill, MCP does not
activate without MCP relevance, frontend/security/research routes remain
conditional, and every route has a role/evidence explanation. The overlay
increases candidate eligibility as intended, but it also exposes that broad
inferred metadata can create redundant review selections.

## Per-fixture route metrics

| Fixture | Status | Selected | Role coverage | Filtered | Eligible | Context estimate (B) | Body files |
|---|---|---:|---|---:|---:|---:|---:|
| A | `NO_SKILL_NEEDED` | 0 | — | 194 | 19 | 0 | 0 |
| B | `SKILLS_SELECTED` | 4 | GATE, PROCESS, VERIFY | 201 | 13 | 15,668 | 0 |
| C | `SKILLS_SELECTED` | 5 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 192 | 21 | 14,704 | 0 |
| D | `SKILLS_SELECTED` | 6 | GATE, PROCESS, DOMAIN, REVIEW, VERIFY | 173 | 40 | 56,568 | 0 |
| E | `SKILLS_SELECTED` | 4 | GATE, PROCESS, REVIEW, VERIFY | 209 | 4 | 13,448 | 0 |
| F | `SKILLS_SELECTED` | 3 | GATE, PROCESS, VERIFY | 187 | 26 | 9,632 | 0 |
| G | `SKILLS_SELECTED` | 3 | GATE, PROCESS, DOMAIN | 165 | 48 | 108,128 | 0 |
| H | `SKILLS_SELECTED` | 5 | GATE, PROCESS, REVIEW, VERIFY | 167 | 46 | 18,424 | 0 |
| I | `SKILLS_SELECTED` | 4 | GATE, PROCESS, DOMAIN | 204 | 9 | 17,408 | 0 |
| J | `SKILLS_SELECTED` | 6 | GATE, PROCESS, REVIEW, VERIFY | 168 | 45 | 35,276 | 0 |

`using-superpowers` is a resident gate reference rather than a repeated body
load. The route's `body_files_loaded` value is therefore zero even when a
downstream Codex execution would later load selected procedures.

## Evaluation questions

| Question | V2 observation | Verdict |
|---|---|---|
| Does research prefer evidence-oriented procedures? | F selects `wiki-research-loop` and verification, not coding skills; no exact `source-driven-development` registry record exists. | Partial success; registry gap remains |
| Does API architecture surface API/interface discipline? | C surfaces architecture/decision proxies, but not a full API/interface donor. | Partial success; do not relabel proxies |
| Does security hardening surface security expertise conditionally? | E selects `safe-mode` and `permission-tuner`; non-security fixtures do not select them. | Conditional success; exact donor gap remains |
| Does frontend routing cover domain and verification? | D covers frontend/domain/review/verify, but review roles are redundant. | Relevant but needs Tier-1 curation |
| Does product specification avoid premature implementation? | I selects brainstorming, decision support, and PRD procedures; no TDD/frontend/execute route. | Good |
| Does release routing cover tests/review/verification? | J covers all required role classes but has too much review pressure and no exact security-hardening skill. | Coverage good; redundancy issue |

These are semantic evaluation judgments, not exact-ID acceptance rules.

## Historical dogfood replay

The existing comparison fixture is
[`historical-dogfood-v1.json`](../../../fixtures/v3/router/historical-dogfood-v1.json).
Its manual routes are observations, not ground truth. Exact donor names used in
the earlier traces (`addyosmani-source-driven-development`,
`addyosmani-api-and-interface-design`, `addyosmani-security-and-hardening`, and
the installed Deep Understanding workflow) are outside the current registry.

| Historical phase | Comparison | Classification | Reason |
|---|---|---|---|
| Phase 1 | Enriched machine route covers the same process/review/verification intent but uses current IDs/proxies where exact donor IDs are unavailable. | `AMBIGUOUS` | manual intent was richer than registry evidence; no truth label is safe |
| Phase 2 | Enriched routes preserve Codex-focused inspection, implementation, review, verification, and MCP boundaries. | `EQUIVALENT` / `AMBIGUOUS` | current IDs are comparable, but manual adapter intent is not a route oracle |
| Phase 2.5 | Enriched route keeps source-driven/security names as gaps and uses conservative current proxies. | `AMBIGUOUS` | donor provenance differs from registry provenance |
| Phase 2.6 | Enriched route preserves source/provenance review intent without promoting an unavailable exact donor. | `AMBIGUOUS` | no exact source-driven record in the 214 registry |
| Phase 3A | V2 is the same unchanged ten-fixture workload with explicit metadata provenance and richer candidate evidence. | `EQUIVALENT` / `ROUTER_BETTER` | deterministic route evidence is improved; D/H/J show regressions honestly |

The replay therefore informs curation but does not tune production weights to
match every historical manual selection.

## Over-routing findings

- D, H, and J demonstrate duplicate review pressure: V2 selected multiple
  review procedures after enrichment. This is the principal V2 regression.
- The current role inference is broad enough to assign `baseline-ui` to
  `REVIEW` for D and `code-review-excellence` to additional review stages.
- Output inference is present in 208/214 records. That improves artifact
  matching but is too broad to be treated as author-declared output truth.
- G's selected-body byte estimate is 108,128 B. The router did not load these
  bodies, but a downstream execution should ask whether all three are needed.

## Under-routing and metadata gaps

- The exact source-driven, Deep Understanding, security-hardening, and
  API/interface-design donors are registry gaps. Current proxies are explicitly
  not aliases.
- No agent compatibility or permission field is declared by the overlay.
  This is safer than inventing runtime or authority semantics, but it limits
  capability-aware filtering.
- The graph has only nine high-confidence edges. Sparse relationships are
  preferable to fabricated density, but more reviewable edges are needed.
- Deep Understanding remains an escalation capability with status
  `UNAVAILABLE` in the 214-record route catalog; it is not a normal candidate.

## Context and latency evidence

| Measurement | Result |
|---|---:|
| Offline canonical body bytes inspected | 2,155,285 B / 214 files |
| Overlay serialized size | 848,086 B |
| Overlay load/validation, latest observed cold run | 1,336.8 ms (first cold observation 3,135.7 ms) |
| Ten-route warm median range | 1,195.97–1,298.14 ms |
| Ten-route median mean | 1,244.79 ms |
| Metadata records inspected per route | 214 |
| `SKILL.md` files loaded during normal route | 0 |

Selected-body byte proxies for B–J were 15,668, 14,704, 56,568, 13,448,
9,632, 108,128, 18,424, 17,408, and 35,276 respectively. This is an
estimated downstream context size derived from canonical byte counts; it is
not a claim of token savings or model billing. The overlay adds measurable
load/validation overhead, but remains in the same broad interactive order of
magnitude as the existing MVP and introduces no runtime optimization
architecture.

## Conclusion

V2 proves that a single metadata overlay makes more of the catalog executable
by the Stage Router while preserving selected-only body loading and the V1
safety boundaries. It does not yet prove high-quality routing for every skill.
The next work is human/candidate curation and evaluation of review-role
redundancy, exact registry gaps, and context cost. Historical experience may
generate `MetadataProposal` records, but it must not silently rewrite routing
policy.

## Independent review lanes

These conclusions were made independently and are based on the changed source,
the checked-in overlay, and executable validation results:

| Lane | Result | Evidence / finding |
|---|---|---|
| Architecture/API | PASS with curation follow-up | overlay is additive; canonical bodies and v1 registry remain authoritative; no model routing or adapter branching was added |
| Code review | PASS with known V2 route regressions | deterministic route evidence is present; D/H/J expose review-role redundancy rather than hiding it |
| Security/hardening | PASS | body extraction is read-only/no-execution; inferred metadata cannot declare permissions; quarantine/deprecation remain non-executable |
| Simplification | PASS | no metadata manager, catalog service, graph database, vector store, worker system, or orchestration framework was added |
| Verification | PASS | full suite, overlay schema, overlay digest, and optional canonical body freshness validation are green |
| Alibaba OpenCodeReview | `OCR_NATIVE_DIFF = BLOCKED_BY_AUTH` | `ocr v1.11.6`; one `ocr llm test` returned HTTP 401; no native review result is claimed |

No new dependency or MCP server was installed. The only implementation
follow-up required by review is metadata curation: reduce broad output
inference and review-role duplication, then re-run the same fixture suite.
