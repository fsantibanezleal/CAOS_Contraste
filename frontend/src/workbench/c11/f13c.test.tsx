// U16-F13c (R5 batch c15, C11): every row of the back-test table names its segment, the tail level of the row (Q1, R5 ruling 2: the
// table had no segment), and the portfolio where a row has none; with the minors of the batch fixed in the view: the withheld loss
// sentence names its subject (n1), a Spanish clause after a colon starts in lower case (n3), and the published Acerbi-Szekely reference
// points are written with two decimals wherever they appear (n4). Reads the committed documents, in both languages.
import { afterEach, describe, expect, it } from 'vitest';
import type { TestRow } from '../../lib/contract.types';
import { html, setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { noteText } from '../c08/notes';
import { EsBacktestView, TestsView } from './BacktestViews';
import { TimelineView } from './ExceedanceViews';
import { MarketTestsTable } from './MarketCommon';
import { defaultSel, outputsOf, type C11Sel } from './selection';

const TITLE = { en: 'Market VaR and ES back-testing', es: 'Pruebas retrospectivas de VaR y ES de mercado' };
const WINDOWS = ['calm-2004-06', 'equity-2007-09', 'equity-2020', 'fx-2008', 'mixed-2023', 'rates-2022'];
const selOf = (w: string) => defaultSel(committedData('C11', `${w}.json`, 'models-ladder.json', TITLE)) as C11Sel;
const NBSP = ' ';
const rowsOf = (markup: string) => [...markup.matchAll(/<tr [^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => m[2]);

describe('U16-F13c, C11 (R5 c15)', () => {
  afterEach(() => setLang('en'));

  it('Q1: every back-test row names its segment, the tail level, at both levels of every window', () => {
    const want = {
      en: { 0.01: `1${NBSP}% tail (99${NBSP}% VaR)`, 0.025: `2.5${NBSP}% tail (97.5${NBSP}% VaR)` },
      es: { 0.01: `cola de 1${NBSP}% (VaR al 99${NBSP}%)`, 0.025: `cola de 2,5${NBSP}% (VaR al 97,5${NBSP}%)` },
    } as const;
    for (const w of WINDOWS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        for (const alpha of [0.01, 0.025] as const) {
          const rows = rowsOf(html(<TestsView sel={{ ...selOf(w), alpha }} />));
          expect(rows.length, w).toBeGreaterThan(0);
          for (const r of rows) {
            expect(r, `${w} ${lang} ${alpha}`).toContain('ct-row-detail');
            expect(r.replace(/<[^>]*>/g, ''), `${w} ${lang} ${alpha}`).toContain(want[lang][alpha]);
          }
        }
      }
    }
  });

  it('ruling 2: a row of no segment names the whole portfolio', () => {
    const row = { ...(selOf('rates-2022').data.variant.tests[0] as TestRow), segment: null };
    for (const [lang, words] of [['en', 'whole portfolio'], ['es', 'toda la cartera']] as const) {
      setLang(lang);
      expect(view(<MarketTestsTable rows={[row]} table="t" />)).toContain(words);
    }
  });

  it('n1: the withheld realised loss names its subject before "not available"', () => {
    const withheld = WINDOWS.filter((w) => outputsOf(selOf(w))!.grid.realised_loss.status !== 'included');
    expect(withheld.length).toBeGreaterThan(0);
    for (const w of withheld) {
      for (const [lang, lead] of [['en', 'Realised loss: not available. A component'], ['es', 'Pérdida realizada: no disponible. Un componente']] as const) {
        setLang(lang);
        const text = view(<TimelineView sel={selOf(w)} />);
        expect(text, w).toContain(lead);
        expect(text, w).not.toMatch(/(not available|no disponible) \(/);
      }
    }
  });

  it('n3: a Spanish clause after a colon starts in lower case (the gate rules and the published ES reference)', () => {
    setLang('es');
    const gates = view(<TestsView sel={selOf('rates-2022')} />);
    expect(gates).toContain('Proporción de fallas de Kupiec: rojo al 5 por ciento');
    expect(gates).not.toMatch(/Kupiec: Rojo/);
    const es = view(<EsBacktestView sel={{ ...selOf('rates-2022'), alpha: 0.025 }} />);
    expect(es).toContain(`: un punto de referencia publicado`);
    expect(es).not.toContain(': Un punto');
  });

  it('n4: the Acerbi-Szekely reference points of a note have two decimals, as the mark and the card write them', () => {
    const note = 'the critical values are simulated per model; -0.70 and -1.8 are a published reference point, not a threshold';
    expect(noteText(note, 'es')).toBe('los valores críticos se simulan por modelo; -0,70 y -1,80 son un punto de referencia publicado, no un umbral');
    expect(noteText(note, 'en')).toBe('the critical values are simulated per model; -0.70 and -1.80 are a published reference point, not a threshold');
  });
});
