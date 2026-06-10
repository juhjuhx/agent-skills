# Agent Skills

170+ AI agent skills, organized into categories. Works with **OpenCode / Claude Code / Gemini CLI / Cursor / Codex / Windsurf / Continue / Aider** and more.

## Quick Install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/juhjuhx/agent-skills/main/install.sh)"
```

Without flags → **interactive mode**: pick which categories to install.

## Installation Options

| Command | What it installs |
|---|---|
| `bash install.sh` | Interactive — pick your categories |
| `bash install.sh --minimal` | Essential + Coding only (~60 skills) |
| `bash install.sh --default` | Essential + Coding + Design (~85 skills) |
| `bash install.sh --all` | Everything (170+ skills) |
| `bash install.sh --category essential,coding,design` | Specific categories only |

## Categories

| Category | Skills | When to install |
|---|---|---|
| **Essential** | Plugin dev, MCP, handoff, skill management | Always |
| **Coding** | Review, debug, TDD, architecture, logic | Every developer |
| **Design** | UI/UX, brand, design systems, accessibility | Designers, frontend |
| **Visual Media** | Image gen, diagrams, infographics, slides | Content creators |
| **Content** | Translation, markdown, URL fetch | Writers, translators |
| **Social Media** | WeChat, Weibo, X/Twitter posting | Social media managers |
| **Video & Cinema** | Cinematic prompts, video presentations | Video creators |
| **Three.js 3D** | Complete 3D graphics pipeline | 3D developers |
| **Pro Workflow** | Context mgmt, wiki, LLM council | Power users |
| **Other Tools** | Caveman, grilling, releases, issues | As needed |

## Manage Later

```bash
# List categories and current selection
bash ~/.agents/skills/skill-manager.sh list

# Add a category
bash ~/.agents/skills/skill-manager.sh enable design

# Remove a category
bash ~/.agents/skills/skill-manager.sh disable social-media

# Switch profile
bash ~/.agents/skills/skill-manager.sh switch minimal

# Re-apply config after updating
bash ~/.agents/skills/skill-manager.sh reapply
```

## How It Works

```
~/.agents/skills/             # Full repo (git source of truth)
~/.agents/skills-enabled/     # Only selected skills (symlinks)
  ├── categories.json
  ├── agent-development/   → ../skills/agent-development/
  ├── diagnose/            → ../skills/diagnose/
  └── ...

~/.config/opencode/skills/ → ~/.agents/skills-enabled/  [symlink]
~/.claude/skills/          → ~/.agents/skills-enabled/  [symlink]
~/.cursor/skills/          → ~/.agents/skills-enabled/  [symlink]
...
```

All agents point to the same `skills-enabled/` directory. Only the skills you selected are visible to your agents — no trigger pollution, no context waste.

## Update

```bash
(cd ~/.agents/skills && git pull)
bash ~/.agents/skills/skill-manager.sh reapply
```

## License

MIT
