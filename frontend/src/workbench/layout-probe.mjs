// The layout probe of U16-F12a (the R4 ruling 8), extended by U16-F13a (R5): opens the views the capture reviews named, at 1280 x 800
// and 390 x 844, in both languages, and measures in the browser what a reader sees, never what the code assumes:
//   - a box that scrolls with content below its visible bottom shows a cue (layout.ts marks it, contraste.css draws the band),
//     and when it holds a table the cue's count equals the rows a reader cannot read, which this probe counts on its own: from
//     each row's text glyphs and the band's drawn geometry (its height, where it sits, the stop of its gradient), never with
//     layout.ts's rule (R5 c06 B1: the probe computed the cue's own rule, so a count one too many passed);
//   - the band sits at the box's real bottom, so no line shows under it (R5 c27 n5);
//   - a box of a card that scrolls but is not one layout.ts marks is a finding (R5 c27 M1: the C21 evidence card scrolled with no cue);
//   - a box with content past its right edge fades that edge;
//   - no card body hides content (the shell's filling body clips what overflows it: the readout and the note of R4 c01 M2, the
//     transfer bars of R5 c03 M2);
//   - a card's note (the shell's box under the drawing) shows whole, or scrolls with the cue;
//   - every plot of a filling drawing keeps its floor (its holder's `data-plot-floor`, else 9rem), with or without a holder (R5 c05
//     M1, M3: no C04 drawing had one), and no bar chart scrolls inside itself (R4 c01 M1, M2, c11 M1, c23 M1, c26 M1, c27 M1).
// Usage (from frontend/, with the built site served, e.g. `npm run preview -- --port 4600`):
//   PLAYWRIGHT_BROWSERS_PATH=<temp root>/ms-playwright node src/workbench/layout-probe.mjs --url http://localhost:4600
//     [--sizes 1280x800,390x844] [--langs es,en] [--only C01,C09] [--font wide] [--walk true [--variants all]] [--json <file>]
// Exit code 0: every view measured clean; 1: a finding (each printed), or a view that could not be opened.
import { writeFileSync } from 'node:fs';
import { chromium } from 'playwright';

const arg = (name, fallback) => {
  const at = process.argv.indexOf(`--${name}`);
  return at > 0 ? process.argv[at + 1] : fallback;
};
const base = arg('url', 'http://localhost:4600').replace(/\/$/, '');
const sizes = arg('sizes', '1280x800,390x844').split(',').map((s) => s.split('x').map(Number));
const langs = arg('langs', 'es,en').split(',');
const only = arg('only', '') ? new Set(arg('only', '').split(',')) : null;
const jsonOut = arg('json', '');
// `--walk true`: every group and sub-view of every case's default variant instead of TARGETS (a sweep for regressions)
const walk = arg('walk', '') === 'true';
// `--variants all` with `--walk true`: every variant of every case, not only the default
const allVariants = arg('variants', '') === 'all';
// `--font wide`: the gate's wide-font pass (Linux fonts are wider than the Windows ones), which wraps more lines
const wide = arg('font', '') === 'wide';

