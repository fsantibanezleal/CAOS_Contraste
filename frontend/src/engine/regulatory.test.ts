// U9-W2: the live regulatory ports held to the regulatory-calculators document (docs/contracts/fixtures/regulatory, and
// data/derived/regulatory/calculators.json once the U9-P2 bake writes it) within 1e-9 relative, the SDD's lanes rule, and
// the regulation map's views rendered on the server from that document. Every assertion reads what the document holds:
// the CRE20 lookup against Tables 1, 6, 7 and 10 to 14 and the LTV steps, the output floor against RBC20.13 (101.5 and
// 95) and the RBC90.1 phase-in, the SBM aggregator under its three correlation scenarios with the MAR21.4(5)(b)
// fallback, the liquidity-horizon cascade of MAR33.4, and the parameter tables of CRE52.72, MAR50.16, MAR33.4 and
// MAR33.12, each parameter with its paragraph and in-force date. A null block shows "not available" with its reason.
import { readFileSync, existsSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { createElement as h, type ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../content/citations';
import { conform } from '../lib/contract.types';
import { escapeHtml, html, setLang } from '../workbench/c03/u6-testkit';
import {
  REGULATORY_CALCULATORS,
  SCENARIOS,
  adjustForCurrencyMismatch,
  bucketCharge,
  cascadeTerms,
  creditEquivalentRwa,
  crossBucketCharge,
  entryById,
  findCell,
  floorBreakdown,
  flooredRwa,
  gridRows,
  liquidityCascadeEs,
  ltvRow,
  ltvSteps,
  matrixOf,
  numberOf,
  parameterTable,
  phaseInRow,
  sbmAggregate,
  scenarioRho,
  subsetMembership,
  vectorOf,
  type RegulatoryDoc,
} from './regulatory';
import { REGISTERED_SECTIONS } from '../pages/methodologyRegistry';
import {
  CascadeCard,
  CascadePart,
  CcrPart,
  Cre20Card,
  CreditPart,
  FloorCard,
  FloorPart,
  ParameterCard,
  RegulationBody,
  SbmCard,
  SbmPart,
  WorkedExamplesCard,
  methodologySection,
} from '../pages/methodology/regulation';

const read = (url: URL): RegulatoryDoc => JSON.parse(readFileSync(url, 'utf8')) as RegulatoryDoc;
const fixtureUrl = new URL('../../../docs/contracts/fixtures/regulatory/calculators-fixture.json', import.meta.url);
const bakedUrl = new URL('../../../data/derived/regulatory/calculators.json', import.meta.url);
const fixture = read(fixtureUrl);
// the live ports are held to the fixture now and to the bake's document as soon as it exists
const documents: Array<[string, RegulatoryDoc]> = [['the contract fixture', fixture], ...(existsSync(bakedUrl) ? ([['the bake', read(bakedUrl)]] as Array<[string, RegulatoryDoc]>) : [])];
const clone = <T,>(v: T): T => structuredClone(v);

const close = (got: number, want: number, rel = 1e-9) => {
  expect(Math.abs(got - want), `${got} against ${want}`).toBeLessThanOrEqual(rel * Math.max(Math.abs(want), 1e-300));
};

const out = (id: string, name: string, doc: RegulatoryDoc = fixture): number => numberOf(entryById(doc, id)!.outputs, name);
const inp = (id: string, name: string, doc: RegulatoryDoc = fixture): number => numberOf(entryById(doc, id)!.inputs, name);

describe('the descriptor of the regulatory-calculators document', () => {
  for (const [name, doc] of documents) {
    it(`describes ${name} key by key`, () => {
      expect(conform(doc, REGULATORY_CALCULATORS)).toEqual([]);
    });
  }
  it('refuses a key the web does not declare and one it lacks', () => {
    const odd = clone(fixture) as unknown as Record<string, unknown>;
    odd.planted = 1;
    delete odd.cre20_grid;
    const found = conform(odd, REGULATORY_CALCULATORS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/cre20_grid: declared by the web, not written by the pipeline/);
  });
});

describe('the CRE20 lookup equals the document', () => {
  for (const [name, doc] of documents) {
    it(`finds every one of the ${doc.cre20_grid.length} cells of ${name} by its own key`, () => {
      expect(doc.cre20_grid.length).toBeGreaterThan(70);
      for (const row of doc.cre20_grid) {
        const hit = findCell(doc.cre20_grid, row.exposure_class, row.key, { shortTerm: row.short_term, cashFlowDependent: row.cash_flow_dependent, counterpartyWeight: row.counterparty_weight });
        expect(hit, `${row.exposure_class} ${row.key}`).toBe(row);
      }
    });
  }
  const g = fixture.cre20_grid;
  const w = (cls: Parameters<typeof findCell>[1], key: string, o: Parameters<typeof findCell>[3] = {}) => findCell(g, cls, key, o)?.risk_weight;
  it('equals Tables 1, 2, 6, 7 and 10 of CRE20 (dossier 01 C)', () => {
    expect(['AAA to AA-', 'A+ to A-', 'BBB+ to BBB-', 'BB+ to B-', 'below B-', 'unrated'].map((k) => w('sovereign', k))).toEqual([0, 0.2, 0.5, 1, 1.5, 1]);
    expect(['0', '1', '2', '3', '4', '5', '6', '7'].map((k) => w('eca', k))).toEqual([0, 0, 0.2, 0.5, 1, 1, 1, 1.5]);
    expect(['AAA to AA-', 'A+ to A-', 'BBB+ to BBB-', 'BB+ to B-', 'below B-'].map((k) => w('bank-ecra', k))).toEqual([0.2, 0.3, 0.5, 1, 1.5]);
    expect(['AAA to AA-', 'A+ to A-', 'BBB+ to BBB-', 'BB+ to B-', 'below B-'].map((k) => w('bank-ecra', k, { shortTerm: true }))).toEqual([0.2, 0.2, 0.2, 0.5, 1.5]);
    expect(['A', 'B', 'C'].map((k) => w('bank-scra', k))).toEqual([0.4, 0.75, 1.5]);
    expect(['A', 'B', 'C'].map((k) => w('bank-scra', k, { shortTerm: true }))).toEqual([0.2, 0.5, 1.5]);
    expect(['AAA to AA-', 'A+ to A-', 'BBB+ to BBB-', 'BB+ to BB-', 'below BB-', 'unrated', 'investment-grade-unrated', 'sme-unrated', 'regulatory-retail-sme'].map((k) => w('corporate', k))).toEqual([0.2, 0.5, 0.75, 1, 1.5, 1, 0.65, 0.85, 0.75]);
  });
  it('equals CRE20.68, CRE20.57 to CRE20.60, CRE20.94 to CRE20.101 and CRE20.104 to CRE20.107', () => {
    expect(['regulatory', 'transactor', 'other'].map((k) => w('retail', k))).toEqual([0.75, 0.45, 1]);
    expect(['equity', 'speculative-unlisted', 'legislated-programme', 'subordinated-debt'].map((k) => w('equity', k))).toEqual([2.5, 4, 1, 1.5]);
    expect(['direct-credit-substitute', 'repo', 'securities-lending', 'forward-purchase', 'nif-ruf', 'transaction-related-contingent', 'commitment', 'trade-letter-of-credit', 'unconditionally-cancellable'].map((k) => w('ccf', k))).toEqual([1, 1, 1, 1, 0.5, 0.5, 0.4, 0.2, 0.1]);
    expect(['provision-below-20pct', 'provision-at-least-20pct', 'residential-non-cash-flow-dependent'].map((k) => w('defaulted', k))).toEqual([1.5, 1, 1]);
  });
  it('steps with the LTV at the edges of Tables 11 to 14, the upper edge belonging to its band', () => {
    const res = (ltv: number, cfd = false) => ltvRow(g, 'residential-re', ltv, { cashFlowDependent: cfd })?.risk_weight;
    expect([0, 0.5, 0.5000001, 0.6, 0.8, 0.8000001, 0.9, 1, 1.0000001, 1.4, 3].map((l) => res(l))).toEqual([0.2, 0.2, 0.25, 0.25, 0.3, 0.4, 0.4, 0.5, 0.7, 0.7, 0.7]);
    expect([0.4, 0.55, 0.7, 0.85, 0.95, 1.2].map((l) => res(l, true))).toEqual([0.3, 0.35, 0.45, 0.6, 0.75, 1.05]);
    const com = (ltv: number, cfd: boolean, cp: number | null = null) => ltvRow(g, 'commercial-re', ltv, { cashFlowDependent: cfd, counterpartyWeight: cp })?.risk_weight;
    expect([0.6, 0.6000001, 2].map((l) => com(l, true))).toEqual([0.7, 0.9, 1.1]);
    expect([0.8, 0.8000001].map((l) => com(l, true))).toEqual([0.9, 1.1]);
    // CRE20.85 Table 13: up to 60 percent min(60 percent, the counterparty's weight), above it the counterparty's weight
    expect([0.5, 0.7].map((l) => com(l, false, 0.2))).toEqual([0.2, 0.2]);
    expect([0.5, 0.7].map((l) => com(l, false, 1))).toEqual([0.6, 1]);
  });
  it('gives the steps of a class as the document orders them, and none for a class without LTV rows', () => {
    const steps = ltvSteps(g, 'residential-re', { cashFlowDependent: false });
    expect(steps.map((s) => s.upTo)).toEqual([0.5, 0.6, 0.8, 0.9, 1, 1.5]);
    expect(steps.map((s) => s.row.risk_weight)).toEqual([0.2, 0.25, 0.3, 0.4, 0.5, 0.7]);
    expect(ltvSteps(g, 'corporate', { cashFlowDependent: false })).toEqual([]);
    expect(ltvRow(g, 'sovereign', 0.5, { cashFlowDependent: false })).toBeNull();
  });
  it('returns null for a key outside the tables, never a placeholder weight', () => {
    expect(findCell(g, 'sovereign', 'AAA')).toBeNull();
    expect(findCell(g, 'bank-scra', 'D')).toBeNull();
    expect(gridRows(g, 'retail')).toHaveLength(3);
  });
  it('applies the currency mismatch of CRE20.92: 1.5 times the weight, at most 150 percent', () => {
    const a = adjustForCurrencyMismatch(g, 0.75)!;
    close(a.adjusted, 1.125);
    expect(a.capped).toBe(false);
    expect(a.multiplier.paragraph).toBe('CRE20.92');
    expect(adjustForCurrencyMismatch(g, 1.2)!.adjusted).toBe(1.5);
    expect(adjustForCurrencyMismatch(g, 1.2)!.capped).toBe(true);
    expect(adjustForCurrencyMismatch(g.filter((r) => r.exposure_class !== 'currency-mismatch'), 0.75)).toBeNull();
  });
  it('turns a conversion factor and a weight into the credit equivalent and the RWA', () => {
    const r = creditEquivalentRwa({ exposure: 100, ccf: 0.4, weight: 0.75 });
    close(r.creditEquivalent, 40);
    close(r.rwa, 30);
  });
});

describe('the output floor equals RBC20.4, RBC20.13 and the RBC90.1 phase-in', () => {
  for (const [name, doc] of documents) {
    it(`reproduces both official examples of ${name} within 1e-9`, () => {
      for (const id of ['rbc20-13-output-floor', 'rbc20-13-output-floor-capped']) {
        const e = entryById(doc, id)!;
        const cap = e.inputs.some((v) => v.name === 'cap_share') ? numberOf(e.inputs, 'cap_share') : null;
        close(flooredRwa(numberOf(e.inputs, 'rwa_nominated'), numberOf(e.inputs, 'rwa_sa_only'), numberOf(e.inputs, 'floor_factor'), cap), numberOf(e.outputs, 'rwa_floored'));
        for (const p of e.published) close(numberOf(e.outputs, p.name), p.value);
      }
    });
    it(`holds the factor of the examples to the phase-in of ${name}: 72.5 percent from 2028`, () => {
      expect(inp('rbc20-13-output-floor', 'floor_factor', doc)).toBe(phaseInRow(doc.output_floor_phase_in, 2028)!.factor);
    });
  }
  const pi = fixture.output_floor_phase_in;
  it('phases in 50, 55, 60, 65, 70 and 72.5 percent (RBC90.1 Table 1), 2028 and later at 72.5', () => {
    expect([2023, 2024, 2025, 2026, 2027, 2028].map((y) => phaseInRow(pi, y)?.factor)).toEqual([0.5, 0.55, 0.6, 0.65, 0.7, 0.725]);
    expect(phaseInRow(pi, 2031)?.factor).toBe(0.725);
    expect(phaseInRow(pi, 2022)).toBeNull();
    expect(phaseInRow(pi, 2024)).toMatchObject({ paragraph: 'RBC90.1', table: 'RBC90.1 Table 1', in_force_date: '2023-01-01' });
  });
  it('is the maximum of the nominated RWA and the factor times the standardised RWA, and the cap limits the increase', () => {
    close(flooredRwa(76, 140, 0.725), 101.5);
    close(flooredRwa(76, 140, 0.725, 0.25), 95);
    close(flooredRwa(120, 140, 0.725), 120);
    close(flooredRwa(120, 140, 0.725, 0.25), 120);
    close(flooredRwa(0, 100, 0.5), 50);
    // never below the nominated RWA
    for (const [n, s, f] of [[10, 0, 0.5], [50, 40, 0.725], [76, 140, 0.5], [1e6, 1, 0.725]]) expect(flooredRwa(n, s, f)).toBeGreaterThanOrEqual(n);
  });
  it('breaks the result into the floor base, the increase and whether the floor and the cap bind', () => {
    const b = floorBreakdown(76, 140, 0.725, 0.25);
    close(b.floor, 101.5);
    close(b.rwa, 95);
    close(b.increase, 19);
    expect(b).toMatchObject({ floorBinds: true, capBinds: true });
    const free = floorBreakdown(120, 140, 0.725, 0.25);
    expect(free).toMatchObject({ floorBinds: false, capBinds: false });
    expect(floorBreakdown(76, 140, 0.725)).toMatchObject({ floorBinds: true, capBinds: false });
    expect(b.pre).toBe(76);
  });
});

describe('the SBM aggregator equals MAR21.4 to MAR21.7', () => {
  it('uses max(2 rho - 1, 0.75 rho), rho and min(1.25 rho, 1) for the three scenarios', () => {
    expect(SCENARIOS).toEqual(['low', 'medium', 'high']);
    close(scenarioRho(0.5, 'low'), numberOf(entryById(fixture, 'sbm-low-and-high-scenarios')!.outputs, 'rho_low'));
    close(scenarioRho(0.5, 'medium'), 0.5);
    close(scenarioRho(0.5, 'high'), 0.625);
    close(scenarioRho(0.8, 'low'), 0.6);
    close(scenarioRho(0.8, 'high'), 1);
    for (const s of SCENARIOS) close(scenarioRho(1, s), 1);
  });
  for (const [name, doc] of documents) {
    it(`reproduces the scenario rows of ${name}`, () => {
      const e = entryById(doc, 'sbm-low-and-high-scenarios')!;
      const rho = numberOf(e.inputs, 'rho');
      for (const s of SCENARIOS) close(scenarioRho(rho, s), numberOf(e.outputs, `rho_${s}`));
    });
    for (const id of ['sbm-bucket-and-cross-bucket-aggregation', 'sbm-cross-bucket-fallback']) {
      it(`reproduces ${id} of ${name}: bucket charges, cross-bucket charges, fallback flags and the maximum`, () => {
        const e = entryById(doc, id)!;
        const input = { ws: [vectorOf(e.inputs, 'ws_1'), vectorOf(e.inputs, 'ws_2')], rho: [matrixOf(e.inputs, 'rho_1'), matrixOf(e.inputs, 'rho_2')], gamma: numberOf(e.inputs, 'gamma') };
        const res = sbmAggregate(input);
        for (const s of SCENARIOS) {
          close(res.scenarios[s].kb[0], numberOf(e.outputs, `k_b1_${s}`));
          close(res.scenarios[s].kb[1], numberOf(e.outputs, `k_b2_${s}`));
          close(res.scenarios[s].charge, numberOf(e.outputs, `cross_bucket_${s}`));
          expect(res.scenarios[s].fallback ? 1 : 0).toBe(numberOf(e.outputs, `fallback_${s}`));
        }
        close(res.charge, numberOf(e.outputs, 'sbm_charge'));
      });
    }
  }
  it('uses the fallback S_b = max(min(sum WS, K_b), -K_b) only when the radicand is negative', () => {
    const e = entryById(fixture, 'sbm-cross-bucket-fallback')!;
    const res = sbmAggregate({ ws: [vectorOf(e.inputs, 'ws_1'), vectorOf(e.inputs, 'ws_2')], rho: [matrixOf(e.inputs, 'rho_1'), matrixOf(e.inputs, 'rho_2')], gamma: 0.8 });
    expect(SCENARIOS.map((s) => res.scenarios[s].fallback)).toEqual([false, true, true]);
    expect(res.binding).toBe('medium');
    // K_b = 17.3205, S_b = +-20 before the fallback and +-17.3205 after it
    close(res.scenarios.medium.kb[0], Math.sqrt(300));
    close(res.scenarios.medium.sb[0], Math.sqrt(300));
    close(res.scenarios.medium.sb[1], -Math.sqrt(300));
    close(res.scenarios.medium.charge, 10.954451150103322);
    // the plain path of the low scenario keeps S_b = sum WS
    expect(res.scenarios.low.sb).toEqual([20, -20]);
  });
  it('gives |WS| for one factor and |sum WS| for perfectly correlated factors, and never a negative charge', () => {
    for (const s of SCENARIOS) {
      close(bucketCharge([-3], [1], s), 3);
      close(bucketCharge([2, 5], [1, 1, 1, 1], s), 7);
    }
    expect(bucketCharge([10, -10], [1, 0.9, 0.9, 1], 'medium')).toBeGreaterThanOrEqual(0);
    expect(crossBucketCharge([5], [5], 0.5, 'medium').charge).toBe(5);
    expect(crossBucketCharge([5, 5], [-5, 5], 1, 'medium').charge).toBeGreaterThanOrEqual(0);
  });
  it('moves with gamma and with the weighted sensitivities', () => {
    const e = entryById(fixture, 'sbm-bucket-and-cross-bucket-aggregation')!;
    const base = { ws: [vectorOf(e.inputs, 'ws_1'), vectorOf(e.inputs, 'ws_2')], rho: [matrixOf(e.inputs, 'rho_1'), matrixOf(e.inputs, 'rho_2')], gamma: 0.5 };
    const a = sbmAggregate(base).charge;
    expect(sbmAggregate({ ...base, gamma: 0.9 }).charge).toBeGreaterThan(a);
    expect(sbmAggregate({ ...base, ws: [base.ws[0], base.ws[1].map((x) => 2 * x)] }).charge).toBeGreaterThan(a);
  });
});

describe('the liquidity-horizon cascade equals MAR33.4', () => {
  const lhs = (doc: RegulatoryDoc) => parameterTable(doc, 'mar33-4-table-1')!.rows.map((r) => r.value);
  for (const [name, doc] of documents) {
    it(`reproduces both invariant cases of ${name}`, () => {
      const t = numberOf(entryById(doc, 'cascade-two-horizons')!.inputs, 't');
      close(liquidityCascadeEs(inp('cascade-two-horizons', 'es_t_p', doc), [inp('cascade-two-horizons', 'es_t_p_2', doc), 0, 0, 0], lhs(doc), t), out('cascade-two-horizons', 'es', doc));
      close(liquidityCascadeEs(inp('cascade-all-lh-ten', 'es_t_p', doc), [0, 0, 0, 0], lhs(doc), 10), out('cascade-all-lh-ten', 'es', doc));
    });
    it(`takes the liquidity horizons of ${name} from MAR33.4 Table 1: 10, 20, 40, 60 and 120 days`, () => {
      expect(lhs(doc)).toEqual([10, 20, 40, 60, 120]);
    });
  }
  it('is sqrt(ES_T(P)^2 + sum_j (ES_T(P, j) sqrt((LH_j - LH_{j-1}) / T))^2)', () => {
    close(liquidityCascadeEs(10, [6, 0, 0, 0], [10, 20, 40, 60, 120]), Math.sqrt(100 + 36));
    close(liquidityCascadeEs(10, [6, 5, 4, 3], [10, 20, 40, 60, 120]), Math.sqrt(100 + 36 * 1 + 25 * 2 + 16 * 2 + 9 * 6));
  });
  it('returns ES_T(P) when no factor has a horizon beyond 10 days, is at least ES_T(P) and is monotone in each ES_T(P, j)', () => {
    const L = [10, 20, 40, 60, 120];
    close(liquidityCascadeEs(10, [0, 0, 0, 0], L), 10);
    for (let j = 0; j < 4; j++) {
      const lo = [1, 1, 1, 1];
      const hi = [...lo];
      hi[j] = 3;
      expect(liquidityCascadeEs(10, hi, L)).toBeGreaterThan(liquidityCascadeEs(10, lo, L));
      expect(liquidityCascadeEs(10, lo, L)).toBeGreaterThanOrEqual(10);
    }
  });
  it('lists the terms with their weights sqrt((LH_j - LH_{j-1}) / T), the first without one', () => {
    const terms = cascadeTerms(10, [6, 5, 4, 3], [10, 20, 40, 60, 120]);
    expect(terms.map((x) => x.j)).toEqual([1, 2, 3, 4, 5]);
    close(terms[1].weight!, 1);
    close(terms[2].weight!, Math.sqrt(2));
    close(terms[4].weight!, Math.sqrt(6));
    expect(terms[0].weight).toBeNull();
    close(Math.sqrt(terms.reduce((s, x) => s + x.term ** 2, 0)), liquidityCascadeEs(10, [6, 5, 4, 3], [10, 20, 40, 60, 120]));
  });
  it('puts a risk factor in the subsets whose horizon it reaches (the nested sets Q(p, j))', () => {
    const L = [10, 20, 40, 60, 120];
    expect(subsetMembership(L, 10)).toEqual([1]);
    expect(subsetMembership(L, 20)).toEqual([1, 2]);
    expect(subsetMembership(L, 60)).toEqual([1, 2, 3, 4]);
    expect(subsetMembership(L, 120)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe('the document readers', () => {
  it('read a value by name and refuse an absent one, a wrong kind and a bad shape', () => {
    const e = entryById(fixture, 'sbm-bucket-and-cross-bucket-aggregation')!;
    expect(vectorOf(e.inputs, 'ws_1')).toEqual([10, -4, 6]);
    expect(matrixOf(e.inputs, 'rho_2')).toEqual([[1, 0.5], [0.5, 1]]);
    expect(() => numberOf(e.inputs, 'absent')).toThrow(/absent/);
    expect(() => numberOf(e.inputs, 'ws_1')).toThrow(/number/);
    expect(() => vectorOf(e.inputs, 'gamma')).toThrow(/vector/);
    expect(() => matrixOf([{ ...e.inputs[0], name: 'm', value: [1, 2, 3] }], 'm')).toThrow(/square/);
    expect(entryById(fixture, 'no-such-entry')).toBeUndefined();
    expect(parameterTable(fixture, 'cre52-72-table-2')!.rows.length).toBe(43);
  });
});

// ------------------------------------------------------------------------------------------------ the views

const LANGS = ['en', 'es'] as const;
const markup = (el: ReactElement, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(h(CitationsProvider, { items: CITATIONS, children: el }));
};
afterEach(() => setLang('en'));
const attr = (m: string, name: string) => m.match(new RegExp(`${name}="([^"]*)"`))?.[1];
/** The markup with every span that opens like `marker` removed whole (a balanced scan), as the gate skips formulas and translate="no". */
function dropSpans(m: string, marker: RegExp): string {
  let out = '';
  let i = 0;
  while (i < m.length) {
    const rest = m.slice(i);
    const open = rest.search(marker);
    if (open < 0) {
      out += rest;
      break;
    }
    out += rest.slice(0, open);
    let depth = 0;
    let end = i + open;
    const tag = /<(\/?)span\b[^>]*>/g;
    tag.lastIndex = i + open;
    for (let t = tag.exec(m); t; t = tag.exec(m)) {
      depth += t[1] ? -1 : 1;
      if (depth === 0) {
        end = tag.lastIndex;
        break;
      }
    }
    i = end > i + open ? end : i + open + 1;
  }
  return out;
}
/** The visible text of a markup as the gate's Spanish-number check reads it: no formula, no translate="no" span, no tag. */
const visibleText = (m: string) => dropSpans(m, /<span class="katex"|<span translate="no"/).replace(/<[^>]+>/g, ' ');
/** The numbers of a Spanish text that write a decimal point; a Spanish thousands group (27.345) passes, as in the gate. */
const decimalPoints = (text: string): string[] =>
  [...text.matchAll(/(?<![\w.,/:@#])(\d+)\.(\d+)(?:[eE][-+]?\d+)?(?![\w/@]|\.\d)/g)]
    .filter((x) => !/^[1-9]\d{0,2}(\.\d{3})+$/.test(text.slice(x.index).match(/^\d+(?:\.\d+)+/)?.[0] ?? x[0]))
    .map((x) => text.slice(Math.max(0, x.index - 25), x.index + x[0].length + 8));

describe('the CRE20 view', () => {
  it('shows the weight of the chosen cell with its table, paragraph and in-force date', () => {
    for (const lang of LANGS) {
      const m = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'sovereign', key: 'A+ to A-' } }), lang);
      const res = m.match(/<[^>]*data-result="cre20"[^>]*>/)![0];
      expect(attr(res, 'data-weight')).toBe('0.2');
      expect(attr(res, 'data-paragraph')).toBe('CRE20.7');
      expect(attr(res, 'data-table')).toBe('CRE20 Table 1');
      expect(attr(res, 'data-in-force')).toBe('2023-01-01');
      expect(m).toContain('CRE20.7');
      expect(m).toContain('2023-01-01');
    }
  });
  it('steps with the LTV: 80 percent of a residential home reads 30 percent (Table 11), cash-flow dependent 45 percent (Table 12)', () => {
    const a = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'residential-re', ltv: 0.8 } }));
    expect(attr(a.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-weight')).toBe('0.3');
    expect(attr(a.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-paragraph')).toBe('CRE20.82');
    const b = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'residential-re', ltv: 0.8, cashFlowDependent: true } }));
    expect(attr(b.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-weight')).toBe('0.45');
    expect(attr(b.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-paragraph')).toBe('CRE20.84');
  });
  it('takes the counterparty weight for commercial real estate that is not cash-flow dependent (Table 13)', () => {
    const m = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'commercial-re', ltv: 0.5, counterpartyWeight: 1 } }));
    expect(attr(m.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-weight')).toBe('0.6');
  });
  it('applies the currency mismatch and reads the conversion factor, the RWA per 100 of exposure following', () => {
    const m = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'retail', key: 'regulatory', mismatch: true, ccf: 'commitment' } }));
    const rwa = m.match(/<[^>]*data-result="rwa"[^>]*>/)![0];
    expect(attr(rwa, 'data-adjusted-weight')).toBe('1.125');
    expect(attr(rwa, 'data-ccf')).toBe('0.4');
    close(Number(attr(rwa, 'data-rwa')), 45);
    expect(attr(rwa, 'data-ccf-paragraph')).toBe('CRE20.94');
    expect(attr(rwa, 'data-mismatch-paragraph')).toBe('CRE20.92');
  });
  it('draws the steps of the class in the chart data: a series per variant, the document values only', () => {
    const m = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'residential-re', ltv: 0.7 } }));
    expect(m).toContain('data-steps="residential-re"');
    expect(attr(m.match(/<[^>]*data-steps="residential-re"[^>]*>/)![0], 'data-series')).toBe('2');
  });
  it('says "not available" with its reason, and draws no chart, when the document has no cell for the class', () => {
    const doc = clone(fixture);
    doc.cre20_grid = doc.cre20_grid.filter((r) => r.exposure_class !== 'residential-re');
    const m = markup(h(Cre20Card, { doc, initial: { cls: 'residential-re', ltv: 0.7 } }));
    expect(m).toContain('data-state="unavailable"');
    expect(m).not.toContain('data-steps=');
  });
  it('writes no decimal point in Spanish outside a marked reference', () => {
    const m = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'bank-ecra', key: 'A+ to A-' } }), 'es');
    expect(decimalPoints(visibleText(m))).toEqual([]);
    expect(m).toMatch(/Ponderador|ponderador/);
  });
});

