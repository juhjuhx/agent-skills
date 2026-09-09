# Catalog Routing Metadata Census

Status: **Phase 3A.1 implementation evidence**. This is a maintenance-time
census and an enrichment proposal, not a production registry migration.

## Source truth

| Item | Observed value |
|---|---|
| Start head | `f81e81a2c98529c8866c9298f97a70d50e619e98` |
| Implementation branch | `feat/v3-routing-metadata` |
| Canonical registry | `.superpowers/SKILLS_INDEX.json` |
| Registry source/ref | `juhjuhx/agent-skills.git` / `main` |
| Registry source commit | `db3b67d5b051c4223da9146b2b836a9ed45e9bac` |
| Indexed skills | 214 unique records |
| Canonical bodies | 214 existing `SKILL.md` files |
| Body bytes inspected offline | 2,155,285 |
| Overlay | [`registry/v3/skill-routing-metadata.json`](../../../registry/v3/skill-routing-metadata.json) |
| Overlay version / digest | `v3-routing-metadata-1` / `sha256:13896c8ded17a16129f2092b2e83d1bbe6465055867f3f948897e78d42a5dcc5` |
| Generator | [`tools/v3/metadata_enrichment.py`](../../../tools/v3/metadata_enrichment.py), version `0.1.0` |
| Body policy | read-only data extraction; no command, script, URL, MCP, or dependency execution |

The registry is the identity and source-digest authority. The overlay is one
keyed routing metadata layer, not a second procedure library. `SKILL.md`
remains the canonical procedure source. The overlay is regenerated only by an
explicit maintenance command; normal router catalog loading does not read
skill bodies.

## Field census

The first column is the current v1-compatible projection before enrichment.
The second is the number of records with a non-empty value in the overlay.
`source` and `trust` are intentionally zero in the overlay because they are
inherited from the current registry projection; the overlay records each
canonical body digest and its provenance separately.

| Field | Current registry | Overlay | Notes |
|---|---:|---:|---|
| `roles` | 0 | 214 | 65 curated seeds; remainder high-confidence identity/category inference |
| `stages` | 0 | 198 | 65 curated; 16 remain unknown/ambiguous |
| `task_modes` | 0 | 190 | 64 curated; remaining values inferred |
| `domains` | 0 | 214 | category and identity mapping; not agent identity |
| `triggers` | 58 | 61 | existing registry values remain author-declared |
| `inputs` | 0 | 13 | conservative `argument-hint` signal only |
| `outputs` | 0 | 208 | 42 curated, 166 inferred; over-generation is a known gap |
| `required_capabilities` | 0 | 6 | only explicit MCP/browser identity signals |
| `tools` | 0 | 15 | frontmatter `allowed-tools` / prerequisite command signal |
| `permissions` | 0 | 0 | deliberately unknown; never inferred from procedure prose |
| `context_cost` | 0 | 214 | byte-derived estimate, not measured token billing |
| `runtime_cost` | 0 | 214 | conservative tool/body-size estimate |
| `relationships` | 0 | 8 records / 9 edges | sparse curated graph only |
| `agent_compatibility` | 0 | 0 | no runtime claims invented |
| `trust` | 214 | 0 | inherited from the registry (`CORE_TRUSTED` projection) |
| `source` | 214 | 0 | inherited source identity; overlay has `source_skill_digest` |
| `source.license` | unavailable | 39 | author-declared frontmatter only |
| `version` | unavailable | 64 | author-declared frontmatter only |
| `risk` | 0 | 214 | conservative routing signal, not an authority grant |
| `eval_status` | 0 | 214 | baseline is `planned`/`unmeasured`; no success claim |
| `extensions.routing` | 0 | 214 | overlay version, triggers, body policy, and provenance references |

Body frontmatter equivalent signals were sparse: `license` 39, `version` 64,
`allowed-tools` 5, `prerequisites` 11, and effective tool declarations 15.
This confirms that filling every v3 field would be fabricated metadata; the
overlay leaves unavailable permissions, agent compatibility, and provenance
unknown instead.

## Quality classification

