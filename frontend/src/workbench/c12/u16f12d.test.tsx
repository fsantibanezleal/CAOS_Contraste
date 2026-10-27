// U16-F12d (fix round 5, the fourth capture review R4, batch c15): on the committed C12 documents, in both languages. No Spanish
// string of the C12 views carries swap, swaption, spread, spot, forward or wheel (ruling 6: permuta, opción sobre permuta,
// diferencial, al contado, a plazo, paquete; B1), and the minors of the batch: the ORE read-out under the profile grid (m1), the
// read-out says "compared" when a point is outside two standard errors (m2), no ASCII "W^2" in a note (m4), the formulas in
// symbols (n2), the stressed effective EPE below the current one said in words (n4), no number broken over a line (n5), a taller
// collateral drawing (n6), lower case after a Spanish colon (n7) and the SA-CCR maturity buckets with their ranges (n8).
import { readFileSync, readdirSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, setLang } from '../c03/u6-testkit';
import { committed } from '../c08/spanish-testkit';
import { committedData as manifestData, render, textOf } from '../c03/u16f2-kit';
import { C12ContextView, C12TestsView } from './C12Common';
import { CvaView, WwrView } from './CreditViews';
import { CollateralView, ProfileView } from './ExposureViews';
import { BaCvaView, ComparisonView, GirrView, SaCcrView } from './RegulatoryViews';
import { defaultSel, segmentText, type C12Sel, type Peers } from './selection';

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
const selOf = (name: string): C12Sel => defaultSel(fixtureData('C12', committed<VariantArtifact>('C12', `${name}.json`), models, title), peers) as C12Sel;
/** The instrument words of the ruling of 2026-10-27 (R4 c15 B1). */
const INSTRUMENT_WORDS = /\b(swaps?|swaptions?|spreads?|spot|t-forward|forward|wheel)\b/gi;

