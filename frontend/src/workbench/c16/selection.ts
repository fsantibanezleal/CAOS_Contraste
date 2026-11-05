// The selection the C16 views share, and the readings of a scenario or reverse-stress document every view needs. Nothing
// here computes a statistic: the ladder, the survival periods, the LCR, the CBC, the sensitivities and the solved
// multipliers are the bake's; the helpers find, name and map. A survival period is a day count, or "survives the horizon"
// with the horizon, and no helper turns the second into a number (the survival convention). Money is in USD thousands as
// the FDIC call report gives it; a narrow place scales it to bn or m with the unit that says so.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { compactMoney, axisScale } from '../c06/format';

export type C16Outputs = components['schemas']['c16Outputs'];
export type C16Reverse = components['schemas']['c16ReverseOutputs'];
export type C16Fit = components['schemas']['c16Fit'];
export type C16Survival = components['schemas']['c16Survival'];
export type C16Base = components['schemas']['c16ReverseBase'];
export type C16A1Score = components['schemas']['c16A1Score'];
export type C16Denominator = components['schemas']['c16Denominator'];
export type C16Item = components['schemas']['c16Item'];
export type C16Label = components['schemas']['c16Label'];

export type DenominatorId = C16Denominator['id'];
export type A1RowId = C16A1Score['row_id'];
export type BaseId = C16Base['base_id'];

export interface C16Sel {
  data: CaseData;
  /** The day of the ladder in focus (a scenario variant with a daily path). */
  day: number;
  /** The denominator of the realised run the comparison is drawn against. */
  denominator: DenominatorId;
  /** The Table A.1 row in focus. */
  row: A1RowId;
  /** The mapping of the uninsured balance to an LCR category in focus (the LCR variant). */
  mapping: string;
  /** The base scenario of the reverse stress in focus. */
  base: BaseId;
  /** The index of the point of the SP(m) curve in focus. */
  point: number;
}

/** The outputs of the selected variant, or null when it is not a scenario document. */
export function outputsOf(sel: Pick<C16Sel, 'data'> | null): C16Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'scenario' ? (out as C16Outputs) : null;
}

/** The outputs of the selected variant, or null when it is not the reverse-stress document. */
export function reverseOf(sel: Pick<C16Sel, 'data'> | null): C16Reverse | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'reverse-stress' ? (out as C16Reverse) : null;
}