describe('the output floor view', () => {
  it('opens on the RBC20.13 example: 76 nominated, 140 standardised, 72.5 percent, floored 101.5', () => {
    const m = markup(h(FloorCard, { doc: fixture }));
    const r = m.match(/<[^>]*data-result="floor"[^>]*>/)![0];
    close(Number(attr(r, 'data-rwa')), 101.5);
    expect(attr(r, 'data-factor')).toBe('0.725');
    expect(attr(r, 'data-year')).toBe('2028');
    expect(attr(r, 'data-paragraph')).toBe('RBC90.1');
    expect(attr(r, 'data-in-force')).toBe('2023-01-01');
    expect(attr(r, 'data-matches-document')).toBe('rbc20-13-output-floor');
  });
  it('gives 95 with the optional RBC90.2 cap of the increase at 25 percent', () => {
    const m = markup(h(FloorCard, { doc: fixture, initial: { capped: true } }));
    const r = m.match(/<[^>]*data-result="floor"[^>]*>/)![0];
    close(Number(attr(r, 'data-rwa')), 95);
    expect(attr(r, 'data-matches-document')).toBe('rbc20-13-output-floor-capped');
  });
  it('follows the phase-in year: 2023 floors at 50 percent of 140, below the nominated 76 so the floor does not bind', () => {
    const m = markup(h(FloorCard, { doc: fixture, initial: { year: 2023 } }));
    const r = m.match(/<[^>]*data-result="floor"[^>]*>/)![0];
    expect(attr(r, 'data-factor')).toBe('0.5');
    close(Number(attr(r, 'data-rwa')), 76);
    expect(attr(r, 'data-floor-binds')).toBe('false');
    expect(attr(r, 'data-matches-document')).toBeUndefined();
  });
  it('lists the six RBC90.1 rows, each with its paragraph and in-force date', () => {
    const m = markup(h(FloorCard, { doc: fixture }));
    const rows = [...m.matchAll(/<tr[^>]*data-phase-in="(\d{4})"[^>]*>/g)];
    expect(rows.map((x) => x[1])).toEqual(['2023', '2024', '2025', '2026', '2027', '2028']);
    for (const x of rows) {
      expect(attr(x[0], 'data-paragraph')).toBe('RBC90.1');
      expect(attr(x[0], 'data-in-force')).toBe('2023-01-01');
    }
  });
  it('says "not available" with its reason when the document has no phase-in', () => {
    const doc = clone(fixture);
    doc.output_floor_phase_in = [];
    const m = markup(h(FloorCard, { doc }));
    expect(m).toContain('data-state="unavailable"');
    expect(m).not.toContain('data-result="floor"');
  });
});

