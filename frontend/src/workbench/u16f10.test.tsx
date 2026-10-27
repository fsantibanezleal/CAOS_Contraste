// Fix round 4 (U16-F10), from the third capture review (R3) on rc3, on the committed documents. Each test fails on the
// defect it names.
import { afterEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { committedData, render, variantIds } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { LadderView } from './c10/ModelViews';
import { defaultSel as c10Sel, outputsOf as c10Outputs } from './c10/selection';
import { daySeconds } from '../lib/days';
import { evidenceText } from './names';
import { collateralRange, committedCollateral, defaultSel as c12Sel, outputsOf as c12Outputs } from './c12/selection';

describe('U16-F10', () => {
  afterEach(() => setLang('en'));

  for (const v of variantIds('C10')) {
    it(`C10 (${v}): the ladder's Inputs column prints the variant's own calibration of each rung (R3 c11 B1)`, () => {
      const sel = c10Sel(committedData('C10', v));
      const markup = render(<LadderView sel={sel} />, 'en');
      for (const r of c10Outputs(sel)?.rungs ?? []) {
        const cell = markup.match(new RegExp(`<td[^>]*data-inputs="${r.id}"[^>]*>([^<]*)</td>`))?.[1] ?? '';
        for (const p of r.parameters ?? []) {
          if (p.name !== 'rho' || typeof p.value !== 'number') continue;
          expect(cell, `${v} ${r.id}`).toContain(formatNumber(p.value, 'en', { digits: 4 }));
        }
      }
    });
  }

  it("a document day is drawn at the reader's local midnight, so the shell formats it as that day in any zone (R3 c12 B1, c15 B1)", () => {
    for (const day of ['2021-12-31', '2022-01-03', '2024-02-29', '2025-06-30']) {
      const d = new Date(daySeconds(day) * 1000);
      const local = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      expect(local).toBe(day);
      expect(d.getHours()).toBe(0);
    }
  });
  for (const v of variantIds('C12')) {
    it(`C12 (${v}): the collateral range holds the document's collateral, a negative one included (R3 c13 BL5)`, () => {
      const o = c12Outputs(c12Sel(committedData('C12', v)));
      if (!o) return;
      const r = collateralRange(o);
      expect(r.min * 1000).toBeLessThanOrEqual(committedCollateral(o));
      expect(r.max * 1000).toBeGreaterThanOrEqual(committedCollateral(o));
    });
  }
  it('a finding cites a row of no model by its segment, and its evidence names the pair and the variable (R3 c20 M2)', () => {
    const keys = ['stability.chi2@-@typical>higher-risk:committed_exposure_amt', 'stability.chi2@-@typical>higher-risk:interest_rate'];
    for (const lang of ['en', 'es'] as const) {
      const texts = keys.map((k) => evidenceText(k, { caseId: 'C20' }, lang));
      for (const t of texts) {
        expect(t).not.toMatch(/@|committed_exposure_amt|interest_rate|typical>/);
      }
      expect(new Set(texts).size).toBe(keys.length);
    }
  });
});
