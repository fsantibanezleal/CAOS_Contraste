// The selection the C06 views share, and the readings of a reporting-date variant every view needs. The only
// arithmetic is what the contract itself states: the weighted ECL is the sum of weight times scenario ECL (the staging
// is frozen), so moving a weight re-weights the per-scenario ECLs the document carries; nothing else is computed here.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C06Outputs = components['schemas']['c06Outputs'];
export type C06Fit = components['schemas']['c06Fit'];
export type C06Models = { fit?: C06Fit };

/** The words for the ids the documents carry (U16-R2 b03 B3): never an id inside a Spanish sentence or cell. */
export const COHORT_TEXT: Record<string, { en: string; es: string }> = { all: { en: 'all', es: 'todas' }, older: { en: 'older', es: 'anteriores' } };
export const cohortText = (id: string): { en: string; es: string } => COHORT_TEXT[id] ?? { en: id, es: id };
export const MOVEMENT_TEXT: Record<string, { en: string; es: string }> = {
  originations: { en: 'originations', es: 'originaciones' },
  derecognition: { en: 'derecognition', es: 'baja en cuentas' },
  'write-off': { en: 'write-off', es: 'castigo' },
  remeasurement: { en: 'remeasurement', es: 'remedición' },
  'macro-update': { en: 'macro update', es: 'actualización macro' },
  'transfer-1-2': { en: 'transfer 1 to 2', es: 'traspaso de 1 a 2' },
  'transfer-2-1': { en: 'transfer 2 to 1', es: 'traspaso de 2 a 1' },
  'transfer-2-3': { en: 'transfer 2 to 3', es: 'traspaso de 2 a 3' },
};
export const movementText = (id: string): { en: string; es: string } => MOVEMENT_TEXT[id] ?? { en: id, es: id };
export const SETTING_TEXT: Record<string, { en: string; es: string }> = {
  'mid-period': { en: 'mid-period', es: 'a mitad de período' },
  original: { en: 'original', es: 'original' },
  current: { en: 'current', es: 'vigente' },
  'end-of-period': { en: 'end of period', es: 'a fin de período' },
};
export const settingText = (id: string): { en: string; es: string } => SETTING_TEXT[id] ?? { en: id, es: id };

export type Measure = 'cumulative' | 'marginal' | 'hazard';
export type Staging = 'recomputed' | 'frozen';
export type Surface = 'ecl' | 'stage2';

export interface C06Sel {
  data: CaseData;
  /** The scenario whose weight the rail moves, and whose curve is drawn heavier. */
  scenario: string;
  /** The segment of the term structures. */
  segment: string;
  /** The sampled account of the SICR pair of curves. */
  account: string;
  measure: Measure;
  /** The weight of `scenario`; the other scenarios keep their ratios. */
  weight: number;
  staging: Staging;
  surface: Surface;
}

/** The outputs of the selected variant, or null when it is not a reporting-date document. */
export function outputsOf(sel: Pick<C06Sel, 'data'> | null): C06Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'reporting-date' ? (out as C06Outputs) : null;
}

/** The fit of the C06 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C06Sel, 'data'> | null): C06Fit | null {
  return (sel?.data.models as unknown as C06Models | undefined)?.fit ?? null;
}

/** The ECL of each scenario at 100 per cent weight, summed over the stages (the model ECL, overlays excluded). */
export function scenarioEcl(o: C06Outputs): Record<string, number> {
  const by: Record<string, number> = {};
  for (const r of o.ecl_by_scenario.rows) by[r.scenario_id] = (by[r.scenario_id] ?? 0) + r.ecl;
  return by;
}

/** The weights with `focus` at `w` and the others in their contract ratios; at the contract weight it returns the contract weights. */
export function rescaled(o: C06Outputs, focus: string, w: number): number[] {
  const f = o.scenarios.find((s) => s.id === focus);
  if (!f) return o.scenarios.map((s) => s.weight);
  const rest = 1 - f.weight;
  const n = o.scenarios.length - 1;
  return o.scenarios.map((s) => {
    if (s.id === focus) return w;
    return rest > 0 ? (s.weight * (1 - w)) / rest : n > 0 ? (1 - w) / n : 0;
  });
}

/** The model ECL at the selection's weights, staging frozen (so linear in the weights, as the contract states). */
export function liveEcl(sel: C06Sel): number {
  const o = outputsOf(sel);
  if (!o) return 0;
  const by = scenarioEcl(o);
  const w = rescaled(o, sel.scenario, sel.weight);
  return o.scenarios.reduce((a, s, i) => a + w[i] * by[s.id], 0);
}

/** The precomputed simplex point nearest to the selection's weights (Euclidean in weight space). */
export function nearestPoint(o: C06Outputs, weights: number[]): C06Outputs['weight_grid']['points'][number] | null {
  let best: C06Outputs['weight_grid']['points'][number] | null = null;
  let bestD = Infinity;
  for (const p of o.weight_grid.points) {
    const d = p.weights.reduce((a, x, i) => a + (x - (weights[i] ?? 0)) ** 2, 0);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  return best;
}

/** The selection a variant opens on: the most adverse scenario at its own weight, the first segment and account. */
export function defaultSel(data: CaseData | null): C06Sel | null {
  if (!data || data.manifest.case_id !== 'C06') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const adverse = [...o.scenarios].sort((a, b) => a.z_mean - b.z_mean)[0];
  return {
    data,
    scenario: adverse.id,
    segment: o.term_structures[0]?.segment_id ?? '',
    account: o.account_curves[0]?.account_id ?? '',
    measure: 'cumulative',
    weight: adverse.weight,
    staging: 'recomputed',
    surface: 'ecl',
  };
}
