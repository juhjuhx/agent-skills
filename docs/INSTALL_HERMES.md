# Install for Hermes Agent

Hermes discovers skills natively from `~/.hermes/skills/`. No adapter, no model or permission
changes.

## Install all public skills

```sh
git clone https://github.com/juhjuhx/agent-skills.git agent-skills && cd agent-skills
bash install.sh --all --host hermes
```

What happens:
1. Clones/uses the checkout under `~/.agents/skills`.
2. Activates all 464 skills into `~/.agents/skills-enabled/` as top-level links.
3. For Hermes, creates **selective per-skill symlinks** into `~/.hermes/skills/` for any skill
   slug not already present. Existing user skills are never touched or overwritten.

## Update / verify / rollback

```sh
bash install.sh --update --host hermes      # ff-only refresh of a clean checkout
bash install.sh --verify --host hermes      # validate links resolve to SKILL.md
bash install.sh --rollback --home $HOME     # restore previous managed backup
```

After install, confirm Hermes sees the new skills (native discovery, no config change):
skill names appear in Hermes' available-skills list for the next session.
