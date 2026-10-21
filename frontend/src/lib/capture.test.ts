// The capture tool (scripts/capture.mjs, U16-R1, decision D16-3) on the real build: two cases at one capture, into a
// temporary folder. Each test runs the tool as a reviewer does (a child process) and reads what it wrote. The tool needs
// a built dist/ and a Playwright browser (set PLAYWRIGHT_BROWSERS_PATH to the device's browsers root), and never runs in CI
// (ADR-0074): the suite is skipped when CI is set or when dist/ is not built.
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright';
import { afterAll, describe, expect, it } from 'vitest';

const frontend = resolve(__dirname, '..', '..');
const repo = resolve(frontend, '..');
const tool = join(frontend, 'scripts', 'capture.mjs');
const dist = join(frontend, 'dist');

const runnable = !process.env.CI && existsSync(join(dist, 'index.html'));

interface Row {
  id: string;
  route: string;
  case: string | null;
  group: { id: string; label: string; key: string } | null;
  sub_view: { id: string; label: string; key: string } | null;
  capture: { id: string; size: string; theme: string; lang: string };
  built: boolean;
  captured: boolean;
  file: string | null;
  settled?: boolean;
  unsettled_reason?: string | null;
  documents?: string[];
  not_found?: string[];
  case_documents?: string[];
  reason?: string;
}

const work = mkdtempSync(join(process.env.CAPTURE_TEST_TMP ?? tmpdir(), 'capture-test-'));
afterAll(() => rmSync(work, { recursive: true, force: true }));

function run(args: string[], cwd = frontend) {
  const r = spawnSync(process.execPath, [tool, ...args], { cwd, encoding: 'utf8', timeout: 240_000, env: process.env });
  return { code: r.status, out: `${r.stdout}${r.stderr}` };
}

/** Everything under a folder with sizes and mtimes: the repository must look the same after the tool ran. */
function listing(dir: string, skip: Set<string> = new Set()): string[] {
  const rows: string[] = [];
  const walk = (d: string) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (skip.has(e.name)) continue;
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else {
        const s = statSync(p);
        rows.push(`${p}|${s.size}|${s.mtimeMs}`);
      }
    }
  };
  walk(dir);
  return rows.sort();
}

/** The groups and sub-views of a case, read straight from the page with plain selectors (independent of the tool). */
async function expectedViews(caseId: string): Promise<string[]> {
  const serveModule = '@fasl-work/caos-app-shell/serve'; // plain JavaScript in the shell, no types
  const { servePages } = (await import(/* @vite-ignore */ serveModule)) as { servePages: (dir: string, base: string) => Promise<{ url: string; close: () => Promise<void> }> };
  const server = await servePages(dist, '/');
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    await page.goto(`${server.url}app?case=${caseId}`, { waitUntil: 'load' });
    await page.waitForSelector('[data-case-workbench] .tablist [role="tab"]');
    const groups = await page.$$eval('[data-case-workbench] .tablist [role="tab"]', (ts) => ts.map((t) => t.getAttribute('data-tab') ?? ''));
    const views: string[] = [];
    for (const g of groups) {
      await page.locator(`[data-case-workbench] .tablist [role="tab"][data-tab="${g}"]`).click();
      await page.waitForTimeout(400);
      const subs = await page.$$eval('[data-case-workbench] .subtablist [role="tab"]', (ts) => ts.map((t) => t.getAttribute('data-tab') ?? ''));
      if (subs.length === 0) views.push(`${g}|`);
      for (const s of subs) views.push(`${g}|${s}`);
    }
    return views;
  } finally {
    await browser.close();
    await server.close();
  }
}

