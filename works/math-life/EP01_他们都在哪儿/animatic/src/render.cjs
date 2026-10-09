// 把 animatic.html 逐帧渲染成视频。
//
// 用法（先 python3 timing.py 生成时间轴，可选 python3 sound.py 生成临时配乐）：
//   npm i playwright && npx playwright install chromium
//   node render.cjs                      整片：../EP01_clean.mp4（无字幕、无声）+ ../EP01_preview.mp4（字幕 + 临时配乐）
//   node render.cjs --stills 3,20,60     只截这几个时间点的静帧，存到 --out 目录（默认 ./stills）
//   node render.cjs --start 40 --end 75  只渲一段，方便检查
//
// 离线渲染字体：FONTSOURCE_DIR=./node_modules/@fontsource node render.cjs（见 frames/src/render.cjs 的说明）

const path = require('node:path');
const fs = require('node:fs');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]);
  return acc;
}, []));
const here = __dirname;
const outDir = path.resolve(here, '..');
const FPS = Number(args.fps || 30);
const fontsDir = process.env.FONTSOURCE_DIR;
const TYPES = { '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };

function ffmpeg(outFile) {
  const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outFile], { stdio: ['pipe', 'inherit', 'inherit'] });
  p.done = new Promise((res, rej) => p.on('close', (code) => (code === 0 ? res() : rej(new Error('ffmpeg exited ' + code)))));
  return p;
}
const write = (p, buf) => new Promise((res) => (p.stdin.write(buf) ? res() : p.stdin.once('drain', res)));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  if (fontsDir) {
    await page.route('https://cdn.jsdelivr.net/npm/@fontsource/**', (route) => {
      const m = new URL(route.request().url()).pathname.match(/^\/npm\/@fontsource\/([^@/]+)@[^/]+\/(.+)$/);
      const file = m && path.join(fontsDir, m[1], m[2]);
      if (!file || !fs.existsSync(file)) return route.abort();
      return route.fulfill({ body: fs.readFileSync(file), headers: { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream', 'access-control-allow-origin': '*' } });
    });
  }
  await page.goto('file://' + path.join(here, 'animatic.html'));
  await page.waitForFunction(() => document.body.dataset.ready === '1');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
  const total = await page.evaluate(() => window.TOTAL);
  const shot = () => page.screenshot({ type: 'jpeg', quality: 92 });

  if (args.stills) {
    const dir = path.resolve(args.out || path.join(here, 'stills'));
    fs.mkdirSync(dir, { recursive: true });
    for (const s of String(args.stills).split(',').map(Number)) {
      await page.evaluate((t) => { window.setSubs(true); window.seek(t); }, s);
      fs.writeFileSync(path.join(dir, `t${s.toFixed(1).padStart(6, '0')}.jpg`), await shot());
      console.log('still', s);
    }
    await browser.close();
    return;
  }

  const t0 = Number(args.start || 0), t1 = Math.min(Number(args.end || total), total);
  const tag = args.start || args.end ? `_${t0}-${t1}` : '';
  const cleanFile = path.join(outDir, `EP01_clean${tag}.mp4`);
  const subsFile = path.join(outDir, `.EP01_subs${tag}.mp4`);
  const clean = ffmpeg(cleanFile), subs = ffmpeg(subsFile);
  const n = Math.round((t1 - t0) * FPS), began = Date.now();
  for (let i = 0; i < n; i++) {
    const t = t0 + i / FPS;
    const hasSub = await page.evaluate((t) => { window.setSubs(false); window.seek(t); return !!window.subAt(t); }, t);
    const a = await shot();
    await write(clean, a);
    if (hasSub) { await page.evaluate(() => window.setSubs(true)); await write(subs, await shot()); }
    else await write(subs, a);
    if (i % 300 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - began) / 1000).toFixed(0)}s`);
  }
  clean.stdin.end(); subs.stdin.end();
  await Promise.all([clean.done, subs.done]);
  await browser.close();

  const wav = path.join(outDir, 'temp_audio.wav'), preview = path.join(outDir, `EP01_preview${tag}.mp4`);
  const mux = fs.existsSync(wav)
    ? ['-y', '-loglevel', 'error', '-i', subsFile, '-ss', String(t0), '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', preview]
    : ['-y', '-loglevel', 'error', '-i', subsFile, '-c', 'copy', preview];
  await new Promise((res, rej) => spawn('ffmpeg', mux, { stdio: 'inherit' }).on('close', (c) => (c === 0 ? res() : rej(new Error('mux failed')))));
  fs.unlinkSync(subsFile);
  console.log('wrote', path.relative(process.cwd(), cleanFile), 'and', path.relative(process.cwd(), preview), `in ${((Date.now() - began) / 1000).toFixed(0)}s`);
})();
