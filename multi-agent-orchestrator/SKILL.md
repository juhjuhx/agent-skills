---
name: multi-agent-orchestrator
description: "Design and build multi-agent orchestration systems — SQLite task store, state machines with transition matrices, plan validation with progressive degradation, artifact injection pipelines, optimistic locking for concurrency, CLI-first DX. Use when: 多agent調度、orchestrator、task store、agent routing、state machine、plan validation、multi-agent coordination、任務分派。"
---

# Multi-Agent Orchestrator

Central coordination system for multiple AI agents (Codex, Claude, Gemini, OpenCode, MiMo, etc.). Not agent-to-agent communication — this is a **hub-and-spoke** model where one orchestrator manages task lifecycle, routing, and artifact flow.

## When to Use

- Building a task management / orchestration layer for multiple AI agents
- Need state machines for task lifecycle (inbox → planning → done)
- Need to route tasks to different agents based on capability
- Need artifact passing between sequential agent steps
- Need concurrency control when multiple agents might claim the same task

## Architecture Pattern

```
User → Orchestrator (state + memory + routing)
         ├── Planner Agent (Codex) → produces plan
         ├── Worker Agents → execute subtasks
         └── Reviewer Agent → validates output
```

Orchestrator owns: state, memory, routing, artifact store.
Agents own: execution, planning, review — never state.

## Core Components

### 1. SQLite State Store

Six tables — see `references/schema.sql` for full DDL:

| Table | Purpose |
|-------|---------|
| `tasks` | Task lifecycle (status, owner, priority, risk) |
| `events` | Event sourcing (every state change logged) |
| `agents` | Agent registry (role, capabilities, priorities) |
| `artifacts` | Worker outputs (patch, summary, test_log) |
| `decisions` | Decision audit trail |
| `resource_status` | Agent availability tracking |
| `plan_metrics` | Recovery pipeline telemetry (degradation level, errors, health score) |

**Key design decisions:**
- WAL mode for concurrent reads
- `version` column on tasks for optimistic locking
- Events table IS the audit trail (event sourcing lite)
- Artifacts store both inline content AND file paths

### 2. State Machine with Transition Matrix

Define legal transitions as a dict. Illegal transitions raise errors.

```
inbox → planning → planned → ready → claimed → running → review → done
  ↓         ↓         ↓        ↓                                        ↓
blocked ←───┘─────────┘────────┘                                      archived
failed  ←────────────────────────────────────────────────┘
```

