// What the Impact views and the published views DRAW, checked against the engine's ports and the artifacts, never
// against the views' own helpers: the markup tests count series and read notes, so a chart that draws wrong numbers
// (a rate doubled, a bound swapped, a path drawn for another portfolio) would pass them. Every chart's props are
// captured as the shell receives them.
import { readFileSync } from 'node:fs';
import { useLangStore } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { pdAgrestiCoull, pdJeffreys, pdWald, portfolioRiskWeight, project } from '../../engine/transitions';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { CapitalView, DriftView, IntervalsView } from './LiveViews';
import { PapersView, PublishedImpactView, RHO_GRID } from './PublishedViews';
import { GRADES, makeSel, type AgencyVariant, type C04Sel, type FamilyVariant, type StartPortfolio } from './selection';

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

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const byId = (id: string): CaseData => {
  const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === id)!;
  return { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
};
const agencyOf = (d: CaseData) => d.variant as unknown as AgencyVariant;
const familyOf = (d: CaseData) => d.variant as unknown as FamilyVariant;

/** Render on the server (language English) and return the props of every chart drawn, in order. */
function drawn(el: ReactElement): UPlotChartProps[] {
  captured.length = 0;
  const initial = useLangStore.getInitialState();
  const before = initial.lang;
  initial.lang = 'en';
  try {
    renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    initial.lang = before;
  }
  return [...captured];
}
const label = (s: { label: unknown }) => (typeof s.label === 'string' ? s.label : (s.label as { en: string }).en);
const series = (p: UPlotChartProps, name: string) => {
  const s = p.series.find((x) => label(x) === name || label(x).startsWith(`${name} `));
  if (!s) throw new Error(`no series "${name}" among ${p.series.map(label).join(' | ')}`);
  return s.values;
};
/** A categorical series drawn with half a step of room at each end: the values at the positions 1 to n. */
const inner = (values: readonly (number | null)[]) => values.slice(1, -1);
/** What a log axis can draw: positive and finite, else a gap. */
const onLog = (x: number) => (Number.isFinite(x) && x > 0 ? x : null);
const close = (got: readonly (number | null)[], want: readonly (number | null)[], what: string) => {
  expect(got.length, what).toBe(want.length);
  got.forEach((x, i) => {
    if (want[i] === null) expect(x, `${what} [${i}]`).toBeNull();
    else expect(x as number, `${what} [${i}]`).toBeCloseTo(want[i] as number, 12);
  });
};

/** The starting portfolios over the eight states, built here from their definitions (selection.START_LABEL). */
function start(kind: StartPortfolio, origination: readonly number[]): number[] {
  if (kind === 'origination') return [...origination];
  if (kind === 'best') return [1, 0, 0, 0, 0, 0, 0, 0];
  if (kind === 'uniform') return [...GRADES.map(() => 1 / 7), 0];
  return [0, 0, 0, 0, 1 / 3, 1 / 3, 1 / 3, 0];
}