/** The views of the R4 rows this unit owns, by case, variant (null: the default), group tab and sub-tab (null: none). */
export const TARGETS = [
  // C01: the scorecard's distribution (c01 M1, c02 M1), the variants table and its chart (c01 M2, c02 M2), the pipeline
  // table (c01 M3, n1; c02 m1), the CSI table (c01 n10), the EBM panels (n8) and the German twin's model views (M4)
  ['C01', 'holdout', 'model', 'scorecard'],
  ['C01', 'german-twin', 'model', 'scorecard'],
  ['C01', 'holdout', 'model', 'ebm'],
  ['C01', 'holdout', 'compare', null],
  ['C01', 'drift-moderate', 'compare', null],
  ['C01', 'drift-severe', 'compare', null],
  ['C01', 'holdout', 'impact', 'decision'],
  ['C01', 'german-twin', 'impact', 'decision'],
  ['C01', 'holdout', 'validation', 'stability'],
  ['C01', 'holdout', 'findings', null],
  // the shared boxes and floors of the other cases' rows (ruling 8)
  ['C04', 'sp', 'impact', 'capital'],
  ['C04', 'thin', 'validation', 'coverage'],
  ['C04', 'withdrawals', 'validation', 'tests'],
  ['C07', 'base', 'comparison', 'segments'],
  ['C09', null, 'ccf', 'by-design'],
  ['C10', 'other-consumer', 'fit', 'backtest'],
  ['C10', 'other-consumer', 'capital', 'rungs'],
  ['C10', 'grid-40', 'compare', null],
  ['C16', 'list-adverse', 'compare', null],
  ['C16', 'reverse-stress', 'compare', null],
  ['C18', 'ngfs-delayed-transition', 'capital', 'stack'],
  ['C21', null, 'rates', 'four-fifths'],
  ['C22', null, 'validation', 'p-values'],
  ['C22', 'other-families', 'validation', 'power'],
  // R5 (U16-F13a): the cue's count (c06 B1, c22 m2, c01 n3, c05 n5), the band's gap (c27 n5), the C21 evidence box (c27 M1), the
  // C04 drawings with no floor holder (c05 M1, M3) and the C02 transfer bars and split (c03 M1, M2)
  ['C01', 'holdout', 'model', 'penalised'],
  ['C01', 'german-twin', 'model', 'ladder'],
  ['C02', 'h1', 'horizons', 'transfer'],
  ['C02', 'pooled', 'horizons', 'transfer'],
  ['C02', 'h1', 'context', null],
  ['C04', null, 'validation', 'pd-by-grade'],
  ['C04', null, 'validation', 'lifetime'],
  ['C04', null, 'validation', 'semesters'],
  ['C04', 'sp', 'validation', 'by-year'],
  ['C04', 'sp', 'validation', 'tests'],
  ['C04', 'sp', 'validation', 'lifetime'],
  ['C04', 'thin', 'validation', 'overlap'],
  ['C04', 'markov', 'model', null],
  ['C04', 'markov', 'validation', 'estimators'],
  ['C04', 'markov', 'validation', 'zeros'],
  ['C04', 'momentum', 'validation', 'power'],
  ['C04', 'momentum', 'validation', 'projection'],
  ['C16', 'list-adverse', 'sensitivity', 'share'],
  ['C16', 'list-extreme', 'survival', 'stack'],
  ['C21', null, 'findings', null],
].map(([caseId, variant, group, sub]) => ({ caseId, variant, group, sub }));

const settleMs = 900;

/** The boxes layout.ts marks (layout.ts SCROLL_BOXES; a vitest holds the two lists equal). */
export const BOXES =
  '.ct-stack-table, .ct-stack-rest, .ct-stack-fill, .ct-scroll, .ct-fade-scroll, .ct-panels-fill, .ct-c20-bars, .ct-stack[data-block="finding-evidence"], .caos-plot.fill > .caos-plot-note, [data-scroll-box]';

/** The opacity of a band drawn as `linear-gradient(transparent, surface <stop>%)` of `h` px at `y` px under its top. */
export function bandOpacity(y, h, stop) {
  if (y <= 0) return 0;
  const end = h * stop;
  return end <= 0 ? 1 : Math.min(1, y / end);
}

/** Whether a row cannot be read above the cue: the middle of its text glyphs lies under the box's visible bottom, or where the band
 * drawn over it is at least half opaque. `glyphs` is the row's text line, top and bottom (page coordinates). */
export function unreadable(glyphs, band) {
  const mid = (glyphs.top + glyphs.bottom) / 2;
  if (mid >= band.visibleBottom) return true;
  return bandOpacity(mid - band.top, band.height, band.stop) >= 0.5;
}

