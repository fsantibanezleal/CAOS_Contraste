// Release 1.00.001 on shell 0.26.0: the full gate's G20 keyboard check starts at Home (the readout of the first point) and then presses
// ArrowRight; it fails when the readout does not change. Three charts failed it, each for a cause of its own, and each test here runs the
// rule on the committed documents the gate walks, never on a fixture:
//  - the EBM shape functions drew the first bin 1e-9 left of the first cut, so the first two points shared an x at any display precision;
//  - the C04 capital chart and the C11 Z2 chart are point charts padded with an empty first point, and the shell's pointer-less cursor of a
//    point chart snaps to the nearest point that has a value: Home and ArrowRight both read the same one.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { EbmExport, ModelsArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { committedData, render, textOf, variantIds, type Lang } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { CapitalView as C04CapitalView } from './c04/LiveViews';
import { makeSel } from './c04/selection';
import { EsBacktestView } from './c11/BacktestViews';
import { defaultSel as c11Default, outputsOf as c11Outputs } from './c11/selection';
import { defaultChallenger } from './model';
import { EbmView, ebmShapes } from './ModelViews';
import { StabilityView } from './ValidationViews';

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
beforeEach(() => {
  captured.length = 0;
});
afterEach(() => setLang('en'));

const LANGS: Lang[] = ['en', 'es'];
const derived = new URL('../../../data/derived/', import.meta.url);

/** The charts a view drew, in order. */
function charts(el: Parameters<typeof render>[0], lang: Lang = 'en'): UPlotChartProps[] {
  captured.length = 0;
  render(el, lang);
  return [...captured];
}

/** The gate's keyboard walk, from a chart's props: a point chart snaps the cursor to the nearest point that holds a value, so the
 * first two points must both hold one, and sit at different x; the readout then differs (x or value). */
function firstTwoReadable(p: UPlotChartProps): string | null {
  const filled = (i: number) => p.series.some((s) => s.values[i] !== null && s.values[i] !== undefined);
  if (p.x.values.length < 2) return null;
  if (!filled(0)) return 'the first point holds no value';
  if (!filled(1)) return 'the second point holds no value';
  if (!(p.x.values[1] > p.x.values[0])) return 'the first two x are not increasing';
  return null;
}