/** The fit of the C16 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C16Sel, 'data'> | null): C16Fit | null {
  return (sel?.data.models as unknown as { fit?: C16Fit } | undefined)?.fit ?? null;
}

export const DENOMINATORS: readonly DenominatorId[] = ['board-stated-share', 'call-report-dep'];
export const DENOMINATOR_SHORT: Record<string, Bi> = {
  'board-stated-share': { en: 'Board share', es: 'Parte de la Junta' },
  'call-report-dep': { en: 'Call report DEP', es: 'DEP del reporte' },
};
export const DENOMINATOR_LONG: Record<string, Bi> = {
  'board-stated-share': { en: 'The Federal Reserve review: roughly 85 percent of the deposit base left in about two days', es: 'La revisión de la Reserva Federal: cerca de 85 por ciento de la base de depósitos salió en cerca de dos días' },
  'call-report-dep': { en: 'The same outflow over the call report\'s DEP of 2022-12-31: 40 plus 100 billion USD', es: 'La misma salida sobre el DEP del reporte al 2022-12-31: 40 más 100 mil millones de USD' },
};
export const COMPARED_AT_TEXT: Record<string, Bi> = {
  'event-horizon': { en: 'at the event horizon', es: 'en el horizonte del evento' },
  'model-horizon': { en: 'at the model horizon', es: 'en el horizonte del modelo' },
};
export const ROLE_TEXT: Record<string, Bi> = {
  calibration: { en: 'calibration', es: 'calibración' },
  scored: { en: 'scored', es: 'evaluada' },
  reference: { en: 'reference only', es: 'solo referencia' },
};
export const BASE_ORDER: readonly BaseId[] = ['list-adverse', 'list-extreme', 'fast-run'];
export const BASE_TEXT: Record<string, Bi> = {
  'list-adverse': { en: 'LiST adverse', es: 'LiST adverso' },
  'list-extreme': { en: 'LiST extreme', es: 'LiST extremo' },
  'fast-run': { en: '2023 fast run', es: 'Corrida rápida 2023' },
};
export const SEGMENT_TEXT: Record<string, Bi> = {
  'retail-insured': { en: 'Retail, insured', es: 'Minorista asegurado' },
  'retail-uninsured': { en: 'Retail, uninsured', es: 'Minorista no asegurado' },
  operational: { en: 'Operational', es: 'Operacional' },
  'non-operational-corporate': { en: 'Non-operational corporate', es: 'Corporativo no operacional' },
  financial: { en: 'Financial', es: 'Financiero' },
};
export const CLASS_TEXT: Record<string, Bi> = {
  'cash-and-balances': { en: 'Cash and balances', es: 'Efectivo y saldos' },
  treasury: { en: 'Treasury', es: 'Tesoro' },
  'mortgage-backed': { en: 'Mortgage-backed', es: 'Respaldados por hipotecas' },
  'other-agency': { en: 'Other agency', es: 'Otras agencias' },
  municipal: { en: 'Municipal', es: 'Municipales' },
  'other-debt': { en: 'Other debt', es: 'Otra deuda' },
};
export const HAIRCUT_RULE_TEXT: Record<string, Bi> = {
  'nominal-value': { en: 'nominal value', es: 'valor nominal' },
  'central-bank-framework': { en: 'central bank framework', es: 'marco del banco central' },
  'lcr-haircut-hqla': { en: 'LCR haircut, HQLA', es: 'recorte LCR, HQLA' },
  'fifty-percent-fallback': { en: '50 percent fallback', es: 'recurso de 50 por ciento' },
  'ecb-equity-table': { en: 'ECB equity table', es: 'tabla de acciones del BCE' },
  'ecb-non-equity-hqla': { en: 'ECB non-equity, HQLA', es: 'BCE no acciones, HQLA' },
};
export const SOURCE_KIND_TEXT: Record<string, Bi> = {
  'transcribed-list-2019': { en: 'transcribed, ECB LiST 2019', es: 'transcrito, BCE LiST 2019' },
  'transcribed-basel-lcr': { en: 'transcribed, Basel LCR', es: 'transcrito, LCR de Basilea' },
  'calibrated-pre-2023': { en: 'calibrated on pre-2023 rows', es: 'calibrado con filas anteriores a 2023' },
  convention: { en: 'convention', es: 'convención' },
  'synthetic-stated': { en: 'synthetic, stated', es: 'sintético, declarado' },
  'scenario-input': { en: 'scenario input', es: 'insumo del escenario' },
};
export const FAMILY_TEXT: Record<string, Bi> = {
  idiosyncratic: { en: 'idiosyncratic', es: 'idiosincrático' },
  'market-wide': { en: 'market-wide', es: 'de todo el mercado' },
  combined: { en: 'combined', es: 'combinado' },
};
export const PHASE_TEXT: Record<string, Bi> = {
  acute: { en: 'acute', es: 'aguda' },
  protracted: { en: 'protracted', es: 'prolongada' },
  'lcr-30-day': { en: '30-day LCR stress', es: 'estrés LCR a 30 días' },
};
/** The scenario family and phase of a variant in one phrase; the Spanish names the phase ("idiosincrático, fase prolongada"), as the two nouns differ in gender (U16-R2 b08 m8). */
export function scenarioPhrase(family: string, phase: string, lang: 'en' | 'es'): string {
  const f = (FAMILY_TEXT[family] ?? { en: family, es: family })[lang];
  const p = (PHASE_TEXT[phase] ?? { en: phase, es: phase })[lang];
  return lang === 'es' ? `${f}, fase ${p}` : `${f}, ${p}`;
}
export const LCR_CATEGORY_TEXT: Record<string, Bi> = {
  retail_stable_insurance_criteria: { en: 'Retail stable, insurance criteria', es: 'Minorista estable, criterios del seguro' },
  retail_stable: { en: 'Retail stable', es: 'Minorista estable' },
  retail_less_stable: { en: 'Retail less stable', es: 'Minorista menos estable' },
  retail_term_gt_30d: { en: 'Retail term over 30 days', es: 'Minorista a plazo sobre 30 días' },
  small_business_stable: { en: 'Small business stable', es: 'Pequeña empresa estable' },
  small_business_less_stable: { en: 'Small business less stable', es: 'Pequeña empresa menos estable' },
  operational: { en: 'Operational deposits', es: 'Depósitos operacionales' },
  operational_insured_portion: { en: 'Operational, insured portion', es: 'Operacional, parte asegurada' },
  cooperative_network: { en: 'Cooperative network', es: 'Red cooperativa' },
  non_financial_corporate: { en: 'Non-financial corporates', es: 'Corporativos no financieros' },
  non_financial_corporate_fully_insured: { en: 'Non-financial corporates, fully insured', es: 'Corporativos no financieros, totalmente asegurados' },
  other_legal_entity: { en: 'Other legal entities', es: 'Otras personas jurídicas' },
  secured_central_bank: { en: 'Secured, central bank', es: 'Garantizado, banco central' },
  secured_level1: { en: 'Secured, Level 1', es: 'Garantizado, Nivel 1' },
  secured_level2a: { en: 'Secured, Level 2A', es: 'Garantizado, Nivel 2A' },
  secured_sovereign_mdb_pse: { en: 'Secured, sovereign, MDB or PSE', es: 'Garantizado, soberano, BMD o entidad pública' },
  secured_level2b_rmbs: { en: 'Secured, Level 2B RMBS', es: 'Garantizado, RMBS de Nivel 2B' },
  secured_other_level2b: { en: 'Secured, other Level 2B', es: 'Garantizado, otro Nivel 2B' },
  secured_other: { en: 'Secured, other', es: 'Garantizado, otro' },
  non_level1_collateral_valuation: { en: 'Valuation changes, non-Level 1 collateral', es: 'Cambios de valor, garantías fuera del Nivel 1' },
  undrawn_retail_small_business: { en: 'Undrawn, retail and small business', es: 'No utilizado, minorista y pequeña empresa' },
  undrawn_credit_non_financial_corporate: { en: 'Undrawn credit, non-financial corporates', es: 'Crédito no utilizado, corporativos no financieros' },
  undrawn_liquidity_non_financial_corporate: { en: 'Undrawn liquidity, non-financial corporates', es: 'Liquidez no utilizada, corporativos no financieros' },
  undrawn_credit_supervised_bank: { en: 'Undrawn credit, supervised banks', es: 'Crédito no utilizado, bancos supervisados' },
  undrawn_liquidity_supervised_bank: { en: 'Undrawn liquidity, supervised banks', es: 'Liquidez no utilizada, bancos supervisados' },
  undrawn_credit_other_fi: { en: 'Undrawn credit, other financial institutions', es: 'Crédito no utilizado, otras instituciones financieras' },
  undrawn_liquidity_other_fi: { en: 'Undrawn liquidity, other financial institutions', es: 'Liquidez no utilizada, otras instituciones financieras' },
  undrawn_other_legal_entity: { en: 'Undrawn, other legal entities', es: 'No utilizado, otras personas jurídicas' },
  net_derivative_outflow: { en: 'Net derivative outflow', es: 'Salida neta de derivados' },
  other_contractual_outflow: { en: 'Other contractual outflows', es: 'Otras salidas contractuales' },
  trade_finance: { en: 'Trade finance', es: 'Financiamiento de comercio' },
  secured_lending_level1: { en: 'Maturing secured lending, Level 1', es: 'Préstamos garantizados que vencen, Nivel 1' },
  secured_lending_level2a: { en: 'Maturing secured lending, Level 2A', es: 'Préstamos garantizados que vencen, Nivel 2A' },
  secured_lending_level2b_rmbs: { en: 'Maturing secured lending, Level 2B RMBS', es: 'Préstamos garantizados que vencen, RMBS de Nivel 2B' },
  secured_lending_other_level2b: { en: 'Maturing secured lending, other Level 2B', es: 'Préstamos garantizados que vencen, otro Nivel 2B' },
  secured_lending_other: { en: 'Maturing secured lending, other collateral', es: 'Préstamos garantizados que vencen, otras garantías' },
  margin_lending_other_collateral: { en: 'Margin lending, other collateral', es: 'Préstamos con margen, otras garantías' },
  facilities_granted_to_bank: { en: 'Facilities granted to the bank', es: 'Líneas otorgadas al banco' },
  operational_deposits_at_other_institutions: { en: 'Operational deposits at other institutions', es: 'Depósitos operacionales en otras instituciones' },
  retail_and_nonfinancial_wholesale: { en: 'Retail and non-financial wholesale inflows', es: 'Entradas minoristas y mayoristas no financieras' },
  financial_institutions_and_central_banks: { en: 'Financial institutions and central banks', es: 'Instituciones financieras y bancos centrales' },
  net_derivative_inflow: { en: 'Net derivative inflow', es: 'Entrada neta de derivados' },
};
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

