---
name: skill-authoring
description: "Author skills for Hermes Agent and MCP projects. Use when: write skill, create SKILL.md, skill authoring, MCP skill, add tool to project."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Skills, Authoring, SKILL.md, MCP, Hermes-Agent, Conventions]
    related_skills: [hermes-agent, plan]
---

# Skill Authoring

Two contexts for writing skills — Hermes-internal and MCP projects. Choose based on where the skill will live.

## Quick Decision

| Context | When | Where to write |
|---------|------|----------------|
| **Hermes-internal** | Skill ships with hermes-agent or lives in `~/.hermes/skills/` | `skill_manage(action='create')` |
| **MCP project** | Skill is for an external project using MCP server pattern | `write_file` to project directory |

---

## Section 1: Hermes-Internal Skills

### Two locations

1. **User-local:** `~/.hermes/skills/<category>/<name>/SKILL.md` — personal, created via `skill_manage(action='create')`
2. **In-repo:** `/path/to/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, use `write_file`

### Required Frontmatter

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars
description: Use when <trigger>. <one-line behavior>.  # ≤ 1024 chars
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

### Size Limits

- Description: ≤ 1024 chars (enforced)
- Full SKILL.md: ≤ 100,000 chars
- Aim for 8-14k chars. Push past 20k → split into `references/*.md`

### Structure

```
# <Title>
## Overview
## When to Use
## <Topic sections>
## Common Pitfalls
## Verification Checklist
```

### Workflow

1. **Gather requirements** — ask about: what task/domain, specific use cases, needs scripts or just instructions, reference materials to include
2. Survey peers in target category: `ls skills/<category>/`
3. Draft with `write_file` or `skill_manage(action='create')`
4. Validate frontmatter (name, description present, description ≤ 1024)
5. **Review with user** — present draft, ask if it covers use cases, anything missing
6. Commit: `git add skills/<category>/<name>/ && git commit`

### Common Pitfalls

1. **Using `skill_manage` for in-repo skills** — it writes to `~/.hermes/skills/`, not repo tree
2. **Leading whitespace before `---`** — validator checks `content.startswith("---")`
3. **Description too generic** — start with "Use when..." and describe the trigger class
4. **Forgetting author/license/metadata** — not enforced but every peer has it
5. **Duplicating a peer** — check `ls skills/<category>/` first
6. **Expecting current session to see new skill** — skill loader is cached at session start

---

## Section 2: MCP Skill Authoring

For external projects that expose tools via MCP (Model Context Protocol).

### The 4-File Pattern

```
src/hermes_skills/<skill-name>/
├── SKILL.md              # Agent-facing documentation
├── manifest.json         # MCP tool definitions
├── src/
│   └── <skill>_server.py # Implementation
└── tests/
    └── test_<skill>.py   # Unit tests
```

### 1. SKILL.md

```markdown
---
name: <skill-name>
description: "One-line description. Use when: trigger keywords."
---
# <skill-name> skill
## When to use
## Tools
### `tool_name`
## Examples
```

Include both Chinese and English triggers for multilingual users.

### 2. manifest.json

```json
{
  "name": "<skill-name>",
  "version": "1.0.0",
  "transport": "stdio",
  "command": "python",
  "args": ["-m", "src.<skill>_server"],
  "tools": [
    {
      "name": "tool_name",
      "description": "What this tool does",
      "input_schema": {
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"]
      }
    }
  ]
}
```

### 3. Server Implementation

```python
import json, sys

def tool_function(param: str) -> dict:
    return {"result": "..."}

def handle_tool(name: str, args: dict) -> str:
    if name == "tool_name":
        result = tool_function(args["param"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            print(handle_tool(req.get("tool", ""), req.get("args", {})))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
```

### 4. Tests

```python
from <skill>_server import tool_function, handle_tool

def test_basic_behavior():
    result = tool_function("input")
    assert "result" in result
```

### MCP Pitfalls

1. **Forgetting `ensure_ascii=False`** — CJK characters get escaped
2. **Not handling unknown tools** — MCP clients may send unexpected names
3. **Missing error handling in stdin loop** — one crash kills the server
4. **Wrong `args` in manifest** — must use `["-m", "src.<module>"]`
5. **Unused imports** — run `ruff check --fix` before committing

---

## Common Pitfalls (Both Contexts)

1. **Don't create skills that duplicate existing ones** — check first
2. **Description is how agents match** — include natural language triggers
3. **Test the skill** — verify it loads and the workflow actually works
4. **Keep it focused** — one skill = one class of task, not one specific session
5. **Description = When to Use, NOT What the Skill Does** — if description summarizes workflow, agents follow the description instead of reading the full skill. Start with "Use when [specific triggering conditions]"
6. **When to add scripts** — deterministic operations (validation, formatting) that would be generated repeatedly
7. **When to split files** — SKILL.md exceeds ~200 lines, distinct domains, rarely-needed advanced features

## Description Optimization (CSO)

The description is the ONLY thing agents see when deciding which skill to load. Optimize for discovery:

**Good:** `Use when tests have race conditions, timing dependencies, or pass/fail inconsistently`
**Bad:** `For async testing` (too vague) or `Use when executing plans - dispatches subagent per task with code review between tasks` (summarizes workflow — agent follows description instead of reading skill)

**Rules:**
- Start with "Use when..." + specific triggers/symptoms
- Include concrete error messages, symptoms, situations
- Write technology-agnostic unless skill is technology-specific
- NEVER summarize the skill's process in the description
- Use keywords agents would search for (error messages, symptoms, synonyms)

## Verification Checklist

- [ ] Frontmatter has name, description (≤ 1024 chars), version, author, license, metadata
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description starts with "Use when..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: Overview → When to Use → body → Pitfalls → Checklist
- [ ] Related skills reference resolves
- [ ] Git commit completed (for in-repo skills)
