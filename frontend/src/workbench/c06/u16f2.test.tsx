// U16-F2 (the R2 fix round, C06), on the committed documents: no id of the document in a Spanish sentence or cell, seven distinct cohort
// curves, the simplex scale in a unit with a colour bar, the rung reasons under their rung and the tests of one name told apart.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C06ContextView } from './C06Common';
import { WeightsView } from './ImpactViews';
import { BacktestView, DecileView, IdentitiesView, RungsView, TestsView } from './ValidationViews';
import { defaultSel, type C06Sel } from './selection';

const captured = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (captured.push(p), mod.UPlotChart(p)) };
});

const ids = variantIds('C06');
const selOf = (id: string) => defaultSel(committedData('C06', id)) as C06Sel;
const RAW = ['real-outcomes', 'mid-period', 'stage1', 'transfer-1-2', 'write-off', 'originations', 'macro-update', 'derecognition'];

describe('U16-F2 C06', () => {
  afterEach(() => setLang('en'));

  for (const id of ids.filter((v) => v.startsWith('rd-'))) {
    it(`V06-1: ${id} in Spanish prints words for the truth status, settings, cohorts, stages and movements`, () => {
      const s = selOf(id);
      const es = [
        textOf(render(<C06ContextView sel={s} />, 'es')), textOf(render(<IdentitiesView sel={s} />, 'es')),
        textOf(render(<BacktestView sel={s} />, 'es')), textOf(render(<DecileView sel={s} />, 'es')),
      ].join(' ');
      for (const raw of RAW) expect(es, `${id}: ${raw}`).not.toContain(raw);
      expect(es).toContain('Freddie Mac: falta la cuenta del titular');
      expect(es).not.toContain("Freddie Mac: the owner's account is missing");
      expect(es).toContain('todas');
    });
  }

  it('V06-2: seven cohort curves take seven distinct colours', () => {
    captured.length = 0;
    render(<BacktestView sel={selOf('rd-2019-12')} />, 'en');
    const p = captured.at(-1)!;
    const predicted = p.series.filter((s) => (s.label as { en: string }).en.startsWith('Predicted'));
    expect(predicted.length).toBe(7);
    expect(new Set(predicted.map((s) => s.color)).size).toBe(7);
  });

  it('V06-4: the simplex colour scale carries a unit and a colour bar, not eleven bare digits', () => {
    const markup = render(<WeightsView sel={selOf('rd-2019-12')} />, 'en');
    expect(markup).toContain('data-colour-bar="simplex"');
    const note = textOf(markup).match(/Colour: ([^)]*)\)/)?.[1] ?? '';
    expect(note).toMatch(/bn USD|m USD/);
  });

  it('V06-5: the rung reason sits under its rung, in the language; a test of one name carries its segment', () => {
    const s = selOf('rd-2019-12');
    const es = render(<RungsView sel={s} />, 'es');
    expect(es).toContain('data-reason="rung"');
    expect(textOf(es)).toContain('Kaplan-Meier es una sola curva');
    expect(es).not.toContain('>Nota<');
    const tests = render(<TestsView sel={s} />, 'es');
    expect(tests).not.toMatch(/<th class="ct-text ct-wide-only">Modelo/);
  });
});
