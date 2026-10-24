// The selection the C11 views share, and the readings of a window document every view needs. Nothing here computes a
// statistic of the model: the forecasts, the exceedances, the scores, the back-tests and the comparison are the bake's.
// The helpers find, name and map; the one count made here is the rolling 250-day exceedance count, a tally of the
// exceedance days the document lists, which the tests check against the document's own maximum and final count.
// Every VaR and ES the document holds is a positive loss, a decimal of the portfolio value (dossier 05 A.0).
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { TestRow } from '../../lib/contract.types';
import type { Bi } from '../c03/U6Shared';
import { testText } from '../names';

export type C11Outputs = components['schemas']['c11Outputs'];
export type C11Fit = components['schemas']['c11Fit'];
export type C11Level = components['schemas']['c11LevelResult'];
export type C11Model = components['schemas']['c11ModelOutput'];
export type C11Alpha = 0.01 | 0.025;

export interface C11Sel {
  data: CaseData;
  /** The tail level in focus. */
  alpha: C11Alpha;
  /** The model of the ladder in focus. */
  model: string;
  /** The back-test (a test id) in focus. */
  test: string;
}

/** The outputs of the selected variant, or null when it is not a window document. */
export function outputsOf(sel: Pick<C11Sel, 'data'> | null): C11Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'window' ? (out as C11Outputs) : null;
}

/** The fit of the C11 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C11Sel, 'data'> | null): C11Fit | null {
  return (sel?.data.models as unknown as { fit?: C11Fit } | undefined)?.fit ?? null;
}

/** One model at one level, or null when the window does not carry it. */
export function levelOf(o: C11Outputs | null, model: string, alpha: number): C11Level | null {
  return o?.models.find((m) => m.model_id === model)?.by_level.find((l) => l.alpha === alpha) ?? null;
}

/** The test rows of a model at a level (segment `alpha=<alpha>`), in the order of the level's own list. */
export function testsOf(sel: Pick<C11Sel, 'data'> | null, o: C11Outputs | null, model: string, alpha: number): TestRow[] {
  const level = levelOf(o, model, alpha);
  const rows = (sel?.data.variant.tests ?? []).filter((t) => t.model_id === model && t.segment === `alpha=${alpha}`);
  if (!level) return rows;
  const order = new Map(level.test_ids.map((id, i) => [id, i]));
  return [...rows].sort((a, b) => (order.get(a.test_id) ?? 99) - (order.get(b.test_id) ?? 99));
}

/** The champion of a level, or null when none (the document then gives the reason). */
export function championOf(o: C11Outputs | null, alpha: number): string | null {
  return o?.comparison.champions.find((c) => c.alpha === alpha)?.model_id ?? null;
}

/** The words of the market back-tests; an id without an entry is shown as it is. */
export const TEST_TEXT: Record<string, Bi> = {
  'market.kupiec_pof': { en: 'Kupiec proportion of failures', es: 'Proporción de fallas de Kupiec' },
  'market.christoffersen_independence': { en: 'Christoffersen independence', es: 'Independencia de Christoffersen' },
  'market.christoffersen_conditional_coverage': { en: 'Christoffersen conditional coverage', es: 'Cobertura condicional de Christoffersen' },
  'market.duration_test': { en: 'Duration test', es: 'Prueba de duración' },
  'market.acerbi_szekely': { en: 'Acerbi-Szekely Z2 (expected shortfall)', es: 'Acerbi-Szekely Z2 (pérdida esperada)' },
  'market.du_escanciano_unconditional': { en: 'Du-Escanciano unconditional', es: 'Du-Escanciano incondicional' },
  'market.du_escanciano_conditional': { en: 'Du-Escanciano conditional', es: 'Du-Escanciano condicional' },
  'market.mcneil_frey_residual_test': { en: 'McNeil-Frey exceedance residuals', es: 'Residuos de excedencia de McNeil-Frey' },
  'market.dynamic_quantile_test': { en: 'Dynamic quantile test', es: 'Prueba de cuantil dinámico' },
  'market.basel_traffic_light': { en: 'Basel traffic light', es: 'Semáforo de Basilea' },
  'market.desk_backtest': { en: 'Desk back-test', es: 'Backtest de mesa' },
  'market.pla_test': { en: 'P&L attribution test', es: 'Prueba de atribución de P&L' },
};
export const testName = (id: string): Bi => TEST_TEXT[id] ?? testText(id);

