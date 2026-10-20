// The selection the C21 views share, and the readings of a year-pair document every view needs. C21 is statistical
// disparity in public HMDA decisions and nothing else: no outcome exists (HMDA has no performance), so no
// outcome-conditioned test (equalized odds, equal opportunity, calibration by group) is read here. Nothing here computes
// a statistic: the rates, ratios, tests, controlled estimates and their confirmation are the bake's; the helpers find,
// name and map. The four-fifths flag is the document's (decided on the counts in exact arithmetic), never a float ratio
// recomputed here.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

type S = components['schemas'];
export type C21Outputs = S['c21Outputs'];
export type C21Attribute = S['c21Attribute'];
export type C21Contrast = S['c21Contrast'];
export type C21Fit = S['c21Fit'];
export type C21Legal = S['c21Legal'];

export interface C21Sel {
  data: CaseData;
  /** The protected attribute in focus (its HMDA field). */
  field: string;
  /** The group compared with the reference group in the contrast views. */
  group: string;
}

export function outputsOf(sel: Pick<C21Sel, 'data'> | null): C21Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'year-pair' ? (out as C21Outputs) : null;
}

export function fitOf(sel: Pick<C21Sel, 'data'> | null): C21Fit | null {
  return (sel?.data.models as unknown as { fit?: C21Fit } | undefined)?.fit ?? null;
}

export function attributeOf(o: C21Outputs | null, field: string): C21Attribute | null {
  return o?.attributes.find((a) => a.field === field) ?? o?.attributes[0] ?? null;
}

export const attributeFor = (sel: C21Sel | null): C21Attribute | null => attributeOf(outputsOf(sel), sel?.field ?? '');

/** The contrast of the group in focus against the reference group, or the first one the attribute carries. */
export function contrastFor(sel: C21Sel | null): C21Contrast | null {
  const a = attributeFor(sel);
  return a?.contrasts.find((c) => c.group === sel?.group) ?? a?.contrasts[0] ?? null;
}

export const FIELD_TEXT: Record<string, Bi> = {
  derived_race: { en: 'Race', es: 'Raza' },
  derived_ethnicity: { en: 'Ethnicity', es: 'Etnicidad' },
  derived_sex: { en: 'Sex', es: 'Sexo' },
  applicant_age: { en: 'Age', es: 'Edad' },
};

export const BASIS_TEXT: Record<string, Bi> = {
  race_color: { en: 'race or colour', es: 'raza o color' },
  national_origin_nearest_UNVERIFIED: { en: 'national origin (the nearest basis, UNVERIFIED)', es: 'origen nacional (la base más cercana, SIN VERIFICAR)' },
  sex: { en: 'sex', es: 'sexo' },
  age_ecoa_only: { en: 'age (ECOA only)', es: 'edad (solo ECOA)' },
};

export const CONTROL_TEXT: Record<string, Bi> = {
  debt_to_income_ratio: { en: 'debt-to-income', es: 'deuda sobre ingreso' },
  combined_loan_to_value_ratio: { en: 'combined loan-to-value', es: 'préstamo sobre valor combinado' },
  income: { en: 'income', es: 'ingreso' },
  loan_amount: { en: 'loan amount', es: 'monto del préstamo' },
  property_value: { en: 'property value', es: 'valor de la propiedad' },
  loan_type: { en: 'loan type', es: 'tipo de préstamo' },
  loan_purpose: { en: 'loan purpose', es: 'propósito del préstamo' },
  lien_status: { en: 'lien status', es: 'rango del gravamen' },
  occupancy_type: { en: 'occupancy type', es: 'tipo de ocupación' },
  credit_score: { en: 'credit score', es: 'puntaje de crédito' },
};

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The selection a variant opens on: the first attribute and its first contrast group. */
export function defaultSel(data: CaseData | null): C21Sel | null {
  if (!data || data.manifest.case_id !== 'C21') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const a = o.attributes[0];
  return { data, field: a?.field ?? '', group: a?.contrasts[0]?.group ?? '' };
}