describe('G20: the EBM shape functions draw the first bin one bin width left of the first cut', () => {
  // every committed models document that carries the EBM
  const documents: Array<{ file: string; models: ModelsArtifact }> = [];
  for (const dir of readdirSync(derived, { withFileTypes: true })) {
    if (!dir.isDirectory()) continue;
    for (const f of readdirSync(new URL(`${dir.name}/`, derived))) {
      if (!/^models-.*\.json$/.test(f)) continue;
      const models = JSON.parse(readFileSync(join(fileURLToPath(derived), dir.name, f), 'utf8')) as ModelsArtifact;
      if (models.model.some((m) => m.id === 'P3-ebm')) documents.push({ file: `${dir.name}/${f}`, models });
    }
  }
  it('reads at least the C01 documents', () => {
    expect(documents.length).toBeGreaterThanOrEqual(3);
  });
  it('the first two x of every continuous shape differ by a bin width (the width of the second bin, or a stated share of the cut)', () => {
    for (const { file, models } of documents) {
      const ex = (models.model.find((m) => m.id === 'P3-ebm')!.details as { export: EbmExport }).export;
      for (const s of ebmShapes(ex, models.fit as never, 'continuous')) {
        const where = `${file} ${s.name}`;
        expect(s.x.length, where).toBe(s.y.length);
        const first = s.x[1] - s.x[0];
        expect(first, where).toBeGreaterThan(0);
        // at the display precision of the readout (four significant digits) the two x are different numbers
        expect(Number(s.x[0].toPrecision(4)), where).not.toBe(Number(s.x[1].toPrecision(4)));
        if (s.x.length >= 3) expect(first, where).toBeCloseTo(s.x[2] - s.x[1], 9);
      }
    }
  });
  it('a term with one cut draws its first bin a stated share of the cut to the left, never on the cut', () => {
    const one = documents.flatMap(({ file, models }) => {
      const ex = (models.model.find((m) => m.id === 'P3-ebm')!.details as { export: EbmExport }).export;
      return ebmShapes(ex, models.fit as never, 'continuous').filter((s) => s.x.length === 2).map((s) => ({ file, s }));
    });
    // the committed documents hold such terms on the categorical side only; the rule is run on a synthetic term as well
    const ex = {
      features: [{ name: 'flag', levels: [{ kind: 'continuous', cuts: [0.5] }] }],
      terms: [{ name: 'flag', features: [0], scores: [0, -0.4, 0.7] }],
    } as unknown as EbmExport;
    const [s] = ebmShapes(ex, undefined, 'continuous');
    expect(s.x).toHaveLength(2);
    expect(s.x[0]).toBeLessThan(0.5);
    expect(0.5 - s.x[0]).toBeCloseTo(0.05, 9);
    expect(s.y).toEqual([-0.4, 0.7]);
    for (const { file, s: t } of one) expect(t.x[1] - t.x[0], file).toBeGreaterThan(0);
  });
  it('the card says where the first bin is drawn, in both languages', () => {
    const data = committedData('C01', variantIds('C01')[0]);
    const sel = { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
    const en = textOf(render(<EbmView sel={sel} />, 'en'));
    const es = textOf(render(<EbmView sel={sel} />, 'es'));
    expect(en).toMatch(/first bin, every value below the first cut, is drawn one bin width to the left of the first cut/);
    expect(es).toMatch(/primer tramo, todo valor bajo el primer corte, se dibuja un ancho de tramo a la izquierda del primer corte/);
  });
  it('the chart of every C01 variant has readable first two points', () => {
    for (const v of variantIds('C01')) {
      const data = committedData('C01', v);
      const sel = { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
      for (const lang of LANGS) for (const p of charts(<EbmView sel={sel} />, lang)) expect(firstTwoReadable(p), `${v} ${lang}`).toBeNull();
    }
  });
});

describe('G20: the C04 capital chart has data at its first two points and room by its range, not by an empty first point', () => {
  for (const v of variantIds('C04')) {
    it(`${v}: the point chart's first two x each hold a value, and the half-step room is the axis range`, () => {
      const data = committedData('C04', v);
      for (const lang of LANGS) {
        const [chart] = charts(<C04CapitalView sel={makeSel(data)} />, lang);
        if (!chart) continue; // a variant with no capital chart draws its reason table
        const scatter = chart.series.every((s) => s.mode === 'points');
        if (!scatter) continue;
        expect(firstTwoReadable(chart), `${v} ${lang}`).toBeNull();
        // the points sit at 1..n, with half a step of room on each side given to the axis
        const n = chart.x.values.length;
        expect(chart.x.values, `${v} ${lang}`).toEqual(Array.from({ length: n }, (_, i) => i + 1));
        expect(chart.x.range, `${v} ${lang}`).toEqual([0.5, n + 0.5]);
      }
    });
  }
});

describe('G20: the C11 Z2 chart has data at its first two points and every mark inside its axis', () => {
  for (const v of variantIds('C11')) {
    it(`${v}: every model's back-test chart`, () => {
      const data = committedData('C11', v);
      const base = c11Default(data)!;
      const o = c11Outputs({ data })!;
      let seen = 0;
      for (const es of o.es_backtests) {
        for (const lang of LANGS) {
          const [chart] = charts(<EsBacktestView sel={{ ...base, model: es.model_id, alpha: es.alpha as never }} />, lang);
          expect(chart, `${v} ${es.model_id} ${es.alpha}`).toBeDefined();
          expect(firstTwoReadable(chart), `${v} ${es.model_id} ${es.alpha} ${lang}`).toBeNull();
          // the two readouts differ at the x format of the chart
          const dec = (chart.x.format as { decimals?: number } | undefined)?.decimals ?? 4;
          expect(formatNumber(chart.x.values[1], lang, { decimals: dec }), `${v} ${es.model_id} ${es.alpha} ${lang}`).not.toBe(
            formatNumber(chart.x.values[0], lang, { decimals: dec }),
          );
          // every mark is inside the axis: the values or the range reach it
          const lo = Math.min(chart.x.values[0], ...(chart.x.range ?? [Infinity]));
          const hi = Math.max(chart.x.values.at(-1)!, ...(chart.x.range ?? [-Infinity]));
          for (const m of chart.marks ?? []) {
            expect(m.x, `${v} ${es.model_id} ${es.alpha} mark`).toBeGreaterThanOrEqual(lo);
            expect(m.x, `${v} ${es.model_id} ${es.alpha} mark`).toBeLessThanOrEqual(hi);
          }
          seen += 1;
        }
      }
      expect(seen).toBeGreaterThanOrEqual(0);
    });
  }
});

describe('G6: the stability view leaves its input table room at a wide font (the drawn share of the viewport)', () => {
  it('the PSI table names the segment on the line of the rung, so seven rows do not take two lines each', () => {
    const data = committedData('C01', variantIds('C01')[0]);
    const sel = { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
    for (const lang of LANGS) {
      const markup = render(<StabilityView sel={sel} />, lang);
      const rows = markup.match(/<span class="ct-row-detail ct-row-detail-inline"/g) ?? [];
      expect(rows.length, lang).toBeGreaterThanOrEqual(5);
      expect(markup, lang).not.toMatch(/<span class="ct-row-detail" data-segment/);
    }
  });
});
