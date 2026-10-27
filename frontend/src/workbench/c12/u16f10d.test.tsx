// U16-F10d (fix round 4, the third capture review R3, batch c13): on the committed C12 documents, in both languages. The Spanish
// Context prints the estimator in Spanish once the models document carries it bilingual (BL4), the initial-margin read-out says
// "regression proxy" once and leaves the bound to the document's limit (BL2), the collateral table comes before the long read-out
// so its rows show at 1280 (m1, m14), the W² chart keeps the room its axis title needs at 1280 (MJ1) and says a rejection in words
// (m12), and no Spanish string of the C12 views carries an English word of the 2026-10-27 ruling.
import { readFileSync, readdirSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, setLang } from '../c03/u6-testkit';
import { committed } from '../c08/spanish-testkit';
import { committedData as manifestData, render, textOf } from '../c03/u16f2-kit';
import { C12ContextView, C12VariantsTable } from './C12Common';
import { ExceedanceView, w2Bars } from './BacktestViews';
import { CollateralView, NettingView, ProfileView, collateralAxisLabel } from './ExposureViews';
import { ComparisonView, SaCcrView } from './RegulatoryViews';
import { defaultSel, horizonsOf, outputsOf, type C12Sel, type Peers } from './selection';

const title = { en: 'Counterparty credit risk', es: 'Riesgo de crédito de contraparte' };
const MODELS = 'models-hw1f-treasury-2000-2025.json';
const NAMES = ['single-swap', 'netting-set', 'csa-mpor-10d', 'csa-mpor-20d', 'with-im', 'wrong-way-risk'];
const models = committed<ModelsArtifact>('C12', MODELS);
const peers: Peers = Object.fromEntries(
  NAMES.map((n) => {
    const d = committed<VariantArtifact>('C12', `${n}.json`);
    return [n, { variantId: d.variant_id, title: { en: n, es: n }, o: d.outputs }];
  }),
) as unknown as Peers;
const selOf = (name: string, m: ModelsArtifact = models): C12Sel =>
  defaultSel(fixtureData('C12', committed<VariantArtifact>('C12', `${name}.json`), m, title), peers) as C12Sel;
/** The models document as the 2.0.0 producer writes it: the estimator bilingual (pipeline/cases/c12/calibration.py ESTIMATOR_TEXT). */
const ESTIMATOR_ES = 'AR(1) exacto por MCO sobre la tasa cero más corta del Tesoro (Brigo et al., arXiv 0812.4210, ecuaciones 55 a 57)';
const rebaked = (): ModelsArtifact => {
  const m = structuredClone(models) as unknown as { fit: { estimator: unknown } };
  m.fit.estimator = { en: (models as unknown as { fit: { estimator: string } }).fit.estimator, es: ESTIMATOR_ES };
  return m as unknown as ModelsArtifact;
};

