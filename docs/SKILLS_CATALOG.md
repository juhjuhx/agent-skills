# Skills Catalog (M4-P8)

Machine-readable index: [`catalog.json`](../catalog.json) / [`catalog.lock.json`](../catalog.lock.json).
This page is the human-facing summary; all counts below are generated from the shipped manifest, not hand-typed.

## Totals

| Metric | Count |
|---|---|
| Core root-level skills | 14 |
| Additional packages under `skills/<slug>/` | 450 |
| **Total public skills** | **464** |
| Distinct categories | 14 |
| Registry records | 461 |

Categories: agent-orchestration, coding, communication, data-science, design, devops, documents, essential, game-development, productivity, research, review, security, video

## Host loadability

Counts of skills declaring each host in `host_compat` (from SKILL.md frontmatter + native discovery evidence):

- `dsh`: 450
- `opencode`: 450
- `claude`: 450
- `codex`: 450
- `gemini`: 450
- `hermes`: 419

### Name-collision conventions

- Three Hermes-adapted packages whose base name matches a core root-level skill ship under a `-hermes` suffix (requesting-code-review-hermes, systematic-debugging-hermes, test-driven-development-hermes). Both versions are name-installable; the root Superpowers version keeps the bare name.
- Roughly 26 registry pairs use a `-2` suffix to distinguish same-named skills from different sources (e.g. `scholar-notes` vs `scholar-notes-2`). The `-2` entry is the local mirror/port. For name-based hosts, the non-suffixed slug is preferred.

> `dsh` requires YAML frontmatter with `name` + `description`; the installer materializes every
> `skills/<slug>` package as a **top-level direct subdirectory** of the skills root so DSH's
> non-recursive scan discovers it. Hermes discovers natively via `~/.hermes/skills` (selective
> per-skill symlinks, never overwriting user skills).

## Browsing by category

- **agent-orchestration**
- **coding**
- **communication**
- **data-science**
- **design**
- **devops**
- **documents**
- **essential**
- **game-development**
- **productivity**
- **research**
- **review**
- **security**
- **video**

Full per-slug listing: `python3 scripts/skills_cli.py list` or `python3 scripts/install_v3.py --list`.
