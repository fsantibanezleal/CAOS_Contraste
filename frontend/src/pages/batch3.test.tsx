// Wave 2 batch 3 on the cross-case pages: C02, C12, C16, C18, C20 and C21 appear on Experiments with one headline row per
// variant in the case's own measures, and on Benchmark with a comparison in the case's own terms or an honest exclusion.
// The C01 scorecard table is for C01 only: any other case without a section gets the generic impact table. Every number is
// read from the contract fixtures here (they share the documents' shape); a field the artifact leaves null reads "not
// available" with its reason.
import { readFileSync } from 'node:fs';
import { formatNumber, pick } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { HAS_OWN_BENCHMARK, NO_BENCHMARK } from './Benchmark';
import { groupCases, sectionKindOf, topRow } from './Experiments';
import { U6_BENCHMARK_CASES, U6_CASES } from './U6Sections';
import { W2_BENCHMARK_CASES, W2_CASES } from './Wave2Sections';
import { B3_BENCHMARK_CASES, B3_CASES, batch3BenchmarkTables, batch3ExperimentTables, impactTables } from './Batch3Sections';

const NOT_AVAILABLE = /not available|no disponible/i;
const BAD = /NaN|undefined|Infinity|\[object/;
const fixture = (dir: string, file: string) => JSON.parse(readFileSync(new URL(`../../../docs/contracts/fixtures/${dir}/${file}`, import.meta.url), 'utf8')) as VariantArtifact<unknown>;
const manifestOf = (id: string, vs: Array<VariantArtifact<unknown>>) =>
  ({ case_id: id, artifacts: vs.map((v) => ({ role: 'variant', variant_id: v.variant_id, title: { en: `A long title of ${v.variant_id}`, es: `Un título largo de ${v.variant_id}` }, short_title: { en: `Fixture ${v.variant_id}`, es: `Prueba ${v.variant_id}` } })) }) as unknown as CaseManifest;

const FIXTURES: Record<string, [string, string[]]> = {
  C02: ['c02', ['variant-horizon-h1-fixture.json', 'variant-horizon-pooled-fixture.json']],
  C12: [
    'c12',
    [
      'variant-swap-exposure-single-swap-fixture.json',
      'variant-swap-exposure-netting-set-fixture.json',
      'variant-swap-exposure-csa-mpor-10d-fixture.json',
      'variant-swap-exposure-csa-mpor-20d-fixture.json',
      'variant-swap-exposure-with-im-fixture.json',
      'variant-swap-exposure-wrong-way-risk-fixture.json',
    ],
  ],
  C16: [
    'c16',
    [
      'variant-scenario-lcr-standard-fixture.json',
      'variant-scenario-list-adverse-fixture.json',
      'variant-scenario-list-extreme-fixture.json',
      'variant-scenario-fast-run-fixture.json',
      'variant-scenario-htm-losses-fixture.json',
      'variant-reverse-fixture.json',
    ],
  ],
  C18: ['c18', ['variant-scenario-baseline-fixture.json', 'variant-scenario-eba-2025-adverse-fixture.json', 'variant-scenario-fed-2026-severely-adverse-fixture.json', 'variant-scenario-ngfs-delayed-transition-fixture.json', 'variant-aggregation-fixture.json', 'variant-reverse-fixture.json']],
  C20: ['c20', ['variant-shock-fixture.json', 'variant-shift-fixture.json', 'variant-seeds-fixture.json', 'variant-perturbation-fixture.json', 'variant-leakage-fixture.json']],
  C21: ['c21', ['variant-year-pair-fixture.json']],
};
const load = (id: string) => FIXTURES[id][1].map((f) => fixture(FIXTURES[id][0], f));
const flat = (tables: Array<{ head: string[]; rows: unknown[][] }>) => tables.flatMap((t) => t.rows.map((r) => r.map(String).join(' | '))).join('\n');
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x)) as T;
const rowOf = (id: string, variant: string, lang: 'en' | 'es' = 'en') => {
  const vs = load(id);
  const [t] = batch3ExperimentTables(manifestOf(id, vs), vs, lang);
  const i = vs.findIndex((v) => v.variant_id === variant);
  expect(i, `${id} ${variant}`).toBeGreaterThanOrEqual(0);
  return t.rows[i].map(String);
};

