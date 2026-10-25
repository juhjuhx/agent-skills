---
name: multi-agent-orchestration
description: >
  Guides deciding when and how to split a task across multiple cooperating
  LLM agents (supervisor/worker, pipeline, or debate patterns) instead of one
  agent with many tools. Use when a user asks to "design a multi-agent
  system," "should this be one agent or several," "orchestrate sub-agents,"
  fix agents that duplicate work or talk past each other, or is deciding how
  a supervisor agent should delegate to and validate specialist agents.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: ai-agent
  maturity: stable
---

# Multi-Agent Orchestration

## Purpose

Splitting a task across multiple agents can reduce per-agent context load,
allow specialization (a narrower system prompt and tool set per role), and
enable parallelism — but it also multiplies the surface area for
coordination failures: duplicated work, agents that silently disagree,
lost context at hand-off boundaries, and cost/latency from redundant model
calls. Multi-agent orchestration is not automatically better than a single
well-designed agent; it is a specific tool for specific shapes of problem.
This skill covers the common orchestration topologies (supervisor/worker,
pipeline, debate/parallel-with-aggregation), when each is justified over a
single agent, and how to keep hand-offs between agents reliable.

## When to use

- A single agent's context or tool set has grown large enough that it
  shows role confusion or degraded performance on any one sub-task (a
  concrete threshold to check, established in
  [agent-architecture-design](../agent-architecture-design/SKILL.md), before
  reaching for multi-agent as a fix).
- A task naturally decomposes into independent workstreams that can run in
  parallel (e.g. researching three unrelated topics before synthesizing).
- A task benefits from specialist framing — a code-review sub-agent with a
  narrow reviewer persona genuinely produces better reviews than one
  generalist agent asked to "also review code" among ten other jobs.
- You need a distinct verification/critic role separate from the agent that
  produced the output, to catch errors the producing agent is blind to.
- Debugging duplicated work, contradictory outputs, or lost context between
  cooperating agents in an existing multi-agent system.

## Prerequisites & environment

- A working single-agent implementation first — multi-agent orchestration
  should be an evolution from a scoped single agent, not a starting design,
  since most of its coordination problems only become visible once you've
  seen where a single agent actually strains.
- An orchestration mechanism: a supervisor process/agent that dispatches to
  sub-agents and collects results, whether hand-rolled or via a
  framework/runtime.
- A shared understanding across the team of what state, if any, is common
  vs. private to each sub-agent (see step 3 below) — undocumented shared
  state is the most common source of multi-agent bugs.
- Cost/latency budget awareness: N agents each making LLM calls costs
  roughly N× a single agent's calls for the same step, before accounting
  for coordination overhead (see
  [llm-cost-and-latency-optimization](../llm-cost-and-latency-optimization/SKILL.md)).

## Step-by-step guidance

1. **Justify the split with a concrete symptom, not intuition.** Before
   introducing a second agent, write down what specifically breaks with
   one agent: context window pressure, measurable role confusion in
   evaluation results (see
   [agent-evaluation-and-guardrails](../agent-evaluation-and-guardrails/SKILL.md)),
   or a genuine need for parallel independent work. "It felt cleaner to
   split it" is not sufficient justification given the added coordination
   cost.

2. **Choose a topology that matches the task's dependency structure:**
   - **Supervisor/worker**: one supervisor agent plans and delegates
     discrete sub-tasks to worker agents (each with a narrow prompt and
     tool set), then integrates results. Best when sub-tasks are
     specialized but the overall task needs central coordination.
   - **Pipeline**: agents run in a fixed sequence, each consuming the
     prior stage's output (e.g. `researcher -> writer -> fact_checker`).
     Best when the task has a natural linear dependency chain.
   - **Parallel + aggregation (fan-out/fan-in)**: independent agents work
     on genuinely independent sub-parts simultaneously, then a final step
     merges results. Best for independent workstreams (e.g. summarizing
     three unrelated documents) where order doesn't matter.
   - **Critic/debate**: a second agent explicitly reviews or challenges the
     first agent's output before it's finalized. Best when catching a
     specific class of error (factual, safety, style) matters more than
     speed.

3. **Define the hand-off contract between agents explicitly**, as a
   structured schema, not free-form prose passed between prompts:

   ```json
   {
     "from_agent": "researcher",
     "to_agent": "writer",
     "task_id": "task-8842",
     "findings": [
       { "claim": "...", "source": "doc-42", "confidence": "high" }
     ],
     "open_questions": ["..."]
   }
   ```

   Free-form hand-offs ("here's what I found: ...") are the single biggest
   source of lost or misinterpreted context between agents.

4. **Give each sub-agent the narrowest system prompt and tool set that its
   role needs** — this is the actual payoff of splitting; a worker agent
   with a 10-line role-specific prompt and 3 tools will outperform the same
   role embedded as one section of a 40-tool generalist's prompt.

5. **Make the supervisor responsible for validating hand-offs**, not just
   routing them — check that a worker's output matches the expected schema
   and addresses the delegated sub-task before passing it downstream or
   integrating it, rather than assuming compliance.

   ```python
   def supervisor_step(task):
       plan = supervisor_llm.plan(task)
       results = {}
       for subtask in plan.subtasks:
           worker = select_worker(subtask.role)
           output = worker.run(subtask)
           if not validate_schema(output, subtask.expected_schema):
               output = worker.run(subtask, retry_hint="prior output was malformed: ...")
           results[subtask.id] = output
       return supervisor_llm.integrate(task, results)
   ```

