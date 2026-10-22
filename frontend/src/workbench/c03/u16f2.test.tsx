// U16-F2 (the R2 fix round, C03), on the committed documents: the champion of the cohorts table, the Spanish scope and rationale,
// the year axes written as years, and the label of the one ladder the models artifact fits.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { C03VariantsTable } from './C03Common';
import { CalibrationView, TrainingView } from './ModelViews';
import { defaultSel, rungLabel, type C03Outputs, type C03Sel } from './selection';
import { ENGLISH_NUMBER, committedData, render, textOf, variantIds } from './u16f2-kit';
import { setLang } from './u6-testkit';
import type { VariantArtifact } from '../../lib/contract.types';

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

const ids = variantIds('C03');
const selOf = (id: string) => defaultSel(committedData('C03', id)) as C03Sel;
const outOf = (s: C03Sel) => (s.data.variant as unknown as VariantArtifact<C03Outputs>).outputs;

describe('U16-F2 C03', () => {
  afterEach(() => setLang('en'));

  it('V03-1: the cohorts table and chart read the champion, never the constant rung that opens the comparison', () => {
    const variants = ids.map((id) => {
      const v = committedData('C03', id).variant as unknown as VariantArtifact<C03Outputs>;
      return { id, title: { en: id, es: id }, v };
    });
    const first = variants[0].v.outputs;
    expect(first.rung_comparison[0].rung_id).not.toBe(first.calibration.rung_id);      // the premise: the comparison opens on the constant
    const markup = render(<C03VariantsTable variants={variants} onPick={() => undefined} current={ids[0]} label={(id) => rungLabel(selOf(ids[0]), id)} />, 'en');
    for (const { v } of variants) {
      const champion = v.outputs.rung_comparison.find((r) => r.rung_id === v.outputs.calibration.rung_id)!;
      expect(champion.auc).not.toBeNull();
      expect(markup).toContain(formatNumber(champion.auc, 'en', { digits: 3 }));
    }
    expect(markup).toContain('WoE scorecard');
    expect(markup).not.toContain('Constant (base rate)');
  });

  for (const id of ids) {
    it(`PR-C03 and V03-2: ${id} in Spanish prints a Spanish scope and a rationale with Spanish numbers`, () => {
      const s = selOf(id);
      const calibration = textOf(render(<CalibrationView sel={s} />, 'es'));
      expect(calibration).toContain(outOf(s).calibration.scope.es);
      expect(calibration).not.toContain('vintages with');
      const training = textOf(render(<TrainingView sel={s} />, 'es'));
      expect(training).toContain(outOf(s).training.rationale.es);
      expect(outOf(s).training.rationale.es).not.toMatch(ENGLISH_NUMBER); // the coefficients table (Spanish decimals such as 0,075) is not an English thousands form
    });
  }

  it('V03-3: both year axes of the training windows are calendar years, written without a group separator', () => {
    captured.length = 0;
    render(<TrainingView sel={selOf(ids[0])} />, 'es');
    const p = captured.at(-1)!;
    expect(p.x.format).toEqual({ decimals: 0, grouping: false });
    expect(p.y.format).toEqual({ decimals: 0, grouping: false });
  });

  it('V03-4: the one ladder of the models artifact is labelled with the window it was fitted for, under every cohort', () => {
    const early = textOf(render(<TrainingView sel={{ ...selOf(ids[1]), rung: 'P1-scorecard' }} />, 'en'));
    expect(early).toContain('Rungs as fitted for the window of the cohort');
    expect(early).toContain('cut-off 2017-09-30');
    expect(early).toContain('not for the window of this cohort');
    const es = textOf(render(<TrainingView sel={{ ...selOf(ids[1]), rung: 'P1-scorecard' }} />, 'es'));
    expect(es).toContain('Peldaños tal como se ajustaron para la ventana de la cohorte');
    expect(es).toContain('no para la ventana de esta cohorte');
    const last = textOf(render(<TrainingView sel={{ ...selOf(ids[ids.length - 1]), rung: 'P1-scorecard' }} />, 'en'));
    expect(last).not.toContain('not for the window of this cohort');
  });
});
