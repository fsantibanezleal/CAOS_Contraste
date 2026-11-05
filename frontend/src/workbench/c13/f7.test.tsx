// U16-F7 (the U16-R2 capture review, batch b06, C13): the minors of the desk views, read on the committed documents.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C13ContextView } from './C13Common';
import { DeskView } from './DeskViews';
import { DetectionView, RanksView } from './PlaViews';
import { defaultSel, levelLabel, parameterText, seedText, type C13Sel } from './selection';

const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => { bars.push(p); return mod.BarChart(p); } };
});

const title = { en: 'FRTB desk eligibility', es: 'Elegibilidad de mesas FRTB' };
const sel = (name = 'missing-basis'): C13Sel => defaultSel(committedData('C13', `${name}.json`, 'models-generator.json', title)) as C13Sel;

describe('U16-F7 C13 (b06 minors)', () => {
  afterEach(() => { setLang('en'); bars.length = 0; });

  it('m6: the Spanish title keeps the noun in lower case after "en la", and the standard error is spelled out', () => {
    expect(levelLabel(0.025, 'es', true)).toBe('cola de 2,5 % (VaR al 97,5 %)');
    expect(levelLabel(0.025, 'es')).toBe('Cola de 2,5 % (VaR al 97,5 %)');
    setLang('es');
    const text = view(<DeskView sel={sel()} />);
    // the 2026-10-27 ruling: back-test is translated (prueba retrospectiva)
    expect(text).toMatch(/Prueba retrospectiva de la mesa en la cola de 2,5 %/);
    expect(text).not.toMatch(/en la Cola/);
    expect(view(<DetectionView sel={sel()} />)).not.toMatch(/EE de Monte Carlo/);
    expect(view(<DetectionView sel={sel()} />)).toMatch(/error estándar de Monte Carlo/);
  });

  it('m7: a seed is written whole and a lag of one day is singular', () => {
    expect(seedText(14000, 'en')).toBe('14000');
    expect(seedText(14892, 'es')).toBe('14892');
    expect(parameterText({ name: 'lag_days', value: 1, unit: 'days' }, 'en', 3)).toBe('lag 1 day');
    expect(parameterText({ name: 'lag_days', value: 1, unit: 'days' }, 'es', 3)).toBe('rezago 1 día');
    expect(parameterText({ name: 'lag_days', value: 20, unit: 'days' }, 'en', 3)).toBe('lag 20 days');
    // R5 c18 m9: a correlation's value does not repeat its name's word
    expect(parameterText({ name: 'factor_correlation', value: 0.6, unit: 'correlation' }, 'en', 3)).toBe('factor correlation 0.6');
    expect(parameterText({ name: 'factor_correlation', value: 0.6, unit: 'correlation' }, 'es', 3)).toBe('correlación entre factores 0,6');
    expect(parameterText({ name: 'correlation_error', value: 0.3, unit: 'correlation-points' }, 'en', 3)).toBe('correlation error 0.3 points');
    const ctx = view(<C13ContextView sel={sel()} />);
    expect(ctx).toMatch(/seed 14000 plus the index/);
    expect(ctx).not.toMatch(/14,000 plus/);
    expect(view(<RanksView sel={sel()} />)).not.toMatch(/seed \d,\d{3}/);
  });

  it('m9: the desk bars count whole exceptions (no "7.0") and the mean is in the table', () => {
    const text = view(<DeskView sel={sel()} />);
    const b = bars.find((x) => /Exceptions in 250 days/.test((x.title as { en: string }).en))!;
    expect(b.axis.format).toEqual({ decimals: 0 });
    const doc = committed<{ outputs: { desk_backtest: Array<{ alpha: number; exceptions: { mean: number } }> } }>('C13', 'missing-basis.json');
    const mean = doc.outputs.desk_backtest[0].exceptions.mean;
    expect(text).toContain(String(Math.round(mean * 10) / 10));
    expect(text).toMatch(/Mean/);
  });
});
