// GATE-15B: the governance register and the reports as documents that fit their box. The paging and the filters are pure
// functions (first page, last page, a filter with its count, the empty filter, every row reachable) and the views are read as
// markup in both languages; the register is the committed one (its size read, never typed), a report the reviewed fixture.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../../workbench/c03/u6-testkit';
import type { FindingRow, GovFindings, GovReport } from '../../workbench/governance/model';
import { PagedReport } from './PagedReport';
import { RegisterBrowser } from './PagedRegister';
import { pageOf, stepStart } from './RowPager';
import { familyOf } from './families';
import { ALL, REGISTER_PER_PAGE, familyOptions, filterRegister, registerView, severityCounts } from './registerPaging';

const real = JSON.parse(readFileSync(new URL('../../../../data/derived/governance/findings.json', import.meta.url), 'utf8')) as GovFindings;
const rows: FindingRow[] = real.rows;
const N = rows.length;
const report = JSON.parse(readFileSync(new URL('../../../../docs/contracts/fixtures/governance/report-C07-banco-andino-fixture.json', import.meta.url), 'utf8')) as GovReport;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const text = (m: string) => m.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/\s+/g, ' ');
const count = (s: string, re: RegExp) => (s.match(re) ?? []).length;

afterEach(() => setLang('en'));

describe('the register is paged with the shell window', () => {
  const none = { severity: ALL, family: ALL };
  it('shows every row under the default filter and starts at the first page', () => {
    const v = registerView(rows, none, 0);
    expect(N).toBeGreaterThan(2 * REGISTER_PER_PAGE);
    expect(v.matching).toBe(N);
    expect(v.hidden).toBe(0);
    expect([v.start, v.end]).toEqual([0, REGISTER_PER_PAGE]);
    expect(v.page).toHaveLength(REGISTER_PER_PAGE);
    expect(v.page[0].severity).toBe('S1');
  });
  it('pulls the last page back so it is full, and a step past the end stays on it', () => {
    const last = registerView(rows, none, 100000);
    expect([last.start, last.end]).toEqual([N - REGISTER_PER_PAGE, N]);
    expect(last.page).toHaveLength(REGISTER_PER_PAGE);
    expect(stepStart(N, REGISTER_PER_PAGE, last.start, 1)).toBe(last.start);
  });
  it('steps forward and back by a page and stops at the first', () => {
    expect(stepStart(N, REGISTER_PER_PAGE, 0, 1)).toBe(REGISTER_PER_PAGE);
    expect(stepStart(N, REGISTER_PER_PAGE, REGISTER_PER_PAGE, -1)).toBe(0);
    expect(stepStart(N, REGISTER_PER_PAGE, 0, -1)).toBe(0);
  });
  it('reaches every row: walking the pages lists each of the findings', () => {
    const seen = new Set<string>();
    let start = 0;
    for (let guard = 0; guard < 200; guard += 1) {
      const v = registerView(rows, none, start);
      for (const r of v.page) seen.add(r.key);
      const next = stepStart(N, REGISTER_PER_PAGE, v.start, 1);
      if (next === v.start) break;
      start = next;
    }
    expect(seen.size).toBe(N);
  });
  it('filters by severity with the count of what it shows and what it hides', () => {
    const v = registerView(rows, { severity: 'S1', family: ALL }, 0);
    expect(v.matching).toBe(real.counts.by_severity.S1);
    expect(v.hidden).toBe(N - v.matching);
    expect(v.page.every((r) => r.severity === 'S1')).toBe(true);
    expect(severityCounts(rows, ALL)).toEqual(real.counts.by_severity);
  });
  it('filters by the question family of the case, and the chips count what a choice shows', () => {
    const fams = familyOptions(rows, ALL);
    expect(fams.reduce((a, f) => a + f.count, 0)).toBe(N);
    for (const f of fams) expect(registerView(rows, { severity: ALL, family: f.id }, 0).matching).toBe(f.count);
    const s1 = familyOptions(rows, 'S1');
    expect(s1.reduce((a, f) => a + f.count, 0)).toBe(real.counts.by_severity.S1);
    expect(filterRegister(rows, { severity: ALL, family: 'pd' }).every((r) => familyOf(r.case_id).id === 'pd')).toBe(true);
  });
  it('gives every case of the register a family of the coverage registry', () => {
    for (const c of new Set(rows.map((r) => r.case_id))) expect(familyOf(c).id, c).not.toBe('other');
  });
  it('is empty, with zero rows and no page, when no finding meets both filters', () => {
    const f = { severity: 'S1', family: 'validator' };
    const v = registerView(rows, f, 0);
    expect(v.matching).toBe(0);
    expect(v.page).toEqual([]);
    expect(v.hidden).toBe(N);
  });
  it('pages a plain list with the same window', () => {
    expect(pageOf([1, 2, 3, 4, 5], 2, 4)).toEqual({ items: [4, 5], start: 3, end: 5 });
  });
});