**Critical rules:**
- `claim_task()` uses atomic `UPDATE ... WHERE status='ready'` — prevents double-claim
- `blocked` can return to any active state (it's a pause, not a dead end)
- `failed` returns to `planning` (retry = re-plan, not re-run)
- `review → running` is allowed (reviewer requests changes)
- Version column for read-modify-write races (optimistic lock)

**Anti-pattern:** Don't allow `inbox → done` or `running → done` (skips review).

### 3. Plan Validation + Progressive Degradation

When a planner (Codex) produces a plan, validate before accepting:

```
Attempt 1: Direct validate → accept if valid
Attempt 2: Auto-fix (missing IDs, missing execution_order) → validate
Attempt 3: Extract valid parts + HermesSelf fills gaps → validate
Attempt 4: Conservative mode (summary only, no execution)
```

**Key principle:** Partial plan > no plan. Never let a task get stuck.

Plan schema requires: `subtasks[]` (each with id, title, recommended_agent), `execution_order`, `review_strategy`.

### 4. Artifact Injection (Tiered)

When Worker B depends on Worker A's output:

| Tier | Content | When |
|------|---------|------|
| 1 | metadata + compressed summary (≤200 tokens) | Always |
| 2 | summary + excerpt (≤1000 tokens) | Budget allows |
| 3 | file path only | Over budget |

Budget is tracked per brief. Patches get first N lines; summaries get full text; test logs get pass/fail counts only.

### 5. Concurrency Control

**Primary:** Atomic `UPDATE ... WHERE status='ready'` — no double-claim possible.
**Secondary:** `version` column for optimistic locking on read-modify-write.

SQLite WAL mode serializes writers, so true race windows are tiny. But code should be correct by construction.

**Stress test pattern**: Spawn N threads all claiming same task. Expect exactly 1 success, N-1 rejections. Verified with 10 threads.

### 6. Recovery Metrics & Health Report

Track every plan validation attempt in `plan_metrics` table. Generate health reports:

```
Health Score = (L1×100 + L2×75 + L3×40 + L4×0) / total_plans
```

Thresholds:
- L4 > 30% → CRITICAL (revise planner prompt)
- L3 > 40% → WARNING (add auto-fix rules)
- L2 > 30% → NOTICE (improve planner prompt)
- L1 > 80% → HEALTHY

### 7. CLI Migration (Gemini → Antigravity)

When migrating between CLI tools (e.g., Gemini CLI → Antigravity CLI `agy`):
- `agy plugin import gemini` does NOT work with old Gemini plugin format
- Must manually copy: skills/, plugins/, SKILLS_INDEX.md, MCP config, trustedFolders.json
- Create AGENTS.md from GEMINI.md (replace CLI references, preserve model names)
- Model names (gemini-3.5-flash) are API identifiers, not CLI references — preserve them
- Antigravity stores config at `~/.gemini/antigravity-cli/` (inherits Gemini's directory)

## Pitfalls

1. **Don't let agents own state.** Agents should never write directly to the state store. They produce artifacts; the orchestrator stores them.
2. **Don't use Markdown as primary storage.** Markdown is for human-readable exports only. SQLite is the source of truth. Multiple agents writing Markdown = race conditions.
3. **Don't build GUI before validating the pipeline.** CLI-first. GUI is a view over the same data — build it after the core pipeline works.
4. **Don't trust planner output.** Always validate. Codex is a conversational agent, not a YAML generator.
5. **Don't inject full artifact content blindly.** Use tiered injection with token budgets. A 500-line patch injected into a prompt wastes context.
6. **Don't skip event logging.** Every state change, every claim, every failure — log it. Debugging multi-agent issues without an event trail is impossible.
7. **Don't trust `agy plugin import gemini`.** It doesn't recognize old Gemini CLI plugin format. Always manually copy skills/config when migrating CLIs.
8. **Don't forget `.env.production` in `.gitignore`.** A critical security risk — production credentials exposed in git. Always verify with `git ls-files | grep env`.

## CLI DX Patterns (Pre-GUI Phase)

Before building a GUI, the CLI needs:
- **Rich board view** — colored status, grouped by state, with icons
- **Dry-run orchestration** — show what WOULD happen without executing
- **Health check** — one-glance system status (stuck tasks, agent availability)
- **ANSI colors** — not optional. Makes CLI output scannable.

## Test Strategy

Three representative test cases:
1. **Simple single-task** — does the planner over-decompose?
2. **Multi-subtask with dependencies** — does it correctly chain depends_on?
3. **Ambiguous/vague request** — does it degrade to conservative mode?

Each MVP phase must have a smoke test. No exceptions.

## Full-System Audit Pattern (Parallel Subagents)

When auditing a full-stack application (frontend + backend + DB + security + performance), dispatch 3 parallel subagents:

1. **Architecture Agent** — Component structure, routing, state management, API routes, middleware, DB schema, LINE Bot integration, responsive design
2. **Test & CI Agent** — Run all test suites, check GitHub CI status, test API endpoints, verify DB connection, check production health
3. **Security & Performance Agent** — Password hashing, SQL injection, CORS, rate limiting, .env exposure, HTTPS, bundle size, image optimization, memory leaks, scroll listeners, animation performance

Each agent reads AGENTS.md/COORDINATION.md/STATE_OF_THE_UNION.md first for context, then reports ALL findings with specific file paths and line numbers.

Severity levels: CRITICAL (immediate action) > HIGH > MEDIUM > LOW > INFO.

## CLI Command Reference (`hermes-orch`)

```bash
hermes-orch init                              # Create DB + seed 6 default agents
hermes-orch task create "title" -r "request" -p high --risk medium
hermes-orch task list [-s status] [-o owner] [-n limit]
hermes-orch task show T-xxxx                   # Detail + events + artifacts + decisions
hermes-orch task update T-xxxx -s running -o codex
hermes-orch task delete T-xxxx
hermes-orch event log T-xxxx -a agent -t type -m "message"
hermes-orch event list T-xxxx
hermes-orch agent list                         # Show all agents with priorities
hermes-orch agent add name -r "role" -c "cap1,cap2" --planner-priority 10
hermes-orch agent status name available        # Set agent status
hermes-orch resource list / set agent status   # Resource management
hermes-orch stats                              # Global statistics (by status, by owner)
```

## References

- `references/schema.sql` — Full SQLite DDL (7 tables)
- `references/transition-matrix.md` — Complete state transition table
- `references/plan-schema.yaml` — Expected plan output format
- `references/risk-audit.md` — 10 architectural risks and mitigations
