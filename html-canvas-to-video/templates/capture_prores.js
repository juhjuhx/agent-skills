/**
 * HTML Canvas Animation → ProRes 4444 Alpha (Resolume Arena ready)
 * 
 * Usage: node capture_prores.js <input.html> [output_dir]
 * 
 * How it works:
 * 1. Opens HTML in Playwright headless Chromium (1920x1080)
 * 2. Injects transparent background + manual frame stepping
 * 3. Captures 9000 frames (5 min @ 30fps) as PNG
 * 4. Compiles to ProRes 4444 with alpha via ffmpeg
 * 
 * Requirements: npm install playwright (in /tmp/pw_capture or local)
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const INPUT_HTML = process.argv[2];
const OUTPUT_DIR = process.argv[3] || path.dirname(INPUT_HTML);

if (!INPUT_HTML) {
  console.error('Usage: node capture_prores.js <input.html> [output_dir]');
  process.exit(1);
}

const log = console.error; // stderr is unbuffered in non-TTY

(async () => {
  const baseName = path.basename(INPUT_HTML, '.html');
  const framesDir = path.join(OUTPUT_DIR, `${baseName}_frames`);
  const outputPath = path.join(OUTPUT_DIR, `${baseName}_alpha.mov`);

  log(`\n=== ${baseName} ===`);
  log(`Output: ${outputPath}\n`);

  if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--use-gl=swiftshader'],
  });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // CRITICAL: preserveDrawingBuffer must be set before getContext
  await page.addInitScript(() => {
    const orig = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, attrs) {
      if (type === '2d') { attrs = attrs || {}; attrs.preserveDrawingBuffer = true; }
      return orig.call(this, type, attrs);
    };
  });

  await page.goto(`file://${path.resolve(INPUT_HTML)}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('#rainCanvas');
  await page.waitForTimeout(1000);

  // Inject alpha-mode: transparent background, no opaque UI elements
  // ADAPT THIS for your specific HTML's animation functions
  await page.evaluate(() => {
    window.recordingMode = true;
    const canvas = document.getElementById('rainCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 1920; canvas.height = 1080;
    window.W = 1920; window.H = 1080;

    // Reinit (adapt function names to your HTML)
    if (typeof calcFrame === 'function') calcFrame();
    if (typeof initDrops === 'function') initDrops();
    if (typeof initCityLights === 'function') initCityLights();

    window._ctx = ctx;
    window._canvas = canvas;
    window._frameNum = 0;
    window._targetFrames = 30 * 60 * 5; // 30fps x 5min

    // ADAPT: copy your HTML's animation logic here, but with:
    // - ctx.clearRect() instead of fillRect for background (transparent)
    // - Skip opaque frame elements
    window._stepFrame = () => {
      if (window._frameNum >= window._targetFrames) return false;
      const time = window._frameNum * (1000 / 30);
      const dt = 1000 / 30;
      window._frameNum++;
      ctx.clearRect(0, 0, window.W, window.H);
      // Call your animation draw functions here
      if (typeof drawCityLights === 'function') drawCityLights(time);
      if (typeof drawLightning === 'function') drawLightning();
      if (typeof updateWaterStreaks === 'function') { updateWaterStreaks(time); drawWaterStreaks(); }
      if (typeof updateDrops === 'function') { updateDrops(time); drawDrops(); }
      return true;
    };

    window._getFramePNG = () => canvas.toDataURL('image/png').split(',')[1];

    // Stop auto-loop
    requestAnimationFrame = () => {};
  });

  // Capture loop
  const TOTAL_FRAMES = 9000;
  const startTime = Date.now();
  log(`Capturing ${TOTAL_FRAMES} frames...`);

  for (let i = 0; i < TOTAL_FRAMES; i++) {
    const hasMore = await page.evaluate(() => window._stepFrame());
    if (!hasMore) { log(`Ended at frame ${i}`); break; }
    const b64 = await page.evaluate(() => window._getFramePNG());
    fs.writeFileSync(path.join(framesDir, `frame_${String(i).padStart(5, '0')}.png`), Buffer.from(b64, 'base64'));
    if ((i + 1) % 500 === 0) {
      const elapsed = (Date.now() - startTime) / 1000;
      log(`  ${i + 1}/${TOTAL_FRAMES} (${(i + 1) / TOTAL_FRAMES * 100 | 0}%) — ${(i + 1) / elapsed | 0} fps`);
    }
  }
  log(`Capture: ${((Date.now() - startTime) / 1000).toFixed(0)}s`);

  await browser.close();

  // ProRes 4444 encode
  log(`\nEncoding ProRes 4444...`);
  execSync([
    'ffmpeg', '-y', '-framerate', '30',
    '-i', path.join(framesDir, 'frame_%05d.png'),
    '-c:v', 'prores_ks', '-profile:v', '4444',
    '-pix_fmt', 'yuva444p10le', '-vendor', 'apl0',
    outputPath,
  ].join(' '), { stdio: 'inherit', timeout: 600000 });

  const size = (fs.statSync(outputPath).size / 1024 / 1024).toFixed(0);
  log(`\nDone: ${outputPath} (${size} MB)`);
  log(`Frames dir: ${framesDir} (delete to save space)`);
})();