describe.skipIf(!runnable)('the capture tool on two cases at one capture', () => {
  const out = join(work, 'two-cases');
  let rows: Row[] = [];
  let before: string[] = [];
  let after: string[] = [];
  let first = { code: -1 as number | null, out: '' };

  it('runs and exits 0', () => {
    const skip = new Set(['node_modules', '.git']);
    before = [...listing(frontend, skip), ...listing(join(repo, 'data'))];
    first = run(['--out', out, '--cases', 'C01,C02', '--captures', '1280x800:light:en']);
    after = [...listing(frontend, skip), ...listing(join(repo, 'data'))];
    expect(first.out).toMatch(/capture: \d+ views, \d+ PNGs/);
    expect(first.code).toBe(0);
    rows = JSON.parse(readFileSync(join(out, 'index.json'), 'utf8')) as Row[];
    expect(rows.length).toBeGreaterThan(10);
  }, 300_000);

  it('lists every group and sub-view of both cases, and nothing else', async () => {
    for (const c of ['C01', 'C02']) {
      const expected = await expectedViews(c);
      const got = rows.filter((r) => r.case === c && r.captured).map((r) => `${r.group?.id ?? ''}|${r.sub_view?.id ?? ''}`);
      expect(got).toEqual(expected);
    }
    expect(new Set(rows.filter((r) => r.captured).map((r) => r.case))).toEqual(new Set(['C01', 'C02']));
    expect(rows.every((r) => r.route === '/app' && r.capture.id === '1280x800-light-en')).toBe(true);
  }, 120_000);

  it('names an existing PNG for every row, with a deterministic name from the view', () => {
    for (const r of rows.filter((x) => x.captured)) {
      expect(r.file).toBeTruthy();
      const p = join(out, r.file as string);
      expect(existsSync(p), p).toBe(true);
      const head = readFileSync(p).subarray(0, 8);
      expect([...head]).toEqual([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
      expect(r.file).toBe(`shots/1280x800-light-en/app/${r.case}/${[r.group?.key, r.sub_view?.key].filter(Boolean).join('__')}.png`);
    }
    expect(new Set(rows.map((r) => r.file)).size).toBe(rows.length);
    expect(existsSync(join(out, 'index.html'))).toBe(true);
    expect(readFileSync(join(out, 'index.html'), 'utf8')).toContain('C02');
  });

  it('records the committed documents the views read', () => {
    for (const c of ['C01', 'C02']) {
      const mine = rows.filter((r) => r.case === c);
      expect(mine.every((r) => (r.case_documents ?? []).includes(`data/manifests/${c}.json`))).toBe(true);
      expect(mine.every((r) => (r.case_documents ?? []).every((d) => d.startsWith('data/')))).toBe(true);
      expect(mine.some((r) => (r.documents ?? []).some((d) => d.startsWith(`data/${c}/`)))).toBe(true);
    }
    expect(rows.every((r) => Array.isArray(r.not_found))).toBe(true);
  });

  it('flags a view that did not settle and a view that settled, never silently', () => {
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => typeof r.settled === 'boolean')).toBe(true);
    expect(rows.every((r) => r.settled === (r.unsettled_reason === null))).toBe(true);
  });

  it('wrote nothing into the repository', () => {
    expect(first.code).toBe(0);
    expect(before.length).toBeGreaterThan(100);
    expect(after).toEqual(before);
    expect(existsSync(join(frontend, 'shots'))).toBe(false);
  });

  it('refuses an output folder inside the repository, writing nothing', () => {
    const inside = join(repo, 'docs', 'capture-test-out');
    const r = run(['--out', inside, '--cases', 'C01', '--captures', '1280x800:light:en']);
    expect(r.code).toBe(2);
    expect(r.out).toMatch(/inside the repository/);
    expect(existsSync(inside)).toBe(false);
  }, 60_000);

  it('lists a planned case as not built, with its reason, and captures nothing for it', () => {
    const o = join(work, 'planned');
    const r = run(['--out', o, '--cases', 'C19', '--captures', '1280x800:light:en']);
    expect(r.code).toBe(0);
    const got = JSON.parse(readFileSync(join(o, 'index.json'), 'utf8')) as Row[];
    expect(got).toHaveLength(1);
    expect(got[0]).toMatchObject({ case: 'C19', built: false, captured: false, file: null });
    expect(got[0].reason).toMatch(/C19/);
    expect(existsSync(join(o, 'shots', '1280x800-light-en'))).toBe(false);
  }, 120_000);

  it('refuses a case the App does not offer', () => {
    const r = run(['--out', join(work, 'unknown'), '--cases', 'C99', '--captures', '1280x800:light:en']);
    expect(r.code).toBe(2);
    expect(r.out).toMatch(/C99/);
  }, 60_000);

  it('captures a view that did not settle anyway and flags it', () => {
    const o = join(work, 'unsettled');
    const r = run(['--out', o, '--cases', 'C01', '--captures', '1280x800:light:en', '--settle-ms', '1']);
    expect(r.code).toBe(0);
    const got = JSON.parse(readFileSync(join(o, 'index.json'), 'utf8')) as Row[];
    expect(got.length).toBeGreaterThan(5);
    expect(got.every((x) => x.settled === false && !!x.unsettled_reason)).toBe(true);
    expect(got.every((x) => existsSync(join(o, x.file as string)))).toBe(true);
  }, 240_000);

  it('captures a view whose document answers 404 and records the path', () => {
    const copy = join(work, 'dist-copy');
    cpSync(dist, copy, { recursive: true });
    const gone = 'data/C02/models-polish-horizons.json';
    expect(existsSync(join(copy, gone))).toBe(true);
    rmSync(join(copy, gone));
    const o = join(work, 'notfound');
    mkdirSync(o, { recursive: true });
    const r = run(['--out', o, '--dist', copy, '--cases', 'C02', '--captures', '1280x800:light:en']);
    expect(r.code).toBe(0);
    const got = JSON.parse(readFileSync(join(o, 'index.json'), 'utf8')) as Row[];
    const hit = got.filter((x) => (x.not_found ?? []).some((p) => p.startsWith(gone)));
    expect(hit.length).toBeGreaterThan(0);
    expect(hit.every((x) => existsSync(join(o, x.file as string)))).toBe(true);
    expect(got.length).toBeGreaterThan(3);
  }, 240_000);
});
