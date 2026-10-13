// The selection the C09 views share, and the readings of an acceleration-level document every view needs. Nothing here
// computes a statistic: the CCF by design, the distribution, the EAD back-test and the floors are the bake's; the
// helpers find, name and map. The known CCF of the generator is always read beside the estimates, and a CCF outside
// [0, 1] is never clipped: the contract flags it and the views print the flag.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C09Outputs = components['schemas']['c09Outputs'];
export type C09Fit = components['schemas']['c09Fit'];
export type C09CcfRow = components['schemas']['c09CcfRow'];

export interface C09Sel {
  data: CaseData;
  /** The reference-date design in focus. */
  design: string;
  /** The treatment of a CCF outside [0, 1] in focus. */
  treatment: string;
  /** The EAD model of the back-test. */
  model: string;
  /** The utilisation band of the back-test read-out. */
  band: string;
}

/** The outputs of the selected variant, or null when it is not an acceleration-level document. */
export function outputsOf(sel: Pick<C09Sel, 'data'> | null): C09Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'acceleration-level' ? (out as C09Outputs) : null;
}

/** The fit of the C09 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C09Sel, 'data'> | null): C09Fit | null {
  return (sel?.data.models as unknown as { fit?: C09Fit } | undefined)?.fit ?? null;
}

export const DESIGN_SHORT: Record<string, Bi> = {
  'fixed-horizon': { en: 'Fixed', es: 'Fijo' },
  cohort: { en: 'Cohort', es: 'Cohorte' },
  'variable-horizon': { en: 'Variable', es: 'Variable' },
};
export const DESIGN_TEXT: Record<string, Bi> = {
  'fixed-horizon': { en: 'Fixed horizon', es: 'Horizonte fijo' },
  cohort: { en: 'Cohort', es: 'Cohorte' },
  'variable-horizon': { en: 'Variable horizon', es: 'Horizonte variable' },
};
export const TREATMENT_TEXT: Record<string, Bi> = {
  none: { en: 'No treatment', es: 'Sin tratamiento' },
  censor: { en: 'Censor', es: 'Censura' },
  'floor-cap': { en: 'Floor and cap', es: 'Piso y tope' },
  'bounded-scale': { en: 'Bounded scale', es: 'Escala acotada' },
};
/** How the facility factors of a design become one CCF: their mean, or the pooled ratio of the sums. */
export const ESTIMATOR_TEXT: Record<string, Bi> = {
  mean: { en: 'Mean of the factors', es: 'Media de los factores' },
  pooled: { en: 'Pooled ratio', es: 'Razón agregada' },
};
const KIND_TEXT: Record<string, Bi> = {
  'ccf-fixed-horizon': { en: 'Fixed-horizon CCF', es: 'CCF a horizonte fijo' },
  'ccf-cohort': { en: 'Cohort CCF', es: 'CCF por cohorte' },
  'ccf-variable-horizon': { en: 'Variable-horizon CCF', es: 'CCF a horizonte variable' },
  'direct-ead': { en: 'Direct EAD', es: 'EAD directo' },
  'utilisation-change': { en: 'Utilisation change', es: 'Cambio de utilización' },
};
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The treatments the document carries for a design, in document order. */
export function treatmentsOf(o: C09Outputs, design: string): string[] {
  return [...new Set(o.ccf_by_design.rows.filter((r) => r.design === design).map((r) => r.treatment))];
}

/** The estimate row of a design and treatment, or null when the document carries no such pair. */
export function ccfRow(o: C09Outputs | null, design: string, treatment: string): C09CcfRow | null {
  return o?.ccf_by_design.rows.find((r) => r.design === design && r.treatment === treatment) ?? null;
}

/** The words for an EAD model: its kind, and its treatment when two models share a kind. Never the internal id. */
export function modelLabel(o: C09Outputs, id: string): Bi {
  const m = o.ead_models.find((x) => x.model_id === id);
  if (!m) return { en: id, es: id };
  const base = text(KIND_TEXT, m.kind);
  const twins = o.ead_models.filter((x) => x.kind === m.kind).length > 1;
  if (!twins || !m.treatment) return base;
  const t = text(TREATMENT_TEXT, m.treatment);
  return { en: `${base.en}, ${t.en.toLowerCase()}`, es: `${base.es}, ${t.es.toLowerCase()}` };
}

/** The kind of an EAD model in words (the table column). */
export const kindText = (kind: string): Bi => text(KIND_TEXT, kind);

/** The utilisation bands of the back-test, lowest first. */
export function bandsOf(o: C09Outputs): Array<{ id: string; lower: number; upper: number }> {
  const seen = new Map<string, { id: string; lower: number; upper: number }>();
  for (const r of o.ead_backtest.rows) if (!seen.has(r.band_id)) seen.set(r.band_id, { id: r.band_id, lower: r.utilisation_lower, upper: r.utilisation_upper });
  return [...seen.values()].sort((a, b) => a.lower - b.lower);
}

/** A band in words: "0% to 25%". */
export function bandLabel(b: { lower: number; upper: number }): Bi {
  const f = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 0 });
  return { en: `${f(b.lower, 'en')} to ${f(b.upper, 'en')}`, es: `${f(b.lower, 'es')} a ${f(b.upper, 'es')}` };
}

/** The selection a variant opens on: the first design and its first treatment, the first back-tested model and band. */
export function defaultSel(data: CaseData | null): C09Sel | null {
  if (!data || data.manifest.case_id !== 'C09') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const first = o.ccf_by_design.rows[0];
  const model = o.ead_backtest.rows[0]?.model_id ?? o.ead_models[0]?.model_id ?? '';
  return { data, design: first?.design ?? 'fixed-horizon', treatment: first?.treatment ?? 'none', model, band: bandsOf(o)[0]?.id ?? '' };
}
