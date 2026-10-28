// The capture tool (U16-R1, decision D16-3): serves the built site the way GitHub Pages does, walks every App view (every
// case, group and sub-view) and every documentation route (every tab), and saves a PNG of each at the captures asked
// for, with an index that lets a reviewer read each view with its case, group, sub-view and the committed documents it
// shows. It measures nothing and judges nothing: the shell gate (npm run gate) measures, the reviewers read these captures.
//
//   npm run capture -- --out <temp root>/<run>                       every built case and route, the three captures of D16-3
//   npm run capture -- --out <dir> --cases C01,C02                   a reviewer batch: those cases only (no documentation routes)
//   npm run capture -- --out <dir> --routes /methodology,/benchmark  those routes only (add /app to walk the cases too)
//   npm run capture -- --out <dir> --captures 1280x800:light:en      one capture; the format is WxH:theme:lang, comma separated
//   npm run capture -- --out <dir> --variants all                    every variant of each case (or --variants id,id), selected in the rail
//   npm run capture -- --out <dir> --url https://<domain>            the deployed origin instead of dist/
// Other options: --dist <dir> (default dist), --base-path /Repo/ (default VITE_BASE or /), --settle-ms 15000 (the gate's), --text true (the
// view's text beside each PNG),
// --workers 4 (parallel pages), --workbench /app, --full-page true (the whole scrollable page instead of the viewport). The output folder is never inside the repository: the tool refuses it.
// Output: <out>/index.json (one row per view and capture, plus one per planned case), <out>/index.html (a grid by case),
// <out>/run.json (the run), <out>/shots/<capture>/<route>/<case>/<group>__<sub>.png. Never runs in CI (ADR-0074); the
// shell is not touched (ADR-0078): it relies on the public DOM contract only (data-brand, data-state, data-stale,
// data-drawn, role=tablist, data-control="case").
import { existsSync, mkdirSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

/** The band of a full-page capture taller than one image can hold: the page is also written in parts of this height. */
const SEGMENT_PX = 12000;
const here = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(here, '..');
const repo = resolve(frontend, '..');
const require = createRequire(import.meta.url);

export const DEFAULT_CAPTURES = ['1280x800:light:en', '1280x800:dark:es', '390x844:light:en'];
const SETTLE_MS = 15000;

// ------------------------------------------------------------------------------------------------------------------
// Options

function parseArgs(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i += 1) {
    const k = argv[i];
    if (!k.startsWith('--')) throw new Error(`unexpected argument "${k}"`);
    const v = argv[i + 1];
    if (v === undefined || v.startsWith('--')) throw new Error(`${k} needs a value`);
    a[k.slice(2)] = v;
    i += 1;
  }
  const known = new Set(['out', 'cases', 'routes', 'captures', 'url', 'dist', 'base-path', 'settle-ms', 'workers', 'workbench', 'full-page', 'variants', 'text']);
  for (const k of Object.keys(a)) if (!known.has(k)) throw new Error(`unknown option --${k}`);
  if (!a.out) throw new Error('--out <dir> is required (the output folder, outside the repository)');
  return a;
}

function parseCaptures(text) {
  return text.split(',').map((s) => s.trim()).filter(Boolean).map((s) => {
    const m = /^(\d+)x(\d+):(light|dark):(en|es)$/.exec(s);
    if (!m) throw new Error(`capture "${s}" is not WxH:theme:lang (for example 1280x800:light:en)`);
    const [, w, h, theme, lang] = m;
    return { id: `${w}x${h}-${theme}-${lang}`, size: `${w}x${h}`, width: Number(w), height: Number(h), theme, lang };
  });
}

/** The output folder must not be inside the repository (the tool writes nothing into it, dist/ included). */
function assertOutside(out) {
  const probe = (p) => {
    let q = resolve(p);
    while (!existsSync(q)) q = dirname(q);
    return join(realpathSync(q), relative(q, resolve(p)));
  };
  const o = probe(out);
  const r = realpathSync(repo);
  const rel = relative(r, o);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) {
    throw new Error(`--out ${out} is inside the repository (${repo}); the tool writes nothing into the repository, use the device temp root`);
  }
}