export const ZONE_TEXT: Record<string, Bi> = {
  green: { en: 'Green', es: 'Verde' },
  amber: { en: 'Amber', es: 'Ámbar' },
  red: { en: 'Red', es: 'Rojo' },
  not_evaluated: { en: 'Not evaluated', es: 'No evaluado' },
};

export const LOSS_TEXT: Record<string, Bi> = {
  fz0: { en: 'FZ0 score', es: 'Puntaje FZ0' },
  tick: { en: 'Tick loss', es: 'Pérdida tick' },
};

export const DIRECTION_TEXT: Record<string, Bi> = {
  better: { en: 'Better than the champion', es: 'Mejor que el campeón' },
  worse: { en: 'Worse than the champion', es: 'Peor que el campeón' },
  indistinguishable: { en: 'Indistinguishable', es: 'Indistinguible' },
  'not-evaluated': { en: 'Not evaluated', es: 'No evaluado' },
};

export const WINDOW_TEXT: Record<string, Bi> = {
  'equity-2007-09': { en: 'Equity 2007 to 2009', es: 'Acciones 2007 a 2009' },
  'equity-2020': { en: 'Equity 2020', es: 'Acciones 2020' },
  'rates-2022': { en: 'Rates 2022', es: 'Tasas 2022' },
  'fx-2008': { en: 'FX 2008', es: 'Divisas 2008' },
  'mixed-2023': { en: 'Mixed 2023', es: 'Mixta 2023' },
  'calm-2004-06': { en: 'Calm 2004 to 2006', es: 'Calma 2004 a 2006' },
};

/** The units a document names ("5 days", "draws"), in words. */
export const UNIT_TEXT: Record<string, Bi> = {
  days: { en: 'days', es: 'días' },
  draws: { en: 'draws', es: 'remuestreos' },
  models: { en: 'models', es: 'modelos' },
  'fz0-loss': { en: 'FZ0 loss', es: 'pérdida FZ0' },
};
const UNIT_ONE: Record<string, Bi> = {
  days: { en: 'day', es: 'día' },
  draws: { en: 'draw', es: 'remuestreo' },
  models: { en: 'model', es: 'modelo' },
};
/** A unit in words, in the singular for a value of one ("1 day", never "1 days"; U16-R2 b05 m4). */
export const unitFor = (unit: string, value: number): Bi => (value === 1 && UNIT_ONE[unit] ? UNIT_ONE[unit] : text(UNIT_TEXT, unit));
/** The hyperparameters a window lists beyond the named ones, in words. */
export const HYPERPARAMETER_TEXT: Record<string, Bi> = {
  caviar_refit_every_days: { en: 'CAViaR refit every', es: 'Reajuste CAViaR cada' },
  hs_short_window: { en: 'Short historical-simulation window', es: 'Ventana corta de simulación histórica' },
  // every key the documents list (R2b c12 B2: five printed as ids, in the Spanish view too)
  hs_long_window: { en: 'Long historical-simulation window', es: 'Ventana larga de simulación histórica' },
  gas_refit_every_days: { en: 'GAS refit every', es: 'Reajuste GAS cada' },
  evt_refit_every_days: { en: 'EVT refit every', es: 'Reajuste EVT cada' },
  z2_draws: { en: 'Z2 simulations', es: 'Simulaciones de Z2' },
  mc_draws: { en: 'Monte Carlo simulations', es: 'Simulaciones de Monte Carlo' },
};

