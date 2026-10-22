// The selection the C14 views share, and the readings of a valuation-date document every view needs. Nothing here
// computes a statistic: the shocked EVE, the NII under the parallel shocks, the replicating portfolios, the dynamic NII
// and the EaR and EVaR are the bake's; the helpers find, name and map. The sign convention is the document's: a positive
// delta EVE or delta NII is a loss, and the views print that convention wherever a delta appears.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { compactMoney, axisScale } from '../c06/format';

export type C14Outputs = components['schemas']['c14Outputs'];
export type C14Fit = components['schemas']['c14Fit'];
export type C14Scenario = components['schemas']['c14Scenario'];
export type C14Shock = components['schemas']['c14ShockResult'];
export type C14NmdModel = components['schemas']['c14NmdModel'];
export type C14Segment = components['schemas']['c14NmdSegment'];

export type Calibration = '2024' | '2016';
export type NmdAssumption = 'behavioural' | 'contractual';
export type ShockId = C14Shock['shock'];
export type NmdCategory = C14Segment['category'];

export interface C14Sel {
  data: CaseData;
  /** The calibration of the shock sizes in focus. */
  calibration: Calibration;
  /** With the behavioural NMD assumptions, or with every non-maturity deposit in the overnight bucket. */
  nmd: NmdAssumption;
  /** The prescribed shock in focus. */
  shock: ShockId;
  /** The non-maturity deposit category whose replicating portfolio is in focus. */
  category: NmdCategory;
}

/** The outputs of the selected variant, or null when it is not a valuation-date document. */
export function outputsOf(sel: Pick<C14Sel, 'data'> | null): C14Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'valuation-date' ? (out as C14Outputs) : null;
}

/** The fit of the C14 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C14Sel, 'data'> | null): C14Fit | null {
  return (sel?.data.models as unknown as { fit?: C14Fit } | undefined)?.fit ?? null;
}

/** The six prescribed shocks of SRP31.90, in the order of the documents. */
export const SHOCK_ORDER: readonly ShockId[] = ['parallel-up', 'parallel-down', 'steepener', 'flattener', 'short-up', 'short-down'];

export const SHOCK_TEXT: Record<string, Bi> = {
  'parallel-up': { en: 'Parallel up', es: 'Paralelo al alza' },
  'parallel-down': { en: 'Parallel down', es: 'Paralelo a la baja' },
  steepener: { en: 'Steepener', es: 'Empinamiento' },
  flattener: { en: 'Flattener', es: 'Aplanamiento' },
  'short-up': { en: 'Short rates up', es: 'Tasas cortas al alza' },
  'short-down': { en: 'Short rates down', es: 'Tasas cortas a la baja' },
};
export const CALIBRATION_TEXT: Record<string, Bi> = {
  '2024': { en: '2024 calibration', es: 'Calibración 2024' },
  '2016': { en: '2016 calibration', es: 'Calibración 2016' },
};
export const CALIBRATION_SHORT: Record<string, Bi> = { '2024': { en: '2024', es: '2024' }, '2016': { en: '2016', es: '2016' } };
export const NMD_TEXT: Record<string, Bi> = {
  behavioural: { en: 'Behavioural', es: 'Conductual' },
  contractual: { en: 'Contractual', es: 'Contractual' },
};
export const NMD_LONG: Record<string, Bi> = {
  behavioural: { en: 'Behavioural NMD (core share and maturity, capped)', es: 'NMD conductual (parte estable y plazo, con tope)' },
  contractual: { en: 'Contractual NMD (all overnight)', es: 'NMD contractual (todo a la vista)' },
};
export const CATEGORY_TEXT: Record<string, Bi> = {
  'retail-transactional': { en: 'Retail transactional', es: 'Minorista transaccional' },
  'retail-non-transactional': { en: 'Retail non-transactional', es: 'Minorista no transaccional' },
  wholesale: { en: 'Wholesale', es: 'Mayorista' },
  'retail-operational': { en: 'Retail operational', es: 'Minorista operacional' },
  'retail-non-operational': { en: 'Retail non-operational', es: 'Minorista no operacional' },
};
export const ORIGIN_TEXT: Record<string, Bi> = {
  'srp31-table-2024': { en: 'Basel SRP31 Table 2 (2024)', es: 'Basilea SRP31 Tabla 2 (2024)' },
  'srp31-table-2016': { en: 'Basel d368 Annex 2 (2016)', es: 'Basilea d368 Anexo 2 (2016)' },
  'cmf-annex1': { en: 'CMF RAN 21-13 Annex 1', es: 'CMF RAN 21-13 Anexo 1' },
  'contraste-estimate': { en: 'Contraste estimate, not a regulatory parameter', es: 'Estimación de Contraste, no un parámetro regulatorio' },
};
export const SOURCE_KIND_TEXT: Record<string, Bi> = {
  'regulatory-cap': { en: 'regulatory cap', es: 'tope regulatorio' },
  fitted: { en: 'fitted', es: 'ajustado' },
  'synthetic-stated': { en: 'synthetic, stated', es: 'sintético, declarado' },
};
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The scenario of a calibration and an NMD assumption, or null when the document carries no such pair. */
export function scenarioOf(o: C14Outputs | null, calibration: string, nmd: string): C14Scenario | null {
  return o?.scenarios.find((s) => s.calibration === calibration && s.nmd_assumption === nmd) ?? null;
}

