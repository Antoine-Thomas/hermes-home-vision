/**
 * QA Script Template — WordPress Theme Headless Testing
 * =====================================================
 * Adaptable puppeteer-core script for headless Chrome theme QA.
 *
 * Usage: node tools/qa.js
 * Requires: npm install puppeteer-core
 *
 * Customize:
 *   - CHROME_PATH (Windows / Mac / Linux)
 *   - BASE_URL (your dev URL)
 *   - VIEWPORTS array
 *   - DOM_CHECKS (page.evaluate selector queries)
 *   - THEME_ROOT (output directory)
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

// === CONFIGURATION ===
const THEME_ROOT = path.resolve(__dirname, '..');
const CHROME_PATH = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const BASE_URL = 'https://yoursite.local';
const TIMESTAMP = Date.now();

const VIEWPORTS = [
  { name: 'mobile', width: 320, height: 900 },
  { name: 'tablet', width: 834, height: 1112 },
  { name: 'desktop', width: 1440, height: 900 },
];

// Selector checks to run via page.evaluate()
const DOM_CHECKS = `
  const results = {};
  results.cardCount = document.querySelectorAll('article.card').length;
  results.mainVisible = !!document.getElementById('main');
  results.hasJS = typeof window.myAPI !== 'undefined';
  return results;
`;

// === HELPERS ===
function log(msg) {
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`[${ts}] ${msg}`);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// === MAIN ===
async function main() {
  log('QA Script — Starting');

  // Kill stale Chrome
  try {
    require('child_process').execSync(
      process.platform === 'win32'
        ? 'powershell -Command "Get-Process chrome* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"'
        : 'pkill -f "Google Chrome" || true',
      { timeout: 5000 }
    );
    log('Chrome processes killed');
  } catch (e) { /* ignore */ }

  const userDataDir = path.join(THEME_ROOT, 'work-in-progress', `chrome-profile-${TIMESTAMP}`);
  fs.mkdirSync(userDataDir, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    userDataDir,
    args: [
      '--no-sandbox', '--disable-gpu',
      '--ignore-certificate-errors',
      '--disable-dev-shm-usage',
    ],
  });

  const results = [];
  try {
    for (const vp of VIEWPORTS) {
      log(`--- ${vp.name} (${vp.width}×${vp.height}) ---`);
      const page = await browser.newPage();
      await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 1 });

      const url = `${BASE_URL}/?cb=${TIMESTAMP}`;
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
      await sleep(900); // wait for JS execution

      const dom = await page.evaluate(DOM_CHECKS);
      log(`  DOM: cards=${dom.cardCount} visible=${dom.mainVisible} js=${dom.hasJS}`);

      const ssPath = path.join(THEME_ROOT, `screenshot-${vp.name}.png`);
      await page.screenshot({ path: ssPath, fullPage: false });
      log(`  Screenshot: ${ssPath} (${fs.statSync(ssPath).size} bytes)`);

      const domContent = await page.content();
      const domPath = path.join(THEME_ROOT, 'work-in-progress', `dom-${vp.name}.html`);
      fs.writeFileSync(domPath, domContent, 'utf-8');
      log(`  DOM dump: ${domPath} (${fs.statSync(domPath).size} bytes)`);

      results.push({ viewport: vp.name, dom, screenshot: ssPath, domDump: domPath });
      await page.close();
      await sleep(300);
    }
  } finally {
    await browser.close();
    log('Browser closed');
  }

  const resultsPath = path.join(THEME_ROOT, 'work-in-progress', 'qa-results.json');
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf-8');
  log(`Results saved: ${resultsPath}`);
  log('QA Script — Done');
}

main().catch(err => { console.error('FATAL:', err.message); process.exit(1); });
