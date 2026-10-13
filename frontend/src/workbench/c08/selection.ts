// The selection the C08 views share, and the readings of a default-cohort document every view needs. Nothing here
// computes a statistic: the LGD proxy, the rungs, the downturn add-on and the floors' bite are the bake's; the helpers
// find, name and map. A loss given default is never clipped to [0, 1]: the contract flags it and the views print the flag.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C08Outputs = components['schemas']['c08Outputs'];
export type C08Fit = components['schemas']['c08Fit'];

export interface C08Sel {
  data: CaseData;
  /** The LGD model in focus. */
  rung: string;
  /** The endpoint shift of the beta regression the Endpoints view marks. */
  epsilon: number;
  /** The default cohort of the realised-against-predicted read-out. */
  cohort: string;
  /** The segment of the floors' read-out. */
  segment: string;
}

/** The outputs of the selected variant, or null when it is not a default-cohort document. */
export function outputsOf(sel: Pick<C08Sel, 'data'> | null): C08Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'default-cohort' ? (out as C08Outputs) : null;
}

/** The fit of the C08 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C08Sel, 'data'> | null): C08Fit | null {
  return (sel?.data.models as unknown as { fit?: C08Fit } | undefined)?.fit ?? null;
}

/** What each kind of LGD model is called. */
export const KIND_TEXT: Record<string, Bi> = {
  ols: { en: 'Linear regression', es: 'Regresión lineal' },
  'fractional-logit': { en: 'Fractional logit', es: 'Logit fraccional' },
  beta: { en: 'Beta regression', es: 'Regresión beta' },
  hurdle: { en: 'Two-stage hurdle', es: 'Modelo en dos etapas' },
  tobit: { en: 'Tobit', es: 'Tobit' },
  'gradient-boosted': { en: 'Gradient boosting', es: 'Gradient boosting' },
  'cure-decomposition': { en: 'Cure-rate decomposition', es: 'Descomposición por tasa de cura' },
};

/** The kind of a rung: the models artifact names it, else the id's own suffix ("L2-fractional-logit"). */
export function kindOf(sel: Pick<C08Sel, 'data'> | null, id: string): string | null {
  const named = fitOf(sel)?.ladder.find((r) => r.rung_id === id)?.kind;
  return named ?? Object.keys(KIND_TEXT).find((k) => id.endsWith(k)) ?? null;
}

/** The words for a model, never its internal id when the kind is known. */
export function rungLabel(sel: Pick<C08Sel, 'data'> | null, id: string): Bi {
  const k = kindOf(sel, id);
  return k ? KIND_TEXT[k] : { en: id, es: id };
}

/** The first calendar year of a default cohort: the models artifact names it, else the id's four leading digits. */
export function cohortYear(sel: Pick<C08Sel, 'data'> | null, id: string): number {
  return fitOf(sel)?.cohorts.find((c) => c.id === id)?.first_year ?? (Number.parseInt(id.slice(0, 4), 10) || 0);
}

/** The bilingual label of a default cohort; the id when the models artifact does not name it. */
export function cohortLabel(sel: Pick<C08Sel, 'data'> | null, id: string): Bi {
  return fitOf(sel)?.cohorts.find((c) => c.id === id)?.label ?? { en: id, es: id };
}

/** The cohorts the realised-against-predicted and downturn rows cover, earliest first. */
export function cohortIds(sel: Pick<C08Sel, 'data'> | null): string[] {
  const o = outputsOf(sel);
  if (!o) return [];
  const ids = [...new Set([...o.realised_vs_predicted.map((r) => r.cohort_id), ...o.downturn.rows.map((r) => r.cohort_id)])];
  return ids.sort((a, b) => cohortYear(sel, a) - cohortYear(sel, b));
}

export { humanize } from '../c03/U6Shared';

const COLLATERAL_TEXT: Record<string, Bi> = {
  unsecured: { en: 'unsecured', es: 'sin garantía' },
  financial: { en: 'financial collateral', es: 'garantía financiera' },
  receivables: { en: 'receivables', es: 'cuentas por cobrar' },
  'real-estate': { en: 'real estate', es: 'bienes raíces' },
  'other-physical': { en: 'other physical collateral', es: 'otra garantía física' },
  qrre: { en: 'qualifying revolving retail', es: 'minorista revolvente calificado' },
  mortgage: { en: 'residential mortgage', es: 'hipoteca residencial' },
};
const PORTFOLIO_TEXT: Record<string, Bi> = { corporate: { en: 'Corporate', es: 'Corporativa' }, retail: { en: 'Retail', es: 'Minorista' } };

/** The words for one cell of the floor table: "Corporate, unsecured". */
export function floorCellLabel(cell: { portfolio: string; collateral: string }): Bi {
  const p = PORTFOLIO_TEXT[cell.portfolio] ?? { en: cell.portfolio, es: cell.portfolio };
  const c = COLLATERAL_TEXT[cell.collateral] ?? { en: cell.collateral, es: cell.collateral };
  return { en: `${p.en}, ${c.en}`, es: `${p.es}, ${c.es}` };
}

export const WORKOUT_CONVENTION: Record<string, Bi> = {
  'eba-interbank-plus-5pp': { en: 'EBA reading: an interbank rate plus 5 percentage points', es: 'Lectura de la EBA: una tasa interbancaria más 5 puntos porcentuales' },
  fixed: { en: 'A fixed rate', es: 'Una tasa fija' },
  'none-proxy': { en: 'None: a charge-off proxy is not discounted', es: 'Ninguno: un proxy de castigo no se descuenta' },
};
export const INCOMPLETE_TEXT: Record<string, Bi> = {
  excluded: { en: 'excluded from the training set', es: 'excluidos del entrenamiento' },
  projected: { en: 'projected to closure', es: 'proyectados hasta el cierre' },
  'not-applicable': { en: 'not applicable', es: 'no aplica' },
};

/** The selection a variant opens on: the first model, the shift the beta rung uses, the cohort of the variant, the first floor row. */
export function defaultSel(data: CaseData | null): C08Sel | null {
  if (!data || data.manifest.case_id !== 'C08') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const rung = o.rung_comparison[0]?.rung_id ?? '';
  const beta = fitOf({ data })?.ladder.find((r) => r.epsilon !== null)?.epsilon ?? null;
  const ids = cohortIds({ data });
  return {
    data,
    rung,
    epsilon: o.endpoint_sensitivity.find((e) => e.epsilon === beta)?.epsilon ?? o.endpoint_sensitivity[0]?.epsilon ?? 0,
    cohort: ids.includes(o.cohort.id) ? o.cohort.id : (ids[0] ?? o.cohort.id),
    segment: o.floors_bite.rows[0]?.segment_id ?? '',
  };
}
