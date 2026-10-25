---
name: kanban-workflow
description: "Hermes Kanban system: orchestrator decomposition + worker lifecycle. Use when: kanban, task routing, multi-agent orchestration, task decomposition, worker dispatch."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [Kanban, Multi-Agent, Orchestration, Routing, Worker, Task-Management]
    related_skills: [coding-agent-delegation, multi-agent-orchestrator, hermes-agent]
---

# Kanban Workflow

Complete guide for the Hermes Kanban system — orchestrator decomposition and worker lifecycle. The core lifecycle is auto-injected into every worker's system prompt via `KANBAN_GUIDANCE`; this skill is the deeper playbook.

## Two Roles

| Role | Job | Load when |
|------|-----|-----------|
| **Orchestrator** | Decompose goals into tasks, route to specialists | You're a planner/dispatcher profile |
| **Worker** | Execute assigned tasks, report results | You're spawned by the dispatcher |

---

## Section 1: Orchestrator — Decomposition Playbook

### Profiles are user-configured — not a fixed roster

Before fanning out, discover available profiles:
- `hermes profile list` — prints configured profiles
- `kanban_list(assignee="<name>")` — sanity-check a name
- Ask the user: "What profiles do you have?"

The dispatcher silently fails for unknown assignees — cards sit in `ready` forever.

### When to use the board (vs. just doing the work)

Create Kanban tasks when:
1. Multiple specialists needed
2. Work should survive a crash/restart
3. User might want to interject
4. Multiple subtasks can run in parallel
5. Review/iteration expected
6. Audit trail matters

If none apply — use `delegate_task` or answer directly.

### Anti-temptation rules

- **Do not execute the work yourself.** Route to the right specialist.
- **For any concrete task, create a Kanban task and assign it.**
- **Split multi-lane requests before creating cards.**
- **Run independent lanes in parallel.** Link only true data dependencies.
- **Never create dependent work as independent ready cards.** Use `parents=[...]`.
- **If no specialist fits, ask the user.** Don't invent profile names.

### Decomposition playbook

**Step 1 — Understand the goal.** Ask clarifying questions if ambiguous.

**Step 2 — Sketch the task graph.** Draft it out loud before creating anything:

1. Extract lanes from the request
2. Map each lane to an available profile
3. Decide dependencies vs. parallel
4. Show the graph to the user for correction

**Step 3 — Create tasks and link:**

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",
    body="Compare estimated costs...",
)[  "task_id"]

t2 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",
    body="Read findings from T1 and T2...",
    parents=[t1, t2],
)[  "task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`.

**Step 4 — Complete your own task:**

```python
kanban_complete(
    summary="decomposed into T1-T4",
    metadata={"task_graph": {...}},
)
```

**Step 5 — Report back to the user.**

### Common patterns

- **Fan-out + fan-in:** N research cards (no parents) + 1 synthesis card (parents=all)
- **Parallel implementation + validation:** One implementer + one researcher, reviewer depends on both
- **Pipeline with gates:** `planner → implementer → reviewer`, each with `parents=[previous]`
- **Same-profile queue:** N tasks, all same profile, no dependencies

### Goal-mode cards (persistent workers)

```python
kanban_create(
    title="Translate the full docs site to French",
    body="Acceptance: every page translated, no English left.",
    assignee="<translator-profile>",
    goal_mode=True,
    goal_max_turns=15,
)[  "task_id"]
```

After each worker turn, a judge evaluates against acceptance criteria. Worker keeps going until done or budget exhausted.

### Recovering stuck workers

1. **Reclaim** — abort running worker, reset to `ready`
2. **Reassign** — switch to different profile with `--reclaim`
3. **Change profile model** — edit profile config, then Reclaim

---

## Section 2: Worker — Lifecycle and Pitfalls

### Workspace handling

| Kind | What it is | How to work |
|------|------------|-------------|
| `scratch` | Fresh tmp dir | Read/write freely; GC'd when archived |
| `dir:<path>` | Shared persistent directory | Other runs will read what you write |
| `worktree` | Git worktree | Run `git worktree add` if `.git` doesn't exist |

### Good summary + metadata shapes

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
    },
)
```

**Review-required coding task:**
```python
kanban_comment(body="review-required handoff:\n" + json.dumps({...}, indent=2))
kanban_block(reason="review-required: rate limiter shipped, needs eyes before merging")
```

**Research task:**
```python
kanban_complete(
    summary="3 libraries reviewed; vLLM wins on throughput",
    metadata={"sources_read": 12, "recommendation": "vLLM"},
)
```

### Claiming cards you created

Pass `created_cards` on `kanban_complete`:
```python
c1 = kanban_create(title="remediate SQL injection", assignee="security-worker")
kanban_complete(summary="Review done; spawned remediations.", created_cards=[c1["task_id"]])
```

**Never invent ids** — only list ids captured from successful `kanban_create` return values.

### Block reasons that get answered fast

Bad: `"stuck"` — no context.

Good: one sentence naming the specific decision needed. Leave longer context as a comment.

```python
kanban_comment(body="Full context: I have user IPs from Cloudflare headers...")
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth)?")
```

### Heartbeats worth sending

Good: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`
Bad: `"still working"`, empty notes

### Retry scenarios

If `kanban_show` returns `runs: [...]` with closed runs, you're a retry:
- `outcome: "timed_out"` — chunk the work or shorten it
- `outcome: "crashed"` — reduce memory footprint
- `outcome: "spawn_failed"` — profile config issue, ask human via `kanban_block`
- `outcome: "blocked"` — previous attempt blocked, check unblock comment

### Do NOT

- Call `delegate_task` as substitute for `kanban_create`
- Call `clarify` — use `kanban_comment` + `kanban_block` instead
- Modify files outside `$HERMES_KANBAN_WORKSPACE`
- Create follow-up tasks assigned to yourself
- Complete a task you didn't finish — block it instead

---

## Common Pitfalls

1. **Inventing profile names** — dispatcher silently drops unknown assignees
2. **Bundling independent lanes** — create separate cards for independent work
3. **Over-linking** — "finally check X" may still be parallel if X is static config
4. **Forgetting dependency links** — use `parents=[...]` on `kanban_create`
5. **Reassignment vs. new task** — create NEW task linked from reviewer's task
6. **Argument order** — `kanban_link(parent_id=..., child_id=...)` — parent first
7. **Task state can change** — always `kanban_show` first on startup
8. **Workspace may have stale artifacts** — read comment thread for context
9. **Don't rely on CLI** — use `kanban_*` tools (work across all backends)
10. **Tenant inheritance** — pass `tenant=os.environ.get("HERMES_TENANT")` on every create

## Verification Checklist

- [ ] Profiles discovered before planning
- [ ] Task graph shown to user before creating cards
- [ ] Dependencies set via `parents=[...]`
- [ ] `kanban_show` checked on worker startup
- [ ] Good summary + metadata on completion
- [ ] `created_cards` only lists ids from successful creates
- [ ] Block reasons name specific decisions
