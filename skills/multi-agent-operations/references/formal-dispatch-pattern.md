# Formal Multi-Agent Dispatch Pattern

> Proven from ArtFactory (2026-06-26) — Codex as coordinator, Hermes/Claude/OpenCode/MimoCode as workers.

## Dispatch Template

Coordinator writes this into `.agents/AGENT_TASK_BOARD.md`:

```markdown
## FORMAL MULTI-AGENT DISPATCH — {date}

User approved formal notification to all agents. This supersedes older windows.

Global boundaries:
- Plan first; wait for lead/user approval before editing source.
- Do not deploy, push, stage, commit, or write production D1.
- Do not print, log, request, or paste any secret/token/password value.
- Do not touch or stage:
  - `{protected_file_1}`
  - `{protected_file_2}`
- Design/image/UI tasks must pause for user direction first.

Required progress report format:
STATUS: IN_PROGRESS | BLOCKED | COMPLETE
Agent:
Task ID:
Files read:
Files changed:
Commands run:
Results:
Remaining risks:
Needs user action:
Next recommended owner:

### Agent assignments
| Agent | Task ID | Scope | Status |
|-------|---------|-------|--------|
| Hermes | H-1 | {scope} | ASSIGNED |
| Claude | C-1 | {scope} | ASSIGNED |
```

## Report File Convention

Each agent writes: `.agents/reports/{date}-{agent}-{task}.md`

Contains full analysis, code evidence, patch plans, test lists.
The task board only gets the summary status line.

## Audit Checklist (for Coordinator)

1. **Scope**: Did the agent only touch files in their assignment?
2. **Protected files**: Did they touch `scripts/output/*.sql`, `SECURITY_REMEDIATION_PLAN.md`, `.db`?
3. **Tests**: `npm test --workspace=backend -- --runInBand` + `npm test --workspace=frontend`
4. **Build**: `npm run build`
5. **git diff --check**: CLEAN (no trailing whitespace, EOF issues)
6. **Report accuracy**: Does Files changed match `git status --short`?
7. **Secrets**: No .env values printed in report or terminal output?

## Return Reasons (Common)

1. Report says "no edits" but files were changed
2. Tests failing after changes
3. git diff --check not clean
4. Functions placed outside framework closure (Pinia defineStore, React component)
5. Protected file touched
6. Scope expanded without approval

## STOP Rule

After completing or hitting a blocker on assigned Task ID:
- STOP all work
- Report in exact format
- Do NOT start next task
- Do NOT expand scope
- Wait for explicit PASS from coordinator
