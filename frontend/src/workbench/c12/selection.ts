// The selection the C12 views share, and the readings of a swap-exposure document every view needs. Nothing here computes
// a statistic of the model: the profiles, the CVA, the backtest and the regulatory blocks are the bake's; the helpers find,
// name and map. The only arithmetic is the live SA-CCR and BA-CVA of the ports (saccr.ts, bacva.ts, held to the
// document's blocks by a parity test), the running sum of the document's own CVA terms (its last value is the document's
// CVA) and the binning of the document's own PITs into ten equal classes. Money is in USD as the document gives it; a
// narrow place scales it to bn, m or thousands with the unit that says so.
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { axisScale, compactMoney } from '../c06/format';
import type { Bi } from '../c03/U6Shared';
import { baCva, baCvaInputFrom, riskWeight, type BaCvaResult, type RatingClass, type SectorId, SECTORS } from './bacva';
import { saCcr, saCcrInputFrom, type SaCcrResult } from './saccr';

export type C12Outputs = components['schemas']['c12Outputs'];
export type C12Fit = components['schemas']['c12Fit'];
export type C12Profile = components['schemas']['c12NonNegProfile'];
export type C12Horizon = components['schemas']['c12BacktestHorizon'];
export type C12Sensitivity = components['schemas']['c12SensitivityCase'];
export type C12Calibration = components['schemas']['c12Calibration'];
export type C12Wwr = components['schemas']['c12Wwr'];
export type C12Money = components['schemas']['c12Money'];

export type VariantId = C12Outputs['variant'];
export type HorizonId = C12Horizon['horizon'];
export type CaseId = C12Sensitivity['case'];
export type Subject = 'book' | 'risk-factor';

/** The variants of the case in the order the SDD states them, and the words for each. */
export const VARIANT_ORDER: readonly VariantId[] = ['single-swap', 'netting-set', 'csa-mpor-10d', 'csa-mpor-20d', 'with-im', 'wrong-way-risk'];
export const VARIANT_TEXT: Record<string, Bi> = {
  'single-swap': { en: 'Single swap', es: 'Una sola permuta' },
  'netting-set': { en: 'Netting set', es: 'Conjunto de neteo' },
  'csa-mpor-10d': { en: 'CSA, MPoR 10 days', es: 'CSA, MPoR de 10 días' },
  'csa-mpor-20d': { en: 'CSA, MPoR 20 days', es: 'CSA, MPoR de 20 días' },
  // the variant's own name, the one its selector shows (R2b c13 m5: "Con margen inicial" in the rail, "CSA con margen inicial" here)
  'with-im': { en: 'With initial margin', es: 'Con margen inicial' },
  'wrong-way-risk': { en: 'Wrong-way risk', es: 'Riesgo de correlación adversa' },
};
export const BASIS_TEXT: Record<string, Bi> = {
  uncollateralised: { en: 'uncollateralised', es: 'sin colateral' },
  'collateralised-vm': { en: 'with variation margin', es: 'con margen de variación' },
  'collateralised-vm-im': { en: 'with variation and initial margin', es: 'con margen de variación e inicial' },
};

