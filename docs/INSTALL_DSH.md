# Install for DeepSeek Harness (DSH)

DSH scans skill roots **non-recursively** at direct-child depth. The installer maps every
`skills/<slug>/` package to a **top-level direct subdirectory** of the skills root, so DSH
discovers all 464 public skills without you copying the `skills/` parent (which would be
a single entry and invisible to the scanner).

## Install

```sh
git clone https://github.com/juhjuhx/agent-skills.git agent-skills && cd agent-skills
bash install.sh --all --host dsh
```

DSH discovery roots supported: `~/.dsh/skills/`, `~/.agents/skills/`, and project-level skill
roots. The installer writes into the first that exists (or is creatable under `--home`).

## Requirements

- Skills carry YAML frontmatter (`name`, `description`) -> detected loadable by DSH.
- DSH reads each plugin/skill's `package.json` peerDependencies and skips version mismatches at
  boot. Skill packages without a pinned `package.json` are discovered and read on demand.

## Verify a skill actually loads in DSH

```sh
bash install.sh --verify --host dsh
dsh --profile web   # then invoke the skill by name; confirm the body loads, not just discovery
```
