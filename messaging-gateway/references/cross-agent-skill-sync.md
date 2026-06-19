# Cross-Agent Skill Migration

## OpenCode → Hermes Skill Sync

User's OpenCode environment has 169 skills at `~/.agents/skills/`. Hermes had 75 builtin skills. Synced 165 missing skills to Hermes.

### Source Layout

```
~/.agents/skills/<skill-name>/
├── SKILL.md              # Required
├── references/           # Optional linked files
├── templates/            # Optional
├── scripts/              # Optional
└── assets/               # Optional
```

### Target Layout

```
~/.hermes/skills/<category>/<skill-name>/
├── SKILL.md
├── references/
├── templates/
├── scripts/
└── assets/
```

### Sync Script Pattern

```bash
#!/bin/bash
SRC_DIR="$HOME/.agents/skills"
DST_DIR="$HOME/.hermes/skills/opencode-oc"
mkdir -p "$DST_DIR"

for skill_dir in "$SRC_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    skill_file="$skill_dir/SKILL.md"
    
    [ ! -f "$skill_file" ] && continue
    
    # Skip if already exists in any Hermes category
    existing=$(find "$HOME/.hermes/skills" -maxdepth 2 -name "SKILL.md" \
        -path "*/$skill_name/*" 2>/dev/null | head -1)
    [ -n "$existing" ] && continue
    
    # Copy SKILL.md + linked directories
    target="$DST_DIR/$skill_name"
    mkdir -p "$target"
    cp "$skill_file" "$target/SKILL.md"
    for subdir in references templates scripts assets; do
        [ -d "$skill_dir/$subdir" ] && cp -r "$skill_dir/$subdir" "$target/"
    done
done
```

### Key Decisions

- Used `opencode-oc` as category name (not `opencode`) to avoid conflicts
- Skipped non-SKILL.md items (README.md, install.sh, _shared dirs)
- Preserved name conflicts — if Hermes already had a skill with same name, kept the Hermes version
- All 165 skills loaded successfully via `skill_view()`

### Skill Format Compatibility

OpenCode skills use YAML frontmatter with `name` and `description`. Hermes skills use the same format. No conversion needed — direct copy works.

OpenCode skills do NOT have `category` in frontmatter. Category is determined by directory structure in Hermes.
