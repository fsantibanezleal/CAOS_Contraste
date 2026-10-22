// The selection the C17 views share, and the readings of a tail-index document every view needs. Nothing here computes a
// statistic: the capital percentiles, the ratios to the truth, the stability profile, the SMA and the scenario influence
// are the bake's; the helpers find, name and map. The true 99.9 percent quantile is always read beside the estimates.
import { formatNumber, type BiText } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';

export type C17Outputs = components['schemas']['c17Outputs'];
export type C17Fit = components['schemas']['c17Fit'];
export type C17Cell = components['schemas']['c17Cell'];
export type C17Capital = components['schemas']['c17Capital'];
export type C17Scenario = components['schemas']['c17Scenario'];

export interface C17Sel {
  data: CaseData;
  /** Years of recorded losses in each history: 5 or 10. */
  years: number;
  /** The collection threshold in EUR: losses below it are not recorded. */
  threshold: number;
  /** The rung of the ladder in focus, by the id of the ladder (`lda-splice`, `sla-mean-corrected`). */
  rung: string;
  /** The scenario of the scenario view in focus. */
  scenario: string;
}

/** The outputs of the selected variant, or null when it is not a tail-index document. */
export function outputsOf(sel: Pick<C17Sel, 'data'> | null): C17Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'tail-index' ? (out as C17Outputs) : null;
}

/** The fit of the C17 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C17Sel, 'data'> | null): C17Fit | null {
  return (sel?.data.models as unknown as { fit?: C17Fit } | undefined)?.fit ?? null;
}

/** The rungs of the ladder of dossier 05, in order: the order of the contract's ladder. */
export const RUNG_ORDER = ['lda-lognormal', 'lda-lognormal-truncated', 'lda-splice', 'sla', 'sla-mean-corrected', 'scenario'] as const;

/** A rung in few words (a bar, a chip, a table row); the models artifact carries the full sentence. */
export const RUNG_SHORT: Record<string, Bi> = {
  'lda-lognormal': { en: 'Lognormal, threshold ignored', es: 'Lognormal, umbral ignorado' },
  'lda-lognormal-truncated': { en: 'Truncated lognormal', es: 'Lognormal truncada' },
  'lda-splice': { en: 'Lognormal and GPD splice', es: 'Empalme lognormal y GPD' },
  sla: { en: 'Single loss approximation (SLA)', es: 'Aproximación de una pérdida (SLA)' },
  'sla-mean-corrected': { en: 'SLA, mean-corrected', es: 'SLA, corregida por la media' },
  scenario: { en: 'Scenario combination', es: 'Combinación con escenarios' },
};

/** The label of the contract is UNVERIFIED in the document and in the English view; the Spanish view says SIN VERIFICAR (U16-R2, b08 B3; C16 says it so). */
export const UNVERIFIED = 'UNVERIFIED';
export const UNVERIFIED_ES = 'SIN VERIFICAR';

export const STATUS_TEXT: Record<string, Bi> = {
  verified: { en: 'verified', es: 'verificado' },
  UNVERIFIED: { en: UNVERIFIED, es: UNVERIFIED_ES },
};

export const AGGREGATION_TEXT: Record<string, Bi> = {
  'monte-carlo': { en: 'Monte Carlo', es: 'Monte Carlo' },
  panjer: { en: 'Panjer recursion', es: 'Recursión de Panjer' },
  fft: { en: 'Fast Fourier transform', es: 'Transformada rápida de Fourier' },
  'closed-form': { en: 'Closed form', es: 'Forma cerrada' },
};

export const SEVERITY_TEXT: Record<string, Bi> = {
  lognormal: { en: 'Lognormal', es: 'Lognormal' },
  'lognormal-truncated': { en: 'Lognormal, truncated at the threshold', es: 'Lognormal, truncada en el umbral' },
  'lognormal-gpd-splice': { en: 'Lognormal body, GPD tail', es: 'Cuerpo lognormal, cola GPD' },
  gpd: { en: 'Generalised Pareto', es: 'Pareto generalizada' },
  none: { en: 'Scenario points', es: 'Puntos de escenario' },
};

export const SCENARIO_KIND_TEXT: Record<string, Bi> = {
  percentile: { en: 'Percentile', es: 'Percentil' },
  individual: { en: 'Individual', es: 'Individual' },
};

export const DISCRETION_TEXT: Record<string, Bi> = {
  none: { en: 'None', es: 'Ninguna' },
  'bucket-1-ilm-one': { en: 'Bucket 1: ILM = 1', es: 'Tramo 1: ILM = 1' },
  'national-ilm-one': { en: 'National discretion: ILM = 1', es: 'Discreción nacional: ILM = 1' },
  'transitional-bic-only': { en: 'Transition: BIC only', es: 'Transición: solo BIC' },
};

export const METHOD_TEXT: Record<string, Bi> = {
  'pseudo-observations': { en: 'Scenario points as pseudo-observations', es: 'Puntos de escenario como pseudo-observaciones' },
  'body-tail': { en: 'Body from data, tail from the scenarios', es: 'Cuerpo de los datos, cola de los escenarios' },
  'bayesian-credibility': { en: 'Bayesian credibility', es: 'Credibilidad bayesiana' },
};