describe('what the C04 live views draw', () => {
  it("Drift: the projected default rate and the TTC rate are Engelmann's propagation of the start, for every start and horizon", () => {
    for (const id of ['sp', 'fitch', 'markov']) {
      const d = byId(id);
      const v = d.variant as VariantArtifact<unknown>;
      const chain = id === 'markov' ? familyOf(d).outputs.generator : null;
      const matrix = chain ? chain.one_year_matrix : agencyOf(d).outputs.pooled.matrix;
      const total = chain ? chain.obligors.reduce((a, b) => a + b, 0) : 1;
      const origination = chain ? [...chain.obligors.map((n) => n / total), 0] : agencyOf(d).outputs.origination;
      for (const kind of ['origination', 'best', 'uniform', 'speculative'] as const) {
        for (const horizon of [5, 20]) {
          const p = project(matrix, start(kind, origination), origination, horizon);
          const [rate, mix] = drawn(<DriftView sel={makeSel(d, { start: kind, horizon })} />);
          const what = `${v.variant_id} ${kind} ${horizon}`;
          close(inner(series(rate, 'Projected')), p.defaultRate, `${what} projected`);
          close(inner(series(rate, 'TTC rate')), p.defaultRate.map(() => p.ttc.defaultRate), `${what} TTC`);
          // the composition: grade k's share of the balance at every date
          GRADES.forEach((g, k) => close(mix.series[k].values, p.portfolio.map((w) => w[k]), `${what} ${g}'s share`));
        }
      }
    }
  });

  it("Drift on Moody's: the composition alone, the matrix's propagation of the start without defaults", () => {
    const d = byId('moodys');
    const o = agencyOf(d).outputs;
    for (const kind of ['origination', 'best', 'speculative'] as const) {
      const p = project(o.pooled.matrix, start(kind, o.origination), o.origination, 20);
      const charts = drawn(<DriftView sel={makeSel(d, { start: kind, horizon: 20 })} />);
      expect(charts).toHaveLength(1);
      GRADES.forEach((g, k) => close(charts[0].series[k].values, p.portfolio.map((w) => w[k]), `moodys ${kind} ${g}`));
    }
  });

  it("Intervals: every bound is the port's at the rail's level and correlation on the definition's pooled counts, D / N the observed rate", () => {
    const d = byId('sp');
    const o = agencyOf(d).outputs;
    for (const [level, rho] of [
      [0.95, 0],
      [0.9, 0.01],
      [0.99, 0.03],
    ] as const) {
      for (const def of ['d2', 'd4'] as const) {
        const l = o.lra[def]!;
        const [chart, widths] = drawn(<IntervalsView sel={makeSel(d, { level, rho, definition: def, grade: 6 })} />);
        const at = (f: (g: number) => number) => GRADES.map((_, g) => onLog(f(g)));
        const what = `${def} ${level} ${rho}`;
        close(inner(series(chart, 'Wald, upper')), at((g) => pdWald(l.defaults[g], l.n[g], { level, rho }).upper), `${what} Wald upper`);
        close(inner(series(chart, 'Agresti-Coull, lower')), at((g) => pdAgrestiCoull(l.defaults[g], l.n[g], { level, rho }).lower), `${what} AC lower`);
        close(inner(series(chart, 'Jeffreys, upper')), at((g) => pdJeffreys(l.defaults[g], l.n[g], { level }).upper), `${what} Jeffreys upper`);
        close(inner(series(chart, 'Observed D / N')), at((g) => l.defaults[g] / l.n[g]), `${what} observed`);
        // the tall screen's widths of CCC-C along the correlation, at the rail's level
        close(series(widths, 'Wald width'), RHO_GRID.map((r) => onLog(pdWald(l.defaults[6], l.n[6], { level, rho: r }).length)), `${what} Wald width`);
        close(series(widths, 'Jeffreys width, no correlation'), RHO_GRID.map(() => onLog(pdJeffreys(l.defaults[6], l.n[6], { level }).length)), `${what} Jeffreys width`);
      }
    }
  });

  it("Capital: each point is the portfolio's IRB risk weight under its row's PDs, and the chosen grade's own beside it", () => {
    const d = byId('sp');
    const o = agencyOf(d).outputs;
    const keep = GRADES.map((_, g) => {
      const xs = (o.pd.keep ?? []).map((row) => row[g]).filter((x): x is number => x !== null);
      return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
    });
    const rows: Array<(number | null)[]> = [o.lra.d2.rate, o.lra.d3.rate, o.lra.d4!.rate, keep, o.generators.em.pd_1y, o.generators.diagonal!.pd_1y, o.generators.weighted!.pd_1y, o.generators.jlt!.pd_1y];
    for (const [lgd, grade] of [
      [0.45, 6],
      [0.25, 3],
    ] as const) {
      const irb = { assetClass: 'corporate' as const, lgd, maturity: o.irb.maturity, regime: 'basel3' as const };
      const results = rows.map((pds) => portfolioRiskWeight(pds as (number | null)[], o.origination.slice(0, 7), irb));
      const [chart, byGrade] = drawn(<CapitalView sel={makeSel(d, { lgd, grade })} />);
      results.forEach((r, i) => expect(inner(chart.series[i].values)[i] as number, `point ${i + 1}`).toBeCloseTo(r.average as number, 12));
      close(inner(chart.series[results.length].values), results.map((r) => onLog(r.riskWeights[grade] as number)), `grade ${grade}'s own`);
      results.forEach((r, i) => close(inner(byGrade.series[i].values), r.riskWeights.map((w) => onLog(w as number)), `row ${i + 1} by grade`));
    }
  });
});

describe('what the C04 published views draw', () => {
  const d = byId('published');
  const o = (d.variant as VariantArtifact<unknown>).outputs as unknown as {
    sr190: { defaults: number; n: number; rows: Array<{ interval: string; rho: number; printed: number[] }> };
    engelmann: { portfolios: Array<{ name: string; pd_path: number[] }> };
  };

  it("Table 5 live: the bounds along the correlation are the ports' at the rail's level; the printed bounds sit at their correlations", () => {
    for (const level of [0.95, 0.9]) {
      const charts = drawn(<PublishedImpactView sel={makeSel(d, { level }) as C04Sel} />);
      const chart = charts.find((c) => c.series.some((s) => label(s) === 'Wald, upper'))!;
      const { defaults, n } = o.sr190;
      close(series(chart, 'Wald, upper'), RHO_GRID.map((rho) => pdWald(defaults, n, { level, rho }).upper), `${level} Wald upper`);
      close(series(chart, 'Agresti-Coull, lower'), RHO_GRID.map((rho) => pdAgrestiCoull(defaults, n, { level, rho }).lower), `${level} AC lower`);
      const printed = RHO_GRID.map((x) => o.sr190.rows.find((r) => r.interval === 'wald' && Math.abs(r.rho - x) < 1e-12)?.printed[1] ?? null);
      close(series(chart, 'Table 5, Wald upper'), printed, `${level} printed Wald upper`);
    }
  });

  it("Engelmann's paths: each starting portfolio's projected PD, year by year, as the bake recomputed it", () => {
    const charts = drawn(<PapersView sel={makeSel(d)} />);
    const chart = charts.find((c) => c.series.some((s) => label(s) === o.engelmann.portfolios[0].name))!;
    for (const p of o.engelmann.portfolios) close(series(chart, p.name), p.pd_path, p.name);
  });
});
