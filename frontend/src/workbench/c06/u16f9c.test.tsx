// U16-F9c (fix round 3, the partial R2b review of C06, report c07), on the committed documents: the rungs by their short titles,
// the conversion without the engine's function names, the SICR accounts summarised with their count, the scenario sources and the
// days past due in words, the mean factor as a number, the corner labels whole and S3 and S4 apart.
import { afterEach, describe, expect, it } from 'vitest';
import { textWidth } from '@fasl-work/caos-app-shell';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C06ContextView, CurveReadout, SEVERITY_TONE } from './C06Common';
import { cornerLabelWidth, cornerLines } from './ImpactViews';
import { NonLinearityView, SicrView } from './TermViews';
import { DecileView, LadderView, RungsView } from './ValidationViews';
import { defaultSel, type C06Sel } from './selection';

const sel = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
const table = (markup: string, name: string) => markup.match(new RegExp(String.raw`<table[^>]*data-table="${name}"[\s\S]*?</table>`))?.[0] ?? '';
const rows = (t: string) => [...t.matchAll(/<tbody>([\s\S]*?)<\/tbody>/g)].flatMap((b) => [...b[1].matchAll(/<tr[\s>]/g)]).length;
const RUNG_ID = /\bL[0-2]-(km|dth|cox)\b/;

describe('U16-F9c C06', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    for (const v of variantIds('C06')) {
      it(`ladder, deciles and rungs (${lang}, ${v}): every rung by its short title, never its id`, () => {
        const s = sel(v);
        for (const el of [<LadderView sel={s} />, <DecileView sel={s} />, <RungsView sel={s} />]) {
          const text = textOf(render(el, lang));
          expect(text).not.toMatch(RUNG_ID);
        }
        expect(textOf(render(<RungsView sel={s} />, lang))).toMatch(/L1 (Hazard|Riesgo en tiempo discreto)/);
      });

      it(`ladder (${lang}, ${v}): the conversion names no engine function and wraps as a list of terms`, () => {
        const markup = render(<LadderView sel={sel(v)} />, lang);
        expect(textOf(markup)).not.toMatch(/riskvalidation|implied_z|ttc_to_pit/);
        expect(markup).toMatch(/<dl[^>]*data-table="conversion"/);
      });

      it(`SICR (${lang}, ${v}): the accounts are summarised by stage and trigger, with how many there are`, () => {
        const s = sel(v);
        const markup = render(<SicrView sel={s} />, lang);
        expect(table(markup, 'sicr-points')).toBe('');
        const summary = table(markup, 'sicr-summary');
        expect(rows(summary)).toBeGreaterThan(0);
        expect(rows(summary)).toBeLessThanOrEqual(8);
        const n = s.data.variant.outputs as unknown as { sicr_points: unknown[] };
        expect(textOf(markup)).toContain(lang === 'en' ? `${n.sicr_points.length} sampled accounts` : `${n.sicr_points.length} cuentas muestreadas`);
      });

      it(`context and SICR (${lang}, ${v}): days past due in words, the scenario sources in the reader's language`, () => {
        const s = sel(v);
        const ctx = textOf(render(<C06ContextView sel={s} />, lang));
        const sicr = textOf(render(<SicrView sel={s} />, lang));
        expect(ctx).not.toMatch(/\bdpd\b/);
        expect(sicr).not.toMatch(/\bdpd\b/);
        if (lang === 'es') expect(table(render(<C06ContextView sel={s} />, lang), 'scenario-definitions')).not.toMatch(/shape transposed|midpoint of|Federal Reserve 2026_Final/);
      });

      it(`non-linearity (${lang}, ${v}): the mean factor is a number of the reader's language, not a raw float`, () => {
        const text = textOf(render(<NonLinearityView sel={sel(v)} />, lang));
        expect(text).not.toMatch(/-?\d[.,]\d{5,}/);
      });

      it(`curves read-out (${lang}, ${v}): the segment in words`, () => {
        expect(render(<CurveReadout sel={sel(v)} />, lang)).not.toMatch(/term-(le|gt)-\d+|term-\d+-\d+/);
      });
    }
  }

  it('the findings drawing gives S3 and S4 different colours', () => {
    expect(SEVERITY_TONE.S3).not.toBe(SEVERITY_TONE.S4);
  });

  it('the simplex corner labels fit whole at the widths of the card (no ellipsis)', () => {
    const s = sel('rd-2020-06');
    const o = s.data.variant.outputs as unknown as { scenarios: Array<{ id: string; label: { en: string; es: string } }>; weight_grid: { scenario_ids: string[] } };
    // the two lower corners run outwards from the triangle in the width the drawing leaves them (the top one has the whole width)
    const lower = o.weight_grid.scenario_ids.slice(1).map((id) => o.scenarios.find((x) => x.id === id)!);
    for (const width of [300, 420, 560]) {
      for (const sc of lower) {
        for (const lang of ['en', 'es'] as const) {
          const full = sc.label[lang];
          const lines = cornerLines(full, cornerLabelWidth(width));
          expect(lines.join(' '), `${width} ${full}`).toBe(full);
          expect(lines.length, `${width} ${full}`).toBeLessThanOrEqual(4);
          for (const l of lines) if (l.includes(' ')) expect(textWidth(l, 12), l).toBeLessThanOrEqual(cornerLabelWidth(width));
        }
      }
    }
  });
});