// every built case of the product at this batch (C19 is planned)
const BUILT = ['c01', 'c02', 'c03', 'c04', 'c05', 'c06', 'c07', 'c08', 'c09', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c20', 'c21', 'c22'];

describe('the Experiments case tabs are grouped by the question family, six more cases included', () => {
  const caseTabs = BUILT.map((id) => ({ id, label: id.toUpperCase(), content: null }));
  const groups = groupCases(caseTabs.filter((c) => c.id !== 'c22'));
  const by = (lang: 'en' | 'es') => Object.fromEntries(groups.map((g) => [pick(g.label, lang), g.tabs.map((t) => t.id)]));
  it('holds no group above six peer tabs and loses no case', () => {
    for (const g of groups) expect(g.tabs.length, g.id).toBeLessThanOrEqual(6);
    expect(groups.flatMap((g) => g.tabs.map((t) => t.id)).sort()).toEqual(BUILT.filter((id) => id !== 'c22').sort());
  });
  it('puts C18 in the capital family, relabelled, in both languages', () => {
    expect(by('en')['Capital, aggregation and stress']).toEqual(['c10', 'c17', 'c18']);
    expect(by('es')['Capital, agregación y estrés']).toEqual(['c10', 'c17', 'c18']);
    expect(groups.find((g) => g.id === 'capital')).toBeDefined();
  });
  it('makes ML and AI risk a family of its own with C20 and C21', () => {
    expect(by('en')['ML and AI risk']).toEqual(['c20', 'c21']);
    expect(by('es')['Riesgo de ML e IA']).toEqual(['c20', 'c21']);
  });
  it('keeps C02 in PD, and C12 and C16 in market and balance-sheet risk, which makes six tabs: the limit', () => {
    expect(by('en')['Credit scoring and PD']).toEqual(['c01', 'c02', 'c03', 'c04', 'c05']);
    expect(by('en')['Market and balance-sheet risk']).toEqual(['c11', 'c12', 'c13', 'c14', 'c15', 'c16']);
    expect(by('es')['Riesgo de mercado y de balance']).toHaveLength(6);
  });
  it('keeps the other families as they were', () => {
    expect(by('en')['Credit losses: provisions, severity and exposure']).toEqual(['c06', 'c07', 'c08', 'c09']);
  });
  it('holds at most six groups in the top row, with C22 in the design group after Coverage, Protocol and Metrics, in both languages', () => {
    const design = [
      { id: 'coverage', label: 'Coverage', content: null },
      { id: 'protocol', label: 'Protocol', content: null },
      { id: 'metrics', label: 'Metrics', content: null },
    ];
    for (const lang of ['en', 'es'] as const) {
      const top = topRow(design, caseTabs, lang);
      expect(top.length, lang).toBeLessThanOrEqual(6);
      expect(top.map((g) => g.id)).toEqual(['design', 'pd', 'credit-losses', 'capital', 'market-balance', 'ml-ai-risk']);
      expect(top[0].tabs.map((t) => t.id)).toEqual(['coverage', 'protocol', 'metrics', 'c22']);
      expect(top[0].tabs[3].label).toBe(lang === 'en' ? 'Validating the validator (C22)' : 'Validar al validador (C22)');
      for (const g of top) expect(g.tabs.length, g.id).toBeLessThanOrEqual(6);
      expect(top.slice(1).flatMap((g) => g.tabs.map((t) => t.id)).sort()).toEqual(BUILT.filter((id) => id !== 'c22').sort());
    }
  });
});

describe('the C01 scorecard table is for C01 only', () => {
  it('registers the six cases and keeps them out of the other sections', () => {
    expect([...B3_CASES].sort()).toEqual(['C02', 'C12', 'C16', 'C18', 'C20', 'C21']);
    for (const id of B3_CASES) {
      expect(U6_CASES.has(id), id).toBe(false);
      expect(W2_CASES.has(id), id).toBe(false);
    }
  });
  it('routes every case to its own section and never a case but C01 to the scorecard', () => {
    expect(sectionKindOf('C01')).toBe('scorecard');
    for (let n = 2; n <= 22; n++) {
      const id = `C${String(n).padStart(2, '0')}`;
      expect(sectionKindOf(id), id).not.toBe('scorecard');
    }
    for (const id of B3_CASES) expect(sectionKindOf(id), id).toBe('batch3');
    for (const id of W2_CASES) expect(sectionKindOf(id), id).toBe('wave2');
    for (const id of U6_CASES) expect(sectionKindOf(id), id).toBe('u6');
    expect(sectionKindOf('C19')).toBe('generic');
  });
});

describe('every batch 3 case has an Experiments table with one headline row per variant', () => {
  for (const id of Object.keys(FIXTURES)) {
    it(`${id}: one row per variant, no gap in either language, Spanish headers in Spanish`, () => {
      const vs = load(id);
      const m = manifestOf(id, vs);
      for (const lang of ['en', 'es'] as const) {
        const tables = batch3ExperimentTables(m, vs, lang);
        expect(tables.length, id).toBeGreaterThan(0);
        expect(tables.reduce((a, t) => a + t.rows.length, 0), id).toBe(vs.length);
        vs.forEach((v, i) => expect(String(tables[0].rows[i][0]), id).toContain(`${lang === 'en' ? 'Fixture' : 'Prueba'} ${v.variant_id}`));
        for (const t of tables) for (const r of t.rows) expect(r.length, id).toBe(t.head.length);
        expect(flat(tables), `${id} ${lang}`).not.toMatch(BAD);
        expect(new Set(tables[0].head).size, `${id} unique headers`).toBe(tables[0].head.length);
      }
      const en = batch3ExperimentTables(m, vs, 'en').flatMap((t) => t.head);
      const es = batch3ExperimentTables(m, vs, 'es').flatMap((t) => t.head);
      expect(es.filter((h, i) => h === en[i] && /[a-z]{4,}/.test(h) && !/^(Brier|CET1|CVA|SA-CCR|EEPE|ORE|PPNR|AUC|LCR)/.test(h)), `${id} headers left in English`).toEqual([]);
    });
  }

  it('C02: horizon, records, defaults, AUC of the champion and of the best rung, calibration light, transfer change', () => {
    const [h1, pooled] = [rowOf('C02', 'fixture-h1'), rowOf('C02', 'fixture-pooled')];
    expect(h1[1]).toMatch(/1/);
    expect(h1[2]).toMatch(/7,027/);
    expect(h1[3]).toMatch(/271/);
    expect(h1[4]).toMatch(/0\.820/);
    expect(h1[5]).toMatch(/0\.880/);
    expect(h1[5]).toMatch(/P4/);
    expect(h1[6]).toMatch(/green/i);
    expect(h1[7]).toMatch(/-0\.040/);
    expect(pooled[1]).toMatch(/pooled/i);
    expect(pooled[7]).toMatch(NOT_AVAILABLE);
    expect(pooled[7]).toContain('firm overlap');
    expect(rowOf('C02', 'fixture-pooled', 'es')[1]).toMatch(/agrupad/i);
    expect(rowOf('C02', 'fixture-h1', 'es')[6]).toMatch(/verde/i);
  });
  it('C02: a champion without a transfer cell shows not available with the reason of the document', () => {
    const vs = load('C02');
    const v = clone(vs[0]) as VariantArtifact<{ transfer: { cells: unknown[] } }>;
    v.outputs.transfer.cells = [];
    const [t] = batch3ExperimentTables(manifestOf('C02', [v]), [v], 'en');
    expect(String(t.rows[0][7])).toMatch(NOT_AVAILABLE);
    expect(String(t.rows[0][7])).toContain('firm overlap');
  });

  it('C12: EEPE, CVA, SA-CCR EAD, the effect of IM or of the wrong-way factor, and the ORE gap with its sign', () => {
    const im = rowOf('C12', 'fixture-with-im');
    expect(im[1]).toMatch(/3,?794|3\.79/);
    expect(im[2]).toMatch(/378/);
    expect(im[3]).toMatch(/172/);
    const o = load('C12').find((x) => x.variant_id === 'fixture-with-im')!.outputs as { initial_margin: { ee_vm_only: { values: number[] } }; exposure: { ee: { values: number[] } } };
    const vm = Math.max(...o.initial_margin.ee_vm_only.values);
    const withIm = Math.max(...o.exposure.ee.values);
    expect(im[4]).toContain(`${formatNumber(Math.round(vm), 'en')} USD`);
    expect(im[4]).toContain(`${formatNumber(Math.round(withIm), 'en')} USD`);
    expect(vm).toBeGreaterThan(withIm);
    expect(im[5]).toMatch(/\+15\.18/);
    expect(im[5]).toMatch(/\+1\.51/);
    const wrong = rowOf('C12', 'fixture-wrong-way-risk');
    expect(wrong[4]).toMatch(/5,?293/);
    expect(wrong[4]).toMatch(/3,?781/);
    expect(wrong[5]).toMatch(NOT_AVAILABLE);
    expect(wrong[5]).toMatch(/different model/);
    const plain = rowOf('C12', 'fixture-single-swap');
    expect(plain[4]).toMatch(NOT_AVAILABLE);
    expect(rowOf('C12', 'fixture-with-im', 'es')[5]).toMatch(/\+15,18/);
  });

  it('C16: the survival period as a day or as surviving the horizon, the LCR where computed, the multiplier per base', () => {
    const adverse = rowOf('C16', 'fixture-list-adverse');
    expect(adverse[1]).toMatch(/68/);
    expect(adverse[1]).toMatch(/125/);
    expect(adverse[2]).toMatch(NOT_AVAILABLE);
    expect(adverse[2]).toContain('run-off ladder');
    const fast = rowOf('C16', 'fixture-fast-run');
    expect(fast[1]).toMatch(/survives the horizon/i);
    expect(fast[1]).toMatch(/5/);
    const lcr = rowOf('C16', 'fixture-lcr-standard');
    expect(lcr.some((c) => /173\.24\s?%/.test(c))).toBe(true);
    expect(lcr[1]).toMatch(NOT_AVAILABLE);
    expect(lcr[1]).toContain('30-day aggregate ratio');
    const rev = rowOf('C16', 'fixture-reverse');
    expect(rev[3]).toMatch(/2\.23/);
    expect(rev[3]).toMatch(/1\.46/);
    expect(rev[3]).toMatch(NOT_AVAILABLE);
    expect(rev[3]).toContain('no bracket exists');
    expect(rowOf('C16', 'fixture-fast-run', 'es')[1]).toMatch(/sobrevive el horizonte/i);
  });

  it('C18: CET1 loss-only and with PPNR, the simple-sum capital, the dependence band, and the reverse distance', () => {
    const base = rowOf('C18', 'fixture-baseline');
    expect(base[1]).toMatch(/9\.41\s?%/);
    expect(base[2]).toMatch(/14\.98\s?%/);
    expect(base[3]).toMatch(/1,?710/);
    expect(base[4]).toMatch(/1,?060/);
    expect(base[4]).toMatch(/2,?018/);
    expect(base[5]).toMatch(NOT_AVAILABLE);
    const agg = rowOf('C18', 'fixture-t-copula-aggregation');
    expect(agg[1]).toMatch(NOT_AVAILABLE);
    expect(agg[1]).toMatch(/aggregation only/);
    expect(agg[4]).toMatch(/\d/);
    const rev = rowOf('C18', 'fixture-reverse-stress');
    expect(rev[5]).toMatch(/1\.485/);
    expect(rev[6]).toMatch(/33\.18\s?%/);
    expect(rev[3]).toMatch(NOT_AVAILABLE);
  });

  it('C20: each kind states its headline: the AUC of the shocks, the worst-subsample gap, the seed dispersion, the noise degradation, the leak', () => {
    const shock = rowOf('C20', 'fixture-sgcd-seen');
    expect(shock[2]).toMatch(/seen/i);
    expect(shock[3]).toMatch(/0\.74/);
    const shift = rowOf('C20', 'fixture-fed-shift');
    expect(shift[3]).toMatch(/-0\.08/);
    const seeds = rowOf('C20', 'fixture-seeds');
    expect(seeds[3]).toMatch(/0\.004/);
    const pert = rowOf('C20', 'fixture-perturbation');
    expect(pert[3]).toMatch(/-0\.001/);
    expect(pert[4]).toMatch(/0\.10/);
    const leak = rowOf('C20', 'fixture-leakage');
    expect(leak[3]).toMatch(/Yes/);
    expect(leak[4]).toContain('fixture_leak');
    expect(rowOf('C20', 'fixture-leakage', 'es')[3]).toMatch(/Sí/);
  });
  it('C20: a preset noise scale the grid does not hold shows not available, never a number', () => {
    const vs = load('C20');
    const v = clone(vs.find((x) => x.variant_id === 'fixture-perturbation')!) as VariantArtifact<{ preset_eps: number }>;
    v.outputs.preset_eps = 9;
    const [t] = batch3ExperimentTables(manifestOf('C20', [v]), [v], 'en');
    expect(String(t.rows[0][3])).toMatch(NOT_AVAILABLE);
  });

  it('C21: the year pair, the adverse impact ratio, the employment-benchmark flag, the conditional disparity and its replication', () => {
    const [row] = [rowOf('C21', 'fixture-2018-19')];
    expect(row[1]).toMatch(/2018/);
    expect(row[1]).toMatch(/2019/);
    expect(row[2]).toMatch(/0\.91/);
    expect(row[3]).toMatch(/employment benchmark/);
    expect(row[4]).toMatch(/0\.61/);
    expect(row[5]).toMatch(/Yes/);
    const es = rowOf('C21', 'fixture-2018-19', 'es');
    expect(es[3]).toMatch(/referencia/i);
    expect(es[5]).toMatch(/Sí/);
  });
  it('C21: a confirmation the document leaves null shows not available with its reason', () => {
    const vs = load('C21');
    const v = clone(vs[0]) as VariantArtifact<{ attributes: Array<{ contrasts: Array<{ confirmation: { estimate: unknown; reason: unknown } }> }> }>;
    for (const a of v.outputs.attributes)
      for (const c of a.contrasts) c.confirmation = { estimate: null, reason: 'the reason of the test' };
    const [t] = batch3ExperimentTables(manifestOf('C21', [v]), [v], 'en');
    expect(String(t.rows[0][5])).toMatch(NOT_AVAILABLE);
    expect(String(t.rows[0][5])).toContain('the reason of the test');
    expect(String(t.rows[0][5])).not.toMatch(/Yes/);
  });
});

describe('the fallback table of a case without a section reads the impact items, never the C01 fields', () => {
  it('a C16 fixture: one row per (variant, item), the unit beside the value, a null value read as not available with the label', () => {
    const vs = load('C16');
    const tables = impactTables(manifestOf('C16', vs), vs, 'en');
    expect(tables).toHaveLength(1);
    const items = vs.reduce((a, v) => a + Object.keys(v.impact).length, 0);
    expect(tables[0].rows.length).toBe(items);
    const text = flat(tables);
    expect(text).toMatch(/1\.73/);
    expect(text).toMatch(/48/);
    expect(text).toMatch(NOT_AVAILABLE);
    expect(text).not.toMatch(BAD);
    expect(text).not.toMatch(/AUC|Jeffreys|PSI|Default rate/);
    const nullRow = tables[0].rows.map((r) => r.map(String)).find((r) => r.join(' ').includes('Fixture fixture-fast-run') && NOT_AVAILABLE.test(r.join(' ')));
    expect(nullRow).toBeDefined();
    expect(nullRow!.join(' ')).toMatch(/Spanish|Run-off|LCR|survival/i);
  });
  it('a document with no outputs.n and no scorecard test rows still yields its rows, in both languages', () => {
    const vs = load('C16');
    for (const lang of ['en', 'es'] as const) {
      const [t] = impactTables(manifestOf('C16', vs), vs, lang);
      for (const r of t.rows) expect(r.length).toBe(t.head.length);
    }
    const [es] = impactTables(manifestOf('C16', vs), vs, 'es');
    expect(es.head.join(' ')).toMatch(/Variante/);
  });
});

describe('Benchmark: a comparison in the case terms or an exclusion with its reason', () => {
  it('compares C02, C12, C18 and C20 and excludes C16 and C21 with a reason in both languages', () => {
    expect([...B3_BENCHMARK_CASES].sort()).toEqual(['C02', 'C12', 'C18', 'C20']);
    for (const id of ['C16', 'C21']) {
      expect(NO_BENCHMARK[id], id).toBeDefined();
      expect(NO_BENCHMARK[id].en.length, id).toBeGreaterThan(40);
      expect(NO_BENCHMARK[id].es.length, id).toBeGreaterThan(40);
      expect(NO_BENCHMARK[id].es, id).not.toBe(NO_BENCHMARK[id].en);
      expect(B3_BENCHMARK_CASES.has(id), id).toBe(false);
    }
    expect(NO_BENCHMARK.C21.en).toMatch(/disparity/i);
  });
  it('leaves no batch 3 case without a section: own, U6, W2, B3, or excluded', () => {
    for (const id of B3_CASES) {
      const homes = [HAS_OWN_BENCHMARK.has(id), U6_BENCHMARK_CASES.has(id), W2_BENCHMARK_CASES.has(id), B3_BENCHMARK_CASES.has(id), id in NO_BENCHMARK].filter(Boolean);
      expect(homes.length, id).toBe(1);
    }
  });
  for (const id of ['C02', 'C12', 'C18', 'C20']) {
    it(`${id}: tables with rows, no gap in either language`, () => {
      const vs = load(id);
      for (const lang of ['en', 'es'] as const) {
        const tables = batch3BenchmarkTables(manifestOf(id, vs), vs, lang);
        expect(tables.length, id).toBeGreaterThan(0);
        for (const t of tables) {
          expect(t.rows.length, `${id} ${t.key}`).toBeGreaterThan(0);
          for (const r of t.rows) expect(r.length).toBe(t.head.length);
          expect(new Set(t.head).size, `${id} unique headers`).toBe(t.head.length);
        }
        expect(flat(tables), `${id} ${lang}`).not.toMatch(BAD);
      }
    });
  }
  it('C12: one row per variant against ORE, the gap signed, the variant without a reconciliation with its reason', () => {
    const vs = load('C12');
    const [t] = batch3BenchmarkTables(manifestOf('C12', vs), vs, 'en');
    expect(t.rows).toHaveLength(vs.length);
    const im = t.rows.map((r) => r.map(String)).find((r) => r[0].includes('fixture-with-im'))!;
    expect(im.join(' ')).toMatch(/\+15\.18/);
    expect(im.join(' ')).toMatch(/reconciled/i);
    const wrong = t.rows.map((r) => r.map(String)).find((r) => r[0].includes('fixture-wrong-way-risk'))!;
    expect(wrong.join(' ')).toMatch(NOT_AVAILABLE);
    expect(wrong.join(' ')).toMatch(/different model/);
  });
  it('C18: the rungs of the dependence band, the lower bound to the worst case', () => {
    const vs = load('C18');
    const tables = batch3BenchmarkTables(manifestOf('C18', vs), vs, 'en');
    const agg = tables.find((t) => t.key.includes('fixture-t-copula-aggregation'))!;
    expect(agg.rows).toHaveLength(8);
    const text = agg.rows.map((r) => r.map(String).join(' | '));
    expect(text.some((r) => /lower bound/i.test(r))).toBe(true);
    expect(text.some((r) => /worst case/i.test(r))).toBe(true);
    expect(text.some((r) => /simple sum/i.test(r))).toBe(true);
    expect(tables.some((t) => t.key.includes('reverse'))).toBe(false);
  });
  it('C02: the champion against the challengers on the holdout, with the DeLong p of the difference', () => {
    const vs = load('C02');
    const tables = batch3BenchmarkTables(manifestOf('C02', vs), vs, 'en');
    const h1 = tables.find((t) => t.key.includes('fixture-h1'))!;
    expect(h1.rows).toHaveLength(2);
    const text = h1.rows.map((r) => r.map(String).join(' | '));
    expect(text[0]).toMatch(/Champion/);
    expect(text[1]).toMatch(/0\.060/);
    expect(text[1]).toMatch(/0\.02/);
  });
  it('C20: the seed ladder, one row per rung, with the AUC dispersion', () => {
    const vs = load('C20');
    const tables = batch3BenchmarkTables(manifestOf('C20', vs), vs, 'en');
    expect(tables).toHaveLength(1);
    expect(tables[0].rows).toHaveLength(1);
    expect(String(tables[0].rows[0].join(' '))).toMatch(/P4/);
    expect(String(tables[0].rows[0].join(' '))).toMatch(/0\.004/);
  });
});
