# Multi-Agent Project Handoff Template

> Template derived from ArtFactory handoff (2026-06-20). Adapt sections to your project.

## Header Block

```markdown
# [Project] 多代理交接 — YYYY-MM-DD HH:MM CST

> **最後活躍代理**: [Agent Name]
> **中斷原因**: [usage limit / crash / user instruction]
> **用戶指令**: 「[keyword]」時，[Agent A] / [Agent B] 皆可接回
```

## 快速啟動指南

```markdown
### 1. 必讀文件順序（按優先級）
① 本檔案
② .agents/AGENT_TASK_BOARD.md
③ COORDINATION.md
④ .agents/DELEGATION_PLAN_*.md
⑤ Latest verification report
⑥ CLAUDE.md / AGENTS.md

### 2. 當前 Git 狀態
Branch / Ahead count / Latest commit / Working tree status / Protected files

### 3. 測試 & 建置狀態
Backend tests / Frontend tests / Coverage / Build / Audit / git diff --check

### 4. 生產環境狀態
Health / API endpoints / SPA status

### 5. 唯一阻塞項
Single most critical blocker with owner
```

## Per-Agent Status Table

```markdown
| Agent | 當前角色 | 已完成 | 待執行 | 接回方式 |
|-------|---------|--------|--------|---------|
| Codex | ... | ... | ... | 讀本檔案 → 從 [task] 開始 |
| Claude | ... | ... | ... | 說「[keyword]」→ 讀本檔案 |
```

## Audit Progress Table

```markdown
| ID | 發現 | 嚴重度 | 狀態 | 負責 |
|----|------|--------|------|------|
| C1 | [critical finding] | 🔴 嚴重 | 🔴 BLOCKED | User |
| B1 | [business logic] | 🟠 業務 | ✅ FIXED | Claude Code |
| H1 | [high risk] | 🟠 高 | ⏳ PENDING | Codex |
| R1 | [race condition] | 🟡 競態 | ✅ FIXED | Claude Code |
```

## Dirty Files List

```markdown
### Modified Tracked Files (N)
(list with ⚠️ markers for protected)

### New Untracked Files (N)
(list with ⚠️ markers for sensitive / must-include-in-release)
```

## Per-Agent Resume Commands

```markdown
### [Agent A] 接回
cat .agents/MULTI_AGENT_HANDOFF_*.md
npm test --workspace=backend -- --runInBand
# then specific task

### [Agent B] 接回
cat .agents/OPENCODE_RELEASE_VERIFY_*.md
curl /health
# then specific verification
```

## Key Principles

1. **Self-contained** — next agent reads ONE file and knows everything
2. **Any agent can pick up** — don't assume same agent type resumes
3. **Track audit findings** — prevent re-auditing fixed items
4. **Mark protected files** — agents overwrite each other without this
5. **Include git ahead count** — prevents force-push confusion
6. **Per-agent commands** — exact bash so next agent doesn't guess