type Lang = 'en' | 'es';

/**
 * A survival period in words: "day 48", or "survives the 125-day horizon". Never a number for the second: a variant that
 * survives its horizon has no survival day, only the horizon it survived. A missing period is the shell's "not available".
 */
export function survivalText(s: Pick<C16Survival, 'kind' | 'day' | 'horizon_days'> | null | undefined, lang: Lang): string {
  if (!s) return formatNumber(null, lang);
  if (s.kind === 'day' && s.day !== null) return lang === 'es' ? `día ${s.day}` : `day ${s.day}`;
  return lang === 'es' ? `sobrevive el horizonte de ${s.horizon_days} días` : `survives the ${s.horizon_days}-day horizon`;
}

/** The survival period when it is a day, or null when the bank survives its horizon (a chart draws no point for it). */
export const survivalDay = (s: Pick<C16Survival, 'kind' | 'day'> | null | undefined): number | null => (s && s.kind === 'day' ? s.day : null);

/** The money fields are USD thousands: a read-out scales to units first, then to bn or m with the unit that says so. */
export function amount(v: number | null | undefined, currency = 'USD') {
  return compactMoney(v === null || v === undefined ? null : v * 1000, currency);
}
/** The scale of a money axis in USD thousands: the divisor from the thousands and the unit its title carries. */
export function axisOf(values: ReadonlyArray<number | null | undefined>, currency = 'USD') {
  const max = Math.max(0, ...values.map((v) => Math.abs(v ?? 0))) * 1000;
  const s = axisScale(max, currency);
  return { div: s.div / 1000, unit: s.unit };
}