/** The result of one shock in a scenario, or null. */
export function shockOf(s: C14Scenario | null, shock: string): C14Shock | null {
  return s?.shocks.find((x) => x.shock === shock) ?? null;
}

/** The scenario in focus for a selection. */
export const scenarioFor = (sel: C14Sel | null): C14Scenario | null => scenarioOf(outputsOf(sel), sel?.calibration ?? '', sel?.nmd ?? '');

/** The factor from the document's money scale to units of the currency (thousands: 1,000). */
export function scaleFactor(o: Pick<C14Outputs, 'units'>): number {
  return o.units.money_scale === 'millions' ? 1e6 : o.units.money_scale === 'thousands' ? 1e3 : 1;
}

/** The unit text of a table column of money in the document's scale: "USD thousands". */
export function scaleUnit(o: Pick<C14Outputs, 'units' | 'currency'>): Bi {
  const word = o.units.money_scale === 'millions' ? { en: 'millions', es: 'millones' } : o.units.money_scale === 'thousands' ? { en: 'thousands', es: 'miles' } : null;
  return word ? { en: `${o.currency} ${word.en}`, es: `${word.es} de ${o.currency}` } : { en: o.currency, es: o.currency };
}

/** An amount of the document in a narrow place (a read-out): scaled to units, then to bn or m with the unit that says so. */
export function amount(o: Pick<C14Outputs, 'units' | 'currency'>, v: number | null | undefined) {
  return compactMoney(v === null || v === undefined ? null : v * scaleFactor(o), o.currency);
}

/** The scale of a money axis: the divisor from the document's scale and the unit its title carries. */
export function axisOf(o: Pick<C14Outputs, 'units' | 'currency'>, values: ReadonlyArray<number | null | undefined>) {
  const k = scaleFactor(o);
  const max = Math.max(0, ...values.map((v) => Math.abs(v ?? 0))) * k;
  const s = axisScale(max, o.currency);
  return { div: s.div / k, unit: s.unit };
}

/** A whole amount of a table cell, in the document's scale. */
export const cell = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The NMD categories of the replicating portfolios, in document order, once each. */
export function categoriesOf(fit: C14Fit | null): NmdCategory[] {
  return [...new Set((fit?.nmd_models ?? []).map((m) => m.category))];
}

/** The replicating portfolio of a category at the valuation date of the variant (the first one of the category when no date matches). */
export function nmdModelOf(fit: C14Fit | null, category: string, valuationDate: string | undefined): C14NmdModel | null {
  const rows = (fit?.nmd_models ?? []).filter((m) => m.category === category);
  return rows.find((m) => m.valuation_date === valuationDate) ?? rows[0] ?? null;
}

/** The selection a variant opens on: the 2024 calibration, behavioural NMD, the first shock and the first category. */
export function defaultSel(data: CaseData | null): C14Sel | null {
  if (!data || data.manifest.case_id !== 'C14') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const fit = fitOf({ data });
  return {
    data,
    calibration: o.scenarios[0]?.calibration ?? '2024',
    nmd: 'behavioural',
    shock: o.scenarios[0]?.shocks[0]?.shock ?? 'parallel-up',
    category: categoriesOf(fit)[0] ?? o.nmd_segments[0]?.category ?? 'retail-transactional',
  };
}
