---
name: html-canvas-to-video
description: "Convert HTML/Canvas animations to video files via headless browser capture. Supports alpha channel (green screen + chromakey), MP4, and PNG sequences."
tags: [video, html, canvas, animation, playwright, ffmpeg, alpha, projection, theater]
---

# HTML Canvas Animation → Video

Capture browser-rendered HTML/Canvas animations into video files using Playwright headless + ffmpeg.

## When to Use

- User has an `.html` file with `<canvas>` or CSS animation and wants a video output
- Need alpha channel (transparency) in the output video
- Converting procedural/generative HTML art to distributable video format
- Theater projection design: HTML animations → projection-ready video

## Prerequisites

```bash
# Playwright (Node.js)
cd /tmp && mkdir -p pw_capture && cd pw_capture && npm init -y && npm install playwright

# ffmpeg with chromakey support
ffmpeg -filters 2>/dev/null | grep chromakey
```

## Workflow A: Green Screen + Alpha (Recommended for Transparency)

Best when the output needs alpha channel for compositing.

### Step 1: Check if HTML has built-in recording

Many theater projection HTML files already include a recording panel.
Look for `rec-panel`, `recBtn`, `captureStream`, `MediaRecorder` in the HTML.
If it has green screen recording (`recordingMode` + `#00FF00` background), use it directly.
If not, modify the HTML to add transparent/green background in recording mode.

### Step 2: Playwright capture script

See `templates/capture_alpha.js` for the full Playwright capture + ffmpeg template script.

Key mechanics:
1. Launch headless Chromium: `chromium.launch({ headless: true, args: ['--no-sandbox', '--use-gl=swiftshader'] })`
2. Set viewport to target resolution (usually 1920x1080)
3. Navigate to `file://` URL of the HTML
4. Trigger recording (e.g., press 'R' for panel, click record button)
5. Listen for `page.waitForEvent('download')` to catch the WebM output
6. Save the download, then run ffmpeg chromakey

### Step 3: ffmpeg chromakey

VP9 with alpha (slow but good quality):

```bash
ffmpeg -y -i input_greenscreen.webm \
  -vf "chromakey=0x00FF00:0.15:0.05" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 \
  -b:v 20M output_alpha.webm
```

ProRes 4444 (faster, industry standard for video production):

```bash
ffmpeg -y -i input_greenscreen.webm \
  -vf "chromakey=0x00FF00:0.15:0.05" \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le \
  output_alpha.mov
```

## Workflow B: Standard Video (No Alpha)

For animations where the background is part of the design (no transparency needed).

Same Playwright capture, but ffmpeg without chromakey:

```bash
ffmpeg -y -i input.webm -c:v libx264 -pix_fmt yuv420p output.mp4
```

## Workflow C: Frame-by-Frame PNG → ProRes 4444 Alpha (RECOMMENDED for Alpha)

**This is the best approach for professional alpha output.** Despite the name, it is NOT slow — the capture runs at ~60fps and ProRes encoding at ~1.1x. Total time: ~5-6 minutes for a 5-minute video (vs 25+ minutes for VP9 alpha).

Best for: Resolume Arena projection overlay, video production with alpha compositing.

### Step 1: Playwright injection approach

Instead of modifying the HTML file, inject modifications via Playwright:

```javascript
// Before page loads: add preserveDrawingBuffer
await page.addInitScript(() => {
  const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, attrs) {
    if (type === '2d') { attrs = attrs || {}; attrs.preserveDrawingBuffer = true; }
    return orig.call(this, type, attrs);
  };
});

// After page loads: inject alpha-mode logic
await page.evaluate(() => {
  window.recordingMode = true;
  const canvas = document.getElementById('rainCanvas');
  canvas.width = 1920; canvas.height = 1080;
  window.W = 1920; window.H = 1080;
  // Reinit particles, cancel requestAnimationFrame loop
  // Expose window._stepFrame() and window._getFramePNG()
});
```

Key: override `requestAnimationFrame` to no-op so the auto-loop stops, then step manually.

### Step 2: Frame capture loop

```javascript
for (let i = 0; i < TOTAL_FRAMES; i++) {
  await page.evaluate(() => window._stepFrame());
  const b64 = await page.evaluate(() => window._getFramePNG());
  fs.writeFileSync(`frame_${String(i).padStart(5,'0')}.png`, Buffer.from(b64, 'base64'));
}
```

### Step 3: Compile to ProRes 4444

```bash
ffmpeg -y -framerate 30 \
  -i frame_%05d.png \
  -c:v prores_ks -profile:v 4444 \
  -pix_fmt yuva444p10le -vendor apl0 \
  output_alpha.mov
```

Performance (tested): capture ~60fps, ProRes encode ~1.1x speed. Total ~5-6 min for 5-min video.

### Step 4: Clean up frame sequence

```bash
rm -rf *_frames/  # Can be 5+ GB for 9000 PNG frames
```

## Workflow D: Frame-by-Frame → H.265 Flat Render (RECOMMENDED for Direct Projection)

When the animation background IS part of the design (no transparency needed) and you want compact output. This is what produced the user's preferred 6-1_fullscreen_h265.mov (198MB vs 4.7GB ProRes).

### Why NOT use Python/OpenCV to re-render?

