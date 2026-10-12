// Render an SVG to PNG with headless Chromium (Playwright).
// Usage: node tools/render.mjs <in.svg> <out.png> [scale]
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const [, , input, output, scaleArg] = process.argv;
const scale = Number(scaleArg || 1);
const svg = readFileSync(resolve(input), 'utf8');
const [, w, h] = svg.match(/viewBox="0 0 (\d+) (\d+)"/);

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({
  viewport: { width: Number(w), height: Number(h) },
  deviceScaleFactor: scale,
});
await page.setContent(
  `<html><body style="margin:0">${svg.replace(/<\?xml[^>]*>/, '')}</body></html>`,
);
await page.locator('svg').screenshot({ path: output });
await browser.close();
