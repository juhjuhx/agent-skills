# ArtFactory Agent Roster & Boundaries

> Source: `~/Desktop/artfactory/.agents/AGENT_TASK_BOARD.md` (last verified: 2026-06-18)

## Current Status (2026-06-18)

- **Release stabilization freeze**: ACTIVE
- **Delegation plan**: `.agents/DELEGATION_PLAN_2026-06-18.md`
- **Backend**: 24 suites / 208 tests / 60.7% coverage (gate: 60%) ✅
- **Frontend**: 22 files / 146 tests
- **Production**: Railway healthy, 114 jobs, v1.0.0
- **Git**: main is 18 commits ahead of origin/main (not pushed)
- **Blocking**: P0-A credential rotation (20 exposed secrets need rotation at provider dashboards)
- **AI model**: gemini-3.5-flash credits exhausted

## Current Agent Roles

| Agent | Role | Write Scope |
|-------|------|-------------|
| Codex CLI | Code review, security hardening, integration verification | Cross-project; small scoped fixes after tests |
| Claude Code | Backend/API/database/LINE Bot implementation | Assigned backend files/tests only |
| Antigravity CLI (agy) | Frontend UX & Animation + System Audit | Assigned frontend files/tests |
| OpenCode | Read-only architecture/security audit | No code writes unless Codex authorizes |
| MiMo Code | Documentation automation, coordination | `.agents/*.md` only; no code or production writes |

## Hard Boundaries (DO NOT violate)

- Do not modify `frontend/src/pages/ProfilePage.vue` unless Codex explicitly opens it
- Do not modify `scripts/output/jobs_1111_compressed.sql` (contains unrelated dirty work)
- Do not write to production D1 without explicit user approval
- Do not call real paid/external APIs during local validation
- Do not commit or publish secrets
- Before editing shared backend files (`index.js`, `cloudflare.js`, `aiService.js`, `lineBot.js`, schema), check the task board

## Shared (Co-Managed) Files

These files require checking the task board before editing:
- `backend/src/index.js` — CSP, CORS, route registration
- `backend/src/services/cloudflare.js` — database access layer
- `backend/src/services/aiService.js` — AI tools
- `cloudflare/d1/schema.sql` — database schema
- `Dockerfile` — build process
- `ARCHITECTURE.md` — architecture doc

## Task Board Location

`~/Desktop/artfactory/.agents/AGENT_TASK_BOARD.md`

## Coordination Docs

- `~/Desktop/artfactory/COORDINATION.md` — latest status + agent announcements
- `~/Desktop/artfactory/AGENTS.md` — project memory + agent roles
- `~/Desktop/artfactory/.agents/COORDINATION_STATUS_SECURITY.md` — security wave status

## Required Agent Report Format

Every agent must report back with:
```
STATUS: COMPLETE | COMPLETE_WITH_NOTES | BLOCKED | NEEDS_INFO
Agent:
Task:
Files changed:
Commands run:
Results:
Findings:
Remaining risks:
Next recommended owner:
```

## Git Commit Conventions

- `security:` — security fixes
- `perf:` — performance improvements
- `test:` — test additions
- `docs:` — documentation only
- `feat:` — new features
- `ci:` — CI/CD changes
- Use `--no-verify` only for documentation commits that mention secret names (not actual secrets)
