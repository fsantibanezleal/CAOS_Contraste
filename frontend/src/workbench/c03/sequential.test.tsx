// BS-15 (unit D15) on the committed C03 documents: the Sequential tab of the Validation group draws the e-process of every cohort, read at every
// age, in both languages: one row per vintage with the first month it rejects and the light of the fixed-window binomial test at the mark, and
// the cohort by average and by product. A vintage that never rejects says "never", never a number; no raw id reaches the page.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf, variantIds } from './u16f2-kit';
import { setLang } from './u6-testkit';
import { defaultSel, outputsOf, type C03Sel } from './selection';
import { SequentialView } from './SequentialView';

const selOf = (id: string) => defaultSel(committedData('C03', id)) as C03Sel;
const LANGS = ['en', 'es'] as const;
const row = (markup: string, attr: string) => markup.match(new RegExp(String.raw`<tr[^>]*${attr}[^>]*>[\s\S]*?</tr>`))?.[0] ?? '';
const cell = (tr: string, col: number) => [...tr.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)][col]?.[1].replace(/<[^>]*>/g, '') ?? '';

describe('BS-15 on the committed C03 documents', () => {
  afterEach(() => setLang('en'));

  it('every cohort carries the block and draws one row per vintage and the cohort by average and by product', () => {
    for (const id of variantIds('C03')) {
      const s = outputsOf(selOf(id))?.sequential;
      expect(s, id).toBeTruthy();
      for (const lang of LANGS) {
        const markup = render(<SequentialView sel={selOf(id)} />, lang);
        expect(markup).toContain('data-table="sequential-vintages"');
        for (const v of s!.vintages) expect(markup, `${id} ${v.fiscal_year}`).toContain(`data-vintage="${v.fiscal_year}"`);
        expect(markup).toContain('data-cohort="average"');
        expect(markup).toContain('data-cohort="product"');
        expect(textOf(markup)).not.toMatch(/NaN|undefined|Infinity/);
      }
    }
  });

  it('the first month a vintage rejects is the one the document states, and "never" when it does not', () => {
    for (const id of variantIds('C03')) {
      const s = outputsOf(selOf(id))!.sequential;
      for (const lang of LANGS) {
        const markup = render(<SequentialView sel={selOf(id)} />, lang);
        for (const v of s.vintages) {
          const tr = row(markup, `data-vintage="${v.fiscal_year}"`);
          expect(tr).toContain(`data-rejected="${v.rejection_month === null ? 'no' : 'yes'}"`);
          expect(cell(tr, 2), `${id} ${v.fiscal_year} ${lang}`).toBe(v.rejection_month === null ? (lang === 'en' ? 'never' : 'nunca') : String(v.rejection_month));
        }
      }
    }
  });

  it('the cohort rows give the first month of the average and the months gained against the 60-month mark', () => {
    const s = outputsOf(selOf('fy2006-07'))!.sequential;
    expect(s.average.rejection_month).toBe(12);
    const markup = render(<SequentialView sel={selOf('fy2006-07')} />, 'en');
    expect(cell(row(markup, 'data-cohort="average"'), 2)).toBe('12');
    expect(cell(row(markup, 'data-cohort="average"'), 3)).toBe('48');
    const calm = outputsOf(selOf('fy2011-14'))!.sequential;
    expect(calm.average.rejection_month).toBeNull();
    expect(cell(row(render(<SequentialView sel={selOf('fy2011-14')} />, 'en'), 'data-cohort="average"'), 2)).toBe('never');
  });

  it('the Spanish page uses the Spanish words and the light of the binomial test at the mark', () => {
    const markup = render(<SequentialView sel={selOf('fy2006-07')} />, 'es');
    const t = textOf(markup);
    expect(t).toContain('Primer mes rechazado');
    expect(t).toContain('Meses antes de la marca');
    expect(t).toContain('La cohorte, por promedio');
    expect(t).not.toContain('First month rejected');
    expect(cell(row(markup, 'data-vintage="2006"'), 5)).toMatch(/rojo|ámbar|verde/);
  });
});
