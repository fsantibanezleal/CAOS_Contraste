// U16-F13d (fix round 6, the fifth capture review R5, batches c16 and c17 (C12)), on the committed documents, in both languages.
// M1: the tests table named the segment only on the back-test rows; R5 ruling 2 gives a row with no segment its scope in words,
// "whole book" / "toda la cartera" for the counterparty book, so every row of every variant carries one. The minors: a million is
// "mn" in English (n1, m5), the swap-book note points up to its table (n2, m8), the comparison note names the grey bar (n3, m9), the
// ORE package reads in Spanish order (n6), the QuantLib gate prints its power of ten (c17 n2) and a zero amount is plain USD (c17 m3).
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C12ContextView, C12TestsView } from './C12Common';
import { ProfileView } from './ExposureViews';
import { ComparisonView } from './RegulatoryViews';
import { amount, defaultSel, type C12Sel, type Peers } from './selection';

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
const rowsOf = (markup: string) => markup.split('<tr data-test="').slice(1).map((r) => r.split('</tr>')[0]);
const plain = (s: string) => s.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

describe('U16-F13d C12', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`M1 (${lang}): every row of every tests table names its segment, a book-level row "whole book"`, () => {
      const scope = lang === 'en' ? 'whole book' : 'toda la cartera';
      for (const name of NAMES) {
        const doc = committed<VariantArtifact>('C12', `${name}.json`);
        setLang(lang);
        const rows = rowsOf(html(<C12TestsView sel={sel(name)} />));
        expect(rows.length, name).toBe(doc.tests.length);
        expect(rows.filter((r) => !/data-segment="/.test(r)).map((r) => r.slice(0, 40)), `${name} ${lang}`).toEqual([]);
        doc.tests.forEach((t, i) => {
          if (t.segment === null) expect(plain(rows[i]).toLowerCase(), `${name} ${t.test_id}`).toContain(scope);
          else expect(plain(rows[i]).toLowerCase(), `${name} ${t.test_id}`).not.toContain(scope);
        });
        // no two rows of one test read alike (the CSA pair of the ORE reconciliation)
        const firstCells = rows.map((r) => plain(r.split('</td>')[0]));
        expect(new Set(firstCells).size, name).toBe(firstCells.length);
      }
    });

    it(`c17 n2 (${lang}): the QuantLib gate prints its power of ten, never "1e-6"`, () => {
      setLang(lang);
      const text = view(<C12TestsView sel={sel('netting-set')} />);
      expect(text).not.toMatch(/\b1e-6\b/);
      expect(text).toContain('10⁻⁶');
    });

    it(`n2, m8 (${lang}): the swap-book note points up to its table`, () => {
      setLang(lang);
      const text = view(<C12ContextView sel={sel('netting-set')} />);
      expect(text).not.toMatch(lang === 'en' ? /swaps below/ : /permutas de abajo/);
      expect(text).toContain(lang === 'en' ? 'The netting set holds the swaps above' : 'El conjunto de neteo tiene las permutas de arriba');
    });

    it(`n3, m9 (${lang}): the comparison note names the grey bar`, () => {
      setLang(lang);
      const text = view(<ComparisonView sel={sel('netting-set')} />);
      expect(text).toContain(lang === 'en' ? 'the grey bar is the undivided GIRR charge' : 'la barra gris es el cargo GIRR sin dividir');
    });
  }

  it('n1, m5: a million is "mn" in the English Context, "M" in the Spanish one', () => {
    setLang('en');
    const en = view(<C12ContextView sel={sel('netting-set')} />);
    expect(en).toMatch(/10 mn, 6 mn, 4 mn, 2 mn/);
    expect(en).not.toMatch(/\d m,/);
    setLang('es');
    expect(view(<C12ContextView sel={sel('netting-set')} />)).toMatch(/10 M, 6 M, 4 M, 2 M/);
  });

  it('n6: the ORE package reads in Spanish order, "en el paquete open-source-risk-engine"', () => {
    setLang('es');
    const text = view(<ProfileView sel={sel('netting-set')} />);
    expect(text).toContain('en el paquete open-source-risk-engine 1.8.17.0');
    expect(text).not.toMatch(/1\.8\.17\.0 paquete/);
  });

  it('c17 m3: a zero amount reads in plain USD, never "0 bn USD"', () => {
    expect(amount(0).unit).toEqual({ en: 'USD', es: 'USD' });
    expect(amount(0).value).toBe(0);
    expect(amount(2.5e6).unit).toEqual({ en: 'mn USD', es: 'M USD' });
  });
});
