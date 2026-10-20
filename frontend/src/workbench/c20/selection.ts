// The selection the C20 views share, and the readings of a variant document every view needs. C20 has five kinds of
// variant document (SGCD shocks seen and held out, the Federal Reserve shift probes, the seed sweep, the perturbation
// grid and the planted leak): the kind of `outputs` says which. Nothing here computes a statistic: the degradation, the
// drift, the dispersion, the coverage and the screens are the bake's; the helpers find, name and map. A view given a
// document of another kind says so and draws nothing.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

type S = components['schemas'];
export type C20Shock = S['c20Outputs'];
export type C20Shift = S['c20OutputsShift'];
export type C20Seeds = S['c20OutputsSeeds'];
export type C20Perturbation = S['c20OutputsPerturbation'];
export type C20Leakage = S['c20OutputsLeakage'];
export type C20Outputs = C20Shock | C20Shift | C20Seeds | C20Perturbation | C20Leakage;
export type C20Fit = S['c20Fit'];
export type C20ShockRow = S['c20ShockRow'];
export type C20Metric = S['c20Metric'];
export type C20FairRow = S['c20FairRow'];
export type C20Kind = C20Outputs['kind'];

export const KINDS: readonly C20Kind[] = ['shock', 'shift', 'seeds', 'perturbation', 'leakage'];

export type Block = 'shipped' | 'applied';
export type Screen = 'temporal' | 'single' | 'overlap' | 'resemblance';

export interface C20Sel {
  data: CaseData;
  /** The SGCD block the drift and quality views read: the shocks as shipped or Contraste's own application of them. */
  block: Block;
  /** The shock in focus (SGCD kind). */
  shock: string;
  /** The synthetic shift in focus (shift kind). */
  shift: string;
  /** The conformal window in focus (shift kind). */
  window: string;
  /** The rung in focus (seed sweep). */
  rung: string;
  /** The noise scale in focus (perturbation grid), as the index of the grid row. */
  eps: number;
  /** The leakage screen in focus. */
  screen: Screen;
  /** The fairness test and attribute in focus (the labelled battery on the Taiwan model). */
  test: string;
  attribute: string;
}

export function outputsOf(sel: Pick<C20Sel, 'data'> | null): C20Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && KINDS.includes(out.kind as C20Kind) ? (out as C20Outputs) : null;
}

export const kindOf = (sel: Pick<C20Sel, 'data'> | null): C20Kind | null => outputsOf(sel)?.kind ?? null;

/** The outputs when the variant is of the kind asked for, else null: a view of another kind says so. */
export function asKind<K extends C20Kind>(sel: Pick<C20Sel, 'data'> | null, kind: K): Extract<C20Outputs, { kind: K }> | null {
  const o = outputsOf(sel);
  return o && o.kind === kind ? (o as Extract<C20Outputs, { kind: K }>) : null;
}

export function fitOf(sel: Pick<C20Sel, 'data'> | null): C20Fit | null {
  return (sel?.data.models as unknown as { fit?: C20Fit } | undefined)?.fit ?? null;
}

/** The rows of the SGCD block in focus. */
export function blockRows(o: C20Shock | null, block: Block): C20ShockRow[] {
  return o ? o[block].rows : [];
}

export const SHOCK_TEXT: Record<string, Bi> = {
  F0: { en: 'F0 faithful records', es: 'F0 registros fieles' },
  F1: { en: 'F1 missing field', es: 'F1 campo faltante' },
  F2: { en: 'F2 ambiguous wording', es: 'F2 redacción ambigua' },
  F3: { en: 'F3 cosmetic noise', es: 'F3 ruido cosmético' },
  F4: { en: 'F4 contradiction', es: 'F4 contradicción' },
  'numeric-noise': { en: 'Numeric noise', es: 'Ruido numérico' },
};

export const DATASET_TEXT: Record<string, Bi> = {
  sgcd: { en: 'SGCD, stressed German credit data', es: 'SGCD, datos estresados de crédito alemán' },
  'uci-german': { en: 'UCI German credit', es: 'UCI crédito alemán' },
  'uci-taiwan': { en: 'UCI Taiwan credit card default', es: 'UCI incumplimiento de tarjetas de Taiwán' },
  'uci-polish': { en: 'UCI Polish company bankruptcy', es: 'UCI quiebra de empresas polacas' },
  'fed-2025-corporate': { en: 'Federal Reserve 2025 corporate portfolios', es: 'Carteras corporativas 2025 de la Reserva Federal' },
};

export const PORTFOLIO_TEXT: Record<string, Bi> = {
  typical: { en: 'Typical risk', es: 'Riesgo típico' },
  'higher-risk': { en: 'Higher risk', es: 'Riesgo mayor' },
  'lower-risk': { en: 'Lower risk', es: 'Riesgo menor' },
};

export const KIND_TEXT: Record<C20Kind, Bi> = {
  shock: { en: 'SGCD shocks', es: 'Choques de SGCD' },
  shift: { en: 'Shift probes', es: 'Sondas de cambio' },
  seeds: { en: 'Seed sweep', es: 'Barrido de semillas' },
  perturbation: { en: 'Perturbation grid', es: 'Grilla de perturbación' },
  leakage: { en: 'Planted leak', es: 'Fuga plantada' },
};

export const SCREEN_TEXT: Record<Screen, Bi> = {
  temporal: { en: 'Temporal order', es: 'Orden temporal' },
  single: { en: 'Single-feature AUC', es: 'AUC de una variable' },
  overlap: { en: 'Entity overlap', es: 'Solapamiento de entidades' },
  resemblance: { en: 'Resemblance AUC', es: 'AUC de parecido' },
};

export const ATTRIBUTE_TEXT: Record<string, Bi> = {
  sex: { en: 'Sex', es: 'Sexo' },
  age: { en: 'Age', es: 'Edad' },
  marital_status: { en: 'Marital status', es: 'Estado civil' },
};

export const FAIR_TESTS = ['fair.equalized_odds', 'fair.equal_opportunity', 'fair.calibration_within_groups', 'fair.auc_by_group'] as const;

/** The text a map holds for an id, or the id itself. */
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The shock rows to focus when a variant opens: the first shock of the shipped block, else the applied one. */
function firstShock(o: C20Shock): string {
  return o.shipped.rows[0]?.shock_id ?? o.applied.rows[0]?.shock_id ?? 'F1';
}

/** The selection a variant opens on: the shipped block, the first shock, shift, window and rung, the preset noise scale. */
export function defaultSel(data: CaseData | null): C20Sel | null {
  if (!data || data.manifest.case_id !== 'C20') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const shift = o.kind === 'shift' ? o.synthetic_shift.shifts[0]?.shift_id ?? '' : '';
  const win = o.kind === 'shift' ? o.synthetic_shift.label_free.conformal.coverage_by_window[0]?.window ?? '' : '';
  const rung = o.kind === 'seeds' ? o.rows[0]?.rung ?? '' : '';
  const eps = o.kind === 'perturbation' ? Math.max(0, o.rows.findIndex((r) => r.eps === o.preset_eps)) : 0;
  const first = o.fairness_battery?.rows[0];
  return {
    data,
    block: 'shipped',
    shock: o.kind === 'shock' ? firstShock(o) : '',
    shift,
    window: win,
    rung,
    eps,
    screen: 'temporal',
    test: first?.test_id ?? FAIR_TESTS[0],
    attribute: first?.attribute ?? 'sex',
  };
}
