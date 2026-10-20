// The live lane of the regulation map (SDD section 3, the lanes rule): the regulatory calculators that belong to no case,
// recomputed in the browser from the parameters of the regulatory-calculators document. Each is a port of a function of
// riskvalidation.regulatory (engine-regulatory-api 2.0.0) and is held to the document by engine/regulatory.test.ts within
// 1e-9 relative: the CRE20 lookup (standardised.lookup and the LTV steps of Tables 11 to 14), the output floor with its
// RBC90.1 phase-in (output_floor), the SBM aggregation under the three correlation scenarios of MAR21.6 with the
// MAR21.4(5)(b) fallback (frtb.bucket_charge, cross_bucket_charge) and the liquidity-horizon cascade of MAR33.4
// (frtb.liquidity_cascade_es). Every table value is read from the document with its paragraph and in-force date; nothing
// here is a regulatory parameter of its own. SA-CCR and BA-CVA are ported beside C12, on the case's netting sets.
import type { components } from '../lib/contract.gen';
import type { Kind } from '../lib/contract.types';

type Schemas = components['schemas'];
export type RegulatoryDoc = Schemas['regulatory-calculators'];
export type RegulatoryEntry = Schemas['regulatoryEntry'];
export type RegulatoryValue = Schemas['regulatoryValue'];
export type GridRow = Schemas['regulatoryGridRow'];
export type PhaseInRow = Schemas['regulatoryPhaseIn'];
export type ParameterTable = Schemas['regulatoryParameterTable'];
export type ExposureClass = GridRow['exposure_class'];

// ---------------------------------------------------------------------------------------------------------------------
// the descriptor: one key per key of the regulatory-calculators 1.0.0 schema, tested against the committed document

const text: Kind = 'text';
const str: Kind = 'string';
const VALUE: Kind = { object: { name: str, symbol: str, value: { anyOf: ['number', 'string', { array: 'number' }] }, unit: str, basis: str, paragraph: str } };
const TRADE: Kind = { object: { trade_id: str, nature: str, paragraph: str, terms: { array: VALUE } } };
const PUBLISHED: Kind = { object: { name: str, value: 'number', unit: str, rounding: str, paragraph: str } };
const ENTRY: Kind = { object: {
  id: str,
  calculator: str,
  title: text,
  kind: str,
  paragraph: str,
  paragraph_range: str,
  in_force_date: str,
  published_date: str,
  source: str,
  trades: { array: TRADE },
  inputs: { array: VALUE },
  outputs: { array: VALUE },
  published: { array: PUBLISHED },
  statement: { nullable: text },
  holds: { nullable: 'boolean' },
  tolerance_relative: 'number',
} };
const PHASE_IN: Kind = { object: { year: 'integer', effective_from: str, factor: 'number', table: str, paragraph: str, in_force_date: str } };
const TABLE: Kind = { object: {
  id: str,
  title: text,
  calculator: str,
  table: str,
  paragraph: str,
  in_force_date: str,
  source: str,
  rows: { array: { object: { key: str, parameter: str, value: 'number', unit: str } } },
} };
const GRID: Kind = { object: {
  exposure_class: str,
  key: str,
  band: str,
  short_term: 'boolean',
  cash_flow_dependent: 'boolean',
  counterparty_weight: { nullable: 'number' },
  risk_weight: 'number',
  table: str,
  paragraph: str,
  in_force_date: str,
} };

export const REGULATORY_CALCULATORS: Kind = { object: {
  schema: str,
  case_id: str,
  document_id: str,
  engine: { object: { name: str, version: str } },
  units: { object: { money: str, rate: str, dates: str } },
  official_examples: { array: ENTRY },
  invariant_cases: { array: ENTRY },
  output_floor_phase_in: { array: PHASE_IN },
  parameter_tables: { array: TABLE },
  cre20_grid: { array: GRID },
  provenance: { object: {
    truth_status: str,
    inputs: { array: { object: { source: str, class: str, files: { array: str } } } },
    licence_classes: { map: str },
    generators: { array: str },
    seed: 'number',
    code_version: str,
    riskvalidation_version: { nullable: str },
  } },
  lane: { object: { lane: str, reasons: { array: str } } },
} };

// ---------------------------------------------------------------------------------------------------------------------
// reading the document

