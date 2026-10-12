// The selection the C07 views share, and the readings of a three-regime variant every view needs. The only arithmetic
// is what the contract states: the IFRS 9 model ECL is the sum of weight times the single-scenario ECL of each weighted
// component, so a sensitivity re-weights the components the document carries; every other number is read as written.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C07Outputs = components['schemas']['c07Outputs'];
export type C07Fit = components['schemas']['c07Fit'];
export type RegimeId = 'cmf-b1' | 'ifrs9' | 'bde-annex9';

export interface C07Sel {
  data: CaseData;
  /** The regime the reader looks at closely. */
  regime: RegimeId;
  /** The segment of the gap read-out. */
  segment: string;
  /** The IFRS 9 weighting scenario whose weight the rail moves. */
  scenario: string;
  /** Its weight; the other components keep their ratios. */
  weight: number;
  /** The B-1 additional provisions the reader tries within the board policy limits; null keeps the document's. */
  additional: number | null;
}

/** The outputs of the selected variant, or null when it is not a three-regime document. */
export function outputsOf(sel: Pick<C07Sel, 'data'> | null): C07Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'three-regime' ? (out as C07Outputs) : null;
}

/** The fit of the C07 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C07Sel, 'data'> | null): C07Fit | null {
  return (sel?.data.models as unknown as { fit?: C07Fit } | undefined)?.fit ?? null;
}

/** The weights of the weighted components with `focus` at `w` and the others in their contract ratios. */
export function reweighted(o: C07Outputs, focus: string, w: number): number[] {
  const comps = o.ifrs9_detail.weighted_components;
  const f = comps.find((c) => c.scenario_id === focus);
  if (!f) return comps.map((c) => c.weight);
  const rest = 1 - f.weight;
  const n = comps.length - 1;
  return comps.map((c) => (c.scenario_id === focus ? w : rest > 0 ? (c.weight * (1 - w)) / rest : n > 0 ? (1 - w) / n : 0));
}

/** The IFRS 9 model ECL (overlays excluded) at the selection's weights. */
export function liveIfrs9(sel: C07Sel): number {
  const o = outputsOf(sel);
  if (!o) return 0;
  const w = reweighted(o, sel.scenario, sel.weight);
  return o.ifrs9_detail.weighted_components.reduce((a, c, i) => a + w[i] * c.single_scenario_ecl, 0);
}

/** The selection a variant opens on: the B-1 regime, the first segment, the most adverse weighted scenario at its own weight. */
export function defaultSel(data: CaseData | null): C07Sel | null {
  if (!data || data.manifest.case_id !== 'C07') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const adverse = [...o.ifrs9_detail.weighted_components].sort((a, b) => a.z - b.z)[0];
  return { data, regime: 'cmf-b1', segment: o.portfolio.segments[0]?.segment_id ?? '', scenario: adverse.scenario_id, weight: adverse.weight, additional: null };
}

/** The bilingual label of a weighting scenario (the models artifact names them); the id when the artifact has none. */
export function componentLabel(sel: Pick<C07Sel, 'data'> | null, id: string): { en: string; es: string } {
  return fitOf(sel)?.ifrs9.weighting_scenarios.find((w) => w.id === id)?.label ?? { en: id, es: id };
}
