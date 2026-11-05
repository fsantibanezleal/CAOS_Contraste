// The selection the C10 views share, and the readings of a loan-type or a correlation-grid document every view needs.
// Nothing here computes a statistic: the fitted distribution, the loss distributions of the rungs, the Euler
// contributions, the granularity adjustment and the size and power of the correlation estimates are the bake's; the
// helpers find, name and map. The portfolio is illustrative and says so on every view that uses it, and the known
// correlation of the simulator is always read beside its estimates.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C10Outputs = components['schemas']['c10LoanTypeOutputs'];
export type C10GridOutputs = components['schemas']['c10GridOutputs'];
export type C10Fit = components['schemas']['c10ModelsFit'];
export type C10Rung = components['schemas']['c10Rung'];
export type C10Measure = components['schemas']['c10Measure'];
export type C10Group = components['schemas']['c10Group'];
export type C10Cell = components['schemas']['c10GridCell'];
export type C10Estimator = components['schemas']['c10Estimator'];
export type C10Euler = components['schemas']['c10Euler'];
export type C10EulerLevel = components['schemas']['c10EulerLevel'];

export type Lang = 'en' | 'es';
export type Level = 0.99 | 0.999;

export interface C10Sel {
  data: CaseData;
  /** The rung of the ladder in focus (a loan-type variant). */
  rung: string;
  /** The confidence level in focus. */
  level: Level;
  /** The estimator of the correlation in focus: maximum likelihood or moments. */
  estimator: string;
  /** The group of the illustrative portfolio in focus. */
  group: string;
  /** The known correlation of the grid cell in focus, as the text of the number (a correlation-grid variant). */
  cell: string;
}

export const LEVELS: Level[] = [0.99, 0.999];

/** The outputs of the selected variant when it is a loan-type document, or null. */
export function outputsOf(sel: Pick<C10Sel, 'data'> | null): C10Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'loan-type' ? (out as C10Outputs) : null;
}

/** The outputs of the selected variant when it is a correlation-grid document, or null. */
export function gridOf(sel: Pick<C10Sel, 'data'> | null): C10GridOutputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'correlation-grid' ? (out as C10GridOutputs) : null;
}

/** The fit of the C10 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C10Sel, 'data'> | null): C10Fit | null {
  return (sel?.data.models as unknown as { fit?: C10Fit } | undefined)?.fit ?? null;
}

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** A confidence level in words: 99% and 99.9%, with the comma of Spanish. */
export const levelLabel = (level: number, lang: Lang): string => formatNumber(level, lang, { percent: true, decimals: level === 0.999 ? 1 : 0 });
export const levelBi = (level: number): Bi => ({ en: levelLabel(level, 'en'), es: levelLabel(level, 'es') });

export const ESTIMATOR_TEXT: Record<string, Bi> = {
  'maximum-likelihood': { en: 'Maximum likelihood', es: 'Máxima verosimilitud' },
  moments: { en: 'Method of moments', es: 'Método de momentos' },
};
export const INTERVAL_TEXT: Record<string, Bi> = {
  'profile-likelihood': { en: 'profile likelihood', es: 'verosimilitud perfilada' },
  'parametric-bootstrap': { en: 'parametric bootstrap', es: 'remuestreo paramétrico' },
};
export const ESTIMATOR_SHORT: Record<string, Bi> = {
  'maximum-likelihood': { en: 'Max. likelihood', es: 'Máx. verosimilitud' },
  moments: { en: 'Moments', es: 'Momentos' },
};
/** The estimator on a chart mark: short enough to sit beside a line at 390 px (U16-R2 b05 M6). */
export const MARK_SHORT: Record<string, Bi> = {
  'maximum-likelihood': { en: 'ML', es: 'MV' },
  moments: { en: 'MoM', es: 'MM' },
};
/** The y-axis titles of the two fit charts: short, so the rotated title is never cut. */
export const DENSITY_TITLE: Bi = { en: 'Density', es: 'Densidad' };
export const LIKELIHOOD_TITLE: Bi = { en: 'Log-likelihood', es: 'Log-verosimilitud' };
/** The cutoff of the profile likelihood, as the label of its line. */
export const cutoffLabel = (value: string, lang: 'en' | 'es'): string => (lang === 'en' ? `Cutoff ${value}` : `Corte ${value}`);
export const ESTIMATOR_HINT: Record<string, Bi> = {
  'maximum-likelihood': { en: 'Maximises the likelihood of the yearly loss rates under the Vasicek distribution; the interval is the profile likelihood.', es: 'Maximiza la verosimilitud de las tasas de pérdida anuales bajo la distribución de Vasicek; el intervalo es la verosimilitud perfilada.' },
  moments: { en: 'Matches the mean and the variance of the yearly loss rates; the interval is a parametric bootstrap.', es: 'Iguala la media y la varianza de las tasas de pérdida anuales; el intervalo es un remuestreo paramétrico.' },
};