export const HORIZONS: readonly HorizonId[] = ['10bd', '20bd', '1m', '3m', '6m', '12m'];
export const HORIZON_SHORT: Record<string, Bi> = {
  '10bd': { en: '10 d', es: '10 d' },
  '20bd': { en: '20 d', es: '20 d' },
  '1m': { en: '1 m', es: '1 m' },
  '3m': { en: '3 m', es: '3 m' },
  '6m': { en: '6 m', es: '6 m' },
  '12m': { en: '12 m', es: '12 m' },
};
export const HORIZON_LONG: Record<string, Bi> = {
  '10bd': { en: '10 business days', es: '10 días hábiles' },
  '20bd': { en: '20 business days', es: '20 días hábiles' },
  '1m': { en: '1 month', es: '1 mes' },
  '3m': { en: '3 months', es: '3 meses' },
  '6m': { en: '6 months', es: '6 meses' },
  '12m': { en: '12 months', es: '12 meses' },
};
export const SUBJECT_TEXT: Record<Subject, Bi> = {
  book: { en: 'Book', es: 'Cartera' },
  'risk-factor': { en: 'Rate', es: 'Tasa' },
};
export const SUBJECT_LONG: Record<Subject, Bi> = {
  book: { en: 'the value of the synthetic book revalued on the realised curve', es: 'el valor de la cartera sintética revalorada con la curva realizada' },
  'risk-factor': { en: 'the risk factor: the shortest Treasury zero rate, the proxy of the short rate', es: 'el factor de riesgo: la tasa cero más corta del Tesoro, el sustituto de la tasa corta' },
};
export const CASE_ORDER: readonly CaseId[] = ['base', 'a-plus-1se', 'a-minus-1se', 'sigma-plus-1se', 'sigma-minus-1se'];
export const CASE_TEXT: Record<string, Bi> = {
  base: { en: 'Base calibration', es: 'Calibración base' },
  'a-plus-1se': { en: 'Reversion a, plus 1 SE', es: 'Reversión a, más 1 ES' },
  'a-minus-1se': { en: 'Reversion a, minus 1 SE', es: 'Reversión a, menos 1 ES' },
  'sigma-plus-1se': { en: 'Volatility sigma, plus 1 SE', es: 'Volatilidad sigma, más 1 ES' },
  'sigma-minus-1se': { en: 'Volatility sigma, minus 1 SE', es: 'Volatilidad sigma, menos 1 ES' },
};
export const SECTOR_TEXT: Record<SectorId, Bi> = {
  'sovereigns-central-banks-mdbs': { en: 'Sovereigns, central banks, MDBs', es: 'Soberanos, bancos centrales, BMD' },
  'local-government-public': { en: 'Local government, public bodies', es: 'Gobierno local, entes públicos' },
  financials: { en: 'Financials', es: 'Financieras' },
  'basic-materials-energy-industrials': { en: 'Materials, energy, industrials', es: 'Materiales, energía, industriales' },
  'consumer-transport-administrative': { en: 'Consumer, transport, administrative', es: 'Consumo, transporte, administrativas' },
  'technology-telecoms': { en: 'Technology, telecoms', es: 'Tecnología, telecomunicaciones' },
  'health-care-utilities-professional': { en: 'Health care, utilities, professional', es: 'Salud, servicios públicos, profesionales' },
  other: { en: 'Other sectors', es: 'Otros sectores' },
};
export const RATING_TEXT: Record<RatingClass, Bi> = {
  'investment-grade': { en: 'Investment grade', es: 'Grado de inversión' },
  'high-yield-or-not-rated': { en: 'High yield or not rated', es: 'Alto rendimiento o sin calificación' },
};
export const RATING_SHORT: Record<RatingClass, Bi> = {
  'investment-grade': { en: 'IG', es: 'GI' },
  'high-yield-or-not-rated': { en: 'HY or NR', es: 'AR o SC' },
};
export const text = (map: Record<string, Bi>, id: string): Bi => map[id] ?? { en: id, es: id };

/** Whether a value is one of the sectors of MAR50.16 Table 1. */
export const isSector = (s: string): s is SectorId => (SECTORS as string[]).includes(s);
export const isRating = (s: string): s is RatingClass => s === 'investment-grade' || s === 'high-yield-or-not-rated';

/** A variant document of the case: its id in the manifest, the title the manifest gives it and its outputs. */
export interface Peer {
  variantId: string;
  title: Bi;
  o: C12Outputs;
}
/** The documents of the case by variant (`outputs.variant`), once loaded: what the cross-variant views draw (the collateral comparison, the wrong-way sweep, the variants table). */
export type Peers = Record<string, Peer>;

