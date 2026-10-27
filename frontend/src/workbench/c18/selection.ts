// The selection the C18 views share, and the readings of a scenario, aggregation or reverse-stress document every view needs.
// Nothing here computes a statistic: the satellite projections, the losses, the capital plan, the band, the Euler allocation
// and the solved scenario are the bake's; the helpers find, name and map. Money is CLP millions as the documents give it; a
// narrow place scales it to bn with the unit that says so. The headline capital of C18 is the simple sum and every other
// aggregate is information for the validator, never capital: the words for both live here so every view says the same.
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { compactMoney, axisScale } from '../c06/format';

export type C18Outputs = components['schemas']['c18Outputs'];
export type C18AggOutputs = components['schemas']['c18AggOutputs'];
export type C18Reverse = components['schemas']['c18RevOutputs'];
export type C18Fit = components['schemas']['c18Fit'];
export type C18Aggregation = components['schemas']['c18Aggregation'];
export type C18PlanCase = components['schemas']['c18PlanCase'];
export type C18PlanYear = components['schemas']['c18PlanYear'];
export type C18BandRow = components['schemas']['c18BandRow'];
export type C18Path = components['schemas']['c18Path'];
export type C18Cell = components['schemas']['c18Cell'];
export type C18SatFit = components['schemas']['c18SatFit'];
export type C18Backcast = components['schemas']['c18Backcast']['per_loan_type'][number];

export type PlanCaseId = C18PlanCase['case'];
export type LoanId = C18SatFit['fed_loan_type'];
export type RiskId = components['schemas']['c18Euler']['allocation'][number]['risk'];
export type MethodId = C18BandRow['method'];

export const PLAN_ORDER: readonly PlanCaseId[] = ['base', 'stress-without-mitigation', 'stress-with-mitigation'];
export const LOAN_ORDER: readonly LoanId[] = ['commercial-industrial', 'commercial-real-estate', 'residential', 'credit-cards', 'other-consumer'];
export const RISK_ORDER: readonly RiskId[] = ['credit', 'market', 'irrbb', 'operational'];

export interface C18Sel {
  data: CaseData;
  /** The year of the three-year projection in focus (1 to 3). */
  year: number;
  /** The index of the scenario path in focus. */
  path: number;
  /** The Federal Reserve loan type in focus (satellites and back-cast). */
  loan: LoanId;
  /** The risk in focus (the marginals, the Euler allocation). */
  risk: RiskId;
  /** The correlation matrix of the aggregation variant in focus: the base matrix or the market-credit 0.8 stress. */
  matrix: 'base' | 'stress';
  /** The index of the row of the band in focus. */
  row: number;
  /** The index of the factor of the reverse stress in focus. */
  factor: number;
  /** The start of the reverse-stress search in focus. */
  start: string;
}

