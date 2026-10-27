// The selection the C03 views share, and the readings of a vintage-cohort document every view needs. Nothing here
// computes a statistic: the vintages, the PD curves, the deciles and the rungs are the bake's; the helpers find and map.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { Bi } from './U6Shared';

export type C03Outputs = components['schemas']['c03Outputs'];
export type C03Fit = components['schemas']['c03Fit'];

export interface C03Sel {
  data: CaseData;
  /** The approval fiscal year in focus. */
  vintage: number;
  /** The month of the curve the horizon read-out reads. */
  horizon: number;
  /** The PD rung in focus. */
  rung: string;
}

/** The outputs of the selected variant, or null when it is not a vintage-cohort document. */
export function outputsOf(sel: Pick<C03Sel, 'data'> | null): C03Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'vintage-cohort' ? (out as C03Outputs) : null;
}

/** The fit of the C03 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C03Sel, 'data'> | null): C03Fit | null {
  return (sel?.data.models as unknown as { fit?: C03Fit } | undefined)?.fit ?? null;
}

/** The selection a variant opens on: the first vintage, its last month, the champion rung of the comparison (the rung the calibration is read on; the first row is the constant anchor). */
export function defaultSel(data: CaseData | null): C03Sel | null {
  if (!data || data.manifest.case_id !== 'C03') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const first = o.vintage_curves[0];
  return { data, vintage: first?.fiscal_year ?? o.cohort.first_fy, horizon: first?.months[first.months.length - 1] ?? o.target.horizon_months, rung: o.rung_comparison.find((r) => r.rung_id === o.calibration.rung_id)?.rung_id ?? o.rung_comparison[0]?.rung_id ?? '' };
}

/** What each kind of PD rung is called. */
export const KIND_TEXT: Record<string, Bi> = {
  constant: { en: 'Constant (base rate)', es: 'Constante (tasa base)' },
  'woe-scorecard': { en: 'WoE scorecard', es: 'Tarjeta de puntuación WoE' },
  'penalised-logit': { en: 'Penalised logit', es: 'Logit penalizado' },
  pltr: { en: 'Logit with rule features', es: 'Logit con reglas' },
  ebm: { en: 'Explainable boosting machine', es: 'Máquina de potenciación explicable' },
  'monotone-gbm': { en: 'Monotone gradient boosting', es: 'Potenciación del gradiente monótona' },
  tabpfn: { en: 'TabPFN', es: 'TabPFN' },
};

/** The kind of a rung: the models artifact names it, else the id's own suffix ("P2-penalised-logit"). */
export function kindOf(sel: Pick<C03Sel, 'data'> | null, id: string): string | null {
  const named = fitOf(sel)?.ladder.find((r) => r.rung_id === id)?.kind;
  return named ?? Object.keys(KIND_TEXT).find((k) => id.endsWith(k)) ?? null;
}

/** The words for a rung, never its internal id when the kind is known. */
export function rungLabel(sel: Pick<C03Sel, 'data'> | null, id: string): Bi {
  const k = kindOf(sel, id);
  return k ? KIND_TEXT[k] : { en: id, es: id };
}

/** The range of fiscal years of a cohort window, "2018-2020". */
export const fyRange = (first: number, last: number): string => (first === last ? `${first}` : `${first}-${last}`);

/** The data source of a document in words (U16-R2b c04 B1: "sba-7a" printed as it is). */
export const SOURCE_TEXT: Record<string, { en: string; es: string }> = {
  'sba-7a': { en: 'SBA 7(a) loan-level file (FOIA)', es: 'Archivo a nivel de préstamo SBA 7(a) (FOIA)' },
};

/** The reasons a document gives for a rung it did not run, in both languages (the document writes them in English; c04 M2). The
 * TabPFN reason names the extra, not the path of its requirements file (R3 c04 m9): the committed string and the re-baked one read
 * the same words. */
const TABPFN_TEXT = {
  en: 'TabPFN is an optional extra of the bake environment and it is not installed there: the challenger is declared absent, and no number stands in for it',
  es: 'TabPFN es un extra opcional del entorno de la corrida y no está instalado en él: el retador se declara ausente y ningún número lo reemplaza',
};
const REASON_TEXT: Record<string, { en: string; es: string }> = {
  'TabPFN is the optional extra (data-pipeline/requirements-tabpfn.txt) and it is not installed in the bake environment: the challenger is declared absent, and no number stands in for it': TABPFN_TEXT,
  [TABPFN_TEXT.en]: TABPFN_TEXT,
};
export const reasonText = (reason: string): { en: string; es: string } => REASON_TEXT[reason] ?? { en: reason, es: reason };
