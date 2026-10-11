// The selection the views share, and the readings of a variant artifact every view needs. Nothing here computes a
// statistic: the tests are riskvalidation's, read from the committed rows; the helpers only find, map and resample.
import type { Lane, Provenance } from '@fasl-work/caos-app-shell';
import type { CaseData } from '../api/artifacts';
import type { ModelSummary, TestRow, Text, TruthStatus, VariantArtifact } from '../lib/contract.types';
import type { PolicyAlphas } from '../lib/policy';

export const CHAMPION = 'P1-scorecard';
export const PORTFOLIO = 'portfolio';

export interface Selection {
  data: CaseData;
  /** The rung compared with the champion in the Impact, Calibration and Discrimination views. */
  challenger: string;
  alphas: PolicyAlphas;
  /** The share of applicants approved in the Impact view. */
  approval: number;
  /** The loss given default assumed in the expected and realised losses. */
  lgd: number;
  /** Index into the variant's scored sample (the live scorer), when the variant has one. */
  applicant: number;
}

/** The lane a replayed view shows: the pipeline computed it offline and the web reads the committed artifact. */
export const REPLAY: Lane = 'replay';

export function provenanceOf(truth: TruthStatus | undefined): Provenance {
  if (truth === 'real-outcomes') return 'real';
  if (truth === 'published-answer') return 'published';
  return 'synthetic';
}

export function rungs(v: VariantArtifact): ModelSummary[] {
  return v.model;
}

export function rung(v: VariantArtifact, id: string): ModelSummary | undefined {
  return v.model.find((m) => m.id === id);
}

/** The challengers a reader can pick: every rung but the anchors and the champion. */
export function challengers(v: VariantArtifact): ModelSummary[] {
  return v.model.filter((m) => m.rung !== 'P0' && m.id !== CHAMPION);
}

export function defaultChallenger(v: VariantArtifact): string {
  const ids = challengers(v).map((m) => m.id);
  return ids.includes('P4-lightgbm') ? 'P4-lightgbm' : ids[ids.length - 1] ?? CHAMPION;
}

export function test(v: VariantArtifact, testId: string, modelId: string | null, segment: string = PORTFOLIO): TestRow | undefined {
  return v.tests.find((t) => t.test_id === testId && t.model_id === modelId && t.segment === segment);
}

export function tests(v: VariantArtifact, testId: string, modelId: string | null): TestRow[] {
  return v.tests.filter((t) => t.test_id === testId && t.model_id === modelId);
}

/** The value a test reports: its metric for a descriptive test, else its statistic. */
export function value(t: TestRow | undefined): number | null {
  if (!t) return null;
  return t.metric ?? t.statistic;
}

export function extra(t: TestRow | undefined, key: string): number | null {
  const v = t?.extras?.[key];
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

/** The label a chip, a column header or a chart key shows ("P2b PLTR"). */
export const shortName = (m: ModelSummary | undefined, fallback = ''): Text => m?.short_title ?? { en: fallback, es: fallback };

/** Linear interpolation of a monotone x grid onto new x values (no extrapolation beyond the ends). */
export function interp(xs: readonly number[], ys: readonly number[], at: readonly number[]): Array<number | null> {
  return at.map((x) => {
    if (!xs.length || x < xs[0] || x > xs[xs.length - 1]) return null;
    let hi = 0;
    while (hi < xs.length - 1 && xs[hi] < x) hi++;
    if (xs[hi] === x || hi === 0) return ys[hi];
    const lo = hi - 1;
    const w = (x - xs[lo]) / (xs[hi] - xs[lo] || 1);
    return ys[lo] + w * (ys[hi] - ys[lo]);
  });
}

/** An evenly spaced grid on [a, b] with n points. */
export function grid(a: number, b: number, n: number): number[] {
  return Array.from({ length: n }, (_, i) => a + ((b - a) * i) / (n - 1));
}

/** The sorted union of several x arrays, and each series' values on it (null where the series has no point). */
export function unionPoints(sets: Array<{ x: number[]; y: number[] }>): { x: number[]; ys: Array<Array<number | null>> } {
  const x = Array.from(new Set(sets.flatMap((s) => s.x))).sort((a, b) => a - b);
  const ys = sets.map((s) => {
    const m = new Map(s.x.map((xv, i) => [xv, s.y[i]]));
    return x.map((xv) => (m.has(xv) ? (m.get(xv) as number) : null));
  });
  return { x, ys };
}

/** Approve the share of lowest-PD applicants by the rung's cut-off curve: approval rate, bad rate, PD x EAD. */
export function atApproval(cut: { approval_rate: number[]; bad_rate: number[]; pd_ead: number[]; ead: number[] }, share: number) {
  const [bad] = interp(cut.approval_rate, cut.bad_rate, [share]);
  const [pdEad] = interp(cut.approval_rate, cut.pd_ead, [share]);
  const [ead] = interp(cut.approval_rate, cut.ead, [share]);
  return { bad, pdEad, ead };
}
