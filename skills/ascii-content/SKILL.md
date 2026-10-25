---
name: ascii-content
description: "ASCII art and video: text banners, cowsay, image-to-ascii, colored ASCII video. Use when: ASCII art, text banner, cowsay, pyfiglet, ASCII video, terminal art."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ASCII, Art, Video, Banners, Creative, Unicode, Text-Art, Animation]
    related_skills: [excalidraw, architecture-diagram]
---

# ASCII Content

Create ASCII art and video content. Multiple tools for different needs — all local or free APIs.

## Section 1: ASCII Art

### Text Banners (pyfiglet)

```bash
pip install pyfiglet --break-system-packages -q
python3 -m pyfiglet "YOUR TEXT" -f slant
python3 -m pyfiglet "TEXT" -f doom -w 80
python3 -m pyfiglet --list_fonts  # 571 fonts
```

**Recommended fonts:** `slant` (clean), `doom` (bold), `big` (readable), `cyberlarge` (cyberpunk)

### Text Banners (asciified API — no install)

```bash
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello+World"
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=Doom"
```

### Cowsay (Message Art)

```bash
cowsay "Hello World"
cowsay -f tux "Linux rules"
cowsay -f dragon "Rawr!"
cowsay -l  # List all 50+ characters
```

### Boxes (Decorative Borders)

```bash
echo "Hello World" | boxes -d stone
echo "Hello World" | boxes -d parchment
boxes -l  # List all 70+ designs
```

### Image to ASCII

```bash
ascii-image-converter image.png -C  # Color output
ascii-image-converter image.png -b   # Braille characters
jp2a --width=80 image.jpg           # Lightweight JPEG only
```

### QR Codes as ASCII

```bash
curl -s "qrenco.de/Hello+World"
```

### Weather as ASCII

```bash
curl -s "wttr.in/London"
```

## Section 2: ASCII Video

Production pipeline for ASCII art video — converts video/audio/images/generative input into colored ASCII character video output (MP4, GIF, image sequence).

### Modes

| Mode | Input | Output |
|------|-------|--------|
| **Video-to-ASCII** | Video file | ASCII recreation |
| **Audio-reactive** | Audio file | Generative visuals |
| **Generative** | None | Procedural animation |
| **Hybrid** | Video + audio | ASCII + reactive overlays |
| **Lyrics/text** | Audio + text | Timed text with effects |

### Stack

Single self-contained Python script per project. No GPU required.

| Layer | Tool | Purpose |
|-------|------|---------|
| Core | Python 3.10+, NumPy | Math, array ops |
| Signal | SciPy | FFT, peak detection |
| Imaging | Pillow | Font rasterization, frame decoding |
| Video I/O | ffmpeg | Decode input, encode output |

### Pipeline

```
INPUT → ANALYZE → SCENE_FN → TONEMAP → SHADE → ENCODE
```

### Creative Direction

- **Character palette:** Density ramps, block elements, symbols, scripts
- **Color strategy:** HSV, OKLAB/OKLCH, discrete RGB palettes
- **Background texture:** Sine fields, fBM noise, voronoi, reaction-diffusion
- **Shader mood:** Retro CRT, clean modern, glitch art, cinematic

### Critical: Brightness

ASCII on black is inherently dark. **Never use `canvas * N` multipliers** — use adaptive tonemap:

```python
def tonemap(canvas, gamma=0.75):
    f = canvas.astype(np.float32)
    lo, hi = np.percentile(f[::4, ::4], [1, 99.5])
    if hi - lo < 10: hi = lo + 10
    f = np.clip((f - lo) / (hi - lo), 0, 1) ** gamma
    return (f * 255).astype(np.uint8)
```

## Decision Flow

1. **Text as banner** → pyfiglet or asciified API
2. **Fun message** → cowsay
3. **Decorative border** → boxes
4. **Specific image** → ascii.co.uk or ascii-image-converter
5. **QR code** → qrenco.de
6. **Video** → ASCII video pipeline
7. **Custom/creative** → LLM generation with Unicode palette

## Common Pitfalls

1. **Font compatibility** — not all Unicode chars render in all fonts
2. **macOS Pillow height** — use `font.getmetrics()` not `textbbox()`
3. **ffmpeg deadlock** — never `stderr=subprocess.PIPE` with long-running ffmpeg
4. **Per-scene variation** — never use same config for entire video
5. **First-render excellence** — output must be visually striking without revision
