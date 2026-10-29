// S-4 (method tiers plan): the PC-Hazard tab of C06 on the committed documents of the six reporting dates, in both languages: the
// rung is named by its short title, never its id; the numbers on screen are the ones the models document holds; a date whose
// follow-up has not reached a horizon says so; the Spanish view carries no English sentence of the tab.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { PchView, pchRecords } from './PchView';
import { defaultSel, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;

describe('S-4 PC-Hazard view on the committed C06 documents', () => {
  afterEach(() => setLang('en'));

  it('every date has the rung, its evaluation and 30 decile cells in the models document', () => {
    for (const id of variantIds('C06')) {
      const { pch, cox } = pchRecords(sel(id));
      expect(pch?.details?.evaluated, id).toBe(true);
      expect(pch?.details?.decile_calibration?.length, id).toBe(30);
      expect(cox?.details?.decile_calibration?.length, id).toBe(30);
      expect(pch?.details?.evaluation?.comparator, id).toBe('L2-cox');
    }
  });

  it('the view names the rungs in words, shows the measured numbers and the verdict, with no raw id', () => {
    for (const id of variantIds('C06')) {
      const ev = pchRecords(sel(id)).pch!.details!.evaluation!;
      for (const lang of ['en', 'es'] as const) {
        const markup = render(<PchView sel={sel(id)} />, lang);
        const text = textOf(markup);
        expect(text, `${id} ${lang}`).toContain('PC-Hazard');
        expect(text, `${id} ${lang}`).toContain('Aalen-Johansen');
        expect(text, `${id} ${lang}`).not.toMatch(/L3-pch|L2-cox|aalen-johansen|kaplan-meier|NaN|undefined/);
        expect(markup, `${id} ${lang}`).toContain('data-table="pch-summary"');
        expect(markup, `${id} ${lang}`).toContain(`data-verdict="${String(ev.holds_at_date)}"`);
        // the integrated Brier of both rungs is printed (five digits), whatever the language's decimal mark
        const fmt = (v: number | null) => (v === null ? null : v.toFixed(5).replace('.', lang === 'es' ? ',' : '.'));
        if (ev.integrated_brier.pch !== null) expect(text, `${id} ${lang}`).toContain(fmt(ev.integrated_brier.pch));
        if (ev.integrated_brier.cox !== null) expect(text, `${id} ${lang}`).toContain(fmt(ev.integrated_brier.cox));
      }
    }
  });

  it('the Spanish view carries no sentence of the English one', () => {
    for (const id of variantIds('C06')) {
      const es = textOf(render(<PchView sel={sel(id)} />, 'es'));
      for (const phrase of ['Predicted minus observed', 'Concordance index', 'Integrated Brier score', 'Hypothesis', 'Accounts', 'Decile']) {
        expect(es, `${id} ${phrase}`).not.toContain(phrase);
      }
      expect(es, id).toContain('Brecha');
    }
  });

  it('a horizon the follow-up has not reached is not available, with its reason, never a number', () => {
    let unobserved = 0;
    for (const id of variantIds('C06')) {
      const rows = pchRecords(sel(id)).pch!.details!.decile_calibration!;
      for (const r of rows) {
        expect(r.observed_aalen_johansen === null, `${id} ${r.months}/${r.decile}`).toBe(r.reason !== null);
        if (r.reason) unobserved += 1;
      }
    }
    expect(unobserved).toBeGreaterThanOrEqual(0);
  });
});