Classification is measured per record from curated routing seeds, conservative
identity/category signals, deprecation markers, and field completeness. It is
not a claim that all `ROUTING_READY` fields are author-declared.

| Classification | Count | Share |
|---|---:|---:|
| `ROUTING_READY` | 65 | 30.4% |
| `PARTIAL` | 131 | 61.2% |
| `LEGACY_MINIMAL` | 0 | 0.0% |
| `AMBIGUOUS` | 16 | 7.5% |
| `DEPRECATED` | 2 | 0.9% |
| **Total** | **214** | **100.0%** |

Deprecated records are `baoyu-image-gen` and `baoyu-xhs-images`. Ambiguous
records are `Hook Development`, `MCP Integration`, `baoyu-post-to-wechat`,
`baoyu-post-to-x`, `brooks-harness`, `comfyui`, `invariant-guard`, `lemmaly`,
`llm-council`, `logic-explain`, `redesign-existing-projects`, `runaway-guard`,
`setup-matt-pocock-skills`, `survey-generator`, `understand-dashboard`, and
`wiki-viewer`. No record was called `LEGACY_MINIMAL` by this census; the
absence is reported rather than converted into a success claim.

## Quality tiers

Tiers are maintenance prioritization, not routing quotas.

| Tier | Count | Routing-ready | Purpose |
|---|---:|---:|---|
| `TIER_1_CORE` | 55 | 55 | foundational process, review, verification, orchestration |
| `TIER_2_DOMAIN` | 120 | 10 | domain procedures with broad reuse |
| `TIER_3_SPECIALIZED` | 37 | 0 | specialized or rare procedures |
| `TIER_4_DEPRECATED` | 2 | 0 | retained for provenance; not executable |

Tier-1 routing-ready coverage is **55/55 (100.0%)** under the current
compatibility/enrichment definition. The actual Tier-1 IDs are:

`baoyu-url-to-markdown`, `baseline-ui`, `brainstorming`, `brooks-audit`,
`brooks-debt`, `brooks-health`, `brooks-review`, `brooks-sweep`, `brooks-test`,
`code-review-excellence`, `codebase-inspection`, `debugging-code`, `diagnose`,
`executing-plans`, `finishing-a-development-branch`, `fixing-accessibility`,
`frontend-design`, `full-output-enforcement`, `grill-me`, `grill-with-docs`,
`handoff`, `image-to-code`, `improve-codebase-architecture`,
`knowledge-consolidation`, `llm-gate`, `logic-diff`, `logic-fix-all`,
`logic-health`, `logic-locate`, `logic-review`, `mcp-audit`, `module-map`,
`official-code-review`, `parallel-worktrees`, `permission-tuner`,
`plan`, `plan-interrogate`, `pr-review-toolkit`, `receiving-code-review`,
`release`, `release-skills`, `requesting-code-review`, `safe-mode`,
`subagent-driven-development`, `systematic-debugging`, `tdd`,
`test-driven-development`, `thoroughness-scoring`, `to-prd`, `understand`,
`using-superpowers`, `verification-before-completion`, `wiki-builder`,
`wiki-research-loop`, and `writing-plans`.

## Required capability resolution

The required capability names were searched against the actual registry and
installed local skill catalog. Exact IDs are not invented when absent.

| Capability | Resolution | Current IDs / evidence |
|---|---|---|
| source-driven development | `REGISTRY_GAP` | exact installed donor is outside the 214-record registry |
| Deep Understanding | `REGISTRY_GAP` | installed workflow exists locally, but no exact registry record |
| security hardening | `REGISTRY_GAP` | `safe-mode` and `permission-tuner` are conservative proxies, not aliases |
| API/interface design | `REGISTRY_GAP` | `improve-codebase-architecture` and `grill-with-docs` are partial proxies |
| MCP audit | `DIRECT` | `mcp-audit` |
| context engineering | `DIRECT` | `context-engineering` |

Among these six, no exact capability was silently relabeled as a canonical
skill. The missing exact records are registry gaps, not proof that the
procedures do not exist elsewhere.

## Provenance policy

