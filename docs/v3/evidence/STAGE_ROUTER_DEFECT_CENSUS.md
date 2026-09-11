# Stage Router Defect Census

Status: Phase 3H precision/regression evidence. This census records only
defects already observed in repository evidence; it is not a prediction over
the remaining catalog.

## Scope and repo truth

| Item | Value |
|---|---|
| Branch | `fix/v3-stage-router-defect-closure` |
| Starting HEAD | `188269a70830a10c2cc360b01b57f291de0b6aa9` |
| Canonical catalog | `.superpowers/SKILLS_INDEX.json` (214 skills) |
| Compiled routing view | `registry/v3/skill-routing-metadata.json` |
| Census fixture | [`stage-router-defect-census-v1.json`](../../../fixtures/v3/routing/stage-router-defect-census-v1.json) |
| Evidence boundary | Phase 3C through Phase 3H dogfood records |

The machine-readable census contains 26 counted occurrences: 18 carried
forward from earlier dogfood records and 8 recorded during the Phase 3H
before-state replay. A score or relationship influence is `null`/`NONE_RECORDED`
when the source evidence did not expose it. Missing historical fields were not
reconstructed from the current router.

## Family census

| Family | Occurrences | Classification | Disposition |
|---|---:|---|---|
| `brandkit` | 5 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH; ROLE_FALSE_POSITIVE | FIXED_METADATA |
| `writing-skills` | 3 | PROCESS_FALSE_POSITIVE; ROLE_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `understand-chat` | 2 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH; METADATA_AMBIGUITY | FIXED_METADATA |
| `llm-council` | 2 | ROLE_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH; METADATA_AMBIGUITY | FIXED_METADATA |
| `maps` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `permission-tuner` | 1 | DOMAIN_FALSE_POSITIVE; ROLE_FALSE_POSITIVE; MISSING_NEGATIVE_SIGNAL | FIXED_METADATA |
| `cost-tracker` | 1 | ROLE_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `wiki-viewer` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `understand` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `brooks-harness` | 1 | DOMAIN_FALSE_POSITIVE; TASK_MODE_MISMATCH | FIXED_METADATA |
| `understand-dashboard` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `understand-domain` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `MCP Integration` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `survey-generator` | 1 | PROCESS_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `understand-diff` | 1 | DOMAIN_FALSE_POSITIVE; STAGE_MISMATCH; MISSING_NEGATIVE_SIGNAL | FIXED_METADATA |
| `invariant-guard` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `redesign-existing-projects` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FIXED_METADATA |
| `mathguard` | 1 | DOMAIN_FALSE_POSITIVE; GENERIC_TRIGGER_OVERREACH | FALSE_POSITIVE_CONFIRMED_BUT_DEFERRED |
| **Total** | **26** |  | **17 fixed; 1 explicitly deferred** |

## Root-cause findings

The recorded evidence supports the following order of causes:

1. Broad generated/curated stage, domain, and role metadata made a semantic
   family look eligible from generic words such as “understand”, “research”,
   “review”, “design”, or “evidence”.
2. Several skills had no explicit activation boundary. Their procedures are
   useful, but only for a narrower domain or task mode.
3. `permission-tuner` additionally needed negative evidence for generic code
   review/release/source work.
4. The recorded occurrences contain no relationship-driven root cause. The
   graph remains intact; compatibility is rechecked after expansion.
5. Global scoring weights were not changed. The correction is a small
   curated semantic patch plus a provenance-gated `required_triggers` filter.

## Semantic boundaries applied

The curated layer uses small digest-bound patches; it does not copy procedure
bodies and it cannot grant authority.

| Skill family | Activation boundary |
|---|---|
| `brandkit` | Explicit branding, visual identity, logo, brand assets, guidelines, or brand-system intent. |
| `maps` | Geospatial/location work such as geocoding, points of interest, directions, OpenStreetMap, or coordinates. |
| `permission-tuner` | Permission, authorization, sandbox/access boundary, least privilege, or permission-prompt work; generic review is excluded. |
| `writing-skills` | Skill authoring, editing, testing, verification, deployment, or equivalent skill-lifecycle work. |
| `cost-tracker` | Cost, budget, quota, billing, token spend, or usage accounting. |
| `llm-council` | Multi-model/multi-LLM perspectives, consensus, deliberation, or ensemble review. |
| `wiki-viewer` | Wiki/knowledge-base browsing, page-link graph, seed queue, or wiki handoff. |
| `understand-chat` | Codebase questions, codebase tour/architecture, knowledge graph, or module dependencies. |
| `understand` | Codebase architecture/dependency mapping or explicit knowledge-graph analysis. |
| `understand-dashboard` | Interactive knowledge-graph/dashboard visualization. |
| `understand-domain` | Business-domain/process-flow/domain-graph analysis. |
| `MCP Integration` | MCP/Model Context Protocol server or integration work. |
| `survey-generator` | Literature survey, literature review, bibliography, or explicit deep dive. |
| `understand-diff` | Git diff, pull request, changed files, affected components, or change-impact analysis. |
| `invariant-guard` | Algorithm correctness, loop invariants, postconditions, termination, recursion base cases, or edge-case correctness. |
| `redesign-existing-projects` | Existing-site/UI redesign or visual-pattern upgrade. |
| `brooks-harness` | Brooks-lint/plugin/harness maintenance, not generic verification. |

The semantic activation list is an OR boundary: at least one explicit
required signal must occur in the TaskSpec/stage request. It is not a
permission, trust, or dependency mechanism. Mandatory dependencies remain
mandatory and can still be added through the existing graph contract.

## Relationship audit

`relationship_audit.recorded_defect_occurrences_with_relationship_cause` is
zero. No `RECOMMENDS`, `COMPLEMENTS`, `REVIEW_WITH`, or `VERIFY_WITH` edge was
removed. Optional candidates still pass semantic compatibility after graph
expansion, and `ALTERNATIVE_TO` remains a deduplication signal rather than a
global deletion rule.

## Evidence and limits

- The exact occurrence-level details, including body/procedure state, live in
  the [machine-readable census](../../../fixtures/v3/routing/stage-router-defect-census-v1.json).
- Historical score components are intentionally unknown where the old report
  did not record them.
- `mathguard` is a confirmed one-off false positive from the Phase 3H
  research replay. Its body was not loaded or executed, it has not repeated,
  and it remains an explicit production-readiness backlog item rather than a
  fixture-specific exclusion.
- `orchestrate` and `session-handoff` in the final dogfood route are not
  defects: the task is explicitly multi-stage orchestration and handoff work.
