// BS-13 (beyond tier): the PLA complement views of C13 rendered from the committed documents. Every number on a view is the
// bake's (the engine's statistics, calibrated on a simulated null); the views name the verdict of the plan's hypothesis whatever
// it is, the lag ladder is the stale-volatility desk only, and the Spanish views carry no English word or raw id.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readFileSync } from 'node:fs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type VariantArtifact } from '../../lib/contract.types';
import { cards, html, setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { ComplementView, LagLadderView } from './ComplementViews';
import { C13_OUTPUTS } from './descriptor';
import { useC13Instrument } from './instrument';
import { defaultSel, outputsOf } from './selection';

type Outputs = components['schemas']['c13Outputs'];

const captured = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return {
    ...mod,
    UPlotChart: (p: UPlotChartProps) => {
      captured.push(p);
      return mod.UPlotChart(p);
    },
  };
});

const title = { en: 'FRTB desk eligibility', es: 'Elegibilidad de mesas FRTB' };
const stale = committedData('C13', 'stale-volatility.json', 'models-generator.json', title);
const none = committedData('C13', 'none.json', 'models-generator.json', title);
const wrong = committedData('C13', 'wrong-correlation.json', 'models-generator.json', title);
const outputs = (d: typeof stale) => outputsOf(defaultSel(d)) as Outputs;
const pct = (v: number, lang: 'en' | 'es' = 'en', d = 1) => formatNumber(v, lang, { percent: true, decimals: d });

describe('the PLA complement in the committed documents', () => {
  afterEach(() => setLang('en'));
  beforeEach(() => {
    captured.length = 0;
  });

  it('every committed deficiency document conforms to the descriptor with the complement member', () => {
    for (const d of [stale, none, wrong]) expect(conform(d.variant.outputs, C13_OUTPUTS)).toEqual([]);
    const file = JSON.parse(readFileSync(new URL('../../../../data/derived/C13/missing-basis.json', import.meta.url), 'utf8')) as VariantArtifact;
    expect(conform(file.outputs, C13_OUTPUTS)).toEqual([]);
  });

  it('the complement view gives the flagged counts, the critical values and the verdict of the hypothesis', () => {
    const o = outputs(stale);
    const c = o.pla_complement!;
    const markup = html(<ComplementView sel={defaultSel(stale)} />);
    expect(cards(markup).length).toBeGreaterThan(0);
    expect(markup).toContain('data-table="c13-complement"');
    expect(markup).toContain(pct(c.flags.family.spearman_roll.rate));
    expect(markup).toContain(pct(c.flags.pla_amber_or_red.rate));
    expect(markup).toContain(`data-verdict="${c.hypothesis!.verdict}"`);
    expect(markup).toContain(formatNumber(c.calibration.thresholds_per_statistic.wald, 'en', { decimals: 2 }));
    expect(markup).toContain('data-synthetic="true"');
    expect(view(<ComplementView sel={defaultSel(stale)} />)).not.toMatch(/NaN|undefined|Infinity|BS-13|spearman_roll|riskvalidation/);
  });

  it('the control reports the false-alarm rate and the planted variants the power; only stale volatility carries a verdict', () => {
    expect(html(<ComplementView sel={defaultSel(none)} />)).toContain('data-role="size"');
    expect(html(<ComplementView sel={defaultSel(none)} />)).not.toContain('data-verdict');
    expect(html(<ComplementView sel={defaultSel(wrong)} />)).toContain('data-role="power"');
    expect(html(<ComplementView sel={defaultSel(wrong)} />)).toContain('data-wald-at-least-ks');
  });

  it('the lag ladder draws the four lags of the stale-volatility desk and the other desks say it is not theirs', () => {
    const c = outputs(stale).pla_complement!;
    captured.length = 0;
    const markup = html(<LagLadderView sel={defaultSel(stale)} />);
    expect(captured).toHaveLength(1);
    expect(captured[0].x.values).toEqual([5, 10, 20, 40]);
    const roll = captured[0].series.find((s) => (s.label as { en: string }).en === 'Lagging scale')!;
    expect(roll.values).toEqual(c.lag_ladder!.map((r) => r.per_statistic.spearman_roll.rate));
    for (const lag of [5, 10, 20, 40]) expect(markup).toContain(`data-lag="${lag}"`);
    expect(markup).toContain('data-table="c13-power-by-size"');
    expect(html(<LagLadderView sel={defaultSel(none)} />)).toContain('data-state="unavailable"');
  });

  it('the Spanish views name the complement in Spanish, with the Spanish number form', () => {
    setLang('es');
    const text = view(<ComplementView sel={defaultSel(stale)} />) + view(<LagLadderView sel={defaultSel(stale)} />);
    expect(text).toContain('complemento de escala y nivel');
    expect(text).toContain(pct(outputs(stale).pla_complement!.flags.family.spearman_roll.rate, 'es').replace(' ', ' '));
    expect(text).not.toMatch(/Lagging|Scale and level|Size of the move|false alarms|Regulatory PLA|spearman_roll|BS-13/);
  });

  it('the PLA group offers the complement and the lag ladder', () => {
    function Tabs() {
      const inst = useC13Instrument(stale, () => undefined);
      return <div>{inst?.groups[0].content}</div>;
    }
    const markup = html(<Tabs />);
    expect(markup).toContain('Complement');
    expect(markup).toContain('Lag ladder');
  });
});