export const ladderOf = (o: C16Outputs | null) => o?.path?.ladder ?? null;

/** The first day of the ladder and its last, or null when the variant has no daily path. */
export function dayRange(o: C16Outputs | null): { min: number; max: number } | null {
  const days = ladderOf(o)?.day_index;
  return days && days.length ? { min: days[0], max: days[days.length - 1] } : null;
}

/** The index in the ladder of a day (the ladder is columnar: one value per day), or -1. */
export const dayIndex = (o: C16Outputs | null, day: number): number => ladderOf(o)?.day_index.indexOf(day) ?? -1;

/** The score row of the Table A.1 in focus, or null. */
export const rowOf = (o: C16Outputs | null, id: string): C16A1Score | null => o?.scoring.table_a1_scoring.find((r) => r.row_id === id) ?? null;
export const denominatorOf = (o: C16Outputs | null, id: string): C16Denominator | null => o?.scoring.denominators.find((d) => d.id === id) ?? null;
export const baseOf = (r: C16Reverse | null, id: string): C16Base | null => r?.bases.find((b) => b.base_id === id) ?? null;

/** The selection a variant opens on: the survival day (or the first day), the Board denominator, the SVB row, the central mapping, the first base. */
export function defaultSel(data: CaseData | null): C16Sel | null {
  if (!data || data.manifest.case_id !== 'C16') return null;
  const o = outputsOf({ data });
  const r = reverseOf({ data });
  if (!o && !r) return null;
  const range = dayRange(o);
  const sday = survivalDay(o?.path?.survival);
  return {
    data,
    day: sday ?? range?.min ?? 1,
    denominator: 'board-stated-share',
    row: 'svb-2023',
    mapping: o?.lcr?.mapping_sensitivity[0]?.mapping_id ?? 'central',
    base: r?.bases[0]?.base_id ?? 'list-adverse',
    point: 0,
  };
}