describe('the register view states what it shows', () => {
  it('states the first page and no filter, in English and in Spanish', () => {
    const en = html(<RegisterBrowser rows={rows} />);
    expect(text(en)).toContain(`All ${N} register rows are listed, no filter applied.`);
    expect(en).toMatch(new RegExp(`data-pager-position[^>]*>1 to 8 of ${N}<`));
    expect(count(en, /data-finding="/g)).toBe(REGISTER_PER_PAGE);
    setLang('es');
    const es = html(<RegisterBrowser rows={rows} />);
    expect(es).toMatch(new RegExp(`data-pager-position[^>]*>1 a 8 de ${N}<`));
    expect(text(es)).toContain(`Se listan las ${N} filas del registro, sin filtro.`);
  });
  it('states the last page', () => {
    const m = html(<RegisterBrowser rows={rows} initial={{ start: 100000 }} />);
    expect(m).toMatch(new RegExp(`data-pager-position[^>]*>${N - 7} to ${N} of ${N}<`));
    expect(m).toMatch(/data-pager-next[^>]*aria-disabled="true"/);
    expect(m).toMatch(/data-pager-prev[^>]*aria-disabled="false"/);
  });
  it('shows the count a filter hides and the count the chips offer', () => {
    const m = html(<RegisterBrowser rows={rows} initial={{ severity: 'S1' }} />);
    expect(text(m)).toContain(`5 of ${N} register rows match the filter; the filter hides the other ${N - 5}.`);
    expect(m).toMatch(/data-pager-position[^>]*>1 to 5 of 5</);
    expect(text(m)).toContain('S1 critical (5)');
    expect(text(m)).toContain(`All (${N})`);
    setLang('es');
    expect(text(html(<RegisterBrowser rows={rows} initial={{ severity: 'S1' }} />))).toContain(`5 de ${N} filas del registro cumplen el filtro; el filtro oculta las otras ${N - 5}.`);
  });
  it('shows an empty state for a filter nothing meets, with the count and no table', () => {
    const m = html(<RegisterBrowser rows={rows} initial={{ severity: 'S1', family: 'validator' }} />);
    expect(m).toContain('data-register-empty');
    expect(m).not.toContain('data-register ');
    expect(m).toMatch(/data-pager-position[^>]*>0 of 0</);
    expect(text(m)).toContain(`0 of ${N} register rows match the filter`);
  });
});

describe('a report is read a section at a time', () => {
  const sections = report.sections.length;
  it('shows the first section and its position, with every section in the select', () => {
    const m = html(<PagedReport report={report} />);
    expect(sections).toBe(12);
    expect(count(m, /<section data-section="/g)).toBe(1);
    expect(m).toContain('data-section="1"');
    expect(m).toMatch(/data-pager-position[^>]*>1 of 12</);
    expect(count(m, /<option /g)).toBe(sections);
  });
  it('shows the opinion section on its own page, and the last page, in both languages', () => {
    const m = html(<PagedReport report={report} initial={10} />);
    expect(m).toContain('data-section="11"');
    expect(m).toMatch(/data-pager-position[^>]*>11 of 12</);
    expect(html(<PagedReport report={report} initial={999} />)).toMatch(/data-pager-position[^>]*>12 of 12</);
    setLang('es');
    expect(html(<PagedReport report={report} initial={2} />)).toMatch(/data-pager-position[^>]*>3 de 12</);
  });
});
