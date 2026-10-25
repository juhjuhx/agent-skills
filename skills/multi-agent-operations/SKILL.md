---
name: multi-agent-operations
description: "Distribute skills and sync memory across multiple AI agents. Use when: install skills, distribute skills, sync memory, cross-agent, multi-agent coordination."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Multi-Agent, Skills, Distribution, Memory, Cross-Agent, Sync]
    related_skills: [multi-agent-orchestrator, coding-agent-delegation, hermes-agent]
---

# Multi-Agent Operations

Two operational skills for working with multiple AI agents on the same machine — distributing skills and syncing memory.

## Section 1: Skill Distribution

Distribute SKILL.md files to all AI agents on this machine. Each agent stores skills in a different directory.

### Agent Install Paths (macOS)

| Agent | Global Path |
|-------|-------------|
| Hermes | `~/.hermes/skills/{name}/SKILL.md` |
| Claude Code | `~/.claude/skills/{name}/SKILL.md` |
| Codex | `~/.agents/skills/{name}/SKILL.md` |
| Antigravity CLI (agy) | `~/.gemini/antigravity-cli/skills/{name}/SKILL.md` |
| OpenCode | `~/.config/opencode/skills/{name}/SKILL.md` |

### Procedure

1. **Read the source file** — extract individual skills from markdown
2. **Platform adaptation** — rewrite Windows paths (`C:\Users\...`) to macOS (`~/...`)
3. **Install to all agents** — copy SKILL.md to each agent's directory
4. **Verify** — read back one file to confirm
5. **Report** — print summary table of skills before/after

### Pitfalls

- **MiMoCode is Windows-only** — skip on macOS
- **Path adaptation is critical** — Windows paths won't work on macOS
- **Dedup before install** — check if skill already exists
- **Gemini CLI deprecated** — replaced by Antigravity CLI (`agy`)

## Section 2: Cross-Agent Memory Sync

Handle "save/record this" requests when the work was done in another agent (OpenCode, Claude Code, Codex, etc.), not in the current Hermes session.

### Key Signals

- User says "幫我記..." about work not found in session_search
- User references "剛剛" but nothing matches in session_search
- session_search returns 0 results despite user insisting it exists

### Procedure

1. **Quick check** — ONE session_search (limit=3), don't search exhaustively
2. **If not found → ask the user directly** — "這個是在其他 agent 做的對吧？告訴我重點，我直接存起來。"
3. **Check filesystem artifacts** (parallel to asking):
   ```bash
   find ~/Desktop -maxdepth 2 -mtime -1 -type f \( -name "*.md" -o -name "*.py" \)
   ```
4. **Record to memory** — what, where, status, next steps

### Recording Format

```
[項目名稱] — [狀態] ([日期])
- 來源: [agent/tool name]
- 做了什麼: [brief summary]
- 檔案位置: [paths if known]
- 下一步: [next action]
```

### Pitfalls

- **DON'T search exhaustively** — ask the user after one quick search
- **DON'T assume "剛廣" means this session** — user runs multiple agents simultaneously
- **Memory limit hit** — compress existing entries before adding new ones
- **Filesystem locations** — check `~/Desktop/` AND `~/Documents/`

---

## Section 3: Project Handoff When Agent Goes Offline

When an agent in a multi-agent project hits usage limits, crashes, or is otherwise unavailable, create a handoff document so any other agent can pick up immediately.

### Trigger Signals

- Agent hits usage limit (e.g. "You've hit your usage limit")
- Agent session terminates unexpectedly during multi-agent work
- User says "記錄工作進度" or "交接" in context of multi-agent project
- User wants other agents to be able to say a keyword (e.g. "繼續 artfactory") and resume

### Required Reads (Before Writing Handoff)

Read these files from the project root in order:

