// Fix round 4 (U16-F10), from the third capture review (R3) on rc3, on the committed documents. Each test fails on the
// defect it names.
import { afterEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { committedData, render, variantIds } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { LadderView } from './c10/ModelViews';
import { defaultSel as c10Sel, outputsOf as c10Outputs } from './c10/selection';
import { daySeconds } from '../lib/days';

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
});