/** In the page: the measures of every scroll box, card body and plot of the open view. */
const measure = (BOXES) => {
  const PLOTS = '.caos-chart.fill > .caos-chart-plot, .caos-bars-host.fill > .caos-bars';
  const remPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const px = (v) => {
    const m = /^\s*(-?\d+(?:\.\d+)?)(rem|px)\s*$/.exec(v ?? '');
    return m ? (m[2] === 'rem' ? Number(m[1]) * remPx : Number(m[1])) : 0;
  };
  const shown = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && !el.closest('.caos-wb-rail, .sr-only, [hidden]') && (!el.checkVisibility || el.checkVisibility({ checkVisibilityCSS: true }));
  };
  const name = (el) => {
    const card = el.closest('.caos-plot');
    const title = card ? (card.querySelector('h2, h3, h4, .caos-plot-title')?.textContent ?? '').trim().slice(0, 70) : '';
    return `${el.className || el.tagName.toLowerCase()} in "${title}"`;
  };
  const scrolls = (v) => v === 'auto' || v === 'scroll';
  // the text line of a row: the union of its text's glyph boxes (a Range over each text node), not the row's padded box
  const glyphs = (tr) => {
    let top = Infinity;
    let bottom = -Infinity;
    const walker = document.createTreeWalker(tr, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.textContent.trim() || n.parentElement?.closest('.sr-only')) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      for (const r of range.getClientRects()) {
        if (r.height <= 0) continue;
        top = Math.min(top, r.top);
        bottom = Math.max(bottom, r.bottom);
      }
    }
    if (top === Infinity) {
      const r = tr.getBoundingClientRect();
      return { top: r.top, bottom: r.bottom };
    }
    return { top, bottom };
  };
  const opacity = (y, h, stop) => (y <= 0 ? 0 : h * stop <= 0 ? 1 : Math.min(1, y / (h * stop)));
  const out = { boxes: [], bodies: [], plots: [], notes: [], unlisted: [] };
  for (const note of document.querySelectorAll('.caos-plot-note')) {
    if (!shown(note)) continue;
    const after = getComputedStyle(note, '::after');
    const cue = after.content && after.content !== 'none' && after.content !== 'normal' && parseFloat(after.height) > 0;
    out.notes.push({ name: name(note), over: note.scrollHeight - note.clientHeight - note.scrollTop, cue });
  }
  for (const box of document.querySelectorAll(BOXES)) {
    if (!shown(box)) continue;
    const cs = getComputedStyle(box);
    const below = scrolls(cs.overflowY) && box.scrollHeight - box.clientHeight - box.scrollTop > 2;
    const right = scrolls(cs.overflowX) && box.scrollWidth - box.clientWidth - box.scrollLeft > 2;
    const after = getComputedStyle(box, '::after');
    const cue = after.content && after.content !== 'none' && after.content !== 'normal' && parseFloat(after.height) > 0 ? after.content.replace(/^"|"$/g, '') : '';
    const visibleBottom = box.getBoundingClientRect().top + box.clientTop + box.clientHeight;
    // the band as drawn: sticky at the box's bottom less its bottom padding and its own `bottom` offset
    const h = parseFloat(after.height) || 0;
    const stop = Number(/(\d+(?:\.\d+)?)%\s*\)\s*$/.exec(after.backgroundImage ?? '')?.[1] ?? 100) / 100;
    const drawnBottom = visibleBottom - (parseFloat(cs.paddingBottom) || 0) - px(after.bottom);
    const band = { top: drawnBottom - h, height: h, stop, visibleBottom };
    let rows = 0;
    if (below) {
      for (const tr of box.querySelectorAll('tbody > tr')) {
        if (tr.closest('.sr-only') || tr.getBoundingClientRect().height <= 0) continue;
        const g = glyphs(tr);
        const mid = (g.top + g.bottom) / 2;
        if (mid >= visibleBottom || opacity(mid - band.top, band.height, band.stop) >= 0.5) rows += 1;
      }
    }
    const mask = cs.maskImage || cs.webkitMaskImage || 'none';
    out.boxes.push({ name: name(box), below, right, rows, cue, gap: cue ? Math.round(visibleBottom - drawnBottom) : 0, fadeRight: mask !== 'none' && /right|90deg/.test(mask) });
  }
  // a box of a card that scrolls with content below but is not one layout.ts marks (R5 c27 M1)
  for (const el of document.querySelectorAll('.caos-plot *')) {
    if (el.matches(BOXES) || el.matches('.caos-plot-body, .caos-chart-plot, .caos-bars, .caos-plot-note') || !shown(el)) continue;
    const cs = getComputedStyle(el);
    if (!scrolls(cs.overflowY) || el.clientHeight === 0 || el.scrollHeight - el.clientHeight - el.scrollTop <= 2) continue;
    out.unlisted.push({ name: name(el), over: el.scrollHeight - el.clientHeight - el.scrollTop });
  }
  for (const body of document.querySelectorAll('.caos-plot.fill > .caos-plot-body')) {
    if (!shown(body)) continue;
    if (getComputedStyle(body).overflowY !== 'hidden') continue;
    // what the body draws, not its scrollHeight, which counts the screen-reader tables; what a scroll box of the body holds scrolls
    const DRAWN = ':scope > *, .caos-chart, .caos-chart-foot, .caos-chart-axis-title, .caos-bars-host, .caos-bars-foot, [data-plot-floor], .ct-stack-chart, .ct-stack-fixed, .ct-stack > *, .ct-panels-fill, table, p';
    const bottom = body.getBoundingClientRect().top + body.clientTop + body.clientHeight;
    let over = 0;
    for (const el of body.querySelectorAll(DRAWN)) {
      if (el.closest('.sr-only')) continue;
      const sb = el.parentElement?.closest(BOXES);
      if (sb && body.contains(sb)) continue;
      const r = el.getBoundingClientRect();
      if (r.height > 0) over = Math.max(over, r.bottom - bottom);
    }
    out.bodies.push({ name: name(body), over: Math.round(over) });
  }
  for (const plot of document.querySelectorAll(PLOTS)) {
    if (!shown(plot) || plot.closest('.ct-c20-bars')) continue;
    const holder = plot.closest('[data-plot-floor]');
    const floor = px(holder ? holder.getAttribute('data-plot-floor') : '9rem') || 9 * remPx;
    const bars = plot.classList.contains('caos-bars');
    out.plots.push({ name: `${bars ? 'bars' : 'plot'} "${(plot.getAttribute('aria-label') ?? '').slice(0, 70)}" in ${name(plot)}`, h: plot.clientHeight, floor, bars, holder: Boolean(holder), scroll: bars ? plot.scrollHeight - plot.clientHeight : 0 });
  }
  return out;
};

