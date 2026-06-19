---
name: macos-cleanup
description: >
  Analyze and free disk space on macOS. Covers mole CLI usage, common large-cache
  locations, interactive TTY tool workarounds, and app container cleanup.
category: apple
triggers:
  - disk space, disk usage, clean up, free space, storage
  - mole, clean, optimize, analyze disk
  - too little space, running out of space
---

# macOS Disk Cleanup

Analyze disk usage and free space on macOS. Primary tool is **mole** (tw93/mole).

## mole — Interactive CLI Workaround

mole is a TTY-based interactive tool. It **cannot** run via plain `piped` input
in non-interactive sessions. Use the `script` wrapper:

```bash
# Analyze disk (menu option 4)
script -q /dev/null bash -c '(echo 4; sleep 1; echo 4; sleep 1; echo "")' | mole 2>&1 | cat
```

The `sleep 1` delays let the UI render before the keystroke arrives.
Pipe through `| cat` to strip TTY control sequences from output.

### mole menu options
1. Clean — free up disk space
2. Uninstall — remove apps completely
3. Optimize — check and maintain system
4. Analyze — explore disk usage (the one we use most)
5. Status — monitor system health

### Drilling into a location
To drill into mole's sub-menus (e.g. selecting option 1 inside Analyze),
add more `sleep + echo` pairs with the target option number.
Exit with `echo q` or Ctrl-D.

## macOS Disk Space Hot Spots

When `mole analyze` shows the overview, these are the usual suspects:

| Location | What | Typical Size |
|---|---|---|
| `~/Library/Caches/` | App caches (browsers, dev tools) | 500MB–2GB |
| `~/Library/Containers/` | Sandboxed app data | Varies wildly |
| `~/.cache/` | CLI tool caches (HF, mole, opencode) | 1–5GB |
| `~/.local/share/` | CLI tool state (opencode, claude) | 500MB–1.5GB |
| `~/Library/Caches/ms-playwright/` | Browser automation browsers | 500–700MB |
| `~/.cache/huggingface/hub/` | HuggingFace model downloads | 0–10GB |
| `~/Library/Developer/` | Xcode derived data, simulators | 5–30GB |
| `~/go/`, `~/.cargo/`, `~/.rustup/` | Language toolchains | 1–5GB each |
| pip cache | `pip cache info` / `pip cache purge` | 100–500MB |
| Homebrew cache | `$(brew --cache)` | 50–200MB |
| `~/.Trash` | Trash | Variable |

### Quick probe commands

```bash
# Top-level overview
du -sh ~/Library/Caches ~/Library/Containers ~/.cache ~/.local ~/Library/Developer 2>/dev/null

# Drill into biggest directory
du -sh ~/.cache/*/ 2>/dev/null | sort -rh | head -10

# Check specific tool caches
du -sh ~/.cache/huggingface/hub/models--*/ 2>/dev/null | sort -rh
du -sh ~/Library/Containers/*/ 2>/dev/null | sort -rh | head -10
```

## Container Cleanup Pitfalls

macOS protects Containers at the top level — `rm -rf ~/Library/Containers/com.app.id`
will fail with "Operation not permitted". Workaround:

```bash
# ✅ Delete contents, not the container shell
rm -rf ~/Library/Containers/com.app.id/Data/Documents/Models/
rm -f ~/Library/Containers/com.app.id/Data/Documents/*.sqlite3*
```

The container shell stays (36KB), but the heavy data is gone.
If the app is uninstalled via Finder/Launchpad, the container goes too.

## AI Image Gen Model Locations

If the user tested local Stable Diffusion / AI image tools:

| App | Model Path | Notes |
|---|---|---|
| Draw Things | `~/Library/Containers/com.liuliu.draw-things/Data/Documents/Models/` | Flux, SDXL, CLIP, VAE, LoRA — can be 10–25GB |
| ComfyUI | `~/Library/Application Support/ComfyUI/models/` or custom | Check `extra_model_paths.yaml` |
| Stable Diffusion (A1111/Forge) | `~/stable-diffusion-webui/models/` | Usually not on macOS |

## HuggingFace Cache

```bash
# See what's cached
du -sh ~/.cache/huggingface/hub/models--*/ 2>/dev/null | sort -rh

# Nuke everything
rm -rf ~/.cache/huggingface/hub/

# Nuke specific model
rm -rf ~/.cache/huggingface/hub/models--org--model-name/
```

## Post-Cleanup Verification

Always verify with `df -h /` after cleanup to confirm space reclaimed.
Report before/after numbers to the user.
