# Donor Research Notes and Provenance

> Status: design research notes. The v3 contracts synthesize patterns; they do not copy upstream prose or implementation.

## Addy Osmani — lifecycle engineering donor

The repository's `addy-*` skills are the local donor set. The useful lifecycle shape is:

```text
DEFINE -> PLAN -> BUILD -> VERIFY -> REVIEW -> SHIP
```

Adopt the qualities **specific**, **verifiable**, **battle-tested**, and **minimal**. The v3 stage plan, acceptance criteria, evidence gate, and incremental rerouting use these qualities as design constraints.

Patterns to integrate and keep attributable:

`spec-driven-development`, `planning-and-task-breakdown`, `incremental-implementation`, `test-driven-development`, `context-engineering`, `source-driven-development`, `doubt-driven-development`, `api-and-interface-design`, `code-review-and-quality`, `code-simplification`, `security-and-hardening`, `performance-optimization`, and `documentation-and-adrs`.

The adapter and router should reuse their engineering disciplines as independent role assignments, not collapse them into one large prompt or duplicate their files per runtime.

## Matt Pocock — composable engineering skills donor

The intended source is [`mattpocock/skills`](https://github.com/mattpocock/skills), **not Maxed Apps**. Its philosophy is small, composable, engineering-oriented, and agent-independent. The v3 graph therefore distinguishes:

- **User-invoked skills** — orchestration entry points such as `to-spec`, `implement`, `wayfinder`, and `grill-with-docs`.
- **Model-invoked skills** — reusable engineering disciplines such as `tdd`, `diagnosing-bugs`, `domain-modeling`, `codebase-design`, `code-review`, and `research`.

Useful patterns to preserve include shared domain language through `CONTEXT.md`, ADRs, deep-module design, and small feedback loops. They become metadata, role, context, and evidence signals rather than a new universal runtime.

## Hermes — learning and long-running coordination donor

Hermes contributes persistent learned skills, `/learn`-style distillation, MCP, cross-agent import, and long-running coordination. v3 adopts the observable proposal/eval/promotion loop in [Learning and Evaluation](LEARNING_AND_EVALS.md), but does not duplicate Hermes memory or automatically import its artifacts into trusted core.

## Alibaba OpenCodeReview — independent evidence donor

The source is [`alibaba/open-code-review`](https://github.com/alibaba/open-code-review). v3 records its `ocr scan` full-source lane separately from `ocr review` diff review and preserves Delegate mode's distinction between deterministic file/rule selection and host-agent review intelligence. The review taxonomy is documented in [Review Pipeline](REVIEW_PIPELINE.md).

## DeepSeek Harness — harness architecture donor

The source is [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness). Treat it as a full harness, not merely a DeepSeek model client. Its architecture motivates tracking plugin-based assembly, ordered prompt sections, runtime context, prompt variables, tool schemas, agent-scoped overrides, tool ordering, context/token cost, and KV-cache stability.

The universal adapter contract therefore separates:

```text
static prompt prefix
  + dynamic runtime context
  + tool-schema budget
  + tool ordering
  + cache stability
```

v3 does not copy DeepSeek implementation directly. The harness is a donor for contract concerns and observability.

## MiMo Code and Compose

MiMo Code is documented as an agent runtime; MiMo models are model profiles. Its native Agent Skills, on-demand loading, primary agents, subagents, permissions, MCP, commands, and Compose workflow are adapter concerns. Compose may provide a native workflow surface, but it does not replace using-superpowers stage routing. A future adapter compares Compose stages to v3 stages and emits the same TaskSpec, route, and evidence artifacts.

## License and provenance rule

Donor ideas must be recorded with source, ref, license, and date before material is imported. Do not copy upstream prose without license/provenance tracking. Distilled local guidance must identify what was adapted, what remains external, and whether the result is a proposal, a generated artifact, or a promoted canonical skill.