const ready = () => {
  if (!document.querySelector('[data-brand]')) return false;
  const shown = (el) => el.getBoundingClientRect().height > 0;
  if ([...document.querySelectorAll('[data-state="loading"]')].some(shown)) return false;
  if ([...document.querySelectorAll('[data-stale="1"]')].some(shown)) return false;
  return true;
};

/** The number a cue states ("3 more rows below", "1 fila más abajo"), or 0 for "more below" with no count. */
export function cueCount(cue) {
  const m = /^(\d+)\s/.exec(cue ?? '');
  return m ? Number(m[1]) : 0;
}

/** The findings of one view's measures. */
export function judge(m) {
  const f = [];
  for (const b of m.boxes) {
    if (b.below && !b.cue) f.push(`${b.name}: content below the box's edge${b.rows ? ` (${b.rows} rows)` : ''} and no cue`);
    // the cue's count is a number of the view: it equals the rows a reader cannot read (R5 ruling 7, c06 B1)
    else if (b.below && cueCount(b.cue) !== b.rows) f.push(`${b.name}: ${b.rows} rows not readable, the cue says "${b.cue}"`);
    if (b.cue && Math.abs(b.gap ?? 0) > 1) f.push(`${b.name}: the cue's band sits ${b.gap}px above the box's edge, a line shows under it`);
    if (b.right && !b.fadeRight) f.push(`${b.name}: content past the right edge and no fade`);
  }
  for (const u of m.unlisted ?? []) f.push(`${u.name}: scrolls ${u.over}px with no cue (a box layout.ts does not mark)`);
  for (const b of m.bodies) if (b.over > 2) f.push(`${b.name}: the card body hides ${b.over}px of its content`);
  for (const n of m.notes ?? []) if (n.over > 2 && !n.cue) f.push(`${n.name}: the card's note is cut (${n.over}px hidden) with no cue`);
  for (const p of m.plots) {
    if (p.h < p.floor - 1) f.push(`${p.name}: plot ${p.h}px under its floor ${Math.round(p.floor)}px${p.holder === false ? ' (no floor holder)' : ''}`);
    if (p.bars && p.scroll > 1) f.push(`${p.name}: the bars scroll inside the drawing (${p.scroll}px more)`);
  }
  return f;
}

/** The variant ids of a case, in the rail's order. */
async function variantsOf(caseId, manifests) {
  if (!manifests.has(caseId)) manifests.set(caseId, await (await fetch(`${base}/data/manifests/${caseId}.json`)).json());
  return manifests.get(caseId).artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id);
}

/** Picks a variant of the open case in the rail (null: the default). */
async function pickVariant(page, caseId, variant, manifests) {
  if (!variant) return;
  const ids = await variantsOf(caseId, manifests);
  const at = ids.indexOf(variant);
  if (at < 0) throw new Error(`no variant ${variant}`);
  await page.locator('[data-control="variant"] [role="radio"]').nth(at).click();
  await page.waitForTimeout(300);
  await page.waitForFunction(ready, null, { timeout: 30000 });
}

