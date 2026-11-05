// U16-R2b (batch c09): the realised view of a variant that tests one cohort draws its values as points on a range around that year
// (B1: one x value was ranged 0..4,000 and a one-point line drew nothing), with a stated reason for no zoom; the two-bar proxy chart
// states why it has no zoom (M1).
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from './spanish-testkit';
import { RealisedView } from './ModelViews';
import { defaultSel, type C08Sel } from './selection';
import { readFileSync } from 'node:fs';

const captured = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (captured.push(p), mod.UPlotChart(p)) };
});

const TITLE = { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' };

describe('U16-R2b c09: C08', () => {
  afterEach(() => setLang('en'));

  it('B1: a single cohort is drawn as points on a year either side of it, and says why it has no zoom', () => {
    captured.length = 0;
    const sel = defaultSel(committedData('C08', 'dc-2020-23.json', 'models-dc-2020-23.json', TITLE)) as C08Sel;
    view(<RealisedView sel={sel} />);
    const p = captured.at(-1)!;
    expect(p.x.values).toHaveLength(1);
    const year = p.x.values[0];
    expect(p.x.range).toEqual([year - 1, year + 1]);
    for (const s of p.series) expect(s.mode).toBe('points');
    expect(p.zoomOff).toBeDefined();
  });

  it('B1: a variant of several cohorts keeps its lines and its zoom', () => {
    captured.length = 0;
    const sel = defaultSel(committedData('C08', 'dc-2003-06.json', 'models-dc-2003-06.json', TITLE)) as C08Sel;
    view(<RealisedView sel={sel} />);
    const p = captured.at(-1)!;
    if (p.x.values.length > 1) {
      expect(p.x.range).toBeUndefined();
      expect(p.zoomOff).toBeUndefined();
    }
  });

  it('M1: the two-bar proxy chart states why it has no zoom', () => {
    expect(readFileSync(new URL('./SeverityViews.tsx', import.meta.url), 'utf8')).toMatch(/zoomOff=\{\{ en: 'Two totals: there is no range of bars to zoom\./);
  });
});