export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** The id of a rung of the ladder as the key of the capital block of a cell (`lda-splice` is `lda_splice`). */
export const rungKey = (rung: string): keyof C17Cell['capital'] => rung.replaceAll('-', '_') as keyof C17Cell['capital'];

/** The words of a rung: its short name; never the internal id. */
export const rungLabel = (rung: string): Bi => text(RUNG_SHORT, rung);

/** A rung's name with the label the contract requires: the UNVERIFIED rung carries it in every place it is named. */
export function rungName(rung: string): Bi {
  const base = rungLabel(rung);
  return rung === 'sla-mean-corrected' ? { en: `${base.en} (${UNVERIFIED})`, es: `${base.es} (${UNVERIFIED_ES})` } : base;
}

/** The cell of the grid for the years and the threshold chosen, or the first when the document carries no such cell. */
export function cellOf(o: C17Outputs, years: number, threshold: number): C17Cell {
  return o.cells.find((c) => c.years === years && c.collection_threshold_eur === threshold) ?? o.cells[0];
}

/** The summary of a rung in a cell, or null with the reason the document gives (the rungs the bake may not evaluate). */
export function capitalOf(cell: C17Cell, rung: string): { summary: C17Capital | null; reason: string | null } {
  const block = cell.capital[rungKey(rung)] as C17Capital | { summary: C17Capital | null; reason: string | null };
  if ('summary' in block) return { summary: block.summary as C17Capital | null, reason: block.reason };
  return { summary: block, reason: null };
}

/** The scenario in focus, or the first the document carries. */
export function scenarioOf(o: C17Outputs, id: string): C17Scenario | null {
  return o.scenario_influence.scenarios.find((s) => s.scenario_id === id) ?? o.scenario_influence.scenarios[0] ?? null;
}

/** The threshold-stability row at the collection threshold of the cell, or the first row. */
export function stabilityAt(cell: C17Cell) {
  return cell.threshold_stability.find((r) => r.threshold_eur === cell.collection_threshold_eur) ?? cell.threshold_stability[0] ?? null;
}

/** The thresholds the grid carries, lowest first, from the cells themselves. */
export const thresholdsOf = (o: C17Outputs): number[] => [...new Set(o.cells.map((c) => c.collection_threshold_eur))].sort((a, b) => a - b);

/** The years of data the grid carries, lowest first. */
export const yearsOf = (o: C17Outputs): number[] => [...new Set(o.cells.map((c) => c.years))].sort((a, b) => a - b);

/** A whole amount of the document: 20,000 or 20.000, never a compact form (tables keep the whole amount). */
export const whole = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** A money amount as a threshold or a label: "EUR 20,000". */
export const eurText = (v: number): Bi => ({ en: `EUR ${whole(v, 'en')}`, es: `EUR ${whole(v, 'es')}` });

/** A cell in words: "10 years, threshold EUR 20,000". */
export function cellLabel(years: number, threshold: number): Bi {
  const t = eurText(threshold);
  return { en: `${years} years, threshold ${t.en}`, es: `${years} años, umbral ${t.es}` };
}

/** The words of an engine test of operational risk; an id without an entry is shown as it is. */
export const TEST_TEXT: Record<string, BiText> = {
  'oprisk.benchmark_reproduction': { en: 'Benchmark reproduction: Monte Carlo, Panjer and FFT', es: 'Reproducción del benchmark: Monte Carlo, Panjer y FFT' },
  'oprisk.threshold_stability': { en: 'Stability of the tail index across thresholds', es: 'Estabilidad del índice de cola entre umbrales' },
  'oprisk.capital_stability': { en: 'Stability of the 99.9 percent capital across histories', es: 'Estabilidad del capital al 99,9 por ciento entre historias' },
  'oprisk.sma_ilm_response': { en: 'Response of the SMA ILM to one large loss', es: 'Respuesta del ILM del SMA a una pérdida grande' },
  'oprisk.scenario_influence': { en: 'Influence of each scenario on the capital', es: 'Influencia de cada escenario en el capital' },
};

/** The view each engine test sits under; a test not named here sits under the ladder. */
export const TEST_VIEW: Record<string, 'exceedance' | 'tail' | 'method' | 'response' | 'scenario'> = {
  'oprisk.benchmark_reproduction': 'exceedance',
  'oprisk.threshold_stability': 'tail',
  'oprisk.capital_stability': 'method',
  'oprisk.sma_ilm_response': 'response',
  'oprisk.scenario_influence': 'scenario',
};

/** The selection a variant opens on: 10 years at the collection threshold of OPE25.18 (EUR 20,000), the spliced LDA. */
export function defaultSel(data: CaseData | null): C17Sel | null {
  if (!data || data.manifest.case_id !== 'C17') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const years = yearsOf(o).includes(10) ? 10 : (yearsOf(o)[0] ?? 10);
  const threshold = thresholdsOf(o).includes(20000) ? 20000 : (thresholdsOf(o)[0] ?? 20000);
  return { data, years, threshold, rung: 'lda-splice', scenario: o.scenario_influence.scenarios[0]?.scenario_id ?? '' };
}