/** The calculator entry (an official example or an invariant case) of `id`. */
export function entryById(doc: RegulatoryDoc, id: string): RegulatoryEntry | undefined {
  return [...doc.official_examples, ...doc.invariant_cases].find((e) => e.id === id);
}

/** The parameter table of `id` (CRE52.72 Table 2, MAR50.16 Table 1, MAR33.4 Table 1, MAR33.12 Table 2). */
export function parameterTable(doc: RegulatoryDoc, id: ParameterTable['id']): ParameterTable | undefined {
  return doc.parameter_tables.find((t) => t.id === id);
}

function valueOf(values: RegulatoryValue[], name: string): RegulatoryValue['value'] {
  const v = values.find((x) => x.name === name);
  if (!v) throw new Error(`${name}: absent from the document`);
  return v.value;
}

/** The named value as a number; a value that is not one throws, so a view never draws a guess. */
export function numberOf(values: RegulatoryValue[], name: string): number {
  const v = valueOf(values, name);
  if (typeof v !== 'number') throw new Error(`${name}: not a number in the document`);
  return v;
}

/** The named value as a vector of numbers. */
export function vectorOf(values: RegulatoryValue[], name: string): number[] {
  const v = valueOf(values, name);
  if (!Array.isArray(v)) throw new Error(`${name}: not a vector in the document`);
  return v;
}

/** The named value as a square matrix: the document writes it row-major in one array. */
export function matrixOf(values: RegulatoryValue[], name: string): number[][] {
  const flat = vectorOf(values, name);
  const n = Math.round(Math.sqrt(flat.length));
  if (n * n !== flat.length) throw new Error(`${name}: ${flat.length} values are not a square matrix`);
  return Array.from({ length: n }, (_, i) => flat.slice(i * n, (i + 1) * n));
}

// ---------------------------------------------------------------------------------------------------------------------
// CRE20: the standardised risk weights as a lookup on the document's grid (riskvalidation.regulatory.standardised.lookup)

export interface CellOptions {
  shortTerm?: boolean;
  cashFlowDependent?: boolean;
  counterpartyWeight?: number | null;
}

/** The cells of one exposure class, in the document's order. */
export function gridRows(grid: GridRow[], cls: ExposureClass): GridRow[] {
  return grid.filter((r) => r.exposure_class === cls);
}

/** The cell keyed exactly as the engine keys it, or null: a key outside the tables never gets a placeholder weight. */
export function findCell(grid: GridRow[], cls: ExposureClass, key: string, o: CellOptions = {}): GridRow | null {
  const cp = o.counterpartyWeight ?? null;
  return grid.find((r) => r.exposure_class === cls && r.key === key && r.short_term === (o.shortTerm ?? false) && r.cash_flow_dependent === (o.cashFlowDependent ?? false) && r.counterparty_weight === cp) ?? null;
}

const LTV_CLASSES: ReadonlySet<ExposureClass> = new Set<ExposureClass>(['residential-re', 'commercial-re']);

export interface LtvStep {
  /** The upper edge of the band as a decimal LTV; the last band of a class has no upper edge and its key stands for it. */
  upTo: number;
  row: GridRow;
}

/** The LTV bands of a real estate class for one cash-flow dependence (and, for commercial real estate that is not cash-flow dependent, one counterparty weight), ascending. */
export function ltvSteps(grid: GridRow[], cls: ExposureClass, o: { cashFlowDependent: boolean; counterpartyWeight?: number | null }): LtvStep[] {
  if (!LTV_CLASSES.has(cls)) return [];
  const cp = o.counterpartyWeight ?? null;
  return grid
    .filter((r) => r.exposure_class === cls && r.cash_flow_dependent === o.cashFlowDependent && r.counterparty_weight === cp)
    .map((row) => ({ upTo: Number(row.key), row }))
    .filter((s) => Number.isFinite(s.upTo))
    .sort((a, b) => a.upTo - b.upTo);
}

/** The band that holds `ltv`: the upper edge of a band belongs to it, and an LTV above the last edge is in the last band. */
export function ltvRow(grid: GridRow[], cls: ExposureClass, ltv: number, o: { cashFlowDependent: boolean; counterpartyWeight?: number | null }): GridRow | null {
  const steps = ltvSteps(grid, cls, o);
  if (steps.length === 0 || !Number.isFinite(ltv) || ltv < 0) return null;
  return (steps.find((s) => ltv <= s.upTo + 1e-12) ?? steps[steps.length - 1]).row;
}