1. `.agents/AGENT_TASK_BOARD.md` — current task assignments & agent status
2. `COORDINATION.md` — release status, hard boundaries, blockers
3. `.agents/DELEGATION_PLAN_*.md` — who writes what files
4. Latest verification report (`*_VERIFY_*.md`)
5. Any audit reports (`DEEP_AUDIT_REPORT_*.md`, `*_AUDIT_*.md`)
6. `AGENTS.md` / `CLAUDE.md` — agent instructions & commands

### Handoff Document Structure

> Full template: `references/multi-agent-handoff-template.md`

Create `.agents/MULTI_AGENT_HANDOFF_YYYY-MM-DD.md` with these sections:

```
# 快速啟動指南 — 任何 Agent 讀這段即可接手
  (必讀文件順序、Git 狀態、測試狀態、生產環境狀態、唯一阻塞項)

# 各代理工作狀態 & 下一步
  (per-agent table: 角色、已完成、待執行、接回方式)

# [中斷 Agent] 最後一輪工作詳情
  (本回合完成的工作、Gate 狀態)

# [審計 Agent] 代碼審計進度
  (已提交報告摘要、關鍵發現、修復進度追蹤表)

# 優先級任務總覽（帶分配）
  (P0 blockers → P1 stabilization → P2 improvements)

# Dirty Files 清單（不可覆蓋）
  (modified tracked + new untracked, with ⚠️ markers for protected/sensitive)

# 「繼續 [project]」快速接回指令
  (per-agent bash commands to resume)
```

### Audit Findings Progress Table

When incorporating audit reports, always create a progress tracking table:

```
| ID | 發現 | 嚴重度 | 狀態 | 負責 |
|----|------|--------|------|------|
| C1 | .env 明文 secrets | 🔴 嚴重 | 🔴 BLOCKED | User |
| B1 | jobs.js 應徵漏洞 | 🟠 業務 | ✅ FIXED | Claude Code |
| H1 | CSP unsafe-inline | 🟠 高 | ⏳ PENDING | Codex |
```

Severity tiers: 🔴 嚴重 → 🟠 高 → 🟡 中
Status: ✅ FIXED → ⏳ PENDING → 🔴 BLOCKED

### Pitfalls

- **DON'T just update AGENT_TASK_BOARD.md** — create a separate handoff doc that's self-contained
- **DON'T assume the next agent is the same type** — any agent (Claude/Codex/OpenCode/Antigravity) might pick up
- **DO include per-agent "接回指令"** — exact bash/cat commands so the next agent doesn't guess
- **DO include dirty file list** — agents overwrite each other's work without this
- **DO track audit findings with progress table** — prevents re-auditing already-fixed items
- **Protected files** — always mark `⚠️ PROTECTED` and `⚠️ SENSITIVE` in dirty file list
- **Git ahead count** — always include how many commits ahead of origin (prevents accidental force-push confusion)

## Section 4: Multi-Agent Task Board

Create shared coordination files that all agents read at session start.

> Full pattern: `references/task-board-pattern.md`

### When to Create

- User has 2+ agents working on the same project
- User says "整理任務" / "建立任務板" / "通知其他 agent"
- Project has multiple phases with different agent owners

### Quick Structure

1. **Agent 速查表** — one row per agent with role and status
2. **進度總覽** — completed / in-progress / not-started items
3. **Per-Agent 區塊** — each agent owns one section (上次完成/當前任務/阻塞項/下一步)
4. **共享規則** — file naming, technical standards, design decision rules
5. **時程** — phase dates and status
6. **相關檔案** — links to style guides, prompts, references

### File Locations

- Task board: `{project}/.agents/AGENT_TASK_BOARD.md`
- Handoff guide: `{project}/.agents/AGENT_HANDOFF.md`
- Global pointer: `~/.agents/shared-memory/MEMORY.md` (must reference task board)

### Pitfall: execute_code Line Numbers

When using `read_file()` inside `execute_code`, the output includes embedded line numbers (`"1|content"`). If you pass this to `write_file()` from hermes_tools, the line numbers get written into the file. Fix: strip with regex `re.sub(r'^\d+\|', '', line)` or use `terminal` heredoc instead.

