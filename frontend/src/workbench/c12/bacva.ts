// The live BA-CVA of C12: a TypeScript port of the basic approach to CVA risk (MAR50, in force 2023-01-01), reduced
// version, held to the C12 documents' `ba_cva` block by a parity test at 1e-9 relative. Every formula and constant is
// transcribed from dossier 01 section E.1 (read at the BIS page on 2026-10-04):
//   capital = DS_BA-CVA K_reduced, DS = 0.65                                                MAR50.14 to MAR50.16
//   K_reduced = sqrt((rho sum SCVA_c)^2 + (1 - rho^2) sum SCVA_c^2), rho = 50%
//   SCVA_c = (1 / alpha) RW_c sum_NS M_NS EAD_NS DF_NS, alpha = 1.4
//   DF_NS = (1 - exp(-0.05 M_NS)) / (0.05 M_NS), and 1 for a bank with an approved internal model (IMM)
//   RW_c by sector and rating class: MAR50.16 Table 1
// The materiality threshold (MAR50.9) and the full version (single-name and index hedges, MAR50.20 to 25) are not
// ported: C12 holds no hedge, and the document says so. Dossier 01 states that no official numeric example of BA-CVA is
// verified (addendum R8), so the parity is to the document's block and the invariants are the tests of this port.

/** DS of MAR50.14. */
export const BA_CVA_DS = 0.65;
/** The supervisory correlation of MAR50.15. */
export const BA_CVA_RHO = 0.5;
/** Alpha of MAR50.15. */
export const BA_CVA_ALPHA = 1.4;
/** The discount rate of the supervisory discount factor, MAR50.15. */
export const BA_CVA_RATE = 0.05;

export type SectorId =
  | 'sovereigns-central-banks-mdbs'
  | 'local-government-public'
  | 'financials'
  | 'basic-materials-energy-industrials'
  | 'consumer-transport-administrative'
  | 'technology-telecoms'
  | 'health-care-utilities-professional'
  | 'other';
export type RatingClass = 'investment-grade' | 'high-yield-or-not-rated';

/** MAR50.16 Table 1: the risk weight of the investment grade and of the high yield or not rated counterparties of each sector. */
export const BA_CVA_RISK_WEIGHTS: Record<SectorId, readonly [number, number]> = {
  'sovereigns-central-banks-mdbs': [0.005, 0.02],
  'local-government-public': [0.01, 0.04],
  financials: [0.05, 0.12],
  'basic-materials-energy-industrials': [0.03, 0.07],
  'consumer-transport-administrative': [0.03, 0.085],
  'technology-telecoms': [0.02, 0.055],
  'health-care-utilities-professional': [0.015, 0.05],
  other: [0.05, 0.12],
};

export const SECTORS = Object.keys(BA_CVA_RISK_WEIGHTS) as SectorId[];

export const riskWeight = (sector: SectorId, rating: RatingClass): number => BA_CVA_RISK_WEIGHTS[sector][rating === 'investment-grade' ? 0 : 1];

/** The supervisory discount factor of a netting set of effective maturity M years. */
export const discountFactor = (m: number, immBank = false): number => (immBank ? 1 : -Math.expm1(-BA_CVA_RATE * m) / (BA_CVA_RATE * m));

export interface BaCvaNettingSet {
  ead: number;
  mYears: number;
}

/** SCVA of one counterparty: (1 / alpha) RW sum over its netting sets of M EAD DF. */
export function scva(rw: number, sets: BaCvaNettingSet[], immBank = false): number {
  return (rw * sets.reduce((s, n) => s + n.mYears * n.ead * discountFactor(n.mYears, immBank), 0)) / BA_CVA_ALPHA;
}

/** K_reduced over the counterparties' SCVA. */
export function kReduced(scvas: number[], rho = BA_CVA_RHO): number {
  const sum = scvas.reduce((s, x) => s + x, 0);
  const squares = scvas.reduce((s, x) => s + x * x, 0);
  return Math.sqrt((rho * sum) ** 2 + (1 - rho * rho) * squares);
}

export interface BaCvaCounterparty {
  rw: number;
  sets: BaCvaNettingSet[];
}

export interface BaCvaResult {
  scva: number[];
  kReduced: number;
  capital: number;
}

export function baCva(counterparties: BaCvaCounterparty[], immBank = false): BaCvaResult {
  const s = counterparties.map((c) => scva(c.rw, c.sets, immBank));
  const k = kReduced(s);
  return { scva: s, kReduced: k, capital: BA_CVA_DS * k };
}

/** The slice of a C12 document's `ba_cva` block the port reads and is held to. */
export interface BaCvaBlock {
  imm_bank: boolean;
  counterparties: Array<{ sector: string; rating_class: string; risk_weight: number; ead: { amount: number }; m_years: number; discount_factor: number; scva: number }>;
  k_reduced: number;
  capital: { amount: number };
}

/** The port's input from the document's block: its counterparties with their risk weights and netting sets. */
export function baCvaInputFrom(block: BaCvaBlock): BaCvaCounterparty[] {
  return block.counterparties.map((c) => ({ rw: c.risk_weight, sets: [{ ead: c.ead.amount, mYears: c.m_years }] }));
}

const closeTo = (a: number, b: number, rel: number): boolean => a === b || Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b));

/** Every field in which the port's result departs from the document's block at the relative tolerance; empty when it is the block. */
export function baCvaMismatches(r: BaCvaResult, block: BaCvaBlock, rel = 1e-9): string[] {
  const out: string[] = [];
  const check = (name: string, live: number, committed: number) => {
    if (!closeTo(live, committed, rel)) out.push(`${name}: live ${live}, committed ${committed}`);
  };
  block.counterparties.forEach((c, i) => {
    check(`${c.sector}.discount_factor`, discountFactor(c.m_years, block.imm_bank), c.discount_factor);
    check(`${c.sector}.scva`, r.scva[i], c.scva);
    if (riskWeight(c.sector as SectorId, c.rating_class as RatingClass) !== c.risk_weight) out.push(`${c.sector}.risk_weight: MAR50.16 Table 1 differs from the committed one`);
  });
  check('k_reduced', r.kReduced, block.k_reduced);
  check('capital', r.capital, block.capital.amount);
  return out;
}
