// U16-F6 (the second fix round, C06), on the committed documents: V06-3, the tables of the deciles, the weights and the stages
// show every column whole at the width of their card (no amount of eleven digits, no header of seven lines, no constant column).
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { StageSummaryView, WeightsView } from './ImpactViews';
import { DecileView } from './ValidationViews';
import { defaultSel, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
const table = (markup: string, name: string) => markup.match(new RegExp(String.raw`<table[^>]*data-table="${name}"[\s\S]*?</table>`))?.[0] ?? '';
const heads = (t: string) => [...t.matchAll(/<th(?:\s[^>]*)?>([\s\S]*?)<\/th>/g)].map((m) => textOf(m[1]).trim());
const cells = (t: string) => [...t.matchAll(/<td(?:\s[^>]*)?>([\s\S]*?)<\/td>/g)].map((m) => textOf(m[1]).trim());

describe('U16-F6 C06 V06-3', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`deciles (${lang}): no Cohort column while one cohort is shown; the headers stay short`, () => {
      const t = table(render(<DecileView sel={sel('rd-2020-06')} />, lang), 'decile-calibration');
      expect(heads(t).length).toBe(5);
      expect(heads(t).join(' ')).not.toMatch(/Cohort|Cohorte/);
    });

    it(`weights (${lang}): the first header is short, the ECL columns are scaled with their unit, no eleven-digit cell`, () => {
      const markup = render(<WeightsView sel={sel('rd-2020-06')} />, lang);
      const t = table(markup, 'weight-grid');
      const h = heads(t);
      expect(h[0].length).toBeLessThanOrEqual(24);
      expect(h[1]).toMatch(/bn USD|mil M USD|mn USD|M USD/);
      for (const c of cells(t)) expect(c, c).not.toMatch(/\d[.,]\d{3}[.,]\d{3}[.,]\d{3}/);
      // the order of the weights is told once, in full, under the table
      expect(textOf(markup)).toMatch(lang === 'en' ? /Weights in the order: Baseline/ : /Pesos en el orden: Base/);
    });

    it(`stages (${lang}): amounts scaled in their column with the unit in the header`, () => {
      const t = table(render(<StageSummaryView sel={sel('rd-2020-06')} />, lang), 'stage-summary');
      const h = heads(t);
      expect(h[2]).toMatch(/bn USD|mil M USD|mn USD|M USD/);
      expect(h[3]).toMatch(/mn USD|M USD|bn USD|mil M USD/);
      for (const c of cells(t)) expect(c, c).not.toMatch(/\d[.,]\d{3}[.,]\d{3}[.,]\d{3}/);
    });
  }
});
