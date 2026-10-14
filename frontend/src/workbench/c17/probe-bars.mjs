// The bar-chart probe of case C17 (U12-W): visits every group and every sub-tab of the case in both variants, both
// languages and both themes, in the gate's wide font, and fails when a horizontal or vertical bar chart scrolls inside
// its own drawing (a `.caos-bars` box whose content is taller than the box). The gate measures the same thing at its own
// sizes; this probe walks every state of the new case on purpose, so a bar chart in a sub-tab nobody opens cannot hide.
// Usage (from frontend/, with the built site served, e.g. `npm run preview -- --port 4177`):
//   PLAYWRIGHT_BROWSERS_PATH=E:/_Temp/ms-playwright node src/workbench/c17/probe-bars.mjs --url http://localhost:4177 [--size 1280x800] [--case C17]
// Exit code 0: no bar chart scrolls and at least one was visited in every state that draws one; 1: one scrolls or none was found.
import { chromium } from 'playwright';

const arg = (name, fallback) => {
  const at = process.argv.indexOf(`--${name}`);
  return at > 0 ? process.argv[at + 1] : fallback;
};
const base = arg('url', 'http://localhost:4177').replace(/\/$/, '');
const caseId = arg('case', 'C17');
const [width, height] = arg('size', '1280x800').split('x').map(Number);
// the gate's wide-font pass replaces --font-sans with a wider face (Linux fonts are wider than the Windows ones)
const WIDE = "'DejaVu Sans', Verdana, sans-serif";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height } });
const problems = [];
const rows = [];
page.on('pageerror', (e) => problems.push(`page error: ${e}`));
page.on('console', (m) => {
  if (m.type() === 'error') problems.push(`console error: ${m.text()}`);
});

const settle = () => page.waitForTimeout(350);
const click = async (locator) => {
  await locator.click();
  await settle();
};

/** Every bar chart now on the page: its box, whether it scrolls, and whether it has been drawn. */
const bars = () =>
  page.$$eval('.caos-bars', (els) =>
    els.map((el) => ({ client: el.clientHeight, scroll: el.scrollHeight, drawn: el.getAttribute('data-drawn'), rows: el.querySelectorAll('[data-bar]').length })),
  );

async function measure(label) {
  await settle();
  const found = await bars();
  for (const b of found) {
    const scrolls = b.scroll > b.client + 1;
    rows.push({ label, ...b, scrolls });
    if (scrolls) problems.push(`${label}: a bar chart scrolls inside its drawing (${b.scroll}px of content in ${b.client}px, ${b.rows} bars)`);
    if (b.drawn !== '1') problems.push(`${label}: a bar chart was not drawn`);
  }
  return found.length;
}

async function walkViews(label) {
  // the tab lists of the case: the rail's sections (the controls), the groups (the longest list) and the sub-tabs of the
  // open group; they are told apart by what they hold, since their names change with the language
  const lists = async () => {
    const all = page.locator('[role=tablist]');
    const n = await all.count();
    const found = [];
    for (let i = 0; i < n; i++) found.push({ at: i, name: (await all.nth(i).getAttribute('aria-label')) ?? '', tabs: await all.nth(i).getByRole('tab').count() });
    const rail = found.filter((f) => /^(controls|controles)$/i.test(f.name));
    const rest = found.filter((f) => !rail.includes(f));
    const groups = rest.reduce((m, f) => (f.tabs > (m?.tabs ?? 0) ? f : m), null);
    return { all, groups, subs: rest.filter((f) => f !== groups) };
  };
  const first = await lists();
  const groupTabs = first.all.nth(first.groups.at).getByRole('tab');
  const n = await groupTabs.count();
  for (let i = 0; i < n; i++) {
    const group = groupTabs.nth(i);
    const gname = (await group.textContent())?.trim() ?? String(i);
    await click(group);
    const now = await lists();
    if (now.subs.length === 0) {
      await measure(`${label} / ${gname}`);
      continue;
    }
    const tabs = now.all.nth(now.subs[0].at).getByRole('tab');
    const k = await tabs.count();
    for (let j = 0; j < k; j++) {
      const t = tabs.nth(j);
      await click(t);
      await measure(`${label} / ${gname} / ${(await t.textContent())?.trim()}`);
    }
  }
}

for (const lang of ['en', 'es']) {
  for (const theme of ['light', 'dark']) {
    await page.goto(`${base}/app/?case=${caseId}`, { waitUntil: 'networkidle' });
    await page.evaluate((font) => document.documentElement.style.setProperty('--font-sans', font), WIDE);
    // the language is remembered between loads and the theme is not: toggle only what differs from the one asked for
    const state = () => page.evaluate(() => ({ lang: document.documentElement.lang, theme: document.documentElement.getAttribute('data-theme') }));
    if ((await state()).lang !== lang) await click(page.locator('button.icon-btn[aria-label*="anguage" i], button.icon-btn[aria-label*="idioma" i]').first());
    if ((await state()).theme !== theme) await click(page.locator('button.icon-btn').last());
    const now = await state();
    if (now.lang !== lang || now.theme !== theme) problems.push(`could not set ${lang} ${theme}: the page is ${now.lang} ${now.theme}`);
    await page.evaluate((font) => document.documentElement.style.setProperty('--font-sans', font), WIDE);
    const variants = page.locator('[data-control=variant] button, [data-control=variant] .chip');
    const nv = await variants.count();
    for (let v = 0; v < Math.max(nv, 1); v++) {
      if (nv > 0) await click(variants.nth(v));
      await walkViews(`${lang} ${theme} ${width}x${height} variant ${v + 1}`);
    }
  }
}
await browser.close();

const visited = rows.length;
const wrong = rows.filter((r) => r.scrolls).length;
console.log(`[probe-bars] ${visited} bar charts visited in ${width}x${height}, ${wrong} scroll inside their drawing`);
for (const r of rows) console.log(`  ${r.scrolls ? 'SCROLLS' : 'ok     '} ${r.label}: ${r.rows} bars, ${r.scroll}px in ${r.client}px`);
if (visited === 0) problems.push('no bar chart was found: the probe visited nothing');
for (const p of [...new Set(problems)]) console.error(`[probe-bars] ${p}`);
process.exit(problems.length ? 1 : 0);