// ------------------------------------------------------------------------------------------------------------------
// In-page helpers (serialised into the page; they read the shell's public DOM contract only)

const readyWhy = () => {
  const shown = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && (!el.checkVisibility || el.checkVisibility({ checkVisibilityCSS: true }));
  };
  if (!document.querySelector('[data-brand]')) return 'no [data-brand]: the shell has not rendered';
  const loading = [...document.querySelectorAll('[data-state="loading"]')].filter(shown);
  if (loading.length) return `${loading.length} element(s) still declare data-state="loading"`;
  const stale = [...document.querySelectorAll('[data-stale="1"]')].filter(shown);
  if (stale.length) return `${stale.length} view(s) still show an earlier selection (data-stale="1")`;
  const undrawn = [...document.querySelectorAll('[data-drawn="0"]')].filter(shown);
  if (undrawn.length) return `${undrawn.length} stage(s) never got a size (data-drawn="0")`;
  const running = document.getAnimations().filter((an) => {
    try {
      return an.playState === 'running' && an.effect.getComputedTiming().iterations !== Infinity;
    } catch {
      return false;
    }
  });
  if (running.length) return `${running.length} finite animation(s) still running`;
  return '';
};

const tablistsOnPage = () => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && (!el.checkVisibility || el.checkVisibility({ checkVisibilityCSS: true }));
  };
  const path = (el) => {
    const parts = [];
    let e = el;
    while (e && e.nodeType === 1 && e !== document.body && e !== document.documentElement) {
      const p = e.parentElement;
      if (!p) break;
      parts.unshift(`${e.tagName.toLowerCase()}:nth-child(${Array.prototype.indexOf.call(p.children, e) + 1})`);
      e = p;
    }
    return parts.length ? `body > ${parts.join(' > ')}` : 'body';
  };
  return [...document.querySelectorAll('[role="tablist"]')]
    // not the header and footer, not a dialog, not the rail of controls (the controls of a case are not views of it)
    .filter((tl) => visible(tl) && !tl.closest('header, footer, [role="dialog"], .caos-wb-rail'))
    .map((tl) => {
      const panel = tl.parentElement ? tl.parentElement.closest('[role="tabpanel"]') : null;
      let owner = null;
      if (panel) {
        const id = panel.getAttribute('aria-labelledby');
        const tab = id ? document.getElementById(id) : null;
        const otl = tab ? tab.closest('[role="tablist"]') : null;
        owner = otl ? path(otl) : 'unknown';
      }
      const tabs = [...tl.querySelectorAll('[role="tab"]')].filter((t) => t.closest('[role="tablist"]') === tl && visible(t));
      return {
        key: path(tl),
        owner,
        source: Boolean(tl.closest('.cs-source-tabs')),
        tabs: tabs.map((t) => ({ label: (t.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60), id: t.getAttribute('data-tab') || '' })),
        active: tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true'),
      };
    });
};

const casesOnPage = () => {
  const ids = [];
  for (const c of document.querySelectorAll('[data-control="case"]')) {
    if (c.tagName === 'SELECT') {
      for (const o of c.options) if (!o.disabled && o.value) ids.push(o.value);
    } else {
      for (const b of c.querySelectorAll('[data-case]')) if (!b.disabled) ids.push(b.getAttribute('data-case'));
    }
  }
  return [...new Set(ids)];
};

// ------------------------------------------------------------------------------------------------------------------
// Names