describe('the SBM view', () => {
  it('opens on the aggregation case: the charge is the maximum of the three scenarios, the high one binding', () => {
    const m = markup(h(SbmCard, { doc: fixture }));
    const r = m.match(/<[^>]*data-result="sbm"[^>]*>/)![0];
    close(Number(attr(r, 'data-charge')), 16.575584454250777);
    expect(attr(r, 'data-binding')).toBe('high');
    expect(attr(r, 'data-paragraph')).toBe('MAR21.7');
    expect(attr(r, 'data-in-force')).toBe('2023-01-01');
    const rows = [...m.matchAll(/<tr[^>]*data-scenario="(low|medium|high)"[^>]*>/g)];
    expect(rows.map((x) => x[1])).toEqual(['low', 'medium', 'high']);
    for (const x of rows) expect(attr(x[0], 'data-fallback')).toBe('false');
  });
  it('flags the MAR21.4(5)(b) fallback under the medium and high scenarios of the opposite-sign case, not under the low one', () => {
    const m = markup(h(SbmCard, { doc: fixture, initial: { preset: 'sbm-cross-bucket-fallback' } }));
    const rows = [...m.matchAll(/<tr[^>]*data-scenario="(low|medium|high)"[^>]*>/g)];
    expect(rows.map((x) => attr(x[0], 'data-fallback'))).toEqual(['false', 'true', 'true']);
    const r = m.match(/<[^>]*data-result="sbm"[^>]*>/)![0];
    close(Number(attr(r, 'data-charge')), 10.954451150103322);
    expect(attr(r, 'data-binding')).toBe('medium');
  });
  it('shows the three scenario correlations of the rho the reader sets', () => {
    const m = markup(h(SbmCard, { doc: fixture, initial: { rho: 0.8 } }));
    const rho = m.match(/<[^>]*data-result="rho"[^>]*>/)![0];
    close(Number(attr(rho, 'data-low')), 0.6);
    expect(attr(rho, 'data-medium')).toBe('0.8');
    expect(attr(rho, 'data-high')).toBe('1');
    expect(attr(rho, 'data-paragraph')).toBe('MAR21.6');
  });
  it('recomputes when the gamma or the scale of the second bucket moves', () => {
    const a = Number(attr(markup(h(SbmCard, { doc: fixture })).match(/<[^>]*data-result="sbm"[^>]*>/)![0], 'data-charge'));
    const b = Number(attr(markup(h(SbmCard, { doc: fixture, initial: { gamma: 0.9 } })).match(/<[^>]*data-result="sbm"[^>]*>/)![0], 'data-charge'));
    expect(b).toBeGreaterThan(a);
  });
  it('says "not available" with its reason when the document lacks the SBM cases', () => {
    const doc = clone(fixture);
    doc.invariant_cases = doc.invariant_cases.filter((e) => e.calculator !== 'frtb-sbm');
    const m = markup(h(SbmCard, { doc }));
    expect(m).toContain('data-state="unavailable"');
  });
});