/** Every group and sub-view of every case's default variant, or of every variant (`--variants all`), read from the page. */
async function walkTargets(page, manifests) {
  const index = await (await fetch(`${base}/data/manifests/index.json`)).json();
  const out = [];
  for (const c of index.cases ?? []) {
    const caseId = c.case_id;
    if (only && !only.has(caseId)) continue;
    const variants = allVariants ? await variantsOf(caseId, manifests).catch(() => [null]) : [null];
    for (const variant of variants) {
      await page.goto(`${base}/app?case=${caseId}`, { waitUntil: 'load', timeout: 30000 });
      await page.waitForFunction(ready, null, { timeout: 30000 }).catch(() => undefined);
      await pickVariant(page, caseId, variant, manifests).catch(() => undefined);
      const groups = await page.$$eval('[data-case-workbench] .tablist [role="tab"]', (ts) => ts.map((t) => t.getAttribute('data-tab') ?? '')).catch(() => []);
      for (const g of groups) {
        await page.locator(`[data-case-workbench] .tablist [role="tab"][data-tab="${g}"]`).click().catch(() => undefined);
        await page.waitForTimeout(300);
        const subs = await page.$$eval('[data-case-workbench] .subtablist [role="tab"]', (ts) => ts.map((t) => t.getAttribute('data-tab') ?? '')).catch(() => []);
        if (subs.length === 0) out.push({ caseId, variant, group: g, sub: null });
        for (const sub of subs) out.push({ caseId, variant, group: g, sub });
      }
    }
  }
  return out;
}

async function main() {
  const browser = await chromium.launch();
  const rows = [];
  let failed = 0;
  const manifests = new Map();
  for (const [w, h] of sizes) {
    for (const lang of langs) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h } });
      await ctx.addInitScript(([l]) => {
        try {
          localStorage.setItem('caos.lang', l);
          localStorage.setItem('caos.theme', 'light');
        } catch {
          /* storage unavailable */
        }
      }, [lang]);
      if (wide) {
        await ctx.addInitScript(() => {
          document.addEventListener('DOMContentLoaded', () => {
            const st = document.createElement('style');
            st.textContent = ":root { --font-sans: 'DejaVu Sans', Verdana, sans-serif !important; }";
            document.head.appendChild(st);
          });
        });
      }
      const page = await ctx.newPage();
      const targets = walk ? await walkTargets(page, manifests) : TARGETS;
      for (const t of targets) {
        if (only && !only.has(t.caseId)) continue;
        const label = `${w}x${h} ${lang} ${t.caseId}${t.variant ? `/${t.variant}` : ''} ${t.group}${t.sub ? `/${t.sub}` : ''}`;
        try {
          await page.goto(`${base}/app?case=${t.caseId}`, { waitUntil: 'load', timeout: 30000 });
          await page.waitForFunction(ready, null, { timeout: 30000 });
          await pickVariant(page, t.caseId, t.variant, manifests);
          const tab = (id) => page.locator(`[role="tab"][data-tab="${id}"]`).filter({ hasNot: page.locator('.caos-wb-rail') }).first();
          await tab(t.group).click();
          if (t.sub) await tab(t.sub).click();
          await page.waitForTimeout(settleMs);
          await page.waitForFunction(ready, null, { timeout: 30000 });
          const m = await page.evaluate(measure, BOXES);
          const found = judge(m);
          rows.push({ label, ...m, findings: found });
          if (found.length) {
            failed += found.length;
            for (const x of found) console.log(`FAIL ${label}: ${x}`);
          } else console.log(`ok   ${label}: ${m.boxes.length} boxes, ${m.plots.length} plots`);
        } catch (e) {
          failed += 1;
          console.log(`FAIL ${label}: the view could not be opened (${String(e.message).split('\n')[0]})`);
          rows.push({ label, error: String(e.message).split('\n')[0] });
        }
      }
      await ctx.close();
    }
  }
  await browser.close();
  if (jsonOut) writeFileSync(jsonOut, JSON.stringify(rows, null, 1));
  console.log(`${rows.length} views, ${failed} finding(s)`);
  process.exit(failed ? 1 : 0);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replaceAll('\\', '/').split('/').pop())) await main();
