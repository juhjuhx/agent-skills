---
name: coding-agent-delegation
description: "Delegate coding to external AI agents: Claude Code, Codex, OpenCode. Use when: delegate coding, autonomous agent, coding agent, Claude Code, Codex, OpenCode, external coder."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Delegation, Claude-Code, Codex, OpenCode, Autonomous, PTY, Automation]
    related_skills: [hermes-agent, github-workflow, multi-agent-orchestrator]
---

# Coding Agent Delegation

Delegate coding tasks to external AI coding agents via the Hermes terminal. Three agents, each with different strengths — choose based on the task.

## Quick Comparison

| Agent | Install | Auth | Best for | PTY needed? |
|-------|---------|------|----------|-------------|
| **Claude Code** | `npm i -g @anthropic-ai/claude-code` | OAuth or `ANTHROPIC_API_KEY` | Complex multi-step tasks, PR reviews | Print mode: no. Interactive: yes (tmux) |
| **Codex** | `npm i -g @openai/codex` | `OPENAI_API_KEY` or OAuth | One-shot tasks, parallel worktrees | Always yes |
| **OpenCode** | `npm i -g opencode-ai@latest` | `opencode auth login` | Provider-agnostic, flexible models | Interactive only |

## Decision Flow

1. **One-shot task** (fix bug, add feature, refactor) → Claude Code print mode or Codex exec
2. **Multi-turn iterative** → Claude Code interactive (tmux) or OpenCode interactive
3. **Parallel batch** (fix multiple issues) → Codex with worktrees
4. **PR review** → Claude Code (`--from-pr`) or OpenCode (`opencode pr`)
5. **Provider flexibility** (not locked to Anthropic/OpenAI) → OpenCode

---

## Section 1: Claude Code

### Print Mode (PREFERRED for most tasks)

```
terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
```

**Key flags:** `-p` (non-interactive), `--max-turns N` (prevent runaway), `--output-format json`, `--model sonnet|opus|haiku`

### Interactive Mode (tmux)

```
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
terminal(command="sleep 5 && tmux send-keys -t claude-work 'Your task here' Enter")
terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")
```

### PR Review

```
terminal(command="claude -p 'Review this PR thoroughly' --from-pr 42 --max-turns 10", workdir="/path/to/repo", timeout=120)
```

### Pitfalls

- Interactive mode REQUIRES tmux (not just pty=true)
- `--dangerously-skip-permissions` dialog defaults to "No" — send Down+Enter
- `--max-turns` is print-mode only
- Session resumption requires same directory

---

## Section 2: Codex

### One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

### Background Mode

```
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
```

### Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution |
| `--full-auto` | Auto-approve file changes in sandbox |
| `--yolo` | No sandbox, no approvals |
| `--sandbox danger-full-access` | No sandbox (for gateway context) |

### Parallel Worktrees

```
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="codex --yolo exec 'Fix issue #78'", workdir="/tmp/issue-78", background=true, pty=true)
```

### Pitfalls

- Always use `pty=true` — Codex hangs without it
- Git repo required — use `mktemp -d && git init` for scratch
- Gateway context may need `--sandbox danger-full-access`

---

## Section 3: OpenCode

### One-Shot Tasks

```
terminal(command="opencode run 'Add retry logic to API calls'", workdir="~/project")
```

### Interactive Sessions

```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
process(action="poll", session_id="<id>")
```

### Key Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot execution |
| `--continue` / `-c` | Continue last session |
| `--model provider/model` | Force specific model |
| `--thinking` | Show model thinking |
| `--file path` / `-f` | Attach context files |

### PR Review

```
terminal(command="opencode pr 42", workdir="~/project", pty=true)
```

### Pitfalls

- `/exit` is NOT valid — use Ctrl+C to exit TUI
- Enter may need to be pressed twice in TUI
- `opencode run` does NOT need pty

---

## Section 4: Parallel Execution Pattern

Run multiple agents simultaneously for batch work:

```
# Task 1: Fix backend
terminal(command="tmux new-session -d -s task1 -x 140 -y 40")
terminal(command="tmux send-keys -t task1 'cd ~/project && claude -p \"Fix auth bug\" --max-turns 10' Enter")

# Task 2: Write tests
terminal(command="tmux new-session -d -s task2 -x 140 -y 40")
terminal(command="tmux send-keys -t task2 'cd ~/project && claude -p \"Write integration tests\" --max-turns 15' Enter")

# Monitor all
terminal(command="sleep 30 && for s in task1 task2; do echo '=== $s ==='; tmux capture-pane -t $s -p -S -5; done")
```

---

## Section 5: Cost & Performance Tips

1. **Use `--max-turns`** in print mode to prevent runaway loops
2. **Use `--effort low`** for simple tasks (Claude Code)
3. **Use `--model haiku`** for cheap tasks, `--model opus` for complex
4. **Pipe input** instead of having the agent read files
5. **Use `--allowedTools`** to restrict capabilities
6. **Start new sessions** for distinct tasks — fresh context is more efficient

---

## Common Pitfalls

1. **Codex/OpenCode require pty=true** — they're interactive terminal apps
2. **Claude Code print mode is cleaner** — prefer it over interactive for one-shots
3. **Always set workdir** — keep agents focused on the right project
4. **Monitor tmux sessions** — use `tmux capture-pane` to check progress
5. **Clean up tmux sessions** — kill them when done
6. **Report results to user** — summarize what the agent did and what changed
7. **Don't kill slow agents** — check progress with `process(action='log')` first
8. **Gateway context needs special handling** — Codex may need `--sandbox danger-full-access`

## Verification Checklist

- [ ] Agent installed and authenticated
- [ ] Correct working directory set
- [ ] `--max-turns` set for print mode tasks
- [ ] PTY enabled for interactive agents
- [ ] tmux sessions cleaned up after completion
- [ ] Results summarized to user