6. **Bound total cost and depth explicitly** at the orchestration level —
   cap how many sub-agents a supervisor can spawn per task and how many
   levels of delegation are allowed (avoid a supervisor's worker itself
   spawning further workers unbounded), independent of any single agent's
   own loop cap (see
   [agent-architecture-design](../agent-architecture-design/SKILL.md)).

7. **Decide where shared state lives** — a common data store both agents
   read/write, or strictly message-passing hand-offs with no shared
   mutable state. Message-passing is easier to reason about and debug;
   shared mutable state introduces race conditions in parallel topologies
   and should be avoided unless there's a specific need for it.

8. **Instrument the full multi-agent trace**, not just each agent's
   individual log — you need to see the sequence of hand-offs, not just
   each agent's isolated behavior, to debug coordination failures.

## Best practices

- Start every multi-agent design as a diagram of hand-offs and their
  schemas before writing any prompt — if you can't draw the data flow, the
  orchestration isn't well-defined yet.
- Prefer a small, fixed number of well-defined roles over a dynamic pool of
  ad hoc agents spawned per task — fixed roles are testable and evaluable
  in isolation.
- Give the supervisor (or an explicit critic agent) the job of catching
  errors the producing agent can't see in itself — self-review by the same
  agent/prompt catches far fewer errors than an independent check.
- Keep per-agent context scoped to what that agent's role needs; do not
  pass the full original task transcript to every worker "just in case."
- Evaluate the multi-agent system end-to-end, not only per-agent — a
  system where every individual agent passes its own eval can still fail
  at the integration points (see
  [agent-evaluation-and-guardrails](../agent-evaluation-and-guardrails/SKILL.md)).
- Re-check the single-agent alternative periodically as models improve —
  a split justified by a smaller/older model's context limits may no
  longer be necessary.

## Common pitfalls

- **Symptom:** Two agents each independently do overlapping work (e.g. both
  fetch and summarize the same document) because task boundaries were left
  implicit.
  **Fix:** Make the supervisor's delegation explicit and mutually
  exclusive per sub-task in the plan; validate at integration time that
  no two workers were assigned overlapping scope.

- **Symptom:** A worker agent's output subtly contradicts another worker's
  output (e.g. different numbers for the same metric), and the supervisor
  merges both into a final answer without noticing.
  **Fix:** Add an explicit consistency-check step (rule-based or a
  dedicated critic agent) before integration, rather than assuming the
  supervisor's integration prompt alone will catch contradictions.

- **Symptom:** Context that mattered in an early agent's reasoning (a
  caveat, an assumption) is lost by the time a later agent in a pipeline
  produces the final output, because hand-offs passed only the "answer,"
  not the reasoning behind it.
  **Fix:** Structure hand-offs to include relevant caveats/assumptions/
  confidence explicitly as schema fields, not just the bottom-line result.

- **Symptom:** Cost and latency balloon because a supervisor spawns
  sub-agents that themselves spawn further sub-agents for sub-sub-tasks,
  with no depth limit.
  **Fix:** Cap delegation depth and total sub-agent count per task at the
  orchestration layer; require justification (in code, not just prompt
  instruction) for any recursive delegation.

- **Symptom:** The team reaches for a multi-agent design for a task a
  single well-scoped agent could have handled, and the result is slower,
  more expensive, and no more accurate.
  **Fix:** Re-evaluate against a single-agent baseline with the same eval
  suite before committing to the multi-agent architecture — the split
  should be justified by a measured gap, not adopted by default because it
  seems more sophisticated.

## Worked example

**Task:** produce a weekly engineering status digest that summarizes
merged PRs, open incidents, and upcoming deploys from three unrelated
internal systems.

Topology: parallel + aggregation, since the three data sources are
independent and don't need to inform each other's summarization.

```
fan-out:
  pr_summarizer_agent    (tools: list_merged_prs, get_pr_details)
  incident_agent          (tools: list_open_incidents)
  deploy_calendar_agent   (tools: get_upcoming_deploys)

each returns:
  { "section": "...", "bullets": [ {"text": "...", "source_id": "..."} ] }

fan-in:
  aggregator_agent receives all three structured outputs (not free text),
  validates each against the shared schema, orders sections, and produces
  the final Markdown digest with source citations preserved from each
  sub-agent's output.
```

Each sub-agent gets a narrow prompt and only the 1–2 tools its section
needs — the PR summarizer never sees incident tools or vice versa — and
the whole run is capped at exactly 3 parallel sub-agents with no further
delegation allowed, keeping cost bounded and predictable per digest run.
The aggregator is evaluated separately (does it preserve every source
citation, does it handle a sub-agent returning an empty section gracefully)
from each sub-agent's own eval suite.

## Cross-references

- [agent-architecture-design](../agent-architecture-design/SKILL.md)
- [agent-tool-use-patterns](../agent-tool-use-patterns/SKILL.md)
- [agent-evaluation-and-guardrails](../agent-evaluation-and-guardrails/SKILL.md)
