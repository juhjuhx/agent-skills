# Cross-Agent Installation (M4-P8)

Copy-paste procedures for deploying the full public skill library to a new machine or
a different host. Every command below corresponds to a real, tested installer flag —
nothing references a flag that does not exist.

All procedures assume the repo is cloned once, then the installer maps skills per host.

```sh
git clone https://github.com/juhjuhx/agent-skills.git agent-skills
cd agent-skills
```

## The four universal commands

| Command | What it does |
|---|---|
| `INSTALL` | `bash install.sh --all --host <host>` |
| `UPDATE`  | `bash install.sh --update --host <host>` (ff-only on a clean checkout) |
| `VERIFY`  | `bash install.sh --verify --host <host>` |
| `ROLLBACK`| `bash install.sh --rollback --home $HOME` (restores last managed backup) |

`<host>` is one of: `hermes`, `dsh`, `opencode`, `claude`, `codex`, `gemini`.
Omit `--host` (default `auto`) to link every host directory that already exists.

## Hermes

```sh
bash install.sh --all --host hermes
# After: every missing skill is symlinked into ~/.hermes/skills/<slug>/
# Existing user skills in that directory are never overwritten.
bash install.sh --verify --host hermes      # confirm links resolve to SKILL.md
```
Expected result: `~/.hermes/skills/` gains up to 461 name-installable skills
(464 packages on disk; 3 extra slugs share a name with a core root skill, root wins).

## DeepSeek Harness

```sh
bash install.sh --all --host dsh
bash install.sh --verify --host dsh
```
DSH scans skill roots non-recursively, so the installer writes each `skills/<slug>`
package as a **top-level direct subdirectory** link — do not manually copy the `skills/`
parent (that would be one invisible entry).

## OpenCode / Claude / Codex / Gemini

```sh
bash install.sh --all --host opencode    # ~/.config/opencode/skills
bash install.sh --all --host claude      # ~/.claude/skills
bash install.sh --all --host codex       # ~/.codex/skills
bash install.sh --all --host gemini      # ~/.gemini/skills
```

## Update + rollback on a later machine

```sh
bash install.sh --update --host hermes    # ff-only refresh; refuses if the checkout is dirty
bash install.sh --verify --host hermes
# If an update goes wrong:
bash install.sh --rollback --home $HOME    # restore the previous managed link set
```

## Notes

- The installer never changes model, default-agent, or permission settings.
- `--update` requires a clean, origin-tracking checkout; it will refuse otherwise.
- `--rollback` restores `~/.agents/skills-enabled-previous-*` (the last backup the
  installer created). It does not delete anything the user owns.
- To see exactly what will happen without touching anything:
  `bash install.sh --all --host hermes --dry-run`.
