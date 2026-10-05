// The live lane of C01 (SDD section 3): the additive scores, computed in the browser from the committed model records
// alone. A scorecard is a points table and a logistic link; an EBM is an intercept plus one score per term. Both are
// held to the pipeline's own scores of 50 holdout applicants by engine/parity.test.ts (CT-105: integer points and
// scores exactly, PDs and logits within 1e-9). GBM and TabPFN scores are never recomputed here: they are replayed.
import type { EbmExport, EbmLevel, ScorecardDetails } from '../lib/contract.types';

export type Value = number | string | null | undefined;
export type Inputs = Record<string, Value>;

/** The first position whose element is greater than x (Python's bisect_right / numpy side='right'). */
export function bisectRight(a: readonly number[], x: number): number {
  let lo = 0;
  let hi = a.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (x < a[mid]) hi = mid;
    else lo = mid + 1;
  }
  return lo;
}

const isMissing = (v: Value): boolean => v === null || v === undefined || (typeof v === 'number' && Number.isNaN(v));

/** The row of a characteristic's points table a value falls in: the numerical bin [split_(i-1), split_i), the
 * category set that holds it, or, for anything else, the table's last row (the zero-WoE "Missing" bin). */
export function scorecardRow(sc: ScorecardDetails, feature: string, value: Value): number {
  const rows = sc.points_table.filter((r) => r.feature === feature);
  const missing = rows.length - 1;
  if (isMissing(value)) return missing;
  const spec = sc.bins[feature];
  if (spec.kind === 'numerical') return bisectRight(spec.splits, Number(value));
  const k = spec.categories.findIndex((cats) => cats.includes(String(value)));
  return k >= 0 ? k : missing;
}

export interface ScorecardScore {
  /** Integer points per characteristic, in the order of `sc.features`. */
  points: number[];
  score: number;
  pd: number;
  /** The rows the applicant falls in, per characteristic. */
  rows: number[];
}

export function scoreScorecard(sc: ScorecardDetails, inputs: Inputs): ScorecardScore {
  const rows: number[] = [];
  const points: number[] = [];
  let eta = sc.intercept;
  for (const f of sc.features) {
    const r = scorecardRow(sc, f, inputs[f]);
    const row = sc.points_table.filter((p) => p.feature === f)[r];
    rows.push(r);
    points.push(row.points);
    eta += sc.coefficients[f] * row.woe;
  }
  return { points, score: points.reduce((a, b) => a + b, 0), pd: 1 / (1 + Math.exp(-eta)), rows };
}

function ebmLevel(levels: EbmLevel[], level: number): EbmLevel {
  return levels[Math.min(level, levels.length - 1)];
}

/** EBM's bin of a value at a binning level: 0 for missing, 1.. for the bins, the last index for an unseen category. */
export function ebmBin(feature: { levels: EbmLevel[] }, level: number, value: Value): number {
  const lv = ebmLevel(feature.levels, level);
  if (isMissing(value)) return 0;
  if (lv.kind === 'nominal') {
    const cats = lv.categories ?? {};
    const key = String(value);
    return key in cats ? cats[key] : Object.keys(cats).length + 1;
  }
  return bisectRight(lv.cuts ?? [], Number(value)) + 1;
}

function at(scores: unknown, idx: number[]): number {
  let cur: unknown = scores;
  for (const i of idx) cur = (cur as unknown[])[i];
  return cur as number;
}

/** The EBM's additive logit: the intercept plus each term's score at the applicant's bins (main terms read level 0,
 * pairs level 1 where the feature has one). */
export function ebmLogit(ex: EbmExport, inputs: Inputs): { logit: number; terms: Array<{ name: string; score: number }> } {
  let logit = ex.intercept;
  const terms: Array<{ name: string; score: number }> = [];
  for (const t of ex.terms) {
    const level = t.features.length === 1 ? 0 : 1;
    const idx = t.features.map((fi) => ebmBin(ex.features[fi], level, inputs[ex.features[fi].name]));
    const s = at(t.scores, idx);
    terms.push({ name: t.name, score: s });
    logit += s;
  }
  return { logit, terms };
}

export const sigmoid = (x: number): number => 1 / (1 + Math.exp(-x));
