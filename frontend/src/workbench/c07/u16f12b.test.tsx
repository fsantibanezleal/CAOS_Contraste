// U16-F12b (fix round 5, the R4 capture review of C07, batch c09 M1 and minors), on the committed C07 documents in both languages:
// the Segments gap table puts the two gaps it is named for next to the segment, and takes the wider share of the row (at 1280 both gap
// columns were cut at the card edge); the bridge drawing names its first step short with the full text as the hint (n1), says how a
// step of zero is drawn and what its axis covers (m2, m3); the consumer B-1 caption is one sentence (n2); the generator id is code (m9).
import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { html } from '../c20/testkit';
import { BridgeView, SegmentsView, stepShort } from './RegimeViews';
import { C07ContextView } from './C07Common';
import { TablesView } from './ValidationViews';
import { defaultSel, type C07Sel } from './selection';

const TITLE = { en: 'Chile provisions trilogy', es: 'Trilogía de provisiones de Chile' };
const at = (file: string) => defaultSel(committedData('C07', file, 'models-banco-andino.json', TITLE)) as C07Sel;
const FILES = ['base.json', 'combined-severe.json'];
const heads = (markup: string, table: string) => {
  const t = markup.match(new RegExp(String.raw`<table[^>]*data-table="${table}"[\s\S]*?</thead>`))?.[0] ?? '';
  return [...t.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((m) => m[1].replace(/<[^>]*>/g, ''));
};
const src = readFileSync(new URL('./RegimeViews.tsx', import.meta.url), 'utf8');

describe('U16-R4 c09 on the committed C07 documents', () => {
  afterEach(() => setLang('en'));

  it('M1: the gap table shows the segment, then the two gaps against B-1, then the three provisions', () => {
    for (const f of FILES) {
      setLang('en');
      expect(heads(html(<SegmentsView sel={at(f)} />), 'segments').slice(0, 3)).toEqual(['Segment', 'IFRS 9 minus B-1', 'BdE minus B-1']);
      setLang('es');
      expect(heads(html(<SegmentsView sel={at(f)} />), 'segments').slice(0, 3)).toEqual(['Segmento', 'IFRS 9 menos B-1', 'BdE menos B-1']);
    }
  });

  it('M1: the table card takes the wider share of the row, the drawing the narrower', () => {
    expect(src).toMatch(/the gap table takes three fifths[\s\S]*?<ViewsRow shares=\{\[2, 3\]\}>\s*<PlotCard\s+fill\s+title=\{\{ en: 'Provision by segment under the three regimes'/);
  });

  it('n1: a bridge step is drawn under the words before its colon, the full label kept for the hint', () => {
    const s = stepShort({ en: 'Measurement basis: bank PD, LGD and recoveries against the B-1 matrices', es: 'Base de medición: PD, LGD y recuperaciones del banco' });
    expect(s).toEqual({ en: 'Measurement basis', es: 'Base de medición' });
    expect(stepShort({ en: 'IFRS 9 overlays', es: 'Ajustes posmodelo IFRS 9' })).toEqual({ en: 'IFRS 9 overlays', es: 'Ajustes posmodelo IFRS 9' });
  });

  it('m2 and m3: the bridge note says the axis covers the running total and how a step of zero is drawn', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const t = view(<BridgeView sel={at('base.json')} />);
      if (lang === 'en') {
        expect(t).toContain('the axis covers the running total of the bridge');
        expect(t).toContain('a step of zero (B-1 minimum top-up, not in IFRS 9) is a dot on the running total');
      } else {
        expect(t).toContain('el eje cubre el total acumulado del puente');
        expect(t).toContain('un paso de cero (Complemento del mínimo B-1, fuera de IFRS 9) es un punto sobre el total acumulado');
      }
    }
  });

  it('n2: the B-1 caption says what the table lacks in one sentence with its capital', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const t = view(<TablesView sel={at('base.json')} />);
      expect(t).not.toMatch(/\. la tabla|\. the table/);
      expect(t).toContain(lang === 'en' ? 'The table gives no PDI or PE for its cells.' : 'La tabla no da PDI ni PE para sus celdas.');
    }
  });

  it('m9: the generator id of the bank note is printed as code the page does not translate', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      expect(html(<C07ContextView sel={at('base.json')} />)).toMatch(/<code translate="no">banco-andino-synthetic\/1\.0\.0<\/code>/);
    }
  });
});
