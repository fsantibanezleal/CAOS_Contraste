// Wave 2 batch 2 on the cross-case pages: the six new cases (C10, C11, C13, C14, C15, C17) appear on Experiments grouped by
// their question family, with one headline row per variant in the case's own measures, and on Benchmark with a comparison
// in the case's own terms or an honest exclusion with its reason. Every number is read from the contract fixtures here
// (they share the documents' shape); a field the artifact leaves null reads "not available" with its reason.
import { readFileSync } from 'node:fs';
import { formatNumber, pick } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { HAS_OWN_BENCHMARK, NO_BENCHMARK } from './Benchmark';
import { groupCases } from './Experiments';
import { U6_BENCHMARK_CASES, U6_CASES } from './U6Sections';
import { W2_BENCHMARK_CASES, W2_CASES, wave2BenchmarkTables, wave2ExperimentTables } from './Wave2Sections';

const NOT_AVAILABLE = /not available|no disponible/i;
const BAD = /NaN|undefined|Infinity|\[object/;
const fixture = (dir: string, file: string) => JSON.parse(readFileSync(new URL(`../../../docs/contracts/fixtures/${dir}/${file}`, import.meta.url), 'utf8')) as VariantArtifact<unknown>;
const manifestOf = (id: string, vs: Array<VariantArtifact<unknown>>) =>
  ({ case_id: id, artifacts: vs.map((v) => ({ role: 'variant', variant_id: v.variant_id, title: { en: `A long title of ${v.variant_id}`, es: `Un título largo de ${v.variant_id}` }, short_title: { en: `Fixture ${v.variant_id}`, es: `Prueba ${v.variant_id}` } })) }) as unknown as CaseManifest;

const FIXTURES: Record<string, [string, string[]]> = {
  C10: ['c10', ['variant-loan-type-fixture.json', 'variant-correlation-grid-fixture.json']],
  C11: ['c11', ['variant-window-fixture.json']],
  C13: ['c13', ['variant-deficiency-fixture.json']],
  C14: ['c14', ['variant-valuation-date-2021-q4-fixture.json', 'variant-valuation-date-2022-q4-fixture.json']],
  C15: ['c15', ['variant-annex1-variant-cpi-surprise-fixture.json', 'variant-annex1-variant-long-uf-fixture.json', 'variant-annex1-variant-offset-on-off-fixture.json']],
  C17: ['c17', ['variant-tail-index-fixture.json', 'variant-tail-index-infinite-mean-fixture.json']],
};
const load = (id: string) => FIXTURES[id][1].map((f) => fixture(FIXTURES[id][0], f));
const flat = (tables: Array<{ head: string[]; rows: unknown[][] }>) => tables.flatMap((t) => t.rows.map((r) => r.map(String).join(' | '))).join('\n');

describe('the Experiments case tabs are grouped by the question family, six new cases included', () => {
  const BUILT = ['c01', 'c03', 'c04', 'c05', 'c06', 'c07', 'c08', 'c09', 'c10', 'c11', 'c13', 'c14', 'c15', 'c17'];
  const groups = groupCases(BUILT.map((id) => ({ id, label: id.toUpperCase(), content: null })));
  it('holds no group above six peer tabs and loses no case', () => {
    for (const g of groups) expect(g.tabs.length, g.id).toBeLessThanOrEqual(6);
    expect(groups.flatMap((g) => g.tabs.map((t) => t.id)).sort()).toEqual([...BUILT].sort());
  });
  it('joins portfolio capital and operational risk, names market risk and the balance sheet, in both languages', () => {
    const by = (lang: 'en' | 'es') => Object.fromEntries(groups.map((g) => [pick(g.label, lang), g.tabs.map((t) => t.id)]));
    expect(by('en')).toMatchObject({ 'Capital, aggregation and stress': ['c10', 'c17'], 'Market and balance-sheet risk': ['c11', 'c13', 'c14', 'c15'] });
    expect(by('es')).toMatchObject({ 'Capital, agregación y estrés': ['c10', 'c17'], 'Riesgo de mercado y de balance': ['c11', 'c13', 'c14', 'c15'] });
    expect(groups.find((g) => g.id === 'capital')).toBeDefined();
    expect(groups.find((g) => g.id === 'market-balance')).toBeDefined();
    expect(groups.length + 1).toBeLessThanOrEqual(6);
  });
  it('keeps the existing families as they were', () => {
    const by = Object.fromEntries(groups.map((g) => [pick(g.label, 'en'), g.tabs.map((t) => t.id)]));
    expect(by['Credit scoring and PD']).toEqual(['c01', 'c03', 'c04', 'c05']);
    expect(by['Credit losses: provisions, severity and exposure']).toEqual(['c06', 'c07', 'c08', 'c09']);
  });
});

describe('every new case has an Experiments table with one headline row per variant', () => {
  it('registers the six cases and keeps them out of the C01 scorecard shape and the U6 sections', () => {
    expect([...W2_CASES].sort()).toEqual(['C10', 'C11', 'C13', 'C14', 'C15', 'C17']);
    for (const id of W2_CASES) expect(U6_CASES.has(id), id).toBe(false);
  });
  for (const id of Object.keys(FIXTURES)) {
    it(`${id}: one row per variant, no gap in either language, Spanish headers in Spanish`, () => {
      const vs = load(id);
      const m = manifestOf(id, vs);
      for (const lang of ['en', 'es'] as const) {
        const tables = wave2ExperimentTables(m, vs, lang);
        expect(tables.length, id).toBeGreaterThan(0);
        expect(tables.reduce((a, t) => a + t.rows.length, 0), id).toBe(vs.length);
        for (const t of tables) {
          for (const r of t.rows) {
            expect(r.length, id).toBe(t.head.length);
            expect(String(r[0])).toBe(`${lang === 'en' ? 'Fixture' : 'Prueba'} ${vs.find((v) => String(r[0]).endsWith(v.variant_id))?.variant_id}`);
          }
        }
        expect(flat(tables), `${id} ${lang}`).not.toMatch(BAD);
      }
      const en = wave2ExperimentTables(m, vs, 'en').flatMap((t) => t.head);
      const es = wave2ExperimentTables(m, vs, 'es').flatMap((t) => t.head);
      expect(es.filter((h, i) => h === en[i] && /[a-z]{4,}/.test(h) && !/^(IFRS|EVE|NII|PLA|FZ0|MCS|LDA|SMA|PD)/.test(h)), `${id} headers left in English`).toEqual([]);
    });
  }

  it('C10: the fitted PD and correlation with their interval, the exceedances, the capital of the C2 rung and the LHP', () => {
    const vs = load('C10');
    const [loan, grid] = wave2ExperimentTables(manifestOf('C10', vs), vs, 'en');
    expect(loan.head.length).toBe(6);
    const row = loan.rows[0].map(String);
    expect(row[1]).toMatch(/0\.30/);
    expect(row[1]).toMatch(/0\.25/);
    expect(row[2]).toMatch(/0\.060/);
    expect(row[3]).toMatch(/5/);
    expect(row[4]).toMatch(/\d/);
    expect(row[5]).toMatch(/\d/);
    expect(row[4]).not.toBe(row[5]);
    expect(grid.head.length).toBe(6);
    const g = grid.rows[0].map(String);
    expect(g[1]).toMatch(/12/);
    for (const c of g.slice(2)) expect(c).toMatch(/\d/);
  });
  it('C10: a rung that did not run shows not available with its reason, never a number', () => {
    const vs = load('C10');
    const v = JSON.parse(JSON.stringify(vs[0])) as VariantArtifact<{ rungs: Array<{ method: string; evaluated: boolean; measures: unknown; reason: string | null }> }>;
    const c2 = v.outputs.rungs.find((r) => r.method === 'gaussian-copula-one-factor')!;
    c2.evaluated = false;
    c2.measures = null;
    c2.reason = 'the reason of the test';
    const [loan] = wave2ExperimentTables(manifestOf('C10', [v]), [v], 'en');
    expect(String(loan.rows[0][4])).toMatch(NOT_AVAILABLE);
    expect(String(loan.rows[0][4])).toContain('the reason of the test');
  });
  it('C11: the champion, the traffic-light zone, the FZ0 average and the MCS size of each level', () => {
    const vs = load('C11');
    const [t] = wave2ExperimentTables(manifestOf('C11', vs), vs, 'en');
    expect(t.head.length).toBe(5);
    const row = t.rows[0].map(String);
    expect(row[1]).toMatch(/1\s?%/);
    expect(row[1]).toMatch(/2\.5\s?%/);
    expect(row[2]).toMatch(/Green|Amber|Red/);
    expect(row[3]).toMatch(/-?\d/);
    expect(row[4]).toMatch(/2 of 3/);
    const es = wave2ExperimentTables(manifestOf('C11', vs), vs, 'es')[0].rows[0].map(String);
    expect(es[2]).toMatch(/Verde|Ámbar|Rojo/);
    expect(es[4]).toMatch(/2 de 3/);
  });
  it('C13: the planted deficiency, the share caught and the PLA zone counts', () => {
    const vs = load('C13');
    const [t] = wave2ExperimentTables(manifestOf('C13', vs), vs, 'en');
    const row = t.rows[0].map(String);
    expect(row[1]).toMatch(/Missing basis/);
    expect(row[2]).toMatch(/92/);
    expect(row[3]).toMatch(/80/);
    expect(row[3]).toMatch(/540/);
    expect(row[3]).toMatch(/380/);
    expect(String(wave2ExperimentTables(manifestOf('C13', vs), vs, 'es')[0].rows[0][1])).toMatch(/Base omitida/);
  });
  it('C14: the largest delta EVE and its shock with and without behavioural NMD, and the outlier test', () => {
    const vs = load('C14');
    const [t] = wave2ExperimentTables(manifestOf('C14', vs), vs, 'en');
    expect(t.rows.length).toBe(2);
    const row = t.rows[1].map(String);
    expect(row[1]).toMatch(/Parallel up/);
    expect(row[2]).toMatch(/Parallel up/);
    expect(row[1]).not.toBe(row[2]);
    expect(row[3]).toMatch(/10\.5\s?%/);
    expect(row[3]).toMatch(/15\s?%/);
    expect(t.head.join(' ')).toMatch(/behavioural/i);
    expect(wave2ExperimentTables(manifestOf('C14', vs), vs, 'es')[0].head.join(' ')).toMatch(/conductual/i);
  });
  it('C15: the largest delta EVE and its shock with and without the offset, the outlier tests and the indexation charge', () => {
    const vs = load('C15');
    const [t] = wave2ExperimentTables(manifestOf('C15', vs), vs, 'en');
    expect(t.rows.length).toBe(3);
    const long = t.rows[1].map(String);
    expect(long[1]).toMatch(/Parallel up/);
    expect(long[1]).not.toBe(long[2]);
    expect(long[3]).toMatch(/10\.0\s?%/);
    expect(long[4]).toMatch(/\d/);
    expect(t.head.join(' ')).toMatch(/indexation/i);
    expect(wave2ExperimentTables(manifestOf('C15', vs), vs, 'es')[0].head.join(' ')).toMatch(/reajustabilidad|indexación/i);
  });
  it('C17: the true 99.9 percent quantile, the LDA capital bias and dispersion, and the SMA capital', () => {
    const vs = load('C17');
    const [t] = wave2ExperimentTables(manifestOf('C17', vs), vs, 'en');
    const row = t.rows[0].map(String);
    expect(row[2]).toMatch(/176/);
    expect(row[3]).toMatch(/0\.97/);
    const cell = (vs[0].outputs as { cells: Array<{ id: string; capital: { lda_splice: { iqr_over_truth: number; ratio_to_truth: { median: number } } } }> }).cells.find((c) => c.id === 'y10-h20000')!;
    expect(row[3]).toBe(formatNumber(cell.capital.lda_splice.ratio_to_truth.median, 'en', { decimals: 2 }));
    expect(row[4]).toBe(formatNumber(cell.capital.lda_splice.iqr_over_truth, 'en', { decimals: 2 }));
    expect(row[5]).toMatch(/144/);
  });
});

describe('Benchmark: a comparison in the case terms or an exclusion with its reason', () => {
  it('compares C10, C11, C13 and C17 and excludes C14 and C15 with a reason in both languages', () => {
    expect([...W2_BENCHMARK_CASES].sort()).toEqual(['C10', 'C11', 'C13', 'C17']);
    for (const id of ['C14', 'C15']) {
      expect(NO_BENCHMARK[id], id).toBeDefined();
      expect(NO_BENCHMARK[id].en.length, id).toBeGreaterThan(40);
      expect(NO_BENCHMARK[id].es.length, id).toBeGreaterThan(40);
      expect(NO_BENCHMARK[id].es, id).not.toBe(NO_BENCHMARK[id].en);
      expect(W2_BENCHMARK_CASES.has(id), id).toBe(false);
    }
    for (const id of Object.keys(NO_BENCHMARK)) {
      expect(NO_BENCHMARK[id].en.length, id).toBeGreaterThan(20);
      expect(NO_BENCHMARK[id].es, id).not.toBe(NO_BENCHMARK[id].en);
    }
  });
  it('leaves no new case without a section: own, U6, W2, or excluded', () => {
    for (const id of W2_CASES) {
      const homes = [HAS_OWN_BENCHMARK.has(id), U6_BENCHMARK_CASES.has(id), W2_BENCHMARK_CASES.has(id), id in NO_BENCHMARK].filter(Boolean);
      expect(homes.length, id).toBe(1);
    }
  });
  for (const id of ['C10', 'C11', 'C13', 'C17']) {
    it(`${id}: tables with rows, no gap in either language`, () => {
      const vs = load(id);
      for (const lang of ['en', 'es'] as const) {
        const tables = wave2BenchmarkTables(manifestOf(id, vs), vs, lang);
        expect(tables.length, id).toBeGreaterThan(0);
        for (const t of tables) {
          expect(t.rows.length, `${id} ${t.key}`).toBeGreaterThan(0);
          for (const r of t.rows) expect(r.length).toBe(t.head.length);
        }
        expect(flat(tables), `${id} ${lang}`).not.toMatch(BAD);
      }
    });
  }
  it('C10: every rung against the Monte Carlo reference, the rung that did not run with its reason', () => {
    const vs = load('C10');
    const tables = wave2BenchmarkTables(manifestOf('C10', vs), vs, 'en');
    const rungs = tables.find((t) => t.key.startsWith('rungs'))!;
    expect(rungs.rows.length).toBe(8);
    const text = rungs.rows.map((r) => r.map(String).join(' | '));
    expect(text.some((r) => /Student-t/i.test(r) && NOT_AVAILABLE.test(r) && /no Student-t twist is specified/.test(r))).toBe(true);
    const ref = text.find((r) => /reference/i.test(r));
    expect(ref).toBeDefined();
  });
  it('C11: the ladder by FZ0 and by membership of the model confidence set', () => {
    const vs = load('C11');
    const [t] = wave2ExperimentTables(manifestOf('C11', vs), vs, 'en');
    expect(t).toBeDefined();
    const tables = wave2BenchmarkTables(manifestOf('C11', vs), vs, 'en');
    const text = flat(tables);
    expect(text).toMatch(/FZ0|score/i);
    expect(text).toMatch(/in the set|inside|Yes|No/i);
    expect(text).toMatch(/not available|no disponible/i);
  });
  it('C13: the detection rates of each deficiency, by test', () => {
    const vs = load('C13');
    const text = flat(wave2BenchmarkTables(manifestOf('C13', vs), vs, 'en'));
    expect(text).toMatch(/85\.0\s?%/);
    expect(text).toMatch(/92\.0\s?%/);
  });
  it('C17: every LDA rung against the true quantile and the SMA, the rung without a summary with its reason', () => {
    const vs = load('C17');
    const v = JSON.parse(JSON.stringify(vs[0])) as VariantArtifact<{ cells: Array<{ id: string; capital: Record<string, unknown> }> }>;
    for (const c of v.outputs.cells) c.capital.scenario = { summary: null, reason: 'the scenario reason of the test' };
    const text = flat(wave2BenchmarkTables(manifestOf('C17', [v]), [v], 'en'));
    expect(text).toMatch(/UNVERIFIED/);
    expect(text).toMatch(/SMA|standardised/i);
    expect(text).toContain('the scenario reason of the test');
    expect(text).toMatch(/not available/i);
  });
});