export const METHOD_TEXT: Record<string, Bi> = {
  'lhp-vasicek': { en: 'Large homogeneous portfolio', es: 'Cartera homogénea grande' },
  'gaussian-copula-one-factor': { en: 'Gaussian copula, one factor', es: 'Cópula gaussiana, un factor' },
  'gaussian-copula-multi-factor': { en: 'Gaussian copula, several factors', es: 'Cópula gaussiana, varios factores' },
  'student-t-copula': { en: 'Student-t copula', es: 'Cópula t de Student' },
  'creditrisk-plus': { en: 'CreditRisk+', es: 'CreditRisk+' },
  'granularity-adjustment': { en: 'Granularity adjustment', es: 'Ajuste de granularidad' },
  'importance-sampling': { en: 'Importance sampling', es: 'Muestreo por importancia' },
};
export const ESTIMATOR_KIND_TEXT: Record<string, Bi> = {
  analytic: { en: 'analytic', es: 'analítico' },
  'monte-carlo': { en: 'Monte Carlo', es: 'Monte Carlo' },
  none: { en: 'did not run', es: 'no corrió' },
};
export const IRB_CLASS_TEXT: Record<string, Bi> = {
  corporate: { en: 'Corporate', es: 'Corporativo' },
  sovereign: { en: 'Sovereign', es: 'Soberano' },
  bank: { en: 'Bank', es: 'Banco' },
  financial_institution: { en: 'Financial institution', es: 'Institución financiera' },
  sme: { en: 'SME', es: 'Pyme' },
  hvcre: { en: 'High-volatility commercial real estate', es: 'Inmobiliario comercial de alta volatilidad' },
  residential_mortgage: { en: 'Residential mortgage', es: 'Hipotecario residencial' },
  qrre: { en: 'Qualifying revolving retail', es: 'Minorista rotativo calificado' },
  other_retail: { en: 'Other retail', es: 'Otro minorista' },
  retail_consumer: { en: 'Retail consumer', es: 'Minorista de consumo' },
};
export const REGIME_TEXT: Record<string, Bi> = {
  basel3: { en: 'Basel III', es: 'Basilea III' },
  crr3: { en: 'CRR3', es: 'CRR3' },
  basel2: { en: 'Basel II', es: 'Basilea II' },
  cl_ran21_6: { en: 'Chile RAN 21-6', es: 'Chile RAN 21-6' },
};
export const SECTOR_TEXT: Record<string, Bi> = {
  prime: { en: 'prime', es: 'preferente' },
  'near-prime': { en: 'near-prime', es: 'casi preferente' },
  core: { en: 'core', es: 'núcleo' },
  periphery: { en: 'periphery', es: 'periferia' },
};

/** The source of the Federal Reserve series and the generator of the simulator. */
export const SOURCE_TEXT: Record<string, Bi> = {
  'fed-chargeoff': { en: 'Federal Reserve charge-off and delinquency rates', es: 'Tasas de castigo y morosidad de la Reserva Federal' },
};
export const GENERATOR_TEXT: Record<string, Bi> = {
  'vasicek-lhp-simulator': { en: 'Vasicek large-homogeneous-portfolio simulator', es: 'Simulador de Vasicek de una cartera homogénea grande' },
};