The overlay supports `AUTHOR_DECLARED`, `CURATED`,
`INFERRED_HIGH_CONFIDENCE`, `INFERRED`, and `UNKNOWN`. Current field counts
are:

| Provenance | Field-value count |
|---|---:|
| `AUTHOR_DECLARED` | 179 |
| `CURATED` | 309 |
| `INFERRED_HIGH_CONFIDENCE` | 777 |
| `INFERRED` | 1,035 |
| `UNKNOWN` | explicit default for unavailable fields |

The router gives full weight to author/curated fields, applies a modest
confidence penalty to high-confidence inference, and treats weaker inference
as contextual evidence only. Inferred metadata cannot declare permissions.
Trust, path confinement, source digest, and canonical registry identity remain
independent of routing confidence.

The enrichment code parses harmless scalar/list frontmatter and reads UTF-8
body bytes. It does not invoke a shell, import skill code, run body examples,
follow referenced URLs, install MCP, or execute prerequisite commands.

## Relationships and duplicate analysis

Nine sparse high-confidence edges were retained, each with relationship
provenance:

- `tdd ALTERNATIVE_TO test-driven-development` (and the reciprocal edge).
- `test-driven-development VERIFY_WITH verification-before-completion`.
- `verification-before-completion VERIFY_WITH test-driven-development`.
- `baoyu-imagine SUPERSEDES baoyu-image-gen` (the target is explicitly deprecated).
- `design-taste-frontend SUPERSEDES design-taste-frontend-v1`.
- `wiki-research-loop VERIFY_WITH verification-before-completion`.
- `code-review-excellence VERIFY_WITH verification-before-completion`.
- `mcp-audit COMPLEMENTS context-engineering`.

The current overlay does not promote several plausible but weaker overlaps:
`code-review-excellence` versus `official-code-review`,
`wiki-builder` versus `knowledge-consolidation`, and `safe-mode` versus
`permission-tuner`. They remain curation candidates rather than fabricated
alternatives or supersession claims. No skills were deleted or merged.

## First v3 dogfood routing trace

`using-superpowers` was used as resident task/session authority. It is recorded
as a `GATE` reference where a substantive route exists, but its full body was
not reloaded for every stage. The task was classified as
`COMPLEX / HIGH-RISK / MEDIUM-AMBIGUITY / ARCHITECTURE-CHANGING`; the installed
Deep Understanding workflow was consulted as an escalation fallback because
the exact capability is not present in the repository registry:

`DEEP_UNDERSTANDING: USED_WITH_FALLBACK (REGISTRY_GAP)`.

All active stages below produced an independent `StageRoute` with
`SKILLS_SELECTED`. Every route inspected 214 metadata records and loaded zero
`SKILL.md` bodies during ranking. Selected bodies were read only downstream,
after route selection, under the read-only maintenance/dogfood boundary.
No model profile was selected; runtime evidence was Codex/host-managed only.

Common inputs were `TaskSpec`, the v3 docs, `.superpowers/SKILLS_INDEX.json`,
`categories.json`, canonical body paths/digests, and the selected stage
objective. Common tools were repository filesystem and git/Python standard
library; no MCP server or external network call was used.