Python OpenCV renderers work for simple visual effects (lines, circles, basic shapes) but **fail for complex Canvas API features**:
- 4-stop radial gradients with offset centers (big rain drops)
- Quadratic bezier curves (warm streaks)
- HSL color math with dynamic saturation/lightness
- Canvas composite operations

The 6-1 rain animation (simple lines) worked in Python. The 7-1 animation (complex radial gradients for big drops) produced "black holes" and "white holes" due to broken alpha compositing. **Use Playwright frame capture for any HTML with complex Canvas effects** — it renders pixel-perfectly in the browser.

### Same Playwright injection, different encode

Use the same frame capture as Workflow C, but encode to H.265 instead of ProRes:

```bash
ffmpeg -y -framerate 30 \
  -i frame_%05d.png \
  -c:v hevc_videotoolbox \
  -b:v 30M -tag:v hvc1 \
  -pix_fmt yuv420p \
  output_h265.mov
```

On macOS, `hevc_videotoolbox` uses hardware encoding (~6x real-time). On Linux, use `libx265` instead.

File size: ~200-300MB for 5 min 1080p (vs 4.7GB ProRes, vs 198MB for simple content).

### Choosing between output strategies

| Strategy | Format | Size (5min 1080p) | Use case |
|----------|--------|-------------------|----------|
| ProRes 4444 alpha | .mov | ~4.7 GB | Arena overlay compositing |
| H.265 flat | .mov | ~200-300 MB | Direct projection, simpler workflow |
| WebM alpha | .webm | ~100 MB | Web delivery (slow to encode) |

For Resolume Arena: use ProRes 4444 if you need to composite the animation on top of a background image. Use H.265 flat if the animation includes its own background.

## Pitfalls

### preserveDrawingBuffer is REQUIRED for canvas.toDataURL()
Without `preserveDrawingBuffer: true`, `canvas.toDataURL()` returns blank/empty images in headless Chromium. Must be set at `getContext('2d')` time — either in the HTML or via `addInitScript()` injection.

### VP9 alpha encoding is very slow
About 0.2x speed (25 min for 5 min video). For faster output use ProRes 4444 or the PNG→ProRes workflow (Workflow C). The VP9 alpha codec (`libvpx-vp9` with `yuva420p`) is computationally expensive — avoid for production work.

### Green screen WebM not playable on macOS
IINA and QuickTime don't support WebM. Convert to MP4 for preview:
```bash
ffmpeg -y -i input_greenscreen.webm -c:v libx264 -pix_fmt yuv420p -crf 18 preview.mp4
```

### Window frame / opaque elements in overlay videos
When capturing for projection overlay (Resolume Arena, etc.), opaque UI elements (window frames, dark borders) will block the background layer. In alpha mode, either remove these elements or make them transparent. The user decides per-project.

### Node.js stdout buffering in non-TTY
When running Playwright scripts via `terminal(background=true)`, `console.log` output is buffered and invisible.
Use `console.error` for all logging - stderr is unbuffered. Add `2>&1` to the shell command to see it.

### Chromium headless + canvas.captureStream
Works in Playwright headless Chromium. The `--use-gl=swiftshader` flag ensures WebGL/canvas rendering.
Without it, some canvas effects may render as black.

### Python f-string vs JavaScript template literals
When generating JS code from Python, `{}` in JS gets interpreted as Python f-string variables.
Use string concatenation or `json.dumps()` instead of f-strings for JS code blocks:
```python
# WRONG — Python interprets JS template literals as f-string vars
f"if (window._frameNum >= {TOTAL}) return false;"  # TOTAL is Python var, OK
f"const x = `${{i + 1}}/${{TOTAL}}`;"  # BROKEN — {{}} escaping nightmare

# RIGHT — use string concatenation in the JS
"if (window._frameNum >= " + str(TOTAL) + ") return false;"
```

### JS variable scope across page.evaluate boundary
Variables defined in Node.js scope are NOT accessible inside `page.evaluate()`.
Pass dynamic values as parameters:
```python
# WRONG
await page.evaluate(() => { if (window._frameNum >= TOTAL) ... });  # TOTAL undefined in browser

# RIGHT — pass as parameter
await page.evaluate((total) => { if (window._frameNum >= total) ... }, TOTAL)
```

### Frame capture speed varies by HTML complexity
- Simple animations (lines, circles): ~60 fps capture
- Complex animations (radial gradients, bezier curves): ~19 fps capture
- Both are acceptable for 5-minute videos (2-8 min capture time)

### TTY-requiring CLI tools
Tools like `mole` (macOS disk cleanup) need interactive TTY. Workaround with `script`:
```bash
script -q /dev/null bash -c '(echo 4; sleep 1; echo "")' | mole 2>&1 | cat
```

### macOS Container permissions
`rm -rf ~/Library/Containers/<app>` returns "Operation not permitted".
Delete the contents inside first, then the container is mostly empty.

### Large disk consumers on macOS
Before starting video work, check available space with `mole` (option 4: Analyze).
Common hogs: AI art app containers (20GB+), HuggingFace cache, Playwright browser cache.

## Resolume Arena Integration

For theater projection overlay in Arena:
1. Import the ProRes 4444 `.mov` file
2. Add to a Video Layer
3. Set Blend Mode to "Alpha Add" or "Add" depending on effect
4. Place background scene image on a lower layer
5. The alpha channel automatically composites the animation on top
