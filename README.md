# Huang's AI Agent Skills (167)

Personal skills collection for AI agents (OpenCode / Claude Code / Gemini CLI).

## Structure

Each skill is a directory with a `SKILL.md` file containing instructions, trigger keywords, and workflows.

```
skills/
├── visual-atelier/     # Super visual engine — PPT, infographics, diagrams
├── baoyu-imagine/      # AI image generation
├── html-ppt/           # HTML presentations
├── tdd/                # Test-driven development
├── diagnose/           # Systematic debugging
├── writing-plans/      # Implementation plan writing
├── ...
```

## Installation

### OpenCode
Skills are auto-discovered from `.config/opencode/skills/`.

### Claude Code
```bash
# Link all skills
cd ~/.claude/skills
for d in ~/.agents/skills/*/; do
  name=$(basename "$d")
  ln -sfn "$d" "$name"
done
```

### Gemini CLI
```bash
gemini skills link ~/.agents/skills/*/
```

## Origin

Maintained at `~/.agents/skills/`. Source of truth for all AI agent environments.
