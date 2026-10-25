# Multi-Agent Task Board Pattern

> Proven structure from 《你要去哪裡》project (2026-06-25).
> Creates a shared coordination file all agents read at session start.

## File Location

- Project-specific: `{project_root}/.agents/AGENT_TASK_BOARD.md`
- Global shared memory: `~/.agents/shared-memory/MEMORY.md`

## Task Board Structure

```markdown
# {Project Name} — 多 Agent 任務板

> Updated: {timestamp}
> 所有 AI Agent 啟動時必須讀取此檔案。

---

## ⚡ Agent 速查表

| Agent | 角色 | 狀態 |
|-------|------|------|
| **Hermes** | 中控/路由 | 🟢 活躍 |
| **Claude Code** | Backend | 🟡 待命 |
| **Codex** | Review | 🔴 額度用盡 |

---

## 📊 進度總覽

### ✅ 已完成 — {N} 項
| Item | Status | Agent | Notes |

### 📝 進行中 — {N} 項
| Item | Prompt/File | Priority |

### 🔲 未開始 — {N} 項
| Item | Dependencies |

---

## 🤖 各 Agent 任務區塊

### ═══ {Agent Name} ═══
**上次活躍**：{date}
**上次完成**：
- ✅ {task 1}
- ✅ {task 2}
**當前任務**：{description}
**阻塞項**：{blocker or 無}
**下一步**：{action}

---

## 📋 共享規則
1. {rule 1}
2. {rule 2}

---

## 📅 時程
| Phase | Date | Content | Status |

---

## 🔗 相關檔案
| File | Purpose |
```

## Per-Agent Section Rules

Each agent gets exactly ONE section with these fields:
- **上次活躍**: last date they did work
- **上次完成**: bullet list of completed tasks
- **當前任務**: what they should be doing now
- **阻塞項**: what's preventing progress (or 無)
- **下一步**: concrete next action

**CRITICAL**: Only the owning agent updates their section. Never modify another agent's section.

## Shared Rules Section

Must include at minimum:
1. File naming conventions
2. Technical standards (HTML format, SVG format, etc.)
3. Design decision rules (who decides, how to ask)
4. Filesystem rules (macOS backslash paths → os.walk())
5. Update rules (when to update task board)

## Global Shared Memory Pointer

Task board MUST be referenced from `~/.agents/shared-memory/MEMORY.md`:

```markdown
## 任務板位置
- {Project}: `{path}/.agents/AGENT_TASK_BOARD.md`
- 全域共享記憶：本檔案
```

## Handoff File (New Session Startup)

Create `.agents/AGENT_HANDOFF.md` for agents joining mid-project:

```markdown
# {Project} — Agent 接回指南

## 🚀 快速啟動
1. 讀本檔案
2. 讀 AGENT_TASK_BOARD.md
3. 讀 ~/.agents/shared-memory/MEMORY.md
4. 確認自己的任務區塊
5. 開始工作

## 📁 專案目錄結構
(full tree with annotations)

## 🤖 各 Agent 具體任務
### {Agent Name}
**你的任務**：{description}
#### 任務清單（按優先順序）
| # | Task | File | Reference |

## 📋 共享規則
(consolidated from task board)
```

## Pitfalls

- **Don't use line numbers in files** — `read_file()` in `execute_code` returns `"1|content"`. If you pass this to `write_file()` from hermes_tools, line numbers get embedded. Strip with `re.sub(r'^\d+\|', '', line)` or use `terminal` heredoc instead.
- **Don't put all agents in one section** — each agent needs their own clearly delineated section
- **Don't forget the global memory pointer** — agents won't find the task board without it
- **Don't mix status with instructions** — task board = status, handoff = instructions
- **Update timestamp on every change** — agents check timestamp to detect stale boards
- **Protected/sensitive files** — always mark with ⚠️ in any file listing
