/**
 * Capture HTML canvas animation → green screen WebM → alpha video
 * Uses console.error for all output (unbuffered in non-TTY mode)
 *
 * Usage: node capture_alpha.js <input.html> [output_dir]
 *
 * Prerequisites: npm install playwright (in current or /tmp/pw_capture)
 * The HTML should have built-in recording (canvas.captureStream + MediaRecorder)
 * that outputs a green screen WebM when recording mode is triggered.
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const INPUT_HTML = process.argv[2];
const OUTPUT_DIR = process.argv[3] || path.dirname(INPUT_HTML);

if (!INPUT_HTML) {
  console.error('Usage: node capture_alpha.js <input.html> [output_dir]');
  process.exit(1);
}

// Use stderr for all logging (unbuffered in non-TTY)
const log = console.error;

(async () => {
  const baseName = path.basename(INPUT_HTML, '.html');
  const webmPath = path.join(OUTPUT_DIR, `${baseName}_greenscreen.webm`);
  const alphaWebmPath = path.join(OUTPUT_DIR, `${baseName}_alpha.webm`);

  log(`\n=== Capturing: ${baseName} ===`);
  log(`HTML:  ${INPUT_HTML}`);
  log(`WebM:  ${webmPath}`);
  log(`Alpha: ${alphaWebmPath}\n`);

  // 1. Launch headless Chromium with SwiftShader for canvas rendering
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--use-gl=swiftshader'],
  });

  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // 2. Load the HTML file
  const fileUrl = `file://${path.resolve(INPUT_HTML)}`;
  log('Loading HTML...');
  await page.goto(fileUrl, { waitUntil: 'networkidle' });

  await page.waitForSelector('#rainCanvas');  // adjust selector to match your canvas id
  await page.waitForTimeout(2000);
  log('Canvas ready.');

  // 3. Set up download handling BEFORE triggering recording
  const downloadPromise = page.waitForEvent('download', { timeout: 600000 });

  // 4. Trigger recording (customize per HTML file)
  //    Common patterns: press 'R' for panel, click '#recBtn'
  log('Opening recording panel...');
  await page.keyboard.press('r');
  await page.waitForTimeout(500);

  log('Starting recording...');
  await page.click('#recBtn');

  // 5. Monitor progress
  const startTime = Date.now();
  const DURATION = 5 * 60 * 1000;  // match RECORD_DURATION in HTML

  const progressInterval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    const pct = Math.min(100, (elapsed / DURATION * 100)).toFixed(0);
    const mins = Math.floor(elapsed / 60000);
    const secs = Math.floor((elapsed % 60000) / 1000);
    log(`  Recording: ${pct}% (${mins}m${String(secs).padStart(2,'0')}s)`);
  }, 10000);

  // 6. Wait for download (triggers after recording stops)
  log('Waiting for recording to complete...');
  const download = await downloadPromise;
  clearInterval(progressInterval);

  log(`Download received: ${download.suggestedFilename()}`);

  await download.saveAs(webmPath);
  log(`Saved: ${webmPath} (${(fs.statSync(webmPath).size / 1024 / 1024).toFixed(1)} MB)`);

  await browser.close();
  log('Browser closed.');

  // 7. ffmpeg chromakey → alpha video
  log(`\n=== Chroma key: ${baseName} ===`);

  const ffmpegCmd = [
    'ffmpeg', '-y',
    '-i', webmPath,
    '-vf', 'chromakey=0x00FF00:0.15:0.05',
    '-c:v', 'libvpx-vp9',
    '-pix_fmt', 'yuva420p',
    '-auto-alt-ref', '0',
    '-b:v', '20M',
    alphaWebmPath,
  ].join(' ');

  log(ffmpegCmd);

  try {
    execSync(ffmpegCmd, { stdio: 'inherit', timeout: 300000 });
    const alphaStats = fs.statSync(alphaWebmPath);
    log(`\n=== DONE ===`);
    log(`Alpha video: ${alphaWebmPath}`);
    log(`Size: ${(alphaStats.size / 1024 / 1024).toFixed(1)} MB`);
  } catch (e) {
    log('ffmpeg failed: ' + e.message);
    process.exit(1);
  }
})();