type Kinded = { data: CaseData } | null;
const outputsRaw = (sel: Kinded) => (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;

/** The outputs of the selected variant when it is a scenario document, else null. */
export function outputsOf(sel: Kinded): C18Outputs | null {
  const out = outputsRaw(sel);
  return out && out.kind === 'scenario' ? (out as C18Outputs) : null;
}
/** The outputs of the selected variant when it is the t-copula aggregation document, else null. */
export function aggDocOf(sel: Kinded): C18AggOutputs | null {
  const out = outputsRaw(sel);
  return out && out.kind === 'aggregation' ? (out as C18AggOutputs) : null;
}
/** The outputs of the selected variant when it is the reverse-stress document, else null. */
export function reverseOf(sel: Kinded): C18Reverse | null {
  const out = outputsRaw(sel);
  return out && out.kind === 'reverse' ? (out as C18Reverse) : null;
}
/** The fit of the C18 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Kinded): C18Fit | null {
  return (sel?.data.models as unknown as { fit?: C18Fit } | undefined)?.fit ?? null;
}
/** The aggregation block in focus: a scenario variant's own, or the aggregation variant's base or stressed matrix. */
export function aggOf(sel: (Kinded & { matrix?: 'base' | 'stress' }) | null): C18Aggregation | null {
  const s = outputsOf(sel);
  if (s) return s.aggregation;
  const a = aggDocOf(sel);
  if (!a) return null;
  return sel?.matrix === 'stress' ? a.correlation_stress.aggregation : a.aggregation;
}

export const planOf = (o: C18Outputs | null, id: PlanCaseId): C18PlanCase | null => o?.capital_plan.cases.find((c) => c.case === id) ?? null;
export const yearOf = (c: C18PlanCase | null, year: number): C18PlanYear | null => c?.years.find((y) => y.year === year) ?? null;
export const satFitOf = (fit: C18Fit | null, loan: string): C18SatFit | null => fit?.satellites.find((s) => s.fed_loan_type === loan) ?? null;
export const backcastOf = (o: C18Outputs | null, loan: string): C18Backcast | null => o?.backcast.per_loan_type.find((b) => b.fed_loan_type === loan) ?? null;
export const marginalOf = (a: C18Aggregation | null, risk: string) => a?.marginals.find((m) => m.risk === risk) ?? null;

/** The selection a variant opens on: year 1, the first path, the first loan type, credit, the base matrix, the first band row. */
export function defaultSel(data: CaseData | null): C18Sel | null {
  if (!data || data.manifest.case_id !== 'C18') return null;
  const r = reverseOf({ data });
  const o = outputsOf({ data });
  const a = aggDocOf({ data });
  if (!o && !a && !r) return null;
  return { data, year: 1, path: 0, loan: 'commercial-industrial', risk: 'credit', matrix: 'base', row: 0, factor: 0, start: r?.starts[0]?.start_id ?? 'start-0' };
}

// --- the words -------------------------------------------------------------------------------------------------------

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

export const PLAN_TEXT: Record<string, Bi> = {
  base: { en: 'Base', es: 'Base' },
  'stress-without-mitigation': { en: 'Stress, no mitigation', es: 'Estrés sin mitigación' },
  'stress-with-mitigation': { en: 'Stress, with mitigation', es: 'Estrés con mitigación' },
};
export const PLAN_LONG: Record<string, Bi> = {
  base: { en: 'The ordinary plan: the base scenario over the three years of the planning period', es: 'El plan ordinario: el escenario base en los tres años del periodo de planificación' },
  'stress-without-mitigation': { en: 'The scenario with the losses taken and no action of the bank', es: 'El escenario con las pérdidas asumidas y sin acción del banco' },
  'stress-with-mitigation': { en: 'The scenario with the mitigation actions of the plan', es: 'El escenario con las acciones de mitigación del plan' },
};
export const LOAN_TEXT: Record<string, Bi> = {
  'commercial-industrial': { en: 'Commercial and industrial', es: 'Comercial e industrial' },
  'commercial-real-estate': { en: 'Commercial real estate', es: 'Inmobiliario comercial' },
  residential: { en: 'Residential real estate', es: 'Inmobiliario residencial' },
  'credit-cards': { en: 'Credit cards', es: 'Tarjetas de crédito' },
  'other-consumer': { en: 'Other consumer', es: 'Otro consumo' },
};
export const CLASS_TEXT: Record<string, Bi> = {
  commercial: { en: 'Commercial', es: 'Comercial' },
  consumer: { en: 'Consumer', es: 'Consumo' },
  mortgage: { en: 'Mortgage', es: 'Hipotecario' },
};
export const RISK_TEXT: Record<string, Bi> = {
  credit: { en: 'Credit', es: 'Crédito' },
  market: { en: 'Market', es: 'Mercado' },
  irrbb: { en: 'IRRBB', es: 'IRRBB' },
  operational: { en: 'Operational', es: 'Operacional' },
  total: { en: 'Total', es: 'Total' },
};
export const REGRESSOR_TEXT: Record<string, Bi> = {
  real_gdp_growth: { en: 'Real GDP growth', es: 'Crecimiento del PIB real' },
  unemployment_rate: { en: 'Unemployment rate', es: 'Tasa de desempleo' },
  cpi_inflation: { en: 'CPI inflation', es: 'Inflación del IPC' },
  treasury_3m: { en: '3-month Treasury rate', es: 'Tasa del Tesoro a 3 meses' },
  treasury_5y: { en: '5-year Treasury rate', es: 'Tasa del Tesoro a 5 años' },
  treasury_10y: { en: '10-year Treasury rate', es: 'Tasa del Tesoro a 10 años' },
  mortgage_rate: { en: 'Mortgage rate', es: 'Tasa hipotecaria' },
  prime_rate: { en: 'Prime rate', es: 'Tasa preferencial' },
};
export const PROVIDER_TEXT: Record<string, Bi> = {
  fed: { en: 'Federal Reserve', es: 'Reserva Federal' },
  'eba-esrb': { en: 'EBA and ESRB', es: 'EBA y ESRB' },
  ngfs: { en: 'NGFS', es: 'NGFS' },
};
export const LINK_TEXT: Record<string, Bi> = {
  probit: { en: 'probit', es: 'probit' },
  logit: { en: 'logit', es: 'logit' },
  identity: { en: 'identity (a signed rate)', es: 'identidad (una tasa con signo)' },
};
export const LEVEL_RULE_TEXT: Record<string, Bi> = {
  level: { en: 'the published level', es: 'el nivel publicado' },
  'baseline-plus-deviation': { en: 'baseline plus the published deviation', es: 'línea base más la desviación publicada' },
  'baseline-times-percent-deviation': { en: 'baseline times the published percent deviation', es: 'línea base por la desviación porcentual publicada' },
};
export const LABEL_TEXT: Record<string, Bi> = {
  convention: { en: 'convention', es: 'convención' },
  'case assumption': { en: 'case assumption', es: 'supuesto del caso' },
  'us-calibrated-adaptation': { en: 'US-calibrated adaptation', es: 'adaptación calibrada en EE. UU.' },
  'contraste-approximation': { en: 'Contraste approximation', es: 'aproximación de Contraste' },
  'ppnr-labelled-row': { en: 'labelled row', es: 'fila rotulada' },
  'rate-only-descriptive': { en: 'rate only, descriptive, no forecast claim', es: 'solo tasa, descriptiva, sin pretensión de pronóstico' },
};
export const REQUIREMENT_TEXT: Record<string, Bi> = {
  'internal-target': { en: 'internal target (OI)', es: 'objetivo interno (OI)' },
  'legal-minimum': { en: 'legal minimum', es: 'mínimo legal' },
};
export const CELL_TEXT: Record<string, Bi> = {
  RI: { en: 'RI (immaterial risk)', es: 'RI (riesgo inmaterial)' },
  'not-to-be-filled': { en: 'not to be filled', es: 'no debe llenarse' },
  'not-applicable': { en: 'not applicable', es: 'no aplica' },
};
export const METHOD_TEXT: Record<string, Bi> = {
  'lower-bound': { en: 'Lower bound under dependence uncertainty', es: 'Cota inferior bajo incertidumbre de dependencia' },
  'simple-sum': { en: 'Simple sum, the headline', es: 'Suma simple, la cifra principal' },
  'variance-covariance': { en: 'Variance-covariance', es: 'Varianza-covarianza' },
  'gaussian-copula': { en: 'Gaussian copula', es: 'Cópula gaussiana' },
  'worst-case': { en: 'Worst case under dependence uncertainty', es: 'Peor caso bajo incertidumbre de dependencia' },
};
/** A row of the band in words: the t copula carries its degrees of freedom. */
export function methodText(r: { method: string; nu: number | null }): Bi {
  if (r.method === 't-copula') {
    const nu = r.nu === null ? '' : String(r.nu);
    return { en: `Student t copula, ${nu} degrees of freedom`, es: `Cópula t de Student, ${nu} grados de libertad` };
  }
  return text(METHOD_TEXT, r.method);
}
/** The short form for a select or a chart row. */
export function methodShort(r: { method: string; nu: number | null }): Bi {
  if (r.method === 't-copula') return { en: `t copula, ν ${r.nu}`, es: `Cópula t, ν ${r.nu}` };
  const map: Record<string, Bi> = {
    'lower-bound': { en: 'Lower bound', es: 'Cota inferior' },
    'simple-sum': { en: 'Simple sum (headline)', es: 'Suma simple (principal)' },
    'variance-covariance': { en: 'Variance-covariance', es: 'Varianza-covarianza' },
    'gaussian-copula': { en: 'Gaussian copula', es: 'Cópula gaussiana' },
    'worst-case': { en: 'Worst case', es: 'Peor caso' },
  };
  return text(map, r.method);
}

/** Said wherever a diversified or bound figure is drawn: it is information for the validator and never the capital. */
export const NOT_CAPITAL: Bi = {
  en: 'Information, not capital: only the simple sum is the capital of this case.',
  es: 'Información, no capital: solo la suma simple es el capital de este caso.',
};
export const US_ADAPTATION: Bi = {
  en: 'US-calibrated adaptation transposed onto Banco Andino: the paths and the satellites are United States ones, shaped onto the last observed value of the synthetic bank.',
  es: 'Adaptación calibrada en EE. UU. transpuesta a Banco Andino: las trayectorias y los satélites son de Estados Unidos, llevados al último valor observado del banco sintético.',
};
export const P2G_LABEL: Bi = {
  en: 'A Contraste approximation: the CMF calibration of the P2G is not public.',
  es: 'Una aproximación de Contraste: la calibración de la P2G de la CMF no es pública.',
};
export const MONEY_UNIT: Bi = { en: 'CLP millions', es: 'millones de CLP' };

/** The money fields are CLP millions: a narrow place scales to units first, then to bn with the unit that says so. */
export function amount(v: number | null | undefined, currency = 'CLP') {
  return compactMoney(v === null || v === undefined ? null : v * 1e6, currency);
}
/** The scale of a money axis in CLP millions: the divisor from the millions and the unit its title carries. */
export function axisOf(values: ReadonlyArray<number | null | undefined>, currency = 'CLP') {
  const max = Math.max(0, ...values.map((v) => Math.abs(v ?? 0))) * 1e6;
  const s = axisScale(max, currency);
  return { div: s.div / 1e6, unit: s.unit };
}

/** The Spanish names of the rows of the summary table of Annex 3, with their accents (the CMF's own labels are written without them). */
export const ANNEX3_ES: Record<string, string> = {
  '1': 'Ratios de capital', '1.1': 'PE / APR', '1.2': 'T1 / APR', '1.3': 'CET1 / APR', '2': 'Patrimonio efectivo', '2.T2': 'T2', '2.AT1': 'AT1', '2.CET1': 'CET1',
  '3': 'APR', '4': 'Cuantificación del capital necesario', '4.1': 'Riesgo de crédito', '4.1.1': 'Método estándar', '4.1.2': 'Modelo interno',
  '4.2': 'Riesgo de mercado (ME)', '4.3': 'Riesgo operacional (ME)', '4.4': 'Riesgo de concentración', '4.4.1': 'Individual', '4.4.2': 'Sectorial',
  '4.4.3': 'Otro tipo', '4.5': 'RMLB', '4.6': 'Riesgo estratégico', '4.7': 'Riesgo reputacional', '4.8': 'Otros riesgos materiales', '5': 'OI',
  '6': 'Cuantificación del capital necesario por riesgos no cubiertos en el pilar 1 (4.4+4.5+4.6+4.7+4.8)',
  '7': 'Exigencia mínima de PE, en período de planificación (8%+7.1+7.2)',
  '7.1': 'Exigencia adicional de PE por art. 66 quater (banco sistémico)', '7.2': 'Exigencia adicional de PE por art. 66 quinquies',
  '8': 'Cuantificación del capital necesario por riesgos no cubiertos en el pilar 1 y no exigidos por el art. 66 quinquies (6-7.2)',
  '9': 'Colchones de conservación y contracíclico, en período de planificación (art. 66 bis y 66 ter)',
  '10.1': 'Impacto en el índice de capital básico de las pruebas de tensión severas, sin mitigación',
  '10.2': 'Impacto en el índice de capital básico de las pruebas de tensión severas, con mitigación',
  '11': 'Componente d) del OI', '12': 'Holgura del índice de patrimonio efectivo respecto del OI (1.1 - 5)',
};

/** The English names of the 34 rows of the summary table of Annex 3; the Spanish is the CMF's own label as the document carries it. */
export const ANNEX3_EN: Record<string, string> = {
  '1': 'Capital ratios',
  '1.1': 'Effective equity over RWA (PE / APR)',
  '1.2': 'Tier 1 over RWA (T1 / APR)',
  '1.3': 'CET1 over RWA (CET1 / APR)',
  '2': 'Effective equity (PE)',
  '2.T2': 'Tier 2 (T2)',
  '2.AT1': 'Additional Tier 1 (AT1)',
  '2.CET1': 'CET1',
  '3': 'Risk-weighted assets (APR)',
  '4': 'Quantification of the capital needed',
  '4.1': 'Credit risk',
  '4.1.1': 'Standardised method',
  '4.1.2': 'Internal model',
  '4.2': 'Market risk (standardised)',
  '4.3': 'Operational risk (standardised)',
  '4.4': 'Concentration risk',
  '4.4.1': 'Individual',
  '4.4.2': 'Sectoral',
  '4.4.3': 'Other kind',
  '4.5': 'Interest rate risk of the banking book (RMLB)',
  '4.6': 'Strategic risk',
  '4.7': 'Reputational risk',
  '4.8': 'Other material risks',
  '5': 'Internal target of effective equity (OI)',
  '6': 'Capital needed for risks outside Pillar 1 (4.4 + 4.5 + 4.6 + 4.7 + 4.8)',
  '7': 'Minimum effective equity in the planning period (8% + 7.1 + 7.2)',
  '7.1': 'Additional effective equity under art. 66 quater (systemic bank)',
  '7.2': 'Additional effective equity under art. 66 quinquies',
  '8': 'Capital needed for risks outside Pillar 1 and not required by art. 66 quinquies (6 - 7.2)',
  '9': 'Conservation and countercyclical buffers in the planning period (art. 66 bis and 66 ter)',
  '10.1': 'Impact on the basic capital ratio of the severe stress tests, without mitigation',
  '10.2': 'Impact on the basic capital ratio of the severe stress tests, with mitigation',
  '11': 'Component d) of the OI',
  '12': 'Headroom of the effective equity ratio over the OI (1.1 - 5)',
};

export const TEST_TEXT: Record<string, Bi> = {
  'aggregation.simple_sum_and_variance_covariance': { en: 'The aggregate against the simple sum and the variance-covariance formula', es: 'El agregado frente a la suma simple y la fórmula de varianza-covarianza' },
  'aggregation.copula_choice_sensitivity': { en: 'Copula choice: Gaussian against Student t', es: 'Elección de cópula: gaussiana frente a t de Student' },
  'aggregation.worst_case_bracket': { en: 'The worst-case bracket around the aggregates', es: 'El rango del peor caso alrededor de los agregados' },
  'aggregation.correlation_stress': { en: 'Stress of the inter-risk correlation', es: 'Estrés de la correlación entre riesgos' },
  'aggregation.diversification_sign': { en: 'Sign of every diversification benefit', es: 'Signo de cada beneficio de diversificación' },
  'aggregation.horizon_confidence_consistency': { en: 'One horizon and one confidence level across the marginals', es: 'Un horizonte y un nivel de confianza en todas las marginales' },
  'aggregation.elliptical_mc_agreement': { en: 'Monte Carlo against the variance-covariance anchor', es: 'Monte Carlo frente al ancla de varianza-covarianza' },
  'aggregation.rosenberg_schuermann_reference': { en: 'Rosenberg and Schuermann reference (not a gate)', es: 'Referencia de Rosenberg y Schuermann (no es un umbral)' },
  'portfolio.euler_additivity': { en: 'The Euler contributions add up to the total', es: 'Las contribuciones de Euler suman el total' },
  'stress.satellite_backcast': { en: 'Back-cast of the satellites through 2020 to 2025', es: 'Prueba retrospectiva de los satélites entre 2020 y 2025' },
  'stress.sensitivity_monotonicity': { en: 'Sign and monotonicity of every sensitivity', es: 'Signo y monotonía de cada sensibilidad' },
  'stress.static_balance_sheet_rules': { en: 'The static balance sheet rules applied', es: 'Las reglas de balance estático aplicadas' },
  'stress.scenario_severity': { en: 'Severity of each path against history', es: 'Severidad de cada trayectoria frente a la historia' },
  'stress.reverse_solution_check': { en: 'Reverse stress: the loss at the solution equals the threshold', es: 'Estrés inverso: la pérdida en la solución iguala el umbral' },
};

/** The unit of the level a path draws: the published unit when the path is published as a level, the unit of the regressor otherwise (a
 * deviation added to a baseline is drawn as the level it builds; U16-R3 c19 M2: the NGFS line was titled "Abs. difference"). The four
 * regressors a scenario maps to are rates or growth in percent. */
export function plottedUnit(p: { unit: string; level_rule: { kind: string } }): Bi {
  if (p.level_rule.kind === 'level') return { en: p.unit, es: UNIT_ES[p.unit] ?? p.unit };
  return { en: 'percent', es: 'por ciento' };
}
const UNIT_ES: Record<string, string> = { percent: 'por ciento', 'percent, annualised': 'por ciento, anualizado' };

/** A name inside a sentence: its first letter lower case, an acronym kept (U16-R3 c19 m8: "real gdp growth"). */
export const inSentence = (name: string): string => name.charAt(0).toLowerCase() + name.slice(1);