/** The diagnostics a rung reports and the parameters it takes, in words (the document gives their snake_case names). */
export const DIAGNOSTIC_TEXT: Record<string, Bi> = {
  n_max: { en: 'maximum loss units', es: 'máximo de unidades de pérdida' },
  tail_mass_left_out: { en: 'tail mass left out', es: 'masa de cola omitida' },
  expected_loss: { en: 'expected loss', es: 'pérdida esperada' },
  unit_rounding: { en: 'unit rounding', es: 'redondeo de la unidad' },
  variance_ratio_vs_plain_mc: { en: 'variance ratio against plain Monte Carlo', es: 'razón de varianza frente a Monte Carlo simple' },
  variance_ratio_es_vs_plain_mc: { en: 'ES variance ratio against plain Monte Carlo', es: 'razón de varianza del ES frente a Monte Carlo simple' },
  effective_sample_share: { en: 'effective sample share', es: 'proporción de muestra efectiva' },
};
export const PARAMETER_TEXT: Record<string, Bi> = {
  pd: { en: 'PD', es: 'PD' },
  lgd: { en: 'LGD', es: 'LGD' },
  n_factors: { en: 'factors', es: 'factores' },
  factor_correlation: { en: 'factor correlation', es: 'correlación entre factores' },
  loss_unit: { en: 'loss unit', es: 'unidad de pérdida' },
  threshold: { en: 'threshold', es: 'umbral' },
  factor_shift: { en: 'factor shift', es: 'desplazamiento del factor' },
  // the Greek parameters as their symbols, never their ASCII names (R3 c11 n5)
  rho: { en: 'ρ', es: 'ρ' },
  nu: { en: 'ν', es: 'ν' },
  xi: { en: 'ξ', es: 'ξ' },
  gamma: { en: 'γ', es: 'γ' },
  sigma2: { en: 'σ²', es: 'σ²' },
};
export const UNIT_TEXT: Record<string, Bi> = {
  'loss units': { en: 'loss units', es: 'unidades de pérdida' },
  ratio: { en: 'ratio', es: 'razón' },
  share: { en: 'share', es: 'proporción' },
  decimal: { en: 'decimal', es: 'decimal' },
};

/** The units a diagnostic or a parameter is written without a word for: the number says it, or the name does. */
const NO_UNIT_WORD = new Set(['-', 'decimal', 'ratio', 'share', 'loss units']);

/** A diagnostic or a parameter with its value and unit in the language: "variance ratio 388,7 razón". */
export function measureText(map: Record<string, Bi>, name: string, value: number, unit: string, lang: 'en' | 'es'): string {
  // a pure number takes no unit word, and a count of loss units is already named so (R3 c11 n4: "388.7 ratio", "12,728 loss units")
  const unitText = NO_UNIT_WORD.has(unit) ? '' : (UNIT_TEXT[unit]?.[lang] ?? unit);
  return `${(map[name] ?? { en: name, es: name })[lang]} ${formatNumber(value, lang, { digits: 4 })} ${unitText}`.trim();
}
export const EULER_METHOD_TEXT: Record<string, Bi> = {
  'gaussian-copula-one-factor': METHOD_TEXT['gaussian-copula-one-factor'],
  'gaussian-copula-multi-factor': METHOD_TEXT['gaussian-copula-multi-factor'],
  'student-t-copula': METHOD_TEXT['student-t-copula'],
  'creditrisk-plus': METHOD_TEXT['creditrisk-plus'],
};
export const VAR_METHOD_TEXT: Record<string, Bi> = {
  kernel: { en: 'kernel estimate', es: 'estimador de núcleo' },
  'closed-form-one-factor': { en: 'closed form, one factor', es: 'forma cerrada, un factor' },
};

/** The ladder rung of the document by id. */
export const rungOf = (o: C10Outputs, id: string): C10Rung | undefined => o.rungs.find((r) => r.id === id);

/** The measure of a rung at a level, or null when the rung did not run or has no such level. */
export function measureOf(r: C10Rung | undefined, level: number): C10Measure | null {
  return r?.measures?.find((m) => m.level === level) ?? null;
}

/** The Euler block that belongs to a rung (the rung's method), or null when the rung carries none. */
export function eulerOf(o: C10Outputs, rung: C10Rung | undefined): C10Euler | null {
  return o.euler.find((e) => e.rung_method === rung?.method) ?? null;
}

export function eulerLevelOf(e: C10Euler | null, level: number): C10EulerLevel | null {
  return e?.levels.find((l) => l.level === level) ?? null;
}

/** The label of a portfolio group in words, never its internal id. */
export function groupLabel(groups: C10Group[], id: string): Bi {
  const g = groups.find((x) => x.id === id);
  return g ? { en: g.label.en, es: g.label.es } : { en: id, es: id };
}

/** The fitted interval of the estimator in focus. */
export function estimatorFit(o: C10Outputs, estimator: string) {
  return estimator === 'moments' ? o.fit.moments : o.fit.maximum_likelihood;
}

