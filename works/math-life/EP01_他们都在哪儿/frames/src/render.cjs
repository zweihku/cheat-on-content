// 把 frames.html 里的每个 <section class="frame"> 渲染成 1080×1920 的 JPG，输出到 ../
//
// 用法：
//   npm i playwright && npx playwright install chromium
//   node render.cjs
//
// 字体默认从 jsDelivr 加载（fontsource）。离线渲染时，把 @fontsource 包装到本地，
// 再用 FONTSOURCE_DIR 指过去：
//   npm i @fontsource/noto-serif-sc @fontsource/eb-garamond
//   FONTSOURCE_DIR=./node_modules/@fontsource node render.cjs

const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('playwright');

const here = __dirname;
const outDir = path.resolve(here, '..');
const fontsDir = process.env.FONTSOURCE_DIR;
const only = process.argv.slice(2); // 可选：只渲染指定 id，如 f01 f03

const TYPES = { '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });

  if (fontsDir) {
    await page.route('https://cdn.jsdelivr.net/npm/@fontsource/**', async (route) => {
      const { pathname } = new URL(route.request().url());
      const m = pathname.match(/^\/npm\/@fontsource\/([^@/]+)@[^/]+\/(.+)$/);
      const file = m && path.join(fontsDir, m[1], m[2]);
      if (!file || !fs.existsSync(file)) return route.abort();
      return route.fulfill({
        body: fs.readFileSync(file),
        headers: { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'access-control-allow-origin': '*' },
      });
    });
  }

  await page.goto('file://' + path.join(here, 'frames.html'));
  await page.waitForFunction(() => document.body.dataset.ready === '1');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);

  const frames = await page.$$eval('section.frame', (els) => els.map((e) => ({ id: e.id, name: e.dataset.name })));
  for (const { id, name } of frames) {
    if (only.length && !only.includes(id)) continue;
    const file = path.join(outDir, `${id}-${name}.jpg`);
    await page.locator('#' + id).screenshot({ path: file, type: 'jpeg', quality: 90 });
    console.log('wrote', path.relative(process.cwd(), file));
  }

  const missing = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'error').map((f) => f.family));
  if (missing.length) console.warn('font load errors:', [...new Set(missing)].join(', '));
  await browser.close();
})();
