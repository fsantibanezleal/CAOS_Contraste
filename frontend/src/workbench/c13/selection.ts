// The selection the C13 views share, and the readings of a deficiency document every view needs. The statistics, the
// zone counts, the detection rate and the desk back-test are the bake's. The one thing computed here is the picture of
// the example replication, which the document keeps whole for that purpose: the ranks of its two P&L series (the
// Spearman scatter) and their two empirical distribution functions with the largest gap (the Kolmogorov-Smirnov
// picture of MAR32.36 to MAR32.41). The tests recompute the document's own Spearman and KS from them.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { Bi } from '../c03/U6Shared';

export type C13Outputs = components['schemas']['c13Outputs'];
export type C13Fit = components['schemas']['c13Fit'];
export type C13Alpha = 0.01 | 0.025;
export type C13Statistic = 'overall' | 'spearman' | 'ks';

export interface C13Sel {
  data: CaseData;
  /** The desk back-test level in focus. */
  alpha: C13Alpha;
  /** The statistic whose zone counts are in focus: the joint zone of MAR32.42, or one of its two statistics. */
  statistic: C13Statistic;
}

/** The outputs of the selected variant, or null when it is not a deficiency document. */
export function outputsOf(sel: Pick<C13Sel, 'data'> | null): C13Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'deficiency' ? (out as C13Outputs) : null;
}

/** The fit of the C13 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C13Sel, 'data'> | null): C13Fit | null {
  return (sel?.data.models as unknown as { fit?: C13Fit } | undefined)?.fit ?? null;
}

export const DEFICIENCY_TEXT: Record<string, Bi> = {
  none: { en: 'No deficiency (control)', es: 'Sin deficiencia (control)' },
  'missing-basis': { en: 'Missing basis', es: 'Base omitida' },
  'stale-volatility': { en: 'Stale volatility', es: 'Volatilidad desactualizada' },
  'wrong-correlation': { en: 'Wrong correlation', es: 'Correlación errónea' },
  'omitted-factor': { en: 'Omitted risk factor', es: 'Factor de riesgo omitido' },
  'time-misalignment': { en: 'Time misalignment', es: 'Desfase temporal' },
};

export const INTENDED_TEXT: Record<string, Bi> = {
  none: { en: 'none (the control)', es: 'ninguna (el control)' },
  spearman: { en: 'Spearman', es: 'Spearman' },
  ks: { en: 'Kolmogorov-Smirnov', es: 'Kolmogorov-Smirnov' },
  either: { en: 'either statistic', es: 'cualquiera de los dos estadísticos' },
};

export const STATISTIC_TEXT: Record<C13Statistic, Bi> = {
  overall: { en: 'Joint zone (MAR32.42)', es: 'Zona conjunta (MAR32.42)' },
  spearman: { en: 'Spearman alone', es: 'Solo Spearman' },
  ks: { en: 'Kolmogorov-Smirnov alone', es: 'Solo Kolmogorov-Smirnov' },
};

export const ZONE_TEXT: Record<string, Bi> = {
  green: { en: 'Green', es: 'Verde' },
  amber: { en: 'Amber', es: 'Ámbar' },
  red: { en: 'Red', es: 'Rojo' },
};

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** A desk level in words: "1% tail (99% VaR)". */
export function levelLabel(alpha: number, lang: 'en' | 'es'): string {
  const f = (v: number) => (v === 0.025 ? (lang === 'es' ? '2,5' : '2.5') : String(Math.round(v * 100)));
  const g = (v: number) => (v === 0.025 ? (lang === 'es' ? '97,5' : '97.5') : String(Math.round((1 - v) * 100)));
  return lang === 'es' ? `Cola de ${f(alpha)} % (VaR al ${g(alpha)} %)` : `${f(alpha)}% tail (${g(alpha)}% VaR)`;
}

/** A desk level in a few words, for a chip of the narrow rail: "2.5% tail". */
export function levelShort(alpha: number, lang: 'en' | 'es'): string {
  const f = alpha === 0.025 ? (lang === 'es' ? '2,5' : '2.5') : String(Math.round(alpha * 100));
  return lang === 'es' ? `Cola de ${f} %` : `${f}% tail`;
}

/** The average ranks of a series (ties share the mean of their ranks), 1 for the smallest. */
export function ranks(x: readonly number[]): number[] {
  const order = x.map((_, i) => i).sort((a, b) => x[a] - x[b]);
  const r = new Array<number>(x.length).fill(0);
  let i = 0;
  while (i < order.length) {
    let j = i;
    while (j + 1 < order.length && x[order[j + 1]] === x[order[i]]) j++;
    for (let k = i; k <= j; k++) r[order[k]] = (i + j) / 2 + 1;
    i = j + 1;
  }
  return r;
}

/** The ranks of the two series, as the scatter draws them: HPL on x, RTPL on y. */
export function rankSeries(hpl: readonly number[], rtpl: readonly number[]): { x: number[]; y: number[] } {
  return { x: ranks(hpl), y: ranks(rtpl) };
}

/** Spearman's coefficient: the correlation of the two rank series. */
export function spearmanOf(hpl: readonly number[], rtpl: readonly number[]): number {
  const { x, y } = rankSeries(hpl, rtpl);
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

/** The count of values in the sorted array that are at most `p`. */
function countAtMost(sorted: readonly number[], p: number): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid] <= p) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

/**
 * The two empirical distribution functions on the pooled values, each in steps of `step` per observation (MAR32.39 to
 * MAR32.41: F(x) = 0.004 times the number of observations at most x), and the largest gap between them as an exact
 * integer count of steps over the number of observations.
 */
export function ecdfGap(hpl: readonly number[], rtpl: readonly number[], step = 0.004): { points: number[]; hpl: number[]; rtpl: number[]; steps: number; gap: number; at: number } {
  const sh = [...hpl].sort((a, b) => a - b);
  const sr = [...rtpl].sort((a, b) => a - b);
  const points = [...new Set([...hpl, ...rtpl])].sort((a, b) => a - b);
  let steps = 0;
  let at = points[0] ?? 0;
  const fh: number[] = [];
  const fr: number[] = [];
  for (const p of points) {
    const ch = countAtMost(sh, p);
    const cr = countAtMost(sr, p);
    fh.push(ch * step);
    fr.push(cr * step);
    const d = Math.abs(cr - ch);
    if (d > steps) {
      steps = d;
      at = p;
    }
  }
  return { points, hpl: fh, rtpl: fr, steps, gap: steps / hpl.length, at };
}

/** The selection a variant opens on: the first desk level and the joint zone. */
export function defaultSel(data: CaseData | null): C13Sel | null {
  if (!data || data.manifest.case_id !== 'C13') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  return { data, alpha: (o.desk_backtest[0]?.alpha ?? 0.025) as C13Alpha, statistic: 'overall' };
}