/** The reasons a document gives for a score it could not compute, in Spanish (the document writes them in English). */
export const REASON_ES: Record<string, string> = {
  'the model forecasts no ES: FZ0 is not defined': 'el modelo no pronostica ES: FZ0 no está definido',
};

export const CLASS_TEXT: Record<string, Bi> = {
  equity: { en: 'Equity', es: 'Acciones' },
  rates: { en: 'Rates', es: 'Tasas' },
  fx: { en: 'FX', es: 'Divisas' },
  mixed: { en: 'Mixed', es: 'Mixta' },
};

export const SOURCE_CLASS_TEXT: Record<string, Bi> = {
  'derived-only': { en: 'derived results only', es: 'solo resultados derivados' },
  'mirror-allowed': { en: 'mirror allowed', es: 'espejo permitido' },
};

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** A tail level in words: "1% tail (99% VaR)". */
export function alphaLabel(alpha: number): Bi {
  const f = (lang: 'en' | 'es') => formatNumber(alpha, lang, { percent: true, decimals: alpha === 0.025 ? 1 : 0 });
  const g = (lang: 'en' | 'es') => formatNumber(1 - alpha, lang, { percent: true, decimals: alpha === 0.025 ? 1 : 0 });
  return { en: `${f('en')} tail (${g('en')} VaR)`, es: `Cola de ${f('es')} (VaR al ${g('es')})` };
}

/** A tail level in a few words, for a chip of the narrow rail: "1% tail". */
export function alphaShort(alpha: number): Bi {
  const f = (lang: 'en' | 'es') => formatNumber(alpha, lang, { percent: true, decimals: alpha === 0.025 ? 1 : 0 });
  return { en: `${f('en')} tail`, es: `Cola de ${f('es')}` };
}

/** The words for a model of the ladder: the title the models document gives its rung, else the variant's. Never the id. */
export function modelLabel(sel: Pick<C11Sel, 'data'> | null, id: string): Bi {
  const rung = fitOf(sel)?.ladder.find((r) => r.model_id === id);
  if (rung) return rung.title;
  const m = sel?.data.variant.model.find((x) => x.id === id);
  return m ? m.title : { en: 'A model', es: 'Un modelo' };
}

/** The rung of a model (R1 to R10) as a short label. */
export function rungOf(sel: Pick<C11Sel, 'data'> | null, id: string): string {
  return fitOf(sel)?.ladder.find((r) => r.model_id === id)?.rung ?? sel?.data.variant.model.find((x) => x.id === id)?.rung ?? '';
}

/** A loss as a percent of the portfolio value, two decimals: 0.84%. */
export const lossPct = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });

/** A date of the document (an ISO day) as epoch seconds, for the time axis of a chart. */
export const seconds = (day: string): number => Date.parse(`${day}T00:00:00Z`) / 1000;

/** The one-line convention every view states (the full definition is in the Context and the models document). */
export const CONVENTION_LINE: Bi = {
  en: 'VaR and ES are positive losses, decimals of the portfolio value: a VaR of 1% means a loss of 1% of its value.',
  es: 'El VaR y la ES son pérdidas positivas, decimales del valor de la cartera: un VaR de 1 % significa una pérdida de 1 % de su valor.',
};

/** The sentence that says where the hyperparameters were fixed, before any test window (decision D1). */
export function spanLine(o: C11Outputs): Bi {
  const s = o.hyperparameters.fixed_on;
  return {
    en: `Hyperparameters fixed on ${s.start} to ${s.end}, before the earliest test window, and never tuned on a test window.`,
    es: `Hiperparámetros fijados en ${s.start} a ${s.end}, antes de la primera ventana de prueba, y nunca ajustados en una ventana de prueba.`,
  };
}

/**
 * The tally of the exceedance days in each complete window of `window` grid days: element i is the count in the days
 * i - window + 1 to i, for i from window - 1 on. Empty when the grid is shorter than the window.
 */