export interface C12Sel {
  data: CaseData;
  /** The documents of every variant of the case, or null while they load. */
  peers: Peers | null;
  /** The index of the point of the time grid in focus. */
  t: number;
  /** The backtest horizon in focus and what is backtested. */
  horizon: HorizonId;
  subject: Subject;
  /** The index of the wrong-way point in focus (the b grid), or the calibration case in focus. */
  b: number;
  caseId: CaseId;
  /** The collateral held, C, of the live SA-CCR in USD; null keeps the document's. */
  collateral: number | null;
  /** The sector and rating class of the live BA-CVA's counterparty. */
  sector: SectorId;
  rating: RatingClass;
}

/** The outputs of the selected variant, or null when it is not a swap-exposure document. */
export function outputsOf(sel: Pick<C12Sel, 'data'> | null): C12Outputs | null {
  const out = (sel?.data.variant as { outputs?: { kind?: string } } | undefined)?.outputs;
  return out && out.kind === 'swap-exposure' ? (out as C12Outputs) : null;
}

/** The fit of the C12 models artifact, or null when the artifact carries none. */
export function fitOf(sel: Pick<C12Sel, 'data'> | null): C12Fit | null {
  return (sel?.data.models as unknown as { fit?: C12Fit } | undefined)?.fit ?? null;
}

export const gridOf = (o: C12Outputs | null): number[] => o?.exposure.time_grid_years ?? [];

/** The index of the grid point nearest to a time. */
export function nearestIndex(grid: readonly number[], t: number): number {
  let best = 0;
  grid.forEach((g, i) => {
    if (Math.abs(g - t) < Math.abs(grid[best] - t)) best = i;
  });
  return best;
}

/** The backtest horizons of the subject in focus. */
export const horizonsOf = (o: C12Outputs | null, subject: Subject): C12Horizon[] => (o ? (subject === 'book' ? o.backtest.book_horizons : o.backtest.risk_factor.horizons) : []);
export const horizonOf = (o: C12Outputs | null, subject: Subject, id: string): C12Horizon | null => horizonsOf(o, subject).find((h) => h.horizon === id) ?? null;
export const sensitivityOf = (o: C12Outputs | null, id: string): C12Sensitivity | null => o?.calibration_sensitivity.find((c) => c.case === id) ?? null;

/** The wrong-way block of the document, or the one of the wrong-way variant when the document has none (and it is loaded). */
export function wwrOf(sel: C12Sel | null): { block: C12Wwr; owner: C12Outputs } | null {
  const o = outputsOf(sel);
  if (o?.wrong_way_risk) return { block: o.wrong_way_risk, owner: o };
  const peer = sel?.peers?.['wrong-way-risk']?.o;
  return peer?.wrong_way_risk ? { block: peer.wrong_way_risk, owner: peer } : null;
}

/** The collateral held of the document's SA-CCR block, and the largest collateral the live control offers (USD). */
export const committedCollateral = (o: C12Outputs | null): number => o?.sa_ccr.c.amount ?? 0;
export function collateralRange(o: C12Outputs | null): { min: number; max: number; step: number } {
  const v = o?.sa_ccr.v.amount ?? 0;
  const top = Math.max(2 * Math.max(v, committedCollateral(o), 0), 100_000);
  const max = Math.ceil(top / 1000);
  // a negative collateral is collateral the bank posted, which raises the exposure (CRE52.17): the range reaches below 0 when the
  // document's does, so the control and the chart can show it (R3 c13 BL5: the margined variants marked 0 and drew the EAD at 0)
  const min = Math.min(0, Math.floor((2 * committedCollateral(o)) / 1000));
  return { min, max, step: Math.max(1, Math.round((max - min) / 200)) };
}

/** The live SA-CCR on the collateral in focus, from the document's inputs: the port of CRE52. */
export function liveSaCcr(o: C12Outputs | null, collateral: number | null): SaCcrResult | null {
  if (!o) return null;
  const input = saCcrInputFrom(o.sa_ccr);
  return saCcr(collateral === null ? input : { ...input, c: collateral });
}