describe('U16-F10d C12', () => {
  afterEach(() => setLang('en'));

  it('BL4: the Spanish Context prints the estimator in Spanish from the bilingual document, and the English one stays', () => {
    const es = textOf(render(<C12ContextView sel={selOf('netting-set', rebaked())} />, 'es'));
    expect(es).toContain(ESTIMATOR_ES);
    expect(es).not.toContain('exact AR(1) OLS');
    const en = textOf(render(<C12ContextView sel={selOf('netting-set', rebaked())} />, 'en'));
    expect(en).toContain('exact AR(1) OLS on the shortest Treasury zero rate');
    // a document baked before c12-models 2.0.0 (the English sentence alone) still renders
    expect(textOf(render(<C12ContextView sel={selOf('netting-set')} />, 'en'))).toContain('exact AR(1) OLS');
  });

  for (const lang of ['en', 'es'] as const) {
    it(`BL2 (${lang}): the initial-margin read-out leaves "regression proxy, never SIMM" to the document's limit`, () => {
      const markup = render(<CollateralView sel={selOf('with-im')} />, lang);
      const dd = markup.match(/<dd data-im="regression-proxy"[^>]*>([\s\S]*?)<\/dd>/)?.[1] ?? '';
      expect(dd).not.toMatch(lang === 'en' ? /^a regression proxy, not SIMM/ : /^un proxy por regresión, no SIMM/);
      expect(textOf(dd)).toMatch(lang === 'en' ? /^the ORE dynamic margin by regression of order/ : /^el margen dinámico de ORE por regresión de orden/);
    });

    it(`m1, m14 (${lang}): the collateral table comes before the read-out of the CSA and the margin`, () => {
      for (const name of ['csa-mpor-10d', 'csa-mpor-20d', 'with-im']) {
        const markup = render(<CollateralView sel={selOf(name)} />, lang);
        expect(markup.indexOf('data-table="c12-collateral"'), name).toBeGreaterThan(0);
        expect(markup.indexOf('data-table="c12-collateral"'), name).toBeLessThan(markup.indexOf('data-table="c12-csa"'));
      }
    });

    it(`m7 (${lang}): the collateral axis names the initial margin it also draws`, () => {
      const unit = { en: 'thousand USD', es: 'miles de USD' };
      expect(collateralAxisLabel(true, unit)[lang]).toBe(lang === 'en' ? 'EE and initial margin (thousand USD)' : 'EE y margen inicial (miles de USD)');
      expect(collateralAxisLabel(false, unit)[lang]).toBe(lang === 'en' ? 'EE (thousand USD)' : 'EE (miles de USD)');
      expect(render(<CollateralView sel={selOf('with-im')} />, lang)).toContain('data-series="5"');
    });

    it(`MJ1, m12 (${lang}): the W² chart keeps 13.5rem at 1280 and a rejected horizon says so in its label`, () => {
      const markup = render(<ExceedanceView sel={selOf('netting-set')} />, lang);
      expect(markup).toMatch(/class="ct-stack-chart" style="min-height:clamp\(13\.5rem/);
      const rows = horizonsOf(outputsOf(selOf('netting-set')), 'book');
      const bars = w2Bars(rows, '10bd');
      expect(bars.map((b) => b.id)).toEqual(['10bd', '20bd', '1m', '3m', '6m', '12m']);
      for (const b of bars) {
        const h = rows.find((r) => r.horizon === b.id)!;
        expect(b.label[lang].endsWith(lang === 'en' ? ', rejected' : ', rechazado'), b.id).toBe(h.reject_at_5pct);
        expect(b.value).toBe(h.w2);
      }
      expect(bars.some((b) => b.tone === 'bad')).toBe(true);
    });

    it(`m5 (${lang}): the SA-CCR caption gives the replacement cost its floor under a CSA, not zero`, () => {
      const text = textOf(render(<SaCcrView sel={selOf('csa-mpor-10d')} />, lang));
      expect(text).not.toMatch(lang === 'en' ? /the replacement cost falls to zero/ : /el costo de reemplazo baja a cero/);
      expect(text).toContain(lang === 'en' ? 'the threshold plus the minimum transfer amount less the independent amount' : 'el umbral más el monto mínimo de transferencia menos el monto independiente');
    });

    it(`m6 (${lang}): the hedging-set row names the number it labels`, () => {
      const text = textOf(render(<SaCcrView sel={selOf('netting-set')} />, lang));
      expect(text).not.toMatch(/0\.5 percent of (?!it)|0,5 por ciento de (?!él)/);
      expect(text).toContain(lang === 'en' ? 'effective notional after the offset formula of CRE52.57' : 'nocional efectivo tras la fórmula de compensación de CRE52.57');
    });

    it(`m2 (${lang}): the ORE column of the variants table does not say "reconciled" where a point is outside two standard errors`, () => {
      const markup = render(<C12VariantsTable peers={peers} onPick={() => undefined} current="netting-set" />, lang);
      for (const name of ['csa-mpor-10d', 'csa-mpor-20d', 'with-im']) {
        const o = peers[name as keyof Peers]!.o;
        expect(o.ore_reconciliation.all_within_two_se, name).toBe(false);
        const row = markup.match(new RegExp(`<tr data-variant="${name}"[\\s\\S]*?</tr>`))?.[0] ?? '';
        expect(textOf(row), name).toContain(lang === 'en' ? 'compared, outside two SE' : 'comparada, fuera de dos ES');
      }
    });
  }

  for (const lang of ['en', 'es'] as const) {
    it(`m1 (${lang}): the profile and the comparison tables get the taller box at 1280`, () => {
      expect(render(<ProfileView sel={selOf('netting-set')} />, lang)).toMatch(/class="ct-c12-tall"[\s\S]*data-table="c12-profile"/);
      expect(render(<ComparisonView sel={selOf('netting-set')} />, lang)).toMatch(/class="ct-c12-tall"[\s\S]*data-table="c12-regulatory"/);
    });

    it(`m10, m13 (${lang}): a named parameter's unit is never joined to its value, the error is ES in Spanish, the question not repeated`, () => {
      const text = textOf(render(<C12ContextView sel={defaultSel(manifestData('C12', 'netting-set'), peers) as C12Sel} />, lang));
      expect(text).not.toMatch(/Financieras sector|Financials sector|Grado de inversión clase|Investment grade class|\d{4}-\d{2}-\d{2} (fecha|date)\b|\d{4}-\d{2} (mes|month)\b|\d orden del polinomio|\d polynomial order/);
      expect(text).toMatch(lang === 'en' ? /\(SE \d/ : /\(ES \d/);
      if (lang === 'es') expect(text).not.toMatch(/\(SE \d/);
      const q = (committed<{ question: { en: string; es: string } }>('manifests', 'C12.json')).question[lang];
      expect(text.split(q.slice(0, 40)).length - 1).toBe(1);
    });

    it(`m11, m15 (${lang}): the variants caption follows the table's CVA, and the netting block says it is without collateral`, () => {
      const v = textOf(render(<C12VariantsTable peers={peers} onPick={() => undefined} current="netting-set" />, lang));
      expect(v).not.toMatch(/changes the CVA and not the exposure|cambia el CVA y no la exposición/);
      expect(peers['wrong-way-risk' as keyof Peers]!.o.cva_dva.cva.amount).toBeCloseTo(peers['netting-set' as keyof Peers]!.o.cva_dva.cva.amount, 6);
      const n = textOf(render(<NettingView sel={selOf('csa-mpor-10d')} />, lang));
      expect(n).toContain(lang === 'en' ? 'Netted EE, without collateral' : 'EE neteada, sin colateral');
      expect(textOf(render(<NettingView sel={selOf('netting-set')} />, lang))).not.toContain(lang === 'en' ? 'without collateral' : 'sin colateral;');
    });
  }

  it('the Spanish strings of the C12 views carry no English word of the 2026-10-27 ruling (backtest, proxy, hazard, add-on)', () => {
    const dir = new URL('./', import.meta.url);
    const found: string[] = [];
    for (const f of readdirSync(dir).filter((n) => /\.tsx?$/.test(n) && !n.includes('.test.'))) {
      const src = readFileSync(new URL(f, dir), 'utf8');
      for (const m of src.matchAll(/\bes: (['`])((?:\\.|(?!\1).)*)\1/g)) {
        const words = m[2].match(/\b(backtest\w*|back-test\w*|proxy|proxies|hazard|add-on)\b/gi);
        if (words) found.push(`${f}: ${words.join(', ')}: ${m[2].slice(0, 80)}`);
      }
    }
    expect(found).toEqual([]);
  });
});
