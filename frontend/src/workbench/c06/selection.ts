// The selection the C06 views share, and the readings of a reporting-date variant every view needs. The only
// arithmetic is what the contract itself states: the weighted ECL is the sum of weight times scenario ECL (the staging
// is frozen), so moving a weight re-weights the per-scenario ECLs the document carries; nothing else is computed here.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { testText } from '../names';

export type C06Outputs = components['schemas']['c06Outputs'];
export type C06Fit = components['schemas']['c06Fit'];
export type C06Models = { fit?: C06Fit };

/** The words for the ids the documents carry (U16-R2 b03 B3): never an id inside a Spanish sentence or cell. */
export const COHORT_TEXT: Record<string, { en: string; es: string }> = { all: { en: 'all', es: 'todas' }, older: { en: 'older', es: 'anteriores' } };
/** The tests of the IFRS 9 battery in words (the id stays in the cell's title, never printed as the name). */
export const IFRS9_TEST_TEXT: Record<string, { en: string; es: string }> = {
  'ifrs9.lifetime_pd_backtest': { en: 'Lifetime PD backtest', es: 'Prueba retrospectiva de la PD de vida' },
  'ifrs9.sicr_effectiveness': { en: 'Effectiveness of the stage flag (SICR)', es: 'Efectividad de la marca de etapa (SICR)' },
  'ifrs9.sicr_threshold_stability': { en: 'Stability of the SICR threshold', es: 'Estabilidad del umbral de SICR' },
  'ifrs9.stage_migration_backtest': { en: 'Stage migration backtest', es: 'Prueba retrospectiva de la migración de etapas' },
  'ifrs9.ecl_backtest': { en: '12-month ECL backtest', es: 'Prueba retrospectiva de la PCE a 12 meses' },
  'ifrs9.scenario_sensitivity': { en: 'Sensitivity to the scenarios', es: 'Sensibilidad a los escenarios' },
  'ifrs9.nonlinearity': { en: 'Nonlinearity of the ECL in the scenario weights', es: 'No linealidad de la PCE en los pesos de escenarios' },
  'ifrs9.overlay_diagnostics': { en: 'Overlay diagnostics', es: 'Diagnóstico de los ajustes' },
  'ifrs9.reconciliation_identities': { en: 'Reconciliation identities', es: 'Identidades de conciliación' },
};
export const ifrs9TestText = (id: string): { en: string; es: string } => IFRS9_TEST_TEXT[id] ?? testText(id);
export const cohortText = (id: string): { en: string; es: string } => COHORT_TEXT[id] ?? { en: id, es: id };
export const MOVEMENT_TEXT: Record<string, { en: string; es: string }> = {
  originations: { en: 'originations', es: 'originaciones' },
  derecognition: { en: 'derecognition', es: 'baja en cuentas' },
  'write-off': { en: 'write-off', es: 'castigo' },
  repayments: { en: 'repayments', es: 'amortizaciones' },
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

/** The sector groups of the fit by the first two digits of the NAICS code (``data-pipeline/pipeline/cases/c06/panel.py``
 * SECTOR_GROUPS, from the SBA file's NAICS field), in words. */
const SECTOR_TEXT: Record<string, { en: string; es: string }> = {
  agriculture: { en: 'Agriculture', es: 'Agricultura' },
  'mining-utilities-construction': { en: 'Mining, utilities and construction', es: 'Minería, servicios básicos y construcción' },
  manufacturing: { en: 'Manufacturing', es: 'Manufactura' },
  wholesale: { en: 'Wholesale trade', es: 'Comercio mayorista' },
  retail: { en: 'Retail trade', es: 'Comercio minorista' },
  transport: { en: 'Transport and warehousing', es: 'Transporte y almacenamiento' },
  'information-finance-professional': { en: 'Information, finance and professional services', es: 'Información, finanzas y servicios profesionales' },
  'education-health': { en: 'Education and health care', es: 'Educación y salud' },
  'arts-recreation': { en: 'Arts and recreation', es: 'Artes y recreación' },
  'accommodation-food': { en: 'Accommodation and food services', es: 'Alojamiento y servicios de comida' },
  'other-services': { en: 'Other services', es: 'Otros servicios' },
  'other-unknown': { en: 'Other or unknown sector', es: 'Sector otro o desconocido' },
};
/** The macro covariates of the hazard rung (the names C18 gives the same series). */
const MACRO_TEXT: Record<string, { en: string; es: string }> = {
  unemployment_rate: { en: 'Unemployment rate', es: 'Tasa de desempleo' },
  real_gdp_growth: { en: 'Real GDP growth', es: 'Crecimiento del PIB real' },
  prime_rate: { en: 'Prime rate', es: 'Tasa preferencial' },
};
const usd = (k: string, lang: 'en' | 'es') => `USD ${formatNumber(Number(k) * 1000, lang, { decimals: 0 })}`;

/**
 * A covariate code of the fit (``c06/ladder.py``: size, term and age bands, the sector groups, the revolving flag, the macro
 * series) in words (R3 c07 B3: the disclosure printed ``size_50k_150k``, ``sector_retail``, ``unemployment_rate``). A code
 * the patterns do not know is returned as written, so a new covariate is seen, not hidden.
 */
export function covariateText(code: string): { en: string; es: string } {
  if (MACRO_TEXT[code]) return MACRO_TEXT[code];
  if (code === 'revolver') return { en: 'Revolving line', es: 'Línea revolvente' };
  if (code.startsWith('sector_') && SECTOR_TEXT[code.slice(7)]) return SECTOR_TEXT[code.slice(7)];
  let m = /^size_(\d+)k_(\d+)k$/.exec(code);
  if (m) return { en: `Size ${usd(m[1], 'en')} to ${formatNumber(Number(m[2]) * 1000, 'en', { decimals: 0 })}`, es: `Monto ${usd(m[1], 'es')} a ${formatNumber(Number(m[2]) * 1000, 'es', { decimals: 0 })}` };
  m = /^size_over_(\d+)k$/.exec(code);
  if (m) return { en: `Size above ${usd(m[1], 'en')}`, es: `Monto sobre ${usd(m[1], 'es')}` };
  m = /^term_(\d+)_(\d+)$/.exec(code);
  if (m) return { en: `Term ${m[1]} to ${m[2]} months`, es: `Plazo de ${m[1]} a ${m[2]} meses` };
  m = /^term_over_(\d+)$/.exec(code);
  if (m) return { en: `Term over ${m[1]} months`, es: `Plazo sobre ${m[1]} meses` };
  m = /^age_q_(\d+)_(\d+)$/.exec(code);
  if (m) return { en: `Loan age ${m[1]} to ${m[2]} quarters`, es: `Antigüedad de ${m[1]} a ${m[2]} trimestres` };
  m = /^age_q_(\d+)_plus$/.exec(code);
  if (m) return { en: `Loan age ${m[1]} quarters or more`, es: `Antigüedad de ${m[1]} trimestres o más` };
  return { en: code, es: code };
}

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
