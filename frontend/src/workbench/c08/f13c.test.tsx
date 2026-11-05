// U16-F13c (R5 batch c11, C08): every row of the tests table names its segment, a row its document gives none naming the whole
// portfolio (M1, R5 ruling 2: the "LGD calibration over time" rows showed none); with the minors of the batch fixed in the view: the
// Endpoints axis and readout with two decimals (n4), the parity chart's x axis ticked at whole percents while its readout keeps two
// decimals (n5), the shortfall in points, as the finding says it (n6), and one precision for a floor's binding share in the bar and the
// table (n7). Reads the committed documents, in both languages.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { formatNumber, type BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData, view } from './spanish-testkit';
import { WHOLE_PORTFOLIO } from './words';
import { DownturnView, FloorsView } from './DownturnViews';
import { CalibrationView, EndpointsView, RungsView } from './ModelViews';
import { defaultSel, outputsOf, type C08Sel } from './selection';

const lines = vi.hoisted(() => [] as UPlotChartProps[]);
const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});

const TITLE = { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' };
const COHORTS = ['dc-2003-06', 'dc-2007-08', 'dc-2009-10', 'dc-2011-13', 'dc-2014-19', 'dc-2020-23'];
const selOf = (c: string) => defaultSel(committedData('C08', `${c}.json`, `models-${c}.json`, TITLE)) as C08Sel;
const rowsOf = (markup: string, test?: string) =>
  [...markup.matchAll(/<tr [^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].filter((m) => !test || m[1] === test).map((m) => m[2]);

describe('U16-F13c, C08 (R5 c11)', () => {
  afterEach(() => setLang('en'));

  it('M1: every tests row names its segment; the over-time rows, which the document gives none, name the whole portfolio', () => {
    for (const c of COHORTS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const words = WHOLE_PORTFOLIO[lang];
        const markup = html(<RungsView sel={selOf(c)} />);
        const rows = rowsOf(markup);
        expect(rows.length, c).toBeGreaterThan(0);
        for (const r of rows) expect(r, `${c} ${lang}`).toContain('ct-row-detail');
        const over = rowsOf(markup, 'lgd_ead.lgd_calibration_over_time');
        expect(over.length, c).toBeGreaterThan(0);
        for (const r of over) expect(r.replace(/<[^>]*>/g, ' '), `${c} ${lang}`).toContain(words);
      }
    }
  });

  it('n4: the Endpoints axis and its readout print two decimals, as the table does (78.44 %, never 78.4 %)', () => {
    lines.length = 0;
    html(<EndpointsView sel={selOf('dc-2009-10')} />);
    expect(lines.at(-1)!.y.format).toEqual({ percent: true, decimals: 2 });
  });

  it('n5: the parity chart ticks its x axis at whole percents, at most six ticks, and its readout keeps two decimals', () => {
    for (const c of COHORTS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        lines.length = 0;
        html(<CalibrationView sel={selOf(c)} />);
        const p = lines.at(-1)!;
        expect(p.x.format, c).toEqual({ percent: true, decimals: 2 });
        const ticks = p.x.ticks ?? [];
        const xs = p.x.values.filter((v): v is number => v !== null);
        const inside = ticks.filter((t) => t.value >= Math.min(...xs) - 1e-9 && t.value <= Math.max(...xs) + 1e-9);
        expect(ticks.length, c).toBeLessThanOrEqual(8);
        // at least two labelled ticks over the points, so the scale reads without a hover
        expect(inside.length, c).toBeGreaterThanOrEqual(2);
        for (const t of ticks) expect(pick(t.label, lang), c).toMatch(/^\d+ %$/);
      }
    }
  });

  it('n6: the downturn shortfall is a difference of LGDs in points, in the mark and the table (0.14 points, never 0.14 %)', () => {
    const sel = selOf('dc-2009-10');
    const short = outputsOf(sel)!.downturn.rows.find((r) => !r.covered)!.shortfall;
    expect(short).toBeGreaterThan(0);
    for (const [lang, unit, value] of [['en', 'points', '0.14'], ['es', 'puntos', '0,14']] as const) {
      expect(formatNumber(short * 100, lang, { decimals: 2 })).toBe(value);
      setLang(lang);
      lines.length = 0;
      const text = view(<DownturnView sel={sel} />);
      const marks = (lines.at(-1)!.marks ?? []).map((m) => (typeof m.label === 'string' ? m.label : m.label?.[lang] ?? ''));
      expect(marks.some((m) => m.includes(`${value} ${unit}`)), marks.join(' | ')).toBe(true);
      expect(marks.join(' ')).not.toMatch(/\d %$/);
      expect(text).toContain(lang === 'en' ? 'Shortfall (points)' : 'Faltante (puntos)');
    }
  });

  it('n7: a floor\'s binding share has one precision in the bar and in the table (0.01 %, never 0.006 % beside it)', () => {
    bars.length = 0;
    html(<FloorsView sel={selOf('dc-2014-19')} />);
    expect(bars.at(-1)!.axis.format).toEqual({ percent: true, decimals: 2 });
  });
});

const pick = (t: string | { en: string; es: string }, lang: 'en' | 'es') => (typeof t === 'string' ? t : t[lang]);
