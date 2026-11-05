// U16-F10b (fix round 4, the R3 capture review of C03, batch c04 minors), on the committed C03 documents in both languages: fixed
// decimals in a column (m2), no cents on billions (m3), the curves' ticks on the 12-month grid with the rail's month marked (m4),
// dates and numbers kept whole at 390 (m5), the TabPFN reason without a path (m9), and the rung words the ruling translates.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf, variantIds } from './u16f2-kit';
import { setLang } from './u6-testkit';
import { KIND_TEXT, defaultSel, reasonText, type C03Sel } from './selection';
import { FiveYearView, StabilityView, curveMarks, curveTicks } from './VintageViews';

const selOf = (id: string) => defaultSel(committedData('C03', id)) as C03Sel;
const LANGS = ['en', 'es'] as const;
const table = (markup: string, name: string) => markup.match(new RegExp(String.raw`<table[^>]*data-table="${name}"[\s\S]*?</table>`))?.[0] ?? '';
const cells = (t: string, col: number) => [...t.matchAll(/<tr[^>]*data-vintage[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)][col]?.[1].replace(/<[^>]*>/g, '') ?? '');

describe('U16-R3 c04 on the committed C03 documents', () => {
  afterEach(() => setLang('en'));

  it('m2: a column keeps its decimals (Brier and AUC three, PSI three), never "0.1" beside "0.106"', () => {
    for (const lang of LANGS) {
      for (const v of variantIds('C03')) {
        const five = table(render(<FiveYearView sel={selOf(v)} />, lang), 'five-year-mark');
        for (const c of [...cells(five, 8), ...cells(five, 9)].filter((x) => /\d/.test(x))) expect(c, `${lang} ${v}`).toMatch(/^\d[.,]\d{3}$/);
        const st = table(render(<StabilityView sel={selOf(v)} />, lang), 'stability');
        for (const c of cells(st, 1)) expect(c, `${lang} ${v}`).toMatch(/^\d[.,]\d{3}$/);
      }
    }
  });

  it('m3 and m5: the approved amount has no cents, and the mark date keeps one line', () => {
    for (const lang of LANGS) {
      const t = table(render(<FiveYearView sel={selOf(variantIds('C03')[0])} />, lang), 'five-year-mark');
      for (const c of cells(t, 3)) expect(c).not.toMatch(/[.,]\d{2}$/);
      expect(t).toMatch(/<td style="white-space:nowrap"[^>]*>\d{4}-\d{2}-\d{2}<\/td>/);
      expect(t).not.toMatch(/<td class="ct-text">\d{4}-\d{2}-\d{2}<\/td>/);
    }
  });

  it('m4: the curves tick at the 12-month grid of the data and mark the rail month', () => {
    const grid = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60];
    expect(curveTicks(grid).map((t) => t.value)).toEqual([12, 24, 36, 48, 60]);
    expect(curveTicks(grid)[0].label).toEqual({ en: '12', es: '12' });
    expect(curveMarks(36)).toEqual([{ x: 36, label: { en: 'Month 36 (the rail)', es: 'Mes 36 (el panel)' } }]);
  });

  it('m9: the TabPFN reason names the extra, not a repository path, for the committed string and the re-baked one', () => {
    const old = 'TabPFN is the optional extra (data-pipeline/requirements-tabpfn.txt) and it is not installed in the bake environment: the challenger is declared absent, and no number stands in for it';
    const now = 'TabPFN is an optional extra of the bake environment and it is not installed there: the challenger is declared absent, and no number stands in for it';
    for (const r of [old, now]) {
      const t = reasonText(r);
      expect(t.en).not.toContain('requirements-tabpfn.txt');
      expect(t.es).not.toContain('requirements-tabpfn.txt');
      expect(t.es).toContain('TabPFN es un extra opcional');
    }
  });

  it('the rung words carry no ruled English word in Spanish (scorecard, boosting)', () => {
    for (const k of Object.values(KIND_TEXT)) expect(k.es).not.toMatch(/scorecard|boosting/i);
    setLang('es');
    expect(textOf(render(<FiveYearView sel={selOf(variantIds('C03')[0])} />, 'es'))).not.toMatch(/Scorecard|boosting/);
  });
});