| Stage / objective | Selected skills by role slot | Considered / rejected evidence | Output / evidence / result |
|---|---|---|---|
| **UNDERSTAND** — establish registry truth and the census | `GATE using-superpowers`; `PROCESS grill-with-docs`; `DOMAIN understand-diff` | 214 metadata records; broad UI/media, security, and unrelated implementation candidates rejected by domain/stage mismatch; Deep Understanding unavailable in registry | TaskSpec classification, source inventory, census inputs; source evidence required; `SKILLS_SELECTED`, no body load during route |
| **RESEARCH** — inspect bodies and donor signals without executing them | `GATE using-superpowers`; `PROCESS knowledge-consolidation`, `pro-wiki-builder`; `DOMAIN understand-chat` | unrelated code/build/release skills rejected; command/script references were treated as data, not actions | source/donor findings and provenance notes; source evidence required; `SKILLS_SELECTED`, no MCP/network |
| **DESIGN** — define the smallest overlay and conservative policy | `GATE using-superpowers`; `PROCESS grill-with-docs`; `DOMAIN improve-codebase-architecture`; `REVIEW brooks-review`; `VERIFY verification-before-completion` | duplicate process/review candidates rejected where they added no uncovered role or evidence; exact API/security donors recorded as registry gaps | overlay/schema decision, review/verification artifacts; schema validation required; `SKILLS_SELECTED` |
| **PLAN** — sequence implementation, replay, review, and docs | `GATE using-superpowers`; `PROCESS executing-plans`, `tdd`, `writing-plans` | alternative TDD procedure was not loaded in addition to the selected process; unrelated runtime adapter skills rejected | bounded implementation plan and test plan; plan evidence required; `SKILLS_SELECTED` |
| **IMPLEMENT** — build overlay and metadata-first integration | `GATE using-superpowers`; `PROCESS executing-plans`, `test-driven-development`; `DOMAIN image-to-code`; `REVIEW code-review-excellence`; `VERIFY verification-before-completion` | image-to-code was a documented router mis-selection for a metadata task; unrelated MCP/permission skills rejected | schema, generator, overlay, router/resolver changes, tests; tests/schema evidence required; `SKILLS_SELECTED` |
| **REVIEW** — inspect implementation and metadata quality | `GATE using-superpowers`; `PROCESS module-map`; `REVIEW brooks-test`, `pr-review-toolkit`, `requesting-code-review`; `VERIFY baseline-ui` | broad design and visual skills rejected; redundant review pressure noted for later V2 analysis | review findings and simplification questions; review evidence required; `SKILLS_SELECTED` |
| **VERIFY** — execute tests and freshness checks | `GATE using-superpowers`; `PROCESS brooks-harness`; `VERIFY verification-before-completion` | implementation/design skills rejected; no new body read by router | full test result, schema/digest/body freshness evidence; `SKILLS_SELECTED` |
| **HARDEN** — inspect trust and extraction boundaries | `GATE using-superpowers`; `PROCESS safe-mode`; `REVIEW llm-gate`, `pr-review-toolkit`; `VERIFY fixing-accessibility` | exact security-hardening donor is a registry gap; broad performance/MCP candidates rejected without task relevance | security findings, no-execution checks, trust/permission review; security evidence required; `SKILLS_SELECTED` |
| **HANDOFF / LEARN** — publish evidence and proposal boundary | `GATE using-superpowers`; `PROCESS handoff`; `VERIFY verification-before-completion` | learning is proposal-only; no automatic promotion or policy rewrite | census, V2 replay, next prompt, and handoff; diff/tests required; `SKILLS_SELECTED` |

The `understand-diff` workflow found no repository knowledge-graph artifact, so
the research stage used its direct-diff fallback. This is recorded as an
operational fallback, not a hidden reasoning artifact. No chain-of-thought,
scratchpad, or private reasoning was stored.

## Router policy change

The existing Stage Router, scorer, and selected-only resolver now understand
the overlay's provenance without creating a new router architecture:

- `load_current_catalog()` consumes the overlay when present.
- `AUTHOR_DECLARED` / `CURATED` fields are enforceable and receive full weight.
- `INFERRED_HIGH_CONFIDENCE` fields remain eligible with a modest penalty.
- `INFERRED` fields do not satisfy hard semantic assertions.
- unknown fields remain conservative; quarantine/blocked trust never wins.
- route ranking remains metadata-only and never requires raw body text.

This is intentionally not a model, learning, or database implementation.

## Known gaps and next curation work

The census finds meaningful coverage but not completeness. The largest gaps are
the absent exact source-driven, Deep Understanding, security-hardening, and
API/interface records; zero declared permissions and agent compatibility;
sparse relationship evidence; and over-broad inferred outputs (208/214). These
are curation/evaluation work items. Future experience may create a
`MetadataProposal`, but promotion must pass evaluation, provenance, security
review, and policy approval.

See the [V2 routing replay](STAGE_ROUTER_EVAL_V2.md) for fixture-level quality,
historical comparisons, context/latency evidence, and failures intentionally
left visible.
