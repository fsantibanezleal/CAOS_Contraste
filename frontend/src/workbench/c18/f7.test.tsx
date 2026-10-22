// U16-F7 (the U16-R2 capture review, batch b09, C18): the minors of the stress views, read on the committed documents.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C18Sel } from './selection';
import { FanView, requirementDecimals } from './CapitalViews';
import { useC18Instrument } from './instrument';
import { BackcastView, PathsView, SatellitesView } from './StressViews';

const charts = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => { charts.push(p); return mod.UPlotChart(p); } };
});

const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const data = (name: string) => fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title);
const selOf = (name: string): C18Sel => defaultSel(data(name)) as C18Sel;
const chartOf = (el: ReactElement) => { charts.length = 0; html(el); return [...charts]; };

function Groups({ name }: { name: string }) {
  const inst = useC18Instrument(data(name), () => undefined);
  return <div>{inst ? inst.groups.map((g) => g.content) : 'none'}</div>;
}

describe('U16-F7 C18 (b09 minors)', () => {
  afterEach(() => { setLang('en'); charts.length = 0; });

  it('m2: with no mitigation to apply the key says the two stress lines are the same line', () => {
    const doc = committedDoc<VariantArtifact>('C18', 'fed-2026-severely-adverse') as any;
    expect(doc.outputs.capital_plan.mitigation.applies).toBe(false);
    const [fan] = chartOf(<FanView sel={selOf('fed-2026-severely-adverse')} />);
    const labels = fan.series.map((s) => (s.label as { en: string }).en);
    expect(labels).toContain('Stress, with mitigation (identical: no mitigation applies)');
    setLang('es');
    const [fanEs] = chartOf(<FanView sel={selOf('fed-2026-severely-adverse')} />);
    expect(fanEs.series.map((s) => (s.label as { es: string }).es)).toContain('Estrés con mitigación (idéntico: no se aplica mitigación)');
  });

  it('m3: the requirement of the fan table has two decimals like the other cells, a third only where the legal figure needs it', () => {
    expect(requirementDecimals(0.145)).toBe(2);
    expect(requirementDecimals(0.09625)).toBe(3);
    const text = visibleText(html(<FanView sel={selOf('fed-2026-severely-adverse')} />));
    expect(text).toMatch(/14\.50 %/);
    expect(text).not.toMatch(/14\.500 %/);
    expect(text).toMatch(/9\.625 %/);
  });

  it('m5: the Spanish back-cast is a retrospective test, in the tab, the title and the unavailable reason', () => {
    setLang('es');
    const tabs = visibleText(html(<Groups name="fed-2026-severely-adverse" />));
    expect(tabs).toContain('Retrospectiva');
    expect(tabs).not.toMatch(/Back-cast/);
    expect(visibleText(html(<BackcastView sel={selOf('fed-2026-severely-adverse')} />))).toContain('La prueba retrospectiva frente a las tasas realizadas');
    expect(visibleText(html(<BackcastView sel={selOf('fed-2026-severely-adverse')} />))).not.toMatch(/back-cast/i);
  });

  it('m8: the five loan types of the satellite chart have five distinct colours', () => {
    const [chart] = chartOf(<SatellitesView sel={selOf('fed-2026-severely-adverse')} />);
    const colours = chart.series.map((s) => s.color);
    expect(colours).toHaveLength(5);
    expect(new Set(colours).size).toBe(5);
    expect(colours.every((c) => typeof c === 'string')).toBe(true);
  });

  it('m11: the US-calibrated adaptation is said once in the paths note, and the Spanish note has no double full stop', () => {
    const en = visibleText(html(<PathsView sel={selOf('fed-2026-severely-adverse')} />));
    expect((en.match(/US-calibrated adaptation/g) ?? []).length).toBe(1);
    setLang('es');
    const es = visibleText(html(<PathsView sel={selOf('fed-2026-severely-adverse')} />));
    expect(es).not.toMatch(/UU\.\./);
    expect((es.match(/adaptación calibrada en EE\. UU\./g) ?? []).length).toBeLessThanOrEqual(1);
  });
});