describe('the cascade view', () => {
  it('opens on the two-horizon case: ES = sqrt(100 + 36) = 11.66', () => {
    const m = markup(h(CascadeCard, { doc: fixture }));
    const r = m.match(/<[^>]*data-result="cascade"[^>]*>/)![0];
    close(Number(attr(r, 'data-es')), 11.661903789690601);
    expect(attr(r, 'data-paragraph')).toBe('MAR33.4');
    expect(attr(r, 'data-in-force')).toBe('2023-01-01');
    expect(attr(r, 'data-matches-document')).toBe('cascade-two-horizons');
  });
  it('returns ES_T(P) when every factor sits at 10 days', () => {
    const m = markup(h(CascadeCard, { doc: fixture, initial: { preset: 'cascade-all-lh-ten' } }));
    const r = m.match(/<[^>]*data-result="cascade"[^>]*>/)![0];
    close(Number(attr(r, 'data-es')), 10);
    expect(attr(r, 'data-matches-document')).toBe('cascade-all-lh-ten');
  });
  it('lists the five horizons of MAR33.4 Table 1 with their weights, and the 18 rows of MAR33.12 Table 2 with their subsets', () => {
    const m = markup(h(CascadeCard, { doc: fixture }));
    expect([...m.matchAll(/<tr[^>]*data-horizon="(\d+)"[^>]*>/g)].map((x) => x[1])).toEqual(['10', '20', '40', '60', '120']);
    const rows = [...m.matchAll(/<tr[^>]*data-parameter-row="([^"]+)"[^>]*>/g)];
    expect(rows).toHaveLength(18);
    for (const x of rows) {
      expect(attr(x[0], 'data-paragraph')).toBe('MAR33.12');
      expect(attr(x[0], 'data-in-force')).toBe('2023-01-01');
    }
    const vol = rows.find((x) => x[1] === 'credit-spread-volatility')![0];
    expect(attr(vol, 'data-subsets')).toBe('1,2,3,4,5');
    expect(attr(rows.find((x) => x[1] === 'equity-large-cap')![0], 'data-subsets')).toBe('1');
  });
  it('does not transcribe the ambiguous commodity-volatility row', () => {
    expect(markup(h(CascadeCard, { doc: fixture }))).not.toContain('commodity-volatility');
  });
});