## Section 6: Formal Multi-Agent Dispatch with Audit Cycle

When a coordinator agent (e.g. Codex) dispatches tasks to multiple agents with a formal audit gate.

> Full pattern: `references/formal-dispatch-pattern.md`

### Dispatch Structure

The coordinator writes a dispatch section in the task board:

```
## FORMAL MULTI-AGENT DISPATCH — {date}

Global boundaries:
- Plan first; wait for approval before editing source
- Do not deploy, push, stage, commit, or write production D1
- Do not touch protected files: {list}
- Report format: {exact format}

Agent assignments:
| Agent | Task ID | Scope | Status |
```

### Report Format (MANDATORY — exact text)

Every agent MUST use this exact format when reporting:

```
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
```

### Report Accuracy Pitfall (CRITICAL)

**Your report MUST match your actual changes.** If you edited files, `Files changed` must list them. If you said "plan only" but ran patches, that's a contradiction the auditor WILL catch and it results in RETURN, not PASS.

Checklist before submitting report:
1. Run `git diff --check` — must be CLEAN
2. Run `git status --short` — verify Files changed matches reality
3. Run tests — must PASS
4. Re-read your report — does Files changed match git status?

### Append-Only Report Files

Each agent writes a report file to avoid concurrent task board edits:

```
.agents/reports/{YYYY-MM-DD}-{agent}-{task-id}.md
```

Example: `.agents/reports/2026-06-26-hermes-h1-h2-h3.md`

The report file contains the full analysis. The task board only gets the summary status line.

### Audit Cycle

1. Agent reports COMPLETE (with report file)
2. Coordinator audits: scope, protected files, tests, git diff
3. PASS → mark complete, assign next task
4. RETURN → send back with specific fix items
5. BLOCKED → dependency on another agent/task

### Plan-First Gate

When dispatch says "plan first":
- Agent produces a plan (read-only analysis + proposed changes)
- Agent reports COMPLETE with the plan
- Coordinator reviews and either approves implementation or modifies scope
- Only THEN does the agent edit source files

### Pitfalls

- **Don't start next task before audit** — wait for explicit PASS
- **Don't expand scope** — only do what's in your Task ID
- **Don't edit protected files** — check the list before every write
- **Don't contradict yourself** — "no source edits" + actual edits = RETURN
- **Run git diff --check before reporting** — catches trailing whitespace, EOF issues

## Section 5: Read-Only Project Audit

When user says "先不要修改" or "read-only review", run a structured audit without writing any files.

> Full pattern: `references/read-only-audit-pattern.md`

### Quick Procedure

1. Read 5 key files (AGENTS.md → CLAUDE.md → ARCHITECTURE.md → COORDINATION.md → AGENT_TASK_BOARD.md)
2. Run verification: git status, tests, build, audit, production health
3. Code-level checks: grep for security patterns, mass assignment, god objects
4. Compile report with severity levels (🔴🟠🟡🟢)
5. Every finding must include: 影響範圍, 可重現, 建議修改檔案, 驗收測試

### Rules
- NO file modifications, NO staging, NO committing, NO deploying
- NO printing secrets (.env, tokens, passwords)
- DO verify protected files are untracked
- DO check git history for leaked secrets

## Common Pitfalls

1. **Agent paths differ** — each agent has its own skill directory structure
2. **Windows paths in skills** — always rewrite to macOS format
3. **Cross-agent memory is manual** — agents don't automatically share state
4. **session_search only searches Hermes** — other agents' work won't appear
5. **Memory has limits** — compress before adding, don't give up

## Verification Checklist

- [ ] Skills installed to all relevant agents
- [ ] Windows paths rewritten for macOS
- [ ] Memory entries are compact and actionable
- [ ] Filesystem artifacts checked for cross-agent work
