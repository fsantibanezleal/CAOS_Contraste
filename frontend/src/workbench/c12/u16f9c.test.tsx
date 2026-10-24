// U16-F9c (fix round 3, the partial R2b review of C12, report c13), on the committed documents: a table of a handful of rows shows
// its rows at 1280 (the PIT classes, the GIRR tenors and the SA-CCR trades in a card beside their drawing; the exceedances and the
// collateral in the taller box), the 309 calibrations paged with their count, no "UNVERIFIED" marker or plan id in the view's own
// words, and the with-im variant called by its one name.
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { setLang } from '../c03/u6-testkit';
import { committed, committedData } from '../c08/spanish-testkit';
import { manifestOf, render, textOf } from '../c03/u16f2-kit';
import { C12ContextView } from './C12Common';
import { ExceedanceView, PitView } from './BacktestViews';
import { CvaView } from './CreditViews';
import { CollateralView } from './ExposureViews';
import { GirrView, SaCcrView } from './RegulatoryViews';
import { VARIANT_TEXT, defaultSel, type C12Sel, type Peers } from './selection';

const title = { en: 'Counterparty credit risk', es: 'Riesgo de crédito de contraparte' };
const MODELS = 'models-hw1f-treasury-2000-2025.json';
const NAMES = ['single-swap', 'netting-set', 'csa-mpor-10d', 'csa-mpor-20d', 'with-im', 'wrong-way-risk'];
const data = (name: string) => committedData('C12', `${name}.json`, MODELS, title);
const peers: Peers = Object.fromEntries(
  NAMES.map((n) => {
    const d = committed<VariantArtifact>('C12', `${n}.json`);
    return [n, { variantId: d.variant_id, title: { en: n, es: n }, o: d.outputs }];
  }),
) as unknown as Peers;
const sel = (name: string): C12Sel => defaultSel(data(name), peers) as C12Sel;
/** The markup after the numbers card opens: a table named here sits in the card beside the drawing, not under it. */
const inNumbersCard = (markup: string, table: string) => {
  const at = markup.indexOf('data-block="numbers"');
  return at >= 0 && markup.indexOf(`data-table="${table}"`, at) > at;
};

describe('U16-F9c C12', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`PIT, GIRR and SA-CCR (${lang}): the tables sit in a card beside the drawing`, () => {
      expect(inNumbersCard(render(<PitView sel={sel('netting-set')} />, lang), 'c12-pit-bins')).toBe(true);
      expect(inNumbersCard(render(<GirrView sel={sel('netting-set')} />, lang), 'c12-girr-tenors')).toBe(true);
      const sa = render(<SaCcrView sel={sel('netting-set')} />, lang);
      expect(inNumbersCard(sa, 'c12-saccr-chain')).toBe(true);
      expect(inNumbersCard(sa, 'c12-saccr-trades')).toBe(true);
    });

    it(`exceedances and collateral (${lang}): the tables get the taller box`, () => {
      expect(render(<ExceedanceView sel={sel('netting-set')} />, lang)).toMatch(/class="ct-c12-tall"[\s\S]*data-table="c12-backtest"/);
      expect(render(<CollateralView sel={sel('netting-set')} />, lang)).toMatch(/class="ct-c12-tall"/);
    });

    it(`context (${lang}): the 309 calibrations are paged, with how many there are`, () => {
      const markup = render(<C12ContextView sel={sel('netting-set')} />, lang);
      const n = (committed<{ fit: { calibrations: unknown[] } }>('C12', MODELS)).fit.calibrations.length;
      const t = markup.match(/<table[^>]*data-table="c12-calibrations"[\s\S]*?<\/table>/)?.[0] ?? '';
      expect((t.match(/<tr data-calibration=/g) ?? []).length).toBe(12);
      expect(markup).toContain(`data-rows="${n}"`);
      expect(textOf(markup)).toContain(lang === 'en' ? `Rows 1 to 12 of ${n}` : `Filas 1 a 12 de ${n}`);
      // the closed forms say what was not checked in words, not as a process marker
      const closed = markup.match(/<dd data-unverified="true">[\s\S]*?<\/dd>/)?.[0] ?? '';
      expect(closed).not.toMatch(/UNVERIFIED|NO están/);
    });

    it(`CVA (${lang}): the caption cites no plan id`, () => {
      expect(textOf(render(<CvaView sel={sel('netting-set')} />, lang))).not.toMatch(/\(R\d+\)/);
    });
  }

  it('the with-im variant is called by the name its selector shows', () => {
    const entry = manifestOf('C12').artifacts.find((a) => a.variant_id === 'with-im')!;
    expect(VARIANT_TEXT['with-im']).toEqual(entry.short_title);
  });
});