export interface MismatchResult {
  adjusted: number;
  multiplier: GridRow;
  cap: GridRow;
  capped: boolean;
}

/** CRE20.92: 1.5 times the weight of an unhedged retail or residential exposure to an individual, at most 150 percent. */
export function adjustForCurrencyMismatch(grid: GridRow[], weight: number): MismatchResult | null {
  const multiplier = findCell(grid, 'currency-mismatch', 'multiplier');
  const cap = findCell(grid, 'currency-mismatch', 'cap');
  if (!multiplier || !cap) return null;
  const raw = multiplier.risk_weight * weight;
  return { adjusted: Math.min(raw, cap.risk_weight), multiplier, cap, capped: raw > cap.risk_weight };
}

/** The credit equivalent amount (exposure times the conversion factor) and the risk-weighted amount (CRE20.94 to CRE20.101). */
export function creditEquivalentRwa(a: { exposure: number; ccf: number; weight: number }): { creditEquivalent: number; rwa: number } {
  const creditEquivalent = a.exposure * a.ccf;
  return { creditEquivalent, rwa: creditEquivalent * a.weight };
}

// ---------------------------------------------------------------------------------------------------------------------
// the output floor (RBC20.4, RBC90.1, RBC90.2; riskvalidation.regulatory.output_floor)

/** The phase-in row in force in `year`: the row of that year, the last row from the last year on, and null before the first (a year the schedule does not reach). */
export function phaseInRow(rows: PhaseInRow[], year: number): PhaseInRow | null {
  const sorted = [...rows].sort((a, b) => a.year - b.year);
  if (sorted.length === 0 || year < sorted[0].year) return null;
  let hit = sorted[0];
  for (const r of sorted) if (r.year <= year) hit = r;
  return hit;
}

/** RWA = max(RWA nominated, f times RWA SA-only); the optional RBC90.2 cap limits the increase to `capShare` of the pre-floor RWA. */
export function flooredRwa(nominated: number, saOnly: number, factor: number, capShare: number | null = null): number {
  const uncapped = Math.max(nominated, factor * saOnly);
  return capShare === null ? uncapped : Math.min(uncapped, nominated * (1 + capShare));
}

export interface FloorBreakdown {
  /** The pre-floor RWA: the nominated one. */
  pre: number;
  /** The floor base: the factor times the standardised-only RWA. */
  floor: number;
  /** The result before the cap. */
  uncapped: number;
  rwa: number;
  increase: number;
  floorBinds: boolean;
  capBinds: boolean;
}

export function floorBreakdown(nominated: number, saOnly: number, factor: number, capShare: number | null = null): FloorBreakdown {
  const floor = factor * saOnly;
  const uncapped = Math.max(nominated, floor);
  const rwa = flooredRwa(nominated, saOnly, factor, capShare);
  return { pre: nominated, floor, uncapped, rwa, increase: rwa - nominated, floorBinds: floor > nominated, capBinds: capShare !== null && uncapped > nominated * (1 + capShare) };
}

// ---------------------------------------------------------------------------------------------------------------------
// the FRTB sensitivities-based method (MAR21.4 to MAR21.7; riskvalidation.regulatory.frtb)

export const SCENARIOS = ['low', 'medium', 'high'] as const;
export type Scenario = (typeof SCENARIOS)[number];

/** MAR21.6: medium is the prescribed correlation, high min(1.25 rho, 1), low max(2 rho - 1, 0.75 rho). */
export function scenarioRho(rho: number, scenario: Scenario): number {
  if (scenario === 'medium') return rho;
  if (scenario === 'high') return Math.min(1.25 * rho, 1);
  return Math.max(2 * rho - 1, 0.75 * rho);
}

/** MAR21.4 within a bucket: K_b = sqrt(max(0, sum WS_k^2 + sum_{k != l} rho_kl WS_k WS_l)), `rho` row-major and n by n, the diagonal untouched. */
export function bucketCharge(ws: number[], rho: number[], scenario: Scenario): number {
  const n = ws.length;
  let total = 0;
  for (let k = 0; k < n; k++) for (let l = 0; l < n; l++) total += k === l ? ws[k] * ws[k] : scenarioRho(rho[k * n + l], scenario) * ws[k] * ws[l];
  return Math.sqrt(Math.max(0, total));
}