const slug = (s) => String(s).toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'x';
const routeSlug = (route) => slug(route.replace(/^\//, '') || 'root');
const tabKey = (i, tab) => `${String(i + 1).padStart(2, '0')}-${slug(tab.id || 'tab')}`;

// ------------------------------------------------------------------------------------------------------------------
// The run

export async function runCapture(opts) {
  const startedAt = Date.now();
  const captures = parseCaptures(opts.captures ?? DEFAULT_CAPTURES.join(','));
  const out = resolve(opts.out);
  assertOutside(out);
  const settleMs = opts['settle-ms'] ? Number(opts['settle-ms']) : SETTLE_MS;
  const workers = Math.max(1, Number(opts.workers ?? 4));
  const workbench = (opts.workbench ?? '/app').trim();
  const fullPage = opts['full-page'] === 'true';
  // --text true: beside each PNG, the text a reader sees in the view (its innerText), for a scan of raw ids and English words
  const withText = opts.text === 'true';
  const wantVariants = opts.variants && opts.variants !== 'all' ? opts.variants.split(',').map((v) => v.trim()).filter(Boolean) : null;
  const variantMode = Boolean(opts.variants);

  const { chromium } = require('playwright');
  const { THEME_STORAGE_KEY, LANG_STORAGE_KEY } = await import('@fasl-work/caos-app-shell/keys');
  const { servePages } = await import('@fasl-work/caos-app-shell/serve');
  const product = JSON.parse(readFileSync(join(repo, 'product.json'), 'utf8'));

  let server = null;
  let base = opts.url;
  const distDir = resolve(opts.dist ?? join(frontend, 'dist'));
  if (!base) {
    if (!existsSync(join(distDir, 'index.html'))) throw new Error(`${distDir} has no index.html: run npm run build first`);
    server = await servePages(distDir, opts['base-path'] ?? process.env.VITE_BASE ?? '/');
    base = server.url;
  }
  base = base.endsWith('/') ? base : `${base}/`;
  const basePath = new URL(base).pathname;
  const urlFor = (route) => new URL(route.replace(/^\//, ''), base).href;
  const routeOf = (href) => {
    const p = new URL(href, base).pathname;
    return p.startsWith(basePath) ? `/${p.slice(basePath.length)}`.replace(/\/$/, '') || '/' : null;
  };

  const getJson = async (rel) => {
    const r = await fetch(new URL(`data/${rel}`, base)).catch(() => null);
    if (!r || r.status !== 200) return null;
    return r.json().catch(() => null);
  };
  const exists = async (rel) => {
    const r = await fetch(new URL(`data/${rel}`, base)).catch(() => null);
    return !!r && r.status === 200 && !(r.headers.get('content-type') ?? '').includes('text/html');
  };

  mkdirSync(out, { recursive: true });
  rmSync(join(out, 'shots'), { recursive: true, force: true });
  mkdirSync(join(out, 'shots'), { recursive: true });

  const browser = await chromium.launch();
  const newContext = async (cap) => {
    const ctx = await browser.newContext({ viewport: { width: cap.width, height: cap.height }, deviceScaleFactor: 1 });
    await ctx.addInitScript(
      ([tk, lk, t, l]) => {
        try {
          localStorage.setItem(tk, t);
          localStorage.setItem(lk, l);
        } catch {
          /* storage unavailable: the row records the mode that came back */
        }
      },
      [THEME_STORAGE_KEY, LANG_STORAGE_KEY, cap.theme, cap.lang],
    );
    return ctx;
  };

  /** A page with its recorder: every response under the base is kept, so a view can name the documents it read and the paths that answered an error. */
  const newPage = async (cap) => {
    const ctx = await newContext(cap);
    const page = await ctx.newPage();
    const rec = { docs: [], errors: [], consoleErrors: [] };
    page.on('response', (r) => {
      if (r.request().method() !== 'GET') return;
      let u;
      try {
        u = new URL(r.url());
      } catch {
        return;
      }
      if (!u.pathname.startsWith(basePath)) return;
      const rel = u.pathname.slice(basePath.length);
      if (r.status() >= 400) rec.errors.push({ path: rel, status: r.status() });
      else if (rel.startsWith('data/')) rec.docs.push(rel);
    });
    page.on('requestfailed', (req) => {
      // a request the page itself cancelled (the default case's manifest, left for the case asked for) is not a missing document
      if (/ABORTED/i.test(req.failure()?.errorText ?? '')) return;
      try {
        const u = new URL(req.url());
        if (u.pathname.startsWith(basePath)) rec.errors.push({ path: u.pathname.slice(basePath.length), status: 0 });
      } catch {
        /* not a URL */
      }
    });
    page.on('console', (m) => {
      if (m.type() === 'error') rec.consoleErrors.push(m.text().slice(0, 200));
    });
    page.on('pageerror', (e) => rec.consoleErrors.push(`page error: ${String(e).slice(0, 200)}`));
    return { ctx, page, rec };
  };

  const settle = async (page) => {
    const t0 = Date.now();
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null))))).catch(() => undefined);
    let last = 'timeout';
    let streak = 0;
    while (Date.now() - t0 < settleMs) {
      const why = await page.evaluate(readyWhy).catch((e) => `evaluate failed: ${e.message}`);
      if (why === '') {
        streak += 1;
        if (streak >= 2) return { why: '', ms: Date.now() - t0 };
      } else {
        streak = 0;
        last = why;
      }
      await page.waitForTimeout(60);
    }
    return { why: last, ms: Date.now() - t0 };
  };

  // ---- discovery on the first page: the routes of the header navigation, the cases the control offers
  let navRoutes;
  let offeredCases = [];
  {
    const { ctx, page } = await newPage(captures[0]);
    await page.goto(urlFor('/'), { waitUntil: 'load', timeout: 30000 });
    const s = await settle(page);
    const brand = await page.evaluate(() => document.querySelector('[data-brand]')?.getAttribute('data-brand') ?? null);
    if (brand !== product.name) throw new Error(`the page at ${base} is "${brand}", not "${product.name}"; nothing is captured`);
    if (s.why) console.warn(`[capture] the landing route did not settle: ${s.why}`);
    const hrefs = await page.$$eval('header nav a[href]', (as) => as.map((a) => a.href));
    navRoutes = [...new Set(hrefs.map(routeOf).filter(Boolean))];
    await page.goto(urlFor(workbench), { waitUntil: 'load', timeout: 30000 });
    // the App route is lazy-loaded (template 0.12.000): wait for its case control whatever --settle-ms says, so a short
    // settle captures unsettled views instead of reading an App that has not rendered yet
    await page.waitForSelector('[data-control="case"]', { timeout: 30000 }).catch(() => undefined);
    await settle(page);
    offeredCases = await page.evaluate(casesOnPage);
    await ctx.close();
  }
  if (!navRoutes.includes(workbench)) navRoutes.unshift(workbench);

  // ---- the selection
  const wantCases = opts.cases ? opts.cases.split(',').map((c) => c.trim()).filter(Boolean) : null;
  const wantRoutes = opts.routes && opts.routes !== 'none' ? opts.routes.split(',').map((r) => r.trim()).filter(Boolean) : opts.routes === 'none' ? [] : null;
  if (wantCases) for (const c of wantCases) if (!offeredCases.includes(c)) throw new Error(`case ${c} is not offered by the App (offered: ${offeredCases.join(', ')})`);
  if (wantRoutes) for (const r of wantRoutes) if (!navRoutes.includes(r)) throw new Error(`route ${r} is not in the header navigation (${navRoutes.join(', ')})`);
  // a reviewer batch (--cases without --routes) captures its cases only
  const routes = wantRoutes ?? (wantCases ? [workbench] : navRoutes);
  const cases = (wantCases ?? offeredCases).filter((c) => offeredCases.includes(c));

  // ---- which of the cases are built: the planned case has no manifest, and the readiness says why
  const caseIndex = await getJson('manifests/index.json');
  const readiness = await getJson('readiness.json');
  const manifestRow = readiness?.contracts?.find((c) => c.id === 'case-manifest');
  const titleOf = new Map((caseIndex?.cases ?? []).map((c) => [c.case_id, c.title?.en ?? '']));
  const built = [];
  const variantsOf = new Map(); // case id -> { def, ids } from the manifest (the variants the rail offers, in its order)
  const notBuilt = [];
  for (const id of cases) {
    const entry = (caseIndex?.cases ?? []).find((c) => c.case_id === id);
    const path = entry?.manifest_path ?? `manifests/${id}.json`;
    if (await exists(path)) {
      built.push(id);
      const m = await getJson(path);
      const ids = (m?.artifacts ?? []).filter((a) => a.role === 'variant').map((a) => a.variant_id);
      variantsOf.set(id, { def: m?.default_variant ?? ids[0] ?? null, ids });
    } else {
      const declared = manifestRow?.missing?.includes(path);
      notBuilt.push({
        route: workbench,
        case: id,
        case_title: titleOf.get(id) ?? '',
        built: false,
        captured: false,
        file: null,
        reason: declared && manifestRow.reason?.en ? manifestRow.reason.en : `the manifest ${path} is not in the build`,
      });
    }
  }

  // ---- the variants to walk per case: the default one only, or (--variants) all of them or those named
  if (wantVariants) {
    for (const v of wantVariants) {
      if (!built.some((id) => variantsOf.get(id).ids.includes(v))) throw new Error(`variant ${v} is not offered by any selected case`);
    }
  }
  const variantsFor = (id) => {
    const { def, ids } = variantsOf.get(id);
    if (!variantMode) return [{ id: def, vi: 0, select: false, walk: false }];
    const chosen = wantVariants ? ids.filter((v) => wantVariants.includes(v)) : ids;
    // a case with no variant list in its manifest is walked once as it renders
    if (ids.length === 0) return [{ id: def, vi: 0, select: false, walk: true }];
    return chosen.map((v) => ({ id: v, vi: ids.indexOf(v), select: v !== def, walk: true }));
  };

  // ---- the tasks: one per (capture, route), and one per (capture, case, variant) on the workbench route
  const tasks = [];
  routes.forEach((route, ri) => {
    captures.forEach((cap, ci) => {
      if (route === workbench) {
        built.forEach((id, ki) => {
          for (const v of variantsFor(id)) tasks.push({ route, ri, cap, ci, caseId: id, ki, variant: v });
        });
      } else tasks.push({ route, ri, cap, ci, caseId: null, ki: 0, variant: null });
    });
  });

  const rows = [];
  const failures = [];

  async function runTask(t) {
    const { ctx, page, rec } = await newPage(t.cap);
    let seq = 0;
    let mark = 0;
    const errMark = { n: 0, c: 0 };
    try {
      const url = t.caseId ? `${urlFor(t.route)}?case=${encodeURIComponent(t.caseId)}` : urlFor(t.route);
      const res = await page.goto(url, { waitUntil: 'load', timeout: 30000 }).catch((e) => e);
      const status = res && typeof res.status === 'function' ? res.status() : `error ${res?.message ?? res}`;

      const emit = async (trail, settled) => {
        const wb = await page.evaluate(() => document.querySelector('[data-case-workbench]')?.getAttribute('data-case') ?? null).catch(() => null);
        const mode = await page.evaluate(() => ({ theme: document.documentElement.dataset.theme ?? null, lang: document.documentElement.lang || null })).catch(() => ({}));
        const parts = trail.map((x) => x.key);
        const dirParts = [t.cap.id, routeSlug(t.route), ...(t.caseId ? [t.caseId] : []), ...(t.variant?.walk ? [t.variant.id] : [])];
        const file = `shots/${dirParts.join('/')}/${parts.length ? parts.join('__') : 'view'}.png`;
        mkdirSync(dirname(join(out, file)), { recursive: true });
        await page.evaluate(() => window.scrollTo(0, 0)).catch(() => undefined);
        await page.screenshot({ path: join(out, file), animations: 'disabled', fullPage: fullPage });
        // a full page taller than the browser paints in one image (about 16,384 px) came out blank past its band (U16-R3 c23 B7:
        // /benchmark blank from 14,900 to 82,274 px at 390): such a page is also written in bands of SEGMENT_PX, listed as `segments`
        const segments = [];
        if (fullPage) {
          const tall = await page.evaluate(() => Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)).catch(() => 0);
          if (tall > SEGMENT_PX) {
            const width = await page.evaluate(() => document.documentElement.clientWidth).catch(() => t.cap.width);
            for (let y = 0, k = 1; y < tall; y += SEGMENT_PX, k += 1) {
              const part = file.replace(/\.png$/, `__part-${String(k).padStart(2, '0')}.png`);
              await page.screenshot({ path: join(out, part), animations: 'disabled', fullPage: true, clip: { x: 0, y, width, height: Math.min(SEGMENT_PX, tall - y) } });
              segments.push(part);
            }
          }
        }
        if (withText) {
          const seen = await page.evaluate(() => document.querySelector('main')?.innerText ?? document.body.innerText).catch(() => '');
          writeFileSync(join(out, file.replace(/\.png$/, '.txt')), seen, 'utf8');
        }
        const docs = rec.docs.slice(mark).map((d) => d.split('?')[0]);
        const miss = rec.errors.slice(errMark.n);
        const warnings = [];
        if (status !== 200) warnings.push(`the route answered ${status}`);
        if (t.caseId && wb !== t.caseId) warnings.push(`asked for case ${t.caseId}; the workbench shows ${wb}`);
        if (mode.theme && mode.theme !== t.cap.theme) warnings.push(`asked for the ${t.cap.theme} theme; the document has ${mode.theme}`);
        if (mode.lang && !mode.lang.startsWith(t.cap.lang)) warnings.push(`asked for ${t.cap.lang}; <html lang> is ${mode.lang}`);
        const consoleErrors = rec.consoleErrors.slice(errMark.c);
        rows.push({
          order: [t.ri, t.caseId ? t.ki : 0, t.variant?.vi ?? 0, t.ci, seq],
          id: [t.cap.id, t.route, t.caseId ?? '-', ...(t.variant?.walk ? [`v:${t.variant.id}`] : []), ...parts].join('|'),
          route: t.route,
          case: t.caseId,
          variant: t.variant?.id ?? null,
          case_title: t.caseId ? titleOf.get(t.caseId) ?? '' : null,
          group: trail[0] ? { id: trail[0].id, label: trail[0].label, key: trail[0].key } : null,
          sub_view: trail[1] ? { id: trail[1].id, label: trail[1].label, key: trail[1].key } : null,
          deeper: trail.slice(2).map((x) => ({ id: x.id, label: x.label, key: x.key })),
          capture: { id: t.cap.id, size: t.cap.size, width: t.cap.width, height: t.cap.height, theme: t.cap.theme, lang: t.cap.lang, full_page: fullPage },
          built: true,
          captured: true,
          file,
          segments,
          settled: settled.why === '',
          unsettled_reason: settled.why || null,
          settle_ms: settled.ms,
          documents: [...new Set(docs)],
          not_found: [...new Set(miss.filter((m) => m.status === 404 || m.status === 0 || m.status >= 400).map((m) => `${m.path}${m.status ? ` (${m.status})` : ' (failed)'}`))],
          case_documents: [...new Set(rec.docs.map((d) => d.split('?')[0]))],
          case_not_found: [...new Set(rec.errors.map((m) => `${m.path}${m.status ? ` (${m.status})` : ' (failed)'}`))],
          console_errors: consoleErrors,
          warnings,
        });
        seq += 1;
        mark = rec.docs.length;
        errMark.n = rec.errors.length;
        errMark.c = rec.consoleErrors.length;
      };

      // a workbench route draws its group tabs after its lazy chunk loads: list the views only once they exist, whatever --settle-ms
      if (t.route === workbench) await page.waitForSelector('[data-case-workbench] .tablist [role="tab"]', { timeout: 30000 }).catch(() => undefined);
      let settled = await settle(page);
      let emitted = 0;

      // a variant walk: select the variant in the rail as a reader does, then wait for the idle state
      if (t.variant?.select) {
        const chip = page.locator('[data-control="variant"] [role="radio"]').nth(t.variant.vi);
        const vid = [t.cap.id, t.route, t.caseId, `v:${t.variant.id}`].join('|');
        try {
          await chip.evaluate((el) => el.scrollIntoView({ block: 'nearest', inline: 'nearest' })).catch(() => undefined);
          await chip.click({ timeout: 5000 });
        } catch (e) {
          failures.push({ id: vid, message: `the variant could not be selected: ${e.message.split('\n')[0]}` });
          return;
        }
        settled = await settle(page);
        if ((await chip.getAttribute('aria-checked').catch(() => null)) !== 'true') {
          failures.push({ id: vid, message: 'the variant chip is not checked after the click' });
          return;
        }
      }

      /** Walks the tab lists owned by `parent` (null: the page itself); a state with no list under it is a view. */
      const visit = async (trail, parentKey, handled) => {
        const lists = (await page.evaluate(tablistsOnPage)).filter((l) => !handled.has(l.key) && !l.source);
        const mine = lists.filter((l) => (parentKey ? l.owner === parentKey : l.owner === null));
        if (mine.length === 0) {
          await emit(trail, settled);
          emitted += 1;
          return 1;
        }
        let leaves = 0;
        for (const tl of mine) {
          handled.add(tl.key);
          for (let i = 0; i < tl.tabs.length; i += 1) {
            const tab = page.locator(tl.key).locator('[role="tab"]').filter({ visible: true }).nth(i);
            const here = [...trail, { key: tabKey(i, tl.tabs[i]), id: tl.tabs[i].id || slug(tl.tabs[i].label), label: tl.tabs[i].label }];
            const selected = (await tab.getAttribute('aria-selected').catch(() => null)) === 'true';
            if (!selected) {
              mark = rec.docs.length;
              errMark.n = rec.errors.length;
              errMark.c = rec.consoleErrors.length;
              try {
                await tab.evaluate((el) => el.scrollIntoView({ block: 'nearest', inline: 'nearest' })).catch(() => undefined);
                await tab.click({ timeout: 5000 });
              } catch (e) {
                failures.push({ id: [t.cap.id, t.route, t.caseId ?? '-', ...here.map((x) => x.key)].join('|'), message: `the tab could not be clicked: ${e.message.split('\n')[0]}` });
              }
              settled = await settle(page);
            }
            const inner = await visit(here, tl.key, new Set(handled));
            leaves += inner;
          }
        }
        return leaves;
      };

      await visit([], null, new Set());
      if (emitted === 0) failures.push({ id: [t.cap.id, t.route, t.caseId ?? '-'].join('|'), message: 'no view was captured' });
    } catch (e) {
      failures.push({ id: [t.cap.id, t.route, t.caseId ?? '-'].join('|'), message: `the walk stopped: ${String(e.message).split('\n')[0]}` });
    } finally {
      await ctx.close().catch(() => undefined);
    }
  }

  let next = 0;
  await Promise.all(
    Array.from({ length: Math.min(workers, tasks.length || 1) }, async () => {
      while (next < tasks.length) {
        const t = tasks[next];
        next += 1;
        await runTask(t);
      }
    }),
  );
  await browser.close();
  if (server) await server.close();

  // ---- the index, in the order of the routes, the cases, the captures and the walk
  rows.sort((a, b) => {
    for (let i = 0; i < 5; i += 1) if (a.order[i] !== b.order[i]) return a.order[i] - b.order[i];
    return 0;
  });
  const index = rows.map(({ order, ...r }) => r);
  const planned = notBuilt.map((r) => ({ id: `not-built|${r.route}|${r.case}`, ...r }));
  const all = [...index, ...planned];
  writeFileSync(join(out, 'index.json'), `${JSON.stringify(all, null, 2)}\n`);
  writeFileSync(join(out, 'index.html'), indexHtml(all, product.name));
  const build = existsSync(join(distDir, 'build.json')) && !opts.url ? JSON.parse(readFileSync(join(distDir, 'build.json'), 'utf8')) : null;
  const summary = {
    product: product.name,
    target: opts.url ?? 'dist',
    build,
    captures: captures.map((c) => c.id),
    routes,
    variants: variantMode ? (opts.variants === 'all' ? 'all' : wantVariants) : 'default',
    cases_built: built,
    cases_not_built: notBuilt.map((n) => n.case),
    views: new Set(index.map((r) => r.id.split('|').slice(1).join('|'))).size,
    pngs: index.length,
    rows: all.length,
    not_settled: index.filter((r) => !r.settled).length,
    with_not_found: index.filter((r) => r.not_found.length > 0).length,
    with_warnings: index.filter((r) => r.warnings.length > 0).length,
    failures,
    wall_seconds: Math.round((Date.now() - startedAt) / 100) / 10,
  };
  writeFileSync(join(out, 'run.json'), `${JSON.stringify(summary, null, 2)}\n`);
  return summary;
}