describe('the parameter tables and the worked examples', () => {
  it('shows CRE52.72, MAR50.16, MAR33.12 and MAR33.4, every parameter row with its paragraph and in-force date', () => {
    for (const [id, rows] of [['cre52-72-table-2', 15], ['mar50-16-table-1', 8], ['mar33-12-table-2', 18], ['mar33-4-table-1', 5]] as const) {
      const m = markup(h(ParameterCard, { doc: fixture, id }));
      const found = [...m.matchAll(/<tr[^>]*data-parameter-row="([^"]+)"[^>]*>/g)];
      expect(found, id).toHaveLength(rows);
      const t = parameterTable(fixture, id)!;
      for (const x of found) {
        expect(attr(x[0], 'data-paragraph')).toBe(t.paragraph);
        expect(attr(x[0], 'data-in-force')).toBe(t.in_force_date);
      }
      expect(m).toContain(t.paragraph);
      expect(m).toContain(t.in_force_date);
    }
  });
  it('carries every value of the document into its cell', () => {
    const m = markup(h(ParameterCard, { doc: fixture, id: 'cre52-72-table-2' }));
    for (const r of parameterTable(fixture, 'cre52-72-table-2')!.rows) {
      const row = m.match(new RegExp(`<tr[^>]*data-parameter-row="${r.key}"[^>]*>`))![0];
      expect(attr(row, `data-v-${r.parameter}`), `${r.key} ${r.parameter}`).toBe(String(r.value));
    }
  });
  it('says "not available" with its reason when the table is not in the document', () => {
    const doc = clone(fixture);
    doc.parameter_tables = doc.parameter_tables.filter((t) => t.id !== 'mar50-16-table-1');
    const m = markup(h(ParameterCard, { doc, id: 'mar50-16-table-1' }));
    expect(m).toContain('data-state="unavailable"');
  });
  it('lists the five CRE99 netting sets with the published EAD beside the engine value, each with paragraph and dates', () => {
    const m = markup(h(WorkedExamplesCard, { doc: fixture }));
    const rows = [...m.matchAll(/<tr[^>]*data-example="(cre99-netting-set-\d)"[^>]*>/g)];
    expect(rows.map((x) => x[1])).toEqual(['cre99-netting-set-1', 'cre99-netting-set-2', 'cre99-netting-set-3', 'cre99-netting-set-4', 'cre99-netting-set-5']);
    expect(rows.map((x) => attr(x[0], 'data-published-ead'))).toEqual(['569', '381', '5406', '936', '1879']);
    for (const x of rows) {
      expect(attr(x[0], 'data-paragraph')).toBe('CRE52.1');
      expect(attr(x[0], 'data-in-force')).toBe('2023-01-01');
      expect(Math.round(Number(attr(x[0], 'data-engine-ead')))).toBe(Number(attr(x[0], 'data-published-ead')));
    }
  });
});

