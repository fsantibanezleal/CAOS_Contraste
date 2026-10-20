// U9-W1: the C12 instrument rendered on the server from the c12-outputs and c12-models fixtures (docs/contracts/fixtures/c12),
// and the live SA-CCR and BA-CVA ports held to the documents' blocks at 1e-9 relative. The views are built on the reviewed
// contracts while the engine and the bake are built, so every assertion reads what the fixtures hold: the profiles with
// their Monte Carlo band and the ORE overlay, collateral against the margin period and initial margin as a regression proxy
// and never SIMM, the netting benefit, the CVA build-up and the wrong-way sweep without an ORE reconciliation, the
// regulatory against modelled table, the PIT back-test with its simulated critical values, every named parameter as a
// convention, "not available" with a reason for every null, and no number that the document does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { BA_CVA_RISK_WEIGHTS, SECTORS, baCva, baCvaInputFrom, baCvaMismatches, discountFactor, kReduced, riskWeight, scva } from './bacva';
import { C12_FIT, C12_OUTPUTS } from './descriptor';
import { useC12Instrument } from './instrument';
import { hedgingSetEffectiveNotional, irBucket, maturityFactor, multiplier, replacementCost, saCcr, saCcrInputFrom, saCcrMismatches, supervisoryDuration } from './saccr';
import {
  VARIANT_ORDER, defaultSel, fitOf, histogram, liveBaCva, liveSaCcr, nearestIndex, outputsOf, runningSum, wwrOf,
  type C12Outputs, type C12Sel, type Peers,
} from './selection';
import { BaCvaReadout, C12ContextView, C12FindingsView, C12TestsView, C12VariantsTable, C12VariantsView, CaseReadout, HorizonReadout, SaCcrReadout, TimeReadout, cell, digits } from './C12Common';
import { CollateralView, NettingView, ProfileView, SensitivityView } from './ExposureViews';
import { CvaView, WwrView } from './CreditViews';
import { BaCvaView, ComparisonView, GirrView, SaCcrView } from './RegulatoryViews';
import { ExceedanceView, PitView } from './BacktestViews';

type Doc = VariantArtifact<C12Outputs>;