/** The live BA-CVA on the sector and rating in focus, with the EAD of the live SA-CCR: the port of MAR50 (reduced). */
export function liveBaCva(o: C12Outputs | null, ead: number | null, sector: SectorId, rating: RatingClass): BaCvaResult | null {
  if (!o || ead === null) return null;
  const input = baCvaInputFrom(o.ba_cva);
  const first = input[0];
  if (!first) return null;
  const replaced = [{ rw: riskWeight(sector, rating), sets: first.sets.map((s) => ({ ...s, ead })) }, ...input.slice(1)];
  return baCva(replaced, o.ba_cva.imm_bank);
}

/** The selection a variant opens on: the first point of the grid, the 12-month horizon of the book, the base case, the document's own collateral and counterparty. */
export function defaultSel(data: CaseData | null, peers: Peers | null = null): C12Sel | null {
  if (!data || data.manifest.case_id !== 'C12') return null;
  const o = outputsOf({ data });
  if (!o) return null;
  const cp = o.ba_cva.counterparties[0];
  return {
    data,
    peers,
    t: 0,
    horizon: '12m',
    subject: 'book',
    b: Math.max(0, (o.wrong_way_risk?.b_grid ?? []).indexOf(0)),
    caseId: 'base',
    collateral: null,
    sector: cp && isSector(cp.sector) ? cp.sector : 'financials',
    rating: cp && isRating(cp.rating_class) ? cp.rating_class : 'investment-grade',
  };
}

// --- money --------------------------------------------------------------------------------------------------------------

/** An amount of USD for a narrow place: scaled to bn or m with the unit that says so (the table beside keeps the whole amount). */
export function amount(v: number | null | undefined, currency = 'USD') {
  // zero is plain USD, never "0 bn USD" (the shared form gives zero the billion unit; R4 c16 m3, R5 c17 m3)
  if (v === 0) return { ...compactMoney(0, currency), value: 0, unit: { en: currency, es: currency } };
  return compactMoney(v ?? null, currency);
}
/** The scale of a money axis in USD: the divisor and the unit its title carries. */
export function axisOf(values: ReadonlyArray<number | null | undefined>, currency = 'USD') {
  return axisScale(Math.max(0, ...values.map((v) => Math.abs(v ?? 0))), currency);
}

// --- the running sum and the histogram -----------------------------------------------------------------------------------

/** The running sum of a column of terms: the build-up of the CVA over the time buckets (its last value is the sum of the terms). */
export function runningSum(terms: readonly number[]): number[] {
  let s = 0;
  return terms.map((x) => (s += x));
}

/** The PITs in `bins` equal classes of (0, 1): the counts a histogram draws. A PIT of exactly 1 falls in the last class. */
export function histogram(pits: readonly number[], bins = 10): number[] {
  const counts = new Array<number>(bins).fill(0);
  for (const p of pits) counts[Math.min(bins - 1, Math.max(0, Math.floor(p * bins)))] += 1;
  return counts;
}

/** The segment of an engine test row in words ("book-10bd-q90" is "Book, 10 business days, quantile 90 %"); an unknown form is returned as it is. */
export function segmentText(segment: string | null | undefined, lang: 'en' | 'es'): string {
  if (!segment) return '';
  const m = /^(book|risk factor|risk-factor)-([0-9a-z]+?)(?:-q(\d+))?$/.exec(segment);
  const horizon = m ? HORIZON_LONG[m[2]] : undefined;
  if (!m || !horizon) return segment;
  const subject = SUBJECT_TEXT[m[1] === 'book' ? 'book' : 'risk-factor'][lang];
  const quantile = m[3] ? `${lang === 'es' ? 'cuantil' : 'quantile'} ${m[3]} %` : '';
  return [subject, horizon[lang], quantile].filter(Boolean).join(', ');
}