describe('the Methodology section', () => {
  const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  const dense = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);
  const parts = [['credit', CreditPart], ['floor', FloorPart], ['sbm', SbmPart], ['cascade', CascadePart], ['ccr', CcrPart]] as const;

  it('is one method section of the capital group, registered, with five sub-tabs', () => {
    expect(methodologySection.id).toBe('regulation');
    expect(methodologySection.group).toBe('capital');
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('regulation');
    const m = markup(h(RegulationBody, { doc: fixture }));
    expect(m).toContain('data-area="method"');
    expect(m).toContain('data-method-kind="classical"');
    expect((m.match(/role="tab"/g) ?? []).length).toBe(5);
  });
  it('has exactly one honest callout, and opens with dense paragraphs, a captioned equation and a figure, in both languages', () => {
    for (const lang of LANGS) {
      const m = markup(h(RegulationBody, { doc: fixture }), lang);
      expect(m.match(/data-callout="honest"/g)?.length ?? 0, lang).toBe(1);
      expect(dense(m).length, lang).toBeGreaterThanOrEqual(4);
      expect(m.match(/class="equation"/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(2);
      expect(m.match(/<figure/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
    }
  });
  for (const [id, Part] of parts) {
    it(`the ${id} part has four dense paragraphs, two captioned equations and a figure, and Spanish writes no decimal point`, () => {
      for (const lang of LANGS) {
        const m = markup(h(Part, { doc: fixture }), lang);
        expect(dense(m).length, `${id} ${lang}`).toBeGreaterThanOrEqual(4);
        expect(m.match(/class="equation"/g)?.length ?? 0, `${id} ${lang}`).toBeGreaterThanOrEqual(id === 'ccr' ? 3 : 2);
        expect(m.match(/<figure/g)?.length ?? 0, `${id} ${lang}`).toBeGreaterThanOrEqual(1);
        expect(m).not.toContain('data-callout="honest"');
        if (lang === 'es') expect(decimalPoints(visibleText(m)), `${id} writes a decimal point`).toEqual([]);
      }
    });
  }
  it('names the fixture when the document stands on one, and never claims approval or compliance', () => {
    for (const lang of LANGS) {
      const m = markup(h(RegulationBody, { doc: fixture }), lang);
      expect(m).toContain('data-fixture="true"');
      const text = visibleText(m).replace(/\s+/g, ' ');
      // the callout disclaims approval, compliance and equivalence; nothing says a result is approved, certified or compliant
      expect(text).toContain(lang === 'en' ? 'They do not claim regulatory approval, compliance or equivalence' : 'No afirman aprobación regulatoria, cumplimiento ni equivalencia');
      expect(text.toLowerCase()).not.toMatch(/is (approved|certified|compliant)|(approved|certified) by|es (aprobad|certificad)|(aprobado|certificado) por|conforme a la norma/);
      expect(m).not.toContain('data-callout="strong"');
    }
    const baked = clone(fixture);
    baked.provenance.inputs = [{ source: 'treasury', class: 'mirror-allowed', files: [] }] as typeof baked.provenance.inputs;
    expect(markup(h(RegulationBody, { doc: baked }))).not.toContain('data-fixture="true"');
  });
  it('says loading while the document is on its way and "not available" with its reason when it is absent', () => {
    const loading = markup(h(RegulationBody, { doc: undefined }));
    expect(loading).toContain('data-state="loading"');
    const absent = markup(h(RegulationBody, { doc: null, reason: { en: 'the regulatory bake has not written calculators.json', es: 'el proceso no escribió calculators.json' } }));
    expect(absent).toContain('data-state="unavailable"');
    expect(absent).toContain(escapeHtml('the regulatory bake has not written calculators.json'));
    // the theory is text and is there with or without the document
    expect(dense(absent).length).toBeGreaterThanOrEqual(4);
  });
  it('plants: a changed document value changes the markup', () => {
    const doc = clone(fixture);
    doc.cre20_grid.find((r) => r.exposure_class === 'sovereign' && r.key === 'A+ to A-')!.risk_weight = 0.35;
    const a = markup(h(Cre20Card, { doc: fixture, initial: { cls: 'sovereign', key: 'A+ to A-' } }));
    const b = markup(h(Cre20Card, { doc, initial: { cls: 'sovereign', key: 'A+ to A-' } }));
    expect(a).not.toEqual(b);
    expect(attr(b.match(/<[^>]*data-result="cre20"[^>]*>/)![0], 'data-weight')).toBe('0.35');
  });
});