/** The known-correlation cell as the key the rail holds, and the cell of a key. */
export const cellKey = (c: C10Cell): string => String(c.known_rho);
export const cellOf = (g: C10GridOutputs, key: string): C10Cell | undefined => g.cells.find((c) => cellKey(c) === key);
export const estimatorOf = (c: C10Cell | undefined, estimator: string): C10Estimator | null => c?.estimators.find((e) => e.estimator === estimator) ?? null;

/** The default selection of a variant: the first Monte Carlo rung that ran, 99.9%, maximum likelihood, the first group, the size cell. */
export function defaultSel(data: CaseData | null): C10Sel | null {
  if (!data || data.manifest.case_id !== 'C10') return null;
  const o = outputsOf({ data });
  const g = gridOf({ data });
  if (!o && !g) return null;
  const rungs = o?.rungs ?? [];
  const rung = (rungs.find((r) => r.evaluated && r.estimator === 'monte-carlo') ?? rungs.find((r) => r.evaluated) ?? rungs[0])?.id ?? '';
  const cell = g ? (g.cells.find((c) => c.known_rho === g.generator.null_rho) ?? g.cells[0]) : undefined;
  return { data, rung, level: 0.999, estimator: 'maximum-likelihood', group: o?.portfolio.groups[0]?.id ?? '', cell: cell ? cellKey(cell) : '' };
}

/**
 * The remarks the producer attaches to the citations of the ladder, the estimators and the granularity adjustment (English only in the
 * models artifact): the citation as published, its locators and the remark in Spanish. A reference it does not know is shown as written.
 */
const REFERENCE_ES: Record<string, string> = {
  // the second moment as a superscript (R5 c13 N5); a document baked before it writes the caret, which `referenceNote` reads the same
  'dossier 04 C.4 (E[L²] = joint default probability)': 'dossier 04 C.4 (E[L²] = probabilidad conjunta de incumplimiento)',
  // the authors joined with "y" and the month in Spanish; the titles and the journals stay as published (R3 c11 n1)
  'Vasicek (2002), Risk, December 2002; dossier 04 C.4': 'Vasicek (2002), Risk, diciembre de 2002; dossier 04 C.4',
  'Frey and McNeil (2003); Demarta and McNeil (2005); dossier 04 H.3': 'Frey y McNeil (2003); Demarta y McNeil (2005); dossier 04 H.3',
  'Haaf, Reiss and Schoenmakers (2004); dossier 04 H.4': 'Haaf, Reiss y Schoenmakers (2004); dossier 04 H.4',
  'Gordy and Lutkebohmert (2013); dossier 04 H.5': 'Gordy y Lutkebohmert (2013); dossier 04 H.5',
  'Glasserman and Li (2005); dossier 04 H.7 (the twist is UNVERIFIED there; acceptance is unbiasedness against plain Monte Carlo)':
    'Glasserman y Li (2005); dossier 04 H.7 (la inclinación está SIN VERIFICAR allí; la aceptación es la ausencia de sesgo frente al Monte Carlo simple)',
  'Glasserman and Li (2005); no Student-t twist is specified, so the rung is a not-evaluated row':
    'Glasserman y Li (2005); no se especifica una inclinación para la t de Student, así que el escalón es una fila no evaluada',
  // the producer's wording since U16-F12c (R4 c13 n5: "a not-evaluated row" is the document's jargon, not the reader's)
  'Glasserman and Li (2005); no Student-t twist is specified, so the rung does not run':
    'Glasserman y Li (2005); no se especifica una inclinación para la t de Student, así que el escalón no corre',
  'Gordy and Lutkebohmert (2013), eq. 15 and eq. 16 (dossier 04 H.5)': 'Gordy y Lutkebohmert (2013), ecs. 15 y 16 (dossier 04 H.5)',
  'Gordy and Lutkebohmert (2013), eq. 15 and p. 46 (dossier 04 H.5)': 'Gordy y Lutkebohmert (2013), ec. 15 y p. 46 (dossier 04 H.5)',
};
export const referenceNote = (reference: string, lang: 'en' | 'es'): string => {
  // a power written with a caret is the superscript in reader text ("E[L^2]" reads "E[L²]"; R5 c13 N5)
  const ref = reference.replace(/\^2/g, '²');
  return lang === 'es' ? REFERENCE_ES[ref] ?? ref : ref;
};
