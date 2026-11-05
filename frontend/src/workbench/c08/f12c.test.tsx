// U16-F12c (R4 batch c10, C08): the Downturn chart keeps a band above its data for its mark labels, so at 390 the labels no longer
// hide the downturn line and the uncovered cohort's point (MJ1); with the minors of the batch fixed in the view: fixed decimals on the
// RMSE bars and the rail read-out (m1), two decimals in the readouts of the percent charts (n2), a taller parity chart (m10), the
// cohort period kept whole in a table cell (n1) and a rail model name that fits (n4). Reads the committed documents, in both languages.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData } from './spanish-testkit';
import { useC08Instrument } from './instrument';
import { DownturnView } from './DownturnViews';
import { CalibrationView, RealisedView, RungsView } from './ModelViews';
import { RungReadout } from './C08Common';
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

function Rail({ sel, at }: { sel: C08Sel; at: number }) {
  const inst = useC08Instrument(sel.data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}

describe('U16-F12c, C08 (R4 c10)', () => {
  afterEach(() => setLang('en'));

  it('MJ1: the Downturn y axis leaves a band above the data for its mark labels (a row of about an eighth of the plot per label)', () => {
    for (const c of COHORTS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        lines.length = 0;
        html(<DownturnView sel={selOf(c)} />);
        const p = lines.at(-1)!;
        const values = p.series.flatMap((s) => s.values).filter((v): v is number => v !== null);
        const range = p.y.range;
        expect(range, c).toBeDefined();
        const [lo, hi] = range!;
        expect(lo, c).toBeLessThanOrEqual(Math.min(...values));
        const free = (hi - Math.max(...values)) / (hi - lo);
        expect(free, c).toBeGreaterThanOrEqual(0.12 * (p.marks ?? []).length);
      }
    }
  });

  it('n2: the Downturn, Realised and Calibration charts read their percents with two decimals (82.06 % against 82.21 %)', () => {
    const sel = selOf('dc-2009-10');
    lines.length = 0;
    html(<DownturnView sel={sel} />);
    html(<RealisedView sel={sel} />);
    html(<CalibrationView sel={sel} />);
    expect(lines).toHaveLength(3);
    for (const p of lines) expect(p.y.format).toEqual({ percent: true, decimals: 2 });
    expect(lines[2].x.format).toEqual({ percent: true, decimals: 2 });
  });

  it('m1: the RMSE bars and the rail read-out print three fixed decimals, as the tables do (0.300 beside 0.297, never 0.3)', () => {
    bars.length = 0;
    const sel = selOf('dc-2003-06');
    html(<RungsView sel={sel} />);
    expect(bars.at(-1)!.axis.format).toEqual({ decimals: 3 });
    const s = selOf('dc-2014-19');
    const r = outputsOf(s)!.rung_comparison.find((x) => x.rung_id === s.rung)!;
    const markup = html(<RungReadout sel={s} />);
    expect(markup).toContain(formatNumber(r.r2 as number, 'en', { decimals: 3 }));
    expect(markup).toContain(formatNumber(r.rmse as number, 'en', { decimals: 3 }));
    expect(markup).toContain(formatNumber(r.spearman as number, 'en', { decimals: 3 }));
  });

  it('m10: the calibration parity chart takes at least 22 rem of its card', () => {
    const markup = html(<CalibrationView sel={selOf('dc-2009-10')} />);
    expect(markup).toContain('--ct-chart-min:22rem');
  });

  it('n1: a cohort period stays whole in the realised and downturn tables (never "Defaults 2009-" over "10")', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf('dc-2009-10');
      for (const markup of [html(<RealisedView sel={sel} />), html(<DownturnView sel={sel} />)]) {
        expect(markup).toMatch(/<span style="white-space:nowrap">2009-10<\/span>/);
      }
    }
  });

  it('n4: the rail model select names every model whole in Spanish (no ellipsis), with the full name as its hint', () => {
    setLang('es');
    const es = html(<Rail sel={selOf('dc-2009-10')} at={0} />);
    const opts = [...es.matchAll(/<option[^>]*>([^<]*)<\/option>/g)].map((x) => x[1]);
    expect(opts.length).toBeGreaterThan(0);
    for (const o of opts) expect(o).not.toContain('…');
    expect(opts).toContain('Árboles potenciados');
    expect(es).toContain('Árboles potenciados por gradiente');
  });
});