describe('U16-F12d C12', () => {
  afterEach(() => setLang('en'));

  it('B1: no Spanish string of the C12 views carries swap, swaption, spread, spot, forward or wheel', () => {
    const dir = new URL('./', import.meta.url);
    const found: string[] = [];
    for (const f of readdirSync(dir).filter((n) => /\.tsx?$/.test(n) && !n.includes('.test.'))) {
      const src = readFileSync(new URL(f, dir), 'utf8');
      for (const m of src.matchAll(/\bes: (['`])((?:\\.|(?!\1).)*)\1/g)) {
        const words = m[2].replace(/\$\{[^}]*\}/g, '').match(INSTRUMENT_WORDS);
        if (words) found.push(`${f}: ${words.join(', ')}: ${m[2].slice(0, 80)}`);
      }
    }
    expect(found).toEqual([]);
  });

  it('B1: the Spanish views of the netting set print none of those words where the view writes the text', () => {
    for (const [name, el] of [
      ['tests', <C12TestsView key="t" sel={selOf('netting-set')} />],
      ['profile', <ProfileView key="p" sel={selOf('netting-set')} />],
      ['saccr', <SaCcrView key="s" sel={selOf('netting-set')} />],
      ['cva', <CvaView key="c" sel={selOf('netting-set')} />],
    ] as const) {
      // the measure note of the exposure block is a document text (re-baked by the integrator), so it is cut out first
      const doc = (committed<VariantArtifact>('C12', 'netting-set.json').outputs as unknown as { exposure: { measure_note: { es: string } } }).exposure.measure_note.es;
      const text = textOf(render(el, 'es')).replace(doc, '');
      expect(text.match(INSTRUMENT_WORDS), name).toBeNull();
    }
    expect(textOf(render(<C12TestsView sel={selOf('netting-set')} />, 'es'))).toContain('Opción sobre permuta pagadora frente a QuantLib 1.44');
    expect(textOf(render(<C12TestsView sel={selOf('netting-set')} />, 'en'))).toContain('Payer swaption against QuantLib 1.44');
  });

  for (const lang of ['en', 'es'] as const) {
    it(`m1 (${lang}): the profile grid comes before the ORE read-out`, () => {
      const markup = render(<ProfileView sel={selOf('netting-set')} />, lang);
      expect(markup.indexOf('data-table="c12-profile-grid"')).toBeGreaterThan(0);
      expect(markup.indexOf('data-table="c12-profile-grid"')).toBeLessThan(markup.indexOf('data-ore='));
    });

    it(`m2 (${lang}): the profile read-out says "compared", not "reconciled", where a point is outside two standard errors`, () => {
      for (const name of ['csa-mpor-10d', 'csa-mpor-20d']) {
        const text = textOf(render(<ProfileView sel={selOf(name)} />, lang));
        expect(text, name).not.toMatch(lang === 'en' ? /reconciled on open-source/ : /conciliada en open-source/);
        expect(text, name).toMatch(lang === 'en' ? /compared on open-source-risk-engine/ : /comparada en open-source-risk-engine/);
      }
      expect(textOf(render(<ProfileView sel={selOf('netting-set')} />, lang))).toMatch(lang === 'en' ? /reconciled on open-source/ : /conciliada en open-source/);
    });

    it(`m4 (${lang}): no tests note prints the ASCII W^2`, () => {
      const text = textOf(render(<C12TestsView sel={selOf('netting-set')} />, lang));
      expect(text).not.toContain('W^2');
      expect(text).toContain('W²');
    });

    it(`n2 (${lang}): the BA-CVA and GIRR formulas are written in symbols, not ASCII`, () => {
      const ba = textOf(render(<BaCvaView sel={selOf('netting-set')} />, lang));
      expect(ba).not.toMatch(/sqrt\(|raíz\(|\^2|\brho\b/);
      expect(ba).toContain('K = √((ρ Σ SCVA)² + (1 − ρ²) Σ SCVA²)');
      for (const el of [<GirrView key="g" sel={selOf('netting-set')} />, <ComparisonView key="c" sel={selOf('netting-set')} />]) {
        expect(textOf(render(el, lang))).not.toMatch(/sqrt\(/);
      }
    });

    it(`n4 (${lang}): the comparison says when the stressed effective EPE is below the current one, and which one the capital uses`, () => {
      for (const name of ['netting-set', 'csa-mpor-10d', 'csa-mpor-20d']) {
        const o = peers[name as keyof Peers]!.o;
        expect(o.regulatory_comparison.stressed.effective_epe.amount, name).toBeLessThan(o.exposure.eepe.amount);
        const text = textOf(render(<ComparisonView sel={selOf(name)} />, lang));
        expect(text, name).toContain(lang === 'en'
          ? 'the stressed effective EPE is below the current one: the 2007 to 2009 calibration gives this book a smaller exposure. The capital takes the greater of the two, so the current one applies'
          : 'la EPE efectiva en estrés está bajo la actual: la calibración de 2007 a 2009 da a esta cartera una exposición menor. El capital toma la mayor de las dos, así que se aplica la actual');
      }
    });

    it(`n5 (${lang}): the parity tolerance and the test statistic never break over a line, and a quantile keeps its percent sign`, () => {
      const sa = render(<SaCcrView sel={selOf('netting-set')} />, lang);
      expect(textOf(sa)).not.toContain('1e-9');
      expect(sa).toMatch(/white-space:nowrap">10⁻⁹/);
      const tests = render(<C12TestsView sel={selOf('netting-set')} />, lang);
      expect(tests).toMatch(/<span style="white-space:nowrap">[\d.,]+E-\d+<\/span>/);
      expect(segmentText('book-10bd-q90', lang)).toMatch(/90 %$/);
    });

    it(`n6 (${lang}): the collateral drawing keeps 19rem at 1280`, () => {
      expect(render(<CollateralView sel={selOf('netting-set')} />, lang)).toMatch(/class="ct-stack-chart" style="min-height:19rem/);
    });

    it(`n8 (${lang}): the SA-CCR maturity buckets carry their ranges`, () => {
      const text = textOf(render(<SaCcrView sel={selOf('netting-set')} />, lang));
      expect(text).toContain(lang === 'en' ? 'B3, over 5 years' : 'B3, más de 5 años');
      expect(text).toContain(lang === 'en' ? 'B2, 1 to 5 years' : 'B2, de 1 a 5 años');
      expect(text).toContain(lang === 'en' ? 'B1, under 1 year' : 'B1, menos de 1 año');
    });
  }

  it('n7: a Spanish sentence after a colon starts in lower case', () => {
    const cva = textOf(render(<CvaView sel={selOf('netting-set')} />, 'es'));
    expect(cva).not.toMatch(/aproximación: [A-ZÁÉÍÓÚ][a-záéíóú]/);
    const ctx = textOf(render(<C12ContextView sel={defaultSel(manifestData('C12', 'netting-set'), peers) as C12Sel} />, 'es'));
    expect(ctx).not.toMatch(/aproximación: [A-ZÁÉÍÓÚ][a-záéíóú]/);
    const wwr = textOf(render(<WwrView sel={selOf('wrong-way-risk')} />, 'es'));
    expect(wwr).not.toMatch(/adversa: [A-ZÁÉÍÓÚ][a-záéíóú]/);
    const wwrOther = textOf(render(<WwrView sel={selOf('netting-set')} />, 'es'));
    expect(wwrOther).not.toMatch(/adversa: [A-ZÁÉÍÓÚ][a-záéíóú]/);
  });
});