const fixture = <T,>(name: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c12/${name}-fixture.json`, import.meta.url), 'utf8')) as T;
const single = fixture<Doc>('variant-swap-exposure-single-swap');
const netting = fixture<Doc>('variant-swap-exposure-netting-set');
const csa10 = fixture<Doc>('variant-swap-exposure-csa-mpor-10d');
const csa20 = fixture<Doc>('variant-swap-exposure-csa-mpor-20d');
const withIm = fixture<Doc>('variant-swap-exposure-with-im');
const wwr = fixture<Doc>('variant-swap-exposure-wrong-way-risk');
const models = fixture<ModelsArtifact>('models');
const ALL: Doc[] = [single, netting, csa10, csa20, withIm, wwr];
const title = { en: 'Swap exposure, CVA and SA-CCR', es: 'Exposición de swaps, CVA y SA-CCR' };
const dataOf = (v: Doc): CaseData => fixtureData('C12', v as unknown as VariantArtifact, models, title);
const peers: Peers = Object.fromEntries(ALL.map((d) => [d.outputs.variant, { variantId: d.variant_id, title: { en: d.outputs.variant, es: d.outputs.variant }, o: d.outputs }]));
const selOf = (v: Doc, patch: Partial<C12Sel> = {}, withPeers = true): C12Sel => ({ ...(defaultSel(dataOf(v), withPeers ? peers : null) as C12Sel), ...patch });
const clone = <T,>(v: T): T => structuredClone(v);

const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');
const text = (t: { en: string; es: string }, lang: 'en' | 'es' = 'en') => escapeHtml(t[lang]);
const rel = (a: number, b: number) => Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1e-300);

const VIEWS: Array<[string, (p: { sel: C12Sel | null }) => ReactElement]> = [
  ['Profile', ProfileView], ['Collateral', CollateralView], ['Netting', NettingView], ['Sensitivity', SensitivityView],
  ['CVA', CvaView], ['Wrong-way', WwrView], ['Comparison', ComparisonView], ['SA-CCR', SaCcrView], ['BA-CVA', BaCvaView], ['GIRR', GirrView],
  ['PIT', PitView], ['Exceedances', ExceedanceView], ['Tests', C12TestsView], ['Findings', C12FindingsView], ['Context', C12ContextView],
];

function Names({ v }: { v: Doc }) {
  const inst = useC12Instrument(dataOf(v), () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Rail({ v }: { v: Doc }) {
  const inst = useC12Instrument(dataOf(v), () => undefined);
  return <div>{inst ? inst.rail.map((s) => (typeof s.label === 'string' ? s.label : s.label.en)).join('|') : 'none'}</div>;
}
function Controls({ v }: { v: Doc }) {
  const inst = useC12Instrument(dataOf(v), () => undefined);
  return <pre>{JSON.stringify(inst?.controls)}</pre>;
}
function Other() {
  const inst = useC12Instrument({ ...dataOf(netting), manifest: { ...dataOf(netting).manifest, case_id: 'C15' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C12 contract descriptors', () => {
  it('describe the six variant fixtures and the models fit key by key, in both directions', () => {
    for (const v of ALL) expect(conform(v.outputs, C12_OUTPUTS), v.variant_id).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C12_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone(netting);
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).girr;
    const found = conform(odd.outputs, C12_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/girr: declared by the web, not written by the pipeline/);
  });
});

describe('the live SA-CCR port (CRE52, interest rate class)', () => {
  it('reproduces the sa_ccr block of every C12 fixture at 1e-9 relative, every intermediate value', () => {
    for (const d of ALL) {
      const block = d.outputs.sa_ccr;
      const live = saCcr(saCcrInputFrom(block));
      expect(saCcrMismatches(live, block), d.variant_id).toEqual([]);
      expect(rel(live.ead, block.ead.amount), `${d.variant_id} EAD`).toBeLessThan(1e-9);
      expect(rel(live.multiplier, block.multiplier), `${d.variant_id} multiplier`).toBeLessThan(1e-9);
      expect(rel(live.rc, block.rc.amount) || 0, `${d.variant_id} RC`).toBeLessThan(1e-9);
      for (const t of block.trades) {
        const l = live.trades.find((x) => x.tradeId === t.trade_id)!;
        expect(rel(l.supervisoryDuration, t.supervisory_duration), t.trade_id).toBeLessThan(1e-9);
        expect(l.bucket).toBe(t.bucket);
      }
    }
  });

  it('is held to the committed block: a changed formula or a changed committed value is a mismatch', () => {
    const block = clone(netting.outputs.sa_ccr);
    const live = saCcr(saCcrInputFrom(block));
    block.ead.amount *= 1 + 1e-6;
    expect(saCcrMismatches(live, block).join('\n')).toMatch(/ead: live/);
    const block2 = clone(netting.outputs.sa_ccr);
    block2.trades[0].supervisory_duration += 0.001;
    expect(saCcrMismatches(saCcr(saCcrInputFrom(netting.outputs.sa_ccr)), block2).join('\n')).toMatch(/SW-1.supervisory_duration/);
    // a port with a wrong constant would depart from the committed block: here the offset flag of the hedging set is flipped
    const flipped = saCcr({ ...saCcrInputFrom(netting.outputs.sa_ccr), offset: { USD: false } });
    expect(saCcrMismatches(flipped, netting.outputs.sa_ccr).length).toBeGreaterThan(0);
  });

  it('holds the formulas of CRE52 (dossier 01 E.2)', () => {
    // supervisory duration, CRE52.34, and the margined and unmargined maturity factors, CRE52.48 and CRE52.52
    expect(supervisoryDuration(0, 10)).toBeCloseTo((1 - Math.exp(-0.5)) / 0.05, 12);
    expect(supervisoryDuration(2, 2)).toBe(0);
    expect(maturityFactor(0.25, null)).toBeCloseTo(0.5, 12);
    expect(maturityFactor(7, null)).toBe(1);
    expect(maturityFactor(7, 14)).toBeCloseTo(1.5 * Math.sqrt(14 / 250), 12); // CRE99 netting set 5
    expect(maturityFactor(7, 10)).toBeCloseTo(1.5 * Math.sqrt(10 / 250), 12);
    // the buckets of CRE52.57
    expect(irBucket(0.99)).toBe('B1');
    expect(irBucket(1)).toBe('B2');
    expect(irBucket(5)).toBe('B2');
    expect(irBucket(5.01)).toBe('B3');
    // the offset formula and the sum of absolute values
    expect(hedgingSetEffectiveNotional(1, 1, 1)).toBeCloseTo(Math.sqrt(6.4), 12);
    expect(hedgingSetEffectiveNotional(1, -2, 3, false)).toBe(6);
    expect(hedgingSetEffectiveNotional(0, 0, 5)).toBe(5);
    // the replacement cost, unmargined and margined, CRE52.10 and CRE52.18 (CRE99 netting set 5: max(80 - 200; 0 + 5 - 150; 0) = 0)
    expect(replacementCost(60, 20, false)).toBe(40);
    expect(replacementCost(80, 200, true, 0, 5, 150)).toBe(0);
    expect(replacementCost(80, 0, true, 100, 10, 0)).toBe(110);
    // the multiplier, CRE52.23: one at V - C >= 0, never below the floor of 5 percent, and CRE99 netting set 2 (-20 over 282.128832)
    expect(multiplier(0, 100)).toBe(1);
    expect(multiplier(50, 100)).toBe(1);
    expect(multiplier(-1e12, 100)).toBeCloseTo(0.05, 12);
    expect(multiplier(-20, 282.128832)).toBeCloseTo(0.965208, 6);
    expect(multiplier(-5, 0)).toBe(1);
    // EAD = alpha (RC + PFE)
    const one = saCcr({ trades: [{ tradeId: 'A', hedgingSet: 'USD', startYears: 0, endYears: 10, notional: 1e6, delta: 1 }], v: 100, c: 0, th: 0, mta: 0, nica: 0, mporBusinessDays: null });
    expect(one.ead).toBeCloseTo(1.4 * (one.rc + one.pfe), 9);
    expect(one.rc).toBe(100);
  });

  it('moves with the collateral: the replacement cost falls to zero and the multiplier falls below one', () => {
    const o = netting.outputs;
    const base = liveSaCcr(o, null)!;
    const over = liveSaCcr(o, 400_000)!;
    expect(base.rc).toBe(o.sa_ccr.rc.amount);
    expect(over.rc).toBe(0);
    expect(over.multiplier).toBeLessThan(base.multiplier);
    expect(over.ead).toBeLessThan(base.ead);
    // the same collateral as the document is the document's block
    expect(liveSaCcr(o, o.sa_ccr.c.amount)!.ead).toBe(base.ead);
  });
});

describe('the live BA-CVA port (MAR50, reduced version)', () => {
  it('reproduces the ba_cva block of every C12 fixture at 1e-9 relative', () => {
    for (const d of ALL) {
      const block = d.outputs.ba_cva;
      const live = baCva(baCvaInputFrom(block), block.imm_bank);
      expect(baCvaMismatches(live, block), d.variant_id).toEqual([]);
      expect(rel(live.capital, block.capital.amount), d.variant_id).toBeLessThan(1e-9);
      expect(rel(live.kReduced, block.k_reduced), d.variant_id).toBeLessThan(1e-9);
    }
  });

  it('holds the risk weights of MAR50.16 Table 1 for all sixteen cells, and the document\'s own is the table\'s', () => {
    expect(Object.keys(BA_CVA_RISK_WEIGHTS)).toHaveLength(8);
    expect(riskWeight('financials', 'investment-grade')).toBe(0.05);
    expect(riskWeight('financials', 'high-yield-or-not-rated')).toBe(0.12);
    expect(riskWeight('sovereigns-central-banks-mdbs', 'investment-grade')).toBe(0.005);
    expect(riskWeight('sovereigns-central-banks-mdbs', 'high-yield-or-not-rated')).toBe(0.02);
    expect(riskWeight('consumer-transport-administrative', 'high-yield-or-not-rated')).toBe(0.085);
    expect(riskWeight('technology-telecoms', 'high-yield-or-not-rated')).toBe(0.055);
    expect(riskWeight('health-care-utilities-professional', 'investment-grade')).toBe(0.015);
    for (const d of ALL) for (const c of d.outputs.ba_cva.counterparties) expect(c.risk_weight).toBe(riskWeight(c.sector as never, c.rating_class as never));
  });

  it('holds the invariants of the formulas (dossier 01 M.1; no official numeric example is verified)', () => {
    // rho = 1 gives the sum of the SCVA, rho = 0 the root of the sum of squares; one counterparty gives its own SCVA
    expect(kReduced([3, 4], 1)).toBeCloseTo(7, 12);
    expect(kReduced([3, 4], 0)).toBeCloseTo(5, 12);
    expect(kReduced([5])).toBeCloseTo(5, 12);
    // K lies between the two extremes for rho = 50 percent
    const k = kReduced([3, 4]);
    expect(k).toBeGreaterThan(5);
    expect(k).toBeLessThan(7);
    // the discount factor tends to one as the maturity tends to zero and is one for an internal-model bank
    expect(discountFactor(1e-9)).toBeCloseTo(1, 8);
    expect(discountFactor(10)).toBeCloseTo((1 - Math.exp(-0.5)) / 0.5, 12);
    expect(discountFactor(10, true)).toBe(1);
    // SCVA = RW M EAD DF / 1.4
    expect(scva(0.05, [{ ead: 1400, mYears: 2 }])).toBeCloseTo((0.05 * 2 * 1400 * discountFactor(2)) / 1.4, 12);
    // capital is 0.65 K
    const r = baCva([{ rw: 0.05, sets: [{ ead: 1400, mYears: 2 }] }]);
    expect(r.capital).toBeCloseTo(0.65 * r.kReduced, 12);
    // a counterparty with no exposure has no charge
    expect(baCva([{ rw: 0.05, sets: [{ ead: 0, mYears: 2 }] }]).capital).toBe(0);
  });

  it('chains from the live SA-CCR: a larger collateral lowers the EAD and the capital, and a riskier sector raises it', () => {
    const o = netting.outputs;
    const sa = liveSaCcr(o, null)!;
    const ba = liveBaCva(o, sa.ead, 'financials', 'investment-grade')!;
    expect(rel(ba.capital, baCva(baCvaInputFrom(o.ba_cva), false).capital)).toBeLessThan(1e-9); // the document's EAD is rounded to six decimals
    const less = liveBaCva(o, liveSaCcr(o, 400_000)!.ead, 'financials', 'investment-grade')!;
    expect(less.capital).toBeLessThan(ba.capital);
    expect(liveBaCva(o, sa.ead, 'financials', 'high-yield-or-not-rated')!.capital).toBeGreaterThan(ba.capital);
    expect(liveBaCva(o, sa.ead, 'sovereigns-central-banks-mdbs', 'investment-grade')!.capital).toBeLessThan(ba.capital);
    expect(SECTORS.length).toBe(8);
  });
});

describe('the selection helpers', () => {
  it('nearestIndex, runningSum and histogram read the document and nothing else', () => {
    expect(nearestIndex([0.25, 0.5, 1, 2], 0.9)).toBe(2);
    expect(nearestIndex([0.25, 0.5, 1, 2], 100)).toBe(3);
    expect(runningSum([1, 2, 3])).toEqual([1, 3, 6]);
    for (const d of ALL) {
      const terms = d.outputs.cva_dva.buckets.map((b) => b.cva_term);
      // the terms and the total are each rounded in the document: the sum agrees with the CVA at the checker's 1e-6 relative
      expect(rel(runningSum(terms).at(-1)!, d.outputs.cva_dva.cva.amount), d.variant_id).toBeLessThan(1e-6);
    }
    expect(histogram([0.05, 0.15, 0.95, 1], 10)).toEqual([1, 1, 0, 0, 0, 0, 0, 0, 0, 2]);
    expect(histogram([0.5], 10).reduce((a, b) => a + b, 0)).toBe(1);
    const h = netting.outputs.backtest.book_horizons[0];
    expect(histogram(h.pits).reduce((a, b) => a + b, 0)).toBe(h.n);
  });

  it('defaultSel is for C12 only and opens on the 12-month back-test of the book, the base case and the document\'s own counterparty', () => {
    expect(defaultSel(null)).toBeNull();
    const other = { ...dataOf(netting), manifest: { ...dataOf(netting).manifest, case_id: 'C15' } };
    expect(defaultSel(other)).toBeNull();
    const sel = selOf(netting);
    expect(sel.horizon).toBe('12m');
    expect(sel.subject).toBe('book');
    expect(sel.caseId).toBe('base');
    expect(sel.collateral).toBeNull();
    expect(sel.sector).toBe(netting.outputs.ba_cva.counterparties[0].sector);
    expect(selOf(wwr).b).toBe(wwr.outputs.wrong_way_risk!.b_grid.indexOf(0));
    expect(wwrOf(selOf(netting))!.owner.variant).toBe('wrong-way-risk');
    expect(wwrOf(selOf(netting, {}, false))).toBeNull();
    expect(outputsOf(selOf(netting))?.kind).toBe('swap-exposure');
    expect(fitOf(selOf(netting))?.min_history_years).toBe(3);
  });
});

describe('the C12 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C12 only, with four groups in the validator order, then Variants', () => {
    expect(html(<Names v={netting} />)).toContain('Exposure|CVA and wrong-way risk|Regulatory capital|Back-test and tests|Variants');
    expect(html(<Other />)).toContain('null');
  });

  it('the rail holds a control and a live read-out per section, and the wrong-way variant swaps the calibration case for its parameter b', () => {
    expect(html(<Rail v={netting} />)).toContain('Time|Back-test|Calibration|Collateral|Counterparty');
    expect(html(<Rail v={wwr} />)).toContain('Time|Back-test|Wrong-way|Collateral|Counterparty');
    expect(html(<Controls v={netting} />)).toContain('&quot;case&quot;:&quot;base&quot;');
    expect(html(<Controls v={wwr} />)).toContain('&quot;b&quot;:1');
    for (const k of ['t', 'horizon', 'subject', 'collateral', 'sector', 'rating']) expect(html(<Controls v={netting} />)).toContain(`&quot;${k}&quot;`);
  });

  it('every rail read-out is drawn with a unit and prints no raw amount', () => {
    for (const [name, el] of [
      ['time', <TimeReadout sel={selOf(netting)} />], ['horizon', <HorizonReadout sel={selOf(netting)} />], ['wrong-way', <CaseReadout sel={selOf(wwr)} />],
      ['calibration', <CaseReadout sel={selOf(netting)} />], ['collateral', <SaCcrReadout sel={selOf(netting)} />], ['counterparty', <BaCvaReadout sel={selOf(netting)} />],
    ] as Array<[string, ReactElement]>) {
      const markup = html(el);
      expect(markup, name).toContain('caos-readout');
      expect(RAW_AMOUNT.test(markup), `${name}: a raw amount in a rail read-out`).toBe(false);
    }
  });

  it('the read-outs move with their controls', () => {
    const a = html(<TimeReadout sel={selOf(netting, { t: 0 })} />);
    const b = html(<TimeReadout sel={selOf(netting, { t: 5 })} />);
    expect(a).not.toBe(b);
    expect(html(<HorizonReadout sel={selOf(netting, { horizon: '10bd' })} />)).not.toBe(html(<HorizonReadout sel={selOf(netting, { horizon: '12m' })} />));
    expect(html(<SaCcrReadout sel={selOf(netting, { collateral: 0 })} />)).not.toBe(html(<SaCcrReadout sel={selOf(netting, { collateral: 300_000 })} />));
    expect(html(<BaCvaReadout sel={selOf(netting, { sector: 'financials' })} />)).not.toBe(html(<BaCvaReadout sel={selOf(netting, { sector: 'sovereigns-central-banks-mdbs' })} />));
    expect(html(<CaseReadout sel={selOf(wwr, { b: 0 })} />)).not.toBe(html(<CaseReadout sel={selOf(wwr, { b: 4 })} />));
    expect(html(<CaseReadout sel={selOf(netting, { caseId: 'base' })} />)).not.toBe(html(<CaseReadout sel={selOf(netting, { caseId: 'sigma-plus-1se' })} />));
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={selOf(netting)} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
    for (const d of ALL) for (const [name, View] of VIEWS) expect(cards(html(<View sel={selOf(d)} />)).length, `${name} on ${d.variant_id}`).toBeGreaterThan(0);
  });

  it('a view given a document that is not a swap-exposure document says not available and draws nothing', () => {
    const odd = clone(netting);
    (odd.outputs as unknown as { kind: string }).kind = 'scenario';
    const oddSel: C12Sel = { ...selOf(netting), data: dataOf(odd) };
    expect(outputsOf(oddSel)).toBeNull();
    for (const [name, View] of VIEWS.filter(([n]) => !['Tests', 'Findings', 'Context'].includes(n))) {
      const markup = html(<View sel={oddSel} />);
      expect(markup, name).toContain('data-state="unavailable"');
      expect(markup, name).not.toContain('data-series=');
    }
  });

  it('the EE, ENE and PFE profile gives every grid point, the Monte Carlo standard error and the ORE overlay', () => {
    const markup = html(<ProfileView sel={selOf(netting)} />);
    const e = netting.outputs.exposure;
    expect(markup).toContain('data-series="7"'); // minus 2 SE, plus 2 SE, EE, ENE, PFE, effective EE, ORE
    e.time_grid_years.forEach((_, i) => {
      expect(markup).toContain(cell(e.ee.values[i], 'en'));
      expect(markup).toContain(cell(e.pfe.values[i], 'en'));
    });
    expect(markup).toContain(cell(e.eepe.amount, 'en'));
    expect(markup).toContain(cell(e.epe.amount, 'en'));
    expect(markup).toContain('data-ore="reconciled"');
    expect(markup).toContain('1.8.17.0');
    expect(markup).toContain(cell(netting.outputs.ore_reconciliation.ore_ee!.values[2], 'en'));
    expect(markup).toContain('2 SE');
  });

  it('the wrong-way variant draws no ORE overlay and says it has no ORE reconciliation', () => {
    const markup = html(<ProfileView sel={selOf(wwr)} />);
    expect(markup).toContain('data-series="6"');
    expect(markup).toContain('data-ore="not-applicable"');
    expect(markup).toContain(text(wwr.outputs.ore_reconciliation.reason!));
    expect(markup).not.toContain('reconciled on');
    const v = html(<WwrView sel={selOf(wwr)} />);
    expect(v).toContain('data-block="ore-limit"');
    expect(v).toContain('data-ore-status="not-applicable"');
    expect(v).toContain(text(wwr.outputs.wrong_way_risk!.ore_limit));
  });

  it('the collateral view puts the uncollateralised EE against variation margin at 10 and 20 days and initial margin on one axis, the initial margin a regression proxy and never SIMM', () => {
    const markup = html(<CollateralView sel={selOf(withIm)} />);
    expect(markup).toContain('data-series="5"'); // uncollateralised, MPoR 10, MPoR 20, with IM, the dynamic IM
    expect(markup).toContain('Variation margin, MPoR 10 days');
    expect(markup).toContain('Variation margin, MPoR 20 days');
    expect(markup).toContain('regression proxy');
    expect(markup).toContain('data-im="regression-proxy"');
    expect(markup).toContain('data-simm-used="false"');
    expect(markup).toContain('not SIMM');
    expect(markup).not.toMatch(/ISDA SIMM (risk weights|methodology) (are|is) used/);
    const im = withIm.outputs.initial_margin!;
    expect(markup).toContain(`${im.horizon_calendar_days}`);
    expect(markup).toContain(text(im.limit));
    for (const d of [netting, csa10, csa20, withIm]) expect(markup).toContain(cell(d.outputs.exposure.eepe.amount, 'en'));
    // a variant without a CSA says so in words
    expect(html(<CollateralView sel={selOf(single)} />)).toContain('this variant has no CSA');
    expect(html(<CollateralView sel={selOf(single)} />)).toContain('data-im="none"');
    // the CSA terms of a collateralised variant
    const csa = html(<CollateralView sel={selOf(csa20)} />);
    expect(csa).toContain(`margin period ${csa20.outputs.collateral!.csa.mpor_business_days} business days`);
    expect(csa).toContain(text(csa20.outputs.collateral!.limit));
    // the other variants are loading: no chart, a declared state
    expect(html(<CollateralView sel={selOf(netting, {}, false)} />)).toContain('data-state="loading"');
  });

  it('the netting view gives the single-trade EE, their sum, the netted EE and the benefit, and a one-swap book has nothing to net', () => {
    const markup = html(<NettingView sel={selOf(netting, { t: 3 })} />);
    const nb = netting.outputs.netting_benefit;
    for (const t of nb.per_trade_ee) {
      expect(markup).toContain(`data-trade="${t.trade_id}"`);
      expect(markup).toContain(cell(t.ee.values[3], 'en'));
    }
    expect(markup).toContain(cell(nb.sum_of_single_trade_ee.values[3], 'en'));
    expect(markup).toContain(cell(nb.netted_ee.values[3], 'en'));
    expect(markup).toContain(cell(nb.benefit.values[3], 'en'));
    expect(markup).toContain('data-series="7"'); // four trades, the sum, the netted EE, the benefit
    const one = html(<NettingView sel={selOf(single)} />);
    expect(one).toContain('data-series="3"');
    expect(one).toContain('data-trade="SW-1"');
  });

  it('the calibration sensitivity draws the five cases for EE and for PFE with the document\'s EEPE and PFE peak', () => {
    const markup = html(<SensitivityView sel={selOf(netting, { caseId: 'a-plus-1se' })} />);
    expect((markup.match(/data-series="5"/g) ?? []).length).toBe(2);
    for (const c of netting.outputs.calibration_sensitivity) {
      expect(markup).toContain(`data-case="${c.case}"`);
      expect(markup).toContain(cell(c.eepe.amount, 'en'));
      expect(markup).toContain(cell(c.pfe_peak.amount, 'en'));
    }
    expect(markup).toContain('Reversion a, plus 1 SE');
  });

  it('the CVA is built up from the buckets: the running sum ends at the document\'s CVA and the counterparty curve is a proxy', () => {
    const markup = html(<CvaView sel={selOf(netting)} />);
    const c = netting.outputs.cva_dva;
    expect(markup).toContain(cell(c.cva.amount, 'en'));
    expect(markup).toContain(cell(c.dva.amount, 'en'));
    expect(markup).toContain(cell(c.bcva.amount, 'en'));
    expect(markup).toContain('data-label="proxy"');
    expect(markup).toContain('proxy');
    for (const b of c.buckets) expect(markup).toContain(`data-bucket="${b.t_end}"`);
    expect(markup).toContain(formatNumber(c.buckets[0].survival, 'en', { percent: true, decimals: 3 }));
    expect(markup).toContain('a synthetic flat spread, a convention of the case');
    const hqm = clone(netting);
    hqm.outputs.cva_dva.credit_curve_source = 'hqm-minus-treasury';
    expect(html(<CvaView sel={selOf(hqm)} />)).toContain('Treasury HQM corporate spot curve minus the Treasury zero curve');
  });

  it('the wrong-way sweep gives the CVA at every b, b = 0 as the independent CVA and the largest b w stated', () => {
    const markup = html(<WwrView sel={selOf(wwr)} />);
    const w = wwr.outputs.wrong_way_risk!;
    for (const p of w.sweep) {
      expect(markup).toContain(`data-b="${p.b}"`);
      expect(markup).toContain(cell(p.cva.amount, 'en'));
    }
    expect(markup).toContain('data-independent="true"');
    expect(markup).toContain(formatNumber(w.largest_b_w, 'en', { digits: 4 }));
    expect(markup).toContain(formatNumber(w.w_max_usd_million, 'en', { digits: 4 }));
    expect(markup).toContain(cell(w.independent_cva.amount, 'en'));
    expect(markup).toContain('wrong-way');
    expect(markup).toContain('right-way');
    // from any other variant the sweep is the wrong-way variant's, said so
    const other = html(<WwrView sel={selOf(netting)} />);
    expect(other).toContain('Drawn from the wrong-way variant');
    expect(other).toContain(cell(w.sweep[0].cva.amount, 'en'));
    // with that variant absent: not available, with the reason
    const none = html(<WwrView sel={selOf(netting, {}, false)} />);
    expect(none).toContain('data-state="unavailable"');
    expect(none).toContain('the wrong-way variant is loading');
    const gone = html(<WwrView sel={selOf(netting, { peers: Object.fromEntries(Object.entries(peers).filter(([k]) => k !== 'wrong-way-risk')) })} />);
    expect(gone).toContain('holds none of the wrong-way variant');
  });

  it('the regulatory table sets the SA-CCR EAD against alpha times EEPE, the BA-CVA against the CVA and the GIRR charge with and without the division by sqrt(2)', () => {
    const markup = html(<ComparisonView sel={selOf(netting)} />);
    const r = netting.outputs.regulatory_comparison;
    expect(markup).toContain(cell(r.sa_ccr_ead.amount, 'en'));
    expect(markup).toContain(cell(r.alpha_times_eepe.amount, 'en'));
    expect(markup).toContain(formatNumber(r.sa_ccr_over_alpha_eepe, 'en', { digits: 4 }));
    expect(markup).toContain(cell(netting.outputs.ba_cva.capital.amount, 'en'));
    expect(markup).toContain(cell(netting.outputs.cva_dva.cva.amount, 'en'));
    expect(markup).toContain(cell(netting.outputs.girr.delta_charge.amount, 'en'));
    expect(markup).toContain(cell(netting.outputs.girr.delta_charge_undivided.amount, 'en'));
    expect(markup).toContain('sqrt(2)');
    expect(markup).toContain('convention');
    expect(markup).toContain(cell(r.stressed.effective_epe.amount, 'en'));
    expect(markup).toContain('data-spread-rose="true"');
    expect(markup).toContain('CRE53.7 and CRE53.51');
    const flat = clone(netting);
    flat.outputs.regulatory_comparison.stressed.spread_rose = false;
    expect(html(<ComparisonView sel={selOf(flat)} />)).toContain('the window is not a stress window');
  });

  it('the live SA-CCR view shows the port on the document\'s inputs as the committed block, and says so when a control moves the inputs', () => {
    const base = html(<SaCcrView sel={selOf(netting)} />);
    const sa = netting.outputs.sa_ccr;
    expect(base).toContain('data-parity="match"');
    expect(base).toContain(`data-live-ead="${saCcr(saCcrInputFrom(sa)).ead}"`);
    expect(base).toContain(`data-committed-ead="${sa.ead.amount}"`);
    expect(base).toContain('1e-9 relative');
    for (const t of sa.trades) expect(base).toContain(`data-trade="${t.trade_id}"`);
    expect(base).toContain('data-hedging-set="USD"');
    expect(base).toContain(cell(sa.ead.amount, 'en'));
    expect(base).toContain('data-series="3"');
    const moved = html(<SaCcrView sel={selOf(netting, { collateral: 300_000 })} />);
    expect(moved).toContain('data-parity="moved"');
    expect(moved).not.toBe(base);
    // a port that departs from a corrupted committed block is reported in the view
    const bad = clone(netting);
    bad.outputs.sa_ccr.ead.amount *= 2;
    expect(html(<SaCcrView sel={selOf(bad)} />)).toContain('data-parity="mismatch"');
    // the margined variants use the margined maturity factor
    expect(html(<SaCcrView sel={selOf(csa10)} />)).toContain('data-parity="match"');
  });

  it('the live BA-CVA view gives the capital by sector at the rating class in focus, the chain from the live EAD, and the limit', () => {
    const base = html(<BaCvaView sel={selOf(netting)} />);
    const ba = netting.outputs.ba_cva;
    expect(base).toContain('data-parity="match"');
    expect(base).toContain(cell(ba.capital.amount, 'en'));
    expect(base).toContain(cell(ba.k_reduced, 'en'));
    expect(base).toContain(pct(ba.counterparties[0].risk_weight));
    expect(base).toContain(text(ba.limit));
    expect(base).toContain('Financials');
    const moved = html(<BaCvaView sel={selOf(netting, { sector: 'technology-telecoms', rating: 'high-yield-or-not-rated' })} />);
    expect(moved).toContain('data-parity="moved"');
    expect(moved).toContain(pct(0.055));
    const collateral = html(<BaCvaView sel={selOf(netting, { collateral: 300_000 })} />);
    expect(collateral).toContain('data-parity="moved"');
    expect(collateral).not.toContain(`data-live-capital="${ba.capital.amount}"`);
  });

  it('the GIRR view gives the sensitivities by tenor, the three scenarios and the charge with and without the division, the division a convention', () => {
    const markup = html(<GirrView sel={selOf(netting)} />);
    const g = netting.outputs.girr;
    for (const s of g.scenarios) {
      expect(markup).toContain(`data-scenario="${s.scenario}"`);
      expect(markup).toContain(cell(s.k_b, 'en'));
    }
    expect(markup).toContain(cell(g.delta_charge.amount, 'en'));
    expect(markup).toContain(cell(g.delta_charge_undivided.amount, 'en'));
    expect(markup).toContain('data-status="convention"');
    g.sensitivities.forEach((s) => expect(markup).toContain(cell(s, 'en')));
    for (const t of (models.fit as unknown as { girr_parameters: { tenors_years: number[] } }).girr_parameters.tenors_years) expect(markup).toContain(`data-tenor="${t}"`);
    expect(markup).toMatch(/1\.7[\s\u00a0]%/);
    expect(markup).toContain('MAR21.44');
  });

  it('the PIT histogram bins the document\'s PITs and gives the statistic, both critical values and the effective sample size', () => {
    const sel = selOf(netting, { horizon: '3m', subject: 'book' });
    const markup = html(<PitView sel={sel} />);
    const h = netting.outputs.backtest.book_horizons.find((x) => x.horizon === '3m')!;
    expect(markup).toContain(`data-w2="${h.w2}"`);
    expect(markup).toContain(digits(h.w2, 'en'));
    expect(markup).toContain(digits(h.critical_simulated.p05, 'en'));
    expect(markup).toContain(digits(h.critical_iid.p05, 'en'));
    expect(markup).toContain(formatNumber(h.effective_sample_size, 'en', { digits: 4 }));
    expect(markup).toContain(`data-reject="${h.reject_at_5pct}"`);
    expect(markup).toContain('(i + 1) / (N + 2)');
    expect((markup.match(/data-bin="/g) ?? []).length).toBe(10);
    const rf = html(<PitView sel={selOf(netting, { subject: 'risk-factor', horizon: '10bd' })} />);
    expect(rf).toContain('the risk factor');
    expect(rf).not.toBe(markup);
  });

  it('the exceedance view gives the Anderson-Darling result per horizon, the counts at every quantile and the three sub-windows', () => {
    const markup = html(<ExceedanceView sel={selOf(netting)} />);
    for (const h of netting.outputs.backtest.book_horizons) {
      expect(markup).toContain(`data-horizon="${h.horizon}"`);
      expect(markup).toContain(digits(h.w2, 'en'));
      for (const e of h.exceedances) expect(markup).toContain(`${e.count} / ${formatNumber(e.expected, 'en', { digits: 4 })}`);
    }
    for (const w of netting.outputs.backtest.sub_windows) expect(markup).toContain(`data-window="${w.window}"`);
    expect(markup).toContain('BCBS 185');
    const rf = html(<ExceedanceView sel={selOf(netting, { subject: 'risk-factor' })} />);
    expect(rf).toContain('data-block="risk-factor"');
    expect(rf).not.toContain('data-table="c12-subwindows"');
  });

  it('the tests table shows a test that did not run with its reason and no number', () => {
    const markup = html(<C12TestsView sel={selOf(netting)} />);
    expect(markup).toContain('data-light="not_evaluated"');
    const nr = netting.tests.find((t) => t.light === 'not_evaluated')!;
    expect(markup).toContain(escapeHtml(nr.notes ?? ''));
    expect(markup).toContain('data-test="ccr.ee_analytic_vs_simulated"');
    expect(markup).toContain('Analytic and simulated EE of a single swap');
    expect(markup).toContain('data-test="ccr.cva_recomputed"');
  });

  it('the variants table sets the six variants side by side with the headline numbers and the ORE status', () => {
    const markup = html(<C12VariantsTable peers={peers} onPick={() => undefined} current={netting.variant_id} />);
    for (const id of VARIANT_ORDER) expect(markup).toContain(`data-variant="${id}"`);
    for (const d of ALL) {
      expect(markup).toContain(cell(d.outputs.cva_dva.cva.amount, 'en'));
      expect(markup).toContain(cell(d.outputs.sa_ccr.ead.amount, 'en'));
    }
    expect(markup).toContain('data-ore="not-applicable"');
    expect(markup).toContain('no reconciliation');
    expect(markup).toContain('ct-current');
    expect(html(<C12VariantsView sel={selOf(netting, {}, false)} onPick={() => undefined} />)).toContain('data-state="loading"');
    expect(html(<C12VariantsView sel={selOf(netting)} onPick={() => undefined} />)).toContain('data-table="variants-c12"');
  });

  it('the context names what the case is: a real curve, a synthetic book, a proxy counterparty curve, initial margin never SIMM, and every named parameter as a convention', () => {
    const markup = html(<C12ContextView sel={selOf(withIm)} />);
    const o = withIm.outputs;
    expect(markup).toContain('data-fixture="true"');
    expect(markup).toContain(text(o.sign_convention.statement));
    expect(markup).toContain('never ISDA SIMM');
    expect(markup).toContain('no ORE reconciliation');
    for (const t of o.book.trades) expect(markup).toContain(`data-trade="${t.trade_id}"`);
    expect(markup).toContain(o.curve.curve_date);
    expect(markup).toContain('data-table="c12-curve"');
    expect(markup).toContain('Interpolated silently');
    const conventions = (markup.match(/data-status="convention"/g) ?? []).length;
    expect(conventions).toBeGreaterThanOrEqual(Object.keys(o.named_parameters).length);
    expect(Object.keys(o.named_parameters).length).toBe(Object.keys(C12_OUTPUTS.object.named_parameters.object).length);
    expect(markup).not.toContain('data-status="regulatory"');
    // the models artifact: every calibration date, the proxy, the limits and the unverified closed forms
    const fit = fitOf(selOf(withIm))!;
    for (const c of fit.calibrations) expect(markup).toContain(`data-calibration="${c.backtest_date}"`);
    expect(markup).toContain('data-label="proxy"');
    expect(markup).toContain(text(fit.credit_curve.derivation));
    for (const l of fit.limits) expect(markup).toContain(text(l));
    expect(markup).toContain('data-unverified="true"');
    expect(markup).toContain('UNVERIFIED as papers');
  });

  it('the Spanish rendering reads as Spanish and keeps the number format of the language', () => {
    setLang('es');
    expect(html(<ProfileView sel={selOf(netting)} />)).toContain('Perfiles de exposición');
    const imM = html(<CollateralView sel={selOf(withIm)} />);
    expect(imM).toContain('proxy por regresión');
    expect(imM).toContain('no SIMM');
    expect(imM).toContain(cell(netting.outputs.exposure.eepe.amount, 'es'));
    expect(html(<WwrView sel={selOf(wwr)} />)).toContain('no tiene conciliación con ORE');
    expect(html(<WwrView sel={selOf(wwr)} />)).toContain(formatNumber(wwr.outputs.wrong_way_risk!.largest_b_w, 'es', { digits: 4 }));
    const ctx = html(<C12ContextView sel={selOf(netting)} />);
    expect(ctx).toContain('convención');
    expect(ctx).toContain('Nocional (USD)');
    expect(ctx).toContain('Plazos ausentes');
    expect(html(<SaCcrView sel={selOf(netting)} />)).toContain('El puerto en vivo reproduce el bloque del documento');
    expect(html(<PitView sel={selOf(netting)} />)).toContain('El histograma de los PIT');
    expect(html(<ComparisonView sel={selOf(netting)} />)).toContain('Regulatorio contra modelado');
    expect(html(<C12VariantsTable peers={peers} onPick={() => undefined} current={netting.variant_id} />)).toContain('Riesgo de correlación adversa');
  });

  it('every view reads its number from the document: a changed field changes the markup', () => {
    const odd = clone(netting);
    odd.outputs.exposure.eepe.amount = 12345678;
    expect(html(<ProfileView sel={selOf(odd)} />)).toContain(cell(12345678, 'en'));
    expect(html(<ProfileView sel={selOf(netting)} />)).not.toContain(cell(12345678, 'en'));
    const reg = clone(netting);
    reg.outputs.girr.delta_charge.amount = 87654321;
    expect(html(<ComparisonView sel={selOf(reg)} />)).toContain(cell(87654321, 'en'));
    const bt = clone(netting);
    bt.outputs.backtest.book_horizons[5].w2 = 9.8765;
    expect(html(<ExceedanceView sel={selOf(bt)} />)).toContain(digits(9.8765, 'en'));
    const cva = clone(netting);
    cva.outputs.cva_dva.buckets[0].cva_term = 4321.5;
    expect(html(<CvaView sel={selOf(cva)} />)).toContain(formatNumber(4321.5, 'en', { digits: 4 }));
  });

  it('a null block shows "not available" with its reason, never an empty chart', () => {
    // the ORE profile of a reconciled variant is dropped: the column says not available and no overlay series is drawn
    const noOre = clone(netting);
    noOre.outputs.ore_reconciliation = { ...noOre.outputs.ore_reconciliation, status: 'not-applicable', ore_ee: null, ore_ee_discounted: null, ore_eepe: null, ore_cva: null, ore_dim: null, agreement: null, eepe_agreement: null, cva_agreement: null, dim_agreement: null, all_within_two_se: null, ore_version: null, platform: null, run_seconds: null, reason: { en: 'ORE did not run on this machine.', es: 'ORE no corrió en esta máquina.' } } as never;
    const markup = html(<ProfileView sel={selOf(noOre)} />);
    expect(markup).toContain('data-series="6"');
    expect(markup).toContain('ORE did not run on this machine.');
    expect(markup).toContain('data-na="true"');
    // the models artifact absent: the GIRR tenors are not available, not zero
    const sel = selOf(netting);
    const bare: C12Sel = { ...sel, data: { ...sel.data, models: { ...(sel.data.models as object), fit: undefined } as never } };
    const girr = html(<GirrView sel={bare} />);
    expect(girr).toContain('data-na="true"');
    expect(girr).toContain(NA);
  });
});