export function rollingCounts(exceedanceDays: readonly number[], n: number, window = 250): number[] {
  if (n < window) return [];
  const hit = new Uint8Array(n);
  for (const d of exceedanceDays) if (d >= 0 && d < n) hit[d] = 1;
  const out: number[] = [];
  let sum = 0;
  for (let i = 0; i < n; i++) {
    sum += hit[i];
    if (i >= window) sum -= hit[i - window];
    if (i >= window - 1) out.push(sum);
  }
  return out;
}

/** The first number of exceptions of a zone in the MAR32.9 table of the models document (5 for amber, 10 for red), or null. */
export function zoneStart(fit: C11Fit | null, zone: 'amber' | 'red'): number | null {
  return fit?.traffic_light.rows.find((r) => r.zone === zone)?.exceptions ?? null;
}

/** The selection a variant opens on: the first level, its champion (else the first model) and that model's first test. */
export function defaultSel(data: CaseData | null): C11Sel | null {
  if (!data || data.manifest.case_id !== 'C11') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const alpha = (o.levels[0]?.alpha ?? 0.01) as C11Alpha;
  const model = championOf(o, alpha) ?? o.models[0]?.model_id ?? '';
  const test = levelOf(o, model, alpha)?.test_ids[0] ?? '';
  return { data, alpha, model, test };
}

/** How each rung of the ladder forms its expected shortfall (the document gives it in English only). */
const ES_METHOD: Array<[string, string]> = [
  ['tail mean of the sorted window', 'media de la cola de la ventana ordenada'],
  ['tail integral of the interpolated weighted quantile function', 'integral de la cola de la función de cuantiles ponderada e interpolada'],
  ['normal ES from the window mean and volatility', 'ES normal con la media y la volatilidad de la ventana'],
  ['none: the Cornish-Fisher expansion gives the VaR only', 'ninguno: la expansión de Cornish-Fisher da solo el VaR'],
  ['normal ES from the EWMA volatility', 'ES normal con la volatilidad EWMA'],
  ['Student-t tail mean of the unit-variance innovation', 'media de la cola t de Student de la innovación de varianza unitaria'],
  ['tail mean of the GARCH-filtered standardised residuals', 'media de la cola de los residuos estandarizados filtrados por GARCH'],
  ['GPD tail ES, undefined for xi at or above 1', 'ES de la cola GPD, indefinido para xi igual o mayor que 1'],
  ['none: CAViaR forecasts the VaR only', 'ninguno: CAViaR pronostica solo el VaR'],
  ['autoregressive gap below the CAViaR VaR, fitted by the asymmetric Laplace likelihood', 'brecha autorregresiva bajo el VaR de CAViaR, ajustada con la verosimilitud de Laplace asimétrica'],
  ['joint VaR and ES from one dynamic factor (FZ0 estimation)', 'VaR y ES conjuntos de un factor dinámico (estimación FZ0)'],
  ['joint VaR and ES from two dynamic factors (FZ0 estimation)', 'VaR y ES conjuntos de dos factores dinámicos (estimación FZ0)'],
  ['one dynamic factor with a log absolute return term (FZ0 estimation)', 'un factor dinámico con un término de log del retorno absoluto (estimación FZ0)'],
  ['network output', 'salida de la red'],
];
export const esMethodText = (method: string, lang: 'en' | 'es'): string => (lang === 'en' ? method : (ES_METHOD.find(([en]) => en === method)?.[1] ?? method));

/** The source of a rung ("historical simulation (textbook; Pritsker 2001)"): the citation stays, its English remarks are translated. */
export const rungSourceText = (source: string, lang: 'en' | 'es'): string =>
  lang === 'en'
    ? source
    : source
        .replace('historical simulation (textbook;', 'simulación histórica (de texto;')
        .replace('(preprint; challenger only)', '(preprint; solo retador)')
        .replace('; two-step estimation declared in the engine', '; estimación en dos pasos declarada en el motor');