// ------------------------------------------------------------------------------------------------------------------
// index.html: a grid by case (and by documentation route), one row per view, one thumbnail per capture

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

function indexHtml(all, product) {
  const groups = new Map();
  for (const r of all) {
    const key = r.case ? `${r.route} ${r.case}` : r.route;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const body = [];
  for (const [key, list] of groups) {
    const first = list[0];
    body.push(`<section><h2>${esc(key)}${first.case_title ? ` <small>${esc(first.case_title)}</small>` : ''}</h2>`);
    if (first.built === false) {
      body.push(`<p class="nb">Not built: ${esc(first.reason)}</p></section>`);
      continue;
    }
    const caps = [...new Map(list.map((r) => [r.capture.id, r.capture])).values()];
    const views = new Map();
    for (const r of list) {
      const vk = r.id.split('|').slice(3).join('|');
      if (!views.has(vk)) views.set(vk, new Map());
      views.get(vk).set(r.capture.id, r);
    }
    body.push(`<table><thead><tr><th>View</th>${caps.map((c) => `<th>${esc(c.size)} ${esc(c.theme)} ${esc(c.lang)}</th>`).join('')}</tr></thead><tbody>`);
    for (const [vk, byCap] of views) {
      const any = [...byCap.values()][0];
      const label = [any.id.split('|')[3]?.startsWith('v:') ? `variant ${any.variant}` : '', any.group?.label, any.sub_view?.label, ...any.deeper.map((d) => d.label)].filter(Boolean).join(' > ') || 'whole page';
      body.push(`<tr><th scope="row">${esc(label)}<br><code>${esc(vk)}</code></th>`);
      for (const c of caps) {
        const r = byCap.get(c.id);
        if (!r) {
          body.push('<td></td>');
          continue;
        }
        const flags = [!r.settled ? 'not settled' : '', r.not_found.length ? `404: ${r.not_found.join(', ')}` : '', ...r.warnings].filter(Boolean);
        body.push(
          `<td><a href="${esc(r.file)}"><img loading="lazy" src="${esc(r.file)}" alt="${esc(label)}"></a>` +
            `<details><summary>${flags.length ? `<b>${esc(flags.join('; '))}</b>` : 'documents'}</summary><ul>${r.documents.map((d) => `<li>${esc(d)}</li>`).join('') || '<li>none requested while this view settled</li>'}</ul></details></td>`,
        );
      }
      body.push('</tr>');
    }
    body.push('</tbody></table></section>');
  }
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(product)} capture index</title>
<style>
body{font:14px/1.4 system-ui,sans-serif;margin:16px;background:#fff;color:#111}
h2{margin:28px 0 8px}small{font-weight:400;color:#555}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:1px solid #bbb;padding:6px;vertical-align:top}
thead th{background:#eee}tbody th{width:16%;text-align:left;font-weight:600;word-break:break-word}
img{max-width:100%;height:auto;display:block;border:1px solid #ddd}details{margin-top:4px;font-size:12px}.nb{color:#a40}
</style></head><body><h1>${esc(product)} capture index</h1>
<p>One row per view, one column per capture. The data is in <code>index.json</code>.</p>
${body.join('\n')}
</body></html>
`;
}

// ------------------------------------------------------------------------------------------------------------------

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (e) {
    console.error(`capture: ${e.message}`);
    process.exit(2);
  }
  try {
    const s = await runCapture(args);
    console.log(
      `capture: ${s.views} views, ${s.pngs} PNGs, ${s.cases_not_built.length} case(s) not built (${s.cases_not_built.join(', ') || 'none'}), ` +
        `${s.not_settled} not settled, ${s.with_not_found} with a 404, ${s.failures.length} failure(s), ${s.wall_seconds} s; index ${join(resolve(args.out), 'index.json')}`,
    );
    for (const f of s.failures.slice(0, 40)) console.log(`FAIL ${f.id}: ${f.message}`);
    process.exit(s.failures.length ? 1 : 0);
  } catch (e) {
    console.error(`capture: ${e.message}`);
    process.exit(2);
  }
}