export interface CrossBucket {
  charge: number;
  /** Whether the radicand was negative and S_b was replaced by max(min(sum WS, K_b), -K_b) (MAR21.4(5)(b)). */
  fallback: boolean;
  /** The S_b the charge used: the sums of the weighted sensitivities, or their replacements. */
  sb: number[];
}

/** MAR21.4 across buckets: sqrt(sum K_b^2 + sum_{b != c} gamma_bc S_b S_c) with the fallback when the radicand is negative. */
export function crossBucketCharge(kb: number[], sb: number[], gamma: number, scenario: Scenario): CrossBucket {
  const g = scenarioRho(gamma, scenario);
  const radicand = (s: number[]) => kb.reduce((a, k) => a + k * k, 0) + s.reduce((a, x, b) => a + s.reduce((c, y, d) => c + (b === d ? 0 : g * x * y), 0), 0);
  const plain = radicand(sb);
  if (plain >= 0) return { charge: Math.sqrt(plain), fallback: false, sb };
  const alt = sb.map((s, b) => Math.max(Math.min(s, kb[b]), -kb[b]));
  return { charge: Math.sqrt(Math.max(radicand(alt), 0)), fallback: true, sb: alt };
}

export interface SbmInput {
  /** The weighted sensitivities of each bucket. */
  ws: number[][];
  /** The within-bucket correlations of each bucket, n by n. */
  rho: number[][][];
  /** The cross-bucket correlation (one value between every two buckets). */
  gamma: number;
}

export interface SbmScenario {
  kb: number[];
  sb: number[];
  charge: number;
  fallback: boolean;
}

export interface SbmResult {
  scenarios: Record<Scenario, SbmScenario>;
  /** MAR21.7: the maximum over the three scenarios. */
  charge: number;
  /** The scenario that gave the maximum (the first of low, medium, high on a tie). */
  binding: Scenario;
}

export function sbmAggregate(input: SbmInput): SbmResult {
  const scenarios = {} as Record<Scenario, SbmScenario>;
  for (const s of SCENARIOS) {
    const kb = input.ws.map((w, b) => bucketCharge(w, input.rho[b].flat(), s));
    const sums = input.ws.map((w) => w.reduce((a, x) => a + x, 0));
    const cross = crossBucketCharge(kb, sums, input.gamma, s);
    scenarios[s] = { kb, sb: cross.sb, charge: cross.charge, fallback: cross.fallback };
  }
  let binding: Scenario = 'low';
  for (const s of SCENARIOS) if (scenarios[s].charge > scenarios[binding].charge) binding = s;
  return { scenarios, charge: scenarios[binding].charge, binding };
}

// ---------------------------------------------------------------------------------------------------------------------
// the liquidity-horizon cascade (MAR33.4; riskvalidation.regulatory.frtb.liquidity_cascade_es)

export interface CascadeTerm {
  j: number;
  lh: number;
  /** sqrt((LH_j - LH_{j-1}) / T); the first subset has none. */
  weight: number | null;
  es: number;
  /** The term inside the square root before squaring: ES_T(P) for j = 1, ES_T(P, j) times the weight after. */
  term: number;
}

/** The terms of the cascade: `lhs` the horizons LH_1 to LH_m of MAR33.4 Table 1 in days, `esByJ` the ES_T(P, j) for j = 2 to m (absent ones count as zero). */
export function cascadeTerms(esT: number, esByJ: number[], lhs: number[], t = 10): CascadeTerm[] {
  return lhs.map((lh, i) => {
    if (i === 0) return { j: 1, lh, weight: null, es: esT, term: esT };
    const weight = Math.sqrt((lh - lhs[i - 1]) / t);
    const es = esByJ[i - 1] ?? 0;
    return { j: i + 1, lh, weight, es, term: es * weight };
  });
}

/** ES = sqrt(ES_T(P)^2 + sum_{j >= 2} (ES_T(P, j) sqrt((LH_j - LH_{j-1}) / T))^2). */
export function liquidityCascadeEs(esT: number, esByJ: number[], lhs: number[], t = 10): number {
  return Math.sqrt(cascadeTerms(esT, esByJ, lhs, t).reduce((a, x) => a + x.term * x.term, 0));
}

/** The subsets Q(p, j) a risk factor with liquidity horizon `factorLh` belongs to: those whose horizon it reaches, as 1-based indices. */
export function subsetMembership(lhs: number[], factorLh: number): number[] {
  return lhs.flatMap((lh, i) => (lh <= factorLh ? [i + 1] : []));
}
